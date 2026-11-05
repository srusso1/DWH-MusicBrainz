"""
build_guion_junta_pdf.py
========================
Genera docs/Guion_Junta_Directiva_DWMusicBrainz.pdf: el guion para explicar el
dashboard a una junta directiva, página por página, con cifras y análisis.

Requiere docs/build/metricas_databricks.json y docs/build/datos_junta.json.

Uso:
    python scripts/generar_datos_junta.py
    python scripts/build_guion_junta_pdf.py [ruta_salida.pdf]
"""

import json
import sys
from collections import defaultdict
from pathlib import Path

from reportlab.lib.units import cm
from reportlab.platypus import KeepTogether, NextPageTemplate, PageBreak, Spacer

from doc_pdf_comun import (
    AZUL, BASE_DIR, BUILD, DURAZNO, LAVANDA, MENTA, Documento, P, aviso, figura, fmt_dec, fmt_int, fmt_mill, fmt_pct,
    fmt_signo, indice, metricas, portada_factory, rejilla_kpi, seccion, tabla, vinetas,
)

SALIDA = BASE_DIR / "docs" / "Guion_Junta_Directiva_DWMusicBrainz.pdf"

# Valores comprobados en el dashboard publicado contra SQL durante las pruebas en vivo.
DEMO_ANIOS = {"lanzamientos": 1169839, "pistas": 15574369, "artistas": 599256, "isrc": 0.251, "digital": 0.193}
DEMO_SIGLO_XX = {"isrc": 0.241, "por_lanzamiento": 10.6, "por_soporte": 9.8}
DEMO_2010S = {"isrc": 0.310, "por_lanzamiento": 10.2, "por_soporte": 9.1}


def datos():
    return json.loads((BUILD / "datos_junta.json").read_text(encoding="utf-8"))


def decir(texto):
    return P(f"«{texto}»", "script_say")


def senalar(texto):
    return P(f"<b>En pantalla:</b> {texto}", "body_muted")


def bloque(titulo, tiempo, pantalla, guion, lectura):
    cabeza = [P(f"{titulo} <font size=8.6 color='#56647A'>· {tiempo}</font>", "h2"), senalar(pantalla)]
    h = [KeepTogether(cabeza + [decir(guion[0])])]
    h += [decir(t) for t in guion[1:]]
    if lectura:
        h.append(P("Lo que debe quedar claro", "h3"))
        h += vinetas(lectura)
    return h


def ctx(m, D):
    f = lambda n: D[n]["filas"]
    v = lambda n: f(n)[0]["valor"]
    T = m["totales"]
    L = T["lanzamientos"]
    anual = defaultdict(lambda: defaultdict(int))
    for r in f("g_area_formato"):
        anual[r["anio"]][r["categoria_formato"]] += r["valor"]
    tot = {a: sum(x.values()) for a, x in anual.items()}
    cuota = {r["anio"]: r for r in f("g_cuota")}
    return {
        "T": T, "L": L, "anual": anual, "tot": tot, "cuota": cuota, "v": v, "f": f,
        "paises": sorted(f("g_paises"), key=lambda r: -r["valor"]),
        "idiomas": sorted(f("g_idiomas"), key=lambda r: -r["valor"]),
        "tipos": sorted(f("g_tipo_artista"), key=lambda r: -r["valor"]),
        "areas": sorted(f("g_areas"), key=lambda r: -r["valor"]),
        "top": sorted(f("g_top_artistas"), key=lambda r: -r["lanzamientos_v"]),
        "disp": sorted(f("g_dispersion"), key=lambda r: -r["participacion_digital"]),
        "decadas": sorted(f("g_decada"), key=lambda r: r["decada"]),
        "meses": sorted(f("g_mes"), key=lambda r: r["mes_txt"]),
        "empaque": sorted(f("g_empaque"), key=lambda r: -r["pistas_lanz"]),
        "pivot": {(r["nombre_pais"], r["tipo_artista"]): r["cobertura"] for r in f("g_pivot")},
        "emer": sorted(f("g_emergentes"), key=lambda r: -r["lanzamientos_v"]),
        "formatos": {r["categoria"]: r for r in m["formatos"]},
        "mezcla": {(r["decada"], r["categoria_formato"]): r["valor"] for r in f("g_mezcla")},
        "dec_m": {r["decada"]: r for r in m["decadas"]},
        "bandas": m["histograma"]["bandas"],
    }


def cuota_pico_optico(c):
    r = max(c["cuota"].values(), key=lambda x: x["cd"])
    return r["anio"], r["cd"]


