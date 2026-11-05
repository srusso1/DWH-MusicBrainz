# Databricks notebook source
# ============================================================================
# PRUEBA DE CAPACIDAD: DWMusicBrainz en Databricks Free Edition
# Mide si el cómputo serverless soporta la carga completa del volcado y el
# join del hecho a nivel de pista (58,8 M de filas).
#
# Cada etapa registra su resultado en workspace.meta.spike_metrics y se omite
# si su tabla ya existe, para poder reanudar si la cuota diaria corta la corrida.
# Script descartable: no es el pipeline definitivo.
# ============================================================================

import json
import time

from pyspark.sql import functions as F
from pyspark.sql.types import StringType, StructField, StructType

DUMP_VERSION = "20261104-002222"
RAW_DIR = f"/Volumes/workspace/landing/mbdump/{DUMP_VERSION}/mbdump"
METRICS_TABLE = "workspace.meta.spike_metrics"
FACT_TABLE = "workspace.gold.spike_fact_pista"
EXPECTED_TRACKS = 58_809_976

# Orden real de columnas del volcado (Schema Sequence 31). Bronze guarda texto.
TABLES = {
    "release_unknown_country": ["release", "date_year", "date_month", "date_day"],
    "release_country": ["release", "country", "date_year", "date_month", "date_day"],
    "artist_credit_name": ["artist_credit", "position", "artist", "name", "join_phrase"],
    "isrc": ["id", "recording", "isrc", "source", "created"],
    "artist": [
        "id", "gid", "name", "sort_name", "begin_date_year", "begin_date_month",
        "begin_date_day", "end_date_year", "end_date_month", "end_date_day", "type",
        "area", "gender", "comment", "edits_pending", "last_updated", "ended",
        "begin_area", "end_area",
    ],
    "medium": [
        "id", "release", "position", "format", "name", "edits_pending",
        "last_updated", "track_count", "gid",
    ],
    "release": [
        "id", "gid", "name", "artist_credit", "release_group", "status", "packaging",
        "language", "script", "barcode", "comment", "edits_pending", "quality",
        "last_updated",
    ],
    "recording": [
        "id", "gid", "name", "artist_credit", "length", "comment", "edits_pending",
        "last_updated", "video",
    ],
    "track": [
        "id", "gid", "recording", "medium", "position", "number", "name",
        "artist_credit", "length", "edits_pending", "last_updated", "is_data_track",
    ],
}

# COMMAND ----------


def log_metric(stage, seconds, rows=None, status="OK", detail=None):
    row = [(stage, float(seconds), rows, status, detail)]
    schema = "stage STRING, seconds DOUBLE, rows BIGINT, status STRING, detail STRING"
    (
        spark.createDataFrame(row, schema)
        .withColumn("logged_at", F.current_timestamp())
        .write.mode("append")
        .saveAsTable(METRICS_TABLE)
    )
    print(f"{stage}: {seconds:.1f}s rows={rows} status={status} {detail or ''}")


def load_bronze(table):
    target = f"workspace.bronze.{table}"
    if spark.catalog.tableExists(target):
        return

    schema = StructType([StructField(c, StringType()) for c in TABLES[table]])
    started = time.time()
    (
        spark.read.schema(schema)
        .option("sep", "\t")
        .option("nullValue", "\\N")
        .option("quote", "")
        .option("mode", "FAILFAST")
        .csv(f"{RAW_DIR}/{table}")
        .write.mode("overwrite")
        .saveAsTable(target)
    )
    rows = spark.table(target).count()
    log_metric(f"bronze.{table}", time.time() - started, rows)


def int_columns(df, columns):
    return df.select(*[F.col(c).cast("int").alias(c) for c in columns])


# COMMAND ----------

for table_name in TABLES:
    load_bronze(table_name)

# COMMAND ----------


