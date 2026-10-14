"""
ingest_tracks_sliced.py
=======================
Ingestión masiva y controlada de exactamente 15,000,000 de pistas reales de MusicBrainz
en silver.track mediante streaming bufferizado a PostgreSQL COPY, optimizando el uso de disco.
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

TRACK_FILE = BASE_DIR / "data" / "raw" / "mbdump" / "track"
TARGET_ROWS = 15_000_000


class MaxLineReader:
    def __init__(self, filepath, max_lines, buffer_size=131072):
        self.f = open(filepath, "r", encoding="utf-8", errors="replace")
        self.max_lines = max_lines
        self.buffer_size = buffer_size
        self.lines_read = 0
        self.last_log_time = time.time()
        self.last_log_lines = 0

    def read(self, size=None):
        if self.lines_read >= self.max_lines:
            return ""

        effective_size = size or self.buffer_size
        chunk = []
        bytes_count = 0

        while bytes_count < effective_size and self.lines_read < self.max_lines:
            line = self.f.readline()
            if not line:
                break
            chunk.append(line)
            bytes_count += len(line)
            self.lines_read += 1

            if self.lines_read % 1_000_000 == 0 and self.lines_read != self.last_log_lines:
                now = time.time()
                elapsed = now - self.last_log_time
                rate = 1_000_000 / max(elapsed, 0.001)
                pct = (self.lines_read / self.max_lines) * 100
                print(f"-> Progreso: {self.lines_read:,} / {self.max_lines:,} ({pct:.1f}%) | Velocidad: {rate:,.0f} filas/seg", flush=True)
                self.last_log_time = now
                self.last_log_lines = self.lines_read

        return "".join(chunk)

    def close(self):
        self.f.close()


def ingest_tracks():
    if not TRACK_FILE.exists():
        print(f"[ERROR] No existe el archivo raw: {TRACK_FILE}")
        sys.exit(1)

    batch_id = f"batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    print("=" * 70)
    print(f"INGESTION MASIVA CONTROLADA DE TRACKS (Meta: {TARGET_ROWS:,} filas reales)")
    print(f"Batch: {batch_id} | Archivo: {TRACK_FILE.name} ({TRACK_FILE.stat().st_size / (1024*1024):.2f} MB)")
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

    # Registrar inicio en auditoría
    cursor.execute("""
        INSERT INTO meta.etl_audit (batch_id, layer, table_name, operation, status)
        VALUES (%s, 'RAW_TO_SILVER', 'silver.track', 'BULK_COPY_SLICED', 'STARTED')
        RETURNING audit_id;
    """, (batch_id,))
    audit_id = cursor.fetchone()[0]

    start_time = time.time()

    try:
        print("-> Truncando silver.track para carga limpia...")
        cursor.execute("TRUNCATE TABLE silver.track RESTART IDENTITY CASCADE;")

        print(f"-> Iniciando streaming de {TARGET_ROWS:,} pistas via COPY FROM STDIN...")
        reader = MaxLineReader(TRACK_FILE, TARGET_ROWS)
        copy_sql = "COPY silver.track FROM STDIN WITH (FORMAT text, DELIMITER E'\\t', NULL '\\N')"
        cursor.copy_expert(copy_sql, reader)
        reader.close()

        elapsed = time.time() - start_time

        cursor.execute("SELECT count(*) FROM silver.track;")
        actual_count = cursor.fetchone()[0]

        cursor.execute("""
            UPDATE meta.etl_audit
            SET status = 'SUCCESS',
                rows_inserted = %s,
                end_time = clock_timestamp(),
                duration_seconds = %s
            WHERE audit_id = %s;
        """, (actual_count, elapsed, audit_id))

        rate = actual_count / max(elapsed, 0.001)
        print("\n" + "=" * 70)
        print(f"[EXITO] silver.track completada:")
        print(f"        Total registros cargados: {actual_count:,}")
        print(f"        Tiempo total: {elapsed:.2f}s | Promedio: {rate:,.0f} filas/seg")
        print("=" * 70)

    except Exception as e:
        elapsed = time.time() - start_time
        cursor.execute("""
            UPDATE meta.etl_audit
            SET status = 'FAILED',
                error_message = %s,
                end_time = clock_timestamp(),
                duration_seconds = %s
            WHERE audit_id = %s;
        """, (str(e), elapsed, audit_id))
        print(f"\n[ERROR] Fallo la carga de silver.track: {e}")
        sys.exit(1)

    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    ingest_tracks()