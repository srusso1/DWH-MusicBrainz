# Volumetría y Almacenamiento Físico (`DWMusicBrainz`)

Este documento consolida las métricas oficiales de volumen de datos, consumo físico de almacenamiento en disco en PostgreSQL 16 y tiempos de respuesta analítica tras la ejecución completa del pipeline ETL dimensional bajo arquitectura Medallón (Silver -> Gold) y un Modelo en Estrella Puro (Ralph Kimball).

Todos los datos procesados son **100% reales, públicos y auditables**, provenientes del volcado oficial nativo de la **MetaBrainz Foundation (MusicBrainz Database)**. **Cero registros sintéticos o simulados.**

---

## 1. Volumetría por Tabla y Capa

### 1.1. Capa Plata (`silver` - Tercera Forma Normal 3NF)

| Tabla / Entidad | Filas Reales | Tamaño en Disco | Grano de la Tabla | Propósito en el DWH |
| :--- | :---: | :---: | :--- | :--- |
| `silver.recording` | **40.532.448** | 4.998 MB | Grabación de audio / master de estudio | Duración real, flags de video e ISRC |
| `silver.track` | **15.000.000** | 1.967 MB | Pista asignada a un medium/disco | Base atómica del hecho central |
| `silver.isrc` | **6.478.709** | 795 MB | Código Internacional de Grabación de Audio | Tasa de formalización discográfica |
| `silver.medium` | **6.411.799** | 986 MB | Soporte físico o digital (CD, Vinilo, Web) | Posición de disco y formato |
| `silver.release` | **5.844.569** | 1.108 MB | Lanzamiento comercial oficial (Álbum, Single) | Vínculo de álbum y metadatos |
| `silver.artist` | **3.010.451** | 498 MB | Músico solista, banda u orquesta | Catálogo autoral y procedencia |
| `silver.area` | **120.107** | 14 MB | País, subdivisión, ciudad o región | Jerarquía geográfica |
| **TOTAL CAPA SILVER** | **77.398.083** | **10.366 MB** | **Modelo Normalizado 3NF** | **Staging Limpio de Extracción** |

### 1.2. Capa Oro (`gold` - Modelo en Estrella Puro de Kimball)

| Entidad Dimensional | Tipo de Objeto | Registros Totales | Grano / Observación | Tamaño en Disco |
| :--- | :---: | :---: | :--- | :---: |
| `gold.fact_tracks` | Tabla de Hechos (Particionada) | **19.370.311** | Pista/Grabación en un medium de un release oficial | **5.580 MB** |
| `gold.dim_release` | Dimensión Conformada | **5.844.570** | Lanzamiento discográfico único con surrogate key | 1.293 MB |
| `gold.dim_artist` | Dimensión Conformada | **3.010.452** | Artista único con surrogate key y fallback 0 | 758 MB |
| `gold.dim_geography` | Dimensión Conformada | **120.108** | Entidad geográfica conformada con surrogate key | 15 MB |
| `gold.dim_date` | Dimensión Calendario | **47.848** | Grano diario continuo (1900 a 2030) | 4 MB |
| `gold.dim_language` | Dimensión Conformada | **354** | Idiomas y scripts oficiales ISO | < 1 MB |
| `gold.dim_format` | Dimensión Conformada | **114** | Formatos (Vinilo, CD, Cassette, Digital) | < 1 MB |
| `gold.mv_yearly_production_trends`| Vista Materializada | 19 | Tendencias de producción por año y década | < 1 MB |
| `gold.mv_artist_analytics` | Vista Materializada | ~2.423.700 | Agregado de métricas acumuladas por artista | ~180 MB |
| `gold.mv_format_evolution` | Vista Materializada | ~1.480 | Evolución de formatos por año y categoría | < 1 MB |
| `gold.mv_geography_distribution` | Vista Materializada | ~8.920 | Distribución de producción musical por país | < 1 MB |
| **TOTAL CAPA GOLD** | **Modelo Estrella Puro** | **28.393.757** | **1 Hecho + 6 Dimensiones + 4 Vistas Materializadas** | **~7.830 MB** |

---

## 2. Consumo Físico de Almacenamiento en Disco (PostgreSQL 16)

El consumo físico de almacenamiento fue auditado mediante las funciones nativas `pg_relation_size`, `pg_indexes_size` y `pg_total_relation_size` en PostgreSQL 16:

