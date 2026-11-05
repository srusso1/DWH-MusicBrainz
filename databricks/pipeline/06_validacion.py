# Databricks notebook source
# ============================================================================
# VALIDACIÓN FINAL: Delta no impone claves foráneas, así que la integridad se
# prueba aquí. Resultados en meta.data_quality_log; un FAIL detiene el job.
# ============================================================================

from pyspark.sql import functions as F

from lib import catalogos as C
from lib import transformaciones as T
from lib.auditoria import registrar_regla
from lib.esquemas import AREA_MUNDIAL, CATALOGO, CATALOGOS_OFICIALES, DUMP_VERSION, FILAS_VOLCADO, TABLAS

dbutils.widgets.text("dump_version", DUMP_VERSION)
dump_version = dbutils.widgets.get("dump_version")

B, S, G = f"{CATALOGO}.bronze", f"{CATALOGO}.silver", f"{CATALOGO}.gold"
FILAS_MINIMAS_HECHO = 50_000_000

CLAVES_HECHO = {
    "fecha_key": "dim_fecha",
    "artista_key": "dim_artista",
    "lanzamiento_key": "dim_lanzamiento",
    "geografia_key": "dim_geografia",
    "formato_key": "dim_formato",
    "idioma_key": "dim_idioma",
}
CLAVES_DISTRIBUCION = {
    "fecha_key": "dim_fecha",
    "formato_key": "dim_formato",
    "idioma_key": "dim_idioma",
    "geografia_key": "dim_geografia",
    "rango_duracion_key": "dim_rango_duracion",
}
DIMENSIONES = {
    "dim_fecha": "fecha_key",
    "dim_artista": "artista_key",
    "dim_lanzamiento": "lanzamiento_key",
    "dim_geografia": "geografia_key",
    "dim_formato": "formato_key",
    "dim_idioma": "idioma_key",
    "dim_rango_duracion": "rango_duracion_key",
}


def escalar(consulta):
    return spark.sql(consulta).first()[0]


estados = []


def regla(codigo, descripcion, esperado, observado, severidad="ERROR"):
    estados.append(registrar_regla(spark, dump_version, codigo, descripcion, esperado, observado, severidad))


# COMMAND ----------

# V01: las filas del volcado llegan completas a Bronze y Silver.
esperadas = FILAS_VOLCADO[dump_version]
for tabla in TABLAS:
    regla(f"V01.bronze.{tabla}", "Bronze coincide con el volcado", esperadas[tabla], spark.table(f"{B}.{tabla}").count())
    regla(f"V01.silver.{tabla}", "Silver coincide con el volcado", esperadas[tabla], spark.table(f"{S}.{tabla}").count())

# V02: claves foráneas de Silver que sostienen el hecho.
for codigo, hijo, columna, padre in [
    ("track_medium", "track", "medium", "medium"),
    ("track_recording", "track", "recording", "recording"),
    ("medium_release", "medium", "release", "release"),
]:
    regla(
        f"V02.{codigo}",
        f"Sin huérfanos {hijo}.{columna} -> {padre}.id",
        0,
        escalar(f"SELECT COUNT(*) FROM {S}.{hijo} h LEFT ANTI JOIN {S}.{padre} p ON h.{columna} = p.id"),
    )

# V03: claves únicas en dimensiones y fila cero presente.
for dimension, clave in DIMENSIONES.items():
    total, distintas, cero = spark.sql(
        f"SELECT COUNT(*), COUNT(DISTINCT {clave}), COUNT_IF({clave} = 0) FROM {G}.{dimension}"
    ).first()
    regla(f"V03.{dimension}.unica", "Clave única", total, distintas)
    regla(f"V03.{dimension}.cero", "Fila cero presente", 1, cero)

# V04 (E07): cero huérfanos en los tres hechos.
for hecho, claves in [
    ("fact_pista", CLAVES_HECHO),
    ("fact_produccion_musical", CLAVES_HECHO),
    ("fact_distribucion_duracion", CLAVES_DISTRIBUCION),
]:
    for clave, dimension in claves.items():
        regla(
            f"V04.{hecho}.{clave}",
            f"Sin huérfanos hacia {dimension}",
            0,
            escalar(f"SELECT COUNT(*) FROM {G}.{hecho} f LEFT ANTI JOIN {G}.{dimension} d ON f.{clave} = d.{clave}"),
        )

