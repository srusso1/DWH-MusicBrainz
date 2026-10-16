# Data Warehouse MusicBrainz (`DWMusicBrainz`)

Data Warehouse analítico de alta volumetría en **PostgreSQL 16** con **Arquitectura Medallón (`silver` -> `gold`)** y **Modelo en Estrella Puro (Ralph Kimball)** íntegramente en español, alimentado exclusivamente con datos 100% reales de la fundación **MetaBrainz (MusicBrainz Database, Schema Sequence 31)**.

---

## 1. Arquitectura General del Sistema

El flujo de datos sigue el patrón Medallón optimizado para alta volumetría con auditoría contable transversal:

```
mbdump.tar.bz2 (C:\Users\sebas\Downloads\mbdump.tar.bz2 o data/downloads/)
           │
           ├── Extracción quirúrgica de TSVs (area, artist, artist_credit_name, release,
           │   release_country, release_unknown_country, medium, recording, track, isrc)
           ▼
        silver (10 Tablas 3NF normalizadas, tipos nativos PostgreSQL + TEXT, PKs e índices)
           │
           ├── Agregación histórica diaria set-based, resolución de claves sustitutas y métricas aditivas
           ▼
         gold (Modelo en Estrella Puro en Español: 6 dimensiones conformadas + fact_produccion_musical)
           │
           └── Consumo analítico (Power BI / 4 Vistas Materializadas OLAP de alto rendimiento)

Esquema meta: meta.etl_audit y meta.data_quality_log (auditoría de lotes y reglas de calidad)
```

---

## 2. Declaración de Negocio y Grano Histórico Diario

* **Declaración del Grano (Ralph Kimball):**
  > *"Un registro individual en la tabla de hechos (`gold.fact_produccion_musical`) representa el resumen histórico diario (`fecha_key`) de la producción musical consolidada por artista (`artista_key`), perfil de lanzamiento (`lanzamiento_key`), ubicación geográfica (`geografia_key`), formato de soporte (`formato_key`) e idioma (`idioma_key`), conteniendo exclusivamente claves foráneas conformadas y métricas numéricas 100% aditivas."*
* **Cero Datos Sintéticos:** El 100% de los datos provienen del volcado nativo oficial de MusicBrainz (`mbdump.tar.bz2`).
* **Cero Textos y Cero Booleanos en la Tabla de Hechos:** La tabla de hechos almacena únicamente llaves enteras hacia las dimensiones y métricas cuantitativas aditivas (`SUM`).

---

## 3. Modelo en Estrella Puro en Español (Capa Gold - Kimball)

### 3.1. Tabla de Hechos Histórica (`gold.fact_produccion_musical`)
Particionada físicamente por rangos temporales en `fecha_key` (1900 a 2030) para garantizar *Partition Pruning*:
* **Llaves Foráneas Conformadas (Grano Diario + Dimensional):**
  * `hecho_key` (`BIGSERIAL` / PK Surrogate junto con `fecha_key`).
  * `fecha_key` (`INTEGER` -> `gold.dim_fecha(fecha_key)`).
  * `artista_key` (`INTEGER` -> `gold.dim_artista(artista_key)`).
  * `lanzamiento_key` (`INTEGER` -> `gold.dim_lanzamiento(lanzamiento_key)`).
  * `geografia_key` (`INTEGER` -> `gold.dim_geografia(geografia_key)`).
  * `formato_key` (`INTEGER` -> `gold.dim_formato(formato_key)`).
  * `idioma_key` (`INTEGER` -> `gold.dim_idioma(idioma_key)`).
* **Métricas Numéricas 100% Aditivas (`SUM`):**
  * `lanzamientos_total` (`INTEGER`): Cantidad de lanzamientos/álbumes publicados en esa fecha y combinación dimensional.
  * `soportes_total` (`INTEGER`): Cantidad de discos/medios físicos o digitales (`medium`).
  * `pistas_total` (`INTEGER`): Cantidad total de pistas/canciones producidas.
  * `grabaciones_unicas_total` (`INTEGER`): Cantidad de grabaciones de audio (`recording`) únicas.
  * `duracion_total_ms` (`BIGINT`): Duración acumulada en milisegundos.
  * `duracion_total_segundos` (`NUMERIC(14,2)`): Duración acumulada en segundos.
  * `duracion_total_minutos` (`NUMERIC(14,2)`): Duración acumulada en minutos.
  * `pistas_con_isrc_total` (`INTEGER`): Cantidad de pistas que cuentan con código internacional ISRC.
  * `pistas_largas_total` (`INTEGER`): Cantidad de pistas con duración superior a 5 minutos (> 300 segundos).
  * `pistas_video_total` (`INTEGER`): Cantidad de pistas correspondientes a grabaciones de video musical.
  * `pistas_completas_total` (`INTEGER`): Cantidad de pistas con duración reportada mayor a cero.

