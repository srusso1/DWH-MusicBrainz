"""
build_defensa_databricks_pdf.py
===============================
Genera la defensa de la capa Gold y del dashboard sobre Databricks. Todas las cifras
salen de docs/build/metricas_databricks.json.

Uso:
    python scripts/build_defensa_databricks_pdf.py [ruta_salida.pdf]
"""

import sys
from pathlib import Path

from reportlab.lib.units import cm
from reportlab.platypus import KeepTogether, NextPageTemplate, PageBreak, Spacer

from doc_pdf_comun import (
    AZUL, BASE_DIR, BUILD, DURAZNO, LAVANDA, MENTA, Documento, P, S, aviso, code, dashboard, diagrama_estrella, figura,
    fmt_dec, fmt_gb, fmt_int, fmt_mill, fmt_mmss, fmt_pct, fmt_signo, g_cuota, g_dispersion, g_histograma, g_mezcla,
    g_paises, indice, metricas, portada_factory, rejilla_kpi, seccion, tabla, vinetas,
)

SALIDA = BASE_DIR / "docs" / "Defensa_Capa_Gold_y_Dashboard_v2.pdf"


def pearson_dispersion(m):
    import math

    x = [math.log10(p["lanzamientos"]) for p in m["paises"]]
    y = [p["digital"] for p in m["paises"]]
    mx, my = sum(x) / len(x), sum(y) / len(y)
    num = sum((a - mx) * (b - my) for a, b in zip(x, y))
    den = math.sqrt(sum((a - mx) ** 2 for a in x) * sum((b - my) ** 2 for b in y))
    return num / den


# Valores críticos de |r| al 5 % (dos colas) para los tamaños de muestra usados.
R_CRITICO = {76: 0.226, 36: 0.329, 13: 0.553}


def lectura_r(p):
    signo = "positiva" if p["r"] > 0 else "negativa"
    if abs(p["r"]) < R_CRITICO[p["n"]]:
        return f"{signo.capitalize()}, no significativa al 5 %"
    return f"Fuerte y {signo}, significativa al 5 %"


