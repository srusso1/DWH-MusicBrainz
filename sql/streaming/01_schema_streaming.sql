-- =============================================================================
-- Capa de streaming (speed layer): Kafka -> Spark Structured Streaming -> PostgreSQL
-- Idempotente: se puede ejecutar varias veces.
-- =============================================================================
CREATE SCHEMA IF NOT EXISTS streaming;

-- Ultima version conocida de cada lanzamiento recibido en tiempo real (dedup por MBID).
CREATE TABLE IF NOT EXISTS streaming.lanzamientos_evento (
    mbid               UUID PRIMARY KEY,
    titulo             TEXT,
    estado             TEXT,
    fecha              TEXT,          -- fecha parcial MusicBrainz: AAAA, AAAA-MM o AAAA-MM-DD
    anio               INTEGER,
    pais               TEXT NOT NULL,
    formatos           TEXT[],
    medio              TEXT,
    formato_principal  TEXT NOT NULL,
    numero_pistas      INTEGER,
    artista            TEXT,
    idioma             TEXT,
    empaque            TEXT,
    codigo_barras      TEXT,
    fuente             TEXT,
    evento_ts          TIMESTAMPTZ NOT NULL,   -- hora de ingesta en el productor
    kafka_ts           TIMESTAMPTZ,            -- hora de escritura en el broker
    kafka_particion    INTEGER,
    kafka_offset       BIGINT,
    batch_id           BIGINT,
    procesado_ts       TIMESTAMPTZ NOT NULL DEFAULT now(),  -- hora de UPSERT
    versiones          INTEGER NOT NULL DEFAULT 1           -- veces que llego el mismo MBID
);
CREATE INDEX IF NOT EXISTS ix_lanz_evento_pais ON streaming.lanzamientos_evento (pais);

-- Agregados por ventana fija de 1 minuto (tiempo de evento) por pais y formato.
CREATE TABLE IF NOT EXISTS streaming.lanzamientos_ventana (
    ventana_inicio  TIMESTAMPTZ NOT NULL,
    ventana_fin     TIMESTAMPTZ NOT NULL,
    pais            TEXT NOT NULL,
    formato         TEXT NOT NULL,
    lanzamientos    BIGINT NOT NULL,
    pistas          BIGINT NOT NULL,
    batch_id        BIGINT,
    actualizado_ts  TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (ventana_inicio, pais, formato)
);

-- Bitacora de micro-lotes aplicados: garantiza idempotencia por (consulta, batch_id).
CREATE TABLE IF NOT EXISTS streaming.control_lotes (
    consulta    TEXT   NOT NULL,
    batch_id    BIGINT NOT NULL,
    filas       INTEGER NOT NULL,
    aplicado_ts TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (consulta, batch_id)
);

-- Tablas de staging (Spark las trunca y rellena en cada micro-lote via JDBC).
CREATE TABLE IF NOT EXISTS streaming.stg_lanzamientos_evento (
    mbid TEXT, titulo TEXT, estado TEXT, fecha TEXT, anio INTEGER, pais TEXT,
    formatos TEXT, medio TEXT, formato_principal TEXT, numero_pistas INTEGER,
    artista TEXT, idioma TEXT, empaque TEXT, codigo_barras TEXT, fuente TEXT,
    evento_ts TIMESTAMPTZ, kafka_ts TIMESTAMPTZ, kafka_particion INTEGER, kafka_offset BIGINT
);

CREATE TABLE IF NOT EXISTS streaming.stg_lanzamientos_ventana (
    ventana_inicio TIMESTAMPTZ, ventana_fin TIMESTAMPTZ, pais TEXT, formato TEXT,
    lanzamientos BIGINT, pistas BIGINT
);

-- Vista de monitoreo: latencia extremo a extremo (productor -> PostgreSQL).
CREATE OR REPLACE VIEW streaming.v_latencia AS
SELECT count(*)                                                        AS eventos,
       round(avg(extract(epoch FROM procesado_ts - evento_ts))::numeric, 2)  AS latencia_prom_s,
       round(percentile_cont(0.5) WITHIN GROUP
             (ORDER BY extract(epoch FROM procesado_ts - evento_ts))::numeric, 2) AS latencia_p50_s,
       round(max(extract(epoch FROM procesado_ts - evento_ts))::numeric, 2)  AS latencia_max_s
FROM streaming.lanzamientos_evento;
