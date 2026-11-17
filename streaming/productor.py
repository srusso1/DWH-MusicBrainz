"""Productor Kafka de lanzamientos reales de MusicBrainz.

Fuentes:
  * ``--fuente api``     sondea la API publica WS2 (JSON) respetando 1 solicitud/s.
  * ``--fuente archivo`` reproduce un archivo JSONL a una tasa configurable.

Garantias del productor (ver streaming/README.md):
  * ``enable.idempotence=True`` + ``acks=all``: sin duplicados por reintentos y
    sin perdida mientras quede una replica sincronizada.
  * Clave = MBID del lanzamiento: todos los eventos de un mismo lanzamiento
    caen en la misma particion y conservan su orden.
  * ``SIGINT``/``SIGTERM`` -> se detiene la lectura y se hace ``flush`` de lo
    pendiente antes de salir.

Ejemplos:
  python -m streaming.productor --fuente archivo \
      --archivo streaming/fixtures/lanzamientos_muestra.jsonl --eventos-por-segundo 50
  python -m streaming.productor --fuente api --desde 2026-11-01 --paginas 3
  python -m streaming.productor --fuente api --sin-kafka --salida muestra.jsonl
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import signal
import sys
import time
from pathlib import Path
from typing import Any, Dict, Iterator, Optional

if __package__ in (None, ""):
    # Permite ejecutar ``python streaming/productor.py`` ademas de ``-m``.
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from streaming.lib.eventos import (  # noqa: E402
    Deduplicador,
    normalizar_release_api,
    serializar_evento,
)

# User-Agent generico (politica de MusicBrainz): sin datos personales.
USER_AGENT = "DWMusicBrainz-Streaming/1.0 (proyecto academico)"
API_URL = "https://musicbrainz.org/ws/2/release"
INTERVALO_MIN_API_S = 1.1  # limite publico: 1 solicitud por segundo
TOPICO_DEFECTO = "musicbrainz.lanzamientos"


def ahora_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def construir_consulta(desde: str, hasta: str) -> str:
    """Consulta Lucene de la API WS2 para lanzamientos fechados en el rango."""
    return f"date:[{desde} TO {hasta}]"


def clave_de_linea(linea: str) -> Optional[bytes]:
    """Clave Kafka (MBID) de una linea JSONL; ``None`` si no se puede extraer."""
    try:
        obj = json.loads(linea)
    except ValueError:
        return None
    if not isinstance(obj, dict) or not obj.get("mbid"):
        return None
    return str(obj["mbid"]).encode("utf-8")


def leer_lineas_jsonl(ruta: Path) -> Iterator[str]:
    """Lineas no vacias de un JSONL, omitiendo comentarios ``#``."""
    with open(ruta, encoding="utf-8") as fh:
        for linea in fh:
            linea = linea.strip()
            if linea and not linea.startswith("#"):
                yield linea


def eventos_desde_respuesta(
    respuesta: Dict[str, Any], dedup: Deduplicador, evento_ts: Optional[str] = None
) -> Iterator[Dict[str, Any]]:
    """Normaliza los ``releases`` de una respuesta WS2 descartando MBID repetidos."""
    for release in respuesta.get("releases") or []:
        mbid = release.get("id")
        if mbid and dedup.es_nuevo(mbid):
            yield normalizar_release_api(release, evento_ts or ahora_iso(), fuente="api")


class Contadores:
    """Contadores alimentados por el callback de entrega de librdkafka."""

    def __init__(self) -> None:
        self.producidos = 0
        self.entregados = 0
        self.fallidos = 0
        self.por_particion: Dict[int, int] = {}
        self.errores: Dict[str, int] = {}

    def callback_entrega(self, err, msg) -> None:
        if err is not None:
            self.fallidos += 1
            self.errores[str(err)] = self.errores.get(str(err), 0) + 1
            return
        self.entregados += 1
        p = msg.partition()
        self.por_particion[p] = self.por_particion.get(p, 0) + 1

    def resumen(self) -> Dict[str, Any]:
        return {
            "producidos": self.producidos,
            "entregados": self.entregados,
            "fallidos": self.fallidos,
            "por_particion": {str(k): v for k, v in sorted(self.por_particion.items())},
            "errores": self.errores,
        }


