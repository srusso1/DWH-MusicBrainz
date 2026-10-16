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
SELECT 'silver.artist_credit_name', COUNT(*) FROM silver.artist_credit_name
UNION ALL
SELECT 'silver.release', COUNT(*) FROM silver.release
UNION ALL
SELECT 'silver.release_country', COUNT(*) FROM silver.release_country
UNION ALL
SELECT 'silver.release_unknown_country', COUNT(*) FROM silver.release_unknown_country
UNION ALL
SELECT 'silver.medium', COUNT(*) FROM silver.medium
UNION ALL
SELECT 'silver.recording', COUNT(*) FROM silver.recording
UNION ALL
SELECT 'silver.track', COUNT(*) FROM silver.track
UNION ALL
SELECT 'silver.isrc', COUNT(*) FROM silver.isrc
UNION ALL
SELECT 'gold.dim_fecha', COUNT(*) FROM gold.dim_fecha
UNION ALL
SELECT 'gold.dim_artista', COUNT(*) FROM gold.dim_artista
UNION ALL
SELECT 'gold.dim_geografia', COUNT(*) FROM gold.dim_geografia
UNION ALL
SELECT 'gold.dim_lanzamiento', COUNT(*) FROM gold.dim_lanzamiento
UNION ALL
SELECT 'gold.dim_formato', COUNT(*) FROM gold.dim_formato
UNION ALL
SELECT 'gold.dim_idioma', COUNT(*) FROM gold.dim_idioma
UNION ALL
SELECT 'gold.fact_produccion_musical', COUNT(*) FROM gold.fact_produccion_musical;

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
-- PRUEBA 3: INTEGRIDAD REFERENCIAL KIMBALL (Cero Huérfanos en fact_produccion_musical)
-- ----------------------------------------------------------------------------
SELECT 'Huérfanos en dim_artista' AS test_name, COUNT(*) AS violaciones
FROM gold.fact_produccion_musical f
LEFT JOIN gold.dim_artista a ON f.artista_key = a.artista_key
WHERE a.artista_key IS NULL
UNION ALL
SELECT 'Huérfanos en dim_fecha', COUNT(*)
FROM gold.fact_produccion_musical f
LEFT JOIN gold.dim_fecha d ON f.fecha_key = d.fecha_key
WHERE d.fecha_key IS NULL
UNION ALL
SELECT 'Huérfanos en dim_lanzamiento', COUNT(*)
FROM gold.fact_produccion_musical f
LEFT JOIN gold.dim_lanzamiento r ON f.lanzamiento_key = r.lanzamiento_key
WHERE r.lanzamiento_key IS NULL
UNION ALL
SELECT 'Huérfanos en dim_formato', COUNT(*)
FROM gold.fact_produccion_musical f
LEFT JOIN gold.dim_formato fmt ON f.formato_key = fmt.formato_key
WHERE fmt.formato_key IS NULL
UNION ALL
SELECT 'Huérfanos en dim_geografia', COUNT(*)
FROM gold.fact_produccion_musical f
LEFT JOIN gold.dim_geografia g ON f.geografia_key = g.geografia_key
WHERE g.geografia_key IS NULL
UNION ALL
SELECT 'Huérfanos en dim_idioma', COUNT(*)
FROM gold.fact_produccion_musical f
LEFT JOIN gold.dim_idioma l ON f.idioma_key = l.idioma_key
WHERE l.idioma_key IS NULL;

-- ----------------------------------------------------------------------------
-- PRUEBA 4: VERIFICACIÓN DE GRANO HISTÓRICO Y MÉTRICAS ADITIVAS
-- ----------------------------------------------------------------------------
SELECT
    SUM(lanzamientos_total) AS total_lanzamientos_consolidados,
    SUM(soportes_total) AS total_soportes_consolidados,
    SUM(pistas_total) AS total_pistas_consolidadas,
    SUM(pistas_con_isrc_total) AS total_pistas_con_isrc,
    SUM(pistas_largas_total) AS total_pistas_largas,
    ROUND(SUM(duracion_total_minutos) / 60.0, 2) AS total_horas_musica
FROM gold.fact_produccion_musical;

-- ----------------------------------------------------------------------------
-- PRUEBA 5: PRUNING DE PARTICIONES (EXPLAIN ANALYZE)
-- ----------------------------------------------------------------------------
EXPLAIN ANALYZE
SELECT 
    d.anio,
    SUM(f.lanzamientos_total) AS lanzamientos,
    SUM(f.pistas_total) AS pistas,
    ROUND(SUM(f.duracion_total_segundos) / NULLIF(SUM(f.pistas_completas_total), 0), 2) AS duracion_promedio_seg
FROM gold.fact_produccion_musical f
JOIN gold.dim_fecha d ON f.fecha_key = d.fecha_key
WHERE f.fecha_key BETWEEN 20200101 AND 20241231
GROUP BY d.anio;