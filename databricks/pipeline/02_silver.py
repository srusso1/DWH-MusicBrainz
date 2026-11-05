# Databricks notebook source
# ============================================================================
# CAPA SILVER: tipos correctos, escapes revertidos y control de calidad.
# try_cast no detiene la carga: toda pérdida de conversión se mide y se registra
# en meta.data_quality_log, y una pérdida mayor que cero hace fallar la etapa.
# ============================================================================

from pyspark.sql import functions as F

from lib.auditoria import ejecutar_etapa, registrar_regla
from lib.esquemas import CATALOGO, CLAVES_PRIMARIAS, DUMP_VERSION, TABLAS
from lib.transformaciones import pg_unescape

dbutils.widgets.text("dump_version", DUMP_VERSION)
dbutils.widgets.text("forzar", "false")
dump_version = dbutils.widgets.get("dump_version")
forzar = dbutils.widgets.get("forzar") == "true"

# COMMAND ----------


def tipar(columna, tipo):
    if tipo == "text":
        return pg_unescape(F.col(columna)).alias(columna)
    if tipo == "string":
        return F.col(columna)
    if tipo == "boolean":
        return (
            F.when(F.col(columna) == "t", True)
            .when(F.col(columna) == "f", False)
            .alias(columna)
        )
    return F.expr(f"try_cast(`{columna}` AS {tipo})").alias(columna)


def construir(tabla):
    columnas = [tipar(c, t) for c, t in TABLAS[tabla].items()]
    (
        spark.table(f"{CATALOGO}.bronze.{tabla}")
        .select(*columnas)
        .write.mode("overwrite")
        .option("overwriteSchema", "true")
        .saveAsTable(f"{CATALOGO}.silver.{tabla}")
    )


def perdidas_de_conversion(tabla):
    """Valores no nulos en Bronze que quedaron nulos en Silver, por tabla."""
    columnas = list(TABLAS[tabla])
    conteos = [F.count(c).alias(c) for c in columnas]
    origen = spark.table(f"{CATALOGO}.bronze.{tabla}").agg(*conteos).first().asDict()
    destino = spark.table(f"{CATALOGO}.silver.{tabla}").agg(*conteos).first().asDict()
    return {c: origen[c] - destino[c] for c in columnas if origen[c] != destino[c]}


# COMMAND ----------

fallas = []
for tabla in TABLAS:
    destino = f"{CATALOGO}.silver.{tabla}"
    ejecutar_etapa(spark, dump_version, "SILVER", destino, lambda t=tabla: construir(t), forzar)

    perdidas = perdidas_de_conversion(tabla)
    fallas.append(
        registrar_regla(
            spark, dump_version, f"S01.{tabla}", "Sin pérdidas de conversión de tipos", {}, perdidas,
        )
    )
    claves = CLAVES_PRIMARIAS[tabla]
    silver = spark.table(destino)
    duplicados = silver.count() - silver.select(*claves).distinct().count()
    fallas.append(
        registrar_regla(spark, dump_version, f"S02.{tabla}", "Clave primaria única", 0, duplicados)
    )

if "FAIL" in fallas:
    raise ValueError("Silver no superó el control de calidad; ver meta.data_quality_log")
