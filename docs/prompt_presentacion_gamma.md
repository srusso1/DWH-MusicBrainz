# Prompt para Generación de Presentación en Gamma App

Este archivo contiene el prompt estructurado para generar las **13 diapositivas oficiales de sustentación** del Data Warehouse MusicBrainz (`DWMusicBrainz`) en herramientas de IA como **Gamma App**, alineado al 100% con el **Modelo en Estrella Puro en Español (Ralph Kimball)** y la tabla de hechos histórica diaria con métricas aditivas (`gold.fact_produccion_musical`).

---

```markdown
Crea una presentación profesional, ejecutiva y de altísimo nivel técnico de 13 diapositivas (formato panorámico 16:9) para la sustentación universitaria de nuestro proyecto integrador de Bases de Datos Avanzadas: "Data Warehouse Masivo de la Industria Musical (DWMusicBrainz)".

---

### INSTRUCCIONES DE ESTILO VISUAL Y DISEÑO (MANDATORIO)
- **Temática visual:** Fusión entre Ingeniería de Datos de alto rendimiento (Data Warehousing corporativo), Arquitectura de Software limpia y la Industria Musical Global (Streaming, sellos discográficos, formalización ISRC).
- **Paleta de colores:**
  - Color primario: Azul marino oscuro institucional (#0B192C / #1E3A8A).
  - Color secundario / acento tecnológico: Violeta eléctrico y Cian (#8B5CF6 / #06B6D4).
  - Acentos de alerta y métricas: Ámbar musical / Dorado de vinilo (#F59E0B).
  - Fondo: Modo oscuro elegante (Dark Mode profesional) con tarjetas de contraste en gris pizarra (#1E293B / #0F172A).

---

### ESTRUCTURA DIAPOSITIVA POR DIAPOSITIVA (13 SLIDES)

#### DIAPOSITIVA 1: Portada Institucional
- **Título principal:** Data Warehouse Masivo de la Industria Musical (DWMusicBrainz)
- **Subtítulo:** Arquitectura Medallón en PostgreSQL 16 & Modelo en Estrella Puro en Español (Ralph Kimball)
- **Badges destacados:**
  - 🐘 PostgreSQL 16 + Docker (Puerto 5435)
  - ⚡ 100% Datos Reales MusicBrainz (Schema Sequence 31 - 0% Sintéticos)
  - 📈 ~89 Millones de Filas en Silver -> Hechos Históricos Diarios Aditivos en Gold
  - 💾 > 14,5 GB de Almacenamiento Físico en Disco
  - 📊 Explotación Analítica en Power BI con Métricas 100% Aditivas (`SUM`)
- **Pie institucional:** Proyecto Integrador | Bases de Datos Avanzadas | 5to Semestre | Ingeniería de Sistemas | Universidad Popular del Cesar | Valledupar, 2026.

---

#### DIAPOSITIVA 2: Planteamiento del Problema: De la Fricción OLTP a la Analítica Histórica OLAP
- **Comparativa visual (2 Columnas enfrentadas):**
  - **Tarjeta 1: El Cuello de Botella Operacional (OLTP 3NF)**
    - ❌ 10 tablas relacionales encadenadas (`track -> recording -> medium -> release -> release_country -> artist_credit_name -> artist -> area -> isrc`).
    - ❌ Consultas analíticas sobre decenas de millones de filas que saturan la RAM y tardan minutos.
  - **Tarjeta 2: La Solución Data Warehouse (OLAP Estrella de Kimball)**
    - ✅ Tabla de hechos histórica diaria (`gold.fact_produccion_musical`) que contiene **únicamente FKs y métricas numéricas 100% aditivas** (cero textos, cero booleanos).
    - ✅ 6 dimensiones conformadas en español con claves subrogadas (`Surrogate Keys`) y patrón Fila Cero (`Key 0`).

---

#### DIAPOSITIVA 3: Objetivos y Requerimientos del Sistema (RF & RNF)
- **Requerimientos Funcionales Clave (RF01 - RF08):**
  - 🏆 RF01: Ranking Top N de artistas por `SUM(lanzamientos_total)`, `SUM(pistas_total)` y duración acumulada.
  - 📻 RF02: Comparativa de duración e idioma según formato (`dim_formato`: Vinilo vs CD vs Digital).
  - 🌍 RF03: Drill-down geográfico (`dim_geografia`) y temporal (`dim_fecha`: Siglo > Década > Año > Mes > Día).
  - ⏱️ RF04 & RF07: Volumen de canciones largas (`SUM(pistas_largas_total)`) y densidad de pistas por lanzamiento/soporte.
  - 📉 RF05: Demostración matemática de cómo el streaming acortó la música (Correlación Pearson).
  - 🔒 RF06 & RF08: Tasa de formalización discográfica ISRC (`SUM(pistas_con_isrc_total) / SUM(pistas_total)`).

---

#### DIAPOSITIVA 4: Origen de Datos 100% Reales y Capa Silver (10 Tablas 3NF)
- **Fuente Oficial:** MusicBrainz Database Full Export (`mbdump.tar.bz2`, Schema Sequence 31).
- **Las 10 Tablas de la Capa Silver (`silver`):**
  1. `silver.area` (120k áreas geográficas)
  2. `silver.artist` (3.01M artistas)
  3. `silver.artist_credit_name` (puente exacto hacia `artist.id` principal)
  4. `silver.release` (5.84M lanzamientos)
  5. `silver.release_country` (fechas históricas reales `date_year/month/day` y país de publicación)
  6. `silver.release_unknown_country` (fechas históricas reales sin país)
  7. `silver.medium` (6.41M soportes físicos/digitales)
  8. `silver.recording` (40.53M grabaciones maestras)
  9. `silver.track` (15.00M pistas)
  10. `silver.isrc` (6.48M códigos internacionales ISRC)

---

#### DIAPOSITIVA 5: Arquitectura Medallón (`silver` -> `gold` -> `meta`)
- 🥈 **Capa Silver (3NF):** ~89,3 millones de filas totales con tipos nativos y `TEXT` TOAST.
- 🥇 **Capa Gold (Modelo Estrella Puro en Español):** 6 dimensiones conformadas + `gold.fact_produccion_musical` particionada por `fecha_key` + 4 vistas materializadas.
- 🛡️ **Esquema Meta (Gobernanza):** `meta.etl_audit` (trazabilidad de lotes y velocidades) y `meta.data_quality_log` (validación automatizada de 0 huérfanos y no negatividad).

---

#### DIAPOSITIVA 6: El Grano Histórico Diario y el Modelo en Estrella Puro en Español
- **Declaración del Grano (Ralph Kimball):**
  - *"Un registro individual en `gold.fact_produccion_musical` representa el resumen histórico diario (`fecha_key`) de la producción musical consolidada por artista (`artista_key`), perfil de lanzamiento (`lanzamiento_key`), geografía (`geografia_key`), formato (`formato_key`) e idioma (`idioma_key`)."*
- **Estructura Exacta de la Tabla de Hechos (`gold.fact_produccion_musical`):**
  - **Claves Foráneas (FKs):** `hecho_key`, `fecha_key`, `artista_key`, `lanzamiento_key`, `geografia_key`, `formato_key`, `idioma_key`.
  - **11 Métricas Numéricas 100% Aditivas (`SUM`):** `lanzamientos_total`, `soportes_total`, `pistas_total`, `grabaciones_unicas_total`, `duracion_total_ms`, `duracion_total_segundos`, `duracion_total_minutos`, `pistas_con_isrc_total`, `pistas_largas_total`, `pistas_video_total`, `pistas_completas_total`.

---

#### DIAPOSITIVA 7: Las 6 Dimensiones Conformadas y sus Atributos Exactos
1. **`gold.dim_fecha` (47.848 filas):** `fecha_key`, `fecha_completa`, `anio`, `trimestre`, `nombre_trimestre`, `mes`, `nombre_mes`, `nombre_mes_corto`, `dia`, `dia_semana`, `nombre_dia`, `es_fin_de_semana`, `decada`, `siglo`.
2. **`gold.dim_artista` (3.010.452 filas):** `artista_key`, `artista_id`, `artista_gid`, `nombre_artista`, `nombre_orden`, `tipo_artista`, `genero`, `area_id`, `nombre_area`, `nombre_pais`, `anio_inicio`, `anio_fin`, `finalizado`.
3. **`gold.dim_lanzamiento` (~150 perfiles):** `lanzamiento_key`, `estado_id`, `empaque_id`, `calidad_id`, `estado_lanzamiento`, `tipo_empaque`, `calidad_datos`.
4. **`gold.dim_geografia` (120.108 filas):** `geografia_key`, `area_id`, `area_gid`, `nombre_area`, `tipo_area`, `nombre_pais`.
5. **`gold.dim_formato` (114 filas):** `formato_key`, `formato_id`, `nombre_formato`, `categoria_formato`.
6. **`gold.dim_idioma` (354 filas):** `idioma_key`, `idioma_id`, `nombre_idioma`, `codigo_iso`.

---

#### DIAPOSITIVA 8: Patrón Anti-Huérfanos "Key 0" y Calidad Referencial
- Cada dimensión conformada posee un registro inicial con clave sustituta `0` (`Sin Fecha`, `Artista Desconocido`, `No Clasificado`, `Sin Área Registrada`, `Formato No Especificado`, `Idioma No Especificado`).
- Durante la agregación histórica hacia `gold.fact_produccion_musical`, `COALESCE(dim_key, 0)` garantiza **0 registros huérfanos**, auditado automáticamente en `meta.data_quality_log`.

---

#### DIAPOSITIVA 9: Pipeline ETL de Alto Rendimiento en Python + PostgreSQL COPY
- Extracción quirúrgica bajo demanda desde `mbdump.tar.bz2` en `etl/silver/ingest_silver.py`.
- Streaming controlado de 15M de pistas con `MaxLineReader` (buffer de 128 KB) en `etl/silver/ingest_tracks_sliced.py`.
- Transformación y agregación histórica set-based en `etl/gold/run_gold_pipeline.py`.

---

#### DIAPOSITIVA 10: Catálogo de Reglas EDA (E01 - E10)
- **E01:** Fallback jerárquico de duración (`track.length` -> `recording.length`) y conteo aditivo `pistas_completas_total`.
- **E02:** Fechas históricas reales de publicación desde `release_country` y `release_unknown_country`.
- **E03:** Resolución de autoría principal (`position = 0`) vía `artist_credit_name`.
- **E04 & E05:** Deduplicación de ISRCs por grabación y conversión de booleanos en métricas enteras aditivas.
- **E09:** JOIN geográfico exacto por clave entera `area_id` (eliminando Fan Traps por nombres de ciudades homónimas).

---

#### DIAPOSITIVA 11: Particionamiento Físico y Vistas Materializadas en Español
- **14 Particiones por Rango en `fecha_key`:** `fact_produccion_unknown`, `pre_1970`, décadas `1970s` a `2010s`, anuales `2020` a `2025`, `2026_plus` y `default`.
- **4 Vistas Materializadas Indexadas:**
  - `gold.mv_tendencias_produccion_anual`
  - `gold.mv_analitica_artistas`
  - `gold.mv_evolucion_formatos`
  - `gold.mv_distribucion_geografica`

---

#### DIAPOSITIVA 12: Explotación Analítica en Power BI y Medidas DAX Aditivas
- Todas las medidas DAX operan sobre `SUM` de columnas aditivas (`SUM(lanzamientos_total)`, `SUM(pistas_total)`, `SUM(pistas_con_isrc_total)`, `SUM(duracion_total_segundos) / SUM(pistas_completas_total)`).
- Hallazgos demostrados: acortamiento de la duración musical en la era del streaming, transición Vinilo -> CD -> Digital y brecha regional de cobertura ISRC.

---

#### DIAPOSITIVA 13: Conclusiones e Ingeniería de Datos
- Un diseño dimensional puro de Ralph Kimball —donde la tabla de hechos almacena únicamente el registro histórico diario con FKs y métricas numéricas aditivas— maximiza el rendimiento analítico y la claridad de negocio.
```
