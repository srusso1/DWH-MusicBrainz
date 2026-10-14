-- ============================================================================
-- PROYECTO: DWMusicBrainz (Data Warehouse Masivo de la Industria Musical)
-- CAPA: Gold / Modelo en Estrella Puro (Ralph Kimball Standard)
-- ARCHIVO: 03_dimensions_facts.sql
-- DESCRIPCIÓN: DDL de las 6 Dimensiones Conformadas y Tabla de Hechos Central
-- ============================================================================

CREATE SCHEMA IF NOT EXISTS gold;

-- ----------------------------------------------------------------------------
-- 1. DIMENSIÓN CONFORMADA: gold.dim_date (Granularidad diaria)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS gold.dim_date (
    date_key            INTEGER PRIMARY KEY,         -- YYYYMMDD (Ej: 20210515, o 0 para Sin Fecha)
    full_date           DATE,
    year                INTEGER NOT NULL,
    quarter             INTEGER NOT NULL,            -- 1, 2, 3, 4
    quarter_name        VARCHAR(10) NOT NULL,        -- 'Q1', 'Q2', 'Q3', 'Q4'
    month               INTEGER NOT NULL,            -- 1 a 12
    month_name          VARCHAR(20) NOT NULL,        -- 'Enero', 'Febrero', etc.
    month_name_short    CHAR(3) NOT NULL,            -- 'Ene', 'Feb', etc.
    day                 INTEGER NOT NULL,
    day_of_week         INTEGER NOT NULL,            -- 1 (Lunes) a 7 (Domingo)
    day_name            VARCHAR(20) NOT NULL,        -- 'Lunes', 'Martes', etc.
    is_weekend          BOOLEAN NOT NULL,
    decade              VARCHAR(20) NOT NULL,        -- '1970s', '1980s', '2020s'
    century             VARCHAR(20) NOT NULL         -- 'Siglo XX', 'Siglo XXI'
);

CREATE INDEX IF NOT EXISTS idx_dim_date_year ON gold.dim_date(year);
CREATE INDEX IF NOT EXISTS idx_dim_date_decade ON gold.dim_date(decade);

