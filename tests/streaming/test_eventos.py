"""Pruebas de la capa de streaming: normalizacion, validacion y deduplicacion.

Se escribieron antes que la implementacion (TDD). Los fragmentos JSON imitan
la forma exacta de la respuesta de la API WS2 de MusicBrainz (``fmt=json``).
"""

import json

import pytest

from streaming.lib.eventos import (
    CAMPOS_EVENTO,
    Deduplicador,
    formato_principal,
    motivo_invalidez,
    normalizar_release_api,
    serializar_evento,
)

TS = "2026-11-17T22:00:00.000Z"

RELEASE_API = {
    "id": "f266bb87-57dd-470f-bb79-97e7eb47392d",
    "title": "Together Again",
    "status": "Official",
    "packaging": "Cardboard/Paper Sleeve",
    "text-representation": {"language": "eng", "script": "Latn"},
    "artist-credit": [
        {"joinphrase": " & ", "name": "John McCutcheon", "artist": {"id": "x"}},
        {"name": "Tom Paxton", "artist": {"id": "y"}},
    ],
    "date": "2026",
    "country": "US",
    "barcode": "195269385354",
    "track-count": 14,
    "media": [{"format": "CD", "disc-count": 0, "track-count": 14}],
}


# --------------------------------------------------------------------------
# Normalizacion API -> evento
# --------------------------------------------------------------------------
class TestNormalizarReleaseApi:
    def test_mapea_todos_los_campos(self):
        ev = normalizar_release_api(RELEASE_API, evento_ts=TS, fuente="api")
        assert ev["mbid"] == "f266bb87-57dd-470f-bb79-97e7eb47392d"
        assert ev["titulo"] == "Together Again"
        assert ev["estado"] == "Official"
        assert ev["fecha"] == "2026"
        assert ev["pais"] == "US"
        assert ev["formatos"] == ["CD"]
        assert ev["medio"] == "CD"
        assert ev["numero_pistas"] == 14
        assert ev["artista"] == "John McCutcheon & Tom Paxton"
        assert ev["idioma"] == "eng"
        assert ev["empaque"] == "Cardboard/Paper Sleeve"
        assert ev["codigo_barras"] == "195269385354"
        assert ev["evento_ts"] == TS
        assert ev["fuente"] == "api"

    def test_contiene_exactamente_el_esquema(self):
        ev = normalizar_release_api(RELEASE_API, evento_ts=TS, fuente="api")
        assert set(ev) == set(CAMPOS_EVENTO)

    def test_campos_ausentes_quedan_en_none(self):
        minimo = {"id": "46f501b6-61d8-44da-9bfc-0b0a906fc1b6", "title": "RAVEPOP"}
        ev = normalizar_release_api(minimo, evento_ts=TS, fuente="api")
        assert ev["pais"] is None
        assert ev["fecha"] is None
        assert ev["formatos"] == []
        assert ev["medio"] is None
        assert ev["numero_pistas"] is None
        assert ev["artista"] is None
        assert ev["idioma"] is None
        assert ev["codigo_barras"] is None

    def test_varios_medios_suman_pistas_si_no_hay_track_count(self):
        rel = {
            "id": "46f501b6-61d8-44da-9bfc-0b0a906fc1b6",
            "title": "Doble",
            "media": [
                {"format": "CD", "track-count": 10},
                {"format": "DVD-Video", "track-count": 3},
            ],
        }
        ev = normalizar_release_api(rel, evento_ts=TS, fuente="api")
        assert ev["numero_pistas"] == 13
        assert ev["formatos"] == ["CD", "DVD-Video"]
        assert ev["medio"] == "CD + DVD-Video"

    def test_medio_sin_formato_se_omite(self):
        rel = {"id": "46f501b6-61d8-44da-9bfc-0b0a906fc1b6", "title": "t",
               "media": [{"track-count": 4}]}
        ev = normalizar_release_api(rel, evento_ts=TS, fuente="api")
        assert ev["formatos"] == []
        assert ev["medio"] is None
        assert ev["numero_pistas"] == 4

    def test_codigo_barras_vacio_es_none(self):
        rel = dict(RELEASE_API, barcode="")
        assert normalizar_release_api(rel, TS, "api")["codigo_barras"] is None

    def test_serializa_a_json_utf8_y_vuelve_igual(self):
        ev = normalizar_release_api(dict(RELEASE_API, title="Canción ñ"), TS, "api")
        crudo = serializar_evento(ev)
        assert isinstance(crudo, bytes)
        assert json.loads(crudo.decode("utf-8")) == ev


