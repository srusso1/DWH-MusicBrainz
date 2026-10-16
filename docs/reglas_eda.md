# Reglas EDA y Criterios de Limpieza de Datos (`DWMusicBrainz`)

Este documento define el catálogo de reglas de calidad y limpieza de datos (**E01 a E10**) aplicadas durante la transformación de la capa **Silver (3NF)** hacia la capa **Gold (Modelo en Estrella Puro en Español)**, garantizando que el hecho histórico diario `gold.fact_produccion_musical` y las 6 dimensiones conformadas operen sobre datos limpios, auditados y matemáticamente aditivos.

---

## 1. Catálogo Oficial de Reglas de Calidad (E01 — E10)

| ID | Regla de Calidad | Acción Técnica Implementada | Justificación Arquitectónica |
| :---: | :--- | :--- | :--- |
| **E01** | Duraciones nulas, negativas o en cero en pistas (`length`) | Fallback jerárquico: `GREATEST(COALESCE(NULLIF(t.length, 0), NULLIF(rec.length, 0), 0), 0)`. Conteo aditivo en `pistas_completas_total`. | Rescata la duración del master original (`recording`) si el track no la reporta y contabiliza aditivamente las pistas con duración válida. |
| **E02** | Fechas históricas reales de lanzamiento parciales o ausentes | Resolución priorizando `silver.release_country`, luego `silver.release_unknown_country`, luego `artist.begin_date_year` y fallback a `fecha_key = 0`. | Garantiza que la dimensión tiempo refleje la fecha histórica real de publicación musical (1900–2030) y no una fecha artificial de edición. |
| **E03** | Artistas sin nombre o créditos compuestos (`artist_credit`) | Resolución del artista principal (`position = 0`) vía `silver.artist_credit_name` e imputación `'Sin Nombre'` si está vacío. | Evita cruzar `artist_credit` directamente contra `artist.id` y asegura integridad en `gold.dim_artista`. |
| **E04** | Códigos ISRC múltiples por grabación | Deduplicación previa `SELECT DISTINCT recording FROM silver.isrc` y suma aditiva `SUM(tiene_isrc)` en `pistas_con_isrc_total`. | Impide la multiplicación de filas (Fan Trap) al unir con `silver.isrc` y convierte el antiguo booleano en una métrica numérica aditiva. |
| **E05** | Eliminación de booleanos y textos en la tabla de hechos | Conversión de flags a métricas enteras aditivas (`lanzamientos_total`, `soportes_total`, `pistas_total`, `pistas_largas_total`, `pistas_video_total`). | Cumple estrictamente el diseño de tabla de hechos histórica de Ralph Kimball donde solo residen FKs y métricas aditivas. |
| **E06** | Textos con longitud extrema (> 1.000 caracteres) | Uso nativo de tipo `TEXT` en PostgreSQL con compresión automática TOAST en `silver` y `gold`. | Evita fallos de truncamiento en nombres extensos de obras clásicas o experimentales. |
| **E07** | Claves foráneas huérfanas en dimensiones | Imputación al registro surrogate `0` de fallback (`COALESCE(dim_key, 0)`). | Garantiza **CERO HUÉRFANOS** en el modelo en estrella sin pérdida de hechos históricos. |
| **E08** | Codificación alterada o presencia de BOM (`\ufeff`) | Decodificación con `utf-8-sig` y manejo seguro `errors='replace'`. | Asegura lecturas limpias de los volcados TSV en entornos Windows. |
| **E09** | Cruce geográfico sin ambigüedad de nombres homónimos | Unión exacta por clave entera (`area_id`) entre `release_country` / `artist.area` y `gold.dim_geografia.area_id`. | Elimina la duplicación de hechos causada por ciudades o regiones con el mismo nombre en distintos países. |
| **E10** | Registro automatizado de auditoría de calidad | Inserción automática de resultados de validación en `meta.data_quality_log` al finalizar `run_gold_pipeline.py`. | Provee trazabilidad verificable de integridad referencial y no negatividad de métricas. |
