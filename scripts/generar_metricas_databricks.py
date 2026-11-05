"""
generar_metricas_databricks.py
==============================
Consulta Gold y meta en Databricks y escribe docs/build/metricas_databricks.json,
la única fuente de cifras de la presentación y de los PDF de defensa.

Requisitos: Databricks CLI autenticada. Variables opcionales:
    DATABRICKS_PROFILE       perfil de la CLI (predeterminado: musicbrainz)
    DATABRICKS_WAREHOUSE_ID  SQL Warehouse (predeterminado: el primero del workspace)
    DATABRICKS_CLI           ruta del ejecutable si no está en el PATH

Uso:
    python scripts/generar_metricas_databricks.py
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
SALIDA = BASE_DIR / "docs" / "build" / "metricas_databricks.json"
PERFIL = os.getenv("DATABRICKS_PROFILE", "musicbrainz")
CATALOGO = "workspace"
RUN_COMPLETA = "1040003573052070"
RUN_FINAL = "853384881134750"

G = f"{CATALOGO}.gold"
HECHO = f"{G}.fact_produccion_musical"
DIGITAL = "Digital / Streaming"
OPTICO = "Físico / Óptico"
VINILO = "Físico / Vinilo"
MAGNETICO = "Físico / Magnético"


def localizar_cli():
    explicita = os.getenv("DATABRICKS_CLI")
    if explicita:
        return explicita
    encontrada = shutil.which("databricks")
    if encontrada:
        return encontrada
    paquetes = Path(os.getenv("LOCALAPPDATA", "")) / "Microsoft" / "WinGet" / "Packages"
    for ruta in paquetes.glob("Databricks.DatabricksCLI_*/databricks.exe"):
        return str(ruta)
    sys.exit("No se encontró la CLI de Databricks. Defina DATABRICKS_CLI.")


CLI = localizar_cli()


def cli(*args):
    r = subprocess.run([CLI, *args, "--profile", PERFIL], capture_output=True, text=True, encoding="utf-8")
    if r.returncode != 0:
        sys.exit(f"Falló la CLI ({' '.join(args[:3])}): {r.stderr[:300]}")
    return json.loads(r.stdout)


def warehouse_id():
    return os.getenv("DATABRICKS_WAREHOUSE_ID") or cli("warehouses", "list", "-o", "json")[0]["id"]


WAREHOUSE = warehouse_id()


def consulta(sql):
    """Ejecuta una consulta y devuelve (columnas, filas como listas de texto)."""
    cuerpo = {"warehouse_id": WAREHOUSE, "statement": sql, "wait_timeout": "50s"}
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(cuerpo, f, ensure_ascii=False)
        ruta = f.name
    try:
        r = cli("api", "post", "/api/2.0/sql/statements", "--json", f"@{ruta}")
    finally:
        os.unlink(ruta)
    while r["status"]["state"] in ("PENDING", "RUNNING"):
        time.sleep(3)
        r = cli("api", "get", f"/api/2.0/sql/statements/{r['statement_id']}")
    if r["status"]["state"] != "SUCCEEDED":
        sys.exit(f"Falló la consulta: {r['status']}: {sql[:300]}")
    columnas = [c["name"] for c in r["manifest"]["schema"]["columns"]]
    return columnas, r.get("result", {}).get("data_array", [])


def filas(sql):
    return consulta(sql)[1]


def una(sql):
    return filas(sql)[0]


def entero(x):
    return int(float(x)) if x is not None else 0


def real(x):
    return float(x) if x is not None else None


def conteos(esquema, tablas):
    sql = " UNION ALL ".join(f"SELECT '{t}', count(*) FROM {CATALOGO}.{esquema}.{t}" for t in tablas)
    return {t: entero(n) for t, n in filas(sql)}


def tablas_de(esquema):
    return [
        r[0]
        for r in filas(
            f"SELECT table_name FROM {CATALOGO}.information_schema.tables "
            f"WHERE table_schema = '{esquema}' ORDER BY table_name"
        )
    ]


def detalle_tablas(esquema, tablas):
    resultado = {}
    for t in tablas:
        columnas, datos = consulta(f"DESCRIBE DETAIL {CATALOGO}.{esquema}.{t}")
        fila = dict(zip(columnas, datos[0]))
        resultado[t] = {
            "bytes": entero(fila.get("sizeInBytes")),
            "archivos": entero(fila.get("numFiles")),
            "clustering": fila.get("clusteringColumns"),
        }
    return resultado


def metricas_totales():
    r = una(f"""
        SELECT SUM(lanzamientos_total), SUM(soportes_total), SUM(pistas_total), SUM(grabaciones_unicas_total),
               COUNT(DISTINCT artista_key), SUM(duracion_total_segundos), SUM(duracion_total_minutos),
               SUM(pistas_con_isrc_total), SUM(pistas_largas_total), SUM(pistas_completas_total),
               SUM(pistas_video_total), COUNT(*)
        FROM {HECHO}""")
    t = dict(zip(
        ["lanzamientos", "soportes", "pistas", "grabaciones", "artistas"],
        [entero(x) for x in r[:5]],
    ))
    t.update(
        pistas_isrc=entero(r[7]), pistas_largas=entero(r[8]), pistas_completas=entero(r[9]),
        pistas_video=entero(r[10]), filas_hecho=entero(r[11]), horas=real(r[6]) / 60,
    )
    t["dur_media_min"] = real(r[5]) / t["pistas_completas"] / 60
    t["isrc_pct"] = t["pistas_isrc"] / t["pistas"]
    t["largas_pct"] = t["pistas_largas"] / t["pistas"]
    t["pistas_por_lanzamiento"] = t["pistas"] / t["lanzamientos"]
    t["pistas_por_soporte"] = t["pistas"] / t["soportes"]
    return t


def por_formato():
    return [
        {"categoria": c, "lanzamientos": entero(l), "pistas": entero(p)}
        for c, l, p in filas(f"""
            SELECT x.categoria_formato, SUM(f.lanzamientos_total), SUM(f.pistas_total)
            FROM {HECHO} f JOIN {G}.dim_formato x USING (formato_key)
            GROUP BY 1 ORDER BY 2 DESC""")
    ]


def serie_anual():
    return [
        {"anio": entero(a), "digital": real(d), "optico": real(o), "vinilo": real(v), "magnetico": real(m), "lanzamientos": entero(n)}
        for a, d, o, v, m, n in filas(f"""
            SELECT d.anio,
                   SUM(CASE WHEN x.categoria_formato = '{DIGITAL}' THEN f.lanzamientos_total ELSE 0 END) / SUM(f.lanzamientos_total),
                   SUM(CASE WHEN x.categoria_formato = '{OPTICO}' THEN f.lanzamientos_total ELSE 0 END) / SUM(f.lanzamientos_total),
                   SUM(CASE WHEN x.categoria_formato = '{VINILO}' THEN f.lanzamientos_total ELSE 0 END) / SUM(f.lanzamientos_total),
                   SUM(CASE WHEN x.categoria_formato = '{MAGNETICO}' THEN f.lanzamientos_total ELSE 0 END) / SUM(f.lanzamientos_total),
                   SUM(f.lanzamientos_total)
            FROM {HECHO} f JOIN {G}.dim_fecha d USING (fecha_key) JOIN {G}.dim_formato x USING (formato_key)
            WHERE d.anio BETWEEN 1950 AND 2025 GROUP BY d.anio HAVING SUM(f.lanzamientos_total) > 0 ORDER BY d.anio""")
    ]


def serie_decadas():
    return [
        {"decada": dc, "vinilo": real(v), "optico": real(o), "digital": real(d), "magnetico": real(m),
         "isrc": real(i), "dur_media_min": real(dur), "lanzamientos": entero(n)}
        for dc, v, o, d, m, i, dur, n in filas(f"""
            SELECT d.decada,
                   SUM(CASE WHEN x.categoria_formato = '{VINILO}' THEN f.lanzamientos_total ELSE 0 END) / SUM(f.lanzamientos_total),
                   SUM(CASE WHEN x.categoria_formato = '{OPTICO}' THEN f.lanzamientos_total ELSE 0 END) / SUM(f.lanzamientos_total),
                   SUM(CASE WHEN x.categoria_formato = '{DIGITAL}' THEN f.lanzamientos_total ELSE 0 END) / SUM(f.lanzamientos_total),
                   SUM(CASE WHEN x.categoria_formato = '{MAGNETICO}' THEN f.lanzamientos_total ELSE 0 END) / SUM(f.lanzamientos_total),
                   SUM(f.pistas_con_isrc_total) / SUM(f.pistas_total),
                   SUM(f.duracion_total_segundos) / SUM(f.pistas_completas_total) / 60,
                   SUM(f.lanzamientos_total)
            FROM {HECHO} f JOIN {G}.dim_fecha d USING (fecha_key) JOIN {G}.dim_formato x USING (formato_key)
            WHERE d.anio BETWEEN 1950 AND 2025 GROUP BY d.decada ORDER BY d.decada""")
    ]


def paises():
    return [
        {"pais": p, "lanzamientos": entero(l), "digital": real(d)}
        for p, l, d in filas(f"""
            SELECT g.nombre_pais, SUM(f.lanzamientos_total),
                   SUM(CASE WHEN x.categoria_formato = '{DIGITAL}' THEN f.lanzamientos_total ELSE 0 END) / SUM(f.lanzamientos_total)
            FROM {HECHO} f JOIN {G}.dim_geografia g USING (geografia_key) JOIN {G}.dim_formato x USING (formato_key)
            WHERE g.tipo_area = 'País' GROUP BY 1 HAVING SUM(f.lanzamientos_total) > 0 ORDER BY 2 DESC LIMIT 30""")
    ]


def histograma():
    filas_h = filas(f"""
        SELECT r.orden, r.etiqueta_rango, SUM(f.pistas_total)
        FROM {G}.fact_distribucion_duracion f JOIN {G}.dim_rango_duracion r USING (rango_duracion_key)
        WHERE r.rango_duracion_key > 0 GROUP BY 1, 2 ORDER BY 1""")
    bandas = [{"orden": entero(o), "banda": e, "pistas": entero(n)} for o, e, n in filas_h]
    total = sum(b["pistas"] for b in bandas)
    acumulado, mediana = 0, None
    for b in bandas:
        acumulado += b["pistas"]
        if mediana is None and acumulado >= total / 2:
            mediana = b["banda"]
    moda = max(bandas, key=lambda b: b["pistas"])
    media = real(una(f"""
        SELECT SUM(duracion_total_ms) / SUM(pistas_total) / 60000
        FROM {G}.fact_distribucion_duracion WHERE rango_duracion_key > 0""")[0])
    dos_mayores = sorted(bandas, key=lambda b: b["pistas"], reverse=True)[:2]
    return {
        "bandas": bandas, "total": total, "mediana_banda": mediana, "moda_banda": moda["banda"],
        "moda_pct": moda["pistas"] / total, "media_min": media,
        "mayor_10_pct": bandas[-1]["pistas"] / total,
        "dos_mayores_pct": sum(b["pistas"] for b in dos_mayores) / total,
    }


def pearson():
    resultado = []
    for inicio, fin in [(1950, 2025), (1990, 2025), (2013, 2025)]:
        r, pendiente, n = una(f"""
            WITH anual AS (
                SELECT d.anio, SUM(f.duracion_total_segundos) / SUM(f.pistas_completas_total) / 60 AS dur_min
                FROM {HECHO} f JOIN {G}.dim_fecha d USING (fecha_key)
                WHERE d.anio BETWEEN {inicio} AND {fin} GROUP BY d.anio)
            SELECT corr(anio, dur_min), regr_slope(dur_min, anio), COUNT(*) FROM anual""")
        resultado.append({"inicio": inicio, "fin": fin, "r": real(r), "pendiente_s": real(pendiente) * 60, "n": entero(n)})
    return resultado


def emergentes():
    total, con_isrc = una(f"""
        WITH a AS (
            SELECT f.artista_key, SUM(f.pistas_con_isrc_total) AS isrc, SUM(f.pistas_total) AS pistas,
                   SUM(f.lanzamientos_total) AS lanzamientos
            FROM {HECHO} f JOIN {G}.dim_artista d USING (artista_key)
            WHERE d.anio_inicio >= 2015 GROUP BY f.artista_key)
        SELECT COUNT(*), COUNT_IF(isrc = pistas AND lanzamientos > 0) FROM a""")
    return {"total": entero(total), "isrc_100": entero(con_isrc)}


def datos_especiales():
    sin_fecha = una(f"SELECT SUM(lanzamientos_total), SUM(pistas_total) FROM {HECHO} WHERE fecha_key = 0")
    futuras = una(f"""
        SELECT COALESCE(SUM(f.pistas_total), 0) FROM {HECHO} f JOIN {G}.dim_fecha d USING (fecha_key)
        WHERE d.anio > YEAR(CURRENT_DATE)""")
    geografia_cero = una(f"SELECT SUM(pistas_total) FROM {HECHO} WHERE geografia_key = 0")
    mundial = una(f"""
        SELECT SUM(f.lanzamientos_total) FROM {HECHO} f JOIN {G}.dim_geografia g USING (geografia_key)
        WHERE g.nombre_area = '[Worldwide]'""")
    afganistan = una(f"""
        SELECT SUM(f.lanzamientos_total), SUM(f.pistas_total) FROM {HECHO} f JOIN {G}.dim_geografia g USING (geografia_key)
        WHERE g.nombre_pais = 'Afghanistan' AND g.tipo_area = 'País'""")
    return {
        "lanzamientos_sin_fecha": entero(sin_fecha[0]), "pistas_sin_fecha": entero(sin_fecha[1]),
        "pistas_fecha_futura": entero(futuras[0]), "pistas_sin_geografia": entero(geografia_cero[0]),
        "lanzamientos_worldwide": entero(mundial[0]),
        "afganistan_lanzamientos": entero(afganistan[0]), "afganistan_pistas": entero(afganistan[1]),
    }


def ejemplo_grano():
    """Un lanzamiento real: filas en el hecho de pista frente al hecho agregado."""
    r = una(f"""
        SELECT COUNT(*), SUM(duracion_ms), SUM(CAST(es_primera_pista_lanzamiento AS INT)),
               SUM(CAST(tiene_isrc AS INT)), MIN(fecha_key), COUNT(DISTINCT soporte_id)
        FROM {G}.fact_pista WHERE lanzamiento_id = 1438346""")
    return {
        "lanzamiento_id": 1438346, "pistas": entero(r[0]), "duracion_ms": entero(r[1]),
        "cuenta_lanzamiento": entero(r[2]), "pistas_isrc": entero(r[3]), "fecha_key": entero(r[4]), "soportes": entero(r[5]),
    }


def calidad_log():
    """Último resultado de cada regla registrada en meta.data_quality_log."""
    registros = filas(f"""
        SELECT severidad, estado, COUNT(*)
        FROM (
            SELECT severidad, estado,
                   ROW_NUMBER() OVER (PARTITION BY regla ORDER BY registrado_en DESC) AS n
            FROM {CATALOGO}.meta.data_quality_log)
        WHERE n = 1 GROUP BY 1, 2""")
    return [{"severidad": s, "estado": e, "reglas": entero(n)} for s, e, n in registros]


def reglas_grupos():
    return [
        {"grupo": g, "reglas": entero(n)}
        for g, n in filas(f"""
            SELECT split(regla, '[.]')[0], COUNT(DISTINCT regla)
            FROM {CATALOGO}.meta.data_quality_log GROUP BY 1 ORDER BY 1""")
    ]


def corrida(run_id):
    r = cli("jobs", "get-run", run_id, "-o", "json")
    tareas = [
        {
            "tarea": t["task_key"],
            "segundos": round(t.get("execution_duration", 0) / 1000),
            "estado": t.get("state", {}).get("result_state"),
        }
        for t in r.get("tasks", [])
        if t.get("state", {}).get("result_state") != "DISABLED"
    ]
    return {"run_id": run_id, "segundos": round(r.get("run_duration", 0) / 1000), "estado": r["state"].get("result_state"), "tareas": tareas}


def prueba_capacidad():
    return [
        {"etapa": e, "segundos": real(s), "filas": entero(n)}
        for e, s, n in filas(f"SELECT stage, seconds, rows FROM {CATALOGO}.meta.spike_metrics ORDER BY logged_at")
    ]


def main():
    silver = [t for t in tablas_de("silver")]
    gold = [t for t in tablas_de("gold") if not t.startswith("spike_")]
    bronze = tablas_de("bronze")
    print(f"Warehouse listo. Tablas: bronze {len(bronze)}, silver {len(silver)}, gold {len(gold)}")

    conteo_silver = conteos("silver", silver)
    principales = {t: n for t, n in conteo_silver.items() if not t.startswith("catalogo_")}
    m = {
        "generado_utc": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M"),
        "version_volcado": "20261104-002222",
        "schema_sequence": 31,
        "totales": metricas_totales(),
        "conteos": {
            "bronze": conteos("bronze", bronze),
            "silver": conteo_silver,
            "silver_principales_total": sum(principales.values()),
            "gold": conteos("gold", gold),
        },
        "detalle": {"silver": detalle_tablas("silver", silver), "gold": detalle_tablas("gold", gold)},
        "formatos": por_formato(),
        "anual": serie_anual(),
        "decadas": serie_decadas(),
        "paises": paises(),
        "idiomas": [
            {"idioma": i, "lanzamientos": entero(n)}
            for i, n in filas(f"""
                SELECT i.nombre_idioma, SUM(f.lanzamientos_total) FROM {HECHO} f JOIN {G}.dim_idioma i USING (idioma_key)
                WHERE i.idioma_id <> 0 GROUP BY 1 ORDER BY 2 DESC LIMIT 8""")
        ],
        "tipos_artista": [
            {"tipo": t, "lanzamientos": entero(n)}
            for t, n in filas(f"""
                SELECT a.tipo_artista, SUM(f.lanzamientos_total) FROM {HECHO} f JOIN {G}.dim_artista a USING (artista_key)
                GROUP BY 1 ORDER BY 2 DESC""")
        ],
        "calidad": [
            {"calidad": c, "lanzamientos": entero(n)}
            for c, n in filas(f"""
                SELECT l.calidad_datos, SUM(f.lanzamientos_total) FROM {HECHO} f JOIN {G}.dim_lanzamiento l USING (lanzamiento_key)
                GROUP BY 1 ORDER BY 2 DESC""")
        ],
        "top_artistas": [
            {"artista": a, "lanzamientos": entero(l), "pistas": entero(p)}
            for a, l, p in filas(f"""
                SELECT a.nombre_artista, SUM(f.lanzamientos_total), SUM(f.pistas_total)
                FROM {HECHO} f JOIN {G}.dim_artista a USING (artista_key)
                WHERE a.nombre_artista NOT LIKE '[%' GROUP BY 1 ORDER BY 2 DESC LIMIT 10""")
        ],
        "histograma": histograma(),
        "pearson": pearson(),
        "emergentes": emergentes(),
        "especiales": datos_especiales(),
        "ejemplo_grano": ejemplo_grano(),
        "calidad_log": calidad_log(),
        "reglas_grupos": reglas_grupos(),
        "prueba_capacidad": prueba_capacidad(),
        "corridas": {"completa": corrida(RUN_COMPLETA), "final": corrida(RUN_FINAL)},
    }

    anual = m["anual"]
    posteriores = [a for a in anual if a["anio"] >= 1990 and (a["digital"] or 0) > (a["optico"] or 0)]
    m["cruce_digital"] = posteriores[0]["anio"]
    m["ultimo_anio"] = next(a for a in anual if a["anio"] == 2025)

    # Cifras de la entrega anterior (segundo corte, PostgreSQL). No se pueden recalcular:
    # la base local ya no forma parte de esta entrega y quedan como referencia histórica.
    m["carga_anterior"] = {
        "pistas": 15_000_000, "lanzamientos": 1_728_603, "soportes": 1_882_045,
        "filas_hecho": 2_967_681, "silver_filas": 98_641_617,
        "r_1950_2025": 0.89, "r_2013_2025": -0.57, "cruce_digital": 2012,
    }

    # Datos del proceso registrados durante la migración; no quedan en una tabla consultable.
    m["proceso"] = {
        "pruebas_fixtures_verde": 26,
        "caminos_evento": {
            "pais_unico": 5_148_387, "sin_pais": 487_239, "diez_o_mas": 45_043,
            "dos_a_nueve": 30_706, "worldwide_explicito": 3_223,
        },
        "afganistan_antes": {"lanzamientos": 32_206, "pistas": 241_780, "artistas": 23_640},
        "worldwide_antes": 2_050_347,
        "pistas_movidas_area": 639_777,
        "filtros": {
            "anio": {"rango": "2000–2010", "lanzamientos": 1_169_839, "pistas": 15_574_369, "artistas": 599_256, "isrc": "25,1 %"},
            "decada": {"valor": "1980s", "pistas_por_lanzamiento": "9,2", "duracion_min": "4,07", "largas": "17,0 %", "horas": "132.202"},
        },
        "almacen": {"consulta_min_s": 1.3, "consulta_max_s": 3.1},
    }

    SALIDA.parent.mkdir(parents=True, exist_ok=True)
    SALIDA.write_text(json.dumps(m, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[OK] {SALIDA}")


if __name__ == "__main__":
    main()
