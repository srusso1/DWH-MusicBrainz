-- ============================================================================
-- PROYECTO: DWMusicBrainz (Data Warehouse Masivo de la Industria Musical)
-- CAPA: Meta / Auditoría y Gobernanza de Datos
-- ARCHIVO: 01_schema_meta.sql
-- DESCRIPCIÓN: Estructura de auditoría, linaje y control de calidad (Medallion)
-- ============================================================================

CREATE SCHEMA IF NOT EXISTS meta;

-- 1. Tabla de Auditoría de Cargas ETL (Control por Lotes / Capas)
CREATE TABLE IF NOT EXISTS meta.etl_audit (
    audit_id BIGSERIAL PRIMARY KEY,
    batch_id VARCHAR(100) NOT NULL,
    layer VARCHAR(50) NOT NULL,            -- 'RAW_TO_SILVER', 'SILVER_TO_GOLD', 'AGGREGATION'
    table_name VARCHAR(100) NOT NULL,
    operation VARCHAR(50) NOT NULL,        -- 'BULK_COPY', 'INSERT_SELECT', 'REFRESH_MV'
    status VARCHAR(20) NOT NULL DEFAULT 'STARTED', -- 'STARTED', 'SUCCESS', 'FAILED'
    rows_read BIGINT DEFAULT 0,
    rows_inserted BIGINT DEFAULT 0,
    rows_rejected BIGINT DEFAULT 0,
    start_time TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    end_time TIMESTAMPTZ,
    duration_seconds NUMERIC(10, 2),
    error_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);

CREATE INDEX IF NOT EXISTS idx_etl_audit_batch ON meta.etl_audit(batch_id);
CREATE INDEX IF NOT EXISTS idx_etl_audit_table ON meta.etl_audit(table_name, layer);

-- 2. Tabla de Registro de Calidad de Datos (Data Quality Log)
CREATE TABLE IF NOT EXISTS meta.data_quality_log (
    check_id BIGSERIAL PRIMARY KEY,
    batch_id VARCHAR(100) NOT NULL,
    rule_name VARCHAR(150) NOT NULL,
    layer VARCHAR(50) NOT NULL,            -- 'SILVER', 'GOLD'
    table_name VARCHAR(100) NOT NULL,
    column_name VARCHAR(100),
    severity VARCHAR(20) NOT NULL,         -- 'CRITICAL', 'WARNING', 'INFO'
    status VARCHAR(20) NOT NULL,           -- 'PASSED', 'FAILED'
    failed_records_count BIGINT DEFAULT 0,
    details JSONB,
    checked_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);

CREATE INDEX IF NOT EXISTS idx_dq_batch ON meta.data_quality_log(batch_id);
CREATE INDEX IF NOT EXISTS idx_dq_rule ON meta.data_quality_log(rule_name, status);

COMMENT ON SCHEMA meta IS 'Metadatos técnicos, control de ejecuciones ETL y auditoría de calidad de datos.';
COMMENT ON TABLE meta.etl_audit IS 'Bitácora central de procesamiento de capas Bronze -> Silver -> Gold.';
COMMENT ON TABLE meta.data_quality_log IS 'Resultados de las verificaciones de integridad referencial, nulos y rangos.';