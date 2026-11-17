"""Pruebas de las funciones puras del productor (sin conexion a Kafka ni a la API)."""

import json

from streaming.productor import (
    USER_AGENT,
    Contadores,
    clave_de_linea,
    construir_consulta,
    eventos_desde_respuesta,
    leer_lineas_jsonl,
)
from streaming.lib.eventos import Deduplicador

MBID = "f266bb87-57dd-470f-bb79-97e7eb47392d"


def test_user_agent_es_generico():
    assert USER_AGENT.startswith("DWMusicBrainz-Streaming/1.0")
    assert "@" not in USER_AGENT


def test_consulta_rango_de_fechas():
    assert construir_consulta("2026-11-01", "2026-11-17") == "date:[2026-11-01 TO 2026-11-17]"


def test_clave_de_linea_valida():
    assert clave_de_linea(json.dumps({"mbid": MBID})) == MBID.encode()


def test_clave_de_linea_malformada_es_none():
    assert clave_de_linea('{"mbid": ') is None
    assert clave_de_linea('"texto"') is None
    assert clave_de_linea(json.dumps({"titulo": "sin mbid"})) is None


def test_leer_lineas_jsonl_omite_comentarios_y_vacias(tmp_path):
    f = tmp_path / "m.jsonl"
    f.write_text('# comentario\n\n{"mbid": "a"}\n{roto\n', encoding="utf-8")
    assert list(leer_lineas_jsonl(f)) == ['{"mbid": "a"}', "{roto"]


def test_eventos_desde_respuesta_deduplica():
    respuesta = {"releases": [
        {"id": MBID, "title": "A"},
        {"id": MBID, "title": "A repetido"},
        {"id": "46f501b6-61d8-44da-9bfc-0b0a906fc1b6", "title": "B"},
    ]}
    dedup = Deduplicador()
    eventos = list(eventos_desde_respuesta(respuesta, dedup, evento_ts="2026-11-17T00:00:00Z"))
    assert [e["titulo"] for e in eventos] == ["A", "B"]
    assert all(e["fuente"] == "api" for e in eventos)
    assert dedup.descartados == 1


def test_contadores_callback():
    c = Contadores()

    class Msg:
        def partition(self):
            return 2

    c.callback_entrega(None, Msg())
    c.callback_entrega("error simulado", Msg())
    assert c.entregados == 1
    assert c.fallidos == 1
    assert c.por_particion == {2: 1}
