"""
run_gold_pipeline.py
====================
Ejecución del pipeline de la capa Gold:
1. Poblado masivo de la tabla de hechos central gold.fact_tracks
2. Refresco de vistas materializadas analíticas
3. Validación y auditoría de calidad de datos Kimball
"""

import os
import sys
import time
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


def run_gold():
    batch_id = f"batch_gold_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    print("=" * 70)
    print("INICIANDO TRANSFORMACION Y POBLADO DE CAPA GOLD")
    print(f"Batch: {batch_id} | DB: {DB_NAME}@{DB_HOST}:{DB_PORT}")
    print("=" * 70)

    conn = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
    )
    conn.autocommit = True
    cursor = conn.cursor()

    # 1. Poblado de fact_tracks
    print("\n-> 1. Poblado masivo de gold.fact_tracks...")
    cursor.execute("""
        INSERT INTO meta.etl_audit (batch_id, layer, table_name, operation, status)
        VALUES (%s, 'SILVER_TO_GOLD', 'gold.fact_tracks', 'INSERT_SELECT', 'STARTED')
        RETURNING audit_id;
    """, (batch_id,))
    audit_id = cursor.fetchone()[0]

    fact_sql_path = BASE_DIR / "etl" / "gold" / "populate_fact_tracks.sql"
    fact_sql = fact_sql_path.read_text(encoding="utf-8-sig")

    t0 = time.time()
    try:
        cursor.execute(fact_sql)
        elapsed_fact = time.time() - t0

        cursor.execute("SELECT count(*) FROM gold.fact_tracks;")
        fact_count = cursor.fetchone()[0]

        cursor.execute("""
            UPDATE meta.etl_audit
            SET status = 'SUCCESS',
                rows_inserted = %s,
                end_time = clock_timestamp(),
                duration_seconds = %s
            WHERE audit_id = %s;
        """, (fact_count, elapsed_fact, audit_id))

        print(f"[OK] gold.fact_tracks completada:")
        print(f"     Total pistas en hechos: {fact_count:,}")
        print(f"     Tiempo: {elapsed_fact:.2f}s ({fact_count / max(elapsed_fact, 0.001):,.0f} filas/seg)")

    except Exception as e:
        elapsed_fact = time.time() - t0
        cursor.execute("""
            UPDATE meta.etl_audit
            SET status = 'FAILED',
                error_message = %s,
                end_time = clock_timestamp(),
                duration_seconds = %s
            WHERE audit_id = %s;
        """, (str(e), elapsed_fact, audit_id))
        print(f"[ERROR] Fallo el poblado de fact_tracks: {e}")
        sys.exit(1)

    # 2. Refresco de Vistas Materializadas
    print("\n-> 2. Refrescando Vistas Materializadas para Power BI...")
    mvs = [
        "gold.mv_yearly_production_trends",
        "gold.mv_artist_analytics",
        "gold.mv_format_evolution",
        "gold.mv_geography_distribution",
    ]
    for mv in mvs:
        print(f"   - Refrescando {mv} ...", end=" ", flush=True)
        t_mv = time.time()
        cursor.execute(f"REFRESH MATERIALIZED VIEW {mv};")
        print(f"OK ({time.time() - t_mv:.2f}s)")

    # 3. Reporte de Almacenamiento en Disco
    print("\n" + "=" * 70)
    print("REPORTE DE ALMACENAMIENTO FISICO EN DISCO (POSTGRESQL 16)")
    print("=" * 70)
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
        print(f" - {s}.{r:<30}: Total {tot:>10} | Datos: {dat:>10} | Indices: {idx:>10}")

    cursor.close()
    conn.close()
    print("\n[FIN] PIPELINE GOLD COMPLETADO EXITOSAMENTE.")


if __name__ == "__main__":
    run_gold()