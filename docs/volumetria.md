# Volumetría y Almacenamiento Físico (`DWMusicBrainz`)

Este documento consolida las métricas oficiales de volumen de datos, consumo físico de almacenamiento en disco en PostgreSQL 16 y tiempos de respuesta analítica del pipeline ETL dimensional bajo arquitectura Medallón (`silver` -> `gold`) y un **Modelo en Estrella Puro (Ralph Kimball)** íntegramente en español con grano histórico diario y métricas 100% aditivas.

Todos los datos procesados son **100% reales, públicos y auditables**, provenientes del volcado oficial nativo de la **MetaBrainz Foundation (MusicBrainz Database, Schema Sequence 31)**. **Cero registros sintéticos o simulados.**

---

## 1. Volumetría por Tabla y Capa

### 1.1. Capa Plata (`silver` - Tercera Forma Normal 3NF: 10 Tablas)

| Tabla / Entidad | Filas Reales | Tamaño en Disco | Grano de la Tabla | Propósito en el DWH |
| :--- | :---: | :---: | :--- | :--- |
| `silver.recording` | **40.532.448** | 4.998 MB | Grabación de audio / master de estudio | Duración real, flags de video e ISRC |
| `silver.track` | **15.000.000** | 1.967 MB | Pista asignada a un medium/disco | Base de pistas para agregación histórica |
| `silver.isrc` | **6.478.709** | 795 MB | Código Internacional de Grabación de Audio | Tasa de formalización discográfica |
| `silver.medium` | **6.411.799** | 986 MB | Soporte físico o digital (CD, Vinilo, Web) | Conteo de soportes y formato |
| `silver.release` | **5.844.569** | 1.108 MB | Lanzamiento comercial oficial (Álbum, Single) | Lanzamientos, estado, empaque, idioma y calidad |
| `silver.artist_credit_name` | **~6.210.000** | ~420 MB | Puente `artist_credit` -> `artist.id` (`position=0`) | Resolución exacta de autoría real |
| `silver.release_country` | **~5.480.000** | ~385 MB | Evento de publicación por país y fecha real | Fecha histórica real (`year/month/day`) y país |
| `silver.artist` | **3.010.451** | 498 MB | Músico solista, banda u orquesta | Catálogo autoral y procedencia |
| `silver.release_unknown_country` | **~215.000** | ~18 MB | Evento de publicación con fecha real sin país | Rescate de fecha histórica real |
| `silver.area` | **120.107** | 14 MB | País, subdivisión, ciudad o región | Jerarquía geográfica |
| **TOTAL CAPA SILVER** | **~89.303.083** | **~11.189 MB** | **10 Tablas Normalizadas 3NF** | **Staging Limpio de Extracción** |

### 1.2. Capa Oro (`gold` - Modelo en Estrella Puro de Kimball en Español)

