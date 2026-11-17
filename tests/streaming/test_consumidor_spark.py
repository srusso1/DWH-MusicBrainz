"""Pruebas de las transformaciones del consumidor con Spark local (modo batch).

Se omiten si PySpark no esta instalado. Se alimentan con lineas reales del
fixture (incluidas las 5 de inyeccion de fallas) con la misma forma de columnas
que entrega la fuente Kafka (key, value, partition, offset, timestamp).
"""

import datetime as dt
import json
from pathlib import Path

import pytest

pytest.importorskip("pyspark")

from pyspark.sql import SparkSession  # noqa: E402
from pyspark.sql.types import (  # noqa: E402
    BinaryType, IntegerType, LongType, StructField, StructType, TimestampType,
)

from streaming.consumidor_spark import (  # noqa: E402
    agregar_ventanas, clasificar, deduplicar_lote, eventos_invalidos, eventos_validos,
)

FIXTURE = Path(__file__).resolve().parents[2] / "streaming" / "fixtures" / "lanzamientos_muestra.jsonl"
ESQUEMA_KAFKA = StructType([
    StructField("key", BinaryType()), StructField("value", BinaryType()),
    StructField("partition", IntegerType()), StructField("offset", LongType()),
    StructField("timestamp", TimestampType()),
])


@pytest.fixture(scope="module")
def spark():
    s = (SparkSession.builder.master("local[1]").appName("pruebas-streaming")
         .config("spark.sql.shuffle.partitions", "1")
         .config("spark.sql.session.timeZone", "UTC")
         .config("spark.ui.enabled", "false").getOrCreate())
    yield s
    s.stop()


@pytest.fixture(scope="module")
def lineas():
    return [l.strip() for l in FIXTURE.read_text(encoding="utf-8").splitlines()
            if l.strip() and not l.startswith("#")]


def _df_kafka(spark, valores):
    ts = dt.datetime(2026, 11, 17, 22, 0, 0)
    filas = [(None, v.encode("utf-8"), i % 3, i, ts) for i, v in enumerate(valores)]
    return spark.createDataFrame(filas, ESQUEMA_KAFKA)


def test_fixture_tiene_299_validos_y_5_fallas(lineas):
    assert len(lineas) == 304


def test_clasificacion_separa_validos_e_invalidos(spark, lineas):
    clas = clasificar(_df_kafka(spark, lineas)).cache()
    assert eventos_validos(clas).count() == 299
    dlq = [json.loads(r.value) for r in eventos_invalidos(clas).collect()]
    assert sorted(d["motivo"] for d in dlq) == sorted([
        "json_malformado", "mbid_ausente", "mbid_invalido",
        "fecha_invalida", "numero_pistas_invalido"])
    assert all(d["valor_original"] and d["offset_origen"] is not None for d in dlq)


def test_validos_tienen_columnas_derivadas(spark, lineas):
    v = eventos_validos(clasificar(_df_kafka(spark, lineas[:3])))
    r = v.first()
    assert r.evento_ts is not None
    assert r.formato_principal
    assert r.pais
    assert str(r.fecha_ingesta) == r.evento_ts.strftime("%Y-%m-%d")


def test_dedup_de_lote_conserva_una_fila_por_mbid(spark, lineas):
    v = eventos_validos(clasificar(_df_kafka(spark, lineas[:10] + lineas[:10])))
    assert v.count() == 20
    d = deduplicar_lote(v)
    assert d.count() == 10
    assert d.select("mbid").distinct().count() == 10


def test_ventanas_cuentan_todos_los_validos(spark, lineas):
    # En modo batch el watermark se ignora; la agregacion es la misma del stream.
    v = eventos_validos(clasificar(_df_kafka(spark, lineas)))
    agg = agregar_ventanas(v)
    total = agg.groupBy().sum("lanzamientos").first()[0]
    assert total == 299
    assert agg.where("pais IS NULL OR formato IS NULL").count() == 0
