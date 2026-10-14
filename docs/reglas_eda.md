# Reglas EDA y Criterios de Limpieza de Datos (`DWMusicBrainz`)

Este documento define el catálogo de reglas de calidad y limpieza de datos (**E01 a E10**) aplicadas durante la transformación de la capa **Silver (3NF)** hacia la capa **Gold (Modelo en Estrella)**, garantizando que el hecho central `gold.fact_tracks` y las 6 dimensiones conformadas operen sobre datos limpios, auditados y matemáticamente consistentes.

---

## 1. Catálogo Oficial de Reglas de Calidad (E01 — E10)

| ID | Regla de Calidad | Acción Técnica Implementada | Justificación Arquitectónica |
| :---: | :--- | :--- | :--- |
| **E01** | Duraciones nulas o en cero en pistas (`length`) | Fallback jerárquico: `COALESCE(NULLIF(t.length, 0), NULLIF(rec.length, 0), 0)`. Flag `is_complete = 0`. | Permite rescatar la duración del master original (`recording`) si el track no la reporta, evitando imputaciones artificiales. |
| **E02** | Textos vacíos, espacios en blanco o nulos en nombres de tracks | Imputar `'Pista Sin Título'` mediante `COALESCE(NULLIF(TRIM(name), ''), 'Pista Sin Título')`. | Garantiza legibilidad en tablas y visualizaciones de Power BI sin alterar el conteo de temas. |
| **E03** | Artistas o lanzamientos sin nombre en origen | Imputar `'Artista No Identificado'` o `'Lanzamiento No Identificado'`. | Cumple la regla de no admitir etiquetas vacías en dimensiones conformadas. |
| **E04** | Códigos ISRC duplicados o múltiples por grabación | Selección determinista del primer código mediante `DISTINCT ON (recording) ORDER BY recording, id`. | Asegura unicidad 1:1 en el hecho central y exactitud en la métrica booleana `has_isrc`. |
| **E05** | Fechas de lanzamiento ausentes, parciales o nulas | Derivación desde `last_updated`; si es nula, asociar a clave subrogada `date_key = 0`. | Protege el grano temporal continuo (1900–2030) sin descartar transacciones comerciales válidas. |
| **E06** | Textos con longitud extrema (> 1.000 caracteres) | Uso nativo de tipo de datos `TEXT` en PostgreSQL con compresión TOAST. | Evita el aborto de transacciones masivas por desbordamiento de `VARCHAR(n)` en temas experimentales. |
| **E07** | Claves foráneas huérfanas en dimensiones | Imputación al registro surrogate `0` de fallback (`dim_*_key = 0`). | Garantiza **CERO HUÉRFANOS** en el modelo en estrella sin pérdida de pistas ni fallos de integridad referencial. |
| **E08** | Codificación alterada o presencia de BOM (`\ufeff`) | Decodificación con `utf-8-sig` y fallback con `errors='replace'`. | Resuelve la incompatibilidad clásica de PowerShell y volcados de texto en Windows. |
| **E09** | Posición del tema (`position`) fuera de rango o nula | `COALESCE(t.position, 1)` y limitación a tipo `SMALLINT`. | Permite responder al requerimiento RF07 (posición de temas en álbumes) sin inconsistencias. |
| **E10** | Clave natural de negocio nula (`track_id IS NULL`) | Descarte inmediato de la fila con registro en auditoría. | Una pista sin identificador único no posee identidad atómica en la industria discográfica. |

---

## 2. Decisiones Arquitectónicas Específicas de la Industria Musical

### 2.1. Gestión de Duraciones Incompletas (E01)
En el negocio de la música, un tema sin duración no significa que la canción no exista; ocurre con frecuencia en pistas promocionales o lanzamientos preliminares.
* En lugar de inventar una duración promedio (lo cual distorsionaría el cálculo de la correlación Pearson en el **RF05**), la duración se mantiene en `0` y se activa el flag booleano `is_complete = 0`.
* En Power BI, las medidas de duración promedio filtran explícitamente `is_complete = 1`, preservando la pureza estadística del cálculo.

### 2.2. Resolución de Códigos ISRC (E04)
El código ISRC (*International Standard Recording Code*) identifica grabaciones sonoras a nivel global. En MusicBrainz, una misma grabación puede tener múltiples ISRCs asignados si fue reeditada en distintos países.
* El pipeline extrae una vista normalizada con `DISTINCT ON (recording)`, tomando el identificador cronológico más antiguo como representativo de la obra original, calculando con exactitud la tasa de formalización del catálogo (**RF06**).

### 2.3. Patrón de Fila Cero Anti-Huérfanos (E07)
A diferencia de sistemas transaccionales que rechazan filas no vinculadas, en Business Intelligence el descarte es el peor error porque altera los totales contables de producción.
* Cada una de las 6 dimensiones posee en su clave sustituta `0` un registro conformado:
  - `dim_artist`: `artist_key = 0` (*"Artista Desconocido"*).
  - `dim_release`: `release_key = 0` (*"Lanzamiento Desconocido"*).
  - `dim_geography`: `geo_key = 0` (*"País / Región Desconocida"*).
  - `dim_format`: `format_key = 0` (*"Formato No Especificado"*).
  - `dim_language`: `language_key = 0` (*"Idioma No Especificado"*).
  - `dim_date`: `date_key = 0` (*"Fecha No Registrada"*).
* Gracias a este patrón, el script de certificación `verify_dwh.py` confirmó **cero huérfanos** sobre los **19.370.311 registros** de hechos.