def resumen(m, c):
    T, L = c["T"], c["L"]
    u = m["ultimo_anio"]
    wide = m["especiales"]["lanzamientos_worldwide"]
    d20 = c["dec_m"]["2020s"]
    h = []
    seccion(h, "Antes de empezar", "Resumen para el presentador", salto=False)
    h.append(P(
        "Este guion cubre las tres páginas del dashboard en <b>unos 15 minutos</b>, más preguntas. El texto entre comillas está pensado "
        "para decirse en voz alta; las líneas <b>En pantalla</b> indican qué señalar. Cada sección cierra con lo que la junta debe recordar."))
    h.append(rejilla_kpi([
        (fmt_int(L), "lanzamientos"), (fmt_int(T["pistas"]), "pistas"), (fmt_int(T["artistas"]), "artistas activos"), (fmt_pct(T["isrc_pct"]), "cobertura ISRC"),
        (fmt_pct(u["digital"]), f"digital en {u['anio']}"), (str(m["cruce_digital"]), "digital supera a óptico"), (fmt_pct(wide / L), "lanzamientos multiterritorio"), (fmt_dec(T["dur_media_min"], 2) + " min", "duración media"),
    ]))
    h.append(Spacer(1, 8))
    h.append(P("Cinco mensajes que la junta debe llevarse", "h2"))
    h += vinetas([
        f"<b>El catálogo ya es digital.</b> {fmt_pct(u['digital'])} de los lanzamientos de {u['anio']} son digitales; el cruce con el formato óptico ocurrió en {m['cruce_digital']}.",
        f"<b>El catálogo se concentró en este siglo.</b> Los años 2020 ya suman {fmt_mill(d20['lanzamientos'], 2)} de lanzamientos en solo seis años.",
        f"<b>La distribución es global.</b> {fmt_pct(wide / L)} del catálogo no se atribuye a un solo país, y Estados Unidos lidera entre los países con {fmt_pct(c['paises'][0]['valor'] / L)}.",
        f"<b>Hay un rezago de formalización.</b> Solo {fmt_pct(T['isrc_pct'])} de las pistas tiene ISRC, aunque en los años 2020 sube a {fmt_pct(d20['isrc'])}.",
        f"<b>La canción típica dura entre 3 y 4 minutos.</b> Las dos bandas más frecuentes concentran {fmt_pct(m['histograma']['dos_mayores_pct'])}, y no se demuestra que el streaming las haya acortado.",
    ])
    h.append(aviso(
        "Estos datos describen el <b>catálogo registrado en MusicBrainz</b>, una base abierta mantenida por su comunidad. "
        "No son ventas, reproducciones ni participación de mercado. Conviene decirlo al inicio: protege la credibilidad de todo lo demás.",
        "La advertencia más importante", DURAZNO))
    h.append(P("Antes de entrar a la sala", "h2"))
    h += vinetas([
        "Abra el dashboard <b>cinco minutos antes</b> y recorra las tres páginas: el warehouse puede estar apagado y las tablas pueden tardar en cargar.",
        "Pulse actualizar y deje todos los filtros en <b>All</b>.",
        "Practique una vez la demostración de la página tres.",
    ])
    return h


