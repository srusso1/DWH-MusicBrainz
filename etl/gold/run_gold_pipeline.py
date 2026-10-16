"""
run_gold_pipeline.py
====================
Ejecución completa e idempotente del pipeline de la capa Gold (Modelo en Estrella Puro en Español):
1. Poblado de las 6 dimensiones conformadas (dim_fecha, dim_artista, dim_geografia, dim_lanzamiento, dim_formato, dim_idioma)
2. Poblado masivo de la tabla de hechos histórica diaria gold.fact_produccion_musical (solo FKs + métricas aditivas)
3. Refresco de las 4 vistas materializadas analíticas para Power BI
4. Registro de controles de calidad de datos en meta.data_quality_log
"""

import os
import sys
import time
import json
from pathlib import Path
from datetime import datetime
import psycopg2
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(BASE_DIR / ".env")

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "5435"))
DB_NAME = os.getenv("DB_NAME", "dw_musicbrainz")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres123")

DIMENSION_JOBS = [
    ("gold.dim_fecha", "populate_dim_date.sql"),
    ("gold.dim_geografia", "populate_dim_geography.sql"),
    ("gold.dim_artista", "populate_dim_artist.sql"),
    ("gold.dim_lanzamiento", "populate_dim_release.sql"),
    ("gold.dim_formato", "populate_dim_format.sql"),
    ("gold.dim_idioma", "populate_dim_language.sql"),
]

MATERIALIZED_VIEWS = [
    "gold.mv_tendencias_produccion_anual",
    "gold.mv_analitica_artistas",
    "gold.mv_evolucion_formatos",
    "gold.mv_distribucion_geografica",
]


def execute_audited_sql(cursor, batch_id, table_name, sql_filename, operation="INSERT_SELECT"):
    cursor.execute("""
        INSERT INTO meta.etl_audit (batch_id, layer, table_name, operation, status)
        VALUES (%s, 'SILVER_TO_GOLD', %s, %s, 'STARTED')
        RETURNING audit_id;
    """, (batch_id, table_name, operation))
    audit_id = cursor.fetchone()[0]

    sql_path = BASE_DIR / "etl" / "gold" / sql_filename
    sql_text = sql_path.read_text(encoding="utf-8-sig")

    t0 = time.time()
    try:
        cursor.execute(sql_text)
        elapsed = time.time() - t0

        cursor.execute(f"SELECT count(*) FROM {table_name};")
        row_count = cursor.fetchone()[0]

        cursor.execute("""
            UPDATE meta.etl_audit
            SET status = 'SUCCESS',
                rows_read = %s,
                rows_inserted = %s,
                end_time = clock_timestamp(),
                duration_seconds = %s
            WHERE audit_id = %s;
        """, (row_count, row_count, elapsed, audit_id))

        rate = row_count / max(elapsed, 0.001)
        print(f"   [OK] {table_name:<28}: {row_count:>12,} filas | {elapsed:>6.2f}s ({rate:,.0f} filas/seg)")
        return row_count

    except Exception as e:
        elapsed = time.time() - t0
        cursor.execute("""
            UPDATE meta.etl_audit
            SET status = 'FAILED',
                error_message = %s,
                end_time = clock_timestamp(),
                duration_seconds = %s
            WHERE audit_id = %s;
        """, (str(e), elapsed, audit_id))
        print(f"   [ERROR] Fallo en {table_name}: {e}")
        raise