def build_fact():
    t = (
        int_columns(
            spark.table("workspace.bronze.track"),
            ["id", "recording", "medium", "position", "artist_credit", "length"],
        )
        .withColumnRenamed("id", "track_id")
        .withColumnRenamed("recording", "recording_id")
        .withColumnRenamed("medium", "medium_id")
        .withColumnRenamed("position", "track_position")
        .withColumnRenamed("artist_credit", "track_credit")
        .withColumnRenamed("length", "track_length")
    )
    m = (
        int_columns(spark.table("workspace.bronze.medium"), ["id", "release", "position", "format"])
        .withColumnRenamed("id", "medium_id")
        .withColumnRenamed("release", "release_id")
        .withColumnRenamed("position", "medium_position")
        .withColumnRenamed("format", "format_id")
    )
    rel = (
        int_columns(
            spark.table("workspace.bronze.release"),
            ["id", "artist_credit", "status", "packaging", "language", "quality"],
        )
        .withColumnRenamed("id", "release_id")
        .withColumnRenamed("artist_credit", "release_credit")
    )
    rec = spark.table("workspace.bronze.recording").select(
        F.col("id").cast("int").alias("recording_id"),
        F.col("length").cast("int").alias("recording_length"),
        (F.col("video") == "t").alias("is_video"),
    )
    acn = int_columns(
        spark.table("workspace.bronze.artist_credit_name").where(F.col("position") == "0"),
        ["artist_credit", "artist"],
    )
    artist_area = int_columns(spark.table("workspace.bronze.artist"), ["id", "area"]).select(
        F.col("id").alias("artist_id"), F.col("area").alias("artist_area")
    )
    isrc = spark.table("workspace.bronze.isrc").select(
        F.col("recording").cast("int").alias("recording_id")
    ).distinct()

    # Evento primario por lanzamiento: prioriza país conocido y la fecha más antigua.
    known = int_columns(
        spark.table("workspace.bronze.release_country"),
        ["release", "country", "date_year", "date_month", "date_day"],
    ).withColumn("priority", F.lit(1))
    unknown = (
        int_columns(
            spark.table("workspace.bronze.release_unknown_country"),
            ["release", "date_year", "date_month", "date_day"],
        )
        .withColumn("country", F.lit(None).cast("int"))
        .withColumn("priority", F.lit(2))
    )
    events = (
        known.unionByName(unknown)
        .groupBy("release")
        .agg(
            F.min(
                F.struct(
                    "priority",
                    F.coalesce("date_year", F.lit(9999)).alias("sort_year"),
                    F.coalesce("date_month", F.lit(12)).alias("sort_month"),
                    F.coalesce("date_day", F.lit(31)).alias("sort_day"),
                    "country",
                    "date_year",
                    "date_month",
                    "date_day",
                )
            ).alias("event")
        )
        .select(
            F.col("release").alias("release_id"),
            F.col("event.country").alias("event_country"),
            F.col("event.date_year").alias("date_year"),
            F.col("event.date_month").alias("date_month"),
            F.col("event.date_day").alias("date_day"),
        )
    )

    base = t.join(m, "medium_id").join(rel, "release_id")

    # Agregaciones en lugar de ROW_NUMBER: evitan ordenar cada partición completa.
    first_release = base.groupBy("release_id").agg(
        F.min(F.struct("medium_position", "medium_id", "track_position", "track_id")).alias("k")
    ).select(F.col("k.track_id").alias("track_id"), F.lit(1).alias("first_in_release"))
    first_medium = base.groupBy("medium_id").agg(
        F.min(F.struct("track_position", "track_id")).alias("k")
    ).select(F.col("k.track_id").alias("track_id"), F.lit(1).alias("first_in_medium"))
    first_recording = base.groupBy("recording_id").agg(
        F.min(F.struct("release_id", "medium_position", "track_position", "track_id")).alias("k")
    ).select(F.col("k.track_id").alias("track_id"), F.lit(1).alias("first_of_recording"))

    track_credit = acn.select(
        F.col("artist_credit").alias("track_credit"), F.col("artist").alias("track_artist")
    )
    release_credit = acn.select(
        F.col("artist_credit").alias("release_credit"), F.col("artist").alias("release_artist")
    )

    fact = (
        base.join(rec, "recording_id", "left")
        .join(events, "release_id", "left")
        .join(track_credit, "track_credit", "left")
        .join(release_credit, "release_credit", "left")
        .withColumn("artist_id", F.coalesce("track_artist", "release_artist"))
        .join(artist_area, "artist_id", "left")
        .join(isrc.withColumn("has_isrc", F.lit(1)), "recording_id", "left")
        .join(first_release, "track_id", "left")
        .join(first_medium, "track_id", "left")
        .join(first_recording, "track_id", "left")
    )

    return fact.select(
        "track_id",
        "recording_id",
        "medium_id",
        "release_id",
        F.expr(
            """
            CASE WHEN date_year BETWEEN 1900 AND 2030 THEN
                date_year * 10000
                + COALESCE(CASE WHEN date_month BETWEEN 1 AND 12 THEN date_month END, 1) * 100
                + CASE
                    WHEN date_month BETWEEN 1 AND 12
                     AND date_day BETWEEN 1 AND day(last_day(make_date(date_year, date_month, 1)))
                    THEN date_day ELSE 1
                  END
            ELSE 0 END
            """
        ).alias("fecha_key"),
        F.coalesce("artist_id", F.lit(0)).alias("artist_id"),
        F.coalesce("event_country", "artist_area", F.lit(0)).alias("area_id"),
        F.coalesce("format_id", F.lit(0)).alias("format_id"),
        F.coalesce("language", F.lit(0)).alias("language_id"),
        F.coalesce("status", F.lit(0)).alias("status_id"),
        F.coalesce("packaging", F.lit(0)).alias("packaging_id"),
        F.coalesce("quality", F.lit(0)).alias("quality_id"),
        F.greatest(
            F.coalesce(
                F.expr("NULLIF(track_length, 0)"),
                F.expr("NULLIF(recording_length, 0)"),
                F.lit(0),
            ),
            F.lit(0),
        ).cast("bigint").alias("duration_ms"),
        F.coalesce("has_isrc", F.lit(0)).alias("has_isrc"),
        F.coalesce("is_video", F.lit(False)).cast("int").alias("is_video"),
        F.coalesce("first_in_release", F.lit(0)).alias("first_in_release"),
        F.coalesce("first_in_medium", F.lit(0)).alias("first_in_medium"),
        F.coalesce("first_of_recording", F.lit(0)).alias("first_of_recording"),
    )