def pagina1(m, c):
    T, L, tot, cuota, v = c["T"], c["L"], c["tot"], c["cuota"], c["v"]
    u = m["ultimo_anio"]
    anio_op, pico_op = cuota_pico_optico(c)
    an = c["anual"]
    p_op = max(((a, x.get("Físico / Óptico", 0)) for a, x in an.items()), key=lambda r: r[1])
    p_vi = max(((a, x.get("Físico / Vinilo", 0)) for a, x in an.items()), key=lambda r: r[1])
    pico = max(tot.items(), key=lambda r: r[1])
    wide = m["especiales"]["lanzamientos_worldwide"]
    pa = c["paises"]
    ids = c["idiomas"]
    tp = c["tipos"]
    suma_p = sum(r["valor"] for r in pa)
    horas = T["horas"]
    h = []
    seccion(h, "Página 1 · 5 minutos", "Resumen ejecutivo")
    h.append(figura(BUILD / "dash_resumen.png", 15.2, "Página Resumen ejecutivo del dashboard."))
    h += bloque("Apertura", "45 segundos", "permanezca en la parte superior, sin filtros.", [
        f"Buenos días. En los próximos quince minutos les voy a mostrar qué nos dice el catálogo musical abierto MusicBrainz: {fmt_mill(T['pistas'])} de pistas y {fmt_mill(L)} de lanzamientos, procesados completos en Databricks.",
        "Un punto antes de empezar: esto mide lo que está registrado en el catálogo, no ventas ni reproducciones. Sirve para ver cómo se publica la música, no cuánto se escucha.",
    ], [])
    h += bloque("Las cinco tarjetas", "45 segundos", "recorra las tarjetas de izquierda a derecha.", [
        f"Tenemos {fmt_int(L)} lanzamientos, que contienen {fmt_int(T['pistas'])} pistas, de {fmt_int(T['artistas'])} artistas activos. Son {fmt_int(horas)} horas de audio: más de {fmt_int(int(horas / 8760))} años de reproducción continua.",
        f"Dos porcentajes marcan la conversación. Primero, la cobertura ISRC, el código internacional que identifica una grabación: solo {fmt_pct(T['isrc_pct'])}. Segundo, la participación digital: {fmt_pct(v('k_digital'))} de todo el catálogo histórico ya es digital.",
    ], [
        f"Un lanzamiento tiene en promedio {fmt_dec(T['pistas_por_lanzamiento'], 1)} pistas.",
        f"Hay {fmt_mill(T['grabaciones'])} de grabaciones únicas para {fmt_mill(T['pistas'])} de pistas: cada grabación aparece {fmt_dec(T['pistas'] / T['grabaciones'], 2)} veces en promedio, por reediciones y recopilaciones.",
    ])
    crec = tot[2020] / tot[2000]
    h += bloque("Lanzamientos por año y formato", "1 minuto 15 segundos", "gráfico de área; siga con el dedo de izquierda a derecha.", [
        f"Esta es la historia completa. En 1950 se registran {fmt_int(tot[1950])} lanzamientos; en 2000, {fmt_int(tot[2000])}; en 2020, {fmt_int(tot[2020])}. Es decir, {fmt_dec(crec, 1)} veces más en dos décadas.",
        f"Fíjense en los colores. El vinilo, en verde, alcanza su máximo en {p_vi[0]} con {fmt_int(p_vi[1])} lanzamientos. El formato óptico, en naranja, llega a {fmt_int(p_op[1])} en {p_op[0]} y empieza a caer. Y el digital, en azul, se convierte en casi todo el crecimiento.",
        f"El punto más alto es {pico[0]}, con {fmt_int(pico[1])} lanzamientos. El dato de {u['anio']}, {fmt_int(tot[u['anio']])}, es menor, pero conviene tomarlo con cautela: los años recientes pueden seguir completándose.",
    ], [
        f"Entre 2019 y 2020 el registro sube {fmt_pct(tot[2020] / tot[2019] - 1)}; el gráfico muestra el salto, no su causa.",
        "Un área más alta significa más lanzamientos registrados, no más negocio.",
    ])
    a10, a11 = cuota[2010], cuota[m["cruce_digital"]]
    h += bloque("Digital contra óptico", "45 segundos", "gráfico de líneas; señale el cruce de las dos líneas.", [
        f"Aquí está el cambio más importante. El formato óptico, es decir CD, DVD y similares, llegó a {fmt_pct(pico_op)} de los lanzamientos en {anio_op}. Todavía en 2010 dominaba con {fmt_pct(a10['cd'])} contra {fmt_pct(a10['digital'])} digital.",
        f"En {m['cruce_digital']} las líneas se cruzan: {fmt_pct(a11['digital'])} digital frente a {fmt_pct(a11['cd'])} óptico. Y en {u['anio']} la brecha es enorme: {fmt_pct(u['digital'])} contra {fmt_pct(u['optico'])}.",
    ], [
        f"La transición tomó alrededor de una década y hoy está prácticamente completa: el vinilo representa {fmt_pct(u['vinilo'])} en {u['anio']}.",
    ])
    h += bloque("Dónde, quién y en qué idioma", "1 minuto 15 segundos", "fila inferior, de izquierda a derecha.", [
        f"Por país lidera Estados Unidos con {fmt_int(pa[0]['valor'])} lanzamientos, {fmt_pct(pa[0]['valor'] / L)} del catálogo. Le siguen Reino Unido con {fmt_pct(pa[1]['valor'] / L)}, Japón con {fmt_pct(pa[2]['valor'] / L)}, Alemania con {fmt_pct(pa[3]['valor'] / L)} y Francia con {fmt_pct(pa[4]['valor'] / L)}. Estos diez países suman {fmt_pct(suma_p / L)}.",
        f"Por tipo de artista, los solistas tienen {fmt_pct(tp[0]['valor'] / L)} y los grupos {fmt_pct(tp[1]['valor'] / L)}. Juntos son {fmt_pct((tp[0]['valor'] + tp[1]['valor']) / L)} del catálogo.",
        f"Y por idioma, el inglés domina con {fmt_int(ids[0]['valor'])} lanzamientos: {fmt_pct(ids[0]['valor'] / L)}, unas {fmt_dec(ids[0]['valor'] / ids[1]['valor'], 0)} veces el japonés, que es segundo con {fmt_pct(ids[1]['valor'] / L)}. El español aparece con {fmt_int(ids[3]['valor'])}, {fmt_pct(ids[3]['valor'] / L)}.",
    ], [
        f"El Top 10 de países no suma 100 % porque {fmt_pct(wide / L)} de los lanzamientos es multiterritorio y va a [Worldwide]; lo mostramos en la página tres.",
        f"<b>[Multiple languages]</b> es una categoría real del catálogo, con {fmt_pct(ids[2]['valor'] / L)}, no un error.",
    ])
    return h


