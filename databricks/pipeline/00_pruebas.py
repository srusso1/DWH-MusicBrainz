# Databricks notebook source
# ============================================================================
# PRUEBAS DE REGLAS DE NEGOCIO (fixtures pequeñas en Databricks)
# Corren en el mismo runtime que el pipeline, sin leer las tablas completas.
# ============================================================================

import json
import traceback

from pyspark.sql import functions as F

from lib import catalogos as C
from lib import transformaciones as T


def filas(df, *columnas):
    return [tuple(fila[c] for c in columnas) for fila in df.select(*columnas).collect()]


def probar_pg_unescape():
    casos = [
        ("a\\tb", "a\tb"),
        ("a\\nb", "a\nb"),
        ("a\\rb", "a\rb"),
        ("a\\\\b", "a\\b"),
        ("a\\\\tb", "a\\tb"),
        ("sin escapes", "sin escapes"),
        (None, None),
    ]
    df = spark.createDataFrame([(c[0],) for c in casos], "v STRING")
    obtenido = dict(filas(df.withColumn("r", T.pg_unescape(F.col("v"))), "v", "r"))
    for entrada, esperado in casos:
        assert obtenido[entrada] == esperado, (entrada, obtenido[entrada], esperado)


def probar_fecha_key():
    casos = [
        (2020, 2, 29, 20200229),
        (2021, 2, 29, 20210201),
        (2021, 4, 31, 20210401),
        (1999, 13, 5, 19990101),
        (2021, 0, 5, 20210101),
        (2000, None, None, 20000101),
        (2000, 2, None, 20000201),
        (2000, None, 15, 20000101),
        (1899, 1, 1, 0),
        (2031, 1, 1, 0),
        (None, 1, 1, 0),
        (1900, 1, 1, 19000101),
        (2030, 12, 31, 20301231),
    ]
    df = spark.createDataFrame(
        [c[:3] for c in casos], "a INT, m INT, d INT"
    ).withColumn("k", T.fecha_key(F.col("a"), F.col("m"), F.col("d")))
    obtenido = {(a, m, d): k for a, m, d, k in filas(df, "a", "m", "d", "k")}
    for a, m, d, esperado in casos:
        assert obtenido[(a, m, d)] == esperado, (a, m, d, obtenido[(a, m, d)], esperado)


def probar_fecha_key_anual():
    df = spark.createDataFrame([(20200229,), (19000101,), (0,)], "k INT")
    obtenido = dict(filas(df.withColumn("a", T.fecha_key_anual(F.col("k"))), "k", "a"))
    assert obtenido == {20200229: 20200101, 19000101: 19000101, 0: 0}, obtenido


def probar_duracion_ms():
    casos = [(100, 200, 100), (0, 120, 120), (None, 120, 120), (None, None, 0), (0, 0, 0), (-5, 200, 0)]
    df = spark.createDataFrame([c[:2] for c in casos], "t INT, r INT").withColumn(
        "d", T.duracion_ms(F.col("t"), F.col("r"))
    )
    obtenido = {(t, r): d for t, r, d in filas(df, "t", "r", "d")}
    for t, r, esperado in casos:
        assert obtenido[(t, r)] == esperado, (t, r, obtenido[(t, r)], esperado)


def probar_rango_duracion():
    casos = {0: 0, -1: 0, 1: 1, 29999: 1, 30000: 2, 599999: 20, 600000: 21, 7200000: 21}
    df = spark.createDataFrame([(k,) for k in casos], "ms BIGINT").withColumn(
        "r", T.rango_duracion_key(F.col("ms"))
    )
    assert dict(filas(df, "ms", "r")) == casos


AREA_MUNDIAL = 240
ESQUEMA_PAIS = "release INT, country INT, date_year INT, date_month INT, date_day INT"
ESQUEMA_SIN_PAIS = "release INT, date_year INT, date_month INT, date_day INT"