def historia(m):
    T, G, H, E = m["totales"], m["conteos"]["gold"], m["histograma"], m["especiales"]
    P_L, P_90, P_R = m["pearson"]
    ult = m["ultimo_anio"]
    LV = dashboard()
    widgets = sum(len(p["layout"]) for p in LV["pages"])
    corea = next(p for p in m["paises"] if p["pais"] == "South Korea")
    r_disp = pearson_dispersion(m)
    dig_total = next(f for f in m["formatos"] if f["categoria"] == "Digital / Streaming")["lanzamientos"] / T["lanzamientos"]
    reglas = sum(r["reglas"] for r in m["calidad_log"] if r["severidad"] == "ERROR")
    reglas_ok = sum(r["reglas"] for r in m["calidad_log"] if r["severidad"] == "ERROR" and r["estado"] == "PASS")
    finales = sum(r["reglas"] for r in m["reglas_grupos"] if r["grupo"].startswith("V"))
    silver_r = sum(r["reglas"] for r in m["reglas_grupos"] if r["grupo"].startswith("S"))
    sin_calificar = next(c for c in m["calidad"] if c["calidad"] == "Sin calificar")["lanzamientos"]

    h = [NextPageTemplate("normal"), PageBreak()]
    h.append(P("Índice", "h1_indice"))
    h.append(Spacer(1, 8))
    h.append(indice())

    seccion(h, "Sección 1", "Resumen ejecutivo")
    h.append(P(
        "La capa <b>Gold</b> de DWMusicBrainz sobre <b>Databricks</b> transforma el modelo normalizado de Silver en un "
        "<b>modelo dimensional en estrella</b>, ahora con el volcado completo de MusicBrainz. Encima se construyó un "
        f"<b>dashboard AI/BI de {len(LV['pages'])} páginas</b>. Esta defensa reemplaza a la de la entrega con 15 M de pistas: "
        "las cifras y varias conclusiones cambiaron."
    ))
    h.append(rejilla_kpi([
        (fmt_int(T["lanzamientos"]), "Lanzamientos únicos"),
        (fmt_int(T["pistas"]), "Pistas analizadas"),
        (fmt_int(T["artistas"]), "Artistas activos"),
        (fmt_pct(T["isrc_pct"]), "Cobertura ISRC"),
        (fmt_pct(dig_total), "Participación digital histórica"),
        (fmt_mmss(T["dur_media_min"]), "Duración media (m:ss)"),
        (fmt_dec(T["pistas_por_lanzamiento"], 1), "Pistas por lanzamiento"),
        (fmt_int(T["horas"]), "Horas de audio catalogadas"),
    ]))
    h.append(P("Hallazgos principales", "h2"))
    h += vinetas([
        f"<b>Transición de formato:</b> digital superó a <b>óptico</b> en <b>{m['cruce_digital']}</b>. En 2025 digital representa {fmt_pct(ult['digital'])} "
        f"de los lanzamientos con fecha y óptico {fmt_pct(ult['optico'])}. Óptico incluye CD, DVD y formatos similares; por eso no se habla solo de CD.",
        f"<b>Duración:</b> entre 1950 y 2025 la duración media crece con el año (r = {fmt_signo(P_L['r'])}). Entre {P_R['inicio']} y {P_R['fin']} el signo se invierte, "
        f"pero la evidencia es débil: la relación no es significativa (r = {fmt_signo(P_R['r'])}, n = {P_R['n']}). La tesis de «canciones más cortas por el streaming» no queda demostrada.",
        f"<b>Distribución:</b> la moda está en {H['moda_banda']} ({fmt_pct(H['moda_pct'])}) y la mediana en {H['mediana_banda']}. La media es {fmt_mmss(H['media_min'])}, con cola larga a la derecha.",
        f"<b>Volumen y digitalización:</b> en el Top 30 de países no hay relación clara entre ambos (r = {fmt_signo(r_disp, 2)} con el logaritmo del volumen). "
        f"Corea del Sur llega a {fmt_pct(corea['digital'])} con {fmt_int(corea['lanzamientos'])} lanzamientos.",
        f"<b>Gobierno del dato:</b> {reglas_ok} de {reglas} reglas bloqueantes aprobadas. Aun así, dos errores graves pasaron las primeras validaciones y se detectaron inspeccionando resultados (sección 8).",
    ])

    seccion(h, "Sección 2", "Contexto, arquitectura y alcance")
    h.append(P(
        f"El volcado oficial se carga en Databricks: un Volume guarda los archivos, <b>Bronze</b> conserva una copia fiel como texto, <b>Silver</b> aplica tipos, escapes y control de "
        f"calidad, y <b>Gold</b> construye el modelo en español. Lakeflow Jobs orquesta el proceso. El volcado usado es {code(m['version_volcado'])}, Schema Sequence {m['schema_sequence']}."
    ))
    h.append(tabla([
        ["Capa", "Propósito", "Modelo", "Objetos principales"],
        ["Volume", "Archivos originales", "TSV", "11 tablas y 6 catálogos oficiales"],
        ["Bronze", "Copia fiel, sin interpretar", "Delta, todo texto", f"11 tablas, {fmt_int(sum(m['conteos']['bronze'].values()))} filas"],
        ["Silver", "Datos tipados y limpios", "Relacional 3FN en Delta", f"{fmt_int(m['conteos']['silver_principales_total'])} filas en 11 tablas, más catálogos"],
        ["Gold", "Consumo analítico", "Estrella de Kimball", "3 hechos, 7 dimensiones y 4 tablas mv_*"],
        ["Consumo", "Dashboard", "Databricks AI/BI", f"{len(LV['pages'])} páginas, {widgets} widgets, {len(LV['datasets'])} datasets"],
    ], [2.2, 4.5, 3.9, 6.3], primera_negrita=True))
    h.append(P("Alcance de los datos", "h2"))
    h += vinetas([
        f"Se procesan <b>{fmt_int(T['pistas'])} pistas</b>, el volcado completo. La carga anterior tomaba las primeras 15 M por orden de archivo y no era una muestra aleatoria.",
        f"Hay {fmt_int(T['lanzamientos'])} lanzamientos con pistas de {fmt_int(m['conteos']['silver']['release'])} en Silver. El resto no tiene pistas asociadas.",
        f"Existen {fmt_int(E['lanzamientos_sin_fecha'])} lanzamientos sin fecha válida en la clave 0 y {fmt_int(E['pistas_sin_geografia'])} pistas sin geografía.",
    ])

    seccion(h, "Sección 3", "Diseño dimensional (metodología Kimball)")
    h.append(P("El modelo sigue los cuatro pasos de Kimball. El grano es la decisión que más cambió frente a la entrega anterior."))
    h.append(tabla([
        ["Paso", "Decisión", "Justificación"],
        ["1. Proceso", "Publicación de pistas en lanzamientos", "Es el evento medible que responde RF01 a RF08."],
        ["2. Grano", "Atómico: una fila por pista en fact_pista", "Conserva el detalle completo y cumple el requisito de más de 50 M de registros."],
        ["3. Dimensiones", "Fecha, artista, lanzamiento, geografía, formato, idioma y rango de duración", "Son los ejes de análisis pedidos."],
        ["4. Hechos", "Banderas en fact_pista y métricas aditivas en los agregados", "Permiten sumar sin duplicar en cualquier nivel."],
    ], [2.6, 6.5, 7.8], primera_negrita=True))
    h.append(aviso(
        "«Una fila de <b>fact_pista</b> representa una pista dentro de un soporte de un lanzamiento.» "
        "«Una fila de <b>fact_produccion_musical</b> consolida las pistas de un día para una combinación de artista, perfil de lanzamiento, geografía, formato e idioma.»",
        "Declaración del grano", AZUL))
    h.append(KeepTogether([diagrama_estrella(m), P("Figura 1. Hechos de Gold y dimensiones conformadas, con filas actuales.", "caption")]))
    h.append(P("Decisiones de diseño clave", "h2"))
    h += vinetas([
        "<b>Dos niveles:</b> fact_pista guarda el detalle; los hechos agregados dan respuestas rápidas al dashboard.",
        "<b>Claves sustitutas:</b> enteros secuenciales ordenados por clave natural; aíslan el modelo de la fuente.",
        "<b>Fila cero:</b> cada dimensión tiene una fila para el valor desconocido, así el hecho nunca pierde filas.",
        f"<b>dim_lanzamiento como dimensión de perfil:</b> {fmt_int(G['dim_lanzamiento'])} combinaciones de estado, empaque y calidad, no una fila por lanzamiento. "
        "El identificador del lanzamiento queda en fact_pista.",
    ])

    seccion(h, "Sección 4", "Tablas de hechos")
    h.append(P(f"<b>fact_pista</b> tiene {fmt_int(G['fact_pista'])} filas. <b>fact_produccion_musical</b> tiene {fmt_int(G['fact_produccion_musical'])} filas y 11 métricas aditivas."))
    h.append(tabla([
        ["Métrica agregada", "Cálculo", "Significado"],
        ["lanzamientos_total", "1 en la primera pista del lanzamiento", "Lanzamientos únicos"],
        ["soportes_total", "1 en la primera pista del soporte", "Discos o medios únicos"],
        ["pistas_total", "Conteo de pistas", "Pistas publicadas"],
        ["grabaciones_unicas_total", "1 en la primera aparición", "Grabaciones distintas"],
        ["duracion_total_*", "Suma de duración", "Tiempo en ms, segundos y minutos"],
        ["pistas_con_isrc_total", "Suma de la bandera tiene_isrc", "Pistas con código ISRC"],
        ["pistas_largas_total", "Pistas de más de 5 minutos", "Pistas largas"],
        ["pistas_video_total", "Suma de la bandera es_video", "Pistas de video"],
        ["pistas_completas_total", "Pistas con duración mayor que 0", "Denominador de promedios"],
    ], [5.2, 6.2, 5.5], primera_negrita=True))
    h.append(aviso(
        "Un conteo distinto por fila no es aditivo: si un lanzamiento aparece en dos filas, la suma lo cuenta dos veces. Por eso cada lanzamiento, soporte y grabación se asigna a una sola fila, "
        f"la de su primera pista. En Databricks se calcula con {code('min(struct(...))')} en lugar de {code('ROW_NUMBER')}. Así, las sumas dan {fmt_int(T['lanzamientos'])} lanzamientos y {fmt_int(T['soportes'])} soportes, iguales a los conteos distintos.",
        "Por qué los conteos son aditivos", MENTA))
    h.append(P("Regla de fecha y territorio", "h2"))
    h += vinetas([
        "La fecha es la más antigua del lanzamiento, con prioridad para eventos con país. Si no es válida, va a la clave 0. No se imputa con otros datos.",
        f"Si un solo país tiene esa fecha, se conserva. Con 10 o más países empatados pasa a [Worldwide]; con 2 a 9, al país con más lanzamientos. Esta regla corrige el caso Afghanistan (sección 8).",
        "Los años válidos van de 1900 a 2030. Las fechas anteriores a 1900 pasan a «sin fecha».",
    ])
    e = m["ejemplo_grano"]
    h.append(P("Ejemplo real", "h2"))
    h.append(P(
        f"El lanzamiento {e['lanzamiento_id']} de Shakira ocupa <b>{e['pistas']} filas</b> en fact_pista, en {e['soportes']} soportes, con {e['pistas_isrc']} pistas con ISRC. Solo {e['cuenta_lanzamiento']} fila suma el lanzamiento. "
        "En la carga recortada aparecía con 21 pistas y 2 soportes, algo consistente con el corte por líneas del archivo."
    ))

    seccion(h, "Sección 5", "Dimensiones conformadas")
    h.append(tabla([
        ["Dimensión", "Filas", "Atributos principales", "Uso"],
        ["dim_fecha", fmt_int(G["dim_fecha"]), "anio, trimestre, mes, decada, siglo", "Rangos y series de tiempo"],
        ["dim_artista", fmt_int(G["dim_artista"]), "nombre_artista, tipo_artista, genero, nombre_pais, anio_inicio", "Tipo de artista y rankings"],
        ["dim_lanzamiento", fmt_int(G["dim_lanzamiento"]), "estado_lanzamiento, tipo_empaque, calidad_datos", "Filtro de estado y densidad"],
        ["dim_formato", fmt_int(G["dim_formato"]), "nombre_formato, categoria_formato", "Mezcla y participación digital"],
        ["dim_geografia", fmt_int(G["dim_geografia"]), "nombre_area, tipo_area, nombre_pais", "Rankings y dispersión"],
        ["dim_idioma", fmt_int(G["dim_idioma"]), "nombre_idioma, codigo_iso", "Top idiomas"],
        ["dim_rango_duracion", fmt_int(G["dim_rango_duracion"]), "etiqueta_rango, limites en segundos", "Histograma"],
    ], [3.4, 1.8, 7.0, 4.7], primera_negrita=True))
    h.append(Spacer(1, 7))
    h += vinetas([
        "<b>Etiquetas:</b> cada ID se resuelve con los catálogos oficiales del volcado. Las reglas V08 a V11 bloquean el job si una etiqueta difiere.",
        f"<b>Calidad:</b> {fmt_int(sin_calificar)} lanzamientos tienen el valor por defecto −1 y figuran como «Sin calificar». Esa cifra no significa calidad baja.",
        "<b>Calidad y catálogo:</b> la calidad no viene como catálogo en el volcado. Sus nombres (0 Baja, 1 Normal, 2 Alta) y la asignación de categorías de formato son criterio del proyecto.",
        "<b>Fila 0 de dim_lanzamiento:</b> la ocupan 770 lanzamientos reales de calidad 0, sin estado ni empaque; no es un desconocido puro.",
        "<b>SCD Tipo 1:</b> las dimensiones se reconstruyen en cada carga; el análisis no requiere historial de atributos.",
    ])

    seccion(h, "Sección 6", "Hecho de distribución y dimensión de bandas", salto=False)
    h.append(P(f"El histograma necesita contar pistas por duración. Para eso existe <b>fact_distribucion_duracion</b>, con {fmt_int(G['fact_distribucion_duracion'])} filas y grano año × formato × idioma × geografía × banda."))
    h += vinetas([
        f"<b>dim_rango_duracion:</b> 20 bandas de 30 s entre 0:00 y 10:00, una banda abierta «10:00+» y la clave 0 «Sin duración».",
        f"<b>Conciliación:</b> las bandas con duración suman {fmt_int(H['total'])} pistas, igual a las pistas con duración del hecho agregado.",
        "<b>Ancho de 30 s:</b> la regla de Sturges con unas 54 M de observaciones sugiere alrededor de 27 clases, cercano a las 21 usadas, y 30 s es fácil de leer.",
        "<b>Sin artista:</b> el grano no incluye artista, así que el filtro de tipo de artista no afecta al histograma. Es una limitación conocida.",
    ])

    seccion(h, "Sección 7", "Diseño físico y rendimiento")
    d = m["detalle"]["gold"]
    h.append(tabla([
        ["Objeto", "Filas", "Tamaño", "Archivos", "Clustering"],
        *[[n, fmt_int(G[n]), fmt_gb(d[n]["bytes"]), fmt_int(d[n]["archivos"]), d[n]["clustering"].strip("[]").replace('"', "").replace(",", ", ") or "—"]
          for n in ("fact_pista", "fact_produccion_musical", "fact_distribucion_duracion", "dim_artista", "mv_analitica_artistas")],
    ], [5.4, 2.6, 2.2, 1.9, 4.8], primera_negrita=True))
    h.append(Spacer(1, 7))
    h += vinetas([
        "<b>Delta Lake:</b> columnar, comprimido y con historial. El historial permitió comparar versiones con <i>time travel</i> y probar que las claves no cambiaron.",
        "<b>Liquid clustering:</b> reemplaza particiones e índices. Se aplica en los hechos sobre fecha_key y artista_key. Su beneficio <b>no se midió</b> contra una tabla sin clustering.",
        f"<b>Tablas agregadas:</b> sostienen el dashboard. En pruebas por la API, el warehouse 2X-Small respondió entre {fmt_dec(m['proceso']['almacen']['consulta_min_s'], 1)} y {fmt_dec(m['proceso']['almacen']['consulta_max_s'], 1)} s.",
        "<b>Advertencia:</b> esas pruebas fueron consultas una a la vez, no varios usuarios simultáneos, y las tablas pueden tardar más al abrir la página si el warehouse estaba apagado.",
    ])

    seccion(h, "Sección 8", "Calidad de datos y hallazgos de auditoría")
    h.append(P(
        f"El registro {code('meta.data_quality_log')} tiene <b>{reglas_ok} de {reglas} reglas bloqueantes aprobadas</b>: {finales} de la validación final y {silver_r} de Silver. "
        "También registra 10 indicadores informativos. Las reglas no reemplazan la revisión: dos de los errores siguientes pasaron las primeras validaciones."
    ))
    a = m["proceso"]["afganistan_antes"]
    h.append(tabla([
        ["#", "Defecto", "Impacto", "Corrección", "Detección"],
        ["1", "Conteos distintos por fila que luego se sumaban (entrega anterior)", "KPI principal inflado", "Asignación a la primera pista", "Conciliación"],
        ["2", "Orden de columnas de medium invertido en el DDL anterior", "edits_pending y track_count cruzados", "Orden real del volcado", "Inspección de archivos"],
        ["3", "Etiquetas escritas a mano por ID", f"{fmt_int(sin_calificar)} lanzamientos «Baja»; 76.524 ciudades como «Condado»", "Catálogos oficiales y reglas V08 a V11", "Inspección, no por reglas"],
        ["4", "Empates de fecha resueltos por menor ID de país", f"Afghanistan con {fmt_int(a['lanzamientos'])} lanzamientos", "Regla nueva y validación V12", "Inspección, no por reglas"],
        ["5", "29 de febrero convertido en día 1", "Fechas alteradas", "Se conserva la fecha real", "Revisión de código"],
        ["6", "artist_credit usado como artist.id", "Riesgo de artista incorrecto", "Sin esa asignación", "Revisión de código"],
    ], [0.6, 5.0, 4.5, 3.9, 2.9]))
    h.append(aviso(
        f"Afghanistan tiene el ID de área 1. Cuando un lanzamiento se publicaba en muchos países con la misma fecha, el desempate elegía el menor ID. Por eso reunía {fmt_int(a['lanzamientos'])} lanzamientos de {fmt_int(a['artistas'])} artistas. "
        f"Con la regla nueva bajó a {fmt_int(E['afganistan_lanzamientos'])} y [Worldwide] subió de {fmt_int(m['proceso']['worldwide_antes'])} a {fmt_int(E['lanzamientos_worldwide'])}. Los totales no cambiaron y {fmt_int(m['proceso']['pistas_movidas_area'])} pistas cambiaron de área.",
        "Caso de estudio: un dato raro era un error de lógica", DURAZNO))
    h.append(P("Datos especiales tratados en el dashboard", "h2"))
    h += vinetas([
        "Artistas como [unknown] o [no artist] se excluyen de los rankings: no son artistas reales.",
        "El ranking de países usa solo áreas de tipo País. [Worldwide] se muestra aparte, como bloque multiterritorial.",
        f"Las series terminan en 2025: 2026 está incompleto y hay {fmt_int(E['pistas_fecha_futura'])} pistas con años posteriores a 2026.",
    ])

    seccion(h, "Sección 9", "Dashboard en Databricks AI/BI")
    h.append(P(
        f"El dashboard tiene {len(LV['pages'])} páginas, {widgets} widgets y {len(LV['datasets'])} datasets. AI/BI no usa DAX: las medidas se escriben como expresiones SQL sobre cada dataset (Anexo A). "
        "Corre sobre el warehouse, sin importar datos al equipo del usuario."
    ))
    h.append(tabla([
        ["Página", "Pregunta que responde", "Contenido"],
        ["Resumen ejecutivo", "¿Cuánto y cómo cambió la industria?", "5 KPI, área por formato, cuota digital y rankings"],
        ["Análisis detallado", "¿Qué la caracteriza por época, país y artista?", "4 KPI, histograma, mezcla, Top 20 y dispersión"],
        ["Calidad y catálogo", "¿Qué tan formalizado y denso es el catálogo?", "4 KPI, tiempo, áreas, empaque, mapa de calor y emergentes"],
    ], [4.0, 6.2, 6.7], primera_negrita=True))
    h.append(Spacer(1, 8))
    h.append(figura(BUILD / "dash_resumen.png", 13.4, "Figura 2. Página Resumen ejecutivo publicada en Databricks."))
    h.append(figura(BUILD / "dash_detallado.png", 13.4, "Figura 3. Página Análisis detallado."))
    h.append(figura(BUILD / "dash_calidad.png", 13.4, "Figura 4. Página Calidad y catálogo."))
    h.append(P("Diferencias funcionales frente a Power BI", "h2"))
    h += vinetas([
        "<b>Drill-down:</b> no existe. Lo reemplazan gráficos por siglo y década, año, mes y Top 15 áreas, con filtros.",
        "<b>Clic para filtrar:</b> hacer clic en un gráfico no filtra los demás; actúan los filtros de página.",
        "<b>Top N:</b> se calcula sobre todos los datos y no se recalcula al filtrar.",
        "<b>Histograma:</b> muestra pistas por banda, no porcentaje.",
        "<b>Dispersión:</b> el eje X es LOG10 calculado en SQL y no responde a filtros.",
        "<b>Tablas:</b> no muestran separador de miles; se probaron tres formatos sin éxito.",
    ])

    seccion(h, "Sección 10", "Diseño del dashboard y teoría del color", salto=False)
    h.append(P("Principios aplicados", "h2"))
    h += vinetas([
        "<b>Regla 3-30-300:</b> en 3 segundos se entiende el propósito, en 30 los hallazgos y en 300 se explora el detalle.",
        "<b>Jerarquía visual (Stephen Few):</b> arriba los filtros, luego KPI, tendencia y desglose.",
        "<b>Relación datos-tinta (Edward Tufte):</b> sin efectos 3D ni sombras; cuadrícula tenue.",
        "<b>Una pregunta por página:</b> cada página tiene un propósito distinto.",
    ])
    h.append(tabla([
        ["Elemento", "Color", "Razón"],
        ["Mensaje principal", "Azul #1F5FA8", "Digital o líder del ranking; concentra la atención."],
        ["Contraste", "Naranja #C2691A", "Complementario del azul: separa digital de óptico."],
        ["Otras categorías", "Verde azulado #08A08C y violeta #8064B5", "Distinguibles entre sí y del par principal."],
        ["Contexto", "Azul grisáceo #A9BDD3", "Acompaña sin competir por la atención."],
        ["Sin peso analítico", "Grises #9AA5B1 y #D5DAE1", "«Otros» y «Desconocido» no deben destacar."],
        ["Lienzo", "#F4F6F8 con tarjetas blancas", "Evita el blanco puro en pantalla grande."],
        ["Texto", "Tinta #1F2A37", "Contraste de 14,5:1 sobre blanco."],
    ], [3.7, 5.3, 7.9], primera_negrita=True))
    h.append(Spacer(1, 7))
    h.append(P("Validación de la paleta", "h2"))
    h.append(P(
        "La paleta se comprobó con un validador que simula daltonismo y mide contraste; no se eligió a ojo. El primer intento falló: el verde azulado estaba apagado y el naranja tenía poco contraste. Se ajustó y volvió a medirse."
    ))
    h.append(tabla([
        ["Paleta", "Resultado", "Detalle"],
        ["Categórica del dashboard", "Aprobada", "Peor separación con daltonismo ΔE 12,5; visión normal ΔE 21,6; contraste de al menos 3:1"],
        ["Presentación pastel", "Aprobada con aviso", "ΔE 8,7 con daltonismo; naranja y menta bajo 3:1, compensado con etiquetas visibles"],
        ["Tintes de Mezcla de formatos", "No aprobados", "Fallan el piso de croma y la separación normal (ΔE 14,5); se distinguen por leyenda y posición"],
    ], [5.0, 3.0, 8.9], primera_negrita=True))
    h.append(Spacer(1, 5))
    h.append(P("<b>Excepción declarada:</b> los tintes de la mezcla se suavizaron para que los bloques grandes no cansen. Es una decisión estética con costo conocido, no una paleta validada.", "body_muted"))

    seccion(h, "Sección 11", "Justificación de cada gráfico")
    h.append(P("Cada gráfico se eligió por el <b>tipo de pregunta estadística</b>, según el selector de Andrew Abela: comparación, composición, distribución y relación."))
    h.append(tabla([
        ["Gráfico", "Pregunta", "Tipo (Abela)", "Por qué este gráfico"],
        ["Tarjetas KPI", "¿Cuál es la magnitud?", "Valor único", "Un número clave no necesita eje."],
        ["Área por año y formato", "¿Cómo creció y cambió la mezcla?", "Composición en el tiempo", "Muestra total y capas en muchos períodos."],
        ["Líneas digital vs. óptico", "¿Cuándo cambió el liderazgo?", "Comparación en el tiempo", "Dos líneas en un eje marcan el cruce."],
        ["Barras horizontales", "¿Quién produce más?", "Comparación", "La longitud se compara bien y caben nombres largos."],
        ["Histograma", "¿Cuánto dura una pista?", "Distribución", "Barras contiguas para clases continuas."],
        ["Columnas al 100 %", "¿Qué dominó cada década?", "Composición relativa", "Compara proporciones aunque cambie el volumen."],
        ["Dispersión logarítmica", "¿Más volumen implica más digital?", "Relación", "Cada punto es un país y revela casos atípicos."],
        ["Tabla Top 20", "¿Qué valores exactos tienen?", "Consulta", "Da precisión en varias métricas."],
        ["Columnas por década, año y mes", "¿Cómo se reparte en el tiempo?", "Comparación temporal", "Sustituyen el drill-down temporal."],
        ["Top 15 áreas", "¿Qué áreas concentran la producción?", "Comparación", "Sustituye el drill-down geográfico."],
        ["Barras agrupadas por empaque", "¿Qué empaque es más denso?", "Comparación de dos medidas", "Ambas medidas comparten unidad; evita el doble eje."],
        ["Mapa de calor ISRC", "¿Qué países y tipos formalizan más?", "Magnitud en cuadrícula", "Un solo tono de claro a oscuro."],
        ["Tabla de emergentes", "¿Quiénes son los nuevos artistas?", "Consulta", "Lista exacta con inicio desde 2015."],
    ], [4.2, 4.6, 3.3, 4.8], primera_negrita=True))
    h.append(P("Gráficos descartados", "h2"))
    h += vinetas([
        "<b>Torta:</b> el ojo compara mal ángulos; con varios formatos, el 100 % apilado es más preciso.",
        "<b>Doble eje:</b> dos escalas sugieren correlaciones que dependen de cómo se elige cada una.",
        "<b>Mapa coroplético:</b> un país dominante satura la escala y el área geográfica distorsiona la lectura.",
        "<b>Dispersión con 30 colores:</b> la primera versión usaba un color por país. Se redujo a dos tonos porque tantos colores no comunicaban nada.",
    ])
    h.append(figura(g_cuota(m), 14.6, f"Figura 5. Cuota anual de digital y óptico. El cruce ocurre en {m['cruce_digital']}."))
    h.append(figura(g_mezcla(m), 14.6, "Figura 6. Mezcla de formatos por década, porcentaje de lanzamientos."))
    h.append(figura(g_paises(m), 14.6, "Figura 7. Lanzamientos por área: [Worldwide] y los nueve primeros países."))
    h.append(figura(g_dispersion(m), 14.6, "Figura 8. Volumen y digitalización en el Top 30 de países, con escala logarítmica."))

    seccion(h, "Sección 12", "Fundamentos estadísticos")
    h.append(tabla([
        ["Estadística", "Medida", "Por qué se usa"],
        ["Total", "SUM(lanzamientos)", "Magnitud aditiva, válida con cualquier filtro."],
        ["Conteo distinto", "COUNT(DISTINCT artista_key)", "Artistas únicos: no se suman, se cuentan en el contexto filtrado."],
        ["Proporción", "parte / NULLIF(total, 0)", "Coberturas y participaciones."],
        ["Media ponderada", "Σ segundos / Σ pistas con duración", "Evita el promedio de promedios."],
        ["Moda y mediana", "Banda más frecuente y percentil 50", "Tendencia central robusta."],
        ["Correlación de Pearson", "corr(año, duración media)", "Fuerza y signo de una relación lineal."],
        ["Pendiente", "regr_slope(duración, año)", "Traduce r a segundos por año."],
        ["Escala logarítmica", "LOG10(lanzamientos)", f"Top 30: de {fmt_int(m['paises'][-1]['lanzamientos'])} a {fmt_int(m['paises'][0]['lanzamientos'])}."],
    ], [4.0, 5.9, 7.0], primera_negrita=True))
    h.append(P("Distribución de la duración", "h2"))
    h.append(figura(g_histograma(m), 13.6, "Figura 9. Pistas por banda de duración de 30 s (excluye pistas sin duración)."))
    h += vinetas([
        f"<b>Moda:</b> {H['moda_banda']} ({fmt_pct(H['moda_pct'])}). <b>Mediana:</b> banda {H['mediana_banda']}. <b>Media:</b> {fmt_mmss(H['media_min'])} min.",
        f"<b>Concentración:</b> las dos bandas más frecuentes reúnen {fmt_pct(H['dos_mayores_pct'])} de las pistas. No son mayoría: esa cifra describe concentración, no un rango universal.",
        f"<b>Asimetría positiva:</b> la media supera a la mediana por la cola larga; {fmt_pct(H['mayor_10_pct'])} supera los 10 minutos.",
    ])
    h.append(PageBreak())
    h.append(P("Correlación año-duración (RF05)", "h2"))
    h.append(tabla([
        ["Período", "r de Pearson", "Pendiente", "Años (n)", "Lectura"],
        *[[f"{p['inicio']}–{p['fin']}", fmt_signo(p["r"]), f"{fmt_signo(p['pendiente_s'], 2)} s/año", str(p["n"]), lectura_r(p)] for p in m["pearson"]],
    ], [3.0, 2.8, 3.0, 2.0, 6.1], primera_negrita=True))
    h.append(aviso(
        f"La hipótesis de RF05 («el streaming acortó las canciones») <b>no queda demostrada</b>. A largo plazo la relación es positiva. En el período reciente r = {fmt_signo(P_R['r'])} con n = {P_R['n']}: "
        "no alcanza el valor crítico de 0,553 para significancia al 5 %. Con la carga recortada se había reportado −0,57, un resultado más fuerte de lo que los datos completos sostienen. "
        "Además, el cálculo usa medias anuales y no prueba causalidad.",
        "Lectura honesta del resultado", DURAZNO))

    seccion(h, "Sección 13", "Trazabilidad de requisitos", salto=False)
    h.append(tabla([
        ["Requisito", "Dónde se responde", "Estado"],
        ["RF01 · Ranking Top N", "Top 20 artistas y Top 10 países, con filtros", "Cubierto; Top N fijo"],
        ["RF02 · Formato e idioma", "KPI de duración, Top idiomas y mezcla de formatos", "Cubierto"],
        ["RF03 · Drill-down", "Gráficos por siglo, década, año, mes y Top 15 áreas", "Parcial: sin drill-down"],
        ["RF04 · Digital vs. físico", "Líneas de cuota, área y KPI de pistas largas", "Cubierto"],
        ["RF05 · Correlación", "Sección 12 de este documento; histograma en el dashboard", "Cubierto en documento"],
        ["RF06 · Formalización ISRC", "Mapa de calor por país y tipo de artista", "Cubierto"],
        ["RF07 · Densidad", "KPI y barras por empaque (Top 8)", "Cubierto"],
        ["RF08 · Emergentes", f"KPI de {fmt_int(m['emergentes']['total'])} artistas y Top 15 con 100 % ISRC ({fmt_int(m['emergentes']['isrc_100'])} califican)", "Cubierto"],
    ], [5.0, 8.4, 3.5], primera_negrita=True))

    seccion(h, "Sección 14", "Limitaciones y trabajo futuro")
    h += vinetas([
        "<b>Asignación a la primera pista:</b> un lanzamiento con varios artistas o formatos se atribuye a los de su primera pista.",
        "<b>Territorio:</b> la regla de 10 países es un criterio del proyecto; con 2 a 9 países se elige el de mayor catálogo, no necesariamente el origen real.",
        "<b>País de respaldo:</b> un lanzamiento sin país toma el área del artista de cada pista.",
        "<b>Fechas:</b> las anteriores a 1900 van a «sin fecha» y hay fechas futuras en el dato.",
        "<b>Top de artistas:</b> está dominado por compositores clásicos por las muchas reediciones; no mide popularidad.",
        "<b>Sin medir:</b> beneficio del clustering, concurrencia del warehouse y consumo de cuota.",
        "<b>Power BI:</b> el reporte queda como entrega anterior, con la carga de 15 M. El dashboard vigente es AI/BI.",
        "<b>Trabajo futuro:</b> agregar drill-down al dashboard y medir rendimiento comparado.",
    ])

    seccion(h, "Sección 15", "Preguntas probables del profesor")
    qa = [
        ("¿Por qué una estrella y no un copo de nieve?", "Minimiza joins, es fácil de entender y funciona bien con herramientas de BI. Las jerarquías se desnormalizan dentro de cada dimensión."),
        ("¿Cuál es el grano?", "Una fila por pista en fact_pista. Los agregados consolidan por día y dimensiones para dar rapidez al dashboard."),
        ("¿Son aditivas todas las métricas?", f"Sí. Cada lanzamiento, soporte y grabación suma una sola vez. La suma coincide con el conteo distinto: {fmt_int(T['lanzamientos'])} lanzamientos. Los artistas activos se calculan como conteo distinto, no se suman."),
        ("¿Qué es la clave 0?", "El miembro desconocido de cada dimensión: los totales cuadran y se ve cuánto dato falta."),
        (f"¿Por qué {fmt_pct(T['isrc_pct'])} de ISRC?", "Es la cobertura en MusicBrainz. Indica cuántas pistas registradas allí tienen código, no el registro real en la industria."),
        ("¿Por qué [Worldwide] es tan grande?", "Es el territorio de lanzamientos multiterritoriales. Se compara aparte porque no es un país."),
        ("¿La correlación prueba que el streaming acortó las canciones?", f"No. Entre {P_R['inicio']} y {P_R['fin']}, r = {fmt_signo(P_R['r'])} no es significativa y Pearson no prueba causalidad."),
        ("¿Cómo sabe que los números son correctos?", f"Por {reglas} reglas bloqueantes, pruebas con datos pequeños, conciliación con el volcado y filtros comparados con SQL. Aun así, dos errores se hallaron por inspección, por eso también revisamos resultados."),
        ("¿Por qué no usó una paleta validada en todos los gráficos?", "La mezcla usa tintes suaves por comodidad visual. Se declara la excepción: se distinguen por leyenda y posición."),
    ]
    for q, a_ in qa:
        h.append(KeepTogether([P(f"<b>P:</b> {q}", "h3"), P(f"<b>R:</b> {a_}")]))

    seccion(h, "Sección 16", "Guion para la mesa directiva")
    h.append(P("Duración estimada: <b>8 minutos</b>. Las frases en cursiva son para decir; los corchetes indican acciones en pantalla. Conviene abrir cada página unos minutos antes."))
    guion = [
        ("0:00 – 0:45 · Apertura", "[Resumen ejecutivo, sin filtros]", f"«Buenos días. Les voy a mostrar qué dicen casi 59 millones de pistas sobre la producción musical. Todo sale de un Data Warehouse verificado sobre el catálogo público de MusicBrainz.»"),
        ("0:45 – 1:45 · Tamaño del catálogo", "[Señalar las tarjetas KPI]", f"«Son {fmt_int(T['lanzamientos'])} lanzamientos y {fmt_int(T['artistas'])} artistas activos. El {fmt_pct(T['isrc_pct'])} de las pistas tiene código ISRC en este catálogo, y esa es la métrica de formalización que seguiremos.»"),
        ("1:45 – 3:00 · La gran transición", "[Señalar área y líneas]", f"«En {m['cruce_digital']} digital superó a los formatos ópticos. En 2025 digital ya es {fmt_pct(ult['digital'])} de los lanzamientos con fecha. La distribución digital ya no es un canal alternativo.»"),
        ("3:00 – 4:00 · Dónde se produce", "[Señalar Top 10 países]", f"«Estados Unidos, Reino Unido y Japón encabezan los países. Hay además {fmt_int(E['lanzamientos_worldwide'])} lanzamientos multiterritoriales, una señal de que mucho contenido se publica globalmente desde el primer día.»"),
        ("4:00 – 5:00 · Qué caracteriza a la música", "[Análisis detallado, histograma]", f"«La duración más frecuente está entre {H['moda_banda']}. Sobre si el streaming acortó las canciones: la caída reciente es débil y no permite afirmarlo.»"),
        ("5:00 – 6:00 · Volumen y digitalización", "[Señalar la dispersión]", f"«Más volumen no significa más digital. Corea del Sur llega a {fmt_pct(corea['digital'])}: los mercados pequeños y muy digitales merecen una mirada aparte.»"),
        ("6:00 – 7:00 · Calidad y talento", "[Calidad y catálogo]", f"«El mapa de calor muestra dónde está más formalizado el catálogo. {fmt_int(m['emergentes']['isrc_100'])} artistas emergentes ya tienen todas sus pistas con ISRC.»"),
        ("7:00 – 8:00 · Confianza y cierre", "[Volver al Resumen ejecutivo]", "«Encontramos y corregimos errores reales antes de esta reunión, y cada cifra se concilia con la fuente. Recomendamos priorizar digital, impulsar el registro ISRC y observar mercados muy digitales. ¿Preguntas?»"),
    ]
    for cuando, accion, decir in guion:
        h.append(KeepTogether([P(cuando, "script_time"), P(accion, "body_muted"), P(decir, "script_say")]))

    seccion(h, "Anexo A", "Medidas del dashboard en SQL")
    h.append(P("Expresiones reales de las tarjetas KPI, extraídas del archivo del dashboard. Se usan NULLIF para evitar divisiones por cero y sumas ponderadas para evitar el promedio de promedios."))
    filas = [["Página", "KPI", "Expresión", "Dataset"]]
    for p in LV["pages"]:
        for l in p["layout"]:
            w = l["widget"]
            s = w.get("spec")
            if s and s["widgetType"] == "counter":
                q = w["queries"][0]["query"]
                filas.append([p["displayName"], s["frame"]["title"], code(q["fields"][0]["expression"].replace("`", "")), q["datasetName"]])
    h.append(tabla(filas, [3.0, 4.2, 6.9, 2.8]))

    seccion(h, "Anexo B", "Glosario")
    h.append(tabla([
        ["Término", "Significado"],
        ["Grano", "Lo que representa exactamente una fila de un hecho."],
        ["Lanzamiento (release)", "Publicación concreta de un álbum, sencillo o EP."],
        ["Soporte (medium)", "Disco o medio dentro de un lanzamiento."],
        ["Grabación (recording)", "La obra grabada; puede aparecer en varios lanzamientos."],
        ["Pista (track)", "Aparición de una grabación en un soporte."],
        ["ISRC", "Código internacional que identifica una grabación."],
        ["Delta Lake", "Formato de tabla con transacciones e historial sobre archivos Parquet."],
        ["Time travel", "Consultar una versión anterior de una tabla Delta."],
        ["Liquid clustering", "Organización de datos que reemplaza particiones y ZORDER."],
        ["AI/BI", "Herramienta de dashboards de Databricks."],
    ], [4.5, 12.4], primera_negrita=True))
    return h


def main():
    salida = Path(sys.argv[1]) if len(sys.argv) > 1 else SALIDA
    m = metricas()
    portada = portada_factory(
        ["Defensa de la capa Gold", "y del dashboard"],
        ["Versión 2: Databricks, volcado completo", f"{fmt_int(m['totales']['pistas'])} pistas"],
        ["Juan Sebastián Rincón Farelo", "Integrantes: Juan Rincón, Sebastián Russo, Jesús Figueroa", "Docente: Amilkar Sierra Romano",
         "Ingeniería de Sistemas · Universidad Popular del Cesar", "Valledupar, noviembre de 2026"],
    )
    doc = Documento(salida, "DWMusicBrainz · Defensa de Gold y dashboard", portada, title="DWMusicBrainz · Defensa de la capa Gold y dashboard (v2)",
                    author="Juan Sebastián Rincón Farelo", subject="Data Warehouse MusicBrainz en Databricks")
    doc.multiBuild([Spacer(1, 1)] + historia(m))
    print(f"[OK] {salida}")


if __name__ == "__main__":
    main()