def pagina2(m, c):
    T, v, f = c["T"], c["v"], c["f"]
    H = m["histograma"]
    P50 = {r["inicio"]: r for r in m["pearson"]}
    mz = c["mezcla"]
    dec_total = lambda d: sum(x for (a, _), x in mz.items() if a == d)
    pc = lambda d, cat: mz.get((d, cat), 0) / dec_total(d)
    top = c["top"]
    disp = c["disp"]
    dd = {r["nombre_pais"]: r["participacion_digital"] for r in disp}
    sin_dur = T["pistas"] - T["pistas_completas"]
    h = []
    seccion(h, "Página 2 · 5 minutos", "Análisis detallado")
    h.append(figura(BUILD / "dash_detallado.png", 15.2, "Página Análisis detallado del dashboard."))
    h += bloque("Las cuatro tarjetas", "30 segundos", "tarjetas superiores.", [
        f"Pasamos del tamaño al contenido. Cada lanzamiento trae {fmt_dec(v('k_pistas_lanz2'), 1)} pistas. Una pista dura en promedio {fmt_dec(v('k_duracion'), 2)} minutos, algo más de cuatro minutos y catorce segundos. Y {fmt_pct(v('k_largas'))} de las pistas supera los cinco minutos.",
    ], [])
    h += bloque("Cuánto dura una canción", "1 minuto", "histograma; señale las dos barras azules.", [
        f"Las dos barras azules son el corazón del catálogo: de tres a cuatro minutos. Juntas concentran {fmt_pct(H['dos_mayores_pct'])} de las pistas con duración conocida. La banda más frecuente, de tres a tres minutos y medio, tiene {fmt_pct(H['moda_pct'])}, y la mediana cae entre tres y medio y cuatro minutos.",
        f"La cola derecha es larga: solo {fmt_pct(H['mayor_10_pct'])} supera los diez minutos, pero esas pistas empujan el promedio hacia arriba. Por eso la media de {fmt_dec(H['media_min'], 2)} minutos es mayor que la duración típica.",
    ], [
        "Para hablar de la canción típica, use la mediana y no el promedio.",
        f"La gráfica cubre {fmt_mill(H['total'], 2)} de pistas; otras {fmt_mill(sin_dur, 2)} no reportan duración.",
    ])
    h += bloque("¿El streaming acortó las canciones?", "45 segundos", "permanezca en el histograma; este análisis no es un gráfico del dashboard.", [
        f"Es la pregunta que siempre aparece, y la respuesta honesta es que no queda demostrado. A largo plazo, de 1950 a 2025, la duración crece: la correlación con el año es {fmt_signo(P50[1950]['r'])}, alrededor de {fmt_dec(P50[1950]['pendiente_s'], 2)} segundos más por año.",
        f"Entre 2013 y 2025 la correlación es {fmt_signo(P50[2013]['r'])}. Es negativa, pero con solo trece años no es estadísticamente significativa. Hay un descenso leve, no una prueba.",
    ], [
        "Correlación no es causalidad, y estos cálculos usan promedios anuales.",
        f"La duración media de los años 2020 es {fmt_dec(c['dec_m']['2020s']['dur_media_min'], 2)} minutos.",
    ])
    cats = ("Físico / Vinilo", "Físico / Óptico", "Digital / Streaming")
    h += bloque("Cómo cambió la mezcla de formatos", "45 segundos", "barras al 100 %; recorra las décadas.", [
        f"Cada barra es una década completa. En los años 1970 el vinilo es {fmt_pct(pc('1970s', cats[0]))} de lo publicado. En los 1990 el óptico toma el relevo con {fmt_pct(pc('1990s', cats[1]))}. En los 2010 el digital ya es {fmt_pct(pc('2010s', cats[2]))}, y en lo que va de los 2020 llega a {fmt_pct(pc('2020s', cats[2]))}.",
        "En medio siglo pasamos por tres formatos dominantes, y hoy lo digital ocupa casi todo el catálogo nuevo.",
    ], [
        f"La barra de los años 1950 muestra {fmt_pct(pc('1950s', 'Otros Formatos'))} en otros formatos, categoría que incluye los discos de shellac.",
    ])
    clasicos = {"Johann Sebastian Bach", "Ludwig van Beethoven", "Wolfgang Amadeus Mozart", "Пётр Ильич Чайковский", "Antonio Vivaldi", "Franz Schubert", "Johannes Brahms", "Fryderyk Chopin", "George Frideric Handel"}
    n_cl = sum(1 for r in top if r["nombre_artista"] in clasicos)
    ts = next(r for r in top if r["nombre_artista"] == "Taylor Swift")
    q = next(r for r in top if r["nombre_artista"] == "Queen")
    h += bloque("Top 20 de artistas", "1 minuto", "tabla inferior izquierda.", [
        f"Encabezan {top[0]['nombre_artista']} con {fmt_int(top[0]['lanzamientos_v'])} lanzamientos, {top[1]['nombre_artista']} con {fmt_int(top[1]['lanzamientos_v'])} y {top[2]['nombre_artista']} con {fmt_int(top[2]['lanzamientos_v'])}. De los veinte, {n_cl} son compositores clásicos.",
        "Esto no significa que sean los artistas más escuchados. Significa que su obra se ha editado y reeditado muchísimas veces, por muchos intérpretes y sellos.",
        f"La columna de cobertura muestra otra cosa: los artistas recientes están mejor registrados. {ts['nombre_artista']} llega a {fmt_pct(ts['cobertura_v'])} y {q['nombre_artista']} a {fmt_pct(q['cobertura_v'])}, frente a {fmt_pct(top[0]['cobertura_v'])} de Bach.",
    ], [
        "Este ranking mide presencia en el catálogo, no popularidad.",
        "Tôle-Ache aparece con 38 minutos por pista y 0 % de ISRC: es un perfil atípico que no se investigó. Si preguntan, dígalo así.",
    ])
    h += bloque("Volumen contra digitalización por país", "1 minuto", "dispersión; señale los puntos azules y luego el punto más alto.", [
        f"Cada punto es un país. Los cinco azules son los de mayor volumen, y todos están entre {fmt_pct(min(dd[x] for x in ('United States', 'United Kingdom', 'Japan', 'Germany', 'France')))} y {fmt_pct(max(dd[x] for x in ('United States', 'United Kingdom', 'Japan', 'Germany', 'France')))} digital.",
        f"Lo interesante está arriba: Corea del Sur con {fmt_pct(dd['South Korea'])}, India con {fmt_pct(dd['India'])} y Brasil con {fmt_pct(dd['Brazil'])}. Tienen menos volumen histórico, pero su catálogo registrado es mucho más digital.",
    ], [
        f"Estos porcentajes son históricos y excluyen [Worldwide]. Por eso quedan por debajo de los {fmt_pct(v('k_digital'))} globales: gran parte de lo digital se publica en muchos países a la vez.",
        "Compare países entre sí, no contra el promedio global.",
    ])
    return h


