-- ============================================================================
-- POBLADO MASIVO DE TABLA DE HECHOS HISTÓRICA DIARIA: gold.fact_produccion_musical
-- Grano: 1 registro histórico por Día (fecha_key) y combinación de las
-- 5 dimensiones conformadas (artista_key, lanzamiento_key, geografia_key,
-- formato_key, idioma_key) con Métricas Numéricas 100% Aditivas.
-- ============================================================================

TRUNCATE TABLE gold.fact_produccion_musical RESTART IDENTITY;

WITH release_evento_primario AS (
    -- Resuelve la primera fecha histórica real de publicación y país de lanzamiento
    -- priorizando silver.release_country y luego silver.release_unknown_country
    SELECT DISTINCT ON (release)
        release,
        country,
        date_year,
        date_month,
        date_day
    FROM (
        SELECT release, country, date_year, date_month, date_day, 1 AS prioridad
        FROM silver.release_country
        UNION ALL
        SELECT release, NULL::INTEGER AS country, date_year, date_month, date_day, 2 AS prioridad
        FROM silver.release_unknown_country
    ) eventos
    ORDER BY
        release,
        prioridad,
        COALESCE(date_year, 9999),
        COALESCE(date_month, 12),
        COALESCE(date_day, 31)
),
isrc_por_grabacion AS (
    -- Determina si una grabación de audio posee al menos un código ISRC registrado
    SELECT DISTINCT recording
    FROM silver.isrc
),
detalle_pistas AS (
    SELECT
        -- 1. Resolución de Fecha Histórica Real (YYYYMMDD) validada en rango 1900-2030
        CASE
            WHEN COALESCE(re.date_year, art.begin_date_year) BETWEEN 1900 AND 2030 THEN
                (COALESCE(re.date_year, art.begin_date_year)::INTEGER * 10000)
                + (
                    CASE
                        WHEN re.date_month BETWEEN 1 AND 12 THEN re.date_month::INTEGER
                        ELSE 1
                    END * 100
                )
                + (
                    CASE
                        WHEN re.date_month IN (1, 3, 5, 7, 8, 10, 12) AND re.date_day BETWEEN 1 AND 31 THEN re.date_day::INTEGER
                        WHEN re.date_month IN (4, 6, 9, 11) AND re.date_day BETWEEN 1 AND 30 THEN re.date_day::INTEGER
                        WHEN re.date_month = 2 AND re.date_day BETWEEN 1 AND 28 THEN re.date_day::INTEGER
                        ELSE 1
                    END
                )
            WHEN rel.last_updated IS NOT NULL
                 AND EXTRACT(YEAR FROM rel.last_updated) BETWEEN 1900 AND 2030 THEN
                TO_CHAR(rel.last_updated, 'YYYYMMDD')::INTEGER
            ELSE 0
        END AS fecha_candidata,

        -- 2. Claves Naturales para cruce con Dimensiones Conformadas
        COALESCE(acn_track.artist, acn_rel.artist, t.artist_credit, 0) AS artista_id_resuelto,
        COALESCE(rel.status, 0) AS estado_id,
        COALESCE(rel.packaging, 0) AS empaque_id,
        COALESCE(rel.quality, 0) AS calidad_id,
        COALESCE(re.country, art.area, 0) AS area_id_resuelta,
        COALESCE(m.format, 0) AS formato_id_resuelto,
        COALESCE(rel.language, 0) AS idioma_id_resuelto,

        -- 3. Entidades y Medidas Base para Agregación Aditiva
        rel.id AS release_id,
        m.id AS medium_id,
        t.id AS track_id,
        t.recording AS recording_id,
        GREATEST(COALESCE(NULLIF(t.length, 0), NULLIF(rec.length, 0), 0), 0)::BIGINT AS duracion_ms,
        CASE WHEN isrc_g.recording IS NOT NULL THEN 1 ELSE 0 END AS tiene_isrc,
        CASE WHEN COALESCE(rec.video, FALSE) IS TRUE THEN 1 ELSE 0 END AS es_video

    FROM silver.track t
    JOIN silver.medium m ON t.medium = m.id
    JOIN silver.release rel ON m.release = rel.id
    LEFT JOIN silver.recording rec ON t.recording = rec.id
    LEFT JOIN release_evento_primario re ON rel.id = re.release
    LEFT JOIN silver.artist_credit_name acn_track
        ON t.artist_credit = acn_track.artist_credit AND acn_track.position = 0
    LEFT JOIN silver.artist_credit_name acn_rel
        ON rel.artist_credit = acn_rel.artist_credit AND acn_rel.position = 0
    LEFT JOIN silver.artist art
        ON COALESCE(acn_track.artist, acn_rel.artist, t.artist_credit) = art.id
    LEFT JOIN isrc_por_grabacion isrc_g
        ON t.recording = isrc_g.recording
)
INSERT INTO gold.fact_produccion_musical (
    fecha_key,
    artista_key,
    lanzamiento_key,
    geografia_key,
    formato_key,
    idioma_key,
    lanzamientos_total,
    soportes_total,
    pistas_total,
    grabaciones_unicas_total,
    duracion_total_ms,
    duracion_total_segundos,
    duracion_total_minutos,
    pistas_con_isrc_total,
    pistas_largas_total,
    pistas_video_total,
    pistas_completas_total
)
SELECT
    -- Claves Foráneas Conformadas con garantía Cero Huérfanos (Patrón Key 0)
    COALESCE(d.fecha_key, 0) AS fecha_key,
    COALESCE(da.artista_key, 0) AS artista_key,
    COALESCE(dl.lanzamiento_key, 0) AS lanzamiento_key,
    COALESCE(dg.geografia_key, 0) AS geografia_key,
    COALESCE(df.formato_key, 0) AS formato_key,
    COALESCE(di.idioma_key, 0) AS idioma_key,

    -- Métricas Históricas 100% Aditivas (Consolidación por Día y Dimensiones)
    COUNT(DISTINCT dp.release_id)::INTEGER AS lanzamientos_total,
    COUNT(DISTINCT dp.medium_id)::INTEGER AS soportes_total,
    COUNT(dp.track_id)::INTEGER AS pistas_total,
    COUNT(DISTINCT dp.recording_id)::INTEGER AS grabaciones_unicas_total,
    SUM(dp.duracion_ms)::BIGINT AS duracion_total_ms,
    ROUND(SUM(dp.duracion_ms) / 1000.0, 2) AS duracion_total_segundos,
    ROUND(SUM(dp.duracion_ms) / 60000.0, 2) AS duracion_total_minutos,
    SUM(dp.tiene_isrc)::INTEGER AS pistas_con_isrc_total,
    SUM(CASE WHEN dp.duracion_ms > 300000 THEN 1 ELSE 0 END)::INTEGER AS pistas_largas_total,
    SUM(dp.es_video)::INTEGER AS pistas_video_total,
    SUM(CASE WHEN dp.duracion_ms > 0 THEN 1 ELSE 0 END)::INTEGER AS pistas_completas_total

FROM detalle_pistas dp
LEFT JOIN gold.dim_fecha d ON dp.fecha_candidata = d.fecha_key
LEFT JOIN gold.dim_artista da ON dp.artista_id_resuelto = da.artista_id
LEFT JOIN gold.dim_lanzamiento dl
    ON dp.estado_id = dl.estado_id
   AND dp.empaque_id = dl.empaque_id
   AND dp.calidad_id = dl.calidad_id
LEFT JOIN gold.dim_geografia dg ON dp.area_id_resuelta = dg.area_id
LEFT JOIN gold.dim_formato df ON dp.formato_id_resuelto = df.formato_id
LEFT JOIN gold.dim_idioma di ON dp.idioma_id_resuelto = di.idioma_id
GROUP BY
    COALESCE(d.fecha_key, 0),
    COALESCE(da.artista_key, 0),
    COALESCE(dl.lanzamiento_key, 0),
    COALESCE(dg.geografia_key, 0),
    COALESCE(df.formato_key, 0),
    COALESCE(di.idioma_key, 0);