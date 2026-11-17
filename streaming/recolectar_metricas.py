"""Recolecta metricas reales de una corrida de la demo y las guarda en JSON.

Fuentes: resumenes del productor, offsets de Kafka (confluent-kafka),
conteos de PostgreSQL (psycopg2) y conteo del lago Bronze (argumento).
No inventa valores: lo que no se pudo medir queda en null.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# Same credentials Docker Compose reads for the postgres container.
load_dotenv(Path(__file__).resolve().parent.parent / ".env")


def offsets_topico(bootstrap: str, topico: str) -> dict:
    from confluent_kafka import Consumer, TopicPartition

    c = Consumer({"bootstrap.servers": bootstrap, "group.id": "dwmb-metricas",
                  "enable.auto.commit": False})
    try:
        meta = c.list_topics(topico, timeout=10)
        parts = sorted(meta.topics[topico].partitions)
        res = {}
        for p in parts:
            bajo, alto = c.get_watermark_offsets(TopicPartition(topico, p), timeout=10)
            res[str(p)] = alto - bajo
        return {"particiones": len(parts), "mensajes_por_particion": res,
                "mensajes_total": sum(res.values())}
    finally:
        c.close()


def metricas_postgres() -> dict:
    import psycopg2

    conn = psycopg2.connect(
        host=os.getenv("PG_HOST", "localhost"), port=int(os.getenv("PG_PORT", "5435")),
        dbname=os.getenv("PG_DATABASE", "dw_musicbrainz"),
        user=os.getenv("PG_USER", "postgres"), password=os.getenv("PG_PASSWORD", "postgres123"))
    with conn, conn.cursor() as cur:
        cur.execute("""SELECT count(*), count(DISTINCT mbid), coalesce(sum(versiones), 0)
                       FROM streaming.lanzamientos_evento""")
        filas, distintos, versiones = cur.fetchone()
        cur.execute("""SELECT count(*), coalesce(sum(lanzamientos), 0), coalesce(sum(pistas), 0)
                       FROM streaming.lanzamientos_ventana""")
        ventanas, lanz_ventanas, pistas = cur.fetchone()
        cur.execute("SELECT consulta, count(*) FROM streaming.control_lotes GROUP BY consulta")
        lotes = dict(cur.fetchall())
        cur.execute("SELECT latencia_prom_s, latencia_p50_s, latencia_max_s FROM streaming.v_latencia")
        prom, p50, mx = cur.fetchone()
        cur.execute("""SELECT pais, formato, sum(lanzamientos) FROM streaming.lanzamientos_ventana
                       GROUP BY pais, formato ORDER BY 3 DESC LIMIT 5""")
        top = [{"pais": a, "formato": b, "lanzamientos": int(c)} for a, b, c in cur.fetchall()]
    conn.close()
    return {
        "filas_lanzamientos_evento": filas, "mbid_distintos": distintos,
        "suma_versiones": int(versiones),
        "filas_lanzamientos_ventana": ventanas,
        "suma_lanzamientos_en_ventanas": int(lanz_ventanas), "suma_pistas_en_ventanas": int(pistas),
        "lotes_aplicados_por_consulta": lotes,
        "latencia_extremo_a_extremo_s": {
            "promedio": float(prom) if prom is not None else None,
            "p50": float(p50) if p50 is not None else None,
            "maximo": float(mx) if mx is not None else None},
        "top5_pais_formato": top,
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--productor", action="append", default=[], help="JSON de resumen del productor")
    p.add_argument("--bronze", help="JSON del inspector del lago (linea RESULTADO_LAGO)")
    p.add_argument("--reinicio", help="JSON con el detalle de la prueba de reinicio")
    p.add_argument("--bootstrap", default=os.getenv("KAFKA_BOOTSTRAP", "localhost:9092"))
    p.add_argument("--salida", default="docs/build/metricas_streaming.json")
    a = p.parse_args()

    resumenes = [json.loads(Path(f).read_text(encoding="utf-8")) for f in a.productor]
    m = {
        "ejecutado": True,
        "timestamp": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "fuente_eventos": "streaming/fixtures/lanzamientos_muestra.jsonl (299 lanzamientos reales "
                          "de la API WS2 de MusicBrainz + 5 lineas de inyeccion de fallas)",
        "productor": {
            "corridas": resumenes,
            "eventos_producidos": sum(r.get("producidos", 0) for r in resumenes),
            "eventos_entregados": sum(r.get("entregados", 0) for r in resumenes),
            "entregas_fallidas": sum(r.get("fallidos", 0) for r in resumenes),
        },
        "kafka": {
            "musicbrainz.lanzamientos": offsets_topico(a.bootstrap, "musicbrainz.lanzamientos"),
            "musicbrainz.lanzamientos.dlq": offsets_topico(a.bootstrap, "musicbrainz.lanzamientos.dlq"),
        },
        "postgres": metricas_postgres(),
        "bronze": json.loads(Path(a.bronze).read_text(encoding="utf-8")) if a.bronze else None,
        "prueba_reinicio": json.loads(Path(a.reinicio).read_text(encoding="utf-8")) if a.reinicio else None,
    }
    m["consumidos_validos"] = (m["bronze"] or {}).get("filas")
    m["enviados_dlq"] = m["kafka"]["musicbrainz.lanzamientos.dlq"]["mensajes_total"]
    pg = m["postgres"]
    m["sin_duplicados"] = (pg["filas_lanzamientos_evento"] == pg["mbid_distintos"] == pg["suma_versiones"]
                           and (m["bronze"] is None or m["bronze"]["filas"] == m["bronze"]["mbid_distintos"]))
    Path(a.salida).parent.mkdir(parents=True, exist_ok=True)
    Path(a.salida).write_text(json.dumps(m, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(m, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