def pagina3(m, c):
    T, L, v = c["T"], c["L"], c["v"]
    E = m["emergentes"]
    dec = c["decadas"]
    total_dec = sum(r["valor"] for r in dec)
    ded = {r["decada"]: r["valor"] for r in dec}
    meses = c["meses"]
    mes_ene = meses[0]["valor"]
    resto = sum(r["valor"] for r in meses[1:])
    oct_ = next(r for r in meses if r["mes_txt"] == 10)
    a = c["areas"]
    emp = {r["tipo_empaque"]: r for r in c["empaque"]}
    fd, fo = c["formatos"]["Digital / Streaming"], c["formatos"]["Físico / Óptico"]
    pv = c["pivot"]
    em = c["emer"]
    jp = sum(1 for r in em if r["pais_artista"] == "Japan")
    d = c["dec_m"]
    h = []
    seccion(h, "Página 3 · 4 minutos, más demostración", "Calidad y catálogo")
    h.append(figura(BUILD / "dash_calidad.png", 15.2, "Parte superior de la página Calidad y catálogo."))
    h += bloque("Las cuatro tarjetas", "20 segundos", "tarjetas superiores.", [
        f"La última página responde qué tan ordenado está el catálogo. Cobertura ISRC de {fmt_pct(v('k_cobertura3'))}, {fmt_dec(v('k_pistas_lanz3'), 1)} pistas por lanzamiento, {fmt_dec(v('k_pistas_sop3'), 1)} por soporte, y {fmt_int(v('k_emergentes'))} artistas emergentes que iniciaron desde 2015.",
    ], [])
    rec = ded["2000s"] + ded["2010s"] + ded["2020s"]
    h += bloque("La línea de tiempo", "45 segundos", "los tres gráficos de la segunda fila.", [
        f"De los {fmt_int(total_dec)} lanzamientos con fecha entre 1900 y 2025, {fmt_pct(rec / total_dec)} se publicó en este siglo. La década más grande es la de 2010 con {fmt_int(ded['2010s'])}. Pero miren los años 2020: ya van {fmt_int(ded['2020s'])} en solo seis años, un ritmo anual {fmt_pct((ded['2020s'] / 6) / (ded['2010s'] / 10) - 1, 0)} mayor.",
        f"En el gráfico por mes hay una trampa. Enero parece gigante, con {fmt_int(mes_ene)}, pero incluye todas las fechas que solo tienen año. Sin enero, los meses se reparten de forma pareja, y octubre es el más alto con {fmt_int(oct_['valor'])}, {fmt_pct(oct_['valor'] / resto)} de los once meses restantes.",
    ], [
        "No concluya que enero es el mes de más lanzamientos: es un efecto de cómo se registran las fechas.",
        f"{fmt_int(m['especiales']['lanzamientos_sin_fecha'])} lanzamientos, {fmt_pct(m['especiales']['lanzamientos_sin_fecha'] / L)}, no tienen fecha y quedan fuera de estos gráficos.",
    ])
    h += bloque("Áreas geográficas", "30 segundos", "Top 15 áreas; señale la barra gris.", [
        f"Esta barra gris es el hallazgo geográfico: [Worldwide], con {fmt_int(a[0]['valor'])} lanzamientos, {fmt_pct(a[0]['valor'] / L)} del catálogo. Es más del doble que Estados Unidos.",
        "No es un país. Son lanzamientos pensados para todo el mundo desde el primer día, otra señal de lo que significa el digital: publicar ya no depende de un territorio.",
    ], [
        "Cuando un lanzamiento salió en 10 o más países el mismo día, se asigna a [Worldwide]. Es una regla del proyecto.",
    ])
    h += bloque("Densidad por empaque", "30 segundos", "barras agrupadas.", [
        f"Las barras indican cuántas pistas trae cada tipo de empaque. Un Jewel Case, la caja clásica de CD, tiene {fmt_dec(emp['Jewel Case']['pistas_lanz'], 1)} pistas por lanzamiento. Sin Embalaje solo {fmt_dec(emp['Sin Embalaje']['pistas_lanz'], 1)}. Lo mismo se ve por formato: {fmt_dec(fd['pistas'] / fd['lanzamientos'], 1)} pistas por lanzamiento en digital contra {fmt_dec(fo['pistas'] / fo['lanzamientos'], 1)} en óptico.",
    ], [
        f"Otro Embalaje marca {fmt_dec(emp['Otro Embalaje']['pistas_lanz'], 1)} pero es una categoría residual. Si la barra llama la atención, aclárelo.",
        f"La diferencia entre las dos barras indica lanzamientos con varios discos: en Gatefold Cover son {fmt_dec(emp['Gatefold Cover']['pistas_lanz'], 1)} frente a {fmt_dec(emp['Gatefold Cover']['pistas_sop'], 1)}.",
    ])
    per = "Persona / Solista"
    h += bloque("Formalización por país", "45 segundos", "mapa de calor; señale la fila de Japón.", [
        f"Cuanto más oscuro, más pistas con código ISRC. Japón sobresale en todas las columnas: {fmt_pct(pv[('Japan', per)])} en solistas y {fmt_pct(pv[('Japan', 'Grupo / Banda')])} en grupos. Estados Unidos tiene {fmt_pct(pv[('United States', per)])} en solistas, y España {fmt_pct(pv[('Spain', per)])}.",
        f"La cobertura también mejora con el tiempo: {fmt_pct(d['1990s']['isrc'])} en los años 1990, {fmt_pct(d['2010s']['isrc'])} en los 2010 y {fmt_pct(d['2020s']['isrc'])} en los 2020. Va en la dirección correcta, pero incluso lo más reciente deja fuera a casi seis de cada diez pistas.",
    ], [
        "Las columnas pequeñas, como Personaje Ficticio, tienen pocos lanzamientos: no las use como conclusión.",
        "Un ISRC ausente en MusicBrainz no significa que no exista: puede no estar registrado en el catálogo.",
    ])
    h += bloque("Talento emergente", "30 segundos", "tabla inferior derecha.", [
        f"Hay {fmt_int(E['total'])} artistas que iniciaron desde 2015, y {fmt_int(E['isrc_100'])}, {fmt_pct(E['isrc_100'] / E['total'])}, tienen todas sus pistas con ISRC. Esta tabla muestra a los de mayor volumen. Encabezan {em[0]['nombre_artista']} y {em[1]['nombre_artista']} con {em[0]['lanzamientos_v']} lanzamientos, y {jp} de los {len(em)} son de Japón.",
    ], [
        "Son 16 filas y no 15 por un empate en la posición.",
        "Compare también la columna de pistas: algunos tienen casi una pista por lanzamiento.",
    ])
    h.append(P("Demostración en vivo: drill-down", "h2"))
    h.append(senalar("tablas de drill-down, al final de la página. Es el momento de mostrar que el dashboard se puede explorar."))
    h.append(decir("Si una cifra les genera una pregunta, podemos bajar de nivel aquí mismo. Déjenme mostrarles."))
    h.append(tabla([
        ["Paso", "Qué hacer", "Qué debe aparecer"],
        ["1", "Clic derecho en <b>Siglo XX</b> y luego <b>Drill down</b>", f"Cobertura {fmt_pct(DEMO_SIGLO_XX['isrc'])}, {fmt_dec(DEMO_SIGLO_XX['por_lanzamiento'], 1)} pistas por lanzamiento, {fmt_dec(DEMO_SIGLO_XX['por_soporte'], 1)} por soporte"],
        ["2", "Pulse <b>Drill up</b> en el encabezado de la tabla", f"Vuelve a {fmt_pct(T['isrc_pct'])}"],
        ["3", "Clic en la barra <b>2010s</b> del primer gráfico", f"Cobertura {fmt_pct(DEMO_2010S['isrc'])}, {fmt_dec(DEMO_2010S['por_lanzamiento'], 1)} pistas por lanzamiento, {fmt_dec(DEMO_2010S['por_soporte'], 1)} por soporte"],
        ["4", "Quite la selección; si no vuelve, recargue la página", f"Vuelve a {fmt_pct(T['isrc_pct'])}"],
    ], [1.2, 8.0, 7.7]))
    h.append(Spacer(1, 6))
    h.append(aviso(
        f"Si prefiere la primera página: en el filtro <b>Año</b> escriba 2000 y 2010. Debe ver {fmt_int(DEMO_ANIOS['lanzamientos'])} lanzamientos, {fmt_int(DEMO_ANIOS['pistas'])} pistas, "
        f"{fmt_int(DEMO_ANIOS['artistas'])} artistas, {fmt_pct(DEMO_ANIOS['isrc'])} de ISRC y {fmt_pct(DEMO_ANIOS['digital'])} digital.", "Alternativa", AZUL))
    return h


