# Databricks notebook source
# ============================================================================
# CATÁLOGOS OFICIALES: fuente de verdad de las etiquetas de dimensiones.
# Se leen del Volume sin copiarlos en el código y quedan en silver.catalogo_*.
# ============================================================================

from pyspark.sql import functions as F

from lib.auditoria import ejecutar_etapa
from lib.esquemas import CATALOGO, CATALOGOS_OFICIALES, DUMP_VERSION

dbutils.widgets.text("dump_version", DUMP_VERSION)
dbutils.widgets.text("forzar", "false")
dump_version = dbutils.widgets.get("dump_version")
forzar = dbutils.widgets.get("forzar") == "true"

directorio = f"/Volumes/{CATALOGO}/landing/mbdump/{dump_version}/mbdump"

# COMMAND ----------


def cargar(tabla):
    (
        spark.read.option("sep", "\t")
        .option("nullValue", "\\N")
        .option("quote", "")
        .option("header", "false")
        .option("inferSchema", "false")
        .csv(f"{directorio}/{tabla}")
        .select(
            F.col("_c0").cast("int").alias("id"),
            F.col("_c1").alias("name"),
            F.col("_c2").cast("int").alias("parent"),
        )
        .write.mode("overwrite")
        .option("overwriteSchema", "true")
        .saveAsTable(f"{CATALOGO}.silver.catalogo_{tabla}")
    )


for tabla, esperadas in CATALOGOS_OFICIALES.items():
    destino = f"{CATALOGO}.silver.catalogo_{tabla}"
    ejecutar_etapa(spark, dump_version, "CATALOGOS", destino, lambda t=tabla: cargar(t), forzar)
    filas = spark.table(destino).count()
    if filas != esperadas:
        raise ValueError(f"{destino}: {filas} filas, se esperaban {esperadas}")
