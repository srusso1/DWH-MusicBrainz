-- ============================================================================
-- POBLADO DE HECHO AGREGADO: gold.fact_distribucion_duracion
-- Grano: Año (YYYY0101) x formato x idioma x geografía x banda de duración.
-- Resuelve año, país, formato e idioma con las mismas reglas que
-- populate_fact_tracks.sql para que ambos hechos sean consistentes.
-- ============================================================================

TRUNCATE TABLE gold.fact_distribucion_duracion;

WITH release_evento_primario AS (
    SELECT DISTINCT ON (release)
        release,
        country,
        date_year
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
detalle_pistas AS (
    SELECT
        -- Año real del lanzamiento (misma regla que el hecho principal), anclado
        -- al 1 de enero; sin fecha real -> clave 0
        CASE
            WHEN re.date_year BETWEEN 1900 AND 2030
                THEN re.date_year::INTEGER * 10000 + 101
            ELSE 0
        END AS fecha_candidata,
        COALESCE(re.country, art.area, 0) AS area_id_resuelta,
        COALESCE(m.format, 0) AS formato_id_resuelto,
        COALESCE(rel.language, 0) AS idioma_id_resuelto,
        GREATEST(COALESCE(NULLIF(t.length, 0), NULLIF(rec.length, 0), 0), 0)::BIGINT AS duracion_ms
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
)
INSERT INTO gold.fact_distribucion_duracion (
    fecha_key,
    formato_key,
    idioma_key,
    geografia_key,
    rango_duracion_key,
    pistas_total,
    duracion_total_ms
)
SELECT
    COALESCE(d.fecha_key, 0),
    COALESCE(df.formato_key, 0),
    COALESCE(di.idioma_key, 0),
    COALESCE(dg.geografia_key, 0),
    CASE
        WHEN dp.duracion_ms <= 0 THEN 0
        WHEN dp.duracion_ms >= 600000 THEN 21
        ELSE (dp.duracion_ms / 30000)::INTEGER + 1
    END AS rango_duracion_key,
    COUNT(*)::INTEGER AS pistas_total,
    SUM(dp.duracion_ms)::BIGINT AS duracion_total_ms
FROM detalle_pistas dp
LEFT JOIN gold.dim_fecha d ON dp.fecha_candidata = d.fecha_key
LEFT JOIN gold.dim_geografia dg ON dp.area_id_resuelta = dg.area_id
LEFT JOIN gold.dim_formato df ON dp.formato_id_resuelto = df.formato_id
LEFT JOIN gold.dim_idioma di ON dp.idioma_id_resuelto = di.idioma_id
GROUP BY 1, 2, 3, 4, 5;