# --------------------------------------------------------------------------
# Reglas de validacion (las mismas que aplica el consumidor Spark)
# --------------------------------------------------------------------------
def _valido(**cambios):
    ev = normalizar_release_api(RELEASE_API, evento_ts=TS, fuente="api")
    ev.update(cambios)
    return json.dumps(ev)


class TestMotivoInvalidez:
    def test_evento_valido_no_tiene_motivo(self):
        assert motivo_invalidez(_valido()) is None

    @pytest.mark.parametrize("fecha", ["2026", "2026-11", "2026-11-17", None])
    def test_fechas_parciales_validas(self, fecha):
        assert motivo_invalidez(_valido(fecha=fecha)) is None

    def test_valor_nulo(self):
        assert motivo_invalidez(None) == "mensaje_vacio"

    def test_valor_vacio(self):
        assert motivo_invalidez("   ") == "mensaje_vacio"

    def test_json_malformado(self):
        assert motivo_invalidez('{"mbid": "abc", ') == "json_malformado"

    def test_json_que_no_es_objeto(self):
        assert motivo_invalidez("[1, 2, 3]") == "json_no_objeto"

    def test_sin_mbid(self):
        assert motivo_invalidez(_valido(mbid=None)) == "mbid_ausente"

    def test_mbid_no_uuid(self):
        assert motivo_invalidez(_valido(mbid="no-es-un-uuid")) == "mbid_invalido"

    @pytest.mark.parametrize("fecha", ["2026-13-01", "2026-02-30", "17/11/2026", "20x6"])
    def test_fecha_invalida(self, fecha):
        assert motivo_invalidez(_valido(fecha=fecha)) == "fecha_invalida"

    @pytest.mark.parametrize("pistas", [-1, "diez", 1.5])
    def test_numero_pistas_invalido(self, pistas):
        assert motivo_invalidez(_valido(numero_pistas=pistas)) == "numero_pistas_invalido"

    def test_sin_evento_ts(self):
        assert motivo_invalidez(_valido(evento_ts=None)) == "evento_ts_ausente"

    def test_acepta_bytes(self):
        assert motivo_invalidez(_valido().encode("utf-8")) is None


# --------------------------------------------------------------------------
# Clave de agregacion
# --------------------------------------------------------------------------
class TestFormatoPrincipal:
    def test_primer_formato(self):
        assert formato_principal(["Vinyl", "CD"]) == "Vinyl"

    def test_sin_formato(self):
        assert formato_principal([]) == "Desconocido"
        assert formato_principal(None) == "Desconocido"


# --------------------------------------------------------------------------
# Deduplicacion del productor
# --------------------------------------------------------------------------
class TestDeduplicador:
    def test_primera_vez_no_es_duplicado(self):
        d = Deduplicador()
        assert d.es_nuevo("a") is True

    def test_segunda_vez_es_duplicado(self):
        d = Deduplicador()
        d.es_nuevo("a")
        assert d.es_nuevo("a") is False
        assert d.descartados == 1

    def test_capacidad_acotada_expulsa_el_mas_antiguo(self):
        d = Deduplicador(capacidad=2)
        d.es_nuevo("a")
        d.es_nuevo("b")
        d.es_nuevo("c")  # expulsa "a"
        assert len(d) == 2
        assert d.es_nuevo("a") is True

    def test_capacidad_invalida(self):
        with pytest.raises(ValueError):
            Deduplicador(capacidad=0)

    def test_precarga_desde_iterable(self):
        d = Deduplicador(["x", "y"])
        assert d.es_nuevo("x") is False
        assert d.es_nuevo("z") is True