def configuracion_productor(bootstrap: str) -> Dict[str, Any]:
    return {
        "bootstrap.servers": bootstrap,
        "client.id": "dwmb-productor-lanzamientos",
        # Entrega exactamente-una-vez por particion dentro de la sesion del productor.
        "enable.idempotence": True,
        "acks": "all",
        "retries": 2147483647,
        "max.in.flight.requests.per.connection": 5,
        "delivery.timeout.ms": 120000,
        "retry.backoff.ms": 200,
        # Rendimiento: micro-lotes de hasta 20 ms comprimidos con lz4.
        "linger.ms": 20,
        "batch.size": 65536,
        "compression.type": "lz4",
    }


class _Parada:
    def __init__(self) -> None:
        self.solicitada = False

    def __call__(self, signum, _frame) -> None:
        print(f"\n[productor] senal {signum} recibida: deteniendo y vaciando buffer...", file=sys.stderr)
        self.solicitada = True


# --------------------------------------------------------------------------
# Fuentes
# --------------------------------------------------------------------------
def fuente_api(args, parada: _Parada, dedup: Deduplicador) -> Iterator[Dict[str, Any]]:
    import requests

    sesion = requests.Session()
    sesion.headers.update({"User-Agent": USER_AGENT, "Accept": "application/json"})
    hasta = args.hasta or dt.date.today().isoformat()
    desde = args.desde or (dt.date.today() - dt.timedelta(days=30)).isoformat()
    consulta = construir_consulta(desde, hasta)
    ultima = 0.0

    while not parada.solicitada:
        offset, total, paginas, fallos = 0, None, 0, 0
        while paginas < args.paginas and fallos < 10:
            if parada.solicitada or (total is not None and offset >= total):
                break
            espera = INTERVALO_MIN_API_S - (time.monotonic() - ultima)
            if espera > 0:
                time.sleep(espera)
            ultima = time.monotonic()
            try:
                r = sesion.get(API_URL, params={"query": consulta, "fmt": "json",
                                                "limit": 100, "offset": offset}, timeout=30)
            except requests.RequestException as exc:
                fallos += 1
                print(f"[productor] error de red: {exc}; reintento en 5 s", file=sys.stderr)
                time.sleep(5)
                continue
            if r.status_code == 503:  # limite de tasa excedido o servidor ocupado
                fallos += 1
                print("[productor] API ocupada (503); espera de 5 s", file=sys.stderr)
                time.sleep(5)
                continue
            r.raise_for_status()
            fallos = 0
            paginas += 1
            datos = r.json()
            total = datos.get("count", 0)
            offset += len(datos.get("releases") or [])
            print(f"[productor] API offset={offset}/{total}", file=sys.stderr)
            yield from eventos_desde_respuesta(datos, dedup)
        if not args.continuo:
            return
        print(f"[productor] ciclo completo; nuevo sondeo en {args.intervalo_sondeo} s", file=sys.stderr)
        fin = time.monotonic() + args.intervalo_sondeo
        while time.monotonic() < fin and not parada.solicitada:
            time.sleep(0.5)


def fuente_archivo(args) -> Iterator[str]:
    for linea in leer_lineas_jsonl(Path(args.archivo)):
        try:
            obj = json.loads(linea)
        except ValueError:
            yield linea  # linea malformada: se envia tal cual (prueba de DLQ)
            continue
        if isinstance(obj, dict):
            # Se re-estampa la hora de ingesta para medir la latencia extremo a extremo.
            obj["evento_ts"] = ahora_iso()
            obj["fuente"] = "archivo"
            yield json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
        else:
            yield linea