def cierre(m, c):
    T, L = c["T"], c["L"]
    u = m["ultimo_anio"]
    d = c["dec_m"]
    dd = {r["nombre_pais"]: r["participacion_digital"] for r in c["disp"]}
    sin_cal = next(r for r in m["calidad"] if r["calidad"] == "Sin calificar")["lanzamientos"]
    h = []
    seccion(h, "Cierre · 1 minuto", "Conclusiones y siguientes pasos")
    h.append(decir(
        f"Para cerrar, cuatro ideas. Uno: la música que se publica hoy es digital, con {fmt_pct(u['digital'])} en {u['anio']}. Dos: se publica para el mundo, con {fmt_pct(m['especiales']['lanzamientos_worldwide'] / L)} del catálogo sin un país único. "
        f"Tres: sigue pendiente la formalización, con {fmt_pct(T['isrc_pct'])} de cobertura. Y cuatro: estas cifras son confiables porque cada una se concilió con la fuente."))
    h.append(decir("Ahora bien, ¿qué haríamos con esto? Les propongo cuatro líneas de trabajo, y quedo atento a sus preguntas."))
    h.append(tabla([
        ["Línea de trabajo", "Evidencia", "Precaución"],
        ["Tratar lo digital como el canal base", f"{fmt_pct(u['digital'])} de los lanzamientos de {u['anio']}", "Mide publicación, no ingresos"],
        ["Impulsar el registro de ISRC", f"{fmt_pct(1 - T['isrc_pct'])} de las pistas sin código; {fmt_pct(d['2020s']['isrc'])} en los años 2020", "Puede existir el código y no estar registrado"],
        ["Observar mercados muy digitales", f"Corea del Sur {fmt_pct(dd['South Korea'])}, India {fmt_pct(dd['India'])}, Brasil {fmt_pct(dd['Brazil'])}", "Indica dónde mirar; requiere datos de mercado"],
        ["Mejorar la calificación de datos", f"{fmt_pct(sin_cal / L)} de los lanzamientos sin calificar", "Depende de la comunidad de MusicBrainz"],
    ], [5.2, 6.4, 5.3], primera_negrita=True))
    h.append(aviso(
        "Estas líneas son propuestas de análisis a partir del catálogo. Si la junta las necesita para decidir inversión, deben contrastarse con ventas, regalías o reproducciones.",
        "Lo que no debe prometer", DURAZNO))
    return h


