-- ============================================================================
-- PROYECTO: DWMusicBrainz (Data Warehouse Masivo de la Industria Musical)
-- CAPA: Silver / Tablas Limpias y Normalizadas (Modelo Relacional 3NF de Staging)
-- ARCHIVO: 02_create_silver_tables.sql
-- DESCRIPCIÓN: DDL de tablas Silver estructuradas según el estándar MusicBrainz
--              (Schema Sequence 31) con soporte nativo TEXT y tablas de vínculo
--              histórico de fechas (release_country / release_unknown_country)
--              y créditos de artistas (artist_credit_name).
-- ============================================================================

CREATE SCHEMA IF NOT EXISTS silver;

-- 1. silver.area (Países, Regiones, Ciudades, Municipios)
CREATE TABLE IF NOT EXISTS silver.area (
    id                  INTEGER PRIMARY KEY,
    gid                 UUID NOT NULL,
    name                TEXT NOT NULL,
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
    comment             TEXT
);

CREATE INDEX IF NOT EXISTS idx_silver_area_type ON silver.area(type);

-- 2. silver.artist (Artistas solistas, Grupos, Bandas, Orquestas)
CREATE TABLE IF NOT EXISTS silver.artist (
    id                  INTEGER PRIMARY KEY,
    gid                 UUID NOT NULL,
    name                TEXT NOT NULL,
    sort_name           TEXT NOT NULL,
    begin_date_year     SMALLINT,
    begin_date_month    SMALLINT,
    begin_date_day      SMALLINT,
    end_date_year       SMALLINT,
    end_date_month      SMALLINT,
    end_date_day        SMALLINT,
    type                INTEGER,
    area                INTEGER,
    gender              INTEGER,
    comment             TEXT,
    edits_pending       INTEGER,
    last_updated        TIMESTAMPTZ,
    ended               BOOLEAN,
    begin_area          INTEGER,
    end_area            INTEGER
);

CREATE INDEX IF NOT EXISTS idx_silver_artist_area ON silver.artist(area);
CREATE INDEX IF NOT EXISTS idx_silver_artist_type ON silver.artist(type);

-- 3. silver.artist_credit_name (Resolución de artist_credit -> artist.id real)
CREATE TABLE IF NOT EXISTS silver.artist_credit_name (
    artist_credit       INTEGER NOT NULL,
    position            SMALLINT NOT NULL,
    artist              INTEGER NOT NULL,
    name                TEXT NOT NULL,
    join_phrase         TEXT,
    PRIMARY KEY (artist_credit, position)
);

CREATE INDEX IF NOT EXISTS idx_silver_acn_artist ON silver.artist_credit_name(artist);

-- 4. silver.release (Álbumes, Singles, EPs, Compilaciones)
CREATE TABLE IF NOT EXISTS silver.release (
    id                  INTEGER PRIMARY KEY,
    gid                 UUID NOT NULL,
    name                TEXT NOT NULL,
    artist_credit       INTEGER NOT NULL,
    release_group       INTEGER NOT NULL,
    status              INTEGER,
    packaging           INTEGER,
    language            INTEGER,
    script              INTEGER,
    barcode             VARCHAR(255),
    comment             TEXT,
    edits_pending       INTEGER,
    quality             SMALLINT,
    last_updated        TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_silver_release_artist_credit ON silver.release(artist_credit);
CREATE INDEX IF NOT EXISTS idx_silver_release_group ON silver.release(release_group);

-- 5. silver.release_country (Fechas históricas reales de publicación y país de lanzamiento)
CREATE TABLE IF NOT EXISTS silver.release_country (
    release             INTEGER NOT NULL,
    country             INTEGER NOT NULL,
    date_year           SMALLINT,
    date_month          SMALLINT,
    date_day            SMALLINT,
    PRIMARY KEY (release, country)
);

CREATE INDEX IF NOT EXISTS idx_silver_rc_release ON silver.release_country(release);
CREATE INDEX IF NOT EXISTS idx_silver_rc_country ON silver.release_country(country);

-- 6. silver.release_unknown_country (Fechas históricas reales de publicación sin país especificado)
CREATE TABLE IF NOT EXISTS silver.release_unknown_country (
    release             INTEGER PRIMARY KEY,
    date_year           SMALLINT,
    date_month          SMALLINT,
    date_day            SMALLINT
);

-- 7. silver.medium (Discos físicos o digitales que componen cada release)
CREATE TABLE IF NOT EXISTS silver.medium (
    id                  INTEGER PRIMARY KEY,
    release             INTEGER NOT NULL,
    position            INTEGER NOT NULL,
    format              INTEGER,
    name                TEXT,
    edits_pending       INTEGER,
    last_updated        TIMESTAMPTZ,
    track_count         INTEGER
);

CREATE INDEX IF NOT EXISTS idx_silver_medium_release ON silver.medium(release);
CREATE INDEX IF NOT EXISTS idx_silver_medium_format ON silver.medium(format);

-- 8. silver.recording (Grabaciones de audio / master)
CREATE TABLE IF NOT EXISTS silver.recording (
    id                  INTEGER PRIMARY KEY,
    gid                 UUID NOT NULL,
    name                TEXT NOT NULL,
    artist_credit       INTEGER NOT NULL,
    length              INTEGER, -- Duración en milisegundos
    comment             TEXT,
    edits_pending       INTEGER,
    last_updated        TIMESTAMPTZ,
    video               BOOLEAN
);

CREATE INDEX IF NOT EXISTS idx_silver_recording_artist_credit ON silver.recording(artist_credit);

-- 9. silver.track (Pistas en un medium con vínculo a grabación)
CREATE TABLE IF NOT EXISTS silver.track (
    id                  INTEGER PRIMARY KEY,
    gid                 UUID NOT NULL,
    recording           INTEGER NOT NULL,
    medium              INTEGER NOT NULL,
    position            INTEGER NOT NULL,
    number              TEXT NOT NULL,
    name                TEXT NOT NULL,
    artist_credit       INTEGER NOT NULL,
    length              INTEGER, -- Duración en milisegundos
    edits_pending       INTEGER,
    last_updated        TIMESTAMPTZ,
    is_data_track       BOOLEAN
);

CREATE INDEX IF NOT EXISTS idx_silver_track_recording ON silver.track(recording);
CREATE INDEX IF NOT EXISTS idx_silver_track_medium ON silver.track(medium);
CREATE INDEX IF NOT EXISTS idx_silver_track_artist_credit ON silver.track(artist_credit);

-- 10. silver.isrc (Códigos Estándar Internacional de Grabación de Audio)
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
