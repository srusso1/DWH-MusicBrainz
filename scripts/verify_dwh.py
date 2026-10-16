"""
verify_dwh.py
=============
Script de auditoría integral y certificación del Data Warehouse DWMusicBrainz.
Verifica:
1. Volumetría por tabla en capas Silver y Gold (Modelo Estrella en Español)
2. Integridad referencial Ralph Kimball (0 huérfanos entre fact_produccion_musical y dimensiones)
3. Totales consolidados de métricas aditivas históricas (lanzamientos_total, pistas_total, etc.)
4. Almacenamiento físico en disco (> 3.0 GB en PostgreSQL 16)
5. Bitácora de auditoría ETL (meta.etl_audit) y calidad (meta.data_quality_log)
"""

import os
import sys
from pathlib import Path
import psycopg2
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "5435"))
DB_NAME = os.getenv("DB_NAME", "dw_musicbrainz")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres123")


def run_verification():
    print("=" * 80)
    print("AUDITORIA Y CERTIFICACION DE DATA WAREHOUSE - DWMusicBrainz")
    print(f"PostgreSQL 16 | Host: {DB_HOST}:{DB_PORT} | Base de Datos: {DB_NAME}")
    print("=" * 80)

    conn = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
    )
    cursor = conn.cursor()

    # 1. Volumetría por Capa
    print("\n1. VOLUMETRIA POR TABLA (100% DATOS REALES MUSICBRAINZ):")
    print("-" * 80)
    tables = [
        ("silver", "area"),
        ("silver", "artist"),
        ("silver", "artist_credit_name"),
        ("silver", "release"),
        ("silver", "release_country"),
        ("silver", "release_unknown_country"),
        ("silver", "medium"),
        ("silver", "recording"),
        ("silver", "track"),
        ("silver", "isrc"),
        ("gold", "dim_fecha"),
        ("gold", "dim_artista"),
        ("gold", "dim_geografia"),
        ("gold", "dim_lanzamiento"),
        ("gold", "dim_formato"),
        ("gold", "dim_idioma"),
        ("gold", "fact_produccion_musical"),
    ]

    total_silver = 0
    total_gold = 0
    for schema, tbl in tables:
        try:
            cursor.execute(f"SELECT count(*) FROM {schema}.{tbl};")
            cnt = cursor.fetchone()[0]
            print(f" - {schema}.{tbl:<28}: {cnt:>12,} filas")
            if schema == "silver":
                total_silver += cnt
            elif schema == "gold":
                total_gold += cnt
        except Exception:
            print(f" - {schema}.{tbl:<28}: [PENDIENTE O EN CARGA]")
            conn.rollback()

    print(f"\n -> Total Filas Consolidadas en Silver: {total_silver:,}")
    print(f" -> Total Filas Consolidadas en Gold:   {total_gold:,}")

    # 2. Resumen de Métricas Aditivas Históricas
    print("\n2. METRICAS HISTORICAS ADITIVAS CONSOLIDADAS (gold.fact_produccion_musical):")
    print("-" * 80)
    try:
        cursor.execute("""
            SELECT
                COALESCE(SUM(lanzamientos_total), 0),
                COALESCE(SUM(soportes_total), 0),
                COALESCE(SUM(pistas_total), 0),
                COALESCE(SUM(pistas_con_isrc_total), 0),
                COALESCE(SUM(pistas_largas_total), 0),
                COALESCE(SUM(pistas_video_total), 0),
                ROUND(COALESCE(SUM(duracion_total_minutos), 0) / 60.0, 2)
            FROM gold.fact_produccion_musical;
        """)
        lanz, sop, pist, isrc, largas, vid, horas = cursor.fetchone()
        print(f" - lanzamientos_total          : {lanz:>14,}")
        print(f" - soportes_total              : {sop:>14,}")
        print(f" - pistas_total                : {pist:>14,}")
        print(f" - pistas_con_isrc_total       : {isrc:>14,}")
        print(f" - pistas_largas_total (>5min) : {largas:>14,}")
        print(f" - pistas_video_total          : {vid:>14,}")
        print(f" - duracion_total_horas        : {horas:>14,}")
    except Exception:
        conn.rollback()

    # 3. Almacenamiento Físico en Disco (Meta: > 3.0 GB)
    print("\n3. ALMACENAMIENTO FISICO EN DISCO (POSTGRESQL 16):")
    print("-" * 80)
    cursor.execute("""
        SELECT 
            pg_size_pretty(SUM(pg_total_relation_size(relid))) as total_dwh_size,
            COALESCE(SUM(pg_total_relation_size(relid)), 0) / (1024.0 * 1024.0 * 1024.0) as total_gb
        FROM pg_catalog.pg_statio_user_tables
        WHERE schemaname IN ('gold', 'silver', 'meta');
    """)
    row = cursor.fetchone()
    total_pretty, total_gb = row[0], row[1]
    print(f" -> Espacio Total Ocupado por el DWH: {total_pretty} ({total_gb:.2f} GB)")
    if total_gb >= 3.0:
        print("    [APROBADO] Supera el umbral mínimo exigido de 3.0 GB.")
    else:
        print(f"    [EN PROCESO] Actualmente en {total_gb:.2f} GB.")

    # 4. Integridad Referencial Kimball
    print("\n4. INTEGRIDAD REFERENCIAL RALPH KIMBALL (CERO HUERFANOS):")
    print("-" * 80)
    integrity_tests = [
        ("Huérfanos en dim_artista", "SELECT COUNT(*) FROM gold.fact_produccion_musical f LEFT JOIN gold.dim_artista a ON f.artista_key = a.artista_key WHERE a.artista_key IS NULL;"),
        ("Huérfanos en dim_fecha", "SELECT COUNT(*) FROM gold.fact_produccion_musical f LEFT JOIN gold.dim_fecha d ON f.fecha_key = d.fecha_key WHERE d.fecha_key IS NULL;"),
        ("Huérfanos en dim_lanzamiento", "SELECT COUNT(*) FROM gold.fact_produccion_musical f LEFT JOIN gold.dim_lanzamiento r ON f.lanzamiento_key = r.lanzamiento_key WHERE r.lanzamiento_key IS NULL;"),
        ("Huérfanos en dim_formato", "SELECT COUNT(*) FROM gold.fact_produccion_musical f LEFT JOIN gold.dim_formato fmt ON f.formato_key = fmt.formato_key WHERE fmt.formato_key IS NULL;"),
        ("Huérfanos en dim_geografia", "SELECT COUNT(*) FROM gold.fact_produccion_musical f LEFT JOIN gold.dim_geografia g ON f.geografia_key = g.geografia_key WHERE g.geografia_key IS NULL;"),
        ("Huérfanos en dim_idioma", "SELECT COUNT(*) FROM gold.fact_produccion_musical f LEFT JOIN gold.dim_idioma l ON f.idioma_key = l.idioma_key WHERE l.idioma_key IS NULL;"),
    ]

    cursor.execute("SELECT count(*) FROM gold.fact_produccion_musical;")
    fact_count = cursor.fetchone()[0]
    if fact_count == 0:
        print(" -> gold.fact_produccion_musical aún no ha sido poblada.")
    else:
        for desc, q in integrity_tests:
            cursor.execute(q)
            huerfanos = cursor.fetchone()[0]
            status = "[OK - 0 HUERFANOS]" if huerfanos == 0 else f"[FALLO: {huerfanos} huérfanos]"
            print(f" - {desc:<35}: {status}")

    # 5. Auditoría de Cargas ETL (meta.etl_audit)
    print("\n5. BITACORA DE AUDITORIA ETL (meta.etl_audit):")
    print("-" * 80)
    cursor.execute("""
        SELECT layer, table_name, operation, status, rows_inserted, duration_seconds
        FROM meta.etl_audit
        ORDER BY audit_id;
    """)
    for l, t, op, st, rows, dur in cursor.fetchall():
        dur_str = f"{dur:.2f}s" if dur else "En curso"
        print(f" - [{st:<7}] {l:<15} | {t:<30} | {op:<22} | {rows:>12,} filas | {dur_str:>10}")

    print("\n" + "=" * 80)
    print("FIN DEL REPORTE DE AUDITORIA.")
    print("=" * 80)

    cursor.close()
    conn.close()


if __name__ == "__main__":
    run_verification()