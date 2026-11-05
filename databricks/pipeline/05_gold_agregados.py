# Databricks notebook source
# ============================================================================
# AGREGADOS GOLD PARA POWER BI: mismos nombres y columnas del modelo semántico.
# Todos se calculan desde gold.fact_pista, la única fuente de verdad.
# Las vistas materializadas de PostgreSQL pasan a ser tablas Delta mv_*.
# ============================================================================

from lib.auditoria import ejecutar_etapa
from lib.esquemas import CATALOGO, DUMP_VERSION

dbutils.widgets.text("dump_version", DUMP_VERSION)
dbutils.widgets.text("forzar", "false")
dbutils.widgets.text("solo", "")
dump_version = dbutils.widgets.get("dump_version")
forzar = dbutils.widgets.get("forzar") == "true"
solo = [t.strip() for t in dbutils.widgets.get("solo").split(",") if t.strip()]

G = f"{CATALOGO}.gold"

CONSULTAS = {
    "fact_produccion_musical": (
        "(fecha_key, artista_key)",
        f"""
        SELECT
            monotonically_increasing_id() AS hecho_key,
            *
        FROM (
            SELECT
                fecha_key, artista_key, lanzamiento_key, geografia_key, formato_key, idioma_key,
                CAST(SUM(es_primera_pista_lanzamiento) AS INT) AS lanzamientos_total,
                CAST(SUM(es_primera_pista_soporte) AS INT) AS soportes_total,
                CAST(COUNT(*) AS INT) AS pistas_total,
                CAST(SUM(es_primera_aparicion_grabacion) AS INT) AS grabaciones_unicas_total,
                SUM(duracion_ms) AS duracion_total_ms,
                CAST(ROUND(SUM(duracion_ms) / 1000.0, 2) AS DECIMAL(18, 2)) AS duracion_total_segundos,
                CAST(ROUND(SUM(duracion_ms) / 60000.0, 2) AS DECIMAL(18, 2)) AS duracion_total_minutos,
                CAST(SUM(tiene_isrc) AS INT) AS pistas_con_isrc_total,
                CAST(SUM(es_pista_larga) AS INT) AS pistas_largas_total,
                CAST(SUM(es_video) AS INT) AS pistas_video_total,
                CAST(SUM(es_pista_completa) AS INT) AS pistas_completas_total
            FROM {G}.fact_pista
            GROUP BY fecha_key, artista_key, lanzamiento_key, geografia_key, formato_key, idioma_key
        )
        """,
    ),
    "fact_distribucion_duracion": (
        "(fecha_key, rango_duracion_key)",
        f"""
        SELECT
            CASE WHEN fecha_key > 0 THEN CAST(FLOOR(fecha_key / 10000) AS INT) * 10000 + 101 ELSE 0 END AS fecha_key,
            formato_key,
            idioma_key,
            geografia_key,
            rango_duracion_key,
            CAST(COUNT(*) AS INT) AS pistas_total,
            SUM(duracion_ms) AS duracion_total_ms
        FROM {G}.fact_pista
        GROUP BY 1, 2, 3, 4, 5
        """,
    ),
    "mv_tendencias_produccion_anual": (
        "(anio)",
        f"""
        SELECT
            d.anio, d.decada, d.siglo,
            SUM(f.lanzamientos_total) AS lanzamientos_total,
            SUM(f.soportes_total) AS soportes_total,
            SUM(f.pistas_total) AS pistas_total,
            COUNT(DISTINCT f.artista_key) AS artistas_activos,
            ROUND(SUM(f.duracion_total_minutos), 2) AS duracion_total_minutos,
            ROUND(SUM(f.duracion_total_segundos) / NULLIF(SUM(f.pistas_completas_total), 0), 2)
                AS duracion_promedio_segundos,
            SUM(f.pistas_con_isrc_total) AS pistas_con_isrc_total,
            SUM(f.pistas_largas_total) AS pistas_largas_total,
            SUM(f.pistas_video_total) AS pistas_video_total,
            ROUND(SUM(f.pistas_con_isrc_total) * 100.0 / NULLIF(SUM(f.pistas_total), 0), 2)
                AS cobertura_isrc_pct
        FROM {G}.fact_produccion_musical f
        JOIN {G}.dim_fecha d ON f.fecha_key = d.fecha_key
        WHERE d.anio BETWEEN 1950 AND 2026
        GROUP BY d.anio, d.decada, d.siglo
        """,
    ),
    "mv_analitica_artistas": (
        "(artista_key)",
        f"""
        SELECT
            a.artista_key, a.artista_id, a.nombre_artista, a.tipo_artista,
            a.genero, a.nombre_pais, a.anio_inicio,
            SUM(f.lanzamientos_total) AS lanzamientos_total,
            SUM(f.soportes_total) AS soportes_total,
            SUM(f.pistas_total) AS pistas_total,
            ROUND(SUM(f.duracion_total_minutos), 2) AS duracion_total_minutos,
            ROUND(SUM(f.duracion_total_segundos) / NULLIF(SUM(f.pistas_completas_total), 0), 2)
                AS duracion_promedio_segundos,
            SUM(f.pistas_con_isrc_total) AS pistas_con_isrc_total,
            SUM(f.pistas_largas_total) AS pistas_largas_total,
            ROUND(SUM(f.pistas_con_isrc_total) * 100.0 / NULLIF(SUM(f.pistas_total), 0), 2)
                AS cobertura_isrc_pct
        FROM {G}.fact_produccion_musical f
        JOIN {G}.dim_artista a ON f.artista_key = a.artista_key
        GROUP BY a.artista_key, a.artista_id, a.nombre_artista, a.tipo_artista,
                 a.genero, a.nombre_pais, a.anio_inicio
        """,
    ),
    "mv_evolucion_formatos": (
        "(anio)",
        f"""
        SELECT
            d.anio, d.decada, fmt.nombre_formato, fmt.categoria_formato,
            SUM(f.lanzamientos_total) AS lanzamientos_total,
            SUM(f.soportes_total) AS soportes_total,
            SUM(f.pistas_total) AS pistas_total,
            SUM(f.pistas_largas_total) AS pistas_largas_total,
            ROUND(SUM(f.duracion_total_minutos), 2) AS duracion_total_minutos,
            ROUND(SUM(f.duracion_total_segundos) / NULLIF(SUM(f.pistas_completas_total), 0), 2)
                AS duracion_promedio_segundos
        FROM {G}.fact_produccion_musical f
        JOIN {G}.dim_fecha d ON f.fecha_key = d.fecha_key
        JOIN {G}.dim_formato fmt ON f.formato_key = fmt.formato_key
        WHERE d.anio BETWEEN 1950 AND 2026
        GROUP BY d.anio, d.decada, fmt.nombre_formato, fmt.categoria_formato
        """,
    ),
    "mv_distribucion_geografica": (
        "(geografia_key)",
        f"""
        SELECT
            g.geografia_key, g.nombre_pais, g.nombre_area, g.tipo_area,
            COUNT(DISTINCT f.artista_key) AS artistas_total,
            SUM(f.lanzamientos_total) AS lanzamientos_total,
            SUM(f.soportes_total) AS soportes_total,
            SUM(f.pistas_total) AS pistas_total,
            SUM(f.pistas_con_isrc_total) AS pistas_con_isrc_total,
            ROUND(SUM(f.duracion_total_minutos) / 60.0, 2) AS duracion_total_horas
        FROM {G}.fact_produccion_musical f
        JOIN {G}.dim_geografia g ON f.geografia_key = g.geografia_key
        GROUP BY g.geografia_key, g.nombre_pais, g.nombre_area, g.tipo_area
        """,
    ),
}

# COMMAND ----------

for nombre, (agrupacion, consulta) in CONSULTAS.items():
    if solo and nombre not in solo:
        continue
    tabla = f"{G}.{nombre}"
    ejecutar_etapa(
        spark,
        dump_version,
        "GOLD_AGG",
        tabla,
        lambda t=tabla, a=agrupacion, q=consulta: spark.sql(
            f"CREATE OR REPLACE TABLE {t} CLUSTER BY {a} AS {q}"
        ),
        forzar,
    )
