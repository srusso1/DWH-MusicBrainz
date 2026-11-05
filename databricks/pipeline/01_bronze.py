# Databricks notebook source
# ============================================================================
# CAPA BRONZE: copia fiel del volcado en Delta, todas las columnas como texto.
# Conserva los escapes de COPY TEXT; se revierten en Silver para no alterar
# nunca el dato crudo. Reutiliza tablas existentes si su conteo coincide.
# ============================================================================

import time

from pyspark.sql.types import StringType, StructField, StructType

from lib.auditoria import ejecutar_etapa, etapa_completada, registrar_etapa
from lib.esquemas import CATALOGO, DUMP_VERSION, FILAS_VOLCADO, TABLAS

dbutils.widgets.text("dump_version", DUMP_VERSION)
dbutils.widgets.text("forzar", "false")
dump_version = dbutils.widgets.get("dump_version")
forzar = dbutils.widgets.get("forzar") == "true"

directorio = f"/Volumes/{CATALOGO}/landing/mbdump/{dump_version}/mbdump"
esperadas = FILAS_VOLCADO[dump_version]

# COMMAND ----------


def cargar(tabla):
    esquema = StructType([StructField(c, StringType()) for c in TABLAS[tabla]])
    (
        spark.read.schema(esquema)
        .option("sep", "\t")
        .option("nullValue", "\\N")
        .option("quote", "")
        .option("mode", "FAILFAST")
        .csv(f"{directorio}/{tabla}")
        .write.mode("overwrite")
        .option("overwriteSchema", "true")
        .saveAsTable(f"{CATALOGO}.bronze.{tabla}")
    )


for tabla in TABLAS:
    destino = f"{CATALOGO}.bronze.{tabla}"
    if not forzar and spark.catalog.tableExists(destino) and not etapa_completada(spark, dump_version, destino):
        inicio = time.time()
        filas = spark.table(destino).count()
        columnas = spark.table(destino).columns
        if filas == esperadas[tabla] and columnas == list(TABLAS[tabla]):
            registrar_etapa(spark, dump_version, "BRONZE", destino, "REUSE", filas, time.time() - inicio, "REUSED")
            continue
    ejecutar_etapa(spark, dump_version, "BRONZE", destino, lambda t=tabla: cargar(t), forzar)
    filas = spark.table(destino).count()
    if filas != esperadas[tabla]:
        raise ValueError(f"{destino}: {filas} filas, se esperaban {esperadas[tabla]}")
