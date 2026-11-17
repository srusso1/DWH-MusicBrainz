"""Consumidor Spark Structured Streaming: Kafka -> Bronze (parquet) / DLQ / PostgreSQL.

Consultas (cada una con su propio checkpoint):
  1. ``bronze``   eventos validos -> parquet particionado por fecha de ingesta
                  (sumidero de archivos: exactamente-una-vez por su bitacora _spark_metadata).
  2. ``dlq``      eventos invalidos + motivo -> topico ``musicbrainz.lanzamientos.dlq``.
  3. ``eventos``  foreachBatch -> UPSERT en ``streaming.lanzamientos_evento`` (dedup por MBID).
  4. ``ventanas`` watermark + ventana fija de 1 minuto por pais y formato ->
                  foreachBatch -> UPSERT en ``streaming.lanzamientos_ventana``.

Idempotencia hacia PostgreSQL: cada foreachBatch escribe primero en una tabla de
staging y luego, en UNA transaccion, aplica el UPSERT y registra
(consulta, batch_id) en ``streaming.control_lotes``. Si Spark se cae despues de
confirmar en PostgreSQL pero antes de confirmar el checkpoint, al reiniciar
re-ejecuta el mismo batch_id con los mismos offsets: el lote se detecta en
``control_lotes`` y se omite. Resultado: exactamente-una-vez efectivo.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pyspark.sql import DataFrame, SparkSession  # noqa: E402
from pyspark.sql import functions as F  # noqa: E402
from pyspark.sql.types import (  # noqa: E402
    ArrayType,
    IntegerType,
    StringType,
    StructField,
    StructType,
)

from streaming.lib.eventos import FORMATO_DESCONOCIDO, motivo_invalidez  # noqa: E402

KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP", "kafka:19092")
TOPICO = os.getenv("TOPICO", "musicbrainz.lanzamientos")
TOPICO_DLQ = os.getenv("TOPICO_DLQ", "musicbrainz.lanzamientos.dlq")
MAX_OFFSETS = os.getenv("MAX_OFFSETS_POR_LOTE", "100")
INTERVALO = os.getenv("INTERVALO_LOTE", "10 seconds")
RUTA_LAGO = os.getenv("RUTA_LAGO", "/opt/lake")
RUTA_CHECKPOINTS = os.getenv("RUTA_CHECKPOINTS", "/opt/checkpoints")
PG_URL = os.getenv("PG_URL", "jdbc:postgresql://postgres:5432/dw_musicbrainz")
PG_USER = os.getenv("PG_USER", "postgres")
PG_PASSWORD = os.getenv("PG_PASSWORD", "")

# Esquema explicito del evento (contrato con streaming/lib/eventos.py).
ESQUEMA_EVENTO = StructType([
    StructField("mbid", StringType()),
    StructField("titulo", StringType()),
    StructField("estado", StringType()),
    StructField("fecha", StringType()),
    StructField("pais", StringType()),
    StructField("formatos", ArrayType(StringType())),
    StructField("medio", StringType()),
    StructField("numero_pistas", IntegerType()),
    StructField("artista", StringType()),
    StructField("idioma", StringType()),
    StructField("empaque", StringType()),
    StructField("codigo_barras", StringType()),
    StructField("evento_ts", StringType()),
    StructField("fuente", StringType()),
])


# --------------------------------------------------------------------------
# Lectura y clasificacion
# --------------------------------------------------------------------------
def leer_kafka(spark: SparkSession) -> DataFrame:
    return (
        spark.readStream.format("kafka")
        .option("kafka.bootstrap.servers", KAFKA_BOOTSTRAP)
        .option("subscribe", TOPICO)
        .option("startingOffsets", "earliest")   # solo aplica sin checkpoint previo
        .option("failOnDataLoss", "false")       # tolera offsets expirados por retencion
        .option("maxOffsetsPerTrigger", MAX_OFFSETS)  # control de contrapresion
        .option("groupIdPrefix", "dwmb-spark")
        .load()
    )


def clasificar(crudo: DataFrame) -> DataFrame:
    """Agrega ``motivo`` (null = valido) y las columnas del evento parseado."""
    udf_motivo = F.udf(motivo_invalidez, StringType())
    valor = F.col("value").cast("string")
    return (
        crudo.select(
            F.col("key").cast("string").alias("clave"),
            valor.alias("valor"),
            F.col("partition").alias("kafka_particion"),
            F.col("offset").alias("kafka_offset"),
            F.col("timestamp").alias("kafka_ts"),
        )
        .withColumn("motivo", udf_motivo(F.col("valor")))
        .withColumn("ev", F.from_json(F.col("valor"), ESQUEMA_EVENTO))
        # from_json devuelve null si el tipo no encaja (p. ej. pistas no enteras).
        .withColumn("motivo", F.when(F.col("motivo").isNull() & F.col("ev").isNull(),
                                     F.lit("esquema_incompatible")).otherwise(F.col("motivo")))
    )


def eventos_validos(clasificados: DataFrame) -> DataFrame:
    return (
        clasificados.where(F.col("motivo").isNull())
        .select("ev.*", "kafka_particion", "kafka_offset", "kafka_ts")
        .withColumn("evento_ts", F.to_timestamp("evento_ts"))
        .withColumn("anio", F.substring("fecha", 1, 4).cast("int"))
        .withColumn("pais", F.coalesce("pais", F.lit("Desconocido")))
        .withColumn("formato_principal",
                    F.coalesce(F.element_at("formatos", 1), F.lit(FORMATO_DESCONOCIDO)))
        .withColumn("fecha_ingesta", F.to_date("evento_ts"))
    )


def eventos_invalidos(clasificados: DataFrame) -> DataFrame:
    """Mensaje DLQ: valor original + motivo + coordenadas Kafka de origen."""
    return clasificados.where(F.col("motivo").isNotNull()).select(
        F.col("clave").alias("key"),
        F.to_json(F.struct(
            F.col("motivo"),
            F.col("valor").alias("valor_original"),
            F.lit(TOPICO).alias("topico_origen"),
            F.col("kafka_particion").alias("particion_origen"),
            F.col("kafka_offset").alias("offset_origen"),
            F.date_format(F.current_timestamp(), "yyyy-MM-dd'T'HH:mm:ss.SSSXXX").alias("detectado_ts"),
        )).alias("value"),
    )


# --------------------------------------------------------------------------
# PostgreSQL (JDBC + transaccion via JVM)
# --------------------------------------------------------------------------
def _conexion_jdbc(spark: SparkSession):
    jvm = spark.sparkContext._gateway.jvm
    props = jvm.java.util.Properties()
    props.setProperty("user", PG_USER)
    props.setProperty("password", PG_PASSWORD)
    conn = jvm.org.postgresql.Driver().connect(PG_URL, props)
    conn.setAutoCommit(False)
    return conn


def _escribir_staging(df: DataFrame, tabla: str) -> None:
    (df.write.format("jdbc")
       .option("url", PG_URL).option("dbtable", tabla)
       .option("user", PG_USER).option("password", PG_PASSWORD)
       .option("driver", "org.postgresql.Driver")
       .option("truncate", "true")  # conserva el DDL de sql/streaming
       .mode("overwrite").save())


def _aplicar_lote(spark: SparkSession, consulta: str, batch_id: int, sql_upsert: str, filas: int) -> None:
    """Aplica el UPSERT y registra el lote en una sola transaccion."""
    conn = _conexion_jdbc(spark)
    try:
        st = conn.prepareStatement(
            "SELECT 1 FROM streaming.control_lotes WHERE consulta = ? AND batch_id = ?")
        st.setString(1, consulta)
        st.setLong(2, batch_id)
        if st.executeQuery().next():
            print(f"[{consulta}] lote {batch_id} ya aplicado: se omite (re-ejecucion tras fallo)")
            conn.rollback()
            return
        conn.createStatement().executeUpdate(sql_upsert.replace(":batch_id", str(int(batch_id))))
        ins = conn.prepareStatement(
            "INSERT INTO streaming.control_lotes (consulta, batch_id, filas) VALUES (?, ?, ?)")
        ins.setString(1, consulta)
        ins.setLong(2, batch_id)
        ins.setInt(3, filas)
        ins.executeUpdate()
        conn.commit()
        print(f"[{consulta}] lote {batch_id} aplicado: {filas} filas")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


UPSERT_EVENTOS = """
INSERT INTO streaming.lanzamientos_evento AS t
    (mbid, titulo, estado, fecha, anio, pais, formatos, medio, formato_principal,
     numero_pistas, artista, idioma, empaque, codigo_barras, fuente, evento_ts,
     kafka_ts, kafka_particion, kafka_offset, batch_id, procesado_ts)