if not spark.catalog.tableExists(FACT_TABLE):
    started = time.time()
    build_fact().write.mode("overwrite").saveAsTable(FACT_TABLE)
    rows = spark.table(FACT_TABLE).count()
    log_metric("gold.spike_fact_pista", time.time() - started, rows)

# COMMAND ----------

started = time.time()
checks = (
    spark.table(FACT_TABLE)
    .agg(
        F.count("*").alias("rows"),
        F.countDistinct("track_id").alias("distinct_tracks"),
        F.sum("first_in_release").alias("releases"),
        F.countDistinct("release_id").alias("distinct_releases"),
        F.sum("first_in_medium").alias("media"),
        F.countDistinct("medium_id").alias("distinct_media"),
        F.sum("first_of_recording").alias("recordings"),
        F.countDistinct("recording_id").alias("distinct_recordings"),
    )
    .first()
    .asDict()
)
log_metric("checks.fact", time.time() - started, checks["rows"], detail=json.dumps(checks))

started = time.time()
yearly = (
    spark.table(FACT_TABLE)
    .groupBy(F.floor(F.col("fecha_key") / 10000).alias("year"), "format_id")
    .agg(F.count("*").alias("tracks"), F.sum("duration_ms").alias("duration_ms"))
    .count()
)
log_metric("query.year_format", time.time() - started, yearly)

dbutils.notebook.exit(
    json.dumps({"expected_tracks": EXPECTED_TRACKS, "checks": checks}, default=str)
)
