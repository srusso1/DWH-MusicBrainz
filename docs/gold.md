# Capa Oro: Modelo en Estrella Puro (Ralph Kimball Star Schema)

La capa **Gold** del Data Warehouse **DWMusicBrainz** implementa un **Modelo en Estrella Puro (Pure Star Schema)** fundamentado en las directrices de Ralph Kimball (*The Data Warehouse Toolkit: The Definitive Guide to Dimensional Modeling*).

Este modelo sitúa una única tabla de hechos central masiva (`gold.fact_tracks`) rodeada por **seis dimensiones conformadas**, conectadas mediante relaciones unidireccionales 1:N basadas en claves subrogadas enteras (`Surrogate Keys`), garantizando total coherencia analítica y cero huérfanos en consultas OLAP y reportes de Power BI.

---

## 1. Justificación Arquitectónica: ¿Por qué Modelo en Estrella Puro?

A diferencia de modelos transaccionales de constelación (donde múltiples hechos coexisten para procesos dispares), en la industria musical moderna el proceso nuclear de negocio es la **Publicación y Consumo de Pistas Musicales (Track Release Process)**.

1. **Declaración del Grano Atómico:**
   > *"Un registro individual en la tabla de hechos representa la inclusión de una pista o grabación de audio (track/recording) dentro de un soporte físico o digital (medium) correspondiente a un lanzamiento discográfico comercial oficial (release), ejecutado por un artista o agrupación en una fecha determinada."*
2. **Preservación Estricta de la Aditividad:**
   * Al situar el grano en el nivel de pista individual (`track`), todas las métricas de negocio son aditivas en todas las dimensiones:
     - `SUM(track_count)`: Volumen exacto de canciones producidas.
     - `SUM(duration_seconds)` / `SUM(duration_minutes)`: Duración acumulada de catálogo sin duplicidades ni trampas de abanico (*fan traps*).
     - `COUNT(CASE WHEN has_isrc THEN 1 END)`: Cobertura de formalización fonográfica.
3. **Simplicidad y Eficiencia en Power BI:**
   * Una sola tabla de hechos rodeada de dimensiones conformadas elimina relaciones de muchos a muchos (*many-to-many*) y filtros bidireccionales en el motor tabular de Power BI (DAX / VertiPaq), maximizando la compresión en memoria y la velocidad de renderizado.

---

## 2. Diagrama del Modelo en Estrella Puro (Kimball Star Schema)

```
                            +-----------------------+
                            |     gold.dim_date     |
                            | (Calendario Continuo) |
                            +-----------------------+
                                        |
                                        | (date_key)
                                        v
+-----------------------+   +-----------------------+   +-----------------------+
|    gold.dim_artist    |-->|   gold.fact_tracks    |<--|   gold.dim_release    |
| (Músicos y Orquestas) |   | (19.3M Hechos Reales) |   | (Álbumes y Singles)   |
+-----------------------+   +-----------------------+   +-----------------------+
                                        ^
                                        |
            +---------------------------+---------------------------+
            | (format_key)              | (geo_key)                 | (language_key)
            |                           |                           |
+-----------------------+   +-----------------------+   +-----------------------+
|   gold.dim_format     |   |  gold.dim_geography   |   |   gold.dim_language   |
| (Vinilo, CD, Digital) |   | (Países y Regiones)   |   | (Idiomas y Alfabetos) |
+-----------------------+   +-----------------------+   +-----------------------+
```

---

## 3. Matriz de Bus de Arquitectura (Kimball Bus Matrix)

La matriz de bus formaliza cómo las dimensiones conformadas cruzan el proceso de negocio central de publicación de pistas:

| Proceso de Negocio / Tabla de Hechos | `dim_date` | `dim_artist` | `dim_release` | `dim_format` | `dim_geography` | `dim_language` |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Publicación de Pistas (`fact_tracks`)** | **X** | **X** | **X** | **X** | **X** | **X** |
| *Métricas Numéricas Clave:* | Año, Década | Tipo Artista | Tipo Release | Categoría | País, Continente | Idioma, Script |
| - `duration_seconds` (Aditiva) | **X** | **X** | **X** | **X** | **X** | **X** |
| - `track_count` (Aditiva) | **X** | **X** | **X** | **X** | **X** | **X** |
| - `has_isrc` (Booleana / Tasa) | **X** | **X** | **X** | **X** | **X** | **X** |
| - `is_long_track` (Booleana) | **X** | **X** | **X** | **X** | **X** | **X** |

---

## 4. Detalle de Dimensiones Conformadas

Todas las dimensiones implementan el patrón de **Fila Cero (`Key 0`)** para garantizar el cumplimiento del principio de **Cero Huérfanos**: si una pista carece de país, formato o idioma en el origen, su clave foránea se enlaza a la clave `0` (*"Sin Información"*), preservando la integridad referencial sin descartar transacciones.

