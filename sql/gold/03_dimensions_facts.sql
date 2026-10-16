-- ============================================================================
-- PROYECTO: DWMusicBrainz (Data Warehouse Masivo de la Industria Musical)
-- CAPA: Gold / Modelo en Estrella Puro (Ralph Kimball Standard)
-- ARCHIVO: 03_dimensions_facts.sql
-- DESCRIPCIÓN: DDL de las 6 Dimensiones Conformadas y Tabla de Hechos Histórica
--              Diaria con Nomenclatura de Negocio en Español y Métricas 100% Aditivas.
-- ============================================================================

CREATE SCHEMA IF NOT EXISTS gold;

-- Limpieza preventiva de objetos con nomenclatura anterior si existiesen
DROP MATERIALIZED VIEW IF EXISTS gold.mv_yearly_production_trends CASCADE;
DROP MATERIALIZED VIEW IF EXISTS gold.mv_artist_analytics CASCADE;
DROP MATERIALIZED VIEW IF EXISTS gold.mv_format_evolution CASCADE;
DROP MATERIALIZED VIEW IF EXISTS gold.mv_geography_distribution CASCADE;
DROP TABLE IF EXISTS gold.fact_tracks CASCADE;
DROP TABLE IF EXISTS gold.dim_date CASCADE;
DROP TABLE IF EXISTS gold.dim_artist CASCADE;
DROP TABLE IF EXISTS gold.dim_geography CASCADE;
DROP TABLE IF EXISTS gold.dim_release CASCADE;
DROP TABLE IF EXISTS gold.dim_format CASCADE;
DROP TABLE IF EXISTS gold.dim_language CASCADE;

-- ----------------------------------------------------------------------------
-- 1. DIMENSIÓN CONFORMADA: gold.dim_fecha (Granularidad diaria 1900-2030)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS gold.dim_fecha (
    fecha_key           INTEGER PRIMARY KEY,         -- YYYYMMDD (Ej: 20210515, o 0 para Sin Fecha)
    fecha_completa      DATE,
    anio                INTEGER NOT NULL,
    trimestre           INTEGER NOT NULL,            -- 1, 2, 3, 4
    nombre_trimestre    VARCHAR(10) NOT NULL,        -- 'Q1', 'Q2', 'Q3', 'Q4'
    mes                 INTEGER NOT NULL,            -- 1 a 12
    nombre_mes          VARCHAR(20) NOT NULL,        -- 'Enero', 'Febrero', etc.
    nombre_mes_corto    CHAR(3) NOT NULL,            -- 'Ene', 'Feb', etc.
    dia                 INTEGER NOT NULL,
    dia_semana          INTEGER NOT NULL,            -- 1 (Lunes) a 7 (Domingo)
    nombre_dia          VARCHAR(20) NOT NULL,        -- 'Lunes', 'Martes', etc.
    es_fin_de_semana    BOOLEAN NOT NULL,
    decada              VARCHAR(20) NOT NULL,        -- '1970s', '1980s', '2020s'
    siglo               VARCHAR(20) NOT NULL         -- 'Siglo XX', 'Siglo XXI'
);

CREATE INDEX IF NOT EXISTS idx_dim_fecha_anio ON gold.dim_fecha(anio);
CREATE INDEX IF NOT EXISTS idx_dim_fecha_decada ON gold.dim_fecha(decada);

