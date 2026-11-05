"""
doc_pdf_comun.py
================
Estilos, diagramas y gráficos compartidos por los PDF de defensa y de documentación.
Las cifras llegan siempre desde docs/build/metricas_databricks.json.

Dependencias: reportlab, matplotlib.
"""

import json
import os
import tempfile
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from reportlab.graphics.shapes import Drawing, Line, Polygon, Rect, String
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    Image,
    KeepTogether,
    NextPageTemplate,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.platypus.tableofcontents import TableOfContents

BASE_DIR = Path(__file__).resolve().parent.parent
BUILD = BASE_DIR / "docs" / "build"
TEMP = Path(tempfile.mkdtemp(prefix="dwmb_doc_"))

INK = colors.HexColor("#23324A")
MUTED = colors.HexColor("#56647A")
HAIRLINE = colors.HexColor("#E3E7ED")
PANEL = colors.HexColor("#F3F6FB")
AZUL = colors.HexColor("#DCE9F8")
MENTA = colors.HexColor("#DAF2E8")
DURAZNO = colors.HexColor("#FCE6D8")
LAVANDA = colors.HexColor("#E9E3F7")
AMARILLO = colors.HexColor("#FFF3CF")
BLANCO = colors.white

# Paleta del dashboard: se repite aquí para que los gráficos coincidan con lo que se presenta.
SERIE = {"azul": "#1F5FA8", "naranja": "#C2691A", "menta": "#08A08C", "lavanda": "#8064B5", "gris": "#9AA5B1", "claro": "#D5DAE1", "suave": "#A9BDD3"}
COLOR_FORMATO = {
    "Digital / Streaming": SERIE["azul"], "Físico / Óptico": SERIE["naranja"], "Físico / Vinilo": SERIE["menta"],
    "Físico / Magnético": SERIE["lavanda"], "Otros Formatos": SERIE["gris"], "Desconocido": SERIE["claro"],
}

FUENTES = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "Fonts"
ARCHIVOS = {"Body": "segoeui.ttf", "Body-Bold": "segoeuib.ttf", "Body-Italic": "segoeuii.ttf", "Body-Semibold": "seguisb.ttf", "Mono": "consola.ttf"}


def registrar_fuentes():
    if all((FUENTES / a).exists() for a in ARCHIVOS.values()):
        for nombre, archivo in ARCHIVOS.items():
            pdfmetrics.registerFont(TTFont(nombre, str(FUENTES / archivo)))
        pdfmetrics.registerFontFamily("Body", normal="Body", bold="Body-Bold", italic="Body-Italic", boldItalic="Body-Bold")
        return {"regular": "Body", "bold": "Body-Bold", "italic": "Body-Italic", "semibold": "Body-Semibold", "mono": "Mono"}
    return {"regular": "Helvetica", "bold": "Helvetica-Bold", "italic": "Helvetica-Oblique", "semibold": "Helvetica-Bold", "mono": "Courier"}


F = registrar_fuentes()
plt.rcParams.update({
    "font.family": "Segoe UI", "font.size": 10, "axes.edgecolor": "#C8D0DA", "axes.labelcolor": "#56647A",
    "xtick.color": "#56647A", "ytick.color": "#56647A", "axes.spines.top": False, "axes.spines.right": False,
})


def metricas():
    ruta = BUILD / "metricas_databricks.json"
    if not ruta.exists():
        raise SystemExit("Falta docs/build/metricas_databricks.json. Ejecute generar_metricas_databricks.py.")
    return json.loads(ruta.read_text(encoding="utf-8"))


def dashboard():
    return json.loads((BASE_DIR / "databricks" / "dashboards" / "DWMusicBrainz.lvdash.json").read_text(encoding="utf-8"))


def fmt_int(n):
    return f"{round(n):,}".replace(",", ".")


def fmt_dec(x, d=2):
    return f"{x:.{d}f}".replace(".", ",")


def fmt_pct(x, d=1):
    return f"{fmt_dec(x * 100, d)} %"


def fmt_signo(x, d=3):
    return ("+" if x >= 0 else "−") + fmt_dec(abs(x), d)


def fmt_mill(n, d=1):
    return f"{fmt_dec(n / 1e6, d)} M"


def fmt_mmss(minutos):
    total = round(minutos * 60)
    return f"{total // 60}:{total % 60:02d}"


def fmt_gb(b):
    if b < 1e6:
        return "< 1 MB"
    if b < 1e8:
        return f"{fmt_int(b / 1e6)} MB"
    return f"{fmt_dec(b / 1e9, 2)} GB"


