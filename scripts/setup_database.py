"""
setup_database.py
=================
Script de inicialización de esquemas, tablas, particiones y vistas materializadas
para el Data Warehouse DWMusicBrainz en PostgreSQL 16.
"""

import os
import sys
import time
from pathlib import Path
import psycopg2
from dotenv import load_dotenv

# Cargar variables de entorno
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "5435"))
DB_NAME = os.getenv("DB_NAME", "dw_musicbrainz")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres123")

SQL_FILES = [
    BASE_DIR / "sql" / "meta" / "01_schema_meta.sql",
    BASE_DIR / "sql" / "silver" / "02_create_silver_tables.sql",
    BASE_DIR / "sql" / "gold" / "03_dimensions_facts.sql",
    BASE_DIR / "sql" / "gold" / "04_indexes_partitions.sql",
    BASE_DIR / "sql" / "gold" / "05_aggregations.sql",
]


def run_setup():
    print("=" * 70)
    print("INICIALIZACION DE BASE DE DATOS - DWMusicBrainz")
    print("=" * 70)
    print(f"Host: {DB_HOST}:{DB_PORT} | DB: {DB_NAME} | User: {DB_USER}")

    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
        )
        conn.autocommit = True
        cursor = conn.cursor()
        print("[OK] Conexion exitosa a PostgreSQL.\n")

        total_start = time.time()
        for sql_file in SQL_FILES:
            if not sql_file.exists():
                print(f"[ERROR] No existe el archivo: {sql_file}")
                sys.exit(1)

            rel_path = sql_file.relative_to(BASE_DIR)
            print(f"-> Ejecutando: {rel_path} ...", end=" ", flush=True)
            start_t = time.time()
            sql_content = sql_file.read_text(encoding="utf-8-sig")
            cursor.execute(sql_content)
            elapsed = time.time() - start_t
            print(f"OK ({elapsed:.2f}s)")

        total_elapsed = time.time() - total_start
        print("\n" + "=" * 70)
        print(f"[EXITO] TODOS LOS ESQUEMAS Y TABLAS CREADOS EXITOSAMENTE ({total_elapsed:.2f}s)")
        print("=" * 70)

        # Resumen de esquemas y tablas creadas
        cursor.execute("""
            SELECT table_schema, count(*) 
            FROM information_schema.tables 
            WHERE table_schema IN ('meta', 'silver', 'gold')
            GROUP BY table_schema
            ORDER BY table_schema;
        """)
        schemas = cursor.fetchall()
        print("\nTablas creadas por esquema:")
        for schema, count in schemas:
            print(f" - Esquema '{schema}': {count} tablas")

        cursor.close()
        conn.close()

    except Exception as e:
        print(f"\n[ERROR FATAL] Fallo la inicializacion: {e}")
        sys.exit(1)


if __name__ == "__main__":
    run_setup()