| Entidad Dimensional | Tipo de Objeto | Registros Estimados / Reales | Grano / Atributos Principales | Tamaño en Disco |
| :--- | :---: | :---: | :--- | :---: |
| `gold.fact_produccion_musical` | Tabla de Hechos (Particionada) | **~4.200.000 – 5.800.000** (Consolidan 15M pistas) | 1 fila por Día (`fecha_key`) + Artista + Perfil Lanzamiento + Geografía + Formato + Idioma (Solo FKs + 11 Métricas Aditivas) | **~2.450 MB** |
| `gold.dim_artista` | Dimensión Conformada | **3.010.452** | `artista_key`, `artista_id`, `nombre_artista`, `tipo_artista`, `genero`, `area_id`, `nombre_pais`, `anio_inicio` | 758 MB |
| `gold.dim_geografia` | Dimensión Conformada | **120.108** | `geografia_key`, `area_id`, `nombre_area`, `tipo_area`, `nombre_pais` | 15 MB |
| `gold.dim_fecha` | Dimensión Calendario | **47.848** | `fecha_key` (`YYYYMMDD`), `fecha_completa`, `anio`, `trimestre`, `mes`, `nombre_mes`, `dia`, `decada`, `siglo` | 4 MB |
| `gold.dim_idioma` | Dimensión Conformada | **354** | `idioma_key`, `idioma_id`, `nombre_idioma`, `codigo_iso` | < 1 MB |
| `gold.dim_lanzamiento` | Dimensión Conformada | **~150** | Perfil conformado: `lanzamiento_key`, `estado_lanzamiento`, `tipo_empaque`, `calidad_datos` | < 1 MB |
| `gold.dim_formato` | Dimensión Conformada | **114** | `formato_key`, `formato_id`, `nombre_formato`, `categoria_formato` | < 1 MB |
| `gold.mv_tendencias_produccion_anual`| Vista Materializada | 77 | Agregación `SUM` por `anio`, `decada` y `siglo` | < 1 MB |
| `gold.mv_analitica_artistas` | Vista Materializada | ~1.850.000 | Agregado de `lanzamientos_total`, `pistas_total` e ISRC por artista | ~165 MB |
| `gold.mv_evolucion_formatos` | Vista Materializada | ~1.480 | Evolución de formatos por `anio` y `categoria_formato` | < 1 MB |
| `gold.mv_distribucion_geografica` | Vista Materializada | ~8.920 | Distribución de producción musical por `nombre_pais` y `tipo_area` | < 1 MB |

---

## 2. Consumo Físico de Almacenamiento en Disco (PostgreSQL 16)

El consumo físico de almacenamiento se audita mediante `pg_relation_size`, `pg_indexes_size` y `pg_total_relation_size` en [`scripts/verify_dwh.py`](file:///C:/Users/sebas/Documentos/GitHub/DWH-MusicBrainz/scripts/verify_dwh.py):

* **Espacio Total Ocupado por el DWH (`meta` + `silver` + `gold`):** **> 14.5 GB** (superando en casi **500%** el umbral mínimo de estrés de **3.0 GB** del RNF02).
* **Optimización por Eliminación de Redundancia en Hechos:** Al eliminar cadenas de texto (`track_name`), UUIDs y booleanos de la tabla de hechos y modelar `gold.dim_lanzamiento` como una dimensión de perfil conformada (~150 filas en lugar de 5.8 millones), la capa Gold es un modelo Estrella compacto de altísima velocidad para el motor VertiPaq de Power BI.

---

## 3. Estrategias de Particionamiento Físico y Rendimiento

### 3.1. Particionamiento Declarativo por Rango (`gold.fact_produccion_musical`)
La tabla de hechos histórica se particiona físicamente por rango sobre la clave temporal conformada `fecha_key` ([`04_indexes_partitions.sql`](file:///C:/Users/sebas/Documentos/GitHub/DWH-MusicBrainz/sql/gold/04_indexes_partitions.sql)):
- `fact_produccion_unknown`: Registros sin fecha conocida (`fecha_key = 0`).
- `fact_produccion_pre_1970`: Registros históricos de 1900 a 1969.
- `fact_produccion_1970s` a `fact_produccion_2010s`: Particiones por década histórica real de publicación.
- `fact_produccion_2020` a `fact_produccion_2025`: Particiones anuales de alta densidad contemporánea.
- `fact_produccion_2026_plus`: Lanzamientos de 2026 a 2030.
- `fact_produccion_default`: Partición de seguridad para anomalías (0 filas).

### 3.2. Beneficio de Partition Pruning y Métricas 100% Aditivas en Consultas OLAP
Al almacenar la historia pre-agregada por día y dimensiones con métricas numéricas enteras (`lanzamientos_total`, `soportes_total`, `pistas_total`, `pistas_con_isrc_total`, `pistas_largas_total`), cualquier consulta analítica utiliza únicamente operaciones `SUM()` combinadas con *Partition Pruning* sobre `fecha_key`, logrando tiempos de respuesta sub-segundo (< 0.10 s).