### 3.2. Dimensiones Conformadas (en Español con Patrón Fila Cero `Key 0`)
1. **`gold.dim_fecha`**: Calendario continuo diario (1900–2030, 47.848 filas) con jerarquía `dia` → `mes` → `trimestre` → `anio` → `decada` → `siglo`.
2. **`gold.dim_artista`**: Artistas solistas, bandas, coros y orquestas (`artista_id`, `nombre_artista`, `tipo_artista`, `genero`, `nombre_pais`, `anio_inicio`).
3. **`gold.dim_lanzamiento`**: Perfil analítico del lanzamiento (`estado_lanzamiento` [Oficial, Promocional, Bootleg], `tipo_empaque` [Jewel Case, Digipak, Gatefold, Digital], `calidad_datos`).
4. **`gold.dim_formato`**: Medios y soportes (`nombre_formato`, `categoria_formato`: `Digital / Streaming`, `Físico / Vinilo`, `Físico / Óptico`, `Físico / Magnético`).
5. **`gold.dim_geografia`**: Países y áreas geográficas (`area_id`, `nombre_area`, `tipo_area`, `nombre_pais`).
6. **`gold.dim_idioma`**: Idiomas oficiales ISO 639-3 (`idioma_id`, `nombre_idioma`, `codigo_iso`).

---

## 4. Requerimientos Funcionales Analíticos (RF01 - RF08)

* **RF01 (Top N de Catálogo):** Ranking de artistas por `SUM(lanzamientos_total)`, `SUM(pistas_total)`, duración acumulada y cobertura ISRC por país y década.
* **RF02 (Métricas por Formato e Idioma):** Duración promedio (`SUM(duracion_total_segundos) / SUM(pistas_completas_total)`) y volumen de lanzamientos y pistas según formato (Vinilo vs CD vs Digital) e idioma.
* **RF03 (Drill-Down Geográfico y Temporal):**
  * Geográfico: País → Tipo de Área → Área.
  * Temporal: Siglo → Década → Año → Trimestre → Mes → Día.
* **RF04 (Digital vs Físico & Canciones Largas):** Comparativa de penetración digital frente a físico y proporción de canciones largas (`SUM(pistas_largas_total)`).
* **RF05 (Correlación Estadística con `corr()`):** Correlación matemática entre año de lanzamiento y duración promedio, demostrando el impacto del streaming en la duración de las canciones.
* **RF06 (Formalización ISRC):** Tasa de formalización (`SUM(pistas_con_isrc_total) / SUM(pistas_total)`) por país y tipo de artista.
* **RF07 (Densidad de Pistas por Lanzamiento y Soporte):** Relación `SUM(pistas_total) / SUM(lanzamientos_total)` y `SUM(pistas_total) / SUM(soportes_total)`.
* **RF08 (Nuevos Artistas y Catálogo Emergente):** Detección de artistas debutantes en la última década con mayor volumen de lanzamientos y cobertura ISRC.

---

## 5. Ejecución del Pipeline E2E

```powershell
# 1) Iniciar contenedor PostgreSQL 16 en puerto 5435
docker compose up -d

# 2) Inicializar esquemas (meta, silver, gold), tablas, particiones y vistas materializadas
python scripts/setup_database.py

# 3) Ingestar tablas de la capa Silver (extrae bajo demanda desde mbdump.tar.bz2 si falta alguna)
python etl/silver/ingest_silver.py
python etl/silver/ingest_tracks_sliced.py

# 4) Poblar las 6 dimensiones conformadas, la tabla de hechos histórica y refrescar vistas materializadas
python etl/gold/run_gold_pipeline.py

# 5) Auditar y certificar volumetría, almacenamiento e integridad referencial Kimball
python scripts/verify_dwh.py
```