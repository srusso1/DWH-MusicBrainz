-- ============================================================================
-- PROYECTO: DWMusicBrainz
-- CAPA: Gold / Distribución de duración de pistas (histograma)
-- ARCHIVO: 06_distribucion_duracion.sql
-- DESCRIPCIÓN: Dimensión de bandas de duración (Kimball "band dimension") y
--              hecho agregado de grano anual que cuenta pistas por banda.
--              Comparte las dimensiones conformadas fecha, formato, idioma y
--              geografía con gold.fact_produccion_musical.
-- ============================================================================

-- ----------------------------------------------------------------------------
-- DIMENSIÓN: gold.dim_rango_duracion (bandas de 30 segundos)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS gold.dim_rango_duracion (
    rango_duracion_key  INTEGER PRIMARY KEY,         -- 0 = sin duración registrada
    orden               INTEGER NOT NULL,
    etiqueta_rango      VARCHAR(20) NOT NULL,        -- '3:30–4:00', '10:00+'
    limite_inferior_seg INTEGER,                     -- inclusivo
    limite_superior_seg INTEGER                      -- exclusivo (NULL = sin límite)
);

-- ----------------------------------------------------------------------------
-- HECHO AGREGADO: gold.fact_distribucion_duracion
--    Grano: 1 registro por Año (fecha_key = 1 de enero del año) x formato x
--    idioma x geografía x banda de duración. Solo FKs + métricas aditivas.
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS gold.fact_distribucion_duracion (
    fecha_key           INTEGER NOT NULL,            -- FK -> gold.dim_fecha (YYYY0101)
    formato_key         INTEGER NOT NULL,            -- FK -> gold.dim_formato
    idioma_key          INTEGER NOT NULL,            -- FK -> gold.dim_idioma
    geografia_key       INTEGER NOT NULL,            -- FK -> gold.dim_geografia
    rango_duracion_key  INTEGER NOT NULL,            -- FK -> gold.dim_rango_duracion
    pistas_total        INTEGER NOT NULL DEFAULT 0,
    duracion_total_ms   BIGINT  NOT NULL DEFAULT 0,
    PRIMARY KEY (fecha_key, formato_key, idioma_key, geografia_key, rango_duracion_key)
);

CREATE INDEX IF NOT EXISTS idx_fact_dist_rango ON gold.fact_distribucion_duracion(rango_duracion_key);

COMMENT ON TABLE gold.dim_rango_duracion IS 'Dimensión de bandas de duración de pista (30 s) para análisis de distribución.';
COMMENT ON TABLE gold.fact_distribucion_duracion IS 'Hecho agregado anual: conteo de pistas por banda de duración (histograma).';