-- ----------------------------------------------------------------------------
-- 2. DIMENSIÓN CONFORMADA: gold.dim_artist (SCD Tipo 1 / Tipo 2 Híbrido)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS gold.dim_artist (
    artist_key          SERIAL PRIMARY KEY,          -- Surrogate Key
    artist_id           INTEGER NOT NULL,            -- Business Key (MusicBrainz ID)
    artist_gid          UUID NOT NULL,               -- GID Universal
    artist_name         VARCHAR(1000) NOT NULL,
    sort_name           VARCHAR(1000),
    artist_type         VARCHAR(100) NOT NULL DEFAULT 'Desconocido', -- Solista, Grupo, Orquesta, etc.
    gender              VARCHAR(50) NOT NULL DEFAULT 'Desconocido',  -- Masculino, Femenino, etc.
    area_name           VARCHAR(1000) DEFAULT 'Sin Área Registrada',
    country_name        VARCHAR(1000) DEFAULT 'Sin País Registrado',
    begin_year          SMALLINT,
    end_year            SMALLINT,
    is_ended            BOOLEAN DEFAULT FALSE,
    created_at          TIMESTAMPTZ DEFAULT clock_timestamp()
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_dim_artist_id ON gold.dim_artist(artist_id);
CREATE INDEX IF NOT EXISTS idx_dim_artist_name ON gold.dim_artist(artist_name);
CREATE INDEX IF NOT EXISTS idx_dim_artist_country ON gold.dim_artist(country_name);
CREATE INDEX IF NOT EXISTS idx_dim_artist_type ON gold.dim_artist(artist_type);

-- ----------------------------------------------------------------------------
-- 3. DIMENSIÓN CONFORMADA: gold.dim_geography (Jerarquía Geográfica Normalizada)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS gold.dim_geography (
    geo_key             SERIAL PRIMARY KEY,          -- Surrogate Key
    area_id             INTEGER NOT NULL,            -- Business Key
    area_gid            UUID NOT NULL,
    area_name           VARCHAR(1000) NOT NULL,
    area_type           VARCHAR(100) NOT NULL DEFAULT 'Desconocido', -- Country, City, Subdivision, etc.
    country_name        VARCHAR(1000) DEFAULT 'No Aplica',
    created_at          TIMESTAMPTZ DEFAULT clock_timestamp()
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_dim_geo_area_id ON gold.dim_geography(area_id);
CREATE INDEX IF NOT EXISTS idx_dim_geo_country ON gold.dim_geography(country_name);
CREATE INDEX IF NOT EXISTS idx_dim_geo_type ON gold.dim_geography(area_type);

-- ----------------------------------------------------------------------------
-- 4. DIMENSIÓN CONFORMADA: gold.dim_release (Álbumes / Lanzamientos)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS gold.dim_release (
    release_key         SERIAL PRIMARY KEY,          -- Surrogate Key
    release_id          INTEGER NOT NULL,            -- Business Key
    release_gid         UUID NOT NULL,
    release_name        VARCHAR(1000) NOT NULL,
    release_status      VARCHAR(100) NOT NULL DEFAULT 'Oficial', -- Oficial, Promocional, Bootleg, etc.
    packaging_type      VARCHAR(100) NOT NULL DEFAULT 'Estándar',-- Jewel Case, Digipak, Vinilo, etc.
    barcode             VARCHAR(255),
    quality             VARCHAR(50) NOT NULL DEFAULT 'Normal',
    created_at          TIMESTAMPTZ DEFAULT clock_timestamp()
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_dim_release_id ON gold.dim_release(release_id);
CREATE INDEX IF NOT EXISTS idx_dim_release_name ON gold.dim_release(release_name);
CREATE INDEX IF NOT EXISTS idx_dim_release_status ON gold.dim_release(release_status);

-- ----------------------------------------------------------------------------
-- 5. DIMENSIÓN CONFORMADA: gold.dim_format (Formato Físico / Digital del Medio)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS gold.dim_format (
    format_key          SERIAL PRIMARY KEY,          -- Surrogate Key
    format_id           INTEGER NOT NULL,            -- Business Key
    format_name         VARCHAR(100) NOT NULL,       -- CD, 12" Vinyl, Digital Media, Cassette, etc.
    category            VARCHAR(100) NOT NULL DEFAULT 'Otros' -- Físico, Digital, Óptico, Magnético
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_dim_format_id ON gold.dim_format(format_id);

-- ----------------------------------------------------------------------------
-- 6. DIMENSIÓN CONFORMADA: gold.dim_language (Idioma y Script de Publicación)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS gold.dim_language (
    language_key        SERIAL PRIMARY KEY,          -- Surrogate Key
    language_id         INTEGER NOT NULL,            -- Business Key
    language_name       VARCHAR(100) NOT NULL,       -- Inglés, Español, Japonés, Francés, etc.
    iso_code            VARCHAR(10) DEFAULT 'und'
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_dim_language_id ON gold.dim_language(language_id);

-- ----------------------------------------------------------------------------
-- 7. TABLA DE HECHOS CENTRAL: gold.fact_tracks (Particionada por Rango de Fecha)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS gold.fact_tracks (
    track_key           BIGSERIAL,
    date_key            INTEGER NOT NULL,            -- FK -> dim_date (Clave de partición)
    artist_key          INTEGER NOT NULL,            -- FK -> dim_artist
    release_key         INTEGER NOT NULL,            -- FK -> dim_release
    geo_key             INTEGER NOT NULL,            -- FK -> dim_geography
    format_key          INTEGER NOT NULL,            -- FK -> dim_format
    language_key        INTEGER NOT NULL,            -- FK -> dim_language
    
    -- Dimensiones Degeneradas y Claves de Negocio
    track_id            INTEGER NOT NULL,
    track_gid           UUID NOT NULL,
    recording_id        INTEGER NOT NULL,
    recording_gid       UUID NOT NULL,
    track_name          VARCHAR(1000) NOT NULL,
    track_number        VARCHAR(50),
    position            INTEGER,
    isrc_code           VARCHAR(15),
    has_isrc            BOOLEAN DEFAULT FALSE,
    is_video            BOOLEAN DEFAULT FALSE,
    
    -- Métricas Aditivas y Semiaditivas
    duration_ms         INTEGER DEFAULT 0,
    duration_seconds    NUMERIC(10, 2) DEFAULT 0.00,
    duration_minutes    NUMERIC(10, 2) DEFAULT 0.00,
    track_count         INTEGER NOT NULL DEFAULT 1,
    is_complete         SMALLINT NOT NULL DEFAULT 1,
    
    PRIMARY KEY (track_key, date_key)
) PARTITION BY RANGE (date_key);

COMMENT ON SCHEMA gold IS 'Capa Gold: Esquema en Estrella Puro (Ralph Kimball) para Business Intelligence y Analítica.';
COMMENT ON TABLE gold.fact_tracks IS 'Tabla de hechos de tracks musicales con métricas de duración y conteos.';