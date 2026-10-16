# Guía de Modelado DAX y Métricas para Power BI (`DWMusicBrainz`)

## 1. Conexión a PostgreSQL en Power BI Desktop
* **Servidor:** `localhost:5435`
* **Base de Datos:** `dw_musicbrainz`
* **Modo de Conexión:** **Import** o **DirectQuery**
* **Tablas a Importar (Capa Gold en Español):**
  * `gold.fact_produccion_musical` (Tabla de hechos histórica diaria con métricas aditivas)
  * `gold.dim_fecha`
  * `gold.dim_artista`
  * `gold.dim_lanzamiento`
  * `gold.dim_formato`
  * `gold.dim_geografia`
  * `gold.dim_idioma`

---

## 2. Relaciones del Modelo en Estrella (Kimball Star Schema)
| Tabla Dimensión (1) | Campo PK | Tabla de Hechos (*) | Campo FK | Cardinalidad | Filtro Cruzado |
|---|---|---|---|---|---|
| `gold.dim_fecha` | `fecha_key` | `gold.fact_produccion_musical` | `fecha_key` | 1 a Varios (`1:*`) | Único (Single) |
| `gold.dim_artista` | `artista_key` | `gold.fact_produccion_musical` | `artista_key` | 1 a Varios (`1:*`) | Único (Single) |
| `gold.dim_lanzamiento` | `lanzamiento_key` | `gold.fact_produccion_musical` | `lanzamiento_key` | 1 a Varios (`1:*`) | Único (Single) |
| `gold.dim_formato` | `formato_key` | `gold.fact_produccion_musical` | `formato_key` | 1 a Varios (`1:*`) | Único (Single) |
| `gold.dim_geografia` | `geografia_key` | `gold.fact_produccion_musical` | `geografia_key` | 1 a Varios (`1:*`) | Único (Single) |
| `gold.dim_idioma` | `idioma_key` | `gold.fact_produccion_musical` | `idioma_key` | 1 a Varios (`1:*`) | Único (Single) |

---

## 3. Diccionario de Medidas DAX (100% Basadas en `SUM` Aditivo)

### 3.1. Volumetría de Producción Musical
```dax
Total Lanzamientos = SUM(gold_fact_produccion_musical[lanzamientos_total])
```

```dax
Total Soportes = SUM(gold_fact_produccion_musical[soportes_total])
```

```dax
Total Pistas = SUM(gold_fact_produccion_musical[pistas_total])
```

```dax
Artistas Activos = DISTINCTCOUNT(gold_fact_produccion_musical[artista_key])
```

### 3.2. Métricas de Tiempo y Duración Ponderada
```dax
Duracion Total (Horas) = 
DIVIDE(
    SUM(gold_fact_produccion_musical[duracion_total_minutos]), 
    60, 
    0
)
```

```dax
Duracion Promedio por Pista (Segundos) = 
DIVIDE(
    SUM(gold_fact_produccion_musical[duracion_total_segundos]),
    SUM(gold_fact_produccion_musical[pistas_completas_total]),
    0
)
```

```dax
Duracion Promedio por Pista (Minutos) = 
DIVIDE(
    [Duracion Promedio por Pista (Segundos)],
    60,
    0
)
```

### 3.3. Estándares Internacionales (ISRC) y Canciones Largas
```dax
Total Pistas con ISRC = SUM(gold_fact_produccion_musical[pistas_con_isrc_total])
```

```dax
Tasa Cobertura ISRC % = 
DIVIDE(
    [Total Pistas con ISRC],
    [Total Pistas],
    0
)
```

```dax
Total Pistas Largas (>5 min) = SUM(gold_fact_produccion_musical[pistas_largas_total])
```

```dax
Proporcion Pistas Largas % = 
DIVIDE(
    [Total Pistas Largas (>5 min)],
    [Total Pistas],
    0
)
```

### 3.4. Análisis de Formatos (Evolución Temporal RF02 & RF04)
```dax
Lanzamientos Digitales = 
CALCULATE(
    [Total Lanzamientos],
    gold_dim_formato[categoria_formato] = "Digital / Streaming"
)
```

```dax
Lanzamientos Vinilo = 
CALCULATE(
    [Total Lanzamientos],
    gold_dim_formato[categoria_formato] = "Físico / Vinilo"
)
```

```dax
Lanzamientos CD Optico = 
CALCULATE(
    [Total Lanzamientos],
    gold_dim_formato[categoria_formato] = "Físico / Óptico"
)
```

```dax
Participacion Digital % = 
DIVIDE([Lanzamientos Digitales], [Total Lanzamientos], 0)
```