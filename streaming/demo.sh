#!/usr/bin/env bash
# =============================================================================
# Demo extremo a extremo de la capa de streaming + prueba de tolerancia a fallos.
#
#   bash streaming/demo.sh            # corrida limpia (borra estado de streaming previo)
#   bash streaming/demo.sh --sin-fallo  # sin matar el consumidor a mitad del flujo
#
# Pasos: levanta Kafka/Postgres, aplica el DDL, arranca Spark, reproduce el
# fixture real, mata Spark a mitad del flujo, lo reinicia, espera a que drene
# y escribe metricas reales en docs/build/metricas_streaming.json.
# Requisitos: Docker en ejecucion y el venv del proyecto con confluent-kafka.
# =============================================================================
set -euo pipefail
export MSYS_NO_PATHCONV=1   # Git Bash en Windows: no reescribir rutas /opt/...
cd "$(dirname "$0")/.."

COMPOSE=(docker compose -f docker-compose.yml -f streaming/docker-compose.streaming.yml)
SPARK=dw_musicbrainz_spark
RT=streaming/_runtime
FIXTURE=streaming/fixtures/lanzamientos_muestra.jsonl
ESPERADOS_VALIDOS=299
CON_FALLO=1
[[ "${1:-}" == "--sin-fallo" ]] && CON_FALLO=0

if [[ -x .venv/Scripts/python.exe ]]; then PY=.venv/Scripts/python.exe
elif [[ -x .venv/bin/python ]]; then PY=.venv/bin/python
else PY=python3; fi

PG_USER="${PG_USER:-postgres}"; PG_DATABASE="${PG_DATABASE:-dw_musicbrainz}"
psql_pg() { "${COMPOSE[@]}" exec -T postgres psql -U "$PG_USER" -d "$PG_DATABASE" -v ON_ERROR_STOP=1 "$@"; }
log() { printf '\n\033[1;36m[demo] %s\033[0m\n' "$*"; }