def code(t):
    return f"<font name='{F['mono']}' size='8.6'>{t}</font>"


def estilos():
    s = {}
    base = dict(fontName=F["regular"], textColor=INK)
    s["body"] = ParagraphStyle("body", fontSize=9.8, leading=14.6, spaceAfter=6, **base)
    s["body_muted"] = ParagraphStyle("body_muted", parent=s["body"], textColor=MUTED, fontSize=9.2, leading=13.4)
    s["bullet"] = ParagraphStyle("bullet", parent=s["body"], leftIndent=13, bulletIndent=2, spaceAfter=3.5)
    s["h1"] = ParagraphStyle("h1", fontName=F["bold"], fontSize=17, leading=22, textColor=INK, spaceBefore=4, spaceAfter=12, backColor=AZUL, borderPadding=(7, 10, 8, 10), borderRadius=7, leftIndent=10, rightIndent=10, keepWithNext=1)
    s["h1_indice"] = ParagraphStyle("h1_indice", parent=s["h1"])
    s["kicker"] = ParagraphStyle("kicker", fontName=F["semibold"], fontSize=9.5, leading=12, textColor=MUTED, spaceAfter=9, keepWithNext=1)
    s["h2"] = ParagraphStyle("h2", fontName=F["bold"], fontSize=12.4, leading=16, textColor=INK, spaceBefore=10, spaceAfter=5, keepWithNext=1)
    s["h3"] = ParagraphStyle("h3", fontName=F["semibold"], fontSize=10.4, leading=14, textColor=INK, spaceBefore=7, spaceAfter=3, keepWithNext=1)
    s["caption"] = ParagraphStyle("caption", fontName=F["italic"], fontSize=8.6, leading=11.5, textColor=MUTED, spaceBefore=2, spaceAfter=9, alignment=TA_CENTER)
    s["cell"] = ParagraphStyle("cell", fontName=F["regular"], fontSize=8.7, leading=11.8, textColor=INK)
    s["cell_b"] = ParagraphStyle("cell_b", parent=s["cell"], fontName=F["semibold"])
    s["cell_h"] = ParagraphStyle("cell_h", parent=s["cell"], fontName=F["bold"])
    s["kpi_v"] = ParagraphStyle("kpi_v", fontName=F["bold"], fontSize=15, leading=18, textColor=INK, alignment=TA_CENTER)
    s["kpi_l"] = ParagraphStyle("kpi_l", fontName=F["regular"], fontSize=8.1, leading=10.4, textColor=MUTED, alignment=TA_CENTER)
    s["call"] = ParagraphStyle("call", parent=s["body"], spaceAfter=0, fontSize=9.5, leading=14)
    s["toc1"] = ParagraphStyle("toc1", fontName=F["semibold"], fontSize=10.4, leading=17, textColor=INK)
    s["toc2"] = ParagraphStyle("toc2", fontName=F["regular"], fontSize=9.2, leading=13.5, textColor=MUTED, leftIndent=14)
    s["script_time"] = ParagraphStyle("script_time", fontName=F["bold"], fontSize=10, leading=14, textColor=INK, spaceBefore=6)
    s["script_say"] = ParagraphStyle("script_say", fontName=F["italic"], fontSize=9.7, leading=14.5, textColor=INK, spaceAfter=4, leftIndent=8)
    s["portada_t"] = ParagraphStyle("portada_t", fontName=F["bold"], fontSize=31, leading=37, textColor=INK, alignment=TA_LEFT)
    return s


S = estilos()


def P(texto, estilo="body"):
    return Paragraph(texto, S[estilo])


def vinetas(items):
    return [Paragraph(t, S["bullet"], bulletText="•") for t in items]