def log_data_quality_checks(cursor, batch_id):
    print("\n-> 4. Ejecutando controles de calidad y registrando en meta.data_quality_log...")
    checks = [
        (
            "INTEGRIDAD_FK_DIM_ARTISTA",
            "artista_key",
            "SELECT COUNT(*) FROM gold.fact_produccion_musical f LEFT JOIN gold.dim_artista d ON f.artista_key = d.artista_key WHERE d.artista_key IS NULL;",
        ),
        (
            "INTEGRIDAD_FK_DIM_FECHA",
            "fecha_key",
            "SELECT COUNT(*) FROM gold.fact_produccion_musical f LEFT JOIN gold.dim_fecha d ON f.fecha_key = d.fecha_key WHERE d.fecha_key IS NULL;",
        ),
        (
            "INTEGRIDAD_FK_DIM_LANZAMIENTO",
            "lanzamiento_key",
            "SELECT COUNT(*) FROM gold.fact_produccion_musical f LEFT JOIN gold.dim_lanzamiento d ON f.lanzamiento_key = d.lanzamiento_key WHERE d.lanzamiento_key IS NULL;",
        ),
        (
            "INTEGRIDAD_FK_DIM_GEOGRAFIA",
            "geografia_key",
            "SELECT COUNT(*) FROM gold.fact_produccion_musical f LEFT JOIN gold.dim_geografia d ON f.geografia_key = d.geografia_key WHERE d.geografia_key IS NULL;",
        ),
        (
            "INTEGRIDAD_FK_DIM_FORMATO",
            "formato_key",
            "SELECT COUNT(*) FROM gold.fact_produccion_musical f LEFT JOIN gold.dim_formato d ON f.formato_key = d.formato_key WHERE d.formato_key IS NULL;",
        ),
        (
            "INTEGRIDAD_FK_DIM_IDIOMA",
            "idioma_key",
            "SELECT COUNT(*) FROM gold.fact_produccion_musical f LEFT JOIN gold.dim_idioma d ON f.idioma_key = d.idioma_key WHERE d.idioma_key IS NULL;",
        ),
        (
            "METRICAS_ADITIVAS_NO_NEGATIVAS",
            "duracion_total_ms",
            "SELECT COUNT(*) FROM gold.fact_produccion_musical WHERE lanzamientos_total <= 0 OR pistas_total <= 0 OR duracion_total_ms < 0;",
        ),
    ]

    for rule_name, col_name, query in checks:
        cursor.execute(query)
        failed_count = cursor.fetchone()[0]
        status = "PASSED" if failed_count == 0 else "FAILED"
        cursor.execute("""
            INSERT INTO meta.data_quality_log (
                batch_id, rule_name, layer, table_name, column_name,
                severity, status, failed_records_count, details
            ) VALUES (%s, %s, 'GOLD', 'gold.fact_produccion_musical', %s, 'CRITICAL', %s, %s, %s);
        """, (
            batch_id,
            rule_name,
            col_name,
            status,
            failed_count,
            json.dumps({"violaciones": failed_count}),
        ))
        print(f"   - [{status}] {rule_name:<35}: {failed_count} violaciones")


def run_gold():
    batch_id = f"batch_gold_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    print("=" * 75)
    print("INICIANDO TRANSFORMACION Y POBLADO DE CAPA GOLD (MODELO ESTRELLA EN ESPANOL)")
    print(f"Batch: {batch_id} | DB: {DB_NAME}@{DB_HOST}:{DB_PORT}")
    print("=" * 75)

    conn = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
    )
    conn.autocommit = True
    cursor = conn.cursor()

    try:
        # 1. Poblado de las 6 Dimensiones Conformadas
        print("\n-> 1. Poblando las 6 Dimensiones Conformadas (Patrón Key 0 Anti-Huérfanos)...")
        for dim_table, sql_file in DIMENSION_JOBS:
            execute_audited_sql(cursor, batch_id, dim_table, sql_file)

        # 2. Poblado de la Tabla de Hechos Histórica Diaria
        print("\n-> 2. Poblando tabla de hechos histórica diaria gold.fact_produccion_musical...")
        execute_audited_sql(
            cursor,
            batch_id,
            "gold.fact_produccion_musical",
            "populate_fact_tracks.sql",
            operation="HISTORICAL_AGGREGATION",
        )

        # 3. Refresco de Vistas Materializadas
        print("\n-> 3. Refrescando Vistas Materializadas para Power BI...")
        for mv in MATERIALIZED_VIEWS:
            print(f"   - Refrescando {mv:<38} ...", end=" ", flush=True)
            t_mv = time.time()
            cursor.execute(f"REFRESH MATERIALIZED VIEW {mv};")
            print(f"OK ({time.time() - t_mv:.2f}s)")

        # 4. Controles de Calidad de Datos
        log_data_quality_checks(cursor, batch_id)

        # 5. Reporte de Almacenamiento en Disco
        print("\n" + "=" * 75)
        print("REPORTE DE ALMACENAMIENTO FISICO EN DISCO (POSTGRESQL 16)")
        print("=" * 75)
        cursor.execute("""
            SELECT 
                schemaname,
                relname,
                pg_size_pretty(pg_total_relation_size(relid)) as total_size,
                pg_size_pretty(pg_relation_size(relid)) as data_size,
                pg_size_pretty(pg_total_relation_size(relid) - pg_relation_size(relid)) as index_size
            FROM pg_catalog.pg_statio_user_tables
            WHERE schemaname IN ('gold', 'silver')
            ORDER BY pg_total_relation_size(relid) DESC
            LIMIT 10;
        """)
        for s, r, tot, dat, idx in cursor.fetchall():
            print(f" - {s}.{r:<32}: Total {tot:>10} | Datos: {dat:>10} | Indices: {idx:>10}")

        print("\n[FIN] PIPELINE GOLD COMPLETADO EXITOSAMENTE.")

    except Exception as e:
        print(f"\n[ERROR FATAL] Pipeline Gold abortado: {e}")
        sys.exit(1)
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    run_gold()