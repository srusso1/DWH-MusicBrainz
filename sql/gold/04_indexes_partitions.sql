-- ============================================================================
-- PROYECTO: DWMusicBrainz (Data Warehouse Masivo de la Industria Musical)
-- CAPA: Gold / Particionamiento Físico e Índices Analíticos
-- ARCHIVO: 04_indexes_partitions.sql
-- DESCRIPCIÓN: Particionamiento por Rango de Fecha e Índices B-Tree Optimizados
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 1. PARTICIONAMIENTO FÍSICO DE gold.fact_tracks POR RANGO DE date_key
-- ----------------------------------------------------------------------------

-- Partición para registros sin fecha conocida o fecha 0
CREATE TABLE IF NOT EXISTS gold.fact_tracks_unknown 
    PARTITION OF gold.fact_tracks 
    FOR VALUES FROM (0) TO (19000101);

-- Partición histórica previa a 1970
CREATE TABLE IF NOT EXISTS gold.fact_tracks_pre_1970 
    PARTITION OF gold.fact_tracks 
    FOR VALUES FROM (19000101) TO (19700101);

-- Década de 1970
CREATE TABLE IF NOT EXISTS gold.fact_tracks_1970s 
    PARTITION OF gold.fact_tracks 
    FOR VALUES FROM (19700101) TO (19800101);

-- Década de 1980
CREATE TABLE IF NOT EXISTS gold.fact_tracks_1980s 
    PARTITION OF gold.fact_tracks 
    FOR VALUES FROM (19800101) TO (19900101);

-- Década de 1990
CREATE TABLE IF NOT EXISTS gold.fact_tracks_1990s 
    PARTITION OF gold.fact_tracks 
    FOR VALUES FROM (19900101) TO (20000101);

-- Década de 2000
CREATE TABLE IF NOT EXISTS gold.fact_tracks_2000s 
    PARTITION OF gold.fact_tracks 
    FOR VALUES FROM (20000101) TO (20100101);

-- Década de 2010
CREATE TABLE IF NOT EXISTS gold.fact_tracks_2010s 
    PARTITION OF gold.fact_tracks 
    FOR VALUES FROM (20100101) TO (20200101);

-- Años recientes anuales de alta densidad (2020 a 2026)
CREATE TABLE IF NOT EXISTS gold.fact_tracks_2020 
    PARTITION OF gold.fact_tracks 
    FOR VALUES FROM (20200101) TO (20210101);

CREATE TABLE IF NOT EXISTS gold.fact_tracks_2021 
    PARTITION OF gold.fact_tracks 
    FOR VALUES FROM (20210101) TO (20220101);

CREATE TABLE IF NOT EXISTS gold.fact_tracks_2022 
    PARTITION OF gold.fact_tracks 
    FOR VALUES FROM (20220101) TO (20230101);

CREATE TABLE IF NOT EXISTS gold.fact_tracks_2023 
    PARTITION OF gold.fact_tracks 
    FOR VALUES FROM (20230101) TO (20240101);

CREATE TABLE IF NOT EXISTS gold.fact_tracks_2024 
    PARTITION OF gold.fact_tracks 
    FOR VALUES FROM (20240101) TO (20250101);

CREATE TABLE IF NOT EXISTS gold.fact_tracks_2025 
    PARTITION OF gold.fact_tracks 
    FOR VALUES FROM (20250101) TO (20260101);

CREATE TABLE IF NOT EXISTS gold.fact_tracks_2026_plus 
    PARTITION OF gold.fact_tracks 
    FOR VALUES FROM (20260101) TO (20300101);

-- Partición por defecto para evitar rechazos en ingestiones imprevistas
CREATE TABLE IF NOT EXISTS gold.fact_tracks_default 
    PARTITION OF gold.fact_tracks 
    DEFAULT;

-- ----------------------------------------------------------------------------
-- 2. ÍNDICES B-TREE EN LA TABLA DE HECHOS (Propagados a todas las particiones)
-- ----------------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_fact_tracks_artist ON gold.fact_tracks(artist_key);
CREATE INDEX IF NOT EXISTS idx_fact_tracks_release ON gold.fact_tracks(release_key);
CREATE INDEX IF NOT EXISTS idx_fact_tracks_geo ON gold.fact_tracks(geo_key);
CREATE INDEX IF NOT EXISTS idx_fact_tracks_format ON gold.fact_tracks(format_key);
CREATE INDEX IF NOT EXISTS idx_fact_tracks_language ON gold.fact_tracks(language_key);
CREATE INDEX IF NOT EXISTS idx_fact_tracks_date ON gold.fact_tracks(date_key);
CREATE INDEX IF NOT EXISTS idx_fact_tracks_recording_id ON gold.fact_tracks(recording_id);
CREATE INDEX IF NOT EXISTS idx_fact_tracks_track_id ON gold.fact_tracks(track_id);