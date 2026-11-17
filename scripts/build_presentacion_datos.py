"""
build_presentacion_datos.py
===========================
Prepara los datos y las imagenes del sitio de presentaciones (carpeta presentacion/).

- Lee docs/build/metricas_databricks.json (corrida real del pipeline en Databricks).
- Lee docs/build/metricas_streaming.json si existe (corrida real de la capa Kafka + Spark).
- Escribe presentacion/assets/datos.js como `window.M = {...}` para que las
  diapositivas funcionen tambien abiertas como archivo local (sin fetch).
- Copia las capturas del dashboard a presentacion/assets/img/.

Uso:
    python scripts/build_presentacion_datos.py
"""
import json
import shutil
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
BUILD = BASE / "docs" / "build"
SITIO = BASE / "presentacion" / "assets"
IMAGENES = ["dash_resumen.png", "dash_detallado.png", "dash_calidad.png", "dash_drill.png"]


def main() -> None:
    metricas = json.loads((BUILD / "metricas_databricks.json").read_text(encoding="utf-8"))
    metricas.pop("detalle", None)  # bytes por tabla: no se usa en las diapositivas

    streaming_path = BUILD / "metricas_streaming.json"
    metricas["streaming"] = (
        json.loads(streaming_path.read_text(encoding="utf-8")) if streaming_path.exists() else {"ejecutado": False}
    )

    dashboard = json.loads((BASE / "databricks" / "dashboards" / "DWMusicBrainz.lvdash.json").read_text(encoding="utf-8"))
    metricas["dashboard"] = {
        "paginas": len(dashboard["pages"]),
        "widgets": sum(len(p["layout"]) for p in dashboard["pages"]),
        "datasets": len(dashboard["datasets"]),
    }

    SITIO.mkdir(parents=True, exist_ok=True)
    contenido = "/* Generado por scripts/build_presentacion_datos.py. No editar a mano. */\nwindow.M = "
    contenido += json.dumps(metricas, ensure_ascii=False, separators=(",", ":")) + ";\n"
    (SITIO / "datos.js").write_text(contenido, encoding="utf-8")

    destino = SITIO / "img"
    destino.mkdir(exist_ok=True)
    for nombre in IMAGENES:
        shutil.copyfile(BUILD / nombre, destino / nombre)

    print(f"[OK] datos.js ({len(contenido) // 1024} KB) e {len(IMAGENES)} imagenes en {SITIO}")


if __name__ == "__main__":
    main()
