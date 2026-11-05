# Databricks notebook source
# ============================================================================
# HECHO A NIVEL DE PISTA: gold.fact_pista
# Grano: una fila por pista. Solo claves y medidas numéricas (reglas E01-E07).
# Banderas de primera aparición: permiten sumar lanzamientos, soportes y
# grabaciones sin doble conteo. Las agregadas para Power BI salen de esta tabla.
# ============================================================================

from pyspark.sql import functions as F

from lib import transformaciones as T
from lib.auditoria import ejecutar_etapa
from lib.esquemas import AREA_MUNDIAL, CATALOGO, DUMP_VERSION

dbutils.widgets.text("dump_version", DUMP_VERSION)
dbutils.widgets.text("forzar", "false")
dump_version = dbutils.widgets.get("dump_version")
forzar = dbutils.widgets.get("forzar") == "true"

TABLA = f"{CATALOGO}.gold.fact_pista"


def silver(tabla):
    return spark.table(f"{CATALOGO}.silver.{tabla}")


def gold(tabla):
    return spark.table(f"{CATALOGO}.gold.{tabla}")


# COMMAND ----------


def id_area_mundial():
    filas = silver("area").where(F.col("name") == AREA_MUNDIAL).select("id").collect()
    if len(filas) != 1:
        raise ValueError(f"Se esperaba una sola área {AREA_MUNDIAL}, hay {len(filas)}")
    return filas[0]["id"]


def construir_fact_pista():
    pistas = silver("track").select(
        F.col("id").alias("track_id"),
        F.col("recording").alias("recording_id"),
        F.col("medium").alias("medium_id"),
        F.col("position").alias("track_position"),
        F.col("artist_credit").alias("track_credit"),
        F.col("length").alias("track_length"),
    )
    soportes = silver("medium").select(
        F.col("id").alias("medium_id"),
        F.col("release").alias("release_id"),
        F.col("position").alias("medium_position"),
        F.col("format").alias("format_id"),
    )
    lanzamientos = silver("release").select(
        F.col("id").alias("release_id"),
        F.col("artist_credit").alias("release_credit"),
        F.coalesce(F.col("status"), F.lit(0)).alias("estado_id"),
        F.coalesce(F.col("packaging"), F.lit(0)).alias("empaque_id"),
        F.coalesce(F.col("quality").cast("int"), F.lit(0)).alias("calidad_id"),
        F.coalesce(F.col("language"), F.lit(0)).alias("idioma_id"),
    )
    grabaciones = silver("recording").select(
        F.col("id").alias("recording_id"),
        F.col("length").alias("recording_length"),
        F.coalesce(F.col("video"), F.lit(False)).cast("int").alias("es_video"),
    )
    con_isrc = (
        silver("isrc")
        .select(F.col("recording").alias("recording_id"))
        .distinct()
        .withColumn("tiene_isrc", F.lit(1))
    )
    eventos = T.evento_primario(
        silver("release_country"), silver("release_unknown_country"), id_area_mundial()
    ).select(
        F.col("release").alias("release_id"),
        F.col("country").alias("evento_area"),
        "date_year",
        "date_month",
        "date_day",
    )
    credito_principal = silver("artist_credit_name").where("position = 0")
    credito_pista = credito_principal.select(
        F.col("artist_credit").alias("track_credit"), F.col("artist").alias("artista_pista")
    )
    credito_lanzamiento = credito_principal.select(
        F.col("artist_credit").alias("release_credit"), F.col("artist").alias("artista_lanzamiento")
    )

    base = T.marcar_primeras_pistas(pistas.join(soportes, "medium_id").join(lanzamientos, "release_id"))

    artistas = gold("dim_artista").select("artista_id", "artista_key", F.col("area_id").alias("area_artista"))
    geografia = F.broadcast(gold("dim_geografia").select("area_id", "geografia_key"))
    formatos = F.broadcast(gold("dim_formato").select("formato_id", "formato_key"))
    idiomas = F.broadcast(gold("dim_idioma").select("idioma_id", "idioma_key"))
    perfiles = F.broadcast(
        gold("dim_lanzamiento").select("estado_id", "empaque_id", "calidad_id", "lanzamiento_key")
    )
    fechas = F.broadcast(gold("dim_fecha").select("fecha_key"))

    enriquecida = (
        base.join(grabaciones, "recording_id", "left")
        .join(con_isrc, "recording_id", "left")
        .join(eventos, "release_id", "left")
        .join(credito_pista, "track_credit", "left")
        .join(credito_lanzamiento, "release_credit", "left")
        # Regla E03: nunca se usa un artist_credit como si fuera un artist.id.
        .withColumn("artista_id", F.coalesce("artista_pista", "artista_lanzamiento", F.lit(0)))
        .join(artistas, "artista_id", "left")
        .withColumn(
            "area_id",
            F.coalesce("evento_area", F.nullif(F.col("area_artista"), F.lit(0)), F.lit(0)),
        )
        .withColumn("formato_id", F.coalesce("format_id", F.lit(0)))
        .withColumn("fecha_candidata", T.fecha_key(F.col("date_year"), F.col("date_month"), F.col("date_day")))
        .withColumn("duracion_ms", T.duracion_ms(F.col("track_length"), F.col("recording_length")))
        .join(geografia, "area_id", "left")
        .join(formatos, "formato_id", "left")
        .join(idiomas, "idioma_id", "left")
        .join(perfiles, ["estado_id", "empaque_id", "calidad_id"], "left")
        .join(fechas, F.col("fecha_candidata") == F.col("fecha_key"), "left")
    )

    return enriquecida.select(
        F.col("track_id").alias("pista_id"),
        F.col("recording_id").alias("grabacion_id"),
        F.col("medium_id").alias("soporte_id"),
        F.col("release_id").alias("lanzamiento_id"),
        # Regla E07: cualquier clave sin dimensión cae en la fila cero.
        F.coalesce("fecha_key", F.lit(0)).alias("fecha_key"),
        F.coalesce("artista_key", F.lit(0)).alias("artista_key"),
        F.coalesce("lanzamiento_key", F.lit(0)).alias("lanzamiento_key"),
        F.coalesce("geografia_key", F.lit(0)).alias("geografia_key"),
        F.coalesce("formato_key", F.lit(0)).alias("formato_key"),
        F.coalesce("idioma_key", F.lit(0)).alias("idioma_key"),
        T.rango_duracion_key(F.col("duracion_ms")).alias("rango_duracion_key"),
        "duracion_ms",
        F.coalesce("tiene_isrc", F.lit(0)).alias("tiene_isrc"),
        F.coalesce("es_video", F.lit(0)).alias("es_video"),
        (F.col("duracion_ms") > 300000).cast("int").alias("es_pista_larga"),
        (F.col("duracion_ms") > 0).cast("int").alias("es_pista_completa"),
        "es_primera_pista_lanzamiento",
        "es_primera_pista_soporte",
        "es_primera_aparicion_grabacion",
    )


def guardar_fact_pista():
    construir_fact_pista().createOrReplaceTempView("fact_pista_nueva")
    spark.sql(
        f"CREATE OR REPLACE TABLE {TABLA} CLUSTER BY (fecha_key, artista_key) "
        "AS SELECT * FROM fact_pista_nueva"
    )


# COMMAND ----------

ejecutar_etapa(spark, dump_version, "GOLD_FACT", TABLA, guardar_fact_pista, forzar)