def eventos_por_lanzamiento(eventos, sin_pais=None):
    conocidos = spark.createDataFrame(eventos, ESQUEMA_PAIS)
    desconocidos = spark.createDataFrame(sin_pais or [], ESQUEMA_SIN_PAIS)
    resultado = T.evento_primario(conocidos, desconocidos, AREA_MUNDIAL)
    return {
        f[0]: f[1:]
        for f in filas(resultado, "release", "country", "date_year", "date_month", "date_day", "regla_evento")
    }


def probar_evento_pais_unico():
    obtenido = eventos_por_lanzamiento(
        [(1, 7, 1999, 1, 1), (1, 1, 2000, 1, 1)],
        [(2, 2005, 6, 7)],
    )
    assert obtenido == {
        1: (7, 1999, 1, 1, "PAIS_UNICO"),
        2: (None, 2005, 6, 7, "SIN_PAIS"),
    }, obtenido


def probar_evento_diez_o_mas_paises_es_mundial():
    eventos = [(1, pais, 2001, 1, 1) for pais in range(1, 11)]
    assert eventos_por_lanzamiento(eventos)[1] == (AREA_MUNDIAL, 2001, 1, 1, "MUNDIAL_10_O_MAS")


def probar_evento_nueve_paises_no_es_mundial():
    # El país 5 aparece además en otros lanzamientos: es el de mayor presencia global.
    eventos = [(1, pais, 2001, 1, 1) for pais in range(1, 10)] + [(2, 5, 1990, 1, 1), (3, 5, 1991, 1, 1)]
    assert eventos_por_lanzamiento(eventos)[1] == (5, 2001, 1, 1, "EMPATE_PAIS_MAYOR")


def probar_evento_empate_de_dos_usa_pais_con_mas_lanzamientos():
    eventos = [
        (1, 3, 2001, 1, 1), (1, 9, 2001, 1, 1),
        (2, 9, 1990, 1, 1), (3, 9, 1991, 1, 1),
    ]
    assert eventos_por_lanzamiento(eventos)[1] == (9, 2001, 1, 1, "EMPATE_PAIS_MAYOR")


def probar_evento_empate_total_usa_menor_id():
    eventos = [(1, 4, 2001, 1, 1), (1, 8, 2001, 1, 1)]
    assert eventos_por_lanzamiento(eventos)[1] == (4, 2001, 1, 1, "EMPATE_PAIS_MAYOR")


def probar_evento_mundial_explicito_gana_el_empate():
    eventos = [(1, 1, 2001, 1, 1), (1, AREA_MUNDIAL, 2001, 1, 1), (1, 9, 2001, 1, 1)]
    assert eventos_por_lanzamiento(eventos)[1] == (AREA_MUNDIAL, 2001, 1, 1, "MUNDIAL_EXPLICITO")


def probar_evento_mundial_explicito_posterior_no_cuenta():
    eventos = [(1, 1, 2000, 1, 1), (1, AREA_MUNDIAL, 2001, 1, 1)]
    assert eventos_por_lanzamiento(eventos)[1] == (1, 2000, 1, 1, "PAIS_UNICO")


def probar_evento_solo_cuenta_paises_de_la_fecha_mas_antigua():
    eventos = [(1, pais, 2001, 1, 1) for pais in range(1, 10)] + [(1, 50, 2002, 1, 1), (1, 51, 2003, 1, 1)]
    assert eventos_por_lanzamiento(eventos)[1][4] == "EMPATE_PAIS_MAYOR"


def probar_evento_conserva_fecha_con_nulos_equivalentes():
    # Mes 12 y mes nulo empatan al ordenar; la fecha sigue siendo la del país de menor id.
    eventos = [(1, 2, 2001, None, None), (1, 3, 2001, 12, 31), (2, 3, 1990, 1, 1)]
    assert eventos_por_lanzamiento(eventos)[1] == (3, 2001, None, None, "EMPATE_PAIS_MAYOR")


