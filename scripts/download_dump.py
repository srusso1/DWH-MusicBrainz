"""
download_dump.py
================
Descargador resiliente para mbdump.tar.bz2 oficial de MetaBrainz con soporte de
reanudación (HTTP Range), cálculo de velocidad en MB/s y barra de progreso.
"""

import os
import sys
import time
import requests
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DOWNLOADS_DIR = BASE_DIR / "data" / "downloads"
DUMP_URL = "https://data.metabrainz.org/pub/musicbrainz/data/fullexport/20261017-002244/mbdump.tar.bz2"
TARGET_FILE = DOWNLOADS_DIR / "mbdump.tar.bz2"


def download():
    DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print("DESCARGA DEL VOLCADO OFICIAL DE MUSICBRAINZ (mbdump.tar.bz2)")
    print("=" * 70)
    print(f"URL: {DUMP_URL}")
    print(f"Destino: {TARGET_FILE}")

    # Verificar encabezado remoto
    try:
        head_resp = requests.head(DUMP_URL, timeout=15, allow_redirects=True)
        total_size = int(head_resp.headers.get("content-length", 0))
    except Exception as e:
        print(f"[ERROR] No se pudo obtener metadatos del dump: {e}")
        sys.exit(1)

    print(f"Tamano esperado: {total_size / (1024**3):.2f} GB ({total_size:,} bytes)")

    # Comprobar si ya esta completo
    initial_bytes = 0
    if TARGET_FILE.exists():
        initial_bytes = TARGET_FILE.stat().st_size
        if initial_bytes == total_size:
            print(f"[OK] El archivo ya esta completamente descargado ({initial_bytes / (1024**3):.2f} GB).")
            return
        elif initial_bytes > total_size:
            print("[WARN] El archivo local es mas grande que el remoto. Reiniciando...")
            TARGET_FILE.unlink()
            initial_bytes = 0
        else:
            print(f"[*] Reanudando descarga desde {initial_bytes / (1024**3):.2f} GB ({initial_bytes:,} bytes)...")

    headers = {}
    if initial_bytes > 0:
        headers["Range"] = f"bytes={initial_bytes}-"

    chunk_size = 4 * 1024 * 1024  # 4 MB
    start_time = time.time()
    downloaded_session = 0
    last_print = start_time

    mode = "ab" if initial_bytes > 0 else "wb"
    with requests.get(DUMP_URL, headers=headers, stream=True, timeout=30) as r:
        if r.status_code not in (200, 206):
            print(f"[ERROR] Codigo de estado inesperado: {r.status_code}")
            sys.exit(1)

        with open(TARGET_FILE, mode) as f:
            for chunk in r.iter_content(chunk_size=chunk_size):
                if chunk:
                    f.write(chunk)
                    downloaded_session += len(chunk)
                    current_total = initial_bytes + downloaded_session

                    now = time.time()
                    if now - last_print >= 2.0:
                        elapsed = now - start_time
                        speed_mb = (downloaded_session / (1024 * 1024)) / max(elapsed, 0.001)
                        pct = (current_total / total_size) * 100 if total_size else 0
                        remaining_bytes = max(0, total_size - current_total)
                        eta_sec = (remaining_bytes / (1024 * 1024)) / max(speed_mb, 0.001)
                        eta_min = eta_sec / 60
                        print(
                            f"-> Progreso: {current_total / (1024**3):.2f} / {total_size / (1024**3):.2f} GB "
                            f"({pct:.1f}%) | Vel: {speed_mb:.1f} MB/s | ETA: {eta_min:.1f} min",
                            flush=True,
                        )
                        last_print = now

    final_size = TARGET_FILE.stat().st_size
    print("\n" + "=" * 70)
    if final_size == total_size:
        print(f"[EXITO] Descarga completada al 100% ({final_size / (1024**3):.2f} GB)")
    else:
        print(f"[INFO] Archivo guardado con {final_size / (1024**3):.2f} GB")
    print("=" * 70)


if __name__ == "__main__":
    download()