### 4.1. `gold.dim_date` (Dimensión Calendario)
* **Grano:** Diario continuo desde el 1 de enero de 1900 hasta el 31 de diciembre de 2030 (47.848 filas).
* **Atributos:** `date_key (PK - YYYYMMDD)`, `full_date`, `year`, `quarter`, `month`, `month_name`, `week`, `day_of_month`, `day_of_week`, `decade ('1970s', '1980s'...)`, `century`, `is_weekend`.

### 4.2. `gold.dim_artist` (Dimensión Artistas)
* **Filas:** 3.010.452 registros únicos.
* **Atributos:** `artist_key (PK Sustituta)`, `artist_id (Clave Natural)`, `artist_gid (MBID)`, `artist_name`, `artist_type ('Person', 'Group', 'Orchestra')`, `gender`, `country_name`, `begin_year`.

### 4.3. `gold.dim_release` (Dimensión Álbumes y Lanzamientos)
* **Filas:** 5.844.570 registros únicos.
* **Atributos:** `release_key (PK Sustituta)`, `release_id (Clave Natural)`, `release_gid (MBID)`, `release_name`, `release_status ('Official', 'Promotion')`, `packaging_type`, `barcode`, `quality`.

### 4.4. `gold.dim_format` (Dimensión Formatos de Soporte)
* **Filas:** 114 formatos catalogados.
* **Atributos:** `format_key (PK Sustituta)`, `format_id (Clave Natural)`, `format_name ('Vinyl', 'CD', 'Cassette', 'Digital Media')`, `category ('Physical Analog', 'Optical Digital', 'Streaming/Digital')`.

### 4.5. `gold.dim_geography` (Dimensión Geográfica)
* **Filas:** 120.108 ubicaciones territoriales.
* **Atributos:** `geo_key (PK Sustituta)`, `area_id (Clave Natural)`, `area_gid (MBID)`, `area_name`, `area_type ('Country', 'City', 'Subdivision')`, `country_name`.

### 4.6. `gold.dim_language` (Dimensión Idiomas y Scripts)
* **Filas:** 354 registros oficiales.
* **Atributos:** `language_key (PK Sustituta)`, `language_id (Clave Natural)`, `language_name`, `iso_code`.

---

## 5. Tabla de Hechos Central (`gold.fact_tracks`)

* **Volumetría Consolidada:** **19.370.311 registros de hechos reales**.
* **Estructura Columnar:**
  - **Claves Foráneas Conformadas:** `date_key`, `artist_key`, `release_key`, `geo_key`, `format_key`, `language_key`.
  - **Dimensiones Degeneradas:** `track_id`, `track_gid`, `recording_id`, `recording_gid`, `track_number`, `position`, `isrc_code`.
  - **Métricas Numéricas Aditivas:**
    - `duration_ms`: Duración nativa en milisegundos.
    - `duration_seconds`: Duración en segundos calculada (`duration_ms / 1000.0`).
    - `duration_minutes`: Duración en minutos calculada (`duration_ms / 60000.0`).
    - `track_count`: Constante 1 para agregaciones directas de alta velocidad.
  - **Métricas Semiaditivas y Flags de Calidad:**
    - `has_isrc`: Booleano `TRUE` si posee código sonoro internacional.
    - `is_long_track`: Booleano `TRUE` si `duration_seconds > 300` (>5 minutos).
    - `is_complete`: Booleano `TRUE` si la pista reporta duración válida mayor a cero.

---

## 6. Vistas Materializadas Analíticas para Power BI

Para acelerar las respuestas de Power BI y evitar el escaneo completo de 19 millones de filas en tableros ejecutivos, la capa Gold incluye 4 vistas materializadas con índices únicos:

1. **`gold.mv_yearly_production_trends` (RF01 & RF05):**
   * Agregación temporal por año, década y siglo. Calcula volumen total de pistas, artistas activos, duración acumulada, duración promedio y porcentaje de penetración del código ISRC.
2. **`gold.mv_artist_analytics` (RF01, RF06 & RF08):**
   * Catálogo analítico por artista, tipo de ensamble y país. Permite identificar de inmediato los rankings Top N y artistas debutantes de la última década con 100% de cobertura ISRC.
3. **`gold.mv_format_evolution` (RF02 & RF04):**
   * Matriz cruzada de formatos (Vinilo vs CD vs Digital) por año, demostrando la transición tecnológica y el auge del streaming frente a los soportes analógicos.
4. **`gold.mv_geography_distribution` (RF03 & RF06):**
   * Agregación por país y continente para soportar visualizaciones de mapas y navegación jerárquica Drill-Down (*Continente > País*).