# --------------------------------------------------------------------------
# Ciclo principal
# --------------------------------------------------------------------------
def ejecutar(args) -> Dict[str, Any]:
    parada = _Parada()
    signal.signal(signal.SIGINT, parada)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, parada)

    dedup = Deduplicador()
    contadores = Contadores()
    inicio = time.monotonic()

    if args.sin_kafka:
        # Modo captura: guarda los eventos normalizados (genera fixtures reales).
        n = 0
        with open(args.salida, "w", encoding="utf-8") as out:
            for ev in fuente_api(args, parada, dedup):
                out.write(json.dumps(ev, ensure_ascii=False) + "\n")
                n += 1
                if args.max_eventos and n >= args.max_eventos:
                    break
        return {"capturados": n, "duplicados_descartados": dedup.descartados}

    from confluent_kafka import Producer

    productor = Producer(configuracion_productor(args.bootstrap))
    intervalo = 1.0 / args.eventos_por_segundo if args.eventos_por_segundo > 0 else 0.0

    if args.fuente == "api":
        mensajes = ((ev["mbid"].encode(), serializar_evento(ev)) for ev in fuente_api(args, parada, dedup))
    else:
        mensajes = ((clave_de_linea(l), l.encode("utf-8")) for l in fuente_archivo(args))

    try:
        for clave, valor in mensajes:
            if parada.solicitada:
                break
            while True:
                try:
                    productor.produce(args.topico, key=clave, value=valor,
                                      on_delivery=contadores.callback_entrega)
                    break
                except BufferError:  # cola local llena: esperar a que drene
                    productor.poll(0.5)
            contadores.producidos += 1
            productor.poll(0)
            if intervalo and args.fuente == "archivo":
                time.sleep(intervalo)
            if args.max_eventos and contadores.producidos >= args.max_eventos:
                break
    finally:
        pendientes = productor.flush(30)
        if pendientes:
            print(f"[productor] {pendientes} mensajes sin confirmar tras flush", file=sys.stderr)

    resumen = contadores.resumen()
    resumen.update({
        "topico": args.topico,
        "fuente": args.fuente,
        "duplicados_descartados": dedup.descartados,
        "duracion_s": round(time.monotonic() - inicio, 2),
    })
    return resumen


def parsear_argumentos(argv=None):
    p = argparse.ArgumentParser(description="Productor Kafka de lanzamientos MusicBrainz")
    p.add_argument("--fuente", choices=["api", "archivo"], required=True)
    p.add_argument("--bootstrap", default=os.getenv("KAFKA_BOOTSTRAP", "localhost:9092"))
    p.add_argument("--topico", default=TOPICO_DEFECTO)
    p.add_argument("--archivo", default="streaming/fixtures/lanzamientos_muestra.jsonl")
    p.add_argument("--eventos-por-segundo", type=float, default=20.0)
    p.add_argument("--desde", help="fecha inicial AAAA-MM-DD (api); defecto: hoy-30d")
    p.add_argument("--hasta", help="fecha final AAAA-MM-DD (api); defecto: hoy")
    p.add_argument("--paginas", type=int, default=3, help="paginas de 100 por ciclo (api)")
    p.add_argument("--continuo", action="store_true", help="sondear la API indefinidamente")
    p.add_argument("--intervalo-sondeo", type=int, default=60)
    p.add_argument("--max-eventos", type=int, default=0)
    p.add_argument("--sin-kafka", action="store_true", help="solo capturar a --salida (api)")
    p.add_argument("--salida", default="lanzamientos_capturados.jsonl")
    p.add_argument("--metricas", help="ruta donde escribir el resumen JSON")
    args = p.parse_args(argv)
    if args.sin_kafka and args.fuente != "api":
        p.error("--sin-kafka solo aplica a --fuente api")
    return args


def main(argv=None) -> int:
    args = parsear_argumentos(argv)
    resumen = ejecutar(args)
    texto = json.dumps(resumen, ensure_ascii=False, indent=2)
    print(texto)
    if args.metricas:
        Path(args.metricas).write_text(texto, encoding="utf-8")
    return 0 if not resumen.get("fallidos") else 1


if __name__ == "__main__":
    sys.exit(main())
