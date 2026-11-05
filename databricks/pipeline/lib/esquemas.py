# ============================================================================
# CONTRATO DE DATOS DEL VOLCADO MUSICBRAINZ (Schema Sequence 31)
# Orden real de columnas de cada archivo y tipo de destino en Silver.
# Tipos: int, smallint, text (revierte escapes), string, boolean, timestamp.
# ============================================================================

CATALOGO = "workspace"
DUMP_VERSION = "20261104-002222"
AREA_MUNDIAL = "[Worldwide]"

TABLAS = {
    "area": {
        "id": "int", "gid": "string", "name": "text", "type": "int",
        "edits_pending": "int", "last_updated": "timestamp",
        "begin_date_year": "smallint", "begin_date_month": "smallint",
        "begin_date_day": "smallint", "end_date_year": "smallint",
        "end_date_month": "smallint", "end_date_day": "smallint",
        "ended": "boolean", "comment": "text",
    },
    "artist": {
        "id": "int", "gid": "string", "name": "text", "sort_name": "text",
        "begin_date_year": "smallint", "begin_date_month": "smallint",
        "begin_date_day": "smallint", "end_date_year": "smallint",
        "end_date_month": "smallint", "end_date_day": "smallint",
        "type": "int", "area": "int", "gender": "int", "comment": "text",
        "edits_pending": "int", "last_updated": "timestamp", "ended": "boolean",
        "begin_area": "int", "end_area": "int",
    },
    "artist_credit_name": {
        "artist_credit": "int", "position": "smallint", "artist": "int",
        "name": "text", "join_phrase": "text",
    },
    "release": {
        "id": "int", "gid": "string", "name": "text", "artist_credit": "int",
        "release_group": "int", "status": "int", "packaging": "int",
        "language": "int", "script": "int", "barcode": "text", "comment": "text",
        "edits_pending": "int", "quality": "smallint", "last_updated": "timestamp",
    },
    "release_country": {
        "release": "int", "country": "int", "date_year": "smallint",
        "date_month": "smallint", "date_day": "smallint",
    },
    "release_unknown_country": {
        "release": "int", "date_year": "smallint", "date_month": "smallint",
        "date_day": "smallint",
    },
    # Corrige el DDL de PostgreSQL: edits_pending es la columna 6 y track_count la 8.
    "medium": {
        "id": "int", "release": "int", "position": "int", "format": "int",
        "name": "text", "edits_pending": "int", "last_updated": "timestamp",
        "track_count": "int", "gid": "string",
    },
    "isrc": {
        "id": "int", "recording": "int", "isrc": "string", "source": "smallint",
        "created": "timestamp",
    },
    "recording": {
        "id": "int", "gid": "string", "name": "text", "artist_credit": "int",
        "length": "int", "comment": "text", "edits_pending": "int",
        "last_updated": "timestamp", "video": "boolean",
    },
    "track": {
        "id": "int", "gid": "string", "recording": "int", "medium": "int",
        "position": "int", "number": "text", "name": "text",
        "artist_credit": "int", "length": "int", "edits_pending": "int",
        "last_updated": "timestamp", "is_data_track": "boolean",
    },
    "language": {
        "id": "int", "iso_code_2t": "string", "iso_code_2b": "string",
        "iso_code_1": "string", "name": "text", "frequency": "int",
        "iso_code_3": "string",
    },
}

# Líneas de cada archivo del volcado, contadas con wc -l antes de subirlo.
FILAS_VOLCADO = {
    "20261104-002222": {
        "area": 120120,
        "artist": 3032671,
        "artist_credit_name": 7364652,
        "release": 5903902,
        "release_country": 13360406,
        "release_unknown_country": 489710,
        "medium": 6474432,
        "isrc": 6579238,
        "recording": 40826836,
        "track": 58809976,
        "language": 7846,
    }
}

# Catálogos oficiales del mismo volcado y sus filas contadas con wc -l.
CATALOGOS_OFICIALES = {
    "area_type": 9,
    "artist_type": 6,
    "gender": 5,
    "medium_format": 115,
    "release_packaging": 24,
    "release_status": 7,
}

# Clave primaria natural de Silver por tabla.
CLAVES_PRIMARIAS = {
    "area": ["id"],
    "artist": ["id"],
    "artist_credit_name": ["artist_credit", "position"],
    "release": ["id"],
    "release_country": ["release", "country"],
    "release_unknown_country": ["release"],
    "medium": ["id"],
    "isrc": ["id"],
    "recording": ["id"],
    "track": ["id"],
    "language": ["id"],
}
