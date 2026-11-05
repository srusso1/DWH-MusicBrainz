# Databricks notebook source
# ============================================================================
# CAPA GOLD: 7 dimensiones conformadas con patrón de fila cero (Kimball).
# Nombres y columnas compatibles con el modelo semántico de Power BI.
# ============================================================================

from pyspark.sql import functions as F

from lib import catalogos as C
from lib.auditoria import ejecutar_etapa
from lib.esquemas import CATALOGO, DUMP_VERSION
from lib.transformaciones import asignar_surrogada, construir_dim_fecha, construir_dim_rango_duracion

dbutils.widgets.text("dump_version", DUMP_VERSION)
dbutils.widgets.text("forzar", "false")
dbutils.widgets.text("solo", "")
dump_version = dbutils.widgets.get("dump_version")
forzar = dbutils.widgets.get("forzar") == "true"
solo = [t.strip() for t in dbutils.widgets.get("solo").split(",") if t.strip()]

GID_CERO = "00000000-0000-0000-0000-000000000000"


def silver(tabla):
    return spark.table(f"{CATALOGO}.silver.{tabla}")


def guardar(df, nombre):
    (
        df.write.mode("overwrite")
        .option("overwriteSchema", "true")
        .saveAsTable(f"{CATALOGO}.gold.{nombre}")
    )


def etiquetas(catalogo, traducciones, columna_id, columna_etiqueta):
    valores = C.etiquetas_por_id(C.leer_catalogo(spark, catalogo), traducciones)
    return C.tabla_etiquetas(spark, valores, columna_id, columna_etiqueta)


def con_fila_cero(cuerpo, clave, fila_cero):
    """Antepone la fila 0 y asigna claves sustitutas desde 1 al resto."""
    columnas = [clave, *[c for c in cuerpo.columns if c != clave]]
    return fila_cero.select(*columnas).unionByName(cuerpo.select(*columnas))


# COMMAND ----------


def dim_fecha():
    guardar(construir_dim_fecha(spark), "dim_fecha")


def dim_rango_duracion():
    guardar(construir_dim_rango_duracion(spark), "dim_rango_duracion")


def dim_geografia():
    tipos = etiquetas("area_type", C.TIPO_AREA, "type", "etiqueta_tipo")
    cuerpo = silver("area").join(tipos, "type", "left").select(
        F.col("id").alias("area_id"),
        F.col("gid").alias("area_gid"),
        F.col("name").alias("nombre_area"),
        F.coalesce(F.col("etiqueta_tipo"), F.lit("Otro / No Clasificado")).alias("tipo_area"),
        F.when(F.col("type") == 1, F.col("name")).otherwise("No Aplica").alias("nombre_pais"),
    )
    cero = spark.createDataFrame(
        [(0, 0, GID_CERO, "Sin Área Registrada", "Desconocido", "Sin País Registrado")],
        "geografia_key INT, area_id INT, area_gid STRING, nombre_area STRING, "
        "tipo_area STRING, nombre_pais STRING",
    )
    df = con_fila_cero(asignar_surrogada(cuerpo, "area_id", "geografia_key"), "geografia_key", cero)
    guardar(df.withColumn("creado_en", F.current_timestamp()), "dim_geografia")


def dim_artista():
    area = silver("area").select(
        F.col("id").alias("area"),
        F.col("name").alias("nombre_area_origen"),
        F.col("type").alias("tipo_area_origen"),
    )
    tipos = etiquetas("artist_type", C.TIPO_ARTISTA, "type", "etiqueta_tipo")
    generos = etiquetas("gender", C.GENERO, "gender", "etiqueta_genero")
    nombre_limpio = F.nullif(F.trim(F.col("name")), F.lit(""))
    artistas = (
        silver("artist")
        .join(area, "area", "left")
        .join(tipos, "type", "left")
        .join(generos, "gender", "left")
    )
    cuerpo = artistas.select(
        F.col("id").alias("artista_id"),
        F.col("gid").alias("artista_gid"),
        F.coalesce(nombre_limpio, F.lit("Sin Nombre")).alias("nombre_artista"),
        F.col("sort_name").alias("nombre_orden"),
        F.coalesce(F.col("etiqueta_tipo"), F.lit("No Clasificado")).alias("tipo_artista"),
        F.coalesce(F.col("etiqueta_genero"), F.lit("Desconocido")).alias("genero"),
        F.coalesce(F.col("area"), F.lit(0)).alias("area_id"),
        F.coalesce(F.col("nombre_area_origen"), F.lit("Sin Área Registrada")).alias("nombre_area"),
        F.when(F.col("tipo_area_origen") == 1, F.col("nombre_area_origen"))
        .otherwise("No Aplica")
        .alias("nombre_pais"),
        F.nullif(F.col("begin_date_year"), F.lit(0)).cast("int").alias("anio_inicio"),
        F.nullif(F.col("end_date_year"), F.lit(0)).cast("int").alias("anio_fin"),
        F.coalesce(F.col("ended"), F.lit(False)).alias("finalizado"),
    )
    cero = spark.createDataFrame(
        [(0, 0, GID_CERO, "Artista Desconocido", "Artista Desconocido", "Desconocido",
          "Desconocido", 0, "Sin Área Registrada", "Sin País Registrado", None, None, False)],
        "artista_key INT, artista_id INT, artista_gid STRING, nombre_artista STRING, "
        "nombre_orden STRING, tipo_artista STRING, genero STRING, area_id INT, nombre_area STRING, "
        "nombre_pais STRING, anio_inicio INT, anio_fin INT, finalizado BOOLEAN",
    )
    df = con_fila_cero(asignar_surrogada(cuerpo, "artista_id", "artista_key"), "artista_key", cero)
    guardar(df.withColumn("creado_en", F.current_timestamp()), "dim_artista")


