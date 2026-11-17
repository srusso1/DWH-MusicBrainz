# Capa de streaming (speed layer): Kafka → Spark Structured Streaming → PostgreSQL

Esta carpeta agrega al Data Warehouse una capa de procesamiento en tiempo real que
complementa la capa batch de Databricks. Los eventos son **lanzamientos reales de
MusicBrainz** obtenidos de la API pública WS2; no se generan datos sintéticos.

## 1. Arquitectura (Lambda)

```
                  ┌──────────────── capa batch ────────────────┐
 Volcado MusicBrainz ─► Databricks (PySpark + Delta) ─► Bronze ─► Silver ─► Gold (Kimball, 58,8 M pistas)
                  └────────────────────────────────────────────┘
                  ┌──────────────── capa de velocidad ─────────┐
 API WS2 / JSONL ─► productor.py ─► Kafka: musicbrainz.lanzamientos (3 particiones)
                                          │
                                          ▼
                       consumidor_spark.py (Structured Streaming)
                        ├─► Bronze local (parquet, partición por fecha de ingesta)
                        ├─► Kafka: musicbrainz.lanzamientos.dlq (eventos inválidos + motivo)
                        ├─► PostgreSQL streaming.lanzamientos_evento   (UPSERT por MBID)
                        └─► PostgreSQL streaming.lanzamientos_ventana  (ventanas de 1 min)
                  └────────────────────────────────────────────┘
```

- **Capa batch**: recalcula la historia completa con alta precisión (Databricks).
- **Capa de velocidad**: entrega en segundos los lanzamientos nuevos, con reglas
  de calidad idénticas en productor y consumidor (`streaming/lib/eventos.py`).
- **Capa de servicio**: PostgreSQL (`streaming.*`) consultable junto con `gold.*`.

## 2. Tópicos

| Tópico | Particiones | Retención | Clave | Uso |
|---|---|---|---|---|
| `musicbrainz.lanzamientos` | 3 | 7 días | MBID del lanzamiento | eventos de entrada |
| `musicbrainz.lanzamientos.dlq` | 1 | 30 días | clave original | eventos inválidos con motivo y offset de origen |

Los tópicos se crean explícitamente (contenedor `kafka-init`); la creación
automática está deshabilitada en el broker para evitar tópicos accidentales.

## 3. Productor (`productor.py`, confluent-kafka)

| Configuración | Valor | Motivo |
|---|---|---|
| `enable.idempotence` | `true` | los reintentos no duplican mensajes (número de secuencia por partición) |
| `acks` | `all` | el broker confirma solo cuando todas las réplicas sincronizadas escribieron |
| `retries` / `delivery.timeout.ms` | máximo / 120 s | reintenta fallos transitorios hasta el plazo de entrega |
| `max.in.flight.requests.per.connection` | 5 | máximo compatible con idempotencia conservando el orden |
| `linger.ms` / `batch.size` | 20 ms / 64 KB | micro-lotes para mayor rendimiento |
| `compression.type` | `lz4` | menos red y disco con bajo costo de CPU |
| clave | MBID | todos los eventos de un lanzamiento van a la misma partición, en orden |

Otros mecanismos: callback de entrega con contadores por partición, manejo de
`BufferError` (cola local llena), `flush` ordenado ante `SIGINT`/`SIGTERM`,
deduplicación LRU de MBID ya enviados y, en la fuente API, límite de 1 solicitud
por segundo, *User-Agent* genérico (`DWMusicBrainz-Streaming/1.0 (proyecto academico)`)
y reintento ante respuestas 503.

```bash
# Reproducir el fixture real a 10 eventos/s
python -m streaming.productor --fuente archivo --eventos-por-segundo 10
# Sondear la API de forma continua (lanzamientos fechados en los últimos 30 días)
python -m streaming.productor --fuente api --continuo --intervalo-sondeo 60
```

## 4. Consumidor (`consumidor_spark.py`, Spark 3.5.3 Structured Streaming)

