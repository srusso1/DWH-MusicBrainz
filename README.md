# Data Warehouse MusicBrainz (DWMusicBrainz)

Data Warehouse analítico de alta volumetría en **PostgreSQL 16** con **Arquitectura Medallón (Silver -> Gold)** y **Modelo en Estrella Puro (Ralph Kimball)**, alimentado exclusivamente con datos 100% reales de la fundación **MetaBrainz (MusicBrainz)**.

Consolida y procesa más de **12 a 16 millones de registros reales** para analítica multidimensional de la industria discográfica y tableros en Power BI.

---

## 1. Arquitectura General del Sistema

El flujo de datos sigue el patrón Medallón optimizado para alta volumetría con auditoría contable transversal:

```
mbdump.tar.bz2 (data/downloads)
           │
           ├── Extracción quirúrgica de TSVs (artist, release, medium, track, recording, area, isrc)
           ▼
        silver (Tablas 3NF normalizadas, tipos nativos PostgreSQL, PKs y FKs)
           │
           ├── Transformación set-based, resolución de claves sustitutas y métricas
           ▼
         gold (Modelo en Estrella Puro: 6 dimensiones conformadas + fact_tracks)
           │
           └── Consumo analítico (Power BI / Consultas OLAP de alto rendimiento)

Esquema meta: meta.etl_audit (auditoría de tiempos, filas leídas, insertadas y linaje)
```

---

## 2. Declaración de Negocio y Grano Atómico

* **Declaración del Grano Atómico:**
  > "Un registro individual en la tabla de hechos representa la inclusión de una pista o grabación física/digital (`track`/`recording`) dentro de un soporte (`medium`) correspondiente a un lanzamiento discográfico comercial oficial (`release`), ejecutado por un artista o agrupación en una fecha determinada."
* **Volumetría Objetivo:** Entre **12 y 16 millones de registros reales** en la tabla de hechos central.
* **Cero Datos Sintéticos:** El 100% de los datos provienen del volcado nativo oficial de MusicBrainz (`mbdump.tar.bz2`).
* **Huella Física en Disco:** > 3.0 GB en PostgreSQL (cumplimiento RNF de prueba de estrés).

---

## 3. Modelo en Estrella Puro (Capa Gold - Kimball)

### 3.1. Tabla de Hechos Central (`gold.fact_tracks`)
Particionada físicamente por rangos temporales en `date_key` (1950 a 2027) para garantizar *Partition Pruning*:
* **Llaves Foráneas y Degeneradas:**
  * `track_id` (BIGINT / PK Degenerada).
  * `date_key` (INT REFERENCES `gold.dim_date(date_key)`).
  * `artist_key` (INT REFERENCES `gold.dim_artist(artist_key)`).
  * `release_key` (INT REFERENCES `gold.dim_release(release_key)`).
  * `format_key` (INT REFERENCES `gold.dim_format(format_key)`).
  * `geography_key` (INT REFERENCES `gold.dim_geography(geography_key)`).
  * `language_key` (INT REFERENCES `gold.dim_language(language_key)`).
* **Métricas Aditivas y Semi-Aditivas:**
  * `duration_ms` (INT): Duración original en milisegundos.
  * `duration_seconds` (NUMERIC(10,2)): Duración en segundos (`duration_ms / 1000.0`).
  * `track_position` (SMALLINT): Número de pista en el soporte físico/digital.
  * `disc_number` (SMALLINT): Número de disco en ediciones multidisco.
  * `is_long_track` (BOOLEAN): Flag (`duration_seconds > 300`, canciones > 5 min).
  * `has_isrc` (BOOLEAN): Flag de registro sonoro internacional ISRC.
  * `track_count` (SMALLINT DEFAULT 1): Constante unitaria para sumatorias de alta velocidad.

