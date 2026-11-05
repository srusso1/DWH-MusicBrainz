# DWMusicBrainz en Databricks

Pipeline Medallón sobre Spark y Delta Lake para el volcado completo de MusicBrainz (58,8 M de pistas). No reemplaza `etl/` ni `sql/`, que conservan la entrega de PostgreSQL con 15 M de pistas.

## Estructura

| Ruta | Función |
|---|---|
| `pipeline/00_pruebas.py` | Pruebas de reglas de negocio con fixtures pequeñas |
| `pipeline/01_bronze.py` | Copia fiel del volcado, todo como texto |
| `pipeline/02_silver.py` | Tipos, escapes y control de calidad |
| `pipeline/02b_catalogos.py` | Catálogos oficiales para las etiquetas |
| `pipeline/03_gold_dimensiones.py` | 7 dimensiones con fila cero |
| `pipeline/04_gold_fact_pista.py` | Hecho a nivel de pista |
| `pipeline/05_gold_agregados.py` | Hechos agregados y tablas `mv_*` para el dashboard |
| `pipeline/06_validacion.py` | Integridad, aditividad y reconciliación |
| `pipeline/lib/` | Contrato de datos, reglas, etiquetas y auditoría |
| `pipeline/job.json` | Definición del job de Lakeflow |
| `dashboards/DWMusicBrainz.lvdash.json` | Dashboard AI/BI de 3 páginas sobre `workspace.gold` |
| `spikes/` | Prueba de capacidad descartable |

## Ejecución

1. Subir el código: `databricks workspace import-dir databricks/pipeline /Users/<usuario>/dwh_musicbrainz/pipeline --overwrite --profile <perfil>`
2. Preparar el job: `pipeline/job.json` usa el marcador `<USUARIO_WORKSPACE>` para no publicar datos personales. Generá una copia local con tu usuario y no la agregues a Git, por ejemplo: `(Get-Content pipeline/job.json -Raw).Replace('<USUARIO_WORKSPACE>', $env:DATABRICKS_USUARIO) | Set-Content job.local.json`
3. Crear el job: `databricks jobs create --json @job.local.json --profile <perfil>`
4. Ejecutar el job: `databricks jobs run-now <job_id> --profile <perfil>`

Cada etapa queda registrada en `workspace.meta.etl_audit` y no se repite para la misma versión del volcado. Para reconstruir todo, ejecutar el job con el parámetro `forzar=true`.

Un archivo de más de 5 GiB no se puede subir con `databricks fs cp`. Por eso `track` está dividido en bloques de 1 GB dentro de `mbdump/track/`, que Spark lee como una sola tabla.

## Decisiones

- **Escapes de texto:** PostgreSQL exporta `\t`, `\n`, `\r` y `\\` con barra invertida. Bronze los conserva sin tocar el dato crudo y Silver los revierte solo en las columnas `text` de `lib/esquemas.py`.
- **Claves sustitutas:** son secuenciales desde 1 y se ordenan por la clave natural. La fila 0 se reserva para el valor desconocido.
- **`dim_lanzamiento`:** es una dimensión de perfil (estado, empaque y calidad), no una fila por lanzamiento. El identificador del lanzamiento queda en `fact_pista.lanzamiento_id`.
- **Primeras pistas:** se calculan con `min(struct)` en lugar de `ROW_NUMBER`.
- **Evento primario:** la fecha es la más antigua del lanzamiento. El territorio se resuelve entre los países empatados en esa fecha:
  - Un solo país: se conserva.
  - `[Worldwide]` entre los empatados: gana.
  - 10 o más países: pasa a `[Worldwide]`, porque el lanzamiento es multiterritorio.
  - De 2 a 9 países: gana el país con más lanzamientos en `release_country`, y el menor id solo desempata.
  - La regla V12 de `06_validacion.py` bloquea el job si un país recibe lanzamientos por estos empates.

## Cambios frente al ETL de PostgreSQL

- Se conserva el 29 de febrero real; antes pasaba al día 1.
- Un `artist_credit` ya no se usa como `artist.id` cuando falta el crédito.
- `medium` usa el orden real de columnas: `edits_pending` es la columna 6 y `track_count` la 8.
- Las etiquetas salen de los catálogos oficiales, no de IDs escritos a mano.

## Etiquetas de dimensiones

Los catálogos oficiales del volcado se cargan desde el Volume a `silver.catalogo_*`. Cada ID se resuelve a su nombre oficial y `lib/catalogos.py` solo traduce ese nombre; un nombre sin traducción conserva el oficial. La categoría de formato se hereda del ancestro más cercano en la jerarquía `parent`.

Las reglas V08 a V11 de `06_validacion.py` bloquean el job si una etiqueta difiere del catálogo.

La calidad es la excepción: MusicBrainz no la publica como catálogo en el volcado, así que `CALIDAD_DATOS` queda definida en el código.

La fila 0 de `dim_lanzamiento` tiene calidad `Baja` porque la ocupan 770 lanzamientos reales con calidad 0, sin estado ni empaque.

Para reconstruir solo algunas tablas, ejecutar el job con `forzar=true` y `solo=<tablas separadas por coma>`, limitando las tareas con `only`.

## Dashboard AI/BI

`dashboards/DWMusicBrainz.lvdash.json` reproduce las 3 páginas del reporte de Power BI. Para desplegarlo:

1. Crear un archivo JSON con `display_name`, `warehouse_id`, `parent_path` y `serialized_dashboard`, este último con el contenido del `.lvdash.json` como texto.
2. Crear el dashboard: `databricks lakeview create --json @cuerpo.json --profile musicbrainz`. Se pasa por archivo porque supera el largo de línea de comandos de Windows.
3. Publicarlo: `databricks lakeview publish <dashboard_id> --warehouse-id <warehouse_id> --embed-credentials=false --profile musicbrainz`.

Para actualizar uno existente se usa `databricks lakeview update <dashboard_id>` y se vuelve a publicar.