def tabla(datos, anchos, encabezado=True, primera_negrita=False, fondo=AZUL, repetir=True):
    filas = []
    for i, fila in enumerate(datos):
        celdas = []
        for j, c in enumerate(fila):
            if i == 0 and encabezado:
                est = "cell_h"
            elif j == 0 and primera_negrita:
                est = "cell_b"
            else:
                est = "cell"
            celdas.append(Paragraph(str(c), S[est]))
        filas.append(celdas)
    t = Table(filas, colWidths=[a * cm for a in anchos], repeatRows=1 if encabezado and repetir else 0, hAlign="LEFT")
    orden = [
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LINEBELOW", (0, 0), (-1, -1), 0.4, HAIRLINE),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 3.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]
    if encabezado:
        orden.append(("BACKGROUND", (0, 0), (-1, 0), fondo))
    for i in range(2 if encabezado else 1, len(filas), 2):
        orden.append(("BACKGROUND", (0, i), (-1, i), PANEL))
    t.setStyle(TableStyle(orden))
    return t


def aviso(texto, titulo=None, tono=None):
    contenido = [P(f"<b>{titulo}</b>", "h3")] if titulo else []
    contenido.append(P(texto, "call"))
    t = Table([[contenido]], colWidths=[16.9 * cm], hAlign="LEFT")
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), tono or AMARILLO),
        ("ROUNDEDCORNERS", [6, 6, 6, 6]),
        ("LEFTPADDING", (0, 0), (-1, -1), 11), ("RIGHTPADDING", (0, 0), (-1, -1), 11),
        ("TOPPADDING", (0, 0), (-1, -1), 8), ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
    ]))
    return KeepTogether([Spacer(1, 3), t, Spacer(1, 8)])


def rejilla_kpi(items, columnas=4):
    tonos = [AZUL, MENTA, DURAZNO, LAVANDA]
    filas, fila = [], []
    for valor, etiqueta in items:
        fila.append([P(valor, "kpi_v"), Spacer(1, 2), P(etiqueta, "kpi_l")])
        if len(fila) == columnas:
            filas.append(fila)
            fila = []
    if fila:
        filas.append(fila + [""] * (columnas - len(fila)))
    t = Table(filas, colWidths=[16.9 / columnas * cm] * columnas, hAlign="LEFT")
    orden = [
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("LEFTPADDING", (0, 0), (-1, -1), 5), ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 9), ("BOTTOMPADDING", (0, 0), (-1, -1), 10), ("LINEAFTER", (0, 0), (-2, -1), 4, BLANCO),
        ("LINEBELOW", (0, 0), (-1, -2), 4, BLANCO),
    ]
    for r in range(len(filas)):
        for c in range(columnas):
            orden.append(("BACKGROUND", (c, r), (c, r), tonos[(r + c) % 4]))
    t.setStyle(TableStyle(orden))
    return t


def figura(ruta, ancho_cm=16.9, pie=None):
    from PIL import Image as Pil

    with Pil.open(ruta) as i:
        w, h = i.size
    elementos = [Image(str(ruta), width=ancho_cm * cm, height=ancho_cm * cm * h / w, hAlign="CENTER")]
    if pie:
        elementos.append(P(pie, "caption"))
    return KeepTogether(elementos)