| Decisión | Detalle | Motivo |
|---|---|---|
| `startingOffsets=earliest` | solo en el primer arranque | después manda el checkpoint |
| `failOnDataLoss=false` | | tolera offsets eliminados por retención sin detener el flujo |
| `maxOffsetsPerTrigger=100` | configurable (`MAX_OFFSETS_POR_LOTE`) | contrapresión: lotes acotados |
| `from_json` con esquema explícito + UDF de validación | | mismas reglas que las pruebas unitarias |
| DLQ en Kafka | JSON con `motivo`, `valor_original`, partición y offset de origen | ningún mensaje se pierde ni detiene el flujo |
| Bronze parquet | `partitionBy(fecha_ingesta)` | sumidero de archivos exactamente-una-vez (`_spark_metadata`) |
| `withWatermark("evento_ts", "2 minutes")` + `window(1 minute)` | por país y formato | acota el estado y admite eventos tardíos hasta 2 min |
| `foreachBatch` + `INSERT … ON CONFLICT` | staging JDBC + transacción | UPSERT idempotente |
| `streaming.control_lotes (consulta, batch_id)` | se inserta en la misma transacción | un lote re-ejecutado tras un fallo se omite |
| Spark SQL | vista temporal + `row_number()` por MBID en cada lote | `ON CONFLICT` no admite la misma clave dos veces |
| Checkpoint por consulta | `bronze`, `dlq`, `eventos`, `ventanas` | recuperación independiente de offsets y estado |
| RocksDB state store | | estado de ventanas fuera del heap de la JVM |

Reglas de validación (`motivo` enviado a la DLQ): `mensaje_vacio`,
`json_malformado`, `json_no_objeto`, `mbid_ausente`, `mbid_invalido` (no UUID),
`fecha_invalida` (no es AAAA, AAAA-MM ni AAAA-MM-DD válida), `numero_pistas_invalido`,
`evento_ts_ausente`, `esquema_incompatible`.

### Garantías de entrega

| Tramo | Garantía |
|---|---|
| Productor → Kafka | exactamente-una-vez por partición dentro de la sesión del productor (idempotencia) |
| Kafka → Bronze parquet | exactamente-una-vez (checkpoint + bitácora del sumidero de archivos) |
| Kafka → PostgreSQL | exactamente-una-vez efectivo (UPSERT + control de `batch_id` en la misma transacción) |
| Kafka → DLQ | al-menos-una-vez (el sumidero Kafka de Spark no es transaccional); un reinicio puede repetir mensajes de la DLQ |

## 5. Ejecución

Requisitos: Docker Desktop en ejecución y el entorno virtual del proyecto con
`pip install -r requirements.txt` (incluye `confluent-kafka`).

```bash
# Demo completa: levanta todo, reproduce el fixture, mata y reinicia Spark,
# verifica que no haya duplicados y escribe docs/build/metricas_streaming.json
bash streaming/demo.sh
bash streaming/demo.sh --sin-fallo     # sin la prueba de reinicio

# Manual
docker compose -f docker-compose.yml -f streaming/docker-compose.streaming.yml up -d
docker compose -f docker-compose.yml -f streaming/docker-compose.streaming.yml exec -T postgres \
    psql -U postgres -d dw_musicbrainz -f /sql/streaming/01_schema_streaming.sql
python -m streaming.productor --fuente archivo
```

Consultas útiles:

```sql
SELECT * FROM streaming.v_latencia;                       -- latencia productor → PostgreSQL
SELECT pais, formato, sum(lanzamientos) FROM streaming.lanzamientos_ventana GROUP BY 1, 2 ORDER BY 3 DESC;
SELECT consulta, count(*) FROM streaming.control_lotes GROUP BY 1;
```

## 6. Pruebas

```bash
python -m pytest tests/streaming -q
```

- `test_eventos.py` y `test_productor.py`: normalización API → evento, reglas de
  validación, deduplicación y callback de entrega (Python puro).
- `test_consumidor_spark.py`: clasificación válido/DLQ, deduplicación SQL por lote y
  agregación por ventanas sobre el fixture real con Spark local. Se omite si
  PySpark no está instalado (PySpark 3.5 requiere Python ≤ 3.11 en Windows y Java 8/11/17).

## 7. Datos de prueba

`fixtures/lanzamientos_muestra.jsonl` contiene 299 lanzamientos reales capturados de
la API WS2 el 2026-11-17 (`--fuente api --sin-kafka`) y **5 líneas de inyección de
fallas**, documentadas en la cabecera del archivo, derivadas de registros reales y
alteradas a propósito para ejercitar la DLQ. No son datos de negocio.

## 8. Limitaciones conocidas

- Broker único con factor de replicación 1: `acks=all` equivale a la confirmación del líder.
  En producción se usarían 3 brokers y `min.insync.replicas=2`.
- Spark corre en modo `local[2]` dentro de un contenedor; no es un clúster.
- La DLQ es al-menos-una-vez (ver tabla de garantías).
- El agregado por ventanas cuenta eventos recibidos; si el mismo MBID se reenvía en otra
  ventana se cuenta de nuevo. La tabla `lanzamientos_evento` sí está deduplicada por MBID.