mkdir -p "$RT"
rm -f "$RT"/*.json

log "1/8 Limpieza del estado previo de streaming (solo topicos, checkpoints, lago y esquema streaming)"
"${COMPOSE[@]}" rm -sf spark-consumidor >/dev/null 2>&1 || true
PROYECTO="${COMPOSE_PROJECT_NAME:-$(basename "$PWD" | tr '[:upper:]' '[:lower:]' | tr -cd 'a-z0-9_-')}"
docker volume rm -f "${PROYECTO}_spark_checkpoints" "${PROYECTO}_spark_lake" >/dev/null 2>&1 || true

log "2/8 Levantando PostgreSQL y Kafka (KRaft) + creacion de topicos"
"${COMPOSE[@]}" up -d postgres kafka
"${COMPOSE[@]}" exec -T kafka /opt/kafka/bin/kafka-topics.sh --bootstrap-server kafka:19092 \
    --delete --topic 'musicbrainz\.lanzamientos.*' >/dev/null 2>&1 || true
sleep 3
"${COMPOSE[@]}" run --rm kafka-init

log "3/8 Aplicando sql/streaming/01_schema_streaming.sql"
until "${COMPOSE[@]}" exec -T postgres pg_isready -U "$PG_USER" >/dev/null 2>&1; do sleep 2; done
psql_pg -f /sql/streaming/01_schema_streaming.sql >/dev/null
psql_pg -c "TRUNCATE streaming.lanzamientos_evento, streaming.lanzamientos_ventana, streaming.control_lotes;" >/dev/null

log "4/8 Arrancando el consumidor Spark (la primera vez descarga dependencias Maven)"
"${COMPOSE[@]}" up -d spark-consumidor
for i in $(seq 1 120); do
  docker logs "$SPARK" 2>&1 | grep -q "consultas activas" && break
  sleep 5
done
docker logs "$SPARK" 2>&1 | grep -q "consultas activas" || { echo "Spark no arranco"; docker logs --tail 80 "$SPARK"; exit 1; }

conteo_pg() { psql_pg -tA -c "SELECT count(*) FROM streaming.lanzamientos_evento;" | tr -d '[:space:]'; }

log "5/8 Reproduciendo el fixture real a 10 eventos/s"
"$PY" -m streaming.productor --fuente archivo --archivo "$FIXTURE" \
      --eventos-por-segundo 10 --metricas "$RT/productor.json" &
PID_PROD=$!

REINICIO_JSON="$RT/reinicio.json"
if [[ $CON_FALLO == 1 ]]; then
  sleep 12
  ANTES=$(conteo_pg)
  log "6/8 PRUEBA DE FALLO: docker kill del consumidor con $ANTES filas en Postgres"
  T0=$(date +%s)
  docker kill "$SPARK" >/dev/null
  wait $PID_PROD
  sleep 5
  log "     Reiniciando el consumidor (recupera offsets y estado desde los checkpoints)"
  docker start "$SPARK" >/dev/null
else
  wait $PID_PROD
fi

log "7/8 Esperando a que el consumidor drene el topico (esperados: $ESPERADOS_VALIDOS validos)"
for i in $(seq 1 90); do
  [[ "$(conteo_pg)" -ge $ESPERADOS_VALIDOS ]] && break
  sleep 4
done
sleep 25   # deja cerrar los lotes de ventanas y DLQ en curso
FINAL=$(conteo_pg)

if [[ $CON_FALLO == 1 ]]; then
  T1=$(date +%s)
  OMITIDOS=$(docker logs "$SPARK" 2>&1 | grep -c "ya aplicado" || true)
  DUP=$(psql_pg -tA -c "SELECT count(*) - count(DISTINCT mbid) FROM streaming.lanzamientos_evento;" | tr -d '[:space:]')
  RESULT=$([[ "$FINAL" == "$ESPERADOS_VALIDOS" && "$DUP" == "0" ]] && echo ok || echo fallo)
  cat > "$REINICIO_JSON" <<EOF
{"ejecutada": true, "metodo": "docker kill (SIGKILL) del contenedor Spark a los 12 s de iniciado el productor",
 "filas_postgres_al_matar": $ANTES, "filas_postgres_final": $FINAL, "esperadas": $ESPERADOS_VALIDOS,
 "duplicados_mbid": $DUP, "lotes_reejecutados_omitidos_por_control": $OMITIDOS,
 "segundos_desde_kill_hasta_drenado": $((T1 - T0)), "resultado": "$RESULT"}
EOF
else
  echo '{"ejecutada": false}' > "$REINICIO_JSON"
fi

log "8/8 Conteos finales"
docker exec "$SPARK" /opt/spark/bin/spark-submit /opt/app/streaming/inspeccionar_lago.py 2>/dev/null \
  | grep RESULTADO_LAGO | sed 's/^RESULTADO_LAGO //' > "$RT/bronze.json"
psql_pg -c "SELECT * FROM streaming.v_latencia;"
psql_pg -c "SELECT consulta, count(*) AS lotes, sum(filas) AS filas FROM streaming.control_lotes GROUP BY 1;"
psql_pg -c "SELECT pais, formato, sum(lanzamientos) AS lanzamientos, sum(pistas) AS pistas
            FROM streaming.lanzamientos_ventana GROUP BY 1,2 ORDER BY 3 DESC LIMIT 10;"
"${COMPOSE[@]}" exec -T kafka /opt/kafka/bin/kafka-get-offsets.sh --bootstrap-server kafka:19092 \
    --topic musicbrainz.lanzamientos
"${COMPOSE[@]}" exec -T kafka /opt/kafka/bin/kafka-get-offsets.sh --bootstrap-server kafka:19092 \
    --topic musicbrainz.lanzamientos.dlq
echo "Muestra de la DLQ:"
"${COMPOSE[@]}" exec -T kafka /opt/kafka/bin/kafka-console-consumer.sh --bootstrap-server kafka:19092 \
    --topic musicbrainz.lanzamientos.dlq --from-beginning --max-messages 5 --timeout-ms 10000 || true

"$PY" -m streaming.recolectar_metricas --productor "$RT/productor.json" \
      --bronze "$RT/bronze.json" --reinicio "$REINICIO_JSON" > /dev/null
log "Metricas escritas en docs/build/metricas_streaming.json"
