"""
ingest_silver.py
================
Ingestión de datos crudos (TSV) a la capa Silver mediante COPY binario/texto
ultrarrápido en PostgreSQL 16 con registro de auditoría en meta.etl_audit.
Soporta extracción quirúrgica bajo demanda desde mbdump.tar.bz2 si algún
archivo TSV aún no ha sido extraído en data/raw/mbdump/.
"""

import os
import sys
import time
import subprocess
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

RAW_DIR = BASE_DIR / "data" / "raw" / "mbdump"
CANDIDATE_DUMPS = [
    Path(os.getenv("MBDUMP_PATH", r"C:\Users\sebas\Downloads\mbdump.tar.bz2")),
    BASE_DIR / "data" / "downloads" / "mbdump.tar.bz2",
]

TABLE_ORDER = [
    "area",
    "artist",
    "artist_credit_name",
    "release",
    "release_country",
    "release_unknown_country",
    "medium",
    "isrc",
    "recording",
    "track",
]


def resolve_dump_archive():
    for path in CANDIDATE_DUMPS:
        if path.exists():
            return path
    return None


def ensure_raw_file(table_name):
    file_path = RAW_DIR / table_name
    if file_path.exists():
        return file_path

    archive_path = resolve_dump_archive()
    if archive_path is None:
        return file_path

    RAW_DIR.parent.mkdir(parents=True, exist_ok=True)
    tar_exe = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32" / "tar.exe"
    tar_cmd = str(tar_exe) if tar_exe.exists() else "tar"

    print(f"[*] Extrayendo mbdump/{table_name} desde {archive_path} ...")
    subprocess.run(
        [tar_cmd, "-xf", str(archive_path), "-C", str(RAW_DIR.parent), f"mbdump/{table_name}"],
        check=True,
    )
    return file_path


def log_audit_start(cursor, batch_id, table_name):
    cursor.execute("""
        INSERT INTO meta.etl_audit (batch_id, layer, table_name, operation, status)
        VALUES (%s, 'RAW_TO_SILVER', %s, 'BULK_COPY', 'STARTED')
        RETURNING audit_id;
    """, (batch_id, table_name))
    return cursor.fetchone()[0]


def log_audit_end(cursor, audit_id, rows_inserted, duration_sec, error=None):
    status = "SUCCESS" if error is None else "FAILED"
    cursor.execute("""
        UPDATE meta.etl_audit
        SET status = %s,
            rows_read = %s,
            rows_inserted = %s,
            end_time = clock_timestamp(),
            duration_seconds = %s,
            error_message = %s
        WHERE audit_id = %s;
    """, (status, rows_inserted, rows_inserted, duration_sec, error, audit_id))


def ingest_table(cursor, table_name, batch_id):
    file_path = ensure_raw_file(table_name)
    if not file_path.exists():
        print(f"[-] Omitiendo '{table_name}': el archivo raw no existe en {file_path}.")
        return 0

    print(f"\n========================================================")
    print(f"-> Ingestando en silver.{table_name} desde {file_path.name}")
    print(f"   Tamano en disco: {file_path.stat().st_size / (1024*1024):.2f} MB")
    print(f"========================================================")

    audit_id = log_audit_start(cursor, batch_id, f"silver.{table_name}")
    start_time = time.time()

    try:
        # Limpieza previa para idempotencia
        cursor.execute(f"TRUNCATE TABLE silver.{table_name} RESTART IDENTITY CASCADE;")
        
        # Ingestion masiva via COPY FROM STDIN
        copy_sql = f"COPY silver.{table_name} FROM STDIN WITH (FORMAT text, DELIMITER E'\\t', NULL '\\N')"
        with open(file_path, "r", encoding="utf-8-sig", errors="replace") as f:
            cursor.copy_expert(copy_sql, f)

        elapsed = time.time() - start_time
        
        # Obtener conteo exacto
        cursor.execute(f"SELECT count(*) FROM silver.{table_name};")
        row_count = cursor.fetchone()[0]
        
        log_audit_end(cursor, audit_id, row_count, elapsed)
        
        rate = row_count / max(elapsed, 0.001)
        print(f"[OK] silver.{table_name} completada:")
        print(f"     Total filas: {row_count:,}")
        print(f"     Tiempo: {elapsed:.2f}s | Velocidad: {rate:,.0f} filas/seg")
        return row_count

    except Exception as e:
        elapsed = time.time() - start_time
        log_audit_end(cursor, audit_id, 0, elapsed, str(e))
        print(f"[ERROR] Fallo la ingestion de silver.{table_name}: {e}")
        raise


def run_silver_ingestion(single_table=None):
    batch_id = f"batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    print(f"INICIANDO INGESTION SILVER (Batch: {batch_id})")

    conn = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
    )
    conn.autocommit = True
    cursor = conn.cursor()

    targets = [single_table] if single_table else TABLE_ORDER
    total_loaded = 0

    for table in targets:
        try:
            total_loaded += ingest_table(cursor, table, batch_id)
        except Exception:
            conn.rollback()
            break

    print("\n" + "=" * 60)
    print(f"RESUMEN INGESTION SILVER: {total_loaded:,} filas totales procesadas.")
    print("=" * 60)

    cursor.close()
    conn.close()


if __name__ == "__main__":
    table_arg = sys.argv[1] if len(sys.argv) > 1 else None
    run_silver_ingestion(table_arg)