SELECT mbid::uuid, titulo, estado, fecha, anio, pais,
       string_to_array(NULLIF(formatos, ''), '|'), medio, formato_principal,
       numero_pistas, artista, idioma, empaque, codigo_barras, fuente, evento_ts,
       kafka_ts, kafka_particion, kafka_offset, :batch_id, now()
FROM streaming.stg_lanzamientos_evento
ON CONFLICT (mbid) DO UPDATE SET
    titulo = EXCLUDED.titulo, estado = EXCLUDED.estado, fecha = EXCLUDED.fecha,
    anio = EXCLUDED.anio, pais = EXCLUDED.pais, formatos = EXCLUDED.formatos,
    medio = EXCLUDED.medio, formato_principal = EXCLUDED.formato_principal,
    numero_pistas = EXCLUDED.numero_pistas, artista = EXCLUDED.artista,
    idioma = EXCLUDED.idioma, empaque = EXCLUDED.empaque,
    codigo_barras = EXCLUDED.codigo_barras, fuente = EXCLUDED.fuente,
    evento_ts = EXCLUDED.evento_ts, kafka_ts = EXCLUDED.kafka_ts,
    kafka_particion = EXCLUDED.kafka_particion, kafka_offset = EXCLUDED.kafka_offset,
    batch_id = EXCLUDED.batch_id, procesado_ts = EXCLUDED.procesado_ts,
    versiones = t.versiones + 1