def probar_evento_primario():
    conocidos = spark.createDataFrame(
        [
            (1, 10, 2001, 5, 1),
            (1, 20, 1999, 12, 31),
            (3, 30, None, None, None),
            (3, 40, 2000, 1, 1),
            (5, 60, 1980, None, None),
            (5, 70, 1980, 3, None),
        ],
        "release INT, country INT, date_year INT, date_month INT, date_day INT",
    )
    desconocidos = spark.createDataFrame(
        [(1, 1990, 1, 1), (2, 2005, 6, 7)],
        "release INT, date_year INT, date_month INT, date_day INT",
    )
    obtenido = {
        f[0]: f[1:]
        for f in filas(
            T.evento_primario(conocidos, desconocidos, AREA_MUNDIAL),
            "release", "country", "date_year", "date_month", "date_day",
        )
    }
    assert obtenido == {
        1: (20, 1999, 12, 31),
        2: (None, 2005, 6, 7),
        3: (40, 2000, 1, 1),
        5: (70, 1980, 3, None),
    }, obtenido


def probar_primeras_pistas():
    # Lanzamiento 1: soporte 10 (2 pistas) y 11. Lanzamiento 2 repite la grabación 500.
    base = spark.createDataFrame(
        [
            (100, 500, 10, 1, 1, 1),
            (101, 501, 10, 1, 1, 2),
            (102, 502, 11, 1, 2, 1),
            (103, 500, 20, 2, 1, 1),
        ],
        "track_id INT, recording_id INT, medium_id INT, release_id INT, "
        "medium_position INT, track_position INT",
    )
    obtenido = {
        f[0]: f[1:]
        for f in filas(
            T.marcar_primeras_pistas(base),
            "track_id", "es_primera_pista_lanzamiento", "es_primera_pista_soporte",
            "es_primera_aparicion_grabacion",
        )
    }
    assert obtenido == {
        100: (1, 1, 1),
        101: (0, 0, 1),
        102: (0, 1, 1),
        103: (1, 1, 0),
    }, obtenido


def probar_surrogada():
    df = spark.createDataFrame([(30,), (10,), (20,)], "id INT")
    obtenido = dict(filas(T.asignar_surrogada(df, "id", "clave"), "id", "clave"))
    assert obtenido == {10: 1, 20: 2, 30: 3}, obtenido


def probar_dim_fecha():
    dim = T.construir_dim_fecha(spark)
    assert dim.count() == 47_848
    assert dim.select("fecha_key").distinct().count() == 47_848
    cero = dim.where("fecha_key = 0").first()
    assert cero["nombre_mes"] == "Sin Fecha" and cero["fecha_completa"] is None
    bisiesto = dim.where("fecha_key = 20240229").first()
    assert bisiesto["nombre_mes"] == "Febrero" and bisiesto["nombre_dia"] == "Jueves"
    lunes = dim.where("fecha_key = 20240101").first()
    assert lunes["dia_semana"] == 1 and lunes["nombre_mes_corto"] == "Ene"
    assert lunes["decada"] == "2020s" and lunes["siglo"] == "Siglo XXI"
    assert lunes["trimestre"] == 1 and lunes["nombre_trimestre"] == "Q1"
    domingo = dim.where("fecha_key = 20240107").first()
    assert domingo["dia_semana"] == 7 and domingo["es_fin_de_semana"] is True
    assert dim.where("fecha_key = 19991231").first()["siglo"] == "Siglo XX"


def probar_dim_rango_duracion():
    dim = T.construir_dim_rango_duracion(spark)
    filas_dim = {f["rango_duracion_key"]: f for f in dim.collect()}
    assert len(filas_dim) == 22
    assert filas_dim[0]["etiqueta_rango"] == "Sin duración"
    assert filas_dim[1]["etiqueta_rango"] == "0:00–0:30"
    assert filas_dim[8]["etiqueta_rango"] == "3:30–4:00"
    assert filas_dim[8]["limite_inferior_seg"] == 210
    assert filas_dim[20]["etiqueta_rango"] == "9:30–10:00"
    assert filas_dim[21]["etiqueta_rango"] == "10:00+"
    assert filas_dim[21]["limite_superior_seg"] is None