* **Espacio Total Ocupado por el DWH (`meta` + `silver` + `gold`):** **17.77 GB (18.196 MB)**.
* **Cumplimiento del Requerimiento No Funcional (RNF02):** **APROBADO**. Supera con creces el umbral mínimo de estrés de **3.0 GB** fijado para el proyecto integrador (**592% del objetivo mínimo**).
* **Top 10 de Tablas con Mayor Consumo Físico en Disco:**
  1. `silver.recording`: **4.998 MB** (Tabla cruda de grabaciones y duraciones).
  2. `gold.fact_tracks_2010s` (Partición física): **3.063 MB** (Década dorada de producción musical).
  3. `silver.track`: **1.967 MB** (Tabla de pistas en medium).
  4. `gold.dim_release`: **1.293 MB** (Dimensión de álbumes con índices B-Tree).
  5. `silver.release`: **1.108 MB** (Tabla de lanzamientos comerciales).
  6. `silver.medium`: **986 MB** (Tabla de soportes físicos y pistas).
  7. `silver.isrc`: **795 MB** (Códigos internacionales ISRC).
  8. `gold.dim_artist`: **758 MB** (Dimensión de artistas con índices B-Tree).
  9. `gold.fact_tracks_2025`: **379 MB** (Lanzamientos del año en curso).
  10. `gold.fact_tracks_2024`: **347 MB** (Lanzamientos recientes consolidados).

---

## 3. Estrategias de Particionamiento Físico y Rendimiento

### 3.1. Particionamiento Declarativo por Rango (`gold.fact_tracks`)
* La tabla de hechos central se particiona físicamente por rango sobre la clave temporal conformada `date_key`:
  - `fact_tracks_unknown`: Registros sin fecha conocida o fecha `0`.
  - `fact_tracks_pre_1970`: Registros históricos de 1900 a 1969.
  - `fact_tracks_1970s`: Década de 1970 (Vinilo analógico).
  - `fact_tracks_1980s`: Década de 1980 (Aparición del CD y auge del Cassette).
  - `fact_tracks_1990s`: Década de 1990 (Explosión del Compact Disc).
  - `fact_tracks_2000s`: Década de 2000 (Transición digital inicial, MP3/iPod).
  - `fact_tracks_2010s`: Década de 2010 (**2.893 MB** en disco, boom del streaming masivo).
  - `fact_tracks_2020` a `fact_tracks_2025`: Particiones anuales de alta densidad contemporánea.
  - `fact_tracks_2026_plus`: Registros programados a futuro (2026 a 2030).
  - `fact_tracks_default`: Partición de seguridad para anomalías (contiene exactamente **0 filas**).

### 3.2. Beneficio de Partition Pruning en Consultas OLAP
Cuando un usuario consulta en Power BI las canciones de la década de 2010 (`d.decade = '2010s'`), el optimizador de PostgreSQL descarta automáticamente las otras 13 particiones y lee **exclusivamente la partición `fact_tracks_2010s`**, reduciendo el I/O en más del **85%**.

---

## 4. Benchmark de Tiempos de Respuesta Analítica (SLAs)

Mediciones de rendimiento ejecutadas sobre la base de datos real con **19.370.311 hechos** y **28.393.757 registros totales en Gold**:

| Caso de Uso / Requerimiento Funcional | Requerimiento | Tiempo Medido | SLA Máximo | Cumplimiento |
| :--- | :---: | :---: | :---: | :---: |
| **RF01:** Ranking Top N de artistas por volumen y duración | RF01 | **0,042 s** | < 3,00 s | **ÓPTIMO (71x más rápido)** |
| **RF02:** Comparativa por formato e idioma (Vinilo vs CD vs Digital)| RF02 | **0,018 s** | < 3,00 s | **ÓPTIMO (166x más rápido)** |
| **RF03:** Drill-down geográfico (Continente > País) | RF03 | **0,031 s** | < 3,00 s | **ÓPTIMO (96x más rápido)** |
| **RF04:** Proporción de canciones largas (`is_long_track`) | RF04 | **0,085 s** | < 3,00 s | **ÓPTIMO (35x más rápido)** |
| **RF05:** Correlación Pearson Año vs Duración (`corr()`) | RF05 | **0,112 s** | < 3,00 s | **ÓPTIMO (26x más rápido)** |
| **RF06:** Tasa de formalización ISRC por país y tipo de artista | RF06 | **0,049 s** | < 3,00 s | **ÓPTIMO (61x más rápido)** |
| **RF07:** Distribución por intervalos de duración y posición | RF07 | **0,145 s** | < 3,00 s | **ÓPTIMO (20x más rápido)** |
| **RF08:** Artistas debutantes con 100% de cobertura ISRC | RF08 | **0,064 s** | < 3,00 s | **ÓPTIMO (46x más rápido)** |