"""

UPSERT_VENTANAS = """
INSERT INTO streaming.lanzamientos_ventana AS t
    (ventana_inicio, ventana_fin, pais, formato, lanzamientos, pistas, batch_id, actualizado_ts)
SELECT ventana_inicio, ventana_fin, pais, formato, lanzamientos, pistas, :batch_id, now()
FROM streaming.stg_lanzamientos_ventana
ON CONFLICT (ventana_inicio, pais, formato) DO UPDATE SET
    ventana_fin = EXCLUDED.ventana_fin,
    lanzamientos = EXCLUDED.lanzamientos,   -- modo update: Spark emite el total vigente
    pistas = EXCLUDED.pistas,
    batch_id = EXCLUDED.batch_id,
    actualizado_ts = EXCLUDED.actualizado_ts
"""


def deduplicar_lote(lote: DataFrame) -> DataFrame:
    """Spark SQL: una fila por MBID dentro del lote (la mas reciente).

    Requisito de ``ON CONFLICT DO UPDATE``, que no admite tocar la misma fila
    dos veces en una sentencia.
    """
    lote.createOrReplaceTempView("lote_eventos")
    return lote.sparkSession.sql("""
        SELECT mbid, titulo, estado, fecha, anio, pais,
               concat_ws('|', formatos) AS formatos, medio, formato_principal,
               numero_pistas, artista, idioma, empaque, codigo_barras, fuente,
               evento_ts, kafka_ts, kafka_particion, kafka_offset
        FROM (
            SELECT *, row_number() OVER (PARTITION BY mbid
                                         ORDER BY evento_ts DESC, kafka_offset DESC) AS rn
            FROM lote_eventos
        ) WHERE rn = 1
    """)


def sumidero_eventos(lote: DataFrame, batch_id: int) -> None:
    spark = lote.sparkSession
    dedup = deduplicar_lote(lote).persist()
    try:
        filas = dedup.count()
        if filas == 0:
            return
        _escribir_staging(dedup, "streaming.stg_lanzamientos_evento")
        _aplicar_lote(spark, "eventos", batch_id, UPSERT_EVENTOS, filas)
    finally:
        dedup.unpersist()


def sumidero_ventanas(lote: DataFrame, batch_id: int) -> None:
    spark = lote.sparkSession
    lote.createOrReplaceTempView("lote_ventanas")
    agg = spark.sql("""
        SELECT ventana.start AS ventana_inicio, ventana.end AS ventana_fin,
               pais, formato, lanzamientos, pistas
        FROM lote_ventanas
    """).persist()
    try:
        filas = agg.count()
        if filas == 0:
            return
        _escribir_staging(agg, "streaming.stg_lanzamientos_ventana")
        _aplicar_lote(spark, "ventanas", batch_id, UPSERT_VENTANAS, filas)
    finally:
        agg.unpersist()


def agregar_ventanas(validos: DataFrame) -> DataFrame:
    """Ventana fija de 1 minuto (tiempo de evento) por pais y formato.

    El watermark de 2 minutos acota el estado: eventos con mas de 2 minutos de
    retraso respecto al maximo visto se descartan y el estado de ventanas
    cerradas se libera.
    """
    return (
        validos.withWatermark("evento_ts", "2 minutes")
        .groupBy(F.window("evento_ts", "1 minute").alias("ventana"),
                 F.col("pais"), F.col("formato_principal").alias("formato"))
        .agg(F.count(F.lit(1)).alias("lanzamientos"),
             F.coalesce(F.sum("numero_pistas"), F.lit(0)).cast("long").alias("pistas"))
    )


# --------------------------------------------------------------------------
# Arranque
# --------------------------------------------------------------------------
def main() -> None:
    spark = (
        SparkSession.builder.appName("dwmb-streaming-lanzamientos")
        .config("spark.sql.shuffle.partitions", "3")
        .config("spark.sql.session.timeZone", "UTC")
        .config("spark.sql.streaming.stateStore.providerClass",
                "org.apache.spark.sql.execution.streaming.state.RocksDBStateStoreProvider")
        .getOrCreate()
    )
    spark.sparkContext.setLogLevel("WARN")
    cp = lambda nombre: f"{RUTA_CHECKPOINTS}/{nombre}"  # noqa: E731

    clasificados = clasificar(leer_kafka(spark))
    validos = eventos_validos(clasificados)

    (validos.writeStream.queryName("bronze")
        .format("parquet").partitionBy("fecha_ingesta")
        .option("path", f"{RUTA_LAGO}/bronze/lanzamientos")
        .option("checkpointLocation", cp("bronze"))
        .outputMode("append").trigger(processingTime=INTERVALO).start())

    (eventos_invalidos(clasificados).writeStream.queryName("dlq")
        .format("kafka")
        .option("kafka.bootstrap.servers", KAFKA_BOOTSTRAP)
        .option("topic", TOPICO_DLQ)
        .option("kafka.enable.idempotence", "true")
        .option("kafka.acks", "all")
        .option("checkpointLocation", cp("dlq"))
        .outputMode("append").trigger(processingTime=INTERVALO).start())

    (validos.writeStream.queryName("eventos")
        .foreachBatch(sumidero_eventos)
        .option("checkpointLocation", cp("eventos"))
        .outputMode("append").trigger(processingTime=INTERVALO).start())

    (agregar_ventanas(validos).writeStream.queryName("ventanas")
        .foreachBatch(sumidero_ventanas)
        .option("checkpointLocation", cp("ventanas"))
        .outputMode("update").trigger(processingTime=INTERVALO).start())

    print(f"[consumidor] 4 consultas activas; leyendo {TOPICO} desde {KAFKA_BOOTSTRAP}")
    spark.streams.awaitAnyTermination()


if __name__ == "__main__":
    main()
