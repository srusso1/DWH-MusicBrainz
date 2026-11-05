"""
generar_datos_junta.py
======================
Ejecuta en Databricks la consulta de cada widget del dashboard, sin filtros de
página, y escribe docs/build/datos_junta.json. El guion para la junta directiva
narra estos resultados, los mismos que se ven en pantalla.

Requisitos: Databricks CLI autenticada. Variables opcionales:
    DATABRICKS_PROFILE       perfil de la CLI (predeterminado: musicbrainz)
    DATABRICKS_WAREHOUSE_ID  SQL Warehouse (predeterminado: el primero del workspace)
    DATABRICKS_CLI           ruta del ejecutable si no está en el PATH

Uso:
    python scripts/generar_datos_junta.py
"""

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DASHBOARD = BASE_DIR / "databricks" / "dashboards" / "DWMusicBrainz.lvdash.json"
SALIDA = BASE_DIR / "docs" / "build" / "datos_junta.json"
PERFIL = os.getenv("DATABRICKS_PROFILE", "musicbrainz")
AGREGADO = re.compile(r"\b(SUM|COUNT|AVG|MIN|MAX)\s*\(", re.I)
SIN_DATOS = ("filter-", "range-slider")


def localizar_cli():
    ruta = os.getenv("DATABRICKS_CLI") or shutil.which("databricks")
    if ruta:
        return ruta
    paquetes = Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft" / "WinGet" / "Packages"
    encontrados = sorted(paquetes.glob("Databricks.DatabricksCLI_*/databricks.exe"))
    if encontrados:
        return str(encontrados[0])
    sys.exit("No se encontró la Databricks CLI; define DATABRICKS_CLI.")


CLI = localizar_cli()


def cli(*args):
    r = subprocess.run([CLI, *args, "--profile", PERFIL], capture_output=True, text=True, encoding="utf-8")
    if r.returncode != 0:
        sys.exit(f"Falló la CLI ({' '.join(args[:3])}): {r.stderr[:300]}")
    return json.loads(r.stdout)


WAREHOUSE = os.getenv("DATABRICKS_WAREHOUSE_ID") or cli("warehouses", "list", "-o", "json")[0]["id"]


def consulta(sql):
    with tempfile.TemporaryDirectory() as d:
        ruta = Path(d) / "q.json"
        ruta.write_text(json.dumps({"warehouse_id": WAREHOUSE, "statement": sql, "wait_timeout": "50s"}), encoding="utf-8")
        r = cli("api", "post", "/api/2.0/sql/statements", "--json", f"@{ruta}")
    if r["status"]["state"] != "SUCCEEDED":
        sys.exit(f"Falló la consulta: {r['status']}\n{sql[:400]}")
    columnas = [c["name"] for c in r["manifest"]["schema"]["columns"]]
    return [dict(zip(columnas, fila)) for fila in r.get("result", {}).get("data_array", [])]


def valor(v):
    if v is None:
        return None
    try:
        n = float(v)
    except (TypeError, ValueError):
        return v
    return int(n) if n.is_integer() else n


def consulta_widget(widget, datasets):
    q = widget["queries"][0]["query"]
    base = datasets[q["datasetName"]]
    campos = q.get("fields", [])
    seleccion = ", ".join(f"{c['expression']} AS `{c['name']}`" for c in campos)
    sql = f"SELECT {seleccion} FROM ({base})"
    if q.get("filters"):
        sql += " WHERE " + " AND ".join(f"({f['expression']})" for f in q["filters"])
    grupo = [c["expression"] for c in campos if not AGREGADO.search(c["expression"])]
    hay_agregado = any(AGREGADO.search(c["expression"]) for c in campos)
    if grupo and hay_agregado:
        sql += " GROUP BY " + ", ".join(grupo)
    return [{k: valor(v) for k, v in fila.items()} for fila in consulta(sql)]


def main():
    d = json.loads(DASHBOARD.read_text(encoding="utf-8"))
    datasets = {x["name"]: "".join(x["queryLines"]) for x in d["datasets"]}
    salida = {}
    for pagina in d["pages"]:
        for bloque in pagina["layout"]:
            w = bloque["widget"]
            spec = w.get("spec")
            if not spec or spec["widgetType"].startswith(SIN_DATOS):
                continue
            filas = consulta_widget(w, datasets)
            salida[w["name"]] = {
                "pagina": pagina["displayName"],
                "tipo": spec["widgetType"],
                "titulo": spec.get("frame", {}).get("title"),
                "filas": filas,
            }
            print(w["name"], len(filas))
    SALIDA.write_text(json.dumps(salida, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[OK] {SALIDA}")


if __name__ == "__main__":
    main()
