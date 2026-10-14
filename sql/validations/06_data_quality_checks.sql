-- ============================================================================
-- PROYECTO: DWMusicBrainz (Data Warehouse Masivo de la Industria Musical)
-- CAPA: Validaciones / Pruebas de Calidad, Auditoría e Integridad Referencial
-- ARCHIVO: 06_data_quality_checks.sql
-- DESCRIPCIÓN: Suite de pruebas automatizadas de integridad Kimball y volumetría
-- ============================================================================

-- ----------------------------------------------------------------------------
-- PRUEBA 1: VOLUMETRÍA POR CAPA (Silver vs Gold)
-- ----------------------------------------------------------------------------
SELECT 'silver.area' AS tabla, COUNT(*) AS total_filas FROM silver.area
UNION ALL
SELECT 'silver.artist', COUNT(*) FROM silver.artist
UNION ALL
SELECT 'silver.release', COUNT(*) FROM silver.release
UNION ALL
SELECT 'silver.medium', COUNT(*) FROM silver.medium
UNION ALL
SELECT 'silver.recording', COUNT(*) FROM silver.recording
UNION ALL
SELECT 'silver.track', COUNT(*) FROM silver.track
UNION ALL
SELECT 'silver.isrc', COUNT(*) FROM silver.isrc
UNION ALL
SELECT 'gold.dim_date', COUNT(*) FROM gold.dim_date
UNION ALL
SELECT 'gold.dim_artist', COUNT(*) FROM gold.dim_artist
UNION ALL
SELECT 'gold.dim_geography', COUNT(*) FROM gold.dim_geography
UNION ALL
SELECT 'gold.dim_release', COUNT(*) FROM gold.dim_release
UNION ALL
SELECT 'gold.dim_format', COUNT(*) FROM gold.dim_format
UNION ALL
SELECT 'gold.dim_language', COUNT(*) FROM gold.dim_language
UNION ALL
SELECT 'gold.fact_tracks', COUNT(*) FROM gold.fact_tracks;

-- ----------------------------------------------------------------------------
-- PRUEBA 2: CONSUMO FÍSICO DE ALMACENAMIENTO EN DISCO (Meta > 3.0 GB)
-- ----------------------------------------------------------------------------
SELECT 
    schemaname,
    relname AS table_name,
    pg_size_pretty(pg_total_relation_size(relid)) AS total_size,
    pg_size_pretty(pg_relation_size(relid)) AS data_size,
    pg_size_pretty(pg_total_relation_size(relid) - pg_relation_size(relid)) AS index_size
FROM pg_catalog.pg_statio_user_tables
WHERE schemaname IN ('silver', 'gold')
ORDER BY pg_total_relation_size(relid) DESC;

-- ----------------------------------------------------------------------------
-- PRUEBA 3: INTEGRIDAD REFERENCIAL KIMBALL (Cero Huérfanos en fact_tracks)
-- ----------------------------------------------------------------------------
SELECT 'Huérfanos en dim_artist' AS test_name, COUNT(*) AS violaciones
FROM gold.fact_tracks f
LEFT JOIN gold.dim_artist a ON f.artist_key = a.artist_key
WHERE a.artist_key IS NULL
UNION ALL
SELECT 'Huérfanos en dim_date', COUNT(*)
FROM gold.fact_tracks f
LEFT JOIN gold.dim_date d ON f.date_key = d.date_key
WHERE d.date_key IS NULL
UNION ALL
SELECT 'Huérfanos en dim_release', COUNT(*)
FROM gold.fact_tracks f
LEFT JOIN gold.dim_release r ON f.release_key = r.release_key
WHERE r.release_key IS NULL
UNION ALL
SELECT 'Huérfanos en dim_format', COUNT(*)
FROM gold.fact_tracks f
LEFT JOIN gold.dim_format fmt ON f.format_key = fmt.format_key
WHERE fmt.format_key IS NULL
UNION ALL
SELECT 'Huérfanos en dim_geography', COUNT(*)
FROM gold.fact_tracks f
LEFT JOIN gold.dim_geography g ON f.geo_key = g.geo_key
WHERE g.geo_key IS NULL;

-- ----------------------------------------------------------------------------
-- PRUEBA 4: PRUNING DE PARTICIONES (EXPLAIN ANALYZE)
-- ----------------------------------------------------------------------------
EXPLAIN ANALYZE
SELECT 
    d.year,
    COUNT(f.track_key) AS tracks,
    ROUND(AVG(f.duration_seconds), 2) AS duracion_promedio
FROM gold.fact_tracks f
JOIN gold.dim_date d ON f.date_key = d.date_key
WHERE f.date_key BETWEEN 20200101 AND 20241231
GROUP BY d.year;