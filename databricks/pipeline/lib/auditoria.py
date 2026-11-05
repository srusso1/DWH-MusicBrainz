# ============================================================================
# AUDITORÍA DEL PIPELINE (equivalente a meta.etl_audit y meta.data_quality_log)
# Cada etapa queda registrada para reanudar si la cuota corta una corrida.
# ============================================================================

import time

from pyspark.sql import functions as F

from lib.esquemas import CATALOGO

TABLA_AUDITORIA = f"{CATALOGO}.meta.etl_audit"
TABLA_CALIDAD = f"{CATALOGO}.meta.data_quality_log"


def _agregar(spark, tabla, fila, esquema):
    (
        spark.createDataFrame([fila], esquema)
        .withColumn("registrado_en", F.current_timestamp())
        .write.mode("append")
        .option("mergeSchema", "true")
        .saveAsTable(tabla)
    )


def registrar_etapa(spark, dump_version, capa, tabla, operacion, filas, segundos, estado, error=None):
    _agregar(
        spark,
        TABLA_AUDITORIA,
        (dump_version, capa, tabla, operacion, filas, float(segundos), estado, error),
        "dump_version STRING, capa STRING, tabla STRING, operacion STRING, filas BIGINT, "
        "segundos DOUBLE, estado STRING, error STRING",
    )
    print(f"[{capa}] {tabla} {operacion}: {filas} filas, {segundos:.1f}s, {estado}")


def etapa_completada(spark, dump_version, tabla):
    if not spark.catalog.tableExists(tabla) or not spark.catalog.tableExists(TABLA_AUDITORIA):
        return False
    return (
        spark.table(TABLA_AUDITORIA)
        .where(
            (F.col("dump_version") == dump_version)
            & (F.col("tabla") == tabla)
            & F.col("estado").isin("SUCCESS", "REUSED")
        )
        .limit(1)
        .count()
        > 0
    )


def ejecutar_etapa(spark, dump_version, capa, tabla, construir, forzar=False):
    """Construye la tabla una sola vez por versión del volcado, salvo que se fuerce."""
    if not forzar and etapa_completada(spark, dump_version, tabla):
        print(f"[{capa}] {tabla}: ya completada, se omite")
        return
    inicio = time.time()
    try:
        construir()
        filas = spark.table(tabla).count()
    except Exception as error:
        registrar_etapa(
            spark, dump_version, capa, tabla, "BUILD", 0, time.time() - inicio, "FAILED",
            str(error)[:1000],
        )
        raise
    registrar_etapa(spark, dump_version, capa, tabla, "BUILD", filas, time.time() - inicio, "SUCCESS")


def registrar_regla(spark, dump_version, regla, descripcion, esperado, observado, severidad="ERROR"):
    estado = "PASS" if esperado == observado else ("WARN" if severidad == "WARN" else "FAIL")
    if severidad == "INFO":
        estado = "INFO"
    _agregar(
        spark,
        TABLA_CALIDAD,
        (dump_version, regla, descripcion, str(esperado), str(observado), severidad, estado),
        "dump_version STRING, regla STRING, descripcion STRING, esperado STRING, "
        "observado STRING, severidad STRING, estado STRING",
    )
    print(f"{estado:<5}{regla}: {descripcion} esperado={esperado} observado={observado}")
    return estado
