# ============================================================================
# ETIQUETAS DE DIMENSIONES A PARTIR DE LOS CATÁLOGOS OFICIALES DEL VOLCADO
# El ID nunca se traduce aquí: silver.catalogo_* resuelve ID -> nombre oficial y
# estos diccionarios solo traducen ese nombre. Un nombre sin traducción conserva
# el oficial, y 06_validacion.py bloquea cualquier diferencia con el catálogo.
# ============================================================================

from functools import reduce

from pyspark.sql import functions as F

from lib.esquemas import CATALOGO

TIPO_ARTISTA = {
    "Person": "Persona / Solista", "Group": "Grupo / Banda", "Other": "Otro",
    "Character": "Personaje Ficticio", "Orchestra": "Orquesta", "Choir": "Coro",
}
GENERO = {
    "Male": "Masculino", "Female": "Femenino", "Other": "Otro",
    "Not applicable": "No Aplica", "Non-binary": "No Binario",
}
TIPO_AREA = {
    "Country": "País", "Subdivision": "Subdivisión", "City": "Ciudad",
    "Municipality": "Municipio", "District": "Distrito", "Island": "Isla",
    "County": "Condado", "Military base": "Base Militar",
    "Indigenous territory / reserve": "Territorio Indígena / Reserva",
}
ESTADO_LANZAMIENTO = {
    "Official": "Oficial", "Promotion": "Promocional", "Bootleg": "Bootleg / No Oficial",
    "Pseudo-Release": "Pseudo-Release", "Withdrawn": "Retirado / Withdrawn",
    "Cancelled": "Cancelado", "Expunged": "Eliminado / Expunged",
}
TIPO_EMPAQUE = {
    "Cardboard/Paper Sleeve": "Cardboard Sleeve / Funda", "Other": "Otro Embalaje",
    "None": "Sin Embalaje",
}
NOMBRE_FORMATO = {
    "Vinyl": "Vinilo", '7" Vinyl': 'Vinilo 7"', '10" Vinyl': 'Vinilo 10"',
    '12" Vinyl': 'Vinilo 12"', '3" Vinyl': 'Vinilo 3"', "Other": "Otro",
}

# MusicBrainz no publica la calidad como catálogo: es una constante de la aplicación.
CALIDAD_DATOS = {-1: "Sin calificar", 0: "Baja", 1: "Normal", 2: "Alta"}

DIGITAL = "Digital / Streaming"
VINILO = "Físico / Vinilo"
OPTICO = "Físico / Óptico"
MAGNETICO = "Físico / Magnético"
OTROS = "Otros Formatos"

# Categoría por nombre oficial; cada formato hereda la de su ancestro más cercano.
CATEGORIA_FORMATO = {
    "Digital Media": DIGITAL,
    "Vinyl": VINILO,
    "CD": OPTICO, "DVD": OPTICO, "SACD": OPTICO, "DualDisc": OPTICO, "LaserDisc": OPTICO,
    "MiniDisc": OPTICO, "Blu-ray": OPTICO, "VCD": OPTICO, "CDV": OPTICO, "HD-DVD": OPTICO,
    "UMD": OPTICO, "DVDplus": OPTICO,
    "Cassette": MAGNETICO, "VHS": MAGNETICO, "Cartridge": MAGNETICO, "Reel-to-reel": MAGNETICO,
    "DAT": MAGNETICO, "DCC": MAGNETICO, "Betamax": MAGNETICO, "Betacam SP": MAGNETICO,
    "Floppy Disk": MAGNETICO,
    "ROM cartridge": OTROS,
}


def leer_catalogo(spark, tabla):
    """Devuelve las filas (id, nombre, padre) de un catálogo oficial."""
    filas = spark.table(f"{CATALOGO}.silver.catalogo_{tabla}").select("id", "name", "parent").collect()
    return [(f["id"], f["name"], f["parent"]) for f in filas]


def etiquetas_por_id(catalogo, traducciones):
    return {identificador: traducciones.get(nombre, nombre) for identificador, nombre, _ in catalogo}


def categorias_por_id(catalogo):
    padres = {identificador: padre for identificador, _, padre in catalogo}
    nombres = {identificador: nombre for identificador, nombre, _ in catalogo}

    def categoria(identificador):
        while identificador is not None:
            nombre = nombres.get(identificador)
            if nombre in CATEGORIA_FORMATO:
                return CATEGORIA_FORMATO[nombre]
            identificador = padres.get(identificador)
        return OTROS

    return {identificador: categoria(identificador) for identificador in nombres}


def tabla_etiquetas(spark, etiquetas, columna_id, columna_etiqueta):
    """Convierte {id: etiqueta} en una tabla pequeña para unir con broadcast."""
    return F.broadcast(
        spark.createDataFrame(
            list(etiquetas.items()), f"`{columna_id}` INT, `{columna_etiqueta}` STRING"
        )
    )


def mapear(columna, valores, otro):
    """Traduce una columna entera a su etiqueta, como un CASE ... ELSE."""
    pares = list(valores.items())
    primero = F.when(columna == pares[0][0], pares[0][1])
    caso = reduce(lambda acc, par: acc.when(columna == par[0], par[1]), pares[1:], primero)
    return caso.otherwise(otro)