def preguntas(m, c):
    T, L = c["T"], c["L"]
    P13 = next(r for r in m["pearson"] if r["inicio"] == 2013)
    h = []
    seccion(h, "Preguntas", "Preguntas probables de la junta")
    bloques = [
        ("¿Estos datos son nuestras ventas?", "No. Son el catálogo público de MusicBrainz. Miden lo publicado y registrado, no lo vendido ni lo escuchado."),
        ("¿Qué tan confiables son?", f"Las {fmt_int(T['pistas'])} pistas coinciden con el volcado original, y el dashboard se comparó con consultas directas. La confiabilidad técnica es alta; la limitación está en lo que la comunidad registró."),
        ("¿Por qué los totales de los gráficos no coinciden entre sí?", f"Cada gráfico aplica su propio rango. El de años cubre 1950 a 2025 y los lanzamientos sin fecha quedan fuera. El total general es {fmt_int(L)}."),
        ("¿Por qué 2025 baja?", "Puede ser un efecto del registro: los lanzamientos recientes siguen agregándose. No lo interprete como una caída de la industria."),
        ("¿El streaming acortó las canciones?", f"No queda demostrado. La correlación reciente es {fmt_signo(P13['r'])}, no significativa con {P13['n']} años."),
        ("¿Por qué Estados Unidos solo tiene 24 % digital si el global es 50 %?", "Porque gran parte de lo digital se publica en muchos países a la vez y se asigna a [Worldwide]. La comparación válida es entre países."),
        ("¿Por qué Bach supera a artistas actuales?", "Porque el ranking cuenta ediciones. Su obra tiene siglos de reediciones e intérpretes."),
        ("¿Qué es exactamente el ISRC?", "Es un código internacional que identifica cada grabación. Facilita rastrear su uso y el pago de regalías."),
        ("¿Por qué ya no usan Power BI?", "El dashboard de Databricks trabaja directamente sobre los datos completos, sin importar millones de filas a un equipo local."),
        ("¿Se puede llegar al detalle por día?", "No. El drill-down llega hasta mes, y muchas fechas ni siquiera tienen día registrado."),
        ("¿Los datos están actualizados?", f"Corresponden al volcado de MusicBrainz {m['version_volcado'][:8]}. Actualizarlos requiere cargar un volcado nuevo y ejecutar el pipeline."),
    ]
    h.append(tabla([["Pregunta", "Respuesta sugerida"]] + [list(b) for b in bloques], [6.0, 10.9], primera_negrita=True))
    h.append(Spacer(1, 8))
    h.append(aviso("Si no sabe una respuesta, dígalo y ofrezca revisarla con el dashboard. Eso genera más confianza que improvisar una causa.", "Regla práctica", MENTA))
    return h


