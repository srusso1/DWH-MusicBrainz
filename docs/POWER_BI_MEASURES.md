# Guía de Modelado DAX y Métricas para Power BI (DWMusicBrainz)

## 1. Conexión a PostgreSQL en Power BI Desktop
* **Servidor:** `localhost:5435`
* **Base de Datos:** `dw_musicbrainz`
* **Modo de Conexión:** **Import** (o **DirectQuery** aprovechando el particionamiento de PostgreSQL 16)
* **Tablas a Importar (Capa Gold):**
  * `gold.fact_tracks`
  * `gold.dim_date`
  * `gold.dim_artist`
  * `gold.dim_release`
  * `gold.dim_format`
  * `gold.dim_geography`
  * `gold.dim_language`

---

## 2. Relaciones del Modelo en Estrella (Kimball Star Schema)
| Tabla Origen (1) | Campo Origen | Tabla Destino (*) | Campo Destino | Cardinalidad | Filtro Cruzado |
|---|---|---|---|---|---|
| `gold.dim_date` | `date_key` | `gold.fact_tracks` | `date_key` | 1 a Varios (1:*) | Único (Single) |
| `gold.dim_artist` | `artist_key` | `gold.fact_tracks` | `artist_key` | 1 a Varios (1:*) | Único (Single) |
| `gold.dim_release` | `release_key` | `gold.fact_tracks` | `release_key` | 1 a Varios (1:*) | Único (Single) |
| `gold.dim_format` | `format_key` | `gold.fact_tracks` | `format_key` | 1 a Varios (1:*) | Único (Single) |
| `gold.dim_geography` | `geo_key` | `gold.fact_tracks` | `geo_key` | 1 a Varios (1:*) | Único (Single) |
| `gold.dim_language` | `language_key` | `gold.fact_tracks` | `language_key` | 1 a Varios (1:*) | Único (Single) |

---

## 3. Diccionario de Medidas DAX Fundamentales

### 3.1. Volumetría Básica
```dax
Total Tracks = SUM(gold_fact_tracks[track_count])
```

```dax
Total Releases = DISTINCTCOUNT(gold_fact_tracks[release_key])
```

```dax
Active Artists = DISTINCTCOUNT(gold_fact_tracks[artist_key])
```

### 3.2. Métricas de Tiempo y Duración
```dax
Total Duration (Hours) = 
DIVIDE(
    SUM(gold_fact_tracks[duration_minutes]), 
    60, 
    0
)
```

```dax
Average Duration (Minutes) = 
AVERAGE(gold_fact_tracks[duration_minutes])
```

```dax
Average Duration (Seconds) = 
AVERAGE(gold_fact_tracks[duration_seconds])
```

### 3.3. Estándares Internacionales y Calidad (ISRC)
```dax
Tracks with ISRC = 
CALCULATE(
    [Total Tracks],
    gold_fact_tracks[has_isrc] = TRUE()
)
```

```dax
ISRC Coverage Rate = 
DIVIDE(
    [Tracks with ISRC],
    [Total Tracks],
    0
)
```

### 3.4. Análisis de Formatos (Evolución Temporal RF03)
```dax
Digital Tracks = 
CALCULATE(
    [Total Tracks],
    gold_dim_format[category] = "Digital / Streaming"
)
```

```dax
Vinyl Tracks = 
CALCULATE(
    [Total Tracks],
    gold_dim_format[category] = "Físico / Vinilo"
)
```

```dax
CD Tracks = 
CALCULATE(
    [Total Tracks],
    gold_dim_format[category] = "Físico / Óptico"
)
```

```dax
Cassette Tracks = 
CALCULATE(
    [Total Tracks],
    gold_dim_format[category] = "Físico / Magnético"
)
```

```dax
Digital Share % = 
DIVIDE([Digital Tracks], [Total Tracks], 0)
```

---

## 4. Estructura de Reportes Analíticos (RF01 a RF08)
1. **RF01 (Tendencias Temporales):** Gráfico de líneas con `Total Tracks` y `Total Duration (Hours)` por `gold_dim_date[year]` y `gold_dim_date[decade]`.
2. **RF02 (Artistas Top):** Tabla y gráfico de barras de `[Total Tracks]` por `gold_dim_artist[artist_name]` y `gold_dim_artist[country_name]`.
3. **RF03 (Evolución de Formatos):** Gráfico de áreas apiladas con `[Digital Share %]`, Vinilos, CDs y Cassettes de 1950 a 2026.
4. **RF04 (Distribución Geográfica):** Mapa coroplético por `gold_dim_geography[country_name]` con `[Total Tracks]`.
5. **RF05 (Adopción ISRC):** Indicador tipo Gauge con `[ISRC Coverage Rate]` y evolución por década.