# ============================================================================
# REGLAS DE NEGOCIO PURAS DEL PIPELINE
# Funciones sin acceso a tablas: se validan con fixtures en 00_pruebas.py.
# ============================================================================

from pyspark.sql import Window
from pyspark.sql import functions as F

MESES = [
    ("Enero", "Ene"), ("Febrero", "Feb"), ("Marzo", "Mar"), ("Abril", "Abr"),
    ("Mayo", "May"), ("Junio", "Jun"), ("Julio", "Jul"), ("Agosto", "Ago"),
    ("Septiembre", "Sep"), ("Octubre", "Oct"), ("Noviembre", "Nov"), ("Diciembre", "Dic"),
]
DIAS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]


def pg_unescape(columna):
    """Revierte los escapes de COPY TEXT de PostgreSQL en una columna de texto."""
    # La barra doble va primero a un marcador para no reinterpretar "\\t" como tabulador.
    marcador = "\u0001"
    resultado = F.regexp_replace(columna, r"\\\\", marcador)
    resultado = F.regexp_replace(resultado, r"\\t", "\t")
    resultado = F.regexp_replace(resultado, r"\\n", "\n")
    resultado = F.regexp_replace(resultado, r"\\r", "\r")
    return F.regexp_replace(resultado, marcador, r"\\")


def fecha_key(anio, mes, dia):
    """Clave YYYYMMDD con fecha real (1900-2030); clave 0 si no existe.

    Mes inválido o ausente pasa a enero y día inválido o ausente pasa a 1, como
    en el ETL original, pero el 29 de febrero de un año bisiesto se conserva.
    """
    mes_valido = mes.between(1, 12)
    bisiesto = ((anio % 4 == 0) & (anio % 100 != 0)) | (anio % 400 == 0)
    dias_mes = (
        F.when(mes.isin(1, 3, 5, 7, 8, 10, 12), 31)
        .when(mes.isin(4, 6, 9, 11), 30)
        .when(bisiesto, 29)
        .otherwise(28)
    )
    mes_final = F.when(mes_valido, mes).otherwise(1)
    dia_final = F.when(mes_valido & dia.between(F.lit(1), dias_mes), dia).otherwise(1)
    return (
        F.when(anio.between(1900, 2030), anio * 10000 + mes_final * 100 + dia_final)
        .otherwise(0)
        .cast("int")
    )


def fecha_key_anual(columna_fecha_key):
    """Ancla una fecha_key al 1 de enero de su año; la clave 0 se mantiene."""
    return (
        F.when(
            columna_fecha_key > 0,
            F.floor(columna_fecha_key / 10000).cast("int") * 10000 + 101,
        )
        .otherwise(0)
        .cast("int")
    )


def duracion_ms(longitud_pista, longitud_grabacion):
    """Regla E01: usa la pista, luego la grabación maestra y nunca devuelve negativos."""
    pista = F.when(longitud_pista != 0, longitud_pista)
    grabacion = F.when(longitud_grabacion != 0, longitud_grabacion)
    return F.greatest(F.coalesce(pista, grabacion, F.lit(0)), F.lit(0)).cast("bigint")


def rango_duracion_key(columna_duracion_ms):
    """Bandas de 30 s: 0 sin duración, 1 a 20 hasta 10:00 y 21 para 10:00+."""
    return (
        F.when(columna_duracion_ms <= 0, 0)
        .when(columna_duracion_ms >= 600000, 21)
        .otherwise(F.floor(columna_duracion_ms / 30000).cast("int") + 1)
        .cast("int")
    )


def evento_primario(conocidos, desconocidos, area_mundial):
    """Evento primario por lanzamiento: fecha más antigua y un solo territorio.

    La fecha se conserva. El territorio se resuelve entre los países empatados en
    esa fecha, para que ningún país reciba un lanzamiento solo por tener menor id:
    un país queda igual; [Worldwide] explícito gana; 10 o más pasan a [Worldwide];
    de 2 a 9 gana el país con más lanzamientos y el menor id solo desempata.
    """
    columnas = ["release", "country", "date_year", "date_month", "date_day"]
    clave = ["prioridad", "orden_anio", "orden_mes", "orden_dia"]
    eventos = (
        conocidos.select(*columnas)
        .withColumn("prioridad", F.lit(1))
        .unionByName(
            desconocidos.withColumn("country", F.lit(None).cast("int"))
            .select(*columnas)
            .withColumn("prioridad", F.lit(2))
        )
        .withColumn("orden_anio", F.coalesce("date_year", F.lit(9999)))
        .withColumn("orden_mes", F.coalesce("date_month", F.lit(12)))
        .withColumn("orden_dia", F.coalesce("date_day", F.lit(31)))
    )

    primero = (
        eventos.groupBy("release")
        .agg(F.min(F.struct(*clave, *columnas[1:])).alias("evento"))
        .select(
            "release",
            *[F.col(f"evento.{c}").alias(c) for c in clave],
            *[F.col(f"evento.{c}").alias(c) for c in columnas[2:]],
        )
    )

    presencia = conocidos.groupBy("country").agg(F.count("*").alias("presencia"))
    empates = (
        eventos.select("release", "country", *clave)
        .join(primero.select("release", *clave), ["release", *clave])
        .join(presencia, "country", "left")
        .groupBy("release")
        .agg(
            F.count("*").alias("paises_empatados"),
            F.max((F.col("country") == area_mundial).cast("int")).alias("mundial_empatado"),
            F.min(
                F.struct(
                    (-F.coalesce(F.col("presencia"), F.lit(0))).alias("orden_presencia"),
                    F.col("country"),
                )
            ).alias("ganador"),
        )
    )

    regla = (
        F.when(F.col("ganador.country").isNull(), "SIN_PAIS")
        .when(F.col("paises_empatados") == 1, "PAIS_UNICO")
        .when(F.col("mundial_empatado") == 1, "MUNDIAL_EXPLICITO")
        .when(F.col("paises_empatados") >= 10, "MUNDIAL_10_O_MAS")
        .otherwise("EMPATE_PAIS_MAYOR")
    )
    return (
        primero.join(empates, "release")
        .withColumn("regla_evento", regla)
        .withColumn(
            "country",
            F.when(
                F.col("regla_evento").isin("MUNDIAL_EXPLICITO", "MUNDIAL_10_O_MAS"),
                F.lit(area_mundial),
            ).otherwise(F.col("ganador.country")),
        )
        .select(*columnas, "regla_evento", "paises_empatados")
    )