def dim_lanzamiento():
    perfiles = (
        silver("release")
        .select(
            F.coalesce(F.col("status"), F.lit(0)).alias("estado_id"),
            F.coalesce(F.col("packaging"), F.lit(0)).alias("empaque_id"),
            F.coalesce(F.col("quality").cast("int"), F.lit(0)).alias("calidad_id"),
        )
        .distinct()
        .where("NOT (estado_id = 0 AND empaque_id = 0 AND calidad_id = 0)")
    )
    estados = etiquetas("release_status", C.ESTADO_LANZAMIENTO, "estado_id", "etiqueta_estado")
    empaques = etiquetas("release_packaging", C.TIPO_EMPAQUE, "empaque_id", "etiqueta_empaque")
    cuerpo = perfiles.join(estados, "estado_id", "left").join(empaques, "empaque_id", "left").select(
        "estado_id",
        "empaque_id",
        "calidad_id",
        F.coalesce(F.col("etiqueta_estado"), F.lit("No Clasificado")).alias("estado_lanzamiento"),
        F.coalesce(F.col("etiqueta_empaque"), F.lit("Estándar / Desconocido")).alias("tipo_empaque"),
        C.mapear(F.col("calidad_id"), C.CALIDAD_DATOS, "Sin calificar").alias("calidad_datos"),
    )
    # La fila 0 la ocupan lanzamientos reales sin estado ni empaque y con calidad 0.
    cero = spark.createDataFrame(
        [(0, 0, 0, 0, "No Clasificado", "Estándar / Desconocido", C.CALIDAD_DATOS[0])],
        "lanzamiento_key INT, estado_id INT, empaque_id INT, calidad_id INT, "
        "estado_lanzamiento STRING, tipo_empaque STRING, calidad_datos STRING",
    )
    orden = ["estado_id", "empaque_id", "calidad_id"]
    df = con_fila_cero(asignar_surrogada(cuerpo, orden, "lanzamiento_key"), "lanzamiento_key", cero)
    guardar(df.withColumn("creado_en", F.current_timestamp()), "dim_lanzamiento")


def dim_formato():
    formatos = (
        silver("medium")
        .select(F.coalesce(F.col("format"), F.lit(0)).alias("formato_id"))
        .distinct()
        .where("formato_id <> 0")
    )
    catalogo = C.leer_catalogo(spark, "medium_format")
    nombres = C.tabla_etiquetas(
        spark, C.etiquetas_por_id(catalogo, C.NOMBRE_FORMATO), "formato_id", "etiqueta_formato"
    )
    categorias = C.tabla_etiquetas(spark, C.categorias_por_id(catalogo), "formato_id", "etiqueta_categoria")
    otro = F.concat(F.lit("Otro Formato ("), F.col("formato_id").cast("string"), F.lit(")"))
    cuerpo = formatos.join(nombres, "formato_id", "left").join(categorias, "formato_id", "left").select(
        "formato_id",
        F.coalesce(F.col("etiqueta_formato"), otro).alias("nombre_formato"),
        F.coalesce(F.col("etiqueta_categoria"), F.lit(C.OTROS)).alias("categoria_formato"),
    )
    cero = spark.createDataFrame(
        [(0, 0, "Formato No Especificado", "Desconocido")],
        "formato_key INT, formato_id INT, nombre_formato STRING, categoria_formato STRING",
    )
    guardar(
        con_fila_cero(asignar_surrogada(cuerpo, "formato_id", "formato_key"), "formato_key", cero),
        "dim_formato",
    )


def dim_idioma():
    usados = (
        silver("release")
        .where("language IS NOT NULL AND language <> 0")
        .select(F.col("language").alias("id"))
        .distinct()
    )
    cuerpo = usados.join(silver("language"), "id", "left").select(
        F.col("id").alias("idioma_id"),
        F.coalesce(
            F.col("name"),
            F.concat(F.lit("Idioma Desconocido ("), F.col("id").cast("string"), F.lit(")")),
        ).alias("nombre_idioma"),
        F.coalesce(F.col("iso_code_3"), F.col("iso_code_2t"), F.lit("und")).alias("codigo_iso"),
    )
    cero = spark.createDataFrame(
        [(0, 0, "Idioma No Especificado", "und")],
        "idioma_key INT, idioma_id INT, nombre_idioma STRING, codigo_iso STRING",
    )
    guardar(
        con_fila_cero(asignar_surrogada(cuerpo, "idioma_id", "idioma_key"), "idioma_key", cero),
        "dim_idioma",
    )


# COMMAND ----------

for construir in [dim_fecha, dim_rango_duracion, dim_geografia, dim_artista, dim_lanzamiento, dim_formato, dim_idioma]:
    if solo and construir.__name__ not in solo:
        continue
    tabla = f"{CATALOGO}.gold.{construir.__name__}"
    ejecutar_etapa(spark, dump_version, "GOLD_DIM", tabla, construir, forzar)
