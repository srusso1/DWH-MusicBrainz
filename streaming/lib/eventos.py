"""Funciones puras del evento ``lanzamiento`` de la capa de streaming.

Este modulo no depende de Kafka ni de Spark: lo usan el productor (para
normalizar respuestas de la API WS2 de MusicBrainz) y el consumidor Spark
(como UDF de validacion), de modo que ambas partes aplican exactamente las
mismas reglas y estas quedan cubiertas por pruebas unitarias.

Compatible con Python 3.8+ (la imagen de Spark trae Python 3.10).
"""

from __future__ import annotations

import datetime as _dt
import json
import re
from collections import OrderedDict
from typing import Any, Dict, Iterable, List, Optional, Union

# Orden canonico de los campos del evento (contrato productor <-> consumidor).
CAMPOS_EVENTO = (
    "mbid",
    "titulo",
    "estado",
    "fecha",
    "pais",
    "formatos",
    "medio",
    "numero_pistas",
    "artista",
    "idioma",
    "empaque",
    "codigo_barras",
    "evento_ts",
    "fuente",
)

FORMATO_DESCONOCIDO = "Desconocido"

_RE_UUID = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
)
# MusicBrainz admite fechas parciales: AAAA, AAAA-MM o AAAA-MM-DD.
_RE_FECHA = re.compile(r"^(\d{4})(?:-(\d{2})(?:-(\d{2}))?)?$")


def _texto(valor: Any) -> Optional[str]:
    """Devuelve el texto recortado o ``None`` si esta vacio."""
    if valor is None:
        return None
    valor = str(valor).strip()
    return valor or None


def _artista(credito: Optional[List[Dict[str, Any]]]) -> Optional[str]:
    """Reconstruye el credito artistico tal como lo muestra MusicBrainz."""
    if not credito:
        return None
    partes = []
    for c in credito:
        partes.append(c.get("name") or (c.get("artist") or {}).get("name") or "")
        partes.append(c.get("joinphrase") or "")
    return _texto("".join(partes))


def normalizar_release_api(
    release: Dict[str, Any], evento_ts: str, fuente: str = "api"
) -> Dict[str, Any]:
    """Convierte un ``release`` de la API WS2 (JSON) en el evento del topico."""
    medios = release.get("media") or []
    formatos = [m["format"] for m in medios if _texto(m.get("format"))]

    pistas = release.get("track-count")
    if pistas is None and medios:
        conteos = [m.get("track-count") for m in medios]
        if all(isinstance(c, int) for c in conteos):
            pistas = sum(conteos)

    return {
        "mbid": _texto(release.get("id")),
        "titulo": _texto(release.get("title")),
        "estado": _texto(release.get("status")),
        "fecha": _texto(release.get("date")),
        "pais": _texto(release.get("country")),
        "formatos": formatos,
        "medio": " + ".join(formatos) if formatos else None,
        "numero_pistas": pistas,
        "artista": _artista(release.get("artist-credit")),
        "idioma": _texto((release.get("text-representation") or {}).get("language")),
        "empaque": _texto(release.get("packaging")),
        "codigo_barras": _texto(release.get("barcode")),
        "evento_ts": evento_ts,
        "fuente": fuente,
    }


def serializar_evento(evento: Dict[str, Any]) -> bytes:
    """Serializa el evento a JSON UTF-8 (valor del mensaje Kafka)."""
    return json.dumps(evento, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def _fecha_valida(fecha: str) -> bool:
    m = _RE_FECHA.match(fecha)
    if not m:
        return False
    anio, mes, dia = m.group(1), m.group(2), m.group(3)
    try:
        _dt.date(int(anio), int(mes or 1), int(dia or 1))
    except ValueError:
        return False
    return True


def motivo_invalidez(valor: Union[str, bytes, None]) -> Optional[str]:
    """Devuelve el motivo por el que un mensaje es invalido, o ``None`` si es valido.

    Se usa como UDF en Spark: los mensajes con motivo se envian al topico DLQ.
    """
    if isinstance(valor, (bytes, bytearray)):
        valor = valor.decode("utf-8", errors="replace")
    if valor is None or not valor.strip():
        return "mensaje_vacio"
    try:
        ev = json.loads(valor)
    except ValueError:
        return "json_malformado"
    if not isinstance(ev, dict):
        return "json_no_objeto"

    mbid = ev.get("mbid")
    if not mbid:
        return "mbid_ausente"
    if not isinstance(mbid, str) or not _RE_UUID.match(mbid.lower()):
        return "mbid_invalido"

    fecha = ev.get("fecha")
    if fecha is not None and (not isinstance(fecha, str) or not _fecha_valida(fecha)):
        return "fecha_invalida"

    pistas = ev.get("numero_pistas")
    if pistas is not None and (
        isinstance(pistas, bool) or not isinstance(pistas, int) or pistas < 0
    ):
        return "numero_pistas_invalido"

    if not ev.get("evento_ts"):
        return "evento_ts_ausente"
    return None


def formato_principal(formatos: Optional[Iterable[str]]) -> str:
    """Primer formato fisico/digital del lanzamiento; clave de agregacion."""
    for f in formatos or []:
        if f:
            return f
    return FORMATO_DESCONOCIDO


class Deduplicador:
    """Conjunto LRU acotado de MBID ya enviados (evita reenviar en cada sondeo)."""

    def __init__(self, iniciales: Iterable[str] = (), capacidad: int = 100_000):
        if capacidad <= 0:
            raise ValueError("capacidad debe ser positiva")
        self._capacidad = capacidad
        self._vistos: "OrderedDict[str, None]" = OrderedDict()
        self.descartados = 0
        for mbid in iniciales:
            self._agregar(mbid)

    def _agregar(self, mbid: str) -> None:
        self._vistos[mbid] = None
        self._vistos.move_to_end(mbid)
        while len(self._vistos) > self._capacidad:
            self._vistos.popitem(last=False)

    def es_nuevo(self, mbid: str) -> bool:
        """Registra el MBID y devuelve ``True`` si no se habia visto."""
        if mbid in self._vistos:
            self._vistos.move_to_end(mbid)
            self.descartados += 1
            return False
        self._agregar(mbid)
        return True

    def __len__(self) -> int:
        return len(self._vistos)
