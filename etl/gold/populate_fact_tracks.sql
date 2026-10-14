-- ============================================================================
-- POBLADO MASIVO DE TABLA DE HECHOS CENTRAL: gold.fact_tracks
-- Particionada por Rango en date_key con Claves Subrogadas Conformadas
-- ============================================================================

INSERT INTO gold.fact_tracks (
    date_key,
    artist_key,
    release_key,
    geo_key,
    format_key,
    language_key,
    track_id,
    track_gid,
    recording_id,
    recording_gid,
    track_name,
    track_number,
    position,
    isrc_code,
    has_isrc,
    is_video,
    duration_ms,
    duration_seconds,
    duration_minutes,
    track_count,
    is_complete
)
SELECT 
    -- 1. Date Key con fallback a 0 (Sin Fecha)
    COALESCE(d.date_key, 0) AS date_key,
    
    -- 2. Claves Subrogadas Conformadas (Garantía Cero Huérfanos)
    COALESCE(a.artist_key, 0) AS artist_key,
    COALESCE(r.release_key, 0) AS release_key,
    COALESCE(geo.geo_key, 0) AS geo_key,
    COALESCE(fmt.format_key, 0) AS format_key,
    COALESCE(lang.language_key, 0) AS language_key,
    
    -- 3. Dimensiones Degeneradas y Negocio
    t.id AS track_id,
    t.gid AS track_gid,
    t.recording AS recording_id,
    COALESCE(rec.gid, '00000000-0000-0000-0000-000000000000'::UUID) AS recording_gid,
    COALESCE(NULLIF(TRIM(t.name), ''), 'Pista Sin Título') AS track_name,
    SUBSTRING(t.number FROM 1 FOR 50) AS track_number,
    t.position,
    i.isrc AS isrc_code,
    (i.isrc IS NOT NULL) AS has_isrc,
    COALESCE(rec.video, FALSE) AS is_video,
    
    -- 4. Métricas Numéricas Aditivas
    COALESCE(NULLIF(t.length, 0), NULLIF(rec.length, 0), 0) AS duration_ms,
    ROUND(COALESCE(NULLIF(t.length, 0), NULLIF(rec.length, 0), 0) / 1000.0, 2) AS duration_seconds,
    ROUND(COALESCE(NULLIF(t.length, 0), NULLIF(rec.length, 0), 0) / 60000.0, 2) AS duration_minutes,
    1 AS track_count,
    CASE WHEN COALESCE(t.length, rec.length, 0) > 0 THEN 1 ELSE 0 END AS is_complete

FROM silver.track t
-- Grabación (master)
LEFT JOIN silver.recording rec ON t.recording = rec.id

-- Medium y Release
JOIN silver.medium m ON t.medium = m.id
JOIN silver.release rel ON m.release = rel.id

-- Código ISRC (primer código asociado si existe)
LEFT JOIN (
    SELECT DISTINCT ON (recording) recording, isrc 
    FROM silver.isrc
    ORDER BY recording, id
) i ON t.recording = i.recording

-- Dimensiones Conformadas
LEFT JOIN gold.dim_artist a ON t.artist_credit = a.artist_id
LEFT JOIN gold.dim_release r ON rel.id = r.release_id
LEFT JOIN gold.dim_format fmt ON COALESCE(m.format, 0) = fmt.format_id
LEFT JOIN gold.dim_language lang ON COALESCE(rel.language, 0) = lang.language_id
LEFT JOIN gold.dim_geography geo ON a.area_name = geo.area_name

-- Cálculo de date_key
LEFT JOIN gold.dim_date d ON 
    TO_CHAR(COALESCE(rel.last_updated, t.last_updated), 'YYYYMMDD')::INTEGER = d.date_key
    AND d.date_key > 0;