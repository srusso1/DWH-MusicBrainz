# Capa Oro: Modelo en Estrella Puro en Español (Ralph Kimball Star Schema)

La capa **Gold** del Data Warehouse **DWMusicBrainz** implementa un **Modelo en Estrella Puro (Pure Star Schema)** fundamentado en las directrices de Ralph Kimball (*The Data Warehouse Toolkit: The Definitive Guide to Dimensional Modeling*), utilizando nomenclatura de negocio íntegramente en español.

Este modelo sitúa una única tabla de hechos histórica diaria (`gold.fact_produccion_musical`) rodeada por **seis dimensiones conformadas** (`dim_fecha`, `dim_artista`, `dim_lanzamiento`, `dim_formato`, `dim_geografia`, `dim_idioma`), conectadas mediante relaciones unidireccionales 1:N basadas en claves subrogadas enteras (`Surrogate Keys`), garantizando total coherencia analítica y cero huérfanos en consultas OLAP y reportes de Power BI.

---

## 1. Justificación Arquitectónica: ¿Por qué una Tabla de Hechos Histórica con Grano Diario y Métricas Aditivas?

Siguiendo la teoría estricta de Ralph Kimball para el almacenamiento histórico dimensional:

1. **Declaración del Grano (Grain Statement):**
   > *"Un registro individual en la tabla de hechos (`gold.fact_produccion_musical`) representa la consolidación histórica diaria (`fecha_key`) de la producción musical para una combinación conformada de artista (`artista_key`), perfil de lanzamiento (`lanzamiento_key`), geografía (`geografia_key`), formato (`formato_key`) e idioma (`idioma_key`)."*
2. **Separación Estricta entre Dimensiones y Hechos (Cero Textos, Cero Booleanos en Hechos):**
   * En la tabla de hechos **no existen cadenas de texto ni flags booleanos**. Todo atributo descriptivo vive en las dimensiones conformadas, mientras que en la tabla de hechos residen únicamente las **6 Claves Foráneas (FKs)** y **11 Métricas Numéricas 100% Aditivas (`SUM`)**.
   * Antiguos indicadores individuales se expresan como conteos aditivos puros: `lanzamientos_total`, `soportes_total`, `pistas_total`, `pistas_con_isrc_total`, `pistas_largas_total`, `pistas_video_total` y `pistas_completas_total`.
3. **Resolución de `dim_lanzamiento` como Dimensión de Perfil Conformada:**
   * Al modelar `dim_lanzamiento` por el perfil analítico del lanzamiento (`estado_lanzamiento`, `tipo_empaque`, `calidad_datos`), evitamos una dimensión monstruosa de 5.8 millones de filas y permitimos que la métrica `lanzamientos_total` sume la cantidad real de álbumes publicados por día, artista, país y formato.

---

## 2. Diagrama del Modelo en Estrella Puro (Kimball Star Schema)

```
                              +-------------------------+
                              |     gold.dim_fecha      |
                              |  (Calendario Continuo)  |
                              +-------------------------+
                                           |
                                           | (fecha_key)
                                           v
+-------------------------+   +-------------------------+   +-------------------------+
|    gold.dim_artista     |-->|      gold.fact_         |<--|  gold.dim_lanzamiento   |
|  (Músicos y Orquestas)  |   |   produccion_musical    |   | (Estado, Empaque, Cal.) |
+-------------------------+   | (Hechos Diarios + SUM)  |   +-------------------------+
                              +-------------------------+
                                           ^
                                           |
              +----------------------------+----------------------------+
              | (formato_key)              | (geografia_key)            | (idioma_key)
              |                            |                            |
+-------------------------+   +-------------------------+   +-------------------------+
|    gold.dim_formato     |   |   gold.dim_geografia    |   |     gold.dim_idioma     |
|  (Vinilo, CD, Digital)  |   |   (Países y Regiones)   |   |  (Idiomas ISO 639-3)    |
+-------------------------+   +-------------------------+   +-------------------------+
```

---