def probar_calidad_datos():
    casos = {-1: "Sin calificar", 0: "Baja", 1: "Normal", 2: "Alta"}
    df = spark.createDataFrame([(k,) for k in casos], "q INT").withColumn(
        "e", C.mapear(F.col("q"), C.CALIDAD_DATOS, "Sin calificar")
    )
    assert dict(filas(df, "q", "e")) == casos


def probar_tipo_area_oficial():
    catalogo = [(3, "City", None), (5, "District", None), (6, "Island", None), (7, "County", None), (1, "Country", None)]
    assert C.etiquetas_por_id(catalogo, C.TIPO_AREA) == {
        3: "Ciudad", 5: "Distrito", 6: "Isla", 7: "Condado", 1: "País",
    }


def probar_genero_oficial():
    catalogo = [(1, "Male", None), (2, "Female", None), (3, "Other", None), (4, "Not applicable", None), (5, "Non-binary", None)]
    assert C.etiquetas_por_id(catalogo, C.GENERO) == {
        1: "Masculino", 2: "Femenino", 3: "Otro", 4: "No Aplica", 5: "No Binario",
    }


def probar_empaque_oficial():
    catalogo = [(7, "None", None), (8, "Cassette Case", None), (12, "Gatefold Cover", None)]
    assert C.etiquetas_por_id(catalogo, C.TIPO_EMPAQUE) == {
        7: "Sin Embalaje", 8: "Cassette Case", 12: "Gatefold Cover",
    }


def probar_nombre_formato_oficial():
    catalogo = [(33, "CD-R", 1), (7, "Vinyl", 73), (31, '12" Vinyl', 7), (13, "Other", None), (19, "DVD-Video", 2)]
    assert C.etiquetas_por_id(catalogo, C.NOMBRE_FORMATO) == {
        33: "CD-R", 7: "Vinilo", 31: 'Vinilo 12"', 13: "Otro", 19: "DVD-Video",
    }


def probar_categoria_formato_por_jerarquia():
    catalogo = [
        (1, "CD", None), (33, "CD-R", 1), (34, "8cm CD", 1), (210, "8cm CD-R", 34),
        (12, "Digital Media", None), (13, "Other", None), (14, "Wax Cylinder", 13),
        (15, "Piano Roll", 13), (16, "DCC", 13), (17, "HD-DVD", 13),
        (73, "Phonograph record", None), (7, "Vinyl", 73), (29, '7" Vinyl', 7),
        (53, "Shellac", 73), (54, '10" Shellac', 53), (9, "Cartridge", 13),
        (78, "8-Track Cartridge", 9), (208, "ROM cartridge", 9), (21, "VHS", None),
    ]
    assert C.categorias_por_id(catalogo) == {
        1: "Físico / Óptico", 33: "Físico / Óptico", 34: "Físico / Óptico", 210: "Físico / Óptico",
        12: "Digital / Streaming", 13: "Otros Formatos", 14: "Otros Formatos",
        15: "Otros Formatos", 16: "Físico / Magnético", 17: "Físico / Óptico",
        73: "Otros Formatos", 7: "Físico / Vinilo", 29: "Físico / Vinilo",
        53: "Otros Formatos", 54: "Otros Formatos", 9: "Físico / Magnético",
        78: "Físico / Magnético", 208: "Otros Formatos", 21: "Físico / Magnético",
    }


def probar_nombre_sin_traduccion_conserva_el_oficial():
    assert C.etiquetas_por_id([(99, "Nuevo Formato", None)], C.NOMBRE_FORMATO) == {99: "Nuevo Formato"}


# COMMAND ----------

resultados = {}
for nombre, prueba in sorted(globals().copy().items()):
    if nombre.startswith("probar_"):
        try:
            prueba()
            resultados[nombre] = "PASS"
        except Exception as error:
            resultados[nombre] = f"FAIL: {type(error).__name__}: {error}"
            traceback.print_exc()

fallidas = {k: v for k, v in resultados.items() if v != "PASS"}
print(json.dumps(resultados, indent=2, ensure_ascii=False))
if fallidas:
    raise AssertionError(json.dumps(fallidas, ensure_ascii=False)[:3000])

dbutils.notebook.exit(json.dumps(resultados))