def guardar(fig, nombre):
    ruta = TEMP / f"{nombre}.png"
    fig.savefig(ruta, dpi=190, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return ruta


def g_cuota(m):
    a = [x for x in m["anual"] if x["anio"] >= 1990]
    fig, ax = plt.subplots(figsize=(8.6, 3.2))
    anios = [x["anio"] for x in a]
    ax.plot(anios, [x["digital"] * 100 for x in a], color=SERIE["azul"], lw=2.4)
    ax.plot(anios, [x["optico"] * 100 for x in a], color=SERIE["naranja"], lw=2.4)
    ax.axvline(m["cruce_digital"], color="#C8D0DA", lw=1)
    ax.text(m["cruce_digital"] + 0.4, 96, f"Cruce: {m['cruce_digital']}", color="#23324A", fontsize=10)
    ax.text(2025.4, a[-1]["digital"] * 100, "Digital", color=SERIE["azul"], va="center", fontweight="bold")
    ax.text(2025.4, a[-1]["optico"] * 100, "Óptico", color=SERIE["naranja"], va="center", fontweight="bold")
    ax.set_ylim(0, 100)
    ax.set_xlim(1990, 2031)
    ax.set_xticks(range(1990, 2026, 5))
    ax.set_ylabel("% de lanzamientos del año")
    ax.yaxis.grid(True, color="#EDF0F4")
    ax.set_axisbelow(True)
    return guardar(fig, "cuota")


def g_mezcla(m):
    d = m["decadas"]
    fig, ax = plt.subplots(figsize=(8.6, 3.2))
    x = [r["decada"] for r in d]
    fondo = [0] * len(d)
    for clave, nombre in [("vinilo", "Físico / Vinilo"), ("optico", "Físico / Óptico"), ("magnetico", "Físico / Magnético"), ("digital", "Digital / Streaming")]:
        v = [r[clave] * 100 for r in d]
        ax.bar(x, v, bottom=fondo, color=COLOR_FORMATO[nombre], label=nombre, width=0.72, edgecolor="white", linewidth=1)
        fondo = [f + y for f, y in zip(fondo, v)]
    resto = [100 - f for f in fondo]
    ax.bar(x, resto, bottom=fondo, color=SERIE["claro"], label="Otros y desconocido", width=0.72, edgecolor="white", linewidth=1)
    ax.set_ylim(0, 100)
    ax.set_ylabel("% de lanzamientos de la década")
    ax.legend(frameon=False, bbox_to_anchor=(1.01, 1), loc="upper left", fontsize=9)
    return guardar(fig, "mezcla")


def g_histograma(m):
    h = m["histograma"]
    b = h["bandas"]
    dos = sorted(b, key=lambda r: r["pistas"], reverse=True)[:2]
    fig, ax = plt.subplots(figsize=(8.6, 3.0))
    ax.bar([r["banda"].split("–")[0] for r in b], [r["pistas"] / 1e6 for r in b],
           color=[SERIE["azul"] if r in dos else SERIE["suave"] for r in b], width=0.92)
    ax.set_ylabel("Millones de pistas")
    ax.set_xlabel("Inicio de la banda de 30 s (min:s)")
    ax.tick_params(axis="x", rotation=55, labelsize=8.5)
    ax.yaxis.grid(True, color="#EDF0F4")
    ax.set_axisbelow(True)
    return guardar(fig, "histograma")


def g_paises(m):
    filas = [("[Worldwide]", m["especiales"]["lanzamientos_worldwide"], SERIE["gris"])]
    for i, p in enumerate(m["paises"][:9]):
        filas.append((p["pais"], p["lanzamientos"], SERIE["azul"] if i == 0 else SERIE["suave"]))
    filas.reverse()
    fig, ax = plt.subplots(figsize=(8.6, 3.2))
    ax.barh([f[0] for f in filas], [f[1] for f in filas], color=[f[2] for f in filas], height=0.72)
    tope = max(f[1] for f in filas)
    for i, f in enumerate(filas):
        ax.text(f[1] + tope * 0.008, i, fmt_int(f[1]), va="center", fontsize=9, color="#23324A")
    ax.xaxis.set_visible(False)
    ax.spines["bottom"].set_visible(False)
    ax.set_xlim(0, tope * 1.13)
    return guardar(fig, "paises")


def g_dispersion(m):
    import math

    paises = m["paises"]
    fig, ax = plt.subplots(figsize=(8.6, 3.5))
    for i, p in enumerate(paises):
        ax.scatter(math.log10(p["lanzamientos"]), p["digital"] * 100, s=42 if i < 5 else 28,
                   color=SERIE["azul"] if i < 5 else SERIE["suave"], zorder=3)
    for nombre in ("United States", "South Korea", "India", "Brazil", "Germany"):
        p = next(x for x in paises if x["pais"] == nombre)
        ax.annotate(nombre, (math.log10(p["lanzamientos"]), p["digital"] * 100), xytext=(6, 4), textcoords="offset points", fontsize=9, color="#23324A")
    ax.set_xlabel("Lanzamientos (log₁₀)")
    ax.set_ylabel("% digital")
    ax.yaxis.grid(True, color="#EDF0F4")
    ax.set_axisbelow(True)
    return guardar(fig, "dispersion")


def g_tareas(m, nombres):
    tareas = {t["tarea"]: t["segundos"] for t in m["corridas"]["completa"]["tareas"]}
    filas = [(et, tareas[k]) for k, et in nombres][::-1]
    fig, ax = plt.subplots(figsize=(8.6, 2.8))
    ax.barh([f[0] for f in filas], [f[1] for f in filas], color=SERIE["menta"], height=0.68)
    for i, f in enumerate(filas):
        ax.text(f[1] + 2, i, f"{f[1]} s", va="center", fontsize=9, color="#23324A")
    ax.xaxis.set_visible(False)
    ax.spines["bottom"].set_visible(False)
    return guardar(fig, "tareas")


def _caja(d, x, y, w, h, relleno, titulo, sub=None, tam=9):
    d.add(Rect(x, y, w, h, rx=6, ry=6, fillColor=relleno, strokeColor=None))
    d.add(String(x + w / 2, y + h - 16, titulo, fontName=F["bold"], fontSize=tam, fillColor=INK, textAnchor="middle"))
    if sub:
        for i, linea in enumerate(sub):
            d.add(String(x + w / 2, y + h - 29 - i * 10.5, linea, fontName=F["regular"], fontSize=7.8, fillColor=MUTED, textAnchor="middle"))


def diagrama_arquitectura(m):
    d = Drawing(480, 205)
    etapas = [
        ("Volcado", ["7,7 GB", "SHA-256"], AMARILLO),
        ("Volume", ["archivos", "crudos"], DURAZNO),
        ("Bronze", [fmt_mill(m["conteos"]["silver_principales_total"], 2), "todo texto"], LAVANDA),
        ("Silver", ["tipos, escapes", "y calidad"], AZUL),
        ("Gold", ["3 hechos,", "7 dimensiones"], MENTA),
        ("Consumo", ["AI/BI y", "Power BI"], DURAZNO),
    ]
    w, h, salto = 68, 74, 82.4
    for i, (t, s, c) in enumerate(etapas):
        x = i * salto
        _caja(d, x, 120, w, h, c, t, s)
        if i < len(etapas) - 1:
            d.add(Polygon([x + w + 3, 151, x + w + 3, 163, x + w + 11, 157], fillColor=colors.HexColor("#A9B4C2"), strokeColor=None))
    _caja(d, 0, 62, 480, 42, PANEL, "Lakeflow Jobs", ["pruebas → bronze → silver → catálogos → dimensiones → hecho de pista → agregados → validación"])
    _caja(d, 0, 6, 235, 46, PANEL, "Unity Catalog", ["catálogo workspace: landing, bronze, silver, gold y meta"])
    _caja(d, 245, 6, 235, 46, PANEL, "Esquema meta", ["etl_audit y data_quality_log"])
    return d


def diagrama_estrella(m):
    g = m["conteos"]["gold"]
    d = Drawing(480, 232)
    cx, cy, cw, ch = 158, 82, 164, 70
    d.add(Rect(cx, cy, cw, ch, rx=6, ry=6, fillColor=AZUL, strokeColor=None))
    d.add(String(cx + cw / 2, cy + 49, "fact_pista", fontName=F["bold"], fontSize=11, fillColor=INK, textAnchor="middle"))
    d.add(String(cx + cw / 2, cy + 33, f"{fmt_int(g['fact_pista'])} filas", fontName=F["regular"], fontSize=9, fillColor=MUTED, textAnchor="middle"))
    d.add(String(cx + cw / 2, cy + 18, f"fact_produccion_musical: {fmt_int(g['fact_produccion_musical'])}", fontName=F["regular"], fontSize=7.6, fillColor=MUTED, textAnchor="middle"))
    d.add(String(cx + cw / 2, cy + 7, f"fact_distribucion_duracion: {fmt_int(g['fact_distribucion_duracion'])}", fontName=F["regular"], fontSize=7.6, fillColor=MUTED, textAnchor="middle"))
    dims = [
        ("dim_fecha", g["dim_fecha"], 0, 172), ("dim_artista", g["dim_artista"], 180, 172), ("dim_geografia", g["dim_geografia"], 360, 172),
        ("dim_formato", g["dim_formato"], 0, 86), ("dim_idioma", g["dim_idioma"], 360, 86),
        ("dim_lanzamiento", g["dim_lanzamiento"], 0, 0), ("dim_rango_duracion", g["dim_rango_duracion"], 360, 0),
    ]
    for nombre, n, x, y in dims:
        xc, yc = x + 60, y + 25
        d.add(Line(xc, yc, cx + cw / 2, cy + ch / 2, strokeColor=colors.HexColor("#C8D0DA"), strokeWidth=0.8))
    d.add(Rect(cx, cy, cw, ch, rx=6, ry=6, fillColor=AZUL, strokeColor=None))
    d.add(String(cx + cw / 2, cy + 49, "fact_pista", fontName=F["bold"], fontSize=11, fillColor=INK, textAnchor="middle"))
    d.add(String(cx + cw / 2, cy + 33, f"{fmt_int(g['fact_pista'])} filas", fontName=F["regular"], fontSize=9, fillColor=MUTED, textAnchor="middle"))
    d.add(String(cx + cw / 2, cy + 18, f"fact_produccion_musical: {fmt_int(g['fact_produccion_musical'])}", fontName=F["regular"], fontSize=7.6, fillColor=MUTED, textAnchor="middle"))
    d.add(String(cx + cw / 2, cy + 7, f"fact_distribucion_duracion: {fmt_int(g['fact_distribucion_duracion'])}", fontName=F["regular"], fontSize=7.6, fillColor=MUTED, textAnchor="middle"))
    tonos = [MENTA, LAVANDA, DURAZNO, AMARILLO, MENTA, LAVANDA, DURAZNO]
    for (nombre, n, x, y), c in zip(dims, tonos):
        d.add(Rect(x, y, 120, 50, rx=6, ry=6, fillColor=c, strokeColor=None))
        d.add(String(x + 60, y + 30, nombre, fontName=F["bold"], fontSize=9, fillColor=INK, textAnchor="middle"))
        d.add(String(x + 60, y + 15, f"{fmt_int(n)} filas", fontName=F["regular"], fontSize=8, fillColor=MUTED, textAnchor="middle"))
    return d


class Documento(BaseDocTemplate):
    def __init__(self, ruta, titulo_corto, portada, **kw):
        super().__init__(str(ruta), pagesize=A4, leftMargin=2.05 * cm, rightMargin=2.05 * cm, topMargin=1.9 * cm, bottomMargin=2.0 * cm, **kw)
        self.titulo_corto = titulo_corto
        marco = Frame(self.leftMargin, self.bottomMargin, self.width, self.height, id="f", leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
        self.addPageTemplates([
            PageTemplate(id="portada", frames=[marco], onPage=portada),
            PageTemplate(id="normal", frames=[marco], onPage=self._pie),
        ])
        self._marcador = 0

    def beforeDocument(self):
        self._marcador = 0

    def _pie(self, canv, doc):
        canv.saveState()
        canv.setFont(F["regular"], 8)
        canv.setFillColor(MUTED)
        canv.drawString(self.leftMargin, 1.15 * cm, self.titulo_corto)
        canv.drawRightString(A4[0] - self.rightMargin, 1.15 * cm, str(doc.page))
        canv.restoreState()

    def afterFlowable(self, flowable):
        if isinstance(flowable, Paragraph) and flowable.style.name in ("h1", "h2"):
            nivel = 0 if flowable.style.name == "h1" else 1
            texto = flowable.getPlainText()
            self._marcador += 1
            clave = f"m{self._marcador}"
            self.canv.bookmarkPage(clave)
            self.canv.addOutlineEntry(texto, clave, level=nivel, closed=nivel > 0)
            self.notify("TOCEntry", (nivel, texto, self.page, clave))


def indice(profundidad=2):
    toc = TableOfContents()
    toc.levelStyles = [S["toc1"], S["toc2"]][:profundidad]
    return toc


def seccion(story, kicker, titulo, salto=True):
    story.append(PageBreak() if salto else Spacer(1, 14))
    story.append(P(kicker, "kicker"))
    story.append(P(titulo, "h1"))
    story.append(Spacer(1, 4))


def portada_factory(titulo, subtitulo, lineas):
    def portada(canv, doc):
        canv.saveState()
        canv.setFillColor(AZUL)
        canv.circle(16.1 * cm, 24.2 * cm, 6.1 * cm, stroke=0, fill=1)
        canv.setFillColor(DURAZNO)
        canv.circle(18.3 * cm, 15.6 * cm, 3.1 * cm, stroke=0, fill=1)
        canv.setFillColor(MENTA)
        canv.circle(12.1 * cm, 16.4 * cm, 2.1 * cm, stroke=0, fill=1)
        canv.setFillColor(LAVANDA)
        canv.circle(17.2 * cm, 4.2 * cm, 1.7 * cm, stroke=0, fill=1)
        canv.setFillColor(MUTED)
        canv.setFont(F["semibold"], 11)
        canv.drawString(2.05 * cm, 25.9 * cm, "DWMusicBrainz · Bases de Datos Avanzadas")
        canv.setFillColor(INK)
        canv.setFont(F["bold"], 31)
        y = 13.1 * cm
        for linea in titulo:
            canv.drawString(2.05 * cm, y, linea)
            y -= 1.3 * cm
        canv.setFont(F["regular"], 13.5)
        canv.setFillColor(MUTED)
        y -= 0.25 * cm
        for linea in subtitulo:
            canv.drawString(2.05 * cm, y, linea)
            y -= 0.65 * cm
        canv.setFont(F["regular"], 10.5)
        y = 6.9 * cm
        for linea in lineas:
            canv.drawString(2.05 * cm, y, linea)
            y -= 0.56 * cm
        canv.restoreState()

    return portada


__all__ = [n for n in dir() if not n.startswith("_")]