## 3. Matriz de Bus de Arquitectura (Kimball Bus Matrix)

| Proceso de Negocio / Tabla de Hechos | `dim_fecha` | `dim_artista` | `dim_lanzamiento` | `dim_formato` | `dim_geografia` | `dim_idioma` |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Producción Musical Diaria (`fact_produccion_musical`)** | **X** | **X** | **X** | **X** | **X** | **X** |
| *Métricas Aditivas (`SUM`):* | `anio`, `decada` | `tipo_artista` | `estado_lanzamiento` | `categoria_formato` | `nombre_pais` | `nombre_idioma` |
| - `lanzamientos_total` (Aditiva) | **X** | **X** | **X** | **X** | **X** | **X** |
| - `soportes_total` (Aditiva) | **X** | **X** | **X** | **X** | **X** | **X** |
| - `pistas_total` (Aditiva) | **X** | **X** | **X** | **X** | **X** | **X** |
| - `duracion_total_segundos` (Aditiva) | **X** | **X** | **X** | **X** | **X** | **X** |
| - `pistas_con_isrc_total` (Aditiva) | **X** | **X** | **X** | **X** | **X** | **X** |
| - `pistas_largas_total` (Aditiva) | **X** | **X** | **X** | **X** | **X** | **X** |

---

## 4. Detalle de Dimensiones Conformadas (Patrón Fila Cero `Key 0`)

Todas las dimensiones implementan el patrón de **Fila Cero (`Key 0`)** para garantizar el principio de **Cero Huérfanos**:

1. **`gold.dim_fecha`**: `fecha_key (PK - YYYYMMDD)`, `fecha_completa`, `anio`, `trimestre`, `nombre_trimestre`, `mes`, `nombre_mes`, `nombre_mes_corto`, `dia`, `dia_semana`, `nombre_dia`, `es_fin_de_semana`, `decada`, `siglo`.
2. **`gold.dim_artista`**: `artista_key (PK)`, `artista_id (BK)`, `artista_gid`, `nombre_artista`, `nombre_orden`, `tipo_artista`, `genero`, `area_id`, `nombre_area`, `nombre_pais`, `anio_inicio`, `anio_fin`, `finalizado`.
3. **`gold.dim_lanzamiento`**: `lanzamiento_key (PK)`, `estado_id`, `empaque_id`, `calidad_id`, `estado_lanzamiento`, `tipo_empaque`, `calidad_datos`.
4. **`gold.dim_formato`**: `formato_key (PK)`, `formato_id (BK)`, `nombre_formato`, `categoria_formato`.
5. **`gold.dim_geografia`**: `geografia_key (PK)`, `area_id (BK)`, `area_gid`, `nombre_area`, `tipo_area`, `nombre_pais`.
6. **`gold.dim_idioma`**: `idioma_key (PK)`, `idioma_id (BK)`, `nombre_idioma`, `codigo_iso`.

---

## 5. Vistas Materializadas Analíticas para Power BI

La capa Gold incluye 4 vistas materializadas indexadas que pre-calculan agregaciones `SUM` sobre `gold.fact_produccion_musical`:

1. **`gold.mv_tendencias_produccion_anual` (RF01 & RF05):** Evolución por año, década y siglo de `lanzamientos_total`, `soportes_total`, `pistas_total`, `artistas_activos`, `duracion_promedio_segundos` y `cobertura_isrc_pct`.
2. **`gold.mv_analitica_artistas` (RF01, RF06 & RF08):** Catálogo consolidado por artista, tipo y país con `lanzamientos_total`, `pistas_total`, `pistas_con_isrc_total` y `pistas_largas_total`.
3. **`gold.mv_evolucion_formatos` (RF02 & RF04):** Matriz temporal por formato y categoría (`Digital / Streaming`, `Físico / Vinilo`, `Físico / Óptico`, `Físico / Magnético`).
4. **`gold.mv_distribucion_geografica` (RF03 & RF06):** Agregación por país y tipo de área con `lanzamientos_total`, `pistas_total` y `duracion_total_horas`.
