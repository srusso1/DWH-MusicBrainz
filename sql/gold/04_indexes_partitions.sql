-- ============================================================================
-- PROYECTO: DWMusicBrainz (Data Warehouse Masivo de la Industria Musical)
-- CAPA: Gold / Particionamiento Físico e Índices Analíticos
-- ARCHIVO: 04_indexes_partitions.sql
-- DESCRIPCIÓN: Particionamiento por Rango de fecha_key e Índices B-Tree Optimizados
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 1. PARTICIONAMIENTO FÍSICO DE gold.fact_produccion_musical POR RANGO DE fecha_key
-- ----------------------------------------------------------------------------

-- Partición para registros sin fecha conocida o fecha 0
CREATE TABLE IF NOT EXISTS gold.fact_produccion_unknown 
    PARTITION OF gold.fact_produccion_musical 
    FOR VALUES FROM (0) TO (19000101);

-- Partición histórica previa a 1970
CREATE TABLE IF NOT EXISTS gold.fact_produccion_pre_1970 
    PARTITION OF gold.fact_produccion_musical 
    FOR VALUES FROM (19000101) TO (19700101);

-- Década de 1970
CREATE TABLE IF NOT EXISTS gold.fact_produccion_1970s 
    PARTITION OF gold.fact_produccion_musical 
    FOR VALUES FROM (19700101) TO (19800101);

-- Década de 1980
CREATE TABLE IF NOT EXISTS gold.fact_produccion_1980s 
    PARTITION OF gold.fact_produccion_musical 
    FOR VALUES FROM (19800101) TO (19900101);

-- Década de 1990
CREATE TABLE IF NOT EXISTS gold.fact_produccion_1990s 
    PARTITION OF gold.fact_produccion_musical 
    FOR VALUES FROM (19900101) TO (20000101);

-- Década de 2000
CREATE TABLE IF NOT EXISTS gold.fact_produccion_2000s 
    PARTITION OF gold.fact_produccion_musical 
    FOR VALUES FROM (20000101) TO (20100101);

-- Década de 2010
CREATE TABLE IF NOT EXISTS gold.fact_produccion_2010s 
    PARTITION OF gold.fact_produccion_musical 
    FOR VALUES FROM (20100101) TO (20200101);

-- Años recientes anuales de alta densidad (2020 a 2026)
CREATE TABLE IF NOT EXISTS gold.fact_produccion_2020 
    PARTITION OF gold.fact_produccion_musical 
    FOR VALUES FROM (20200101) TO (20210101);

CREATE TABLE IF NOT EXISTS gold.fact_produccion_2021 
    PARTITION OF gold.fact_produccion_musical 
    FOR VALUES FROM (20210101) TO (20220101);

CREATE TABLE IF NOT EXISTS gold.fact_produccion_2022 
    PARTITION OF gold.fact_produccion_musical 
    FOR VALUES FROM (20220101) TO (20230101);

CREATE TABLE IF NOT EXISTS gold.fact_produccion_2023 
    PARTITION OF gold.fact_produccion_musical 
    FOR VALUES FROM (20230101) TO (20240101);

CREATE TABLE IF NOT EXISTS gold.fact_produccion_2024 
    PARTITION OF gold.fact_produccion_musical 
    FOR VALUES FROM (20240101) TO (20250101);

CREATE TABLE IF NOT EXISTS gold.fact_produccion_2025 
    PARTITION OF gold.fact_produccion_musical 
    FOR VALUES FROM (20250101) TO (20260101);

CREATE TABLE IF NOT EXISTS gold.fact_produccion_2026_plus 
    PARTITION OF gold.fact_produccion_musical 
    FOR VALUES FROM (20260101) TO (20310101);

-- Partición por defecto para evitar rechazos en ingestiones imprevistas
CREATE TABLE IF NOT EXISTS gold.fact_produccion_default 
    PARTITION OF gold.fact_produccion_musical 
    DEFAULT;

-- ----------------------------------------------------------------------------
-- 2. ÍNDICES B-TREE EN LA TABLA DE HECHOS (Propagados a todas las particiones)
-- ----------------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_fact_prod_artista ON gold.fact_produccion_musical(artista_key);
CREATE INDEX IF NOT EXISTS idx_fact_prod_lanzamiento ON gold.fact_produccion_musical(lanzamiento_key);
CREATE INDEX IF NOT EXISTS idx_fact_prod_geografia ON gold.fact_produccion_musical(geografia_key);
CREATE INDEX IF NOT EXISTS idx_fact_prod_formato ON gold.fact_produccion_musical(formato_key);
CREATE INDEX IF NOT EXISTS idx_fact_prod_idioma ON gold.fact_produccion_musical(idioma_key);
CREATE INDEX IF NOT EXISTS idx_fact_prod_fecha ON gold.fact_produccion_musical(fecha_key);