def _primera_pista(base, grupo, orden, nombre_bandera):
    """Marca con 1 la pista mínima por grupo. min(struct) evita ordenar cada partición."""
    return (
        base.groupBy(grupo)
        .agg(F.min(F.struct(*orden)).alias("primera"))
        .select(F.col("primera.track_id").alias("track_id"), F.lit(1).alias(nombre_bandera))
    )


def marcar_primeras_pistas(base):
    """Agrega las banderas que hacen aditivos lanzamientos, soportes y grabaciones."""
    primeras = [
        _primera_pista(
            base,
            "release_id",
            ["medium_position", "medium_id", "track_position", "track_id"],
            "es_primera_pista_lanzamiento",
        ),
        _primera_pista(
            base,
            "medium_id",
            ["track_position", "track_id"],
            "es_primera_pista_soporte",
        ),
        _primera_pista(
            base,
            "recording_id",
            ["release_id", "medium_position", "track_position", "track_id"],
            "es_primera_aparicion_grabacion",
        ),
    ]
    resultado = base
    for primera in primeras:
        resultado = resultado.join(primera, "track_id", "left")
    return resultado.fillna(
        0,
        subset=[
            "es_primera_pista_lanzamiento",
            "es_primera_pista_soporte",
            "es_primera_aparicion_grabacion",
        ],
    )


def asignar_surrogada(df, columna_orden, nombre_clave):
    """Clave sustituta secuencial desde 1, reproducible por el orden de la clave natural."""
    return df.withColumn(
        nombre_clave, F.row_number().over(Window.orderBy(columna_orden)).cast("int")
    )


def construir_dim_fecha(spark):
    """Calendario diario 1900-2030 más la fila 0 'Sin Fecha'."""
    dias = spark.sql(
        "SELECT explode(sequence(DATE'1900-01-01', DATE'2030-12-31', INTERVAL 1 DAY)) AS d"
    )
    meses = F.array(*[F.lit(m[0]) for m in MESES])
    meses_cortos = F.array(*[F.lit(m[1]) for m in MESES])
    nombres_dias = F.array(*[F.lit(d) for d in DIAS])
    dia_iso = ((F.dayofweek("d") + 5) % 7 + 1).cast("int")

    calendario = dias.select(
        F.date_format("d", "yyyyMMdd").cast("int").alias("fecha_key"),
        F.col("d").alias("fecha_completa"),
        F.year("d").alias("anio"),
        F.quarter("d").alias("trimestre"),
        F.concat(F.lit("Q"), F.quarter("d").cast("string")).alias("nombre_trimestre"),
        F.month("d").alias("mes"),
        F.element_at(meses, F.month("d")).alias("nombre_mes"),
        F.element_at(meses_cortos, F.month("d")).alias("nombre_mes_corto"),
        F.dayofmonth("d").alias("dia"),
        dia_iso.alias("dia_semana"),
        F.element_at(nombres_dias, dia_iso).alias("nombre_dia"),
        dia_iso.isin(6, 7).alias("es_fin_de_semana"),
        F.concat((F.floor(F.year("d") / 10) * 10).cast("string"), F.lit("s")).alias("decada"),
        F.when(F.year("d") < 2000, "Siglo XX").otherwise("Siglo XXI").alias("siglo"),
    )
    sin_fecha = spark.createDataFrame(
        [(0, None, 0, 0, "N/A", 0, "Sin Fecha", "N/A", 0, 0, "Sin Fecha", False, "Sin Década", "Sin Siglo")],
        "fecha_key INT, fecha_completa DATE, anio INT, trimestre INT, nombre_trimestre STRING, "
        "mes INT, nombre_mes STRING, nombre_mes_corto STRING, dia INT, dia_semana INT, "
        "nombre_dia STRING, es_fin_de_semana BOOLEAN, decada STRING, siglo STRING",
    )
    return sin_fecha.unionByName(calendario)


def construir_dim_rango_duracion(spark):
    """22 bandas: clave 0, 20 bandas de 30 s y la banda abierta 10:00+."""

    def etiqueta(segundos):
        return f"{segundos // 60}:{segundos % 60:02d}"

    filas = [(0, 0, "Sin duración", None, None)]
    for n in range(20):
        inferior, superior = n * 30, (n + 1) * 30
        filas.append((n + 1, n + 1, f"{etiqueta(inferior)}–{etiqueta(superior)}", inferior, superior))
    filas.append((21, 21, "10:00+", 600, None))
    return spark.createDataFrame(
        filas,
        "rango_duracion_key INT, orden INT, etiqueta_rango STRING, "
        "limite_inferior_seg INT, limite_superior_seg INT",
    )
