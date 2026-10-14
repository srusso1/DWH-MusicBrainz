-- ============================================================================
-- PROYECTO: DWMusicBrainz (Data Warehouse Masivo de la Industria Musical)
-- CAPA: Silver / Tablas Limpias y Normalizadas (Modelo Relacional 3NF de Staging)
-- ARCHIVO: 02_create_silver_tables.sql
-- DESCRIPCIÓN: DDL de tablas Silver estructuradas según el estándar MusicBrainz
-- ============================================================================

CREATE SCHEMA IF NOT EXISTS silver;

-- 1. silver.area (Países, Regiones, Ciudades, Municipios)
CREATE TABLE IF NOT EXISTS silver.area (
    id                  INTEGER PRIMARY KEY,
    gid                 UUID NOT NULL,
    name                VARCHAR(1000) NOT NULL,
    type                INTEGER,
    edits_pending       INTEGER,
    last_updated        TIMESTAMPTZ,
    begin_date_year     SMALLINT,
    begin_date_month    SMALLINT,
    begin_date_day      SMALLINT,
    end_date_year       SMALLINT,
    end_date_month      SMALLINT,
    end_date_day        SMALLINT,
    ended               BOOLEAN,
    comment             VARCHAR(1000)
);

CREATE INDEX IF NOT EXISTS idx_silver_area_type ON silver.area(type);

-- 2. silver.artist (Artistas solistas, Grupos, Bandas, Orquestas)
CREATE TABLE IF NOT EXISTS silver.artist (
    id                  INTEGER PRIMARY KEY,
    gid                 UUID NOT NULL,
    name                VARCHAR(1000) NOT NULL,
    sort_name           VARCHAR(1000) NOT NULL,
    begin_date_year     SMALLINT,
    begin_date_month    SMALLINT,
    begin_date_day      SMALLINT,
    end_date_year       SMALLINT,
    end_date_month      SMALLINT,
    end_date_day        SMALLINT,
    type                INTEGER,
    area                INTEGER,
    gender              INTEGER,
    comment             VARCHAR(1000),
    edits_pending       INTEGER,
    last_updated        TIMESTAMPTZ,
    ended               BOOLEAN,
    begin_area          INTEGER,
    end_area            INTEGER
);

CREATE INDEX IF NOT EXISTS idx_silver_artist_area ON silver.artist(area);
CREATE INDEX IF NOT EXISTS idx_silver_artist_type ON silver.artist(type);

-- 3. silver.release (Álbumes, Singles, EPs, Compilaciones)
CREATE TABLE IF NOT EXISTS silver.release (
    id                  INTEGER PRIMARY KEY,
    gid                 UUID NOT NULL,
    name                VARCHAR(1000) NOT NULL,
    artist_credit       INTEGER NOT NULL,
    release_group       INTEGER NOT NULL,
    status              INTEGER,
    packaging           INTEGER,
    language            INTEGER,
    script              INTEGER,
    barcode             VARCHAR(255),
    comment             VARCHAR(1000),
    edits_pending       INTEGER,
    quality             SMALLINT,
    last_updated        TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_silver_release_artist_credit ON silver.release(artist_credit);
CREATE INDEX IF NOT EXISTS idx_silver_release_group ON silver.release(release_group);

-- 4. silver.medium (Discos físicos o digitales que componen cada release)
CREATE TABLE IF NOT EXISTS silver.medium (
    id                  INTEGER PRIMARY KEY,
    release             INTEGER NOT NULL,
    position            INTEGER NOT NULL,
    format              INTEGER,
    name                VARCHAR(1000),
    edits_pending       INTEGER,
    last_updated        TIMESTAMPTZ,
    track_count         INTEGER
);

CREATE INDEX IF NOT EXISTS idx_silver_medium_release ON silver.medium(release);
CREATE INDEX IF NOT EXISTS idx_silver_medium_format ON silver.medium(format);

-- 5. silver.recording (Grabaciones de audio / master)
CREATE TABLE IF NOT EXISTS silver.recording (
    id                  INTEGER PRIMARY KEY,
    gid                 UUID NOT NULL,
    name                VARCHAR(1000) NOT NULL,
    artist_credit       INTEGER NOT NULL,
    length              INTEGER, -- Duración en milisegundos
    comment             VARCHAR(1000),
    edits_pending       INTEGER,
    last_updated        TIMESTAMPTZ,
    video               BOOLEAN
);

CREATE INDEX IF NOT EXISTS idx_silver_recording_artist_credit ON silver.recording(artist_credit);

-- 6. silver.track (Pistas en un medium con vínculo a grabación)
CREATE TABLE IF NOT EXISTS silver.track (
    id                  INTEGER PRIMARY KEY,
    gid                 UUID NOT NULL,
    recording           INTEGER NOT NULL,
    medium              INTEGER NOT NULL,
    position            INTEGER NOT NULL,
    number              VARCHAR(100) NOT NULL,
    name                VARCHAR(1000) NOT NULL,
    artist_credit       INTEGER NOT NULL,
    length              INTEGER, -- Duración en milisegundos
    edits_pending       INTEGER,
    last_updated        TIMESTAMPTZ,
    is_data_track       BOOLEAN
);

CREATE INDEX IF NOT EXISTS idx_silver_track_recording ON silver.track(recording);
CREATE INDEX IF NOT EXISTS idx_silver_track_medium ON silver.track(medium);
CREATE INDEX IF NOT EXISTS idx_silver_track_artist_credit ON silver.track(artist_credit);

-- 7. silver.isrc (Códigos Estándar Internacional de Grabación de Audio)
CREATE TABLE IF NOT EXISTS silver.isrc (
    id                  INTEGER PRIMARY KEY,
    recording           INTEGER NOT NULL,
    isrc                CHAR(12) NOT NULL,
    source              SMALLINT,
    edits_pending       INTEGER,
    created             TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_silver_isrc_recording ON silver.isrc(recording);

COMMENT ON SCHEMA silver IS 'Capa Silver: Tablas intermedias normalizadas 3NF limpiadas desde los volcados de MusicBrainz.';
