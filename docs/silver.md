# Capa Plata: Limpieza, Tipado e Integridad Relacional 3NF (`silver`)

La capa **Silver** del Data Warehouse **DWMusicBrainz** consolida los datos extraídos del volcado nativo oficial de MusicBrainz (`mbdump.tar.bz2`, Schema Sequence 31) en un modelo relacional normalizado en **Tercera Forma Normal (3NF)** con tipos nativos de PostgreSQL (`INTEGER`, `SMALLINT`, `UUID`, `BOOLEAN`, `TIMESTAMPTZ`, `TEXT`), claves primarias (`PK`) e índices estratégicos.

---

## 1. Principios de Transformación e Ingeniería de Datos

- **Tipado Fuerte y Soporte de Cadenas Extensas (`TEXT`):** Los atributos descriptivos utilizan el tipo nativo `TEXT` de PostgreSQL con compresión automática TOAST para soportar títulos y comentarios de más de 2.000 caracteres sin errores de truncamiento.
- **Resolución de Fechas Históricas Reales (`release_country` y `release_unknown_country`):** En lugar de utilizar únicamente timestamps de auditoría (`last_updated`), la capa Silver incorpora las tablas de eventos de publicación que contienen el año, mes, día y país real de cada lanzamiento discográfico desde 1900 hasta 2026.
- **Resolución Exacta de Créditos de Artistas (`artist_credit_name`):** Permite vincular de forma determinista cada `artist_credit` con el `artist.id` principal (`position = 0`), evitando falsas igualdades entre IDs de créditos y IDs de artistas.
- **Streaming Bufferizado con `MaxLineReader`:** En `etl/silver/ingest_tracks_sliced.py`, la clase `MaxLineReader` lee con buffer de 128 KB para ingestar 15.000.000 de pistas reales vía `COPY FROM STDIN` sin saturar la memoria RAM.

---

## 2. Las 10 Tablas de la Capa Silver (3NF)

1. **`silver.area`**: Entidades geográficas (`id`, `gid`, `name`, `type`).
2. **`silver.artist`**: Artistas solistas, bandas, coros y orquestas (`id`, `gid`, `name`, `sort_name`, `begin_date_year`, `type`, `area`, `gender`).
3. **`silver.artist_credit_name`**: Tabla puente que resuelve el crédito artístico hacia el `artist` real (`artist_credit`, `position`, `artist`, `name`).
4. **`silver.release`**: Lanzamientos discográficos (`id`, `gid`, `name`, `artist_credit`, `release_group`, `status`, `packaging`, `language`, `quality`).
5. **`silver.release_country`**: Eventos de publicación por país con fecha histórica real (`release`, `country`, `date_year`, `date_month`, `date_day`).
6. **`silver.release_unknown_country`**: Fechas históricas reales de lanzamientos sin país especificado (`release`, `date_year`, `date_month`, `date_day`).
7. **`silver.medium`**: Soportes físicos o digitales que componen un lanzamiento (`id`, `release`, `position`, `format`, `track_count`).
8. **`silver.recording`**: Grabaciones maestras de audio (`id`, `gid`, `name`, `artist_credit`, `length`, `video`).
9. **`silver.track`**: Pistas incluidas en cada soporte (`id`, `gid`, `recording`, `medium`, `position`, `number`, `name`, `artist_credit`, `length`).
10. **`silver.isrc`**: Códigos Estándar Internacionales de Grabación (`id`, `recording`, `isrc`).

---

## 3. Orden de Ingesta y Extracción Bajo Demanda

El script [`etl/silver/ingest_silver.py`](file:///C:/Users/sebas/Documentos/GitHub/DWH-MusicBrainz/etl/silver/ingest_silver.py) verifica la existencia de cada archivo en `data/raw/mbdump/` y, si falta alguno, lo extrae quirúrgicamente desde `mbdump.tar.bz2` antes de ejecutar `COPY FROM STDIN`:

1. `silver.area`
2. `silver.artist`
3. `silver.artist_credit_name`
4. `silver.release`
5. `silver.release_country`
6. `silver.release_unknown_country`
7. `silver.medium`
8. `silver.isrc`
9. `silver.recording`
10. `silver.track` (vía `ingest_tracks_sliced.py` o `ingest_silver.py`)
