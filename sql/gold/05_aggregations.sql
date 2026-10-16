-- ============================================================================
-- PROYECTO: DWMusicBrainz (Data Warehouse Masivo de la Industria Musical)
-- CAPA: Gold / Vistas Materializadas y Agregaciones Analíticas (Power BI)
-- ARCHIVO: 05_aggregations.sql
-- DESCRIPCIÓN: Vistas materializadas en español basadas 100% en SUM de métricas aditivas
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 1. RF01 & RF05: TENDENCIAS TEMPORALES DE PRODUCCIÓN MUSICAL POR AÑO Y DÉCADA
-- ----------------------------------------------------------------------------
CREATE MATERIALIZED VIEW IF NOT EXISTS gold.mv_tendencias_produccion_anual AS
SELECT 
    d.anio,
    d.decada,
    d.siglo,
    SUM(f.lanzamientos_total) AS lanzamientos_total,
    SUM(f.soportes_total) AS soportes_total,
    SUM(f.pistas_total) AS pistas_total,
    COUNT(DISTINCT f.artista_key) AS artistas_activos,
    ROUND(SUM(f.duracion_total_minutos), 2) AS duracion_total_minutos,
    ROUND(
        SUM(f.duracion_total_segundos) / NULLIF(SUM(f.pistas_completas_total), 0),
        2
    ) AS duracion_promedio_segundos,
    SUM(f.pistas_con_isrc_total) AS pistas_con_isrc_total,
    SUM(f.pistas_largas_total) AS pistas_largas_total,
    SUM(f.pistas_video_total) AS pistas_video_total,
    ROUND(
        SUM(f.pistas_con_isrc_total) * 100.0 / NULLIF(SUM(f.pistas_total), 0),
        2
    ) AS cobertura_isrc_pct
FROM gold.fact_produccion_musical f
JOIN gold.dim_fecha d ON f.fecha_key = d.fecha_key
WHERE d.anio BETWEEN 1950 AND 2026
GROUP BY d.anio, d.decada, d.siglo
ORDER BY d.anio
WITH NO DATA;

CREATE UNIQUE INDEX IF NOT EXISTS uq_mv_tendencias_anio ON gold.mv_tendencias_produccion_anual(anio);
CREATE INDEX IF NOT EXISTS idx_mv_tendencias_decada ON gold.mv_tendencias_produccion_anual(decada);

-- ----------------------------------------------------------------------------
-- 2. RF01, RF06 & RF08: ANALÍTICA AVANZADA DE ARTISTAS Y VOLUMETRÍA
-- ----------------------------------------------------------------------------
CREATE MATERIALIZED VIEW IF NOT EXISTS gold.mv_analitica_artistas AS
SELECT 
    a.artista_key,
    a.artista_id,
    a.nombre_artista,
    a.tipo_artista,
    a.genero,
    a.nombre_pais,
    a.anio_inicio,
    SUM(f.lanzamientos_total) AS lanzamientos_total,
    SUM(f.soportes_total) AS soportes_total,
    SUM(f.pistas_total) AS pistas_total,
    ROUND(SUM(f.duracion_total_minutos), 2) AS duracion_total_minutos,
    ROUND(
        SUM(f.duracion_total_segundos) / NULLIF(SUM(f.pistas_completas_total), 0),
        2
    ) AS duracion_promedio_segundos,
    SUM(f.pistas_con_isrc_total) AS pistas_con_isrc_total,
    SUM(f.pistas_largas_total) AS pistas_largas_total,
    ROUND(
        SUM(f.pistas_con_isrc_total) * 100.0 / NULLIF(SUM(f.pistas_total), 0),
        2
    ) AS cobertura_isrc_pct
FROM gold.fact_produccion_musical f
JOIN gold.dim_artista a ON f.artista_key = a.artista_key
GROUP BY 
    a.artista_key, a.artista_id, a.nombre_artista, a.tipo_artista, 
    a.genero, a.nombre_pais, a.anio_inicio
WITH NO DATA;

CREATE UNIQUE INDEX IF NOT EXISTS uq_mv_analitica_artistas_key ON gold.mv_analitica_artistas(artista_key);
CREATE INDEX IF NOT EXISTS idx_mv_analitica_artistas_pais ON gold.mv_analitica_artistas(nombre_pais);
CREATE INDEX IF NOT EXISTS idx_mv_analitica_artistas_pistas ON gold.mv_analitica_artistas(pistas_total DESC);

-- ----------------------------------------------------------------------------
-- 3. RF02 & RF04: EVOLUCIÓN DE FORMATOS (VINILOS, CDS, DIGITAL MEDIA, CASSETTES)
-- ----------------------------------------------------------------------------
CREATE MATERIALIZED VIEW IF NOT EXISTS gold.mv_evolucion_formatos AS
SELECT 
    d.anio,
    d.decada,
    fmt.nombre_formato,
    fmt.categoria_formato,
    SUM(f.lanzamientos_total) AS lanzamientos_total,
    SUM(f.soportes_total) AS soportes_total,
    SUM(f.pistas_total) AS pistas_total,
    SUM(f.pistas_largas_total) AS pistas_largas_total,
    ROUND(SUM(f.duracion_total_minutos), 2) AS duracion_total_minutos,
    ROUND(
        SUM(f.duracion_total_segundos) / NULLIF(SUM(f.pistas_completas_total), 0),
        2
    ) AS duracion_promedio_segundos
FROM gold.fact_produccion_musical f
JOIN gold.dim_fecha d ON f.fecha_key = d.fecha_key
JOIN gold.dim_formato fmt ON f.formato_key = fmt.formato_key
WHERE d.anio BETWEEN 1950 AND 2026
GROUP BY d.anio, d.decada, fmt.nombre_formato, fmt.categoria_formato
WITH NO DATA;

CREATE UNIQUE INDEX IF NOT EXISTS uq_mv_evolucion_formatos ON gold.mv_evolucion_formatos(anio, nombre_formato);
CREATE INDEX IF NOT EXISTS idx_mv_evolucion_formatos_cat ON gold.mv_evolucion_formatos(categoria_formato);

-- ----------------------------------------------------------------------------
-- 4. RF03 & RF06: DISTRIBUCIÓN GEOGRÁFICA Y FORMALIZACIÓN SONORA
-- ----------------------------------------------------------------------------
CREATE MATERIALIZED VIEW IF NOT EXISTS gold.mv_distribucion_geografica AS
SELECT 
    g.geografia_key,
    g.nombre_pais,
    g.nombre_area,
    g.tipo_area,
    COUNT(DISTINCT f.artista_key) AS artistas_total,
    SUM(f.lanzamientos_total) AS lanzamientos_total,
    SUM(f.soportes_total) AS soportes_total,
    SUM(f.pistas_total) AS pistas_total,
    SUM(f.pistas_con_isrc_total) AS pistas_con_isrc_total,
    ROUND(SUM(f.duracion_total_minutos) / 60.0, 2) AS duracion_total_horas
FROM gold.fact_produccion_musical f
JOIN gold.dim_geografia g ON f.geografia_key = g.geografia_key
GROUP BY g.geografia_key, g.nombre_pais, g.nombre_area, g.tipo_area
WITH NO DATA;

CREATE UNIQUE INDEX IF NOT EXISTS uq_mv_dist_geo_key ON gold.mv_distribucion_geografica(geografia_key);
CREATE INDEX IF NOT EXISTS idx_mv_dist_geo_pais ON gold.mv_distribucion_geografica(nombre_pais);