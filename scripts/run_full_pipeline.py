"""
run_full_pipeline.py
====================
Orquestador principal E2E para el Data Warehouse DWMusicBrainz:
1. Ingesta Silver (Extracción y COPY bulk de tablas dimensionales y puente)
2. Ingesta Silver Track (Carga masiva optimizada de 15,000,000 filas reales)
3. Pipeline Gold (Poblado de 6 dimensiones conformadas, tabla de hechos y vistas materializadas)
4. Auditoría y Certificación Kimball (verify_dwh.py)
"""

import sys
import time
import subprocess
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
PYTHON_EXE = BASE_DIR / ".venv" / "Scripts" / "python.exe"
if not PYTHON_EXE.exists():
    PYTHON_EXE = Path(sys.executable)

STEPS = [
    ("1. INGESTION CAPA SILVER (Tablas maestras y puente)", BASE_DIR / "etl" / "silver" / "ingest_silver.py"),
    ("2. INGESTION OPTIMIZADA DE PISTAS (15M filas)", BASE_DIR / "etl" / "silver" / "ingest_tracks_sliced.py"),
    ("3. CONSTRUCCION CAPA GOLD (Modelo en Estrella Kimball)", BASE_DIR / "etl" / "gold" / "run_gold_pipeline.py"),
    ("4. AUDITORIA Y CERTIFICACION FINAL DWH", BASE_DIR / "scripts" / "verify_dwh.py"),
]


def run_pipeline():
    print("=" * 80)
    print("INICIANDO EJECUCION INTEGRAL E2E - DWMusicBrainz")
    print("=" * 80)
    t_global = time.time()

    for idx, (title, script_path) in enumerate(STEPS, start=1):
        print("\n" + "#" * 80)
        print(f"PASO {idx}/{len(STEPS)}: {title}")
        print(f"Script: {script_path.relative_to(BASE_DIR)}")
        print("#" * 80 + "\n")

        t_step = time.time()
        ret = subprocess.run([str(PYTHON_EXE), str(script_path)], cwd=str(BASE_DIR))
        if ret.returncode != 0:
            print(f"\n[ERROR CRITICO] El paso {idx} fallo con codigo {ret.returncode}.")
            sys.exit(ret.returncode)

        elapsed = time.time() - t_step
        print(f"\n[OK] Paso {idx} completado en {elapsed / 60:.2f} minutos ({elapsed:.1f}s).")

    total_elapsed = time.time() - t_global
    print("\n" + "=" * 80)
    print(f"PIPELINE E2E COMPLETADO CON EXITO EN {total_elapsed / 60:.2f} MINUTOS.")
    print("=" * 80)


if __name__ == "__main__":
    run_pipeline()
