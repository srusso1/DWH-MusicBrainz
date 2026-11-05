"""
build_documentacion_tecnica_pdf.py
==================================
Genera la documentación técnica completa de la migración a Databricks. Todas las
cifras salen de docs/build/metricas_databricks.json.

Uso:
    python scripts/build_documentacion_tecnica_pdf.py [ruta_salida.pdf]
"""

import sys
from pathlib import Path

from reportlab.platypus import KeepTogether, NextPageTemplate, PageBreak, Spacer

from doc_pdf_comun import (
    AMARILLO, AZUL, BASE_DIR, DURAZNO, LAVANDA, MENTA, PANEL, Documento, P, aviso, code, dashboard, diagrama_arquitectura,
    diagrama_estrella, figura, fmt_dec, fmt_gb, fmt_int, fmt_mill, fmt_mmss, fmt_pct, fmt_signo, g_cuota, g_tareas,
    indice, metricas, portada_factory, rejilla_kpi, seccion, tabla, vinetas,
)

SALIDA = BASE_DIR / "docs" / "Documentacion_Tecnica_DWMusicBrainz.pdf"

REFERENCIAS = [
    ("Databricks. Free Edition limitations.", "https://docs.databricks.com/aws/en/getting-started/free-edition-limitations"),
    ("Databricks. Serverless compute limitations.", "https://docs.databricks.com/aws/en/compute/serverless/limitations"),
    ("Databricks. Best practices for DBFS and Unity Catalog.", "https://docs.databricks.com/en/dbfs/unity-catalog.html"),
    ("Databricks. Tables concepts.", "https://docs.databricks.com/aws/tables"),
    ("Databricks. Use liquid clustering for tables.", "https://docs.databricks.com/aws/en/delta/clustering"),
    ("Databricks. Pipeline task for jobs.", "https://docs.databricks.com/en/jobs/pipeline.html"),
    ("Databricks. Upload files to a volume.", "https://docs.databricks.com/en/ingestion/add-data/upload-to-volume.html"),
    ("Databricks. Dashboard concepts.", "https://docs.databricks.com/aws/en/dashboards/concepts"),
    ("Databricks. Dashboard limits.", "https://docs.databricks.com/aws/en/dashboards/limits"),
    ("Databricks. Delta UniForm: universal format for lakehouse interoperability.", "https://databricks.com/blog/delta-uniform-universal-format-lakehouse-interoperability"),
    ("DuckDB. Tuning workloads: larger-than-memory workloads.", "https://duckdb.org/docs/current/guides/performance/how_to_tune_workloads"),
    ("Google Cloud. BigQuery sandbox.", "https://cloud.google.com/bigquery/docs/sandbox"),
    ("Snowflake. Página de prueba gratuita.", "https://signup.snowflake.com"),
    ("Amazon Web Services. Amazon Redshift free trial.", "https://aws.amazon.com/redshift/free-trial"),
    ("Microsoft. Fabric trial.", "https://learn.microsoft.com/fabric/get-started/fabric-trial"),
    ("Apache Spark. SPARK-46910: Java mínimo para Spark 4.", "https://issues.apache.org/jira/browse/SPARK-46910"),
    ("Logz.io. Comparing Apache Hive vs. Spark (fuente secundaria).", "https://logz.io/blog/hive-vs-spark/"),
    ("MetaBrainz. Volcados completos de MusicBrainz.", "https://data.metabrainz.org/pub/musicbrainz/data/fullexport/"),
]


def ref(*n):
    return "[" + ", ".join(str(i) for i in n) + "]"


def decision(numero, titulo, elegido, razones, alternativas, costo, evidencia):
    bloque = [P(f"ADR-{numero:02d}. {titulo}", "h2"), tabla([
        ["Decisión", elegido],
        ["Por qué", razones],
        ["Costo real", costo],
        ["Base", evidencia],
    ], [2.5, 14.4], encabezado=False, primera_negrita=True), Spacer(1, 4)]
    bloque.append(tabla([["Alternativa", "Por qué no se eligió"]] + alternativas, [4.7, 12.2], primera_negrita=True, fondo=LAVANDA))
    return [KeepTogether(bloque), Spacer(1, 8)]