-- ----------------------------------------------------------------------------
-- 2. DIMENSIÓN CONFORMADA: gold.dim_artista (Músicos, Grupos y Orquestas)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS gold.dim_artista (
    artista_key         SERIAL PRIMARY KEY,          -- Surrogate Key
    artista_id          INTEGER NOT NULL,            -- Business Key (MusicBrainz ID)
    artista_gid         UUID NOT NULL,               -- GID Universal
    nombre_artista      TEXT NOT NULL,
    nombre_orden        TEXT,
    tipo_artista        VARCHAR(100) NOT NULL DEFAULT 'Desconocido',
    genero              VARCHAR(50) NOT NULL DEFAULT 'Desconocido',
    area_id             INTEGER DEFAULT 0,           -- Vínculo exacto a área geográfica
    nombre_area         TEXT DEFAULT 'Sin Área Registrada',
    nombre_pais         TEXT DEFAULT 'Sin País Registrado',
    anio_inicio         SMALLINT,
    anio_fin            SMALLINT,
    finalizado          BOOLEAN DEFAULT FALSE,
    creado_en           TIMESTAMPTZ DEFAULT clock_timestamp()
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_dim_artista_id ON gold.dim_artista(artista_id);
CREATE INDEX IF NOT EXISTS idx_dim_artista_nombre ON gold.dim_artista(nombre_artista);
CREATE INDEX IF NOT EXISTS idx_dim_artista_pais ON gold.dim_artista(nombre_pais);
CREATE INDEX IF NOT EXISTS idx_dim_artista_tipo ON gold.dim_artista(tipo_artista);

-- ----------------------------------------------------------------------------
-- 3. DIMENSIÓN CONFORMADA: gold.dim_geografia (Jerarquía Geográfica Normalizada)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS gold.dim_geografia (
    geografia_key       SERIAL PRIMARY KEY,          -- Surrogate Key
    area_id             INTEGER NOT NULL,            -- Business Key
    area_gid            UUID NOT NULL,
    nombre_area         TEXT NOT NULL,
    tipo_area           VARCHAR(100) NOT NULL DEFAULT 'Desconocido',
    nombre_pais         TEXT DEFAULT 'No Aplica',
    creado_en           TIMESTAMPTZ DEFAULT clock_timestamp()
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_dim_geo_area_id ON gold.dim_geografia(area_id);
CREATE INDEX IF NOT EXISTS idx_dim_geo_pais ON gold.dim_geografia(nombre_pais);
CREATE INDEX IF NOT EXISTS idx_dim_geo_tipo ON gold.dim_geografia(tipo_area);

-- ----------------------------------------------------------------------------
-- 4. DIMENSIÓN CONFORMADA: gold.dim_lanzamiento (Perfil Analítico de Lanzamiento)
--    Agrupa Estado Comercial, Tipo de Empaque y Calidad de Edición para permitir
--    la consolidación histórica de múltiples lanzamientos por día en los hechos.
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS gold.dim_lanzamiento (
    lanzamiento_key     SERIAL PRIMARY KEY,          -- Surrogate Key
    estado_id           INTEGER NOT NULL DEFAULT 0,
    empaque_id          INTEGER NOT NULL DEFAULT 0,
    calidad_id          SMALLINT NOT NULL DEFAULT 0,
    estado_lanzamiento  VARCHAR(100) NOT NULL DEFAULT 'No Clasificado', -- Oficial, Promocional, Bootleg, Pseudo-Release
    tipo_empaque        VARCHAR(100) NOT NULL DEFAULT 'Estándar / Desconocido', -- Jewel Case, Digipak, Gatefold, Digital
    calidad_datos       VARCHAR(50) NOT NULL DEFAULT 'Normal',          -- Alta, Normal, Baja, Desconocida
    creado_en           TIMESTAMPTZ DEFAULT clock_timestamp(),
    CONSTRAINT uq_dim_lanzamiento_perfil UNIQUE (estado_id, empaque_id, calidad_id)
);

CREATE INDEX IF NOT EXISTS idx_dim_lanzamiento_estado ON gold.dim_lanzamiento(estado_lanzamiento);
CREATE INDEX IF NOT EXISTS idx_dim_lanzamiento_empaque ON gold.dim_lanzamiento(tipo_empaque);

-- ----------------------------------------------------------------------------
-- 5. DIMENSIÓN CONFORMADA: gold.dim_formato (Formato Físico / Digital del Medio)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS gold.dim_formato (
    formato_key         SERIAL PRIMARY KEY,          -- Surrogate Key
    formato_id          INTEGER NOT NULL,            -- Business Key
    nombre_formato      VARCHAR(100) NOT NULL,       -- CD, Vinilo 12", Digital Media, Cassette, etc.
    categoria_formato   VARCHAR(100) NOT NULL DEFAULT 'Otros Formatos'
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_dim_formato_id ON gold.dim_formato(formato_id);
CREATE INDEX IF NOT EXISTS idx_dim_formato_categoria ON gold.dim_formato(categoria_formato);

-- ----------------------------------------------------------------------------
-- 6. DIMENSIÓN CONFORMADA: gold.dim_idioma (Idioma de Publicación ISO 639-3)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS gold.dim_idioma (
    idioma_key          SERIAL PRIMARY KEY,          -- Surrogate Key
    idioma_id           INTEGER NOT NULL,            -- Business Key
    nombre_idioma       VARCHAR(100) NOT NULL,       -- Inglés, Español, Japonés, Instrumental, etc.
    codigo_iso          VARCHAR(10) DEFAULT 'und'
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_dim_idioma_id ON gold.dim_idioma(idioma_id);

-- ----------------------------------------------------------------------------
-- 7. TABLA DE HECHOS HISTÓRICA DIARIA: gold.fact_produccion_musical
--    Grano: 1 registro histórico por Día (fecha_key) y combinación de las
--    5 dimensiones conformadas (artista, perfil de lanzamiento, geografía,
--    formato e idioma), conteniendo EXCLUSIVAMENTE Claves Foráneas y
--    Métricas Numéricas 100% Aditivas (cero textos, cero booleanos).
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS gold.fact_produccion_musical (
    hecho_key                   BIGSERIAL,
    
    -- Claves Foráneas Conformadas (Grano Histórico Diario + Dimensional)
    fecha_key                   INTEGER NOT NULL,    -- FK -> gold.dim_fecha (Clave de partición)
    artista_key                 INTEGER NOT NULL,    -- FK -> gold.dim_artista
    lanzamiento_key             INTEGER NOT NULL,    -- FK -> gold.dim_lanzamiento
    geografia_key               INTEGER NOT NULL,    -- FK -> gold.dim_geografia
    formato_key                 INTEGER NOT NULL,    -- FK -> gold.dim_formato
    idioma_key                  INTEGER NOT NULL,    -- FK -> gold.dim_idioma
    
    -- Métricas Numéricas 100% Aditivas (Hechos Históricos Consolidados)
    lanzamientos_total          INTEGER NOT NULL DEFAULT 0,
    soportes_total              INTEGER NOT NULL DEFAULT 0,
    pistas_total                INTEGER NOT NULL DEFAULT 0,
    grabaciones_unicas_total    INTEGER NOT NULL DEFAULT 0,
    duracion_total_ms           BIGINT  NOT NULL DEFAULT 0,
    duracion_total_segundos     NUMERIC(14, 2) NOT NULL DEFAULT 0.00,
    duracion_total_minutos      NUMERIC(14, 2) NOT NULL DEFAULT 0.00,
    pistas_con_isrc_total       INTEGER NOT NULL DEFAULT 0,
    pistas_largas_total         INTEGER NOT NULL DEFAULT 0,
    pistas_video_total          INTEGER NOT NULL DEFAULT 0,
    pistas_completas_total      INTEGER NOT NULL DEFAULT 0,
    
    PRIMARY KEY (hecho_key, fecha_key)
) PARTITION BY RANGE (fecha_key);

COMMENT ON SCHEMA gold IS 'Capa Gold: Esquema en Estrella Puro (Ralph Kimball) en español con métricas aditivas históricas.';
COMMENT ON TABLE gold.fact_produccion_musical IS 'Tabla de hechos histórica diaria con FKs conformadas y métricas numéricas 100% aditivas.';