### 3.2. Dimensiones Conformadas
1. **`gold.dim_date`**: Calendario continuo (1950–2027) con jerarquía Día → Mes → Trimestre → Año → Década.
2. **`gold.dim_artist`**: Artistas y agrupaciones (`artist_mbid`, `name`, `type`, `begin_year`, `gender`).
3. **`gold.dim_release`**: Álbumes y lanzamientos discográficos (`release_mbid`, `title`, `release_type`, `status`).
4. **`gold.dim_format`**: Medios y soportes (`format_name`, categoría Analógico Físico, Óptico Digital, Streaming).
5. **`gold.dim_geography`**: Países y continentes (`country_code`, `country_name`, `continent`).
6. **`gold.dim_language`**: Idiomas y alfabetos (`language_code`, `language_name`, `script`).

---

## 4. Requerimientos Funcionales Analíticos (RF01 - RF08)

* **RF01 (Top N de Catálogo):** Ranking de artistas y álbumes con mayor volumen de canciones, duración acumulada y porcentaje con ISRC por país y década.
* **RF02 (Métricas por Formato e Idioma):** Duración promedio y cantidad de pistas por álbum según el formato (Vinilo vs CD vs Digital) e idioma.
* **RF03 (Drill-Down Geográfico y Temporal):**
  * Geográfico: Continente → País.
  * Temporal: Década → Año → Mes → Fecha.
* **RF04 (Digital vs Físico & Canciones Largas):** Comparativa de penetración digital frente a físico y proporción de canciones largas (`is_long_track = TRUE`).
* **RF05 (Correlación Estadística con `corr()`):** Correlación matemática entre año de lanzamiento y duración promedio, demostrando el impacto del streaming en la duración de las canciones.
* **RF06 (Formalización ISRC):** Tasa de canciones con código ISRC por cada 100 lanzamientos por país y tipo de artista.
* **RF07 (Distribución por Tramos de Duración):** Distribución de canciones (<2 min, 2-4 min, 4-6 min, >6 min) y su posición en el álbum (`track_position`).
* **RF08 (Nuevos Artistas y Catálogo Emergente):** Detección de artistas debutantes en la última década con mayor catálogo y 100% cobertura ISRC.

---

## 5. Estructura del Repositorio

```
DWMusicBrainz/
├── data/
│   ├── raw/              # TSVs crudos extraídos de mbdump
│   └── downloads/        # Volcados comprimidos (mbdump.tar.bz2)
├── docs/                 # Documentación técnica exhaustiva (Kimball, EDA, Volumetría)
├── sql/
│   ├── meta/             # 01_schema_meta.sql (auditoría y linaje)
│   ├── silver/           # 02_create_silver_tables.sql (tablas 3NF)
│   ├── gold/             # 03_dimensions_facts.sql (Estrella pura)
│   │                     # 04_indexes_partitions.sql (Particionado físico)
│   │                     # 05_aggregations.sql (Vistas para Power BI)
│   └── validations/      # Consultas SQL de verificación de integridad y SLAs
├── etl/
│   ├── common/           # Conexión DB, configuración y logger de auditoría
│   ├── silver/           # Ingesta masiva TSV con COPY nativo
│   ├── gold/             # Poblado dimensional y cálculo de hechos
│   └── run_pipeline.py   # Orquestador del pipeline CLI
├── scripts/
│   ├── setup_database.py # Inicialización DDL de esquemas y tablas
│   └── validate.py       # Validación de volumetría, integridad y benchmarks
├── tests/                # Suite de pruebas automatizadas con pytest
├── docker-compose.yml    # Contenedor PostgreSQL 16 aislado (puerto 5435)
├── requirements.txt      # Dependencias de Python
└── README.md             # Documentación principal
```

---

## 6. Requisitos y Puesta en Marcha

### Requisitos del Sistema
- **Python:** 3.10+
- **Docker Desktop:** Contenedor PostgreSQL 16 en puerto 5435.

### Despliegue Rápido
```powershell
# 1) Iniciar base de datos aislada en Docker
docker compose up -d

# 2) Configurar entorno virtual e instalar dependencias
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# 3) Inicializar base de datos y esquemas
python scripts/setup_database.py
```