def historia(m):
    T, G, H, E, PR = m["totales"], m["conteos"]["gold"], m["histograma"], m["especiales"], m["proceso"]
    S_C = m["conteos"]["silver"]
    B_C = m["conteos"]["bronze"]
    SILVER = m["conteos"]["silver_principales_total"]
    ANT = m["carga_anterior"]
    P_L, P_90, P_R = m["pearson"]
    LV = dashboard()
    widgets = sum(len(p["layout"]) for p in LV["pages"])
    COMP, FINAL = m["corridas"]["completa"], m["corridas"]["final"]
    bloqueantes = sum(r["reglas"] for r in m["calidad_log"] if r["severidad"] == "ERROR")
    aprobadas = sum(r["reglas"] for r in m["calidad_log"] if r["severidad"] == "ERROR" and r["estado"] == "PASS")
    finales = sum(r["reglas"] for r in m["reglas_grupos"] if r["grupo"].startswith("V"))
    silver_r = sum(r["reglas"] for r in m["reglas_grupos"] if r["grupo"].startswith("S"))
    info = sum(r["reglas"] for r in m["reglas_grupos"] if r["grupo"].startswith("I"))
    grupos = {r["grupo"]: r["reglas"] for r in m["reglas_grupos"]}
    cap = {e["etapa"]: e for e in m["prueba_capacidad"]}
    cap_bronze = sum(e["segundos"] for k, e in cap.items() if k.startswith("bronze."))
    cap_hecho = cap["gold.spike_fact_pista"]["segundos"]
    tam_s = sum(v["bytes"] for v in m["detalle"]["silver"].values())
    tam_g = sum(v["bytes"] for v in m["detalle"]["gold"].values())
    sin_cal = next(c for c in m["calidad"] if c["calidad"] == "Sin calificar")["lanzamientos"]
    a = PR["afganistan_antes"]
    cam = PR["caminos_evento"]
    fil = PR["filtros"]

    h = [NextPageTemplate("normal"), PageBreak()]
    h.append(P("Índice", "h1_indice"))
    h.append(Spacer(1, 8))
    h.append(indice())

    # ------------------------------------------------------------------ 1
    seccion(h, "Sección 1", "Resumen para la defensa")
    h.append(P(
        f"<b>El proyecto cumple el requisito de más de 50 millones de registros.</b> DWMusicBrainz pasó de PostgreSQL a Databricks y ahora procesa el volcado completo de MusicBrainz: "
        f"<b>{fmt_int(T['pistas'])} pistas</b> en {code('gold.fact_pista')}, con un pipeline de {COMP['segundos']} segundos y {aprobadas} de {bloqueantes} reglas bloqueantes aprobadas."
    ))
    h.append(rejilla_kpi([
        (fmt_int(T["pistas"]), "Pistas en fact_pista"),
        (fmt_mill(SILVER, 2), "Filas en Bronze y Silver"),
        (f"{COMP['segundos']} s", "Pipeline completo"),
        (f"{aprobadas}/{bloqueantes}", "Reglas bloqueantes aprobadas"),
        (fmt_int(T["lanzamientos"]), "Lanzamientos"),
        (fmt_signo(P_L["r"]), "r 1950–2025"),
        (fmt_signo(P_R["r"]), "r 2013–2025, no significativa"),
        (str(m["cruce_digital"]), "Digital supera a óptico"),
    ]))
    h.append(P("Las cinco ideas que debe recordar", "h2"))
    h += vinetas([
        "<b>Solo una tabla estaba recortada.</b> Silver ya tenía 98,6 M de filas; el tope afectaba a track. El hecho era pequeño por su grano, no por falta de datos.",
        "<b>Python no era el problema.</b> Solo orquestaba: PostgreSQL hacía el trabajo. Decir «Python es lento» es incorrecto.",
        "<b>Spark fue una decisión del proyecto.</b> 58,8 M de filas no es un volumen extremo; un motor de un nodo como DuckDB probablemente alcanzaría. No se hizo ninguna comparación de rendimiento.",
        "<b>Los datos completos corrigieron conclusiones.</b> La caída reciente de duración ya no es significativa y el cruce digital se adelantó de 2012 a 2011.",
        "<b>Validar no basta.</b> Dos errores graves pasaron las primeras reglas porque revisaban integridad, no significado. Se hallaron inspeccionando resultados.",
    ])
    h.append(P("Cómo usar este documento", "h2"))
    h.append(tabla([
        ["Si necesita", "Vaya a"],
        ["Explicar qué se hizo y en qué orden", "Sección 3"],
        ["Mostrar arquitectura y modelo", "Secciones 4 y 5"],
        ["Justificar una tecnología", "Sección 7"],
        ["Explicar errores o demostrar calidad", "Secciones 8 y 9"],
        ["Responder preguntas difíciles", "Sección 12"],
    ], [10.0, 6.9], primera_negrita=True))

    # ------------------------------------------------------------------ 2
    seccion(h, "Sección 2", "Requisito y punto de partida")
    h.append(P("El proyecto se entregó en el segundo corte sobre PostgreSQL. El nuevo requisito pide una base de más de 50 millones de registros. Antes de elegir tecnologías se revisó qué se había hecho realmente, porque varias suposiciones iniciales no eran correctas."))
    h.append(tabla([
        ["Suposición inicial", "Lo que mostró la revisión", "Evidencia"],
        ["La base se redujo a menos de 20 M", f"Solo silver.track se limitó a {fmt_int(ANT['pistas'])} filas; las demás tablas estaban completas", f"{code('TARGET_ROWS')} en etl/silver/ingest_tracks_sliced.py"],
        ["Faltaban datos en todo el proyecto", f"Silver ya sumaba {fmt_int(ANT['silver_filas'])} filas", "Volumetría de la entrega anterior"],
        ["El hecho era pequeño por el recorte", f"Tenía {fmt_int(ANT['filas_hecho'])} filas sobre todo por su grano agregado", "Grano diario de fact_produccion_musical"],
        ["Python hacía el trabajo y era lento", "Python solo orquestaba COPY y SQL; PostgreSQL ejecutaba", "ingest_silver.py y scripts SQL"],
    ], [5.0, 7.2, 4.7]))
    h.append(aviso(
        "Las primeras 15 M líneas del archivo no eran una muestra aleatoria. Además, el corte podía dejar lanzamientos incompletos: "
        f"el lanzamiento {m['ejemplo_grano']['lanzamiento_id']} aparecía con 21 pistas y 2 soportes, y hoy tiene {m['ejemplo_grano']['pistas']} pistas y {m['ejemplo_grano']['soportes']} soportes. Esa diferencia es consistente con el corte, aunque el volcado también pudo cambiar.",
        "Por qué importaba el recorte", DURAZNO))
    h.append(P("Recursos disponibles", "h2"))
    h.append(tabla([
        ["Recurso", "Valor al iniciar", "Consecuencia"],
        ["Memoria RAM", "13,8 GB", "Muy justo para Spark local con este volumen"],
        ["Procesador", "16 hilos", "Suficiente, pero no resuelve la memoria"],
        ["Disco libre", "71 GB", "Alcanza para el dump, no para varias capas locales con holgura"],
        ["Java", "JDK 8 como predeterminado", "Spark 4 exige Java 17 " + ref(16)],
    ], [4.0, 4.4, 8.5], primera_negrita=True))
    h.append(P("Decisiones que tomó el usuario", "h2"))
    h += vinetas([
        "Usar Databricks y Spark, y trabajar en la nube en lugar de Spark local.",
        "Crear los dashboards también en Databricks.",
        "Corregir las etiquetas y las conclusiones con datos completos.",
    ])

    # ------------------------------------------------------------------ 3
    seccion(h, "Sección 3", "Cronología del proceso")
    h.append(P("El orden fue deliberado: primero comprobar el dato, después medir el riesgo y al final construir. Todo ocurrió entre el 4 y el 5 de noviembre de 2026."))
    h.append(tabla([
        ["#", "Etapa", "Qué se hizo", "Resultado"],
        ["1", "Diagnóstico", "Revisión del ETL y la volumetría anterior", "Premisas corregidas (sección 2)"],
        ["2", "Preparación", "CLI de Databricks, inicio de sesión, esquemas y Volume", "Workspace listo: landing, bronze, silver, gold, meta"],
        ["3", "Descarga", f"Volcado {m['version_volcado']} de 7,7 GB", "SHA-256 correcto"],
        ["4", "Extracción", "11 tablas, 15 GB, esquema 31", f"track con {fmt_int(T['pistas'])} líneas"],
        ["5", "Carga", "Subida al Volume con la CLI", "Falló track por el límite de 5 GiB; se dividió en 8 bloques"],
        ["6", "Capacidad", "Prueba con todas las pistas y joins", f"Hecho en {round(cap_hecho)} s; ninguna pista perdida"],
        ["7", "Conexión", "Power BI contra el warehouse con token", "12 filas cargadas: solo prueba conectividad"],
        ["8", "Pipeline", "Bronze, Silver, Gold, validación y job de Lakeflow", f"Corrida de {COMP['segundos']} s con 7 tareas, en estado {COMP['estado']}"],
        ["9", "Etiquetas", "Catálogos oficiales, tarea catalogos y reglas V08 a V11", "Claves y totales idénticos; el job pasó a 8 tareas"],
        ["10", "Dashboard", f"{len(LV['pages'])} páginas en AI/BI", "KPI conciliados con Gold"],
        ["11", "Ajustes visuales", "Filtro de año, dispersión, paleta y formato", "Revisado en el navegador"],
        ["12", "Desempate", "Regla nueva por país y validación V12", f"Corrida de {FINAL['segundos']} s; Afghanistan de {fmt_int(a['lanzamientos'])} a {fmt_int(E['afganistan_lanzamientos'])}"],
        ["13", "Publicación", "Cinco commits en GitHub", "Correo personal retirado del código"],
    ], [0.8, 3.0, 7.0, 6.1]))
    h.append(P("Prueba de capacidad", "h2"))
    h.append(P("Se hizo antes de escribir el pipeline porque era el mayor riesgo: nadie había comprobado que Free Edition soportara el join completo."))
    h.append(tabla([
        ["Etapa", "Tiempo", "Filas"],
        ["Bronze, 9 tablas", f"{round(cap_bronze)} s", fmt_int(sum(e["filas"] for k, e in cap.items() if k.startswith("bronze.")))],
        ["Hecho con todos los joins", f"{round(cap_hecho)} s", fmt_int(cap["gold.spike_fact_pista"]["filas"])],
        ["Validaciones", f"{round(cap['checks.fact']['segundos'])} s", fmt_int(cap["checks.fact"]["filas"])],
        ["Agregación por año y formato", f"{round(cap['query.year_format']['segundos'])} s", f"{fmt_int(cap['query.year_format']['filas'])} grupos"],
    ], [8.0, 3.0, 5.9], primera_negrita=True))
    h.append(aviso("Esta prueba demuestra que el trabajo termina en Free Edition. No demuestra que sea más rápido que otra opción ni dice cuánta cuota consumió.", "Qué demuestra y qué no", AZUL))

    # ------------------------------------------------------------------ 4
    seccion(h, "Sección 4", "Arquitectura")
    h.append(P("Se mantuvo la arquitectura Medallón y se agregó Bronze, que no existía. Cada capa tiene una responsabilidad única y puede reconstruirse desde la anterior."))
    h.append(KeepTogether([diagrama_arquitectura(m), P("Figura 1. Flujo de datos, orquestación y gobierno.", "caption")]))
    h.append(tabla([
        ["Capa", "Responsabilidad", "Regla principal", "Tamaño Delta"],
        ["Volume", "Archivos originales", "No se modifican", "15 GB de TSV"],
        ["Bronze", "Copia fiel", "Todo como texto; conserva escapes", "—"],
        ["Silver", "Datos utilizables", "Tipos, escapes, clave única", fmt_gb(tam_s)],
        ["Gold", "Modelo analítico", "Estrella, fila cero, aditividad", fmt_gb(tam_g)],
        ["meta", "Gobierno", "Registra cargas y reglas", "—"],
    ], [2.4, 4.6, 6.7, 3.2], primera_negrita=True))
    h.append(P("Tareas del job", "h2"))
    h.append(tabla([
        ["Archivo", "Función"],
        ["00_pruebas.py", f"{PR['pruebas_fixtures_verde']} pruebas de reglas de negocio con datos pequeños"],
        ["01_bronze.py", "Carga el volcado sin interpretar"],
        ["02_silver.py", "Aplica tipos, revierte escapes y valida claves"],
        ["02b_catalogos.py", "Carga 6 catálogos oficiales"],
        ["03_gold_dimensiones.py", "Construye 7 dimensiones con fila cero"],
        ["04_gold_fact_pista.py", "Construye el hecho a nivel de pista"],
        ["05_gold_agregados.py", "Construye hechos agregados y tablas mv_*"],
        ["06_validacion.py", "Integridad, aditividad, catálogos y reconciliación"],
    ], [5.5, 11.4], primera_negrita=True))
    h.append(Spacer(1, 6))
    h += vinetas([
        "<b>Reanudable:</b> cada etapa queda en meta.etl_audit y no se repite para la misma versión del volcado, salvo con el parámetro forzar.",
        "<b>Secuencial:</b> nunca corre más de una tarea a la vez, dentro del límite de 5 tareas concurrentes de Free Edition " + ref(1) + ".",
        "<b>Falla de forma visible:</b> si una regla bloqueante no pasa, el job termina en error.",
    ])

    # ------------------------------------------------------------------ 5
    seccion(h, "Sección 5", "Modelo de datos")
    h.append(P("Decisión de grano", "h2"))
    h.append(P(
        f"El hecho agregado nunca iba a llegar a 50 M: con todos los datos tiene {fmt_int(G['fact_produccion_musical'])} filas. Por eso se agregó <b>{code('fact_pista')}</b>, con una fila por pista, "
        "y se conservaron los agregados para que el dashboard responda rápido. Así el requisito se cumple sin importar si se interpreta sobre el origen o sobre la tabla de hechos."
    ))
    h.append(KeepTogether([diagrama_estrella(m), P("Figura 2. Hechos de Gold y dimensiones conformadas.", "caption")]))
    h.append(P("Conteos por tabla", "h2"))
    orden_s = ["track", "recording", "release_country", "artist_credit_name", "isrc", "medium", "release", "artist", "release_unknown_country", "area", "language"]
    h.append(tabla([["Tabla", "Bronze", "Silver"]] + [[t, fmt_int(B_C.get(t, 0)), fmt_int(S_C[t])] for t in orden_s] + [["Total", fmt_int(sum(B_C.values())), fmt_int(SILVER)]], [7.5, 4.7, 4.7], primera_negrita=True))
    h.append(Spacer(1, 6))
    h.append(P(f"Silver incluye además 6 catálogos oficiales de hasta {fmt_int(max(v for k, v in S_C.items() if k.startswith('catalogo_')))} filas.", "body_muted"))
    orden_g = ["fact_pista", "fact_produccion_musical", "fact_distribucion_duracion", "dim_artista", "dim_geografia", "dim_fecha", "dim_idioma", "dim_lanzamiento", "dim_formato", "dim_rango_duracion", "mv_analitica_artistas", "mv_distribucion_geografica", "mv_evolucion_formatos", "mv_tendencias_produccion_anual"]
    d = m["detalle"]["gold"]
    h.append(KeepTogether([tabla([["Tabla Gold", "Filas", "Tamaño", "Clustering"]] + [[t, fmt_int(G[t]), fmt_gb(d[t]["bytes"]), d[t]["clustering"].strip("[]").replace('"', "").replace(",", ", ") or "—"] for t in orden_g], [6.6, 2.8, 2.2, 5.3], primera_negrita=True)]))
    h.append(P("Reglas de negocio del modelo", "h2"))
    h.append(tabla([
        ["Regla", "Definición"],
        ["Fecha", "La más antigua del lanzamiento, con prioridad para eventos con país. Años válidos de 1900 a 2030; si no, clave 0."],
        ["Territorio", "País único se conserva. [Worldwide] gana si está entre los empatados. Con 10 o más países, [Worldwide]. Con 2 a 9, el país con más lanzamientos."],
        ["Artista", "El primero del crédito de la pista, o el del lanzamiento. Un artist_credit nunca se usa como artist.id."],
        ["Duración", "La de la pista; si falta, la de la grabación."],
        ["Primeras pistas", "Cada lanzamiento, soporte y grabación suma una vez, en su primera pista."],
        ["Fila cero", "Todo valor faltante apunta a la clave 0: ninguna fila del hecho se pierde."],
    ], [3.2, 13.7], primera_negrita=True))
    h.append(Spacer(1, 9))
    h.append(tabla([
        ["Camino del territorio", "Lanzamientos"],
        ["País único", fmt_int(cam["pais_unico"])],
        ["Sin país (release_unknown_country)", fmt_int(cam["sin_pais"])],
        ["10 o más países: [Worldwide]", fmt_int(cam["diez_o_mas"])],
        ["2 a 9 países: mayor catálogo", fmt_int(cam["dos_a_nueve"])],
        ["[Worldwide] explícito en el empate", fmt_int(cam["worldwide_explicito"])],
    ], [11.0, 5.9], primera_negrita=True))

    # ------------------------------------------------------------------ 6
    seccion(h, "Sección 6", "Reglas de calidad")
    h.append(P(f"Hay {bloqueantes} reglas bloqueantes y {info} indicadores informativos en {code('meta.data_quality_log')}. Las bloqueantes detienen el job; las informativas muestran cuánto dato incompleto existe."))
    h.append(tabla([
        ["Grupo", "Reglas", "Qué comprueba", "Tipo"],
        ["S01", grupos["S01"], "Sin pérdidas al convertir tipos en Silver", "Bloqueante"],
        ["S02", grupos["S02"], "Clave primaria única en Silver", "Bloqueante"],
        ["V01", grupos["V01"], "Bronze y Silver coinciden con el volcado", "Bloqueante"],
        ["V02", grupos["V02"], "Sin huérfanos entre tablas de Silver", "Bloqueante"],
        ["V03", grupos["V03"], "Dimensiones con clave única y fila cero", "Bloqueante"],
        ["V04", grupos["V04"], "Sin huérfanos en los hechos", "Bloqueante"],
        ["V05", grupos["V05"], "Métricas aditivas", "Bloqueante"],
        ["V06", grupos["V06"], "Agregados reconcilian con el detalle", "Bloqueante"],
        ["V07", grupos["V07"], "Sin medidas negativas", "Bloqueante"],
        ["V08", grupos["V08"], "Etiquetas iguales al catálogo oficial", "Bloqueante"],
        ["V09", grupos["V09"], "Todos los ID existen en el catálogo", "Bloqueante"],
        ["V10", grupos["V10"], "Las traducciones usan nombres oficiales", "Bloqueante"],
        ["V11", grupos["V11"], "Catálogo completo", "Bloqueante"],
        ["V12", grupos["V12"], "Empates multiterritoriales en [Worldwide]", "Bloqueante"],
        ["I01–I06", info, "Pistas sin fecha, artista o geografía; bisiestos; BOM; caminos del territorio", "Informativo"],
    ], [2.0, 1.6, 10.6, 2.7], primera_negrita=True))
    h.append(Spacer(1, 5))
    h.append(P(f"Datos incompletos conocidos: {fmt_int(E['pistas_sin_fecha'])} pistas sin fecha, {fmt_int(E['pistas_sin_geografia'])} sin geografía y {fmt_int(E['pistas_fecha_futura'])} con años posteriores a 2026.", "body_muted"))
    h.append(P("Reglas EDA heredadas", "h2"))
    h.append(tabla([
        ["Regla", "Tema", "En Databricks"],
        ["E01", "Duraciones nulas o en cero", "Respaldo con la duración de la grabación"],
        ["E02", "Fechas parciales o ausentes", "Sin imputar: si no hay fecha, clave 0"],
        ["E03", "Créditos de artista", "Posición 0 de artist_credit_name"],
        ["E04", "ISRC múltiples", "Grabaciones deduplicadas antes del join"],
        ["E05", "Booleanos en hechos", "Banderas en fact_pista; sumas en los agregados"],
        ["E06", "Textos extensos", "STRING de Spark, sin truncar"],
        ["E07", "Claves huérfanas", "Fila cero y regla V04"],
        ["E08", "Codificación y BOM", "Indicador I05: 1 nombre con BOM"],
        ["E09", "Cruce geográfico", "Unión por identificador entero"],
        ["E10", "Registro de auditoría", "meta.data_quality_log"],
    ], [1.8, 6.0, 9.1], primera_negrita=True))

    # ------------------------------------------------------------------ 7
    seccion(h, "Sección 7", "Decisiones de tecnología")
    h.append(P(
        "Cada registro explica qué se eligió, por qué, qué se descartó y qué costó. La fila <b>Base</b> distingue lo <b>medido en este proyecto</b> de lo que viene de <b>documentación</b> y de lo que es <b>criterio</b>."
    ))
    h.append(aviso(
        "<b>No se ejecutó ningún benchmark comparativo.</b> PostgreSQL y Spark no se midieron con los mismos datos. 58,8 M de filas no es un volumen extremo, y un motor de un nodo como DuckDB probablemente podría con él. "
        "Las comparaciones siguientes son cualitativas, basadas en documentación y en las condiciones del proyecto. Las condiciones comerciales cambian: se consultaron el 5 de noviembre de 2026.",
        "Límite de esta comparación", DURAZNO))
    h += decision(1, "Plataforma", "Databricks con Apache Spark",
                  "Es la plataforma solicitada para el proyecto. Da Spark administrado, almacenamiento Delta, catálogo, orquestación y dashboards en un solo lugar, sin operar infraestructura.",
                  [
                      ["PostgreSQL local", "Ya existía y sigue siendo válido para este tamaño. Se descartó porque el proyecto buscaba procesamiento distribuido y por el disco disponible."],
                      ["Spark local", "13,8 GB de RAM y JDK 8. Spark 4 exige Java 17 " + ref(16) + "; además, un solo equipo no muestra procesamiento distribuido."],
                      ["DuckDB", "Probablemente resolvería la carga en un nodo, con procesamiento mayor que la memoria y límites conocidos " + ref(11) + ". No cumple el objetivo de usar Spark."],
                      ["Snowflake", "Prueba limitada a 30 días o 400 USD " + ref(13) + ". Es un almacén SQL; no era el objetivo de Spark."],
                      ["BigQuery", "El sandbox da 10 GB de almacenamiento y las tablas expiran " + ref(12) + "; los 15 GB de archivos superan ese margen."],
                      ["Amazon Redshift", "Crédito de 300 USD por 90 días " + ref(14) + "; exige una cuenta de AWS y no usa Spark como motor."],
                      ["Microsoft Fabric", "Prueba de 60 días " + ref(15) + ". Es viable, pero no era la plataforma pedida y la prueba caduca."],
                      ["Hadoop y Hive", "Exigen operar un clúster y su enfoque por lotes es más pesado " + ref(17) + ". Sin ventaja para este caso."],
                  ],
                  "Dependencia de una plataforma de terceros y curva de aprendizaje. El dashboard y la orquestación no se trasladan directamente a otra herramienta.",
                  f"<b>Medido:</b> la carga completa termina en {COMP['segundos']} s. <b>Criterio:</b> elección de plataforma. <b>Documentación:</b> condiciones de alternativas.")
    h += decision(2, "Plan de Databricks", "Free Edition",
                  "No tiene costo y alcanza para el proyecto: se comprobó con la prueba de capacidad y con el pipeline completo.",
                  [["Plan pago o prueba", "No fue necesario. Quedaba como respaldo si la cuota no alcanzaba."]],
                  "Solo cómputo serverless, un warehouse 2X-Small, cuota diaria que puede apagar el cómputo, sin SLA y sin uso comercial " + ref(1) + ". La cuota consumida es desconocida.",
                  "<b>Medido:</b> todas las corridas terminaron. <b>Sin medir:</b> cuota usada. <b>Documentación:</b> límites del plan.")
    h += decision(3, "Lenguaje", "PySpark para el pipeline y Spark SQL para consultas",
                  "Reutiliza la lógica SQL existente, permite probar funciones con datos pequeños y es el lenguaje disponible en este entorno.",
                  [
                      ["Scala", "No está soportado en Free Edition ni en serverless " + ref(1, 2) + "."],
                      ["pandas", "Trabaja en la memoria de un solo proceso; no es adecuado para 58,8 M de filas con varios joins."],
                  ],
                  "Hay que respetar restricciones de serverless: sin caché de DataFrame y con configuración de Spark limitada " + ref(2) + ".",
                  "<b>Documentación:</b> soporte de lenguajes. <b>Criterio:</b> reutilizar SQL.")
    h += decision(4, "Formato de tablas", "Delta Lake",
                  "Las tablas administradas de Unity Catalog usan Delta por defecto " + ref(4) + ". Aporta transacciones e historial. El historial se usó para comparar versiones y probar que las claves no cambiaron al corregir etiquetas.",
                  [
                      ["Parquet sin Delta", "Sin transacciones ni historial; una escritura fallida podría dejar datos a medias."],
                      ["Apache Iceberg", "Es abierto y está soportado " + ref(4) + ", y UniForm permite leer Delta como Iceberg " + ref(10) + ". No había otro motor que justificara el cambio."],
                      ["Apache Hudi", "Orientado a actualizaciones incrementales, que este proyecto no necesita: cada carga es un volcado completo."],
                  ],
                  "Las tablas se leen mejor dentro de herramientas compatibles con Delta.",
                  "<b>Medido:</b> comparación por <i>time travel</i> sin diferencias en claves. <b>Documentación:</b> soporte de formatos.")
    h += decision(5, "Archivos crudos", "Volume administrado de Unity Catalog",
                  "Gobierna archivos igual que tablas. Databricks marca como obsoletos DBFS root y los montajes, y recomienda volúmenes " + ref(3) + ".",
                  [
                      ["DBFS root o montajes", "Obsoletos y no recomendados " + ref(3) + "."],
                      ["Almacenamiento externo propio", "Exige una cuenta de nube y credenciales; Free Edition no admite ubicaciones personalizadas " + ref(1) + "."],
                  ],
                  "Cada archivo subido por la CLI tuvo un tope de 5 GiB, y por eso track se dividió.",
                  "<b>Medido:</b> error real de la CLI. <b>Documentación:</b> recomendación oficial.")
    h += decision(6, "Orquestación", "Lakeflow Jobs",
                  "Encadena tareas con dependencias, registra cada corrida y permite ejecutar solo una parte. Los Jobs son procedimentales, lo que encaja con notebooks y pruebas " + ref(6) + ".",
                  [
                      ["Apache Airflow", "Requiere instalar y mantener otro servicio, sin beneficio para un flujo lineal."],
                      ["Declarative Pipelines", "Definen transformaciones de forma declarativa " + ref(6) + ". Exigían reescribir la lógica y Free Edition limita los pipelines activos " + ref(1) + "."],
                      ["Script en Python", "Era la opción anterior: sin dependencias administradas ni historial de corridas."],
                  ],
                  "La definición del job es específica de Databricks.",
                  f"<b>Medido:</b> corridas {COMP['run_id']} y {FINAL['run_id']} en SUCCESS. <b>Documentación:</b> diferencia entre Jobs y pipelines.")
    h += decision(7, "Organización física", "Liquid clustering y tablas agregadas",
                  "Databricks lo presenta como reemplazo de particiones y ZORDER " + ref(5) + ". Evita fijar particiones sobre datos desiguales: la producción se concentra en las décadas recientes y 7,6 % de las pistas no tiene fecha.",
                  [
                      ["Particiones por rango", "Era el diseño en PostgreSQL. En Delta exige una elección fija y puede crear demasiados archivos pequeños."],
                      ["ZORDER", "Requiere reoptimizar manualmente y Databricks recomienda liquid clustering " + ref(5) + "."],
                  ],
                  "<b>Su beneficio no se midió.</b> No se comparó contra una tabla sin clustering; los tiempos actuales no se le pueden atribuir.",
                  f"<b>Medido:</b> consultas de {fmt_dec(PR['almacen']['consulta_min_s'], 1)} a {fmt_dec(PR['almacen']['consulta_max_s'], 1)} s en 2X-Small, sin comparación. <b>Documentación:</b> recomendación oficial.")
    h += decision(8, "Cómputo", "Serverless",
                  "Es el único tipo disponible en Free Edition " + ref(1) + ". Arranca sin configurar clústeres.",
                  [["Clústeres clásicos", "No están disponibles en este plan."]],
                  "Sin Spark UI, caché de DataFrame ni la mayoría de configuraciones " + ref(2) + ". Se usa el perfil de consultas para diagnosticar.",
                  "<b>Documentación:</b> limitaciones de serverless.")
    h += decision(9, "Visualización", "Dashboard AI/BI como único dashboard vigente",
                  f"AI/BI corre sobre el warehouse y evita importar {fmt_mill(G['fact_produccion_musical'])} de filas a un equipo con 13,8 GB de RAM. Con el dashboard ya publicado y conciliado, mantener otro reporte no aportaba a esta entrega.",
                  [
                      ["Reconectar Power BI", "Riesgo de memoria sin comprobar: la conexión solo se probó con 12 filas. Se decidió no continuar."],
                      ["Mantener ambos", "Dos herramientas que mantener y dos versiones de las mismas cifras."],
                  ],
                  "El drill-down funciona dentro de tablas dinámicas, no en los gráficos, y llega a mes. Top N no se recalcula con filtros.",
                  "<b>Medido:</b> filtros iguales a SQL. <b>Sin medir:</b> Power BI con 11,5 M de filas, porque no se continuó por esa vía.")
    h += decision(10, "Cálculo de primeras pistas", f"{code('min(struct(...))')} con agregación",
                  "Encuentra la primera pista por lanzamiento, soporte y grabación sin ordenar particiones completas, como hacen las funciones de ventana.",
                  [[code("ROW_NUMBER"), "Es más directo y era la lógica anterior, pero requiere tres ordenamientos sobre 58,8 M de filas."]],
                  "Es menos evidente al leerlo. Una prueba con datos pequeños documenta el comportamiento.",
                  "<b>Criterio técnico:</b> no se midió contra ROW_NUMBER. <b>Medido:</b> la aditividad coincide.")
    h += decision(11, "Carga de archivos", "CLI y división de track en bloques de 1 GB",
                  "Automatizable y repetible. Dividir por líneas evita cortar registros, y Spark lee la carpeta como una tabla.",
                  [
                      ["Interfaz web", "Límite de 5 GB por archivo " + ref(7) + " y sin repetibilidad."],
                      ["SDK o API", "Podría evitar el límite " + ref(7) + ", pero requería más código para una carga única."],
                      ["Comprimir con gzip", "No se puede dividir para procesar en paralelo."],
                  ],
                  "La suposición inicial de que la CLI admitía más de 5 GB fue incorrecta y costó una subida fallida.",
                  f"<b>Medido:</b> 8 bloques con los mismos bytes y {fmt_int(T['pistas'])} líneas.")
    h += decision(12, "Etiquetas de dimensiones", "Catálogos oficiales del volcado",
                  "Traducir por nombre oficial evita errores por ID. Las reglas V08 a V11 bloquean diferencias.",
                  [["Mapas por ID en el código", "Fue la causa del error: 76.524 ciudades aparecían como Condado."]],
                  f"La calidad no tiene catálogo en el volcado: sus nombres y la asignación de categorías de formato son criterio propio. {fmt_int(sin_cal)} lanzamientos quedan «Sin calificar».",
                  "<b>Medido:</b> la regla falló contra las dimensiones viejas y pasó contra las nuevas.")

    # ------------------------------------------------------------------ 8
    seccion(h, "Sección 8", "Errores encontrados y correcciones")
    h.append(P("Documentar los errores es parte de la defensa: muestra cómo se verificó el resultado. La columna <b>Detección</b> es la más importante."))
    h.append(tabla([
        ["Error", "Impacto", "Corrección", "Detección"],
        ["Conteos no aditivos (entrega anterior)", "KPI principal inflado", "Asignación a la primera pista", "Conciliación"],
        ["Orden de columnas de medium", "edits_pending y track_count invertidos en el DDL anterior", "Orden real del volcado", "Inspección de archivos"],
        ["Etiquetas contra catálogos", f"{fmt_int(sin_cal)} lanzamientos como «Baja»; 81.904 áreas mal rotuladas", "Catálogos oficiales y reglas V08 a V11", "<b>Inspección</b>; pasó la primera validación"],
        ["Desempate por menor ID (Afghanistan)", f"{fmt_int(a['lanzamientos'])} lanzamientos asignados a Afghanistan", "Regla nueva y V12", "<b>Inspección</b>; pasó la primera validación"],
        ["Límite de 5 GiB", "track no subió", "8 bloques de 1 GB", "Error de la CLI"],
        ["Falso positivo en V12.grano", "Marcó 51.729 casos válidos", "Regla acotada a eventos con país", "Corrida en rojo"],
        ["Año 0 en el filtro", "El rango empezaba en 0", "Filtro limitado a años reales", "Revisión del usuario"],
        ["Gráfico de dispersión", "No cargaba", "Cálculo en un dataset propio", "Revisión del usuario"],
        ["Versión de tabla inválida", "Widget con error", "Se restauró la versión 2", "Revisión en el navegador"],
        ["Caché del dashboard", "Mostraba datos anteriores a la corrección", "Actualización forzada", "Revisión en el navegador"],
    ], [4.4, 5.1, 3.9, 3.5], primera_negrita=True))
    h.append(aviso(
        f"Afghanistan tiene el ID de área 1. En un empate de fecha, {code('min(struct(...))')} terminaba comparando el ID de país y ganaba el menor. Por eso reunía {fmt_int(a['lanzamientos'])} lanzamientos de {fmt_int(a['artistas'])} artistas, y solo 32 lanzamientos eran de artistas de ese país. "
        f"Tras la corrección quedó en {fmt_int(E['afganistan_lanzamientos'])}. Se movieron {fmt_int(PR['pistas_movidas_area'])} pistas de área y ninguna cambió de fecha.",
        "Por qué pasó la primera validación", AZUL))
    h.append(P("Lección", "h2"))
    h.append(P("Las reglas iniciales comprobaban integridad: claves válidas, sumas correctas. Un dato puede ser íntegro y estar mal. Después de cada hallazgo se agregó una regla bloqueante, así que esos errores ya no pueden volver sin detener el job."))

    # ------------------------------------------------------------------ 9
    seccion(h, "Sección 9", "Evidencia de validación")
    h.append(rejilla_kpi([
        (f"{PR['pruebas_fixtures_verde']}/{PR['pruebas_fixtures_verde']}", "Pruebas con datos pequeños"),
        (str(finales), "Reglas de validación final"),
        (str(silver_r), "Reglas de Silver"),
        ("2", "Filtros comparados con SQL"),
    ]))
    h.append(P("Pruebas", "h2"))
    h.append(P("Corren dentro de Databricks con datos pequeños, porque el entorno local no tiene PySpark. Cada grupo se vio fallar primero y después pasar. Son la primera tarea del job: si fallan, no se procesa nada."))
    h.append(P("Reconciliación", "h2"))
    h.append(tabla([
        ["Comprobación", "Valor", "Resultado"],
        ["Pistas: volcado = Bronze = Silver = fact_pista", fmt_int(T["pistas"]), "Coincide"],
        ["Lanzamientos: suma = conteo distinto", fmt_int(T["lanzamientos"]), "Coincide"],
        ["Soportes: suma = conteo distinto", fmt_int(T["soportes"]), "Coincide"],
        ["Grabaciones: suma = conteo distinto", fmt_int(T["grabaciones"]), "Coincide"],
        ["Pistas con duración: distribución = agregado", fmt_int(H["total"]), "Coincide"],
    ], [10.0, 3.9, 3.0], primera_negrita=True))
    h.append(P("Corridas", "h2"))
    h.append(figura(g_tareas(m, [("pruebas", "Pruebas"), ("bronze", "Bronze"), ("silver", "Silver"), ("gold_dimensiones", "Dimensiones"), ("gold_fact_pista", "Hecho de pista"), ("gold_agregados", "Agregados"), ("validacion", "Validación")]), 14.0, f"Figura 3. Tareas de la corrida completa {COMP['run_id']}."))
    h.append(tabla([
        ["Corrida", "Alcance", "Duración", "Estado"],
        [COMP["run_id"], "Pipeline completo; Bronze reutilizó 9 tablas de la prueba", f"{COMP['segundos']} s", COMP["estado"]],
        ["360438219893932", "Dimensiones, agregados y validación tras corregir etiquetas", "262 s", "SUCCESS"],
        [FINAL["run_id"], "Pruebas, hecho, agregados y validación tras el desempate", f"{FINAL['segundos']} s", FINAL["estado"]],
    ], [4.2, 8.2, 2.2, 2.3], primera_negrita=True))
    h.append(P("Filtros del dashboard contra SQL", "h2"))
    h.append(tabla([
        ["Filtro", "Lanzamientos o razón", "Pistas o duración", "Tercer valor", "Coincidencia"],
        [f"Año {fil['anio']['rango']}", fmt_int(fil["anio"]["lanzamientos"]), fmt_int(fil["anio"]["pistas"]), f"{fmt_int(fil['anio']['artistas'])} artistas", "Exacta"],
        [f"Década {fil['decada']['valor']}", f"{fil['decada']['pistas_por_lanzamiento']} pistas por lanzamiento", f"{fil['decada']['duracion_min']} min", f"{fil['decada']['horas']} horas", "Exacta"],
    ], [3.3, 4.2, 3.2, 3.5, 2.7], primera_negrita=True))
    h.append(P("Se probaron estos dos filtros; los demás filtros de lista usan el mismo control, pero no se probaron uno por uno.", "body_muted"))

    # ------------------------------------------------------------------ 10
    seccion(h, "Sección 10", "Resultados")
    h.append(tabla([
        ["Métrica", "Carga de 15 M", "Volcado completo"],
        ["Pistas", fmt_int(ANT["pistas"]), fmt_int(T["pistas"])],
        ["Lanzamientos", fmt_int(ANT["lanzamientos"]), fmt_int(T["lanzamientos"])],
        ["Soportes", fmt_int(ANT["soportes"]), fmt_int(T["soportes"])],
        ["Filas del hecho agregado", fmt_int(ANT["filas_hecho"]), fmt_int(G["fact_produccion_musical"])],
        ["r año-duración 1950–2025", fmt_signo(ANT["r_1950_2025"], 2), fmt_signo(P_L["r"])],
        ["r año-duración 2013–2025", fmt_signo(ANT["r_2013_2025"], 2), fmt_signo(P_R["r"])],
        ["Digital supera a óptico", str(ANT["cruce_digital"]), str(m["cruce_digital"])],
    ], [8.5, 4.2, 4.2], primera_negrita=True))
    h.append(Spacer(1, 6))
    h.append(figura(g_cuota(m), 14.6, f"Figura 4. Digital supera a óptico en {m['cruce_digital']}."))
    h += vinetas([
        f"<b>Formatos:</b> en 2025, digital {fmt_pct(m['ultimo_anio']['digital'])} y óptico {fmt_pct(m['ultimo_anio']['optico'])} de los lanzamientos con fecha.",
        f"<b>Duración:</b> media de {fmt_mmss(H['media_min'])}; las bandas de 3:00 a 4:00 reúnen {fmt_pct(H['dos_mayores_pct'])} de las pistas.",
        f"<b>RF05:</b> r = {fmt_signo(P_L['r'])} (1950–2025), {fmt_signo(P_90['r'])} (1990–2025) y {fmt_signo(P_R['r'])} (2013–2025). El último valor, con n = {P_R['n']}, no supera el valor crítico de 0,553.",
        f"<b>ISRC:</b> {fmt_pct(T['isrc_pct'])} de las pistas en este catálogo.",
        f"<b>Territorio:</b> [Worldwide] reúne {fmt_int(E['lanzamientos_worldwide'])} lanzamientos; el primer país, {m['paises'][0]['pais']}, {fmt_int(m['paises'][0]['lanzamientos'])}.",
    ])

    # ------------------------------------------------------------------ 11
    seccion(h, "Sección 11", "Limitaciones conocidas")
    h.append(tabla([
        ["Tema", "Limitación", "Impacto"],
        ["Dashboard", "Drill-down en tablas dinámicas, hasta mes y no hasta día", "RF03 queda cubierto sin el nivel día"],
        ["Dashboard", "Clic para filtrar solo entre gráficos del mismo dataset", "Otros datasets no reaccionan"],
        ["Modelo", "Las ciudades no están enlazadas con su país", "El drill geográfico tiene poca profundidad"],
        ["Dashboard", "Top N no se recalcula con filtros", "Los rankings no cambian de integrantes al filtrar"],
        ["Dashboard", "Tablas sin separador de miles", "Solo visual; se probaron tres formatos"],
        ["Dashboard", "Tintes de Mezcla de formatos fuera del umbral de la paleta", "Se distinguen por leyenda y posición"],
        ["Datos", "Fechas anteriores a 1900 pasan a «sin fecha»", "1.266 registros de país, incluido un año 206"],
        ["Datos", f"{fmt_int(E['pistas_fecha_futura'])} pistas con años posteriores a 2026", "Las series terminan en 2025"],
        ["Datos", "Nombres de calidad según conocimiento de MusicBrainz", "El volcado no los trae como catálogo"],
        ["Datos", "Categoría de formato según criterio propio", "Afecta la lectura de digital frente a físico"],
        ["Datos", "Fila 0 de dim_lanzamiento con 770 lanzamientos reales", "No es un desconocido puro"],
        ["Datos", "Regla de 10 países definida por el proyecto", "Otro umbral movería lanzamientos"],
        ["Power BI", "El reporte queda con la carga de 15 M de la entrega anterior", "Sus cifras no son las vigentes; el dashboard oficial es AI/BI"],
        ["Rendimiento", "Sin comparación entre motores", "No se puede afirmar que Spark sea más rápido aquí"],
        ["Rendimiento", "Beneficio del liquid clustering sin medir", "No se le pueden atribuir los tiempos"],
        ["Rendimiento", "Cuota de Free Edition desconocida", "Una corrida futura podría interrumpirse"],
        ["Rendimiento", "Varios usuarios sin probar", "El warehouse es 2X-Small"],
    ], [2.6, 8.0, 6.3], primera_negrita=True))

    # ------------------------------------------------------------------ 12
    seccion(h, "Sección 12", "Guía de defensa")
    h.append(P("Respuestas cortas y honestas. Si no conoce un dato, diga qué se midió y qué no: es mejor que improvisar."))
    bloques = [
        ("Preguntas difíciles", [
            ("¿Por qué Spark si 58 M de filas caben en una sola máquina?", "Porque el objetivo del proyecto era trabajar con procesamiento distribuido y arquitectura lakehouse. Es cierto que un motor de un nodo como DuckDB probablemente alcanzaría. Spark no se eligió por necesidad de volumen."),
            ("¿Por qué no hicieron un benchmark real?", "Porque la prioridad fue cumplir el requisito y validar los datos. Solo medimos que el proceso termina y cuánto tarda. No afirmamos que Spark sea más rápido que PostgreSQL. Es trabajo futuro."),
            ("¿Por qué ya no usan Power BI?", f"AI/BI corre en la nube y evita importar {fmt_mill(G['fact_produccion_musical'])} de filas a un equipo limitado. El drill-down se conserva con tablas dinámicas, y un clic en una barra filtra los gráficos del mismo dataset. El reporte de Power BI queda como parte de la entrega anterior."),
            ("Si Python no era lento, ¿qué ganaron?", "Dejamos un motor de un nodo con disco limitado y pasamos a uno distribuido administrado, con historial, catálogo y orquestación. La ganancia demostrada es funcional, no de velocidad comparada."),
            ("¿Cuánto cuesta esto en producción?", "No lo sabemos. Free Edition no sirve para uso comercial y no medimos la cuota consumida."),
            ("¿Sus reglas garantizan que los datos están bien?", "No. Garantizan lo que comprueban. Dos errores pasaron las primeras reglas; por eso también revisamos resultados."),
        ]),
        ("Modelo y datos", [
            ("¿Dónde están los 50 M de registros?", f"En {fmt_int(G['fact_pista'])} filas de fact_pista, y {fmt_int(SILVER)} filas en Silver."),
            ("¿Por qué conservar hechos agregados?", "Porque el dashboard no necesita detalle por pista y responde más rápido con menos filas."),
            ("¿Cómo evitan el doble conteo?", f"Cada lanzamiento suma solo en su primera pista. La suma da {fmt_int(T['lanzamientos'])}, igual al conteo distinto."),
            ("¿Por qué 5.890.921 y no 5.903.902 lanzamientos?", f"Porque {fmt_int(S_C['release'] - T['lanzamientos'])} lanzamientos no tienen pistas en el volcado."),
            ("¿Por qué hay tantos lanzamientos «Sin calificar»?", "Porque −1 es el valor por defecto en MusicBrainz. No significa baja calidad."),
            ("¿Por qué [Worldwide] supera a Estados Unidos?", "Reúne lanzamientos publicados en muchos territorios. Se muestra aparte porque no es un país."),
        ]),
        ("Tecnología", [
            ("¿Qué aporta Delta sobre Parquet?", "Transacciones e historial. Usamos el historial para probar que las claves no cambiaron."),
            ("¿Qué significa serverless aquí?", "Databricks administra el cómputo: no configuramos clústeres. Es lo único disponible en Free Edition."),
            ("¿Liquid clustering mejoró el rendimiento?", "No lo sabemos: no lo comparamos contra una tabla sin clustering."),
            ("¿Por qué no Scala?", "No está soportado en Free Edition ni en serverless."),
        ]),
        ("Resultados", [
            ("¿El streaming acortó las canciones?", f"Los datos no permiten afirmarlo. Entre 2013 y 2025, r = {fmt_signo(P_R['r'])} con 13 años, no significativa, y Pearson no prueba causalidad."),
            ("¿Por qué cambiaron sus conclusiones?", "Porque la carga anterior era un subconjunto por orden de archivo. Con todos los datos corregimos lo que no se sostenía."),
            ("¿Digital superó al CD en 2011?", "Superó a la categoría óptica, que incluye CD, DVD y similares. Es más preciso decirlo así."),
        ]),
    ]
    for titulo, preguntas in bloques:
        for i, (q, r) in enumerate(preguntas):
            encabezado = [P(titulo, "h2")] if i == 0 else []
            h.append(KeepTogether(encabezado + [P(f"<b>P:</b> {q}", "h3"), P(f"<b>R:</b> {r}")]))

    # ------------------------------------------------------------------ 13
    seccion(h, "Sección 13", "Reproducción y mantenimiento")
    h.append(P("Los pasos detallados están en " + code("databricks/README.md") + ". Este es el recorrido completo."))
    h.append(tabla([
        ["#", "Paso", "Detalle"],
        ["1", "Preparar el workspace", "Crear cuenta, instalar la CLI e iniciar sesión con un perfil propio"],
        ["2", "Crear esquemas", "landing, bronze, silver, gold y meta, más el Volume mbdump"],
        ["3", "Descargar y verificar", "Volcado completo y comprobación SHA-256 " + ref(18)],
        ["4", "Subir archivos", "Dividir track en bloques y copiar con la CLI"],
        ["5", "Importar el código", "Subir databricks/pipeline al workspace"],
        ["6", "Crear el job", "Reemplazar el marcador de usuario en una copia local de job.json"],
        ["7", "Ejecutar y validar", "Correr el job y revisar meta.data_quality_log"],
        ["8", "Desplegar el dashboard", "Crear y publicar desde el archivo .lvdash.json"],
        ["9", "Actualizar el dashboard", "Forzar actualización después de reconstruir Gold"],
        ["10", "Regenerar documentos", "Ejecutar generar_metricas_databricks.py y los scripts de documentos"],
    ], [0.8, 5.0, 11.1]))
    h.append(aviso("No guarde tokens ni datos personales en el repositorio: es público. El archivo job.json usa un marcador y la copia local con su usuario no se agrega a Git.", "Seguridad", AMARILLO))
    h.append(P("Archivos principales", "h2"))
    h.append(tabla([
        ["Ruta", "Contenido"],
        ["databricks/pipeline/", "Pipeline, pruebas, validación y definición del job"],
        ["databricks/dashboards/", "Definición del dashboard AI/BI"],
        ["databricks/spikes/", "Prueba de capacidad descartable"],
        ["etl/, sql/, powerbi/", "Entrega anterior sobre PostgreSQL"],
        ["scripts/generar_metricas_databricks.py", "Consulta cifras y genera docs/build/metricas_databricks.json"],
        ["scripts/build_*.py y build_sustentacion_v4.js", "Generan la presentación y los PDF"],
    ], [7.5, 9.4], primera_negrita=True))

    # ------------------------------------------------------------------ 14
    seccion(h, "Sección 14", "Referencias")
    h.append(P("Consultadas el 5 de noviembre de 2026. Las condiciones de pruebas y planes pueden cambiar. La referencia 17 es una fuente secundaria."))
    for i, (texto, url) in enumerate(REFERENCIAS, 1):
        h.append(P(f"[{i}] {texto} <font color='#3B6FB0'><link href='{url}'>{url}</link></font>", "body_muted"))
    return h


def main():
    salida = Path(sys.argv[1]) if len(sys.argv) > 1 else SALIDA
    m = metricas()
    portada = portada_factory(
        ["Documentación técnica", "de DWMusicBrainz"],
        ["Qué se hizo, con qué tecnologías y por qué", f"Migración a Databricks con {fmt_int(m['totales']['pistas'])} pistas"],
        ["Juan Sebastián Rincón Farelo", "Integrantes: Juan Rincón, Sebastián Russo, Jesús Figueroa", "Docente: Amilkar Sierra Romano",
         "Ingeniería de Sistemas · Universidad Popular del Cesar", "Valledupar, noviembre de 2026"],
    )
    doc = Documento(salida, "DWMusicBrainz · Documentación técnica", portada, title="DWMusicBrainz · Documentación técnica",
                    author="Juan Sebastián Rincón Farelo", subject="Migración del Data Warehouse a Databricks")
    doc.multiBuild([Spacer(1, 1)] + historia(m))
    print(f"[OK] {salida}")


if __name__ == "__main__":
    main()