def anexo(m, c):
    L = c["L"]
    h = []
    seccion(h, "Anexo", "Cifras completas por gráfico")
    h.append(P("Tablas de consulta durante las preguntas. Los porcentajes de lanzamientos se calculan sobre el total de " + fmt_int(L) + ".", "body_muted"))
    h.append(P("Formatos", "h3"))
    h.append(tabla([["Categoría", "Lanzamientos", "% lanzamientos", "Pistas"]] + [
        [r["categoria"], fmt_int(r["lanzamientos"]), fmt_pct(r["lanzamientos"] / L), fmt_int(r["pistas"])] for r in sorted(m["formatos"], key=lambda r: -r["lanzamientos"])
    ], [6.4, 3.6, 3.3, 3.6], primera_negrita=True))
    h.append(P("Cuota anual", "h3"))
    h.append(tabla([["Año", "Lanzamientos", "Digital", "Óptico"]] + [
        [a, fmt_int(c["tot"][a]), fmt_pct(c["cuota"][a]["digital"]), fmt_pct(c["cuota"][a]["cd"])] for a in (1990, 1995, 2000, 2005, 2010, 2011, 2012, 2015, 2020, 2021, 2022, 2023, 2024, 2025)
    ], [3.0, 5.0, 4.4, 4.5], primera_negrita=True))
    h.append(P("Décadas", "h3"))
    h.append(tabla([["Década", "Lanzamientos", "Digital", "Óptico", "Vinilo", "ISRC", "Duración (min)"]] + [
        [r["decada"], fmt_int(r["lanzamientos"]), fmt_pct(r["digital"]), fmt_pct(r["optico"]), fmt_pct(r["vinilo"]), fmt_pct(r["isrc"]), fmt_dec(r["dur_media_min"], 2)] for r in m["decadas"]
    ], [2.2, 3.1, 2.2, 2.2, 2.2, 2.2, 2.8], primera_negrita=True))
    h.append(P("Top 15 áreas", "h3"))
    h.append(tabla([["#", "Área", "Tipo", "Lanzamientos", "%"]] + [
        [i + 1, r["nombre_area"], r["tipo_area"], fmt_int(r["valor"]), fmt_pct(r["valor"] / L)] for i, r in enumerate(c["areas"])
    ], [1.1, 5.4, 4.8, 3.3, 2.3]))
    h.append(P("Idiomas y tipo de artista", "h3"))
    filas = [["Idioma", "Lanzamientos", "%", "Tipo de artista", "Lanzamientos", "%"]]
    ids, tp = c["idiomas"], c["tipos"]
    for i in range(max(len(ids), len(tp))):
        a = [ids[i]["nombre_idioma"], fmt_int(ids[i]["valor"]), fmt_pct(ids[i]["valor"] / L)] if i < len(ids) else ["", "", ""]
        b = [tp[i]["tipo_artista"], fmt_int(tp[i]["valor"]), fmt_pct(tp[i]["valor"] / L)] if i < len(tp) else ["", "", ""]
        filas.append(a + b)
    h.append(tabla(filas, [3.9, 2.4, 1.6, 4.3, 2.8, 1.9]))
    h.append(P("Duración de las pistas", "h3"))
    H = m["histograma"]
    h.append(tabla([["Banda", "Pistas", "%"]] + [[r["banda"], fmt_int(r["pistas"]), fmt_pct(r["pistas"] / H["total"])] for r in H["bandas"]], [5.0, 6.0, 5.9], primera_negrita=True))
    h.append(P("Top 20 artistas", "h3"))
    h.append(tabla([["#", "Artista", "Lanzamientos", "Pistas", "Min", "ISRC"]] + [
        [i + 1, r["nombre_artista"], fmt_int(r["lanzamientos_v"]), fmt_int(r["pistas_v"]), fmt_dec(r["duracion_v"], 2), fmt_pct(r["cobertura_v"])] for i, r in enumerate(c["top"])
    ], [1.0, 6.5, 2.8, 2.6, 1.9, 2.1]))
    h.append(P("Participación digital del Top 30 de países", "h3"))
    dis = c["disp"]
    mitad = (len(dis) + 1) // 2
    filas = [["País", "Lanzamientos", "Digital", "País", "Lanzamientos", "Digital"]]
    for i in range(mitad):
        a = dis[i]
        b = dis[i + mitad] if i + mitad < len(dis) else None
        filas.append([a["nombre_pais"], fmt_int(10 ** a["lanzamientos_log10"]), fmt_pct(a["participacion_digital"])] + ([b["nombre_pais"], fmt_int(10 ** b["lanzamientos_log10"]), fmt_pct(b["participacion_digital"])] if b else ["", "", ""]))
    h.append(tabla(filas, [3.5, 2.8, 2.1, 3.5, 2.9, 2.1]))
    h.append(P("Cobertura ISRC por país y tipo de artista", "h3"))
    tipos = ["Persona / Solista", "Grupo / Banda", "Orquesta", "Coro", "Otro", "No Clasificado"]
    paises = sorted({k[0] for k in c["pivot"]}, key=lambda p: -c["pivot"].get((p, "Persona / Solista"), 0))
    h.append(tabla([["País", "Solista", "Grupo", "Orquesta", "Coro", "Otro", "Sin clasificar"]] + [
        [p] + [fmt_pct(c["pivot"].get((p, t), 0)) for t in tipos] for p in paises
    ], [4.0, 2.1, 2.1, 2.2, 2.0, 2.0, 2.5], primera_negrita=True))
    h.append(P("Lanzamientos por mes", "h3"))
    ms = c["meses"]
    h.append(tabla([["Mes", "Lanzamientos", "Trimestre"]] + [[f"{r['mes_txt']:02d}", fmt_int(r["valor"]), r["nombre_trimestre"]] for r in ms], [5.0, 6.0, 5.9], primera_negrita=True))
    h.append(P("Empaque (Top 8)", "h3"))
    h.append(tabla([["Empaque", "Pistas por lanzamiento", "Pistas por soporte"]] + [[r["tipo_empaque"], fmt_dec(r["pistas_lanz"], 1), fmt_dec(r["pistas_sop"], 1)] for r in c["empaque"]], [7.0, 5.0, 4.9], primera_negrita=True))
    return h


def main():
    salida = Path(sys.argv[1]) if len(sys.argv) > 1 else SALIDA
    m = metricas()
    c = ctx(m, datos())
    portada = portada_factory(
        ["Guion para la", "junta directiva"],
        ["Explicación del dashboard, con cifras y análisis", f"{fmt_int(m['totales']['pistas'])} pistas · Databricks AI/BI"],
        ["Juan Sebastián Rincón Farelo", "Integrantes: Juan Rincón, Sebastián Russo, Jesús Figueroa", "Docente: Amilkar Sierra Romano",
         "Ingeniería de Sistemas · Universidad Popular del Cesar", "Valledupar, noviembre de 2026"],
    )
    doc = Documento(salida, "DWMusicBrainz · Guion para la junta directiva", portada, title="DWMusicBrainz · Guion para la junta directiva",
                    author="Juan Sebastián Rincón Farelo", subject="Explicación del dashboard")
    historia = [Spacer(1, 1), NextPageTemplate("normal"), PageBreak(), P("Índice", "h1_indice"), indice(1), PageBreak()]
    historia += resumen(m, c) + pagina1(m, c) + pagina2(m, c) + pagina3(m, c) + cierre(m, c) + preguntas(m, c) + anexo(m, c)
    doc.multiBuild(historia)
    print(f"[OK] {salida}")


if __name__ == "__main__":
    main()
