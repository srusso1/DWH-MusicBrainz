-- ============================================================================
-- PROYECTO: DWMusicBrainz (Data Warehouse Masivo de la Industria Musical)
-- CAPA: Gold / Vistas Materializadas y Agregaciones Analíticas (Power BI)
-- ARCHIVO: 05_aggregations.sql
-- DESCRIPCIÓN: Vistas materializadas indexadas para acelerar consultas analíticas
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 1. RF01: TENDENCIAS TEMPORALES DE PRODUCCIÓN MUSICAL POR AÑO Y DÉCADA
-- ----------------------------------------------------------------------------
CREATE MATERIALIZED VIEW IF NOT EXISTS gold.mv_yearly_production_trends AS
SELECT 
    d.year,
    d.decade,
    d.century,
    COUNT(f.track_key) AS total_tracks,
    COUNT(DISTINCT f.artist_key) AS active_artists,
    COUNT(DISTINCT f.release_key) AS total_releases,
    ROUND(SUM(f.duration_minutes), 2) AS total_duration_minutes,
    ROUND(AVG(f.duration_seconds), 2) AS avg_track_duration_seconds,
    COUNT(CASE WHEN f.has_isrc THEN 1 END) AS tracks_with_isrc,
    ROUND(COUNT(CASE WHEN f.has_isrc THEN 1 END) * 100.0 / NULLIF(COUNT(f.track_key), 0), 2) AS isrc_coverage_pct
FROM gold.fact_tracks f
JOIN gold.dim_date d ON f.date_key = d.date_key
WHERE d.year BETWEEN 1950 AND 2026
GROUP BY d.year, d.decade, d.century
ORDER BY d.year
WITH NO DATA;

CREATE UNIQUE INDEX IF NOT EXISTS uq_mv_yearly_trends_year ON gold.mv_yearly_production_trends(year);
CREATE INDEX IF NOT EXISTS idx_mv_yearly_trends_decade ON gold.mv_yearly_production_trends(decade);

-- ----------------------------------------------------------------------------
-- 2. RF02 & RF06: ANALÍTICA AVANZADA DE ARTISTAS Y VOLUMETRÍA
-- ----------------------------------------------------------------------------
CREATE MATERIALIZED VIEW IF NOT EXISTS gold.mv_artist_analytics AS
SELECT 
    a.artist_key,
    a.artist_id,
    a.artist_name,
    a.artist_type,
    a.gender,
    a.country_name,
    a.begin_year,
    COUNT(f.track_key) AS total_tracks,
    COUNT(DISTINCT f.release_key) AS total_releases,
    ROUND(SUM(f.duration_minutes), 2) AS total_duration_minutes,
    ROUND(AVG(f.duration_seconds), 2) AS avg_track_duration_seconds,
    COUNT(CASE WHEN f.has_isrc THEN 1 END) AS tracks_with_isrc
FROM gold.fact_tracks f
JOIN gold.dim_artist a ON f.artist_key = a.artist_key
GROUP BY 
    a.artist_key, a.artist_id, a.artist_name, a.artist_type, 
    a.gender, a.country_name, a.begin_year
WITH NO DATA;

CREATE UNIQUE INDEX IF NOT EXISTS uq_mv_artist_analytics_key ON gold.mv_artist_analytics(artist_key);
CREATE INDEX IF NOT EXISTS idx_mv_artist_analytics_country ON gold.mv_artist_analytics(country_name);
CREATE INDEX IF NOT EXISTS idx_mv_artist_analytics_tracks ON gold.mv_artist_analytics(total_tracks DESC);

-- ----------------------------------------------------------------------------
-- 3. RF03: EVOLUCIÓN DE FORMATOS (VINILOS, CDS, DIGITAL MEDIA, CASSETTES)
-- ----------------------------------------------------------------------------
CREATE MATERIALIZED VIEW IF NOT EXISTS gold.mv_format_evolution AS
SELECT 
    d.year,
    d.decade,
    fmt.format_name,
    fmt.category AS format_category,
    COUNT(f.track_key) AS total_tracks,
    COUNT(DISTINCT f.release_key) AS total_releases,
    ROUND(SUM(f.duration_minutes), 2) AS total_duration_minutes
FROM gold.fact_tracks f
JOIN gold.dim_date d ON f.date_key = d.date_key
JOIN gold.dim_format fmt ON f.format_key = fmt.format_key
WHERE d.year BETWEEN 1950 AND 2026
GROUP BY d.year, d.decade, fmt.format_name, fmt.category
WITH NO DATA;

CREATE UNIQUE INDEX IF NOT EXISTS uq_mv_format_evolution ON gold.mv_format_evolution(year, format_name);
CREATE INDEX IF NOT EXISTS idx_mv_format_evolution_cat ON gold.mv_format_evolution(format_category);

-- ----------------------------------------------------------------------------
-- 4. RF04 & RF07: DISTRIBUCIÓN GEOGRÁFICA Y DE IDIOMAS
-- ----------------------------------------------------------------------------
CREATE MATERIALIZED VIEW IF NOT EXISTS gold.mv_geography_distribution AS
SELECT 
    g.geo_key,
    g.country_name,
    g.area_type,
    COUNT(DISTINCT f.artist_key) AS total_artists,
    COUNT(f.track_key) AS total_tracks,
    ROUND(SUM(f.duration_minutes) / 60.0, 2) AS total_duration_hours
FROM gold.fact_tracks f
JOIN gold.dim_geography g ON f.geo_key = g.geo_key
GROUP BY g.geo_key, g.country_name, g.area_type
WITH NO DATA;

CREATE UNIQUE INDEX IF NOT EXISTS uq_mv_geo_distribution_key ON gold.mv_geography_distribution(geo_key);
CREATE INDEX IF NOT EXISTS idx_mv_geo_distribution_country ON gold.mv_geography_distribution(country_name);