# V05: grano, volumen y aditividad de fact_pista.
filas, pistas_distintas, lanzamientos, lanzamientos_distintos, soportes, soportes_distintos, grabaciones, grabaciones_distintas = spark.sql(
    f"""
    SELECT COUNT(*), COUNT(DISTINCT pista_id),
           SUM(es_primera_pista_lanzamiento), COUNT(DISTINCT lanzamiento_id),
           SUM(es_primera_pista_soporte), COUNT(DISTINCT soporte_id),
           SUM(es_primera_aparicion_grabacion), COUNT(DISTINCT grabacion_id)
    FROM {G}.fact_pista
    """
).first()
regla("V05.grano", "Una fila por pista", filas, pistas_distintas)
regla("V05.filas_origen", "fact_pista conserva todas las pistas", esperadas["track"], filas)
regla("V05.volumen", "Supera 50 M de filas", True, filas > FILAS_MINIMAS_HECHO)
regla("V05.lanzamientos", "Lanzamientos aditivos", lanzamientos_distintos, lanzamientos)
regla("V05.soportes", "Soportes aditivos", soportes_distintos, soportes)
regla("V05.grabaciones", "Grabaciones aditivas", grabaciones_distintas, grabaciones)

# V06: los agregados reconcilian con el detalle.
agregado = spark.sql(
    f"""
    SELECT SUM(lanzamientos_total), SUM(soportes_total), SUM(pistas_total),
           SUM(grabaciones_unicas_total), SUM(duracion_total_ms), SUM(pistas_con_isrc_total),
           SUM(pistas_largas_total), SUM(pistas_video_total), SUM(pistas_completas_total)
    FROM {G}.fact_produccion_musical
    """
).first()
detalle = spark.sql(
    f"""
    SELECT SUM(es_primera_pista_lanzamiento), SUM(es_primera_pista_soporte), COUNT(*),
           SUM(es_primera_aparicion_grabacion), SUM(duracion_ms), SUM(tiene_isrc),
           SUM(es_pista_larga), SUM(es_video), SUM(es_pista_completa)
    FROM {G}.fact_pista
    """
).first()
regla("V06.produccion", "fact_produccion_musical reconcilia con fact_pista", tuple(detalle), tuple(agregado))
distribucion = spark.sql(f"SELECT SUM(pistas_total), SUM(duracion_total_ms) FROM {G}.fact_distribucion_duracion").first()
regla("V06.distribucion", "fact_distribucion_duracion reconcilia", (detalle[2], detalle[4]), tuple(distribucion))

# V07: medidas no negativas.
regla(
    "V07.no_negativos",
    "Sin medidas negativas",
    0,
    escalar(f"SELECT COUNT(*) FROM {G}.fact_pista WHERE duracion_ms < 0"),
)

# V08-V10: cada etiqueta coincide con el catálogo oficial del volcado.
REGLAS_CATALOGO = [
    ("area_type", C.TIPO_AREA, "Otro / No Clasificado",
     f"SELECT d.tipo_area AS etiqueta, s.type AS id FROM {S}.area s JOIN {G}.dim_geografia d ON s.id = d.area_id"),
    ("artist_type", C.TIPO_ARTISTA, "No Clasificado",
     f"SELECT d.tipo_artista AS etiqueta, s.type AS id FROM {S}.artist s JOIN {G}.dim_artista d ON s.id = d.artista_id"),
    ("gender", C.GENERO, "Desconocido",
     f"SELECT d.genero AS etiqueta, s.gender AS id FROM {S}.artist s JOIN {G}.dim_artista d ON s.id = d.artista_id"),
    ("release_status", C.ESTADO_LANZAMIENTO, "No Clasificado",
     f"SELECT estado_lanzamiento AS etiqueta, NULLIF(estado_id, 0) AS id FROM {G}.dim_lanzamiento"),
    ("release_packaging", C.TIPO_EMPAQUE, "Estándar / Desconocido",
     f"SELECT tipo_empaque AS etiqueta, NULLIF(empaque_id, 0) AS id FROM {G}.dim_lanzamiento"),
]
for catalogo, traducciones, sin_dato, consulta in REGLAS_CATALOGO:
    oficial = C.leer_catalogo(spark, catalogo)
    esperado = C.etiquetas_por_id(oficial, traducciones)
    C.tabla_etiquetas(spark, esperado, "id", "esperada").createOrReplaceTempView("catalogo_esperado")
    regla(
        f"V08.{catalogo}",
        "Etiquetas iguales al catálogo oficial",
        0,
        escalar(
            f"""
            SELECT COUNT(*) FROM ({consulta}) d LEFT JOIN catalogo_esperado c ON d.id = c.id
            WHERE d.etiqueta <> COALESCE(c.esperada, "{sin_dato}")
            """
        ),
    )
    # Un ID ausente del catálogo no puede quedar oculto como dato sin clasificar.
    regla(
        f"V09.{catalogo}",
        "Todos los ID existen en el catálogo",
        0,
        escalar(
            f"""
            SELECT COUNT(*) FROM ({consulta}) d LEFT ANTI JOIN catalogo_esperado c ON d.id = c.id
            WHERE d.id IS NOT NULL
            """
        ),
    )
    regla(
        f"V10.{catalogo}",
        "Las traducciones usan nombres oficiales",
        [],
        sorted(set(traducciones) - {nombre for _, nombre, _ in oficial}),
    )

catalogo_formato = C.leer_catalogo(spark, "medium_format")
nombres_oficiales = C.etiquetas_por_id(catalogo_formato, C.NOMBRE_FORMATO)
categorias_oficiales = C.categorias_por_id(catalogo_formato)
formatos = {f["formato_id"]: f for f in spark.table(f"{G}.dim_formato").where("formato_id <> 0").collect()}
regla(
    "V08.medium_format.nombre",
    "Nombres iguales al catálogo oficial",
    [],
    sorted(i for i, f in formatos.items() if f["nombre_formato"] != nombres_oficiales.get(i)),
)
regla(
    "V08.medium_format.categoria",
    "Categorías iguales a la jerarquía oficial",
    [],
    sorted(i for i, f in formatos.items() if f["categoria_formato"] != categorias_oficiales.get(i)),
)
regla("V09.medium_format", "Todos los ID existen en el catálogo", [], sorted(set(formatos) - set(nombres_oficiales)))
regla(
    "V10.medium_format",
    "Las traducciones usan nombres oficiales",
    [],
    sorted((set(C.NOMBRE_FORMATO) | set(C.CATEGORIA_FORMATO)) - {n for _, n, _ in catalogo_formato}),
)
calidades = spark.table(f"{G}.dim_lanzamiento").select("calidad_id", "calidad_datos").distinct().collect()
regla(
    "V08.calidad",
    "Calidad según la constante de MusicBrainz",
    [],
    sorted(f["calidad_id"] for f in calidades if C.CALIDAD_DATOS.get(f["calidad_id"]) != f["calidad_datos"]),
)

# V11: los catálogos cargados están completos.
for catalogo, filas_catalogo in CATALOGOS_OFICIALES.items():
    regla(f"V11.{catalogo}", "Catálogo completo", filas_catalogo, spark.table(f"{S}.catalogo_{catalogo}").count())

# V12: ningún país recibe lanzamientos multiterritorio por un empate de fechas.
# Se recalcula en SQL, sin usar evento_primario, para no validar la regla consigo misma.
area_mundial = escalar(f"SELECT id FROM {S}.area WHERE name = '{AREA_MUNDIAL}'")
spark.sql(
    f"""
    WITH eventos AS (
      SELECT release, country, COALESCE(date_year, 9999) AS a, COALESCE(date_month, 12) AS m, COALESCE(date_day, 31) AS d
      FROM {S}.release_country
    ),
    presencia AS (SELECT country, COUNT(*) AS total FROM {S}.release_country GROUP BY country),
    empates AS (
      SELECT e.release, e.country, p.total
      FROM eventos e
      JOIN (SELECT release, MIN(struct(a, m, d)) AS k FROM eventos GROUP BY release) x
        ON e.release = x.release AND struct(e.a, e.m, e.d) = x.k
      JOIN presencia p ON e.country = p.country
    )
    SELECT release,
           COUNT(*) AS n,
           MAX(CASE WHEN country = {area_mundial} THEN 1 ELSE 0 END) AS con_mundial,
           MIN(struct(-total, country)).country AS mayor
    FROM empates
    GROUP BY release
    HAVING COUNT(*) >= 2
    """
).createOrReplaceTempView("empates_territorio")
spark.sql(
    f"""
    SELECT DISTINCT f.lanzamiento_id, g.area_id
    FROM {G}.fact_pista f
    JOIN {G}.dim_geografia g ON f.geografia_key = g.geografia_key
    """
).createOrReplaceTempView("area_lanzamiento")
regla(
    "V12.mundial",
    "Empates de 10+ países o con [Worldwide] quedan en [Worldwide]",
    0,
    escalar(
        f"""
        SELECT COUNT(*) FROM empates_territorio e
        JOIN area_lanzamiento a ON e.release = a.lanzamiento_id
        WHERE (e.n >= 10 OR e.con_mundial = 1) AND a.area_id <> {area_mundial}
        """
    ),
)
regla(
    "V12.empate",
    "Empates de 2 a 9 países quedan en el país con más lanzamientos",
    0,
    escalar(
        """
        SELECT COUNT(*) FROM empates_territorio e
        JOIN area_lanzamiento a ON e.release = a.lanzamiento_id
        WHERE e.n < 10 AND e.con_mundial = 0 AND a.area_id <> e.mayor
        """
    ),
)
regla(
    "V12.grano",
    "Cada lanzamiento con evento de país tiene un solo territorio",
    0,
    escalar(
        f"""
        SELECT COUNT(*) FROM (
          SELECT a.lanzamiento_id
          FROM area_lanzamiento a
          JOIN (SELECT DISTINCT release FROM {S}.release_country) r ON a.lanzamiento_id = r.release
          GROUP BY a.lanzamiento_id
          HAVING COUNT(*) > 1
        )
        """
    ),
)
caminos = T.evento_primario(
    spark.table(f"{S}.release_country"), spark.table(f"{S}.release_unknown_country"), area_mundial
).groupBy("regla_evento").agg(F.count("*").alias("lanzamientos"))
for fila in caminos.collect():
    regla(f"I06.{fila['regla_evento']}", "Lanzamientos por regla de evento primario", "-", fila["lanzamientos"], "INFO")

# I01-I05: indicadores informativos, no bloquean.
regla("I01.sin_fecha", "Pistas en fecha_key 0", "-", escalar(f"SELECT COUNT(*) FROM {G}.fact_pista WHERE fecha_key = 0"), "INFO")
regla("I02.sin_artista", "Pistas en artista_key 0", "-", escalar(f"SELECT COUNT(*) FROM {G}.fact_pista WHERE artista_key = 0"), "INFO")
regla("I03.sin_geografia", "Pistas en geografia_key 0", "-", escalar(f"SELECT COUNT(*) FROM {G}.fact_pista WHERE geografia_key = 0"), "INFO")
regla("I04.bisiestos", "Pistas fechadas un 29 de febrero", "-", escalar(f"SELECT COUNT(*) FROM {G}.fact_pista WHERE fecha_key % 10000 = 229"), "INFO")
regla(
    "I05.bom",
    "E08: nombres de artista con BOM",
    "-",
    escalar(f"SELECT COUNT(*) FROM {S}.artist WHERE startswith(name, '\\uFEFF')"),
    "INFO",
)

fallidas = estados.count("FAIL")
print(f"Reglas: {len(estados)}, fallidas: {fallidas}")
if fallidas:
    raise ValueError(f"{fallidas} reglas fallaron; ver meta.data_quality_log")

dbutils.notebook.exit(f"{len(estados)} reglas evaluadas, 0 fallidas")
