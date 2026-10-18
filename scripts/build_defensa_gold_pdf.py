"""
build_defensa_gold_pdf.py
=========================
Genera el documento de defensa de la capa Gold y del dashboard de Power BI.
Todas las cifras se consultan en vivo sobre PostgreSQL para que el documento
sea reproducible y coincida con el Data Warehouse.

Uso:
    python scripts/build_defensa_gold_pdf.py [ruta_salida.pdf]
"""

import os
import sys
from datetime import date
from pathlib import Path

import psycopg2
from dotenv import load_dotenv
from reportlab.graphics.charts.barcharts import HorizontalBarChart, VerticalBarChart
from reportlab.graphics.charts.lineplots import LinePlot
from reportlab.graphics.shapes import Drawing, Line, Rect, String
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate,
    CondPageBreak,
    Frame,
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
load_dotenv(BASE_DIR / ".env")
DEFAULT_OUTPUT = BASE_DIR / "docs" / "Defensa_Capa_Gold_y_Dashboard.pdf"

# ---------------------------------------------------------------------------
# Paleta y tipografía (idénticas al tema del dashboard de Power BI)
# ---------------------------------------------------------------------------
NAVY = colors.HexColor("#0D366B")
BLUE = colors.HexColor("#2A78D6")
ORANGE = colors.HexColor("#EB6834")
AQUA = colors.HexColor("#1BAF7A")
AMBER = colors.HexColor("#EDA100")
GRAY_SERIES = colors.HexColor("#9B9A94")
INK = colors.HexColor("#1B2433")
MUTED = colors.HexColor("#5B6472")
HAIRLINE = colors.HexColor("#E3E7ED")
PANEL = colors.HexColor("#F4F6F9")
PANEL_BLUE = colors.HexColor("#EAF2FC")
PANEL_ORANGE = colors.HexColor("#FDF0EA")
GOOD = colors.HexColor("#0C7A0C")

FONT_DIR = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "Fonts"
FONT_FILES = {
    "Body": "segoeui.ttf",
    "Body-Bold": "segoeuib.ttf",
    "Body-Semibold": "seguisb.ttf",
    "Body-Italic": "segoeuii.ttf",
}


def register_fonts():
    """Usa Segoe UI (misma fuente del dashboard); si no existe, cae a Helvetica."""
    if all((FONT_DIR / f).exists() for f in FONT_FILES.values()):
        for name, file in FONT_FILES.items():
            pdfmetrics.registerFont(TTFont(name, str(FONT_DIR / file)))
        pdfmetrics.registerFontFamily(
            "Body", normal="Body", bold="Body-Bold", italic="Body-Italic", boldItalic="Body-Bold"
        )
        return {"regular": "Body", "bold": "Body-Bold", "semibold": "Body-Semibold", "italic": "Body-Italic"}
    return {"regular": "Helvetica", "bold": "Helvetica-Bold", "semibold": "Helvetica-Bold", "italic": "Helvetica-Oblique"}


F = register_fonts()


def fmt_int(n):
    return f"{int(n):,}".replace(",", ".")


def fmt_pct(x, decimals=1):
    return f"{x * 100:.{decimals}f}".replace(".", ",") + " %"


def fmt_dec(x, decimals=2):
    return f"{x:.{decimals}f}".replace(".", ",")


PAISES_ES = {
    "United States": "Estados Unidos", "United Kingdom": "Reino Unido", "Germany": "Alemania",
    "Japan": "Japón", "France": "Francia", "Netherlands": "Países Bajos", "Canada": "Canadá",
    "Italy": "Italia", "Australia": "Australia", "Sweden": "Suecia", "Finland": "Finlandia",
    "Spain": "España", "South Korea": "Corea del Sur",
}


def interpret_r(r):
    """Escala convencional de Cohen: |r| < 0,3 débil; < 0,7 moderada; >= 0,7 fuerte."""
    fuerza = "Débil" if abs(r) < 0.3 else "Moderada" if abs(r) < 0.7 else "Fuerte"
    sentido = "positiva: las canciones se alargan" if r > 0 else "negativa: las canciones se acortan"
    return f"{fuerza} y {sentido}."


def fmt_mmss(minutes):
    total = round(minutes * 60)
    return f"{total // 60}:{total % 60:02d}"


# ---------------------------------------------------------------------------
# Extracción de cifras en vivo
# ---------------------------------------------------------------------------
def fetch_metrics():
    conn = psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "5435")),
        dbname=os.getenv("DB_NAME", "dw_musicbrainz"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", "postgres123"),
    )
    cur = conn.cursor()

    def one(sql, params=None):
        cur.execute(sql, params)
        return cur.fetchone()

    def rows(sql, params=None):
        cur.execute(sql, params)
        return cur.fetchall()

    m = {}
    (
        m["lanzamientos"], m["soportes"], m["pistas"], m["grabaciones"], m["artistas"],
        dur_seg, dur_min_total, m["pistas_isrc"], m["pistas_largas"], m["pistas_completas"],
    ) = one("""
        SELECT SUM(lanzamientos_total), SUM(soportes_total), SUM(pistas_total),
               SUM(grabaciones_unicas_total), COUNT(DISTINCT artista_key),
               SUM(duracion_total_segundos), SUM(duracion_total_minutos),
               SUM(pistas_con_isrc_total), SUM(pistas_largas_total), SUM(pistas_completas_total)
        FROM gold.fact_produccion_musical
    """)
    m["horas"] = float(dur_min_total) / 60
    m["dur_media_min"] = float(dur_seg) / m["pistas_completas"] / 60
    m["isrc_pct"] = m["pistas_isrc"] / m["pistas"]
    m["largas_pct"] = m["pistas_largas"] / m["pistas"]
    m["pistas_por_lanz"] = m["pistas"] / m["lanzamientos"]

    m["unicos_silver"] = one("SELECT COUNT(DISTINCT m.release) FROM silver.track t JOIN silver.medium m ON t.medium = m.id")[0]
    m["soportes_silver"] = one("SELECT COUNT(DISTINCT medium) FROM silver.track")[0]
    m["releases_silver"] = one("SELECT COUNT(*) FROM silver.release")[0]
    m["lanz_sin_fecha"] = one("SELECT COALESCE(SUM(lanzamientos_total), 0) FROM gold.fact_produccion_musical WHERE fecha_key = 0")[0]
    m["fact_rows"] = one("SELECT COUNT(*) FROM gold.fact_produccion_musical")[0]
    m["dist_rows"] = one("SELECT COUNT(*) FROM gold.fact_distribucion_duracion")[0]
    m["dist_pistas"] = one("SELECT SUM(pistas_total) FROM gold.fact_distribucion_duracion")[0]

    m["table_counts"] = rows("""
        SELECT 'gold.' || t, (xpath('/row/c/text()', query_to_xml('SELECT COUNT(*) AS c FROM gold.' || t, false, true, '')))[1]::TEXT::BIGINT
        FROM unnest(ARRAY['dim_fecha','dim_artista','dim_lanzamiento','dim_formato','dim_geografia','dim_idioma','dim_rango_duracion']) AS t
    """)

    m["orphans"] = {}
    for dim, key in [("dim_fecha", "fecha_key"), ("dim_artista", "artista_key"), ("dim_lanzamiento", "lanzamiento_key"),
                     ("dim_geografia", "geografia_key"), ("dim_formato", "formato_key"), ("dim_idioma", "idioma_key")]:
        m["orphans"][dim] = one(
            f"SELECT COUNT(*) FROM gold.fact_produccion_musical f LEFT JOIN gold.{dim} d ON f.{key} = d.{key} WHERE d.{key} IS NULL"
        )[0]

    m["formatos"] = rows("""
        SELECT df.categoria_formato, SUM(f.lanzamientos_total)
        FROM gold.fact_produccion_musical f JOIN gold.dim_formato df USING (formato_key)
        GROUP BY 1 ORDER BY 2 DESC
    """)
    lanz_total = float(m["lanzamientos"])
    m["formato_pct"] = {cat: float(v) / lanz_total for cat, v in m["formatos"]}

    m["anual"] = rows("""
        SELECT d.anio,
               SUM(f.lanzamientos_total) FILTER (WHERE df.categoria_formato = 'Digital / Streaming')::FLOAT / NULLIF(SUM(f.lanzamientos_total), 0),
               SUM(f.lanzamientos_total) FILTER (WHERE df.categoria_formato = 'Físico / Óptico')::FLOAT / NULLIF(SUM(f.lanzamientos_total), 0),
               SUM(f.lanzamientos_total)
        FROM gold.fact_produccion_musical f
        JOIN gold.dim_fecha d USING (fecha_key)
        JOIN gold.dim_formato df USING (formato_key)
        WHERE d.anio BETWEEN 1990 AND 2025
        GROUP BY d.anio ORDER BY d.anio
    """)
    m["cruce"] = next((a for a, dig, cd, _ in m["anual"] if dig and cd and dig > cd), None)
    m["anual_dict"] = {a: (dig or 0.0, cd or 0.0, n) for a, dig, cd, n in m["anual"]}

    m["decadas"] = rows("""
        SELECT d.decada,
               SUM(f.lanzamientos_total) FILTER (WHERE df.categoria_formato = 'Físico / Vinilo')::FLOAT / NULLIF(SUM(f.lanzamientos_total), 0),
               SUM(f.lanzamientos_total) FILTER (WHERE df.categoria_formato = 'Físico / Óptico')::FLOAT / NULLIF(SUM(f.lanzamientos_total), 0),
               SUM(f.lanzamientos_total) FILTER (WHERE df.categoria_formato = 'Digital / Streaming')::FLOAT / NULLIF(SUM(f.lanzamientos_total), 0),
               SUM(f.pistas_con_isrc_total)::FLOAT / NULLIF(SUM(f.pistas_total), 0),
               SUM(f.duracion_total_segundos)::FLOAT / NULLIF(SUM(f.pistas_completas_total), 0) / 60
        FROM gold.fact_produccion_musical f
        JOIN gold.dim_fecha d USING (fecha_key)
        JOIN gold.dim_formato df USING (formato_key)
        WHERE d.anio BETWEEN 1950 AND 2025
        GROUP BY d.decada ORDER BY d.decada
    """)

    m["paises"] = rows("""
        SELECT g.nombre_pais, SUM(f.lanzamientos_total),
               SUM(f.lanzamientos_total) FILTER (WHERE df.categoria_formato = 'Digital / Streaming')::FLOAT / NULLIF(SUM(f.lanzamientos_total), 0)
        FROM gold.fact_produccion_musical f
        JOIN gold.dim_geografia g USING (geografia_key)
        JOIN gold.dim_formato df USING (formato_key)
        WHERE g.tipo_area = 'País'
        GROUP BY 1 HAVING SUM(f.lanzamientos_total) > 0 ORDER BY 2 DESC LIMIT 30
    """)
    m["idiomas"] = rows("""
        SELECT i.nombre_idioma, SUM(f.lanzamientos_total)
        FROM gold.fact_produccion_musical f JOIN gold.dim_idioma i USING (idioma_key)
        WHERE i.idioma_id <> 0 GROUP BY 1 ORDER BY 2 DESC LIMIT 8
    """)
    m["tipos_artista"] = rows("""
        SELECT a.tipo_artista, SUM(f.lanzamientos_total)
        FROM gold.fact_produccion_musical f JOIN gold.dim_artista a USING (artista_key)
        GROUP BY 1 ORDER BY 2 DESC
    """)

    m["histograma"] = rows("""
        SELECT r.orden, r.etiqueta_rango, SUM(f.pistas_total)
        FROM gold.fact_distribucion_duracion f JOIN gold.dim_rango_duracion r USING (rango_duracion_key)
        WHERE r.rango_duracion_key > 0
        GROUP BY 1, 2 ORDER BY 1
    """)
    hist_total = sum(int(r[2]) for r in m["histograma"])
    m["hist_total"] = hist_total
    acumulado, m["mediana_banda"] = 0, None
    for _, etiqueta, n in m["histograma"]:
        acumulado += int(n)
        if m["mediana_banda"] is None and acumulado >= hist_total / 2:
            m["mediana_banda"] = etiqueta
    moda = max(m["histograma"], key=lambda r: r[2])
    m["moda_banda"], m["moda_pct"] = moda[1], int(moda[2]) / hist_total
    m["mayor_10_pct"] = int(m["histograma"][-1][2]) / hist_total
    m["dist_media_min"] = float(one("""
        SELECT SUM(duracion_total_ms)::NUMERIC / SUM(pistas_total) / 60000
        FROM gold.fact_distribucion_duracion WHERE rango_duracion_key > 0
    """)[0])

    m["pearson"] = []
    for lo, hi in [(1950, 2025), (1990, 2025), (2013, 2025)]:
        r, slope, n = one("""
            WITH anual AS (
                SELECT d.anio, SUM(f.duracion_total_segundos) / NULLIF(SUM(f.pistas_completas_total), 0) / 60.0 AS dur_min
                FROM gold.fact_produccion_musical f JOIN gold.dim_fecha d USING (fecha_key)
                WHERE d.anio BETWEEN %s AND %s GROUP BY d.anio)
            SELECT corr(anio, dur_min), regr_slope(dur_min, anio), COUNT(*) FROM anual
        """, (lo, hi))
        m["pearson"].append((lo, hi, float(r), float(slope) * 60, n))

    m["corea"] = next((p for p in m["paises"] if p[0] == "South Korea"), None)
    m["db_size"] = one("SELECT pg_size_pretty(pg_database_size(current_database()))")[0]
    conn.close()
    return m


# ---------------------------------------------------------------------------
# Estilos
# ---------------------------------------------------------------------------
def build_styles():
    s = {}
    s["body"] = ParagraphStyle("body", fontName=F["regular"], fontSize=9.6, leading=14.2, textColor=INK, spaceAfter=6)
    s["body_muted"] = ParagraphStyle("body_muted", parent=s["body"], textColor=MUTED, fontSize=8.8, leading=12.6)
    s["bullet"] = ParagraphStyle("bullet", parent=s["body"], leftIndent=14, bulletIndent=4, spaceAfter=3)
    s["h1"] = ParagraphStyle("h1", fontName=F["semibold"], fontSize=19, leading=24, textColor=NAVY, spaceBefore=4, spaceAfter=4)
    s["h1_kicker"] = ParagraphStyle("h1_kicker", fontName=F["semibold"], fontSize=8.5, leading=11, textColor=BLUE, spaceAfter=2)
    s["h2"] = ParagraphStyle("h2", fontName=F["semibold"], fontSize=12.5, leading=17, textColor=INK, spaceBefore=10, spaceAfter=4)
    s["h3"] = ParagraphStyle("h3", fontName=F["semibold"], fontSize=10.4, leading=14, textColor=NAVY, spaceBefore=6, spaceAfter=2)
    s["th"] = ParagraphStyle("th", fontName=F["semibold"], fontSize=8.4, leading=11, textColor=colors.white)
    s["td"] = ParagraphStyle("td", fontName=F["regular"], fontSize=8.4, leading=11.2, textColor=INK)
    s["td_bold"] = ParagraphStyle("td_bold", parent=s["td"], fontName=F["semibold"])
    s["code"] = ParagraphStyle("code", fontName="Courier", fontSize=7.8, leading=10.4, textColor=INK, backColor=PANEL,
                               borderPadding=(6, 6, 6, 6), spaceBefore=4, spaceAfter=10, leftIndent=4, rightIndent=4)
    s["callout"] = ParagraphStyle("callout", parent=s["body"], fontSize=9.4, leading=13.6)
    s["kpi_value"] = ParagraphStyle("kpi_value", fontName=F["semibold"], fontSize=17, leading=20, textColor=INK, alignment=TA_LEFT)
    s["kpi_label"] = ParagraphStyle("kpi_label", fontName=F["regular"], fontSize=8, leading=10, textColor=MUTED)
    s["script_time"] = ParagraphStyle("script_time", fontName=F["semibold"], fontSize=8.4, leading=11, textColor=BLUE)
    s["script_say"] = ParagraphStyle("script_say", parent=s["body"], fontName=F["italic"], leftIndent=8, textColor=INK)
    s["toc1"] = ParagraphStyle("toc1", fontName=F["regular"], fontSize=10, leading=17, textColor=INK, leftIndent=0)
    s["caption"] = ParagraphStyle("caption", fontName=F["italic"], fontSize=8, leading=10.5, textColor=MUTED, alignment=TA_CENTER, spaceAfter=10)
    return s


S = build_styles()


def P(text, style="body"):
    return Paragraph(text, S[style])


def bullets(items, style="bullet"):
    return [Paragraph(item, S[style], bulletText="•") for item in items]


def table(data, col_widths, header=True, zebra=True, font_size=None, first_col_bold=False):
    """Tabla con cabecera azul marino y filas alternas; envuelve celdas en Paragraph."""
    wrapped = []
    for i, row in enumerate(data):
        new_row = []
        for j, cell in enumerate(row):
            if isinstance(cell, str):
                if header and i == 0:
                    style = "th"
                elif first_col_bold and j == 0:
                    style = "td_bold"
                else:
                    style = "td"
                new_row.append(Paragraph(cell, S[style]))
            else:
                new_row.append(cell)
        wrapped.append(new_row)
    t = Table(wrapped, colWidths=col_widths, repeatRows=1 if header else 0)
    cmds = [
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("LINEBELOW", (0, 0), (-1, -1), 0.4, HAIRLINE),
    ]
    if header:
        cmds += [("BACKGROUND", (0, 0), (-1, 0), NAVY)]
    if zebra:
        for r in range(1 if header else 0, len(data)):
            if r % 2 == 0:
                cmds.append(("BACKGROUND", (0, r), (-1, r), PANEL))
    t.setStyle(TableStyle(cmds))
    return t


def callout(text, tone="blue", title=None):
    bg, bar = (PANEL_BLUE, BLUE) if tone == "blue" else (PANEL_ORANGE, ORANGE) if tone == "orange" else (PANEL, MUTED)
    content = []
    if title:
        content.append(Paragraph(f"<font name='{F['semibold']}' color='{bar.hexval().replace('0x', '#')}'>{title}</font>", S["callout"]))
    content.append(Paragraph(text, S["callout"]))
    t = Table([[content]], colWidths=[16.4 * cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), bg),
        ("LINEBEFORE", (0, 0), (0, -1), 3, bar),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    return KeepTogether([t, Spacer(1, 8)])


def kpi_grid(items, cols=4):
    cells = []
    for value, label in items:
        cells.append([Paragraph(value, S["kpi_value"]), Paragraph(label, S["kpi_label"])])
    rows_ = [cells[i:i + cols] for i in range(0, len(cells), cols)]
    while len(rows_[-1]) < cols:
        rows_[-1].append("")
    width = 16.4 * cm / cols
    t = Table(rows_, colWidths=[width] * cols)
    t.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.5, HAIRLINE),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, HAIRLINE),
        ("BACKGROUND", (0, 0), (-1, -1), colors.white),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    return KeepTogether([t, Spacer(1, 10)])


# ---------------------------------------------------------------------------
# Gráficos y diagramas
# ---------------------------------------------------------------------------
def star_schema_drawing():
    w, h = 16.4 * cm, 7.4 * cm
    d = Drawing(w, h)
    cx, cy = w / 2, h / 2
    fact_w, fact_h = 4.6 * cm, 1.7 * cm

    def box(x, y, bw, bh, title, subtitle, fill, stroke, title_color=INK):
        d.add(Rect(x, y, bw, bh, rx=6, ry=6, fillColor=fill, strokeColor=stroke, strokeWidth=1))
        d.add(String(x + bw / 2, y + bh - 15, title, fontName=F["semibold"], fontSize=8.6, fillColor=title_color, textAnchor="middle"))
        d.add(String(x + bw / 2, y + 9, subtitle, fontName=F["regular"], fontSize=7, fillColor=MUTED, textAnchor="middle"))

    dims = [
        ("dim_fecha", "fecha_key · 47.847 días", 0.12, 0.82),
        ("dim_artista", "artista_key · 3,0 M", 0.50, 0.88),
        ("dim_lanzamiento", "perfil · 313 filas", 0.88, 0.82),
        ("dim_formato", "formato_key · 115", 0.12, 0.18),
        ("dim_geografia", "geografia_key · 120 K", 0.50, 0.10),
        ("dim_idioma", "idioma_key · 354", 0.88, 0.18),
    ]
    dim_w, dim_h = 3.7 * cm, 1.15 * cm
    for _, _, fx, fy in dims:
        d.add(Line(cx, cy, fx * w, fy * h, strokeColor=HAIRLINE, strokeWidth=1.4))
    box(cx - fact_w / 2, cy - fact_h / 2, fact_w, fact_h, "fact_produccion_musical", "6 FK + 11 métricas aditivas", PANEL_BLUE, BLUE, NAVY)
    d.add(String(cx, cy - fact_h / 2 - 11, "Grano: día × artista × perfil × país × formato × idioma",
                 fontName=F["regular"], fontSize=6.2, fillColor=MUTED, textAnchor="middle"))
    for name, sub, fx, fy in dims:
        box(fx * w - dim_w / 2, fy * h - dim_h / 2, dim_w, dim_h, name, sub, colors.white, HAIRLINE)
    return d


def line_chart_digital(m):
    years = [a for a in range(1990, 2026) if a in m["anual_dict"]]
    dig = [(a, m["anual_dict"][a][0] * 100) for a in years]
    cd = [(a, m["anual_dict"][a][1] * 100) for a in years]
    d = Drawing(16.4 * cm, 6.4 * cm)
    lp = LinePlot()
    lp.x, lp.y, lp.width, lp.height = 34, 26, 16.4 * cm - 120, 6.4 * cm - 44
    lp.data = [cd, dig]
    lp.lines[0].strokeColor, lp.lines[0].strokeWidth = BLUE, 2
    lp.lines[1].strokeColor, lp.lines[1].strokeWidth = ORANGE, 2
    lp.xValueAxis.valueMin, lp.xValueAxis.valueMax = years[0], years[-1]
    lp.xValueAxis.valueSteps = list(range(1990, 2026, 5))
    lp.yValueAxis.valueMin, lp.yValueAxis.valueMax, lp.yValueAxis.valueStep = 0, 100, 25
    for axis in (lp.xValueAxis, lp.yValueAxis):
        axis.labels.fontName, axis.labels.fontSize, axis.labels.fillColor = F["regular"], 7, MUTED
        axis.strokeColor = HAIRLINE
    lp.yValueAxis.labelTextFormat = "%d %%"
    lp.yValueAxis.visibleGrid, lp.yValueAxis.gridStrokeColor = True, HAIRLINE
    d.add(lp)
    last = years[-1]
    d.add(String(lp.x + lp.width + 6, lp.y + lp.height * m["anual_dict"][last][0] - 3, "Digital",
                 fontName=F["semibold"], fontSize=8, fillColor=INK))
    d.add(String(lp.x + lp.width + 6, lp.y + lp.height * m["anual_dict"][last][1] - 3, "CD óptico",
                 fontName=F["semibold"], fontSize=8, fillColor=INK))
    if m["cruce"]:
        x = lp.x + lp.width * (m["cruce"] - years[0]) / (years[-1] - years[0])
        d.add(Line(x, lp.y, x, lp.y + lp.height, strokeColor=MUTED, strokeWidth=0.6, strokeDashArray=[2, 2]))
        d.add(String(x + 4, lp.y + lp.height - 8, f"Cruce {m['cruce']}", fontName=F["semibold"], fontSize=7.5, fillColor=MUTED))
    return d


def histogram_drawing(m):
    labels = [r[1] for r in m["histograma"]]
    values = [int(r[2]) / m["hist_total"] * 100 for r in m["histograma"]]
    d = Drawing(16.4 * cm, 6.6 * cm)
    bc = VerticalBarChart()
    bc.x, bc.y, bc.width, bc.height = 34, 46, 16.4 * cm - 50, 6.6 * cm - 60
    bc.data = [values]
    bc.bars[0].fillColor, bc.bars[0].strokeColor = BLUE, None
    bc.groupSpacing, bc.barSpacing = 1, 0
    bc.categoryAxis.categoryNames = labels
    bc.categoryAxis.labels.angle, bc.categoryAxis.labels.boxAnchor = 45, "ne"
    bc.categoryAxis.labels.fontName, bc.categoryAxis.labels.fontSize = F["regular"], 6
    bc.categoryAxis.labels.fillColor = MUTED
    bc.categoryAxis.strokeColor = HAIRLINE
    bc.valueAxis.valueMin, bc.valueAxis.valueMax, bc.valueAxis.valueStep = 0, 15, 5
    bc.valueAxis.labels.fontName, bc.valueAxis.labels.fontSize, bc.valueAxis.labels.fillColor = F["regular"], 7, MUTED
    bc.valueAxis.labelTextFormat = "%d %%"
    bc.valueAxis.visibleGrid, bc.valueAxis.gridStrokeColor, bc.valueAxis.strokeColor = True, HAIRLINE, HAIRLINE
    d.add(bc)
    return d


def bar_chart_countries(m):
    top = list(reversed(m["paises"][:10]))
    d = Drawing(16.4 * cm, 6.2 * cm)
    bc = HorizontalBarChart()
    bc.x, bc.y, bc.width, bc.height = 92, 10, 16.4 * cm - 150, 6.2 * cm - 20
    bc.data = [[int(p[1]) for p in top]]
    bc.bars[0].fillColor, bc.bars[0].strokeColor = BLUE, None
    bc.barSpacing, bc.groupSpacing = 0, 3
    bc.categoryAxis.categoryNames = [p[0] for p in top]
    bc.categoryAxis.labels.fontName, bc.categoryAxis.labels.fontSize, bc.categoryAxis.labels.fillColor = F["regular"], 7.5, INK
    bc.categoryAxis.strokeColor = HAIRLINE
    bc.valueAxis.visible = False
    bc.valueAxis.valueMin = 0
    bc.barLabelFormat = lambda v: fmt_int(v)
    bc.barLabels.fontName, bc.barLabels.fontSize, bc.barLabels.fillColor = F["regular"], 7, MUTED
    bc.barLabels.nudge, bc.barLabels.boxAnchor = 8, "w"
    d.add(bc)
    return d


# ---------------------------------------------------------------------------
# Plantilla de páginas
# ---------------------------------------------------------------------------
class DefensaDoc(BaseDocTemplate):
    def __init__(self, filename, **kw):
        super().__init__(filename, pagesize=A4, leftMargin=2.3 * cm, rightMargin=2.3 * cm,
                         topMargin=2.3 * cm, bottomMargin=2 * cm, **kw)
        frame = Frame(self.leftMargin, self.bottomMargin, self.width, self.height, id="main")
        cover_frame = Frame(0, 0, A4[0], A4[1], id="cover", leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
        self.addPageTemplates([
            PageTemplate(id="cover", frames=[cover_frame], onPage=draw_cover),
            PageTemplate(id="content", frames=[frame], onPage=draw_chrome),
        ])

    def afterFlowable(self, flowable):
        if isinstance(flowable, Paragraph) and flowable.style.name == "h1":
            text = flowable.getPlainText()
            key = f"sec-{abs(hash(text))}"
            self.canv.bookmarkPage(key)
            self.canv.addOutlineEntry(text, key, level=0)
            self.notify("TOCEntry", (0, text, self.page, key))


COVER_DATA = {}


def draw_cover(canv, doc):
    w, h = A4
    canv.saveState()
    canv.setFillColor(NAVY)
    canv.rect(0, h * 0.42, w, h * 0.58, stroke=0, fill=1)
    # Banda de acento con los colores de formato (misma paleta del dashboard)
    band = [BLUE, ORANGE, AQUA, AMBER, GRAY_SERIES]
    seg = w / len(band)
    for i, c in enumerate(band):
        canv.setFillColor(c)
        canv.rect(i * seg, h * 0.42 - 6, seg, 6, stroke=0, fill=1)
    canv.setFillColor(colors.HexColor("#9EC5F4"))
    canv.setFont(F["semibold"], 10)
    canv.drawString(2.3 * cm, h - 3.4 * cm, "BASES DE DATOS AVANZADAS · DATA WAREHOUSE")
    canv.setFillColor(colors.white)
    canv.setFont(F["semibold"], 30)
    canv.drawString(2.3 * cm, h - 5.6 * cm, "DWMusicBrainz")
    canv.setFont(F["regular"], 18)
    canv.drawString(2.3 * cm, h - 6.9 * cm, "Capa Gold y dashboard analítico")
    canv.setFont(F["regular"], 11)
    canv.setFillColor(colors.HexColor("#CDE2FB"))
    lines = [
        "Documento técnico de defensa: modelo dimensional, calidad de datos,",
        "modelo semántico, justificación estadística y visual del dashboard,",
        "y guion de presentación ante la junta directiva.",
    ]
    for i, line in enumerate(lines):
        canv.drawString(2.3 * cm, h - 8.6 * cm - i * 15, line)
    canv.setFillColor(INK)
    canv.setFont(F["semibold"], 10)
    y = h * 0.42 - 2.4 * cm
    for label, value in COVER_DATA.get("facts", []):
        canv.setFont(F["semibold"], 18)
        canv.setFillColor(INK)
        canv.drawString(2.3 * cm, y, value)
        canv.setFont(F["regular"], 9)
        canv.setFillColor(MUTED)
        canv.drawString(2.3 * cm, y - 13, label)
        y -= 1.55 * cm
    canv.setFont(F["regular"], 8.5)
    canv.setFillColor(MUTED)
    canv.drawString(2.3 * cm, 2 * cm, f"Autor: Juan Sebastián Rincón Farelo   ·   Generado el {COVER_DATA.get('fecha', '')} desde PostgreSQL 16 (dw_musicbrainz)")
    canv.restoreState()


def draw_chrome(canv, doc):
    w, h = A4
    canv.saveState()
    canv.setStrokeColor(HAIRLINE)
    canv.setLineWidth(0.6)
    canv.line(2.3 * cm, h - 1.5 * cm, w - 2.3 * cm, h - 1.5 * cm)
    canv.setFont(F["semibold"], 7.6)
    canv.setFillColor(NAVY)
    canv.drawString(2.3 * cm, h - 1.25 * cm, "DWMusicBrainz · Capa Gold y dashboard")
    canv.setFont(F["regular"], 7.6)
    canv.setFillColor(MUTED)
    canv.drawRightString(w - 2.3 * cm, h - 1.25 * cm, "Documento de defensa")
    canv.line(2.3 * cm, 1.4 * cm, w - 2.3 * cm, 1.4 * cm)
    canv.drawRightString(w - 2.3 * cm, 1.0 * cm, f"Página {doc.page}")
    canv.restoreState()


def section(story, kicker, title):
    story.append(CondPageBreak(6 * cm))
    story.append(Spacer(1, 14))
    story.append(P(kicker.upper(), "h1_kicker"))
    story.append(P(title, "h1"))
    story.append(Spacer(1, 4))


# ---------------------------------------------------------------------------
# Contenido
# ---------------------------------------------------------------------------
def build_story(m):
    story = []
    fp = m["formato_pct"]
    dig_pct, cd_pct = fp.get("Digital / Streaming", 0), fp.get("Físico / Óptico", 0)
    vin_pct, mag_pct = fp.get("Físico / Vinilo", 0), fp.get("Físico / Magnético", 0)
    otros_pct = fp.get("Otros Formatos", 0)
    p_all, p_90, p_stream = m["pearson"]
    last_year = m["anual_dict"].get(2025, (0, 0, 0))
    dec = {r[0]: r for r in m["decadas"]}
    corea = m["corea"]
    top3_es = [PAISES_ES.get(p[0], p[0]) for p in m["paises"][:3]]
    top3 = f"{top3_es[0]}, {top3_es[1]} y {top3_es[2]}"
    modelo_filas = "~" + fmt_dec((m["fact_rows"] + m["dist_rows"] + sum(c for _, c in m["table_counts"])) / 1e6, 1) + " M de"

    COVER_DATA["facts"] = [
        ("lanzamientos únicos en el modelo", fmt_int(m["lanzamientos"])),
        ("pistas analizadas", fmt_int(m["pistas"])),
        ("artistas con producción registrada", fmt_int(m["artistas"])),
        (f"año en que el digital superó al CD", str(m["cruce"])),
    ]
    COVER_DATA["fecha"] = date.today().strftime("%d/%m/%Y")
    story.append(NextPageTemplate("content"))
    story.append(PageBreak())

    # Índice
    story.append(P("CONTENIDO", "h1_kicker"))
    story.append(Paragraph("Índice", ParagraphStyle("toc_title", parent=S["h1"])))
    toc = TableOfContents()
    toc.levelStyles = [S["toc1"]]
    toc.dotsMinLevel = 0
    story.append(toc)
    story.append(PageBreak())

    # 1. Resumen ejecutivo
    section(story, "Sección 1", "Resumen ejecutivo")
    story.append(P(
        "La capa <b>Gold</b> de DWMusicBrainz transforma el modelo relacional normalizado (3FN) de la capa Silver en un "
        "<b>modelo dimensional en estrella</b> según la metodología de Ralph Kimball, optimizado para preguntas analíticas sobre "
        "la producción musical registrada en MusicBrainz. Sobre ese modelo se construyó un <b>modelo semántico en Power BI</b> "
        "con medidas DAX y un <b>dashboard de dos páginas</b>: un resumen ejecutivo y un análisis detallado."
    ))
    story.append(kpi_grid([
        (fmt_int(m["lanzamientos"]), "Lanzamientos únicos"),
        (fmt_int(m["pistas"]), "Pistas analizadas"),
        (fmt_int(m["artistas"]), "Artistas activos"),
        (fmt_pct(m["isrc_pct"]), "Cobertura ISRC"),
        (fmt_pct(dig_pct), "Participación digital (histórica)"),
        (fmt_mmss(m["dur_media_min"]), "Duración media por pista (m:ss)"),
        (fmt_dec(m["pistas_por_lanz"], 1), "Pistas por lanzamiento"),
        (fmt_int(round(m["horas"])), "Horas de audio catalogadas"),
    ]))
    story.append(P("Hallazgos principales", "h2"))
    story += bullets([
        f"<b>Transición de formato:</b> el formato digital superó al CD óptico en <b>{m['cruce']}</b> y en 2025 representa "
        f"el <b>{fmt_pct(last_year[0])}</b> de los lanzamientos con fecha, frente al {fmt_pct(last_year[1])} del CD.",
        f"<b>Duración de las canciones:</b> entre 1950 y 2025 la duración media por año se correlaciona positivamente con el año "
        f"(r de Pearson = {fmt_dec(p_all[2])}); desde {p_stream[0]}, con el digital dominante, la tendencia se invierte "
        f"(r = {fmt_dec(p_stream[2])}, {fmt_dec(p_stream[3], 2)} s por año).",
        f"<b>Distribución:</b> la duración es unimodal con moda en <b>{m['moda_banda']}</b> ({fmt_pct(m['moda_pct'])} de las pistas), "
        f"mediana en la misma banda y media de {fmt_mmss(m['dist_media_min'])}: asimetría positiva (cola larga a la derecha).",
        f"<b>Volumen ≠ digitalización:</b> los países con más lanzamientos no son los más digitalizados"
        + (f"; por ejemplo, South Korea tiene {fmt_pct(corea[2])} de lanzamientos digitales." if corea else "."),
        f"<b>Gobierno del dato:</b> la auditoría de la capa Gold detectó y corrigió cuatro defectos (sección 8), entre ellos "
        f"un conteo no aditivo que inflaba el KPI principal y un mapeo de idiomas incorrecto.",
    ])

    # 2. Contexto
    section(story, "Sección 2", "Contexto, arquitectura y alcance")
    story.append(P(
        "El proyecto sigue una <b>arquitectura por capas (medallion)</b>: los volcados oficiales de MusicBrainz (archivos TSV dentro de "
        "<font name='Courier'>mbdump.tar.bz2</font>) se cargan con <font name='Courier'>COPY</font> en la capa <b>Silver</b> (tablas "
        "normalizadas en 3FN con auditoría en <font name='Courier'>meta.etl_audit</font>). La capa <b>Gold</b> desnormaliza esa información "
        "en un esquema en estrella orientado al negocio y con nombres en español."
    ))
    story.append(table([
        ["Capa", "Propósito", "Modelo", "Objetos principales"],
        ["Raw", "Archivos originales del volcado", "TSV", "mbdump/*"],
        ["Silver", "Datos limpios, tipados y auditados", "Relacional 3FN", "release, medium, track, recording, artist, area, language, isrc…"],
        ["Gold", "Consumo analítico (OLAP)", "Estrella (Kimball)", "2 hechos, 7 dimensiones, 4 vistas materializadas"],
        ["Semántica", "Medidas de negocio y visualización", "Power BI (Import)", "22 medidas DAX, 2 páginas de dashboard"],
    ], [2.2 * cm, 4.6 * cm, 3.2 * cm, 6.4 * cm]))
    story.append(Spacer(1, 8))
    story.append(P("Alcance de los datos", "h2"))
    story += bullets([
        f"La tabla <font name='Courier'>silver.track</font> se cargó con las <b>primeras {fmt_int(m['pistas'])} pistas</b> del volcado "
        "(carga controlada por espacio en disco). Por lo tanto, el análisis cubre los lanzamientos que tienen pistas dentro de ese "
        f"subconjunto: <b>{fmt_int(m['lanzamientos'])}</b> de {fmt_int(m['releases_silver'])} lanzamientos de Silver.",
        "El subconjunto <b>no es una muestra aleatoria</b>: corresponde al orden del archivo. Las conclusiones describen el catálogo "
        "cargado y no deben generalizarse sin esa salvedad.",
        f"Base de datos PostgreSQL 16 con un tamaño actual de {m['db_size']}.",
    ])

    # 3. Diseño dimensional
    section(story, "Sección 3", "Diseño dimensional (metodología Kimball)")
    story.append(P(
        "El modelo se diseñó con los cuatro pasos de Kimball: (1) elegir el proceso de negocio, (2) declarar el grano, "
        "(3) identificar las dimensiones y (4) identificar los hechos."
    ))
    story.append(table([
        ["Paso", "Decisión", "Justificación"],
        ["1. Proceso", "Producción musical (publicación de pistas en lanzamientos)", "Es el evento medible que responde las preguntas de negocio RF01–RF08."],
        ["2. Grano", "Un registro por día × artista × perfil de lanzamiento × país × formato × idioma", "Grano atómico suficiente para todos los cortes del dashboard sin perder detalle temporal."],
        ["3. Dimensiones", "fecha, artista, lanzamiento (perfil), geografía, formato, idioma", "Son los ejes de análisis pedidos: tiempo, quién, qué tipo, dónde, soporte y lengua."],
        ["4. Hechos", "11 métricas numéricas aditivas", "Solo números que se pueden sumar en cualquier dimensión; los textos viven en las dimensiones."],
    ], [2.4 * cm, 6.2 * cm, 7.8 * cm], first_col_bold=True))
    story.append(Spacer(1, 6))
    story.append(callout(
        "«Un registro de <font name='Courier'>gold.fact_produccion_musical</font> representa la producción musical consolidada de un día "
        "para una combinación de artista, perfil de lanzamiento, país, formato e idioma.»",
        title="Declaración del grano",
    ))
    story.append(KeepTogether([star_schema_drawing(),
                               P("Figura 1. Esquema en estrella de la capa Gold (hecho principal y sus seis dimensiones conformadas).", "caption")]))
    story.append(CondPageBreak(4 * cm))
    story.append(P("Decisiones de diseño clave", "h2"))
    story += bullets([
        "<b>Claves subrogadas enteras</b> (<font name='Courier'>*_key</font>) en lugar de las claves naturales de MusicBrainz: aíslan el DW de "
        "cambios en la fuente, hacen los joins más rápidos y permiten el patrón de fila desconocida.",
        "<b>Patrón Key 0 (fila desconocida):</b> cada dimensión tiene una fila con clave 0 (por ejemplo «Sin País Registrado», "
        "«Idioma No Especificado»). Todo valor faltante apunta a esa fila, por lo que el hecho nunca tiene claves huérfanas y "
        "los totales siempre cuadran.",
        "<b>dim_lanzamiento como dimensión de perfil:</b> en lugar de una fila por lanzamiento (5,8 M), guarda las combinaciones de estado, "
        "empaque y calidad (313 filas). Es una <i>junk dimension</i> que evita una dimensión gigante sin perder capacidad de análisis.",
        "<b>Hecho sin textos ni booleanos:</b> los indicadores (tiene ISRC, es pista larga, es video) se guardan como conteos aditivos, "
        "nunca como banderas, para que <font name='Courier'>SUM</font> funcione en cualquier nivel de agregación.",
    ])
    story.append(P("Matriz de bus (dimensiones conformadas por proceso)", "h2"))
    story.append(table([
        ["Hecho", "fecha", "artista", "lanzamiento", "geografía", "formato", "idioma", "rango duración"],
        ["fact_produccion_musical (diario)", "X", "X", "X", "X", "X", "X", ""],
        ["fact_distribucion_duracion (anual)", "X (año)", "", "", "X", "X", "X", "X"],
    ], [4.4 * cm, 1.3 * cm, 1.4 * cm, 2.3 * cm, 1.8 * cm, 1.6 * cm, 1.5 * cm, 2.1 * cm], first_col_bold=True))
    story.append(P(
        "Ambos hechos comparten las mismas dimensiones conformadas, por lo que un filtro por año, país, formato o idioma afecta "
        "a los dos de forma coherente (<i>drill-across</i>).", "body_muted"))

    # 4. Hecho principal
    section(story, "Sección 4", "Tabla de hechos gold.fact_produccion_musical")
    story.append(P(
        f"Contiene <b>{fmt_int(m['fact_rows'])} filas</b>, con 6 claves foráneas y 11 métricas. Todas las métricas son "
        "<b>aditivas</b>: se pueden sumar en cualquier combinación de dimensiones y el resultado es correcto."
    ))
    story.append(table([
        ["Métrica", "Cálculo en el ETL", "Significado"],
        ["lanzamientos_total", "1 en la fila de la primera pista de cada lanzamiento", "Lanzamientos únicos (álbumes, sencillos, EP…)"],
        ["soportes_total", "1 en la fila de la primera pista de cada soporte", "Discos, casetes o medios digitales únicos"],
        ["pistas_total", "COUNT(pista)", "Pistas (tracks) publicadas"],
        ["grabaciones_unicas_total", "1 en la primera aparición de cada grabación", "Grabaciones distintas"],
        ["duracion_total_ms / _segundos / _minutos", "SUM(duración de la pista)", "Tiempo total de audio"],
        ["pistas_con_isrc_total", "SUM(1 si la grabación tiene ISRC)", "Pistas con código internacional ISRC"],
        ["pistas_largas_total", "SUM(1 si dura más de 5 min)", "Pistas largas"],
        ["pistas_video_total", "SUM(1 si es video)", "Pistas de video"],
        ["pistas_completas_total", "SUM(1 si tiene duración)", "Denominador para promedios de duración"],
    ], [5.0 * cm, 5.6 * cm, 5.8 * cm], first_col_bold=True))
    story.append(Spacer(1, 6))
    story.append(callout(
        "Un <font name='Courier'>COUNT(DISTINCT lanzamiento)</font> calculado por fila <b>no es aditivo</b>: si un álbum tiene pistas de "
        "dos artistas o se editó en dos formatos, aparece en dos filas y al sumarlas se cuenta dos veces. Por eso el ETL asigna cada "
        "lanzamiento, soporte y grabación a <b>una sola fila</b>, la de su primera pista (función de ventana "
        "<font name='Courier'>ROW_NUMBER() OVER (PARTITION BY lanzamiento ORDER BY soporte, pista)</font>). Así, "
        f"<font name='Courier'>SUM(lanzamientos_total)</font> = {fmt_int(m['lanzamientos'])} = número exacto de lanzamientos distintos "
        "en Silver, comprobado por el control de calidad <font name='Courier'>CONCILIACION_LANZAMIENTOS_UNICOS</font>.",
        title="Por qué las métricas de conteo son aditivas (regla de asignación)",
    ))
    story.append(P("Consecuencia de la regla de asignación", "h3"))
    story.append(P(
        "Si un lanzamiento mezcla artistas o formatos, se atribuye al artista y al formato de su primera pista. Es la convención "
        "estándar para mantener la aditividad; la alternativa (repartir fracciones) complica la interpretación sin cambiar las "
        "tendencias. Las métricas de pistas y duración no se ven afectadas porque cada pista ocupa exactamente una fila."
    ))
    story.append(P("Regla de fecha", "h3"))
    story.append(P(
        "La fecha es la del primer evento de publicación del lanzamiento (país conocido primero, luego país desconocido). "
        f"Si el lanzamiento no tiene fecha, va a la clave 0 «Sin fecha» ({fmt_int(m['lanz_sin_fecha'])} lanzamientos). "
        "No se imputa con otros datos, porque eso generaba anacronismos (sección 8)."
    ))

    # 5. Dimensiones
    section(story, "Sección 5", "Dimensiones conformadas")
    counts = dict(m["table_counts"])
    story.append(table([
        ["Dimensión", "Filas", "Atributos principales", "Uso en el dashboard"],
        ["dim_fecha", fmt_int(counts["gold.dim_fecha"]), "fecha_completa, anio, trimestre, mes, nombre_mes, decada, siglo, es_fin_de_semana", "Rango de años, décadas, series de tiempo"],
        ["dim_artista", fmt_int(counts["gold.dim_artista"]), "nombre_artista, tipo_artista, genero, nombre_pais, anio_inicio, anio_fin", "Tipo de artista, Top 20 artistas"],
        ["dim_lanzamiento", fmt_int(counts["gold.dim_lanzamiento"]), "estado_lanzamiento, tipo_empaque, calidad_datos (perfil)", "Filtro por estado del lanzamiento"],
        ["dim_formato", fmt_int(counts["gold.dim_formato"]), "nombre_formato, categoria_formato (Digital, Óptico, Vinilo, Magnético, Otros)", "Mezcla de formatos, participación digital"],
        ["dim_geografia", fmt_int(counts["gold.dim_geografia"]), "nombre_area, tipo_area, nombre_pais", "Top países, dispersión por país"],
        ["dim_idioma", fmt_int(counts["gold.dim_idioma"]), "nombre_idioma, codigo_iso (catálogo oficial ISO 639-3)", "Top idiomas, filtro por idioma"],
        ["dim_rango_duracion", fmt_int(counts["gold.dim_rango_duracion"]), "etiqueta_rango, limite_inferior_seg, limite_superior_seg", "Histograma de duración"],
    ], [3.2 * cm, 1.8 * cm, 6.6 * cm, 4.8 * cm], first_col_bold=True))
    story.append(Spacer(1, 6))
    story += bullets([
        "<b>SCD Tipo 1:</b> las dimensiones se actualizan sobrescribiendo atributos (<font name='Courier'>ON CONFLICT … DO UPDATE</font>). "
        "Es suficiente porque el análisis no requiere historial de cambios de atributos (por ejemplo, el nombre de un idioma).",
        "<b>dim_fecha</b> es un calendario continuo 1900–2030 más la fila desconocida. Por esa fila (fecha nula), Power BI no permite "
        "marcarla como tabla de fechas; las medidas de tendencia trabajan por año con <font name='Courier'>SELECTEDVALUE</font>.",
        "<b>dim_geografia</b> incluye países, regiones, ciudades y subdivisiones. El atributo <font name='Courier'>tipo_area</font> permite "
        "filtrar solo países; la categoría «No Aplica» agrupa áreas que no son países (por ejemplo, regiones o «Worldwide»).",
    ])

    # 6. Distribución
    section(story, "Sección 6", "Hecho de distribución y dimensión de bandas")
    story.append(P(
        "El hecho principal agrega la duración por día y dimensiones, por lo que no conserva la duración individual de cada pista. "
        "Para analizar la <b>distribución</b> (histograma) se creó un segundo proceso dimensional:"
    ))
    story += bullets([
        "<b>gold.dim_rango_duracion</b> (<i>band dimension</i>): 20 bandas de 30 s entre 0:00 y 10:00, una banda abierta «10:00+» y la clave 0 "
        "«Sin duración».",
        f"<b>gold.fact_distribucion_duracion</b> ({fmt_int(m['dist_rows'])} filas): grano <b>año × formato × idioma × país × banda</b>, "
        "con <font name='Courier'>pistas_total</font> y <font name='Courier'>duracion_total_ms</font>.",
        f"<b>Conciliación:</b> suma {fmt_int(m['dist_pistas'])} pistas, exactamente igual al hecho principal (control "
        "<font name='Courier'>CONCILIACION_PISTAS_DISTRIBUCION</font>).",
        "<b>Ancho de banda de 30 s:</b> con más de 14 millones de observaciones, la regla de Sturges (k ≈ 1 + log<sub>2</sub>(n) ≈ 25 clases) "
        "sugiere un número de clases similar a las 21 elegidas; 30 s es además una unidad fácil de leer para negocio.",
        "<b>Grano anual:</b> se eligió año en lugar de día para mantener el hecho pequeño. No incluye artista, por lo que el filtro de "
        "tipo de artista no afecta al histograma (limitación documentada).",
    ])

    # 7. Diseño físico
    section(story, "Sección 7", "Diseño físico y rendimiento")
    story += bullets([
        "<b>Particionamiento por rango</b> de <font name='Courier'>fecha_key</font> en 15 particiones (fecha desconocida, pre-1970, décadas "
        "1970–2010, años 2020–2025, 2026+ y una partición por defecto). PostgreSQL descarta particiones que no cumplen el filtro "
        "(<i>partition pruning</i>), lo que acelera las consultas por período.",
        "<b>Índices B-Tree</b> en cada clave foránea del hecho para acelerar los joins con las dimensiones.",
        "<b>4 vistas materializadas</b> pre-agregadas (tendencias anuales, analítica de artistas, evolución de formatos y distribución "
        "geográfica) para consultas SQL rápidas fuera de Power BI.",
        f"<b>Modo Import en Power BI:</b> el modelo comprime {modelo_filas} filas en memoria (motor VertiPaq), así que los visuales responden "
        "sin consultar PostgreSQL en cada interacción.",
    ])

    # 8. Calidad y auditoría
    section(story, "Sección 8", "Calidad de datos y hallazgos de auditoría")
    story.append(P(
        "Antes de construir el dashboard se auditó la capa Gold con consultas DAX y SQL. Se encontraron y corrigieron cuatro "
        "defectos. Documentarlos es parte del gobierno del dato: muestra que las cifras del dashboard fueron verificadas."
    ))
    story.append(table([
        ["#", "Defecto encontrado", "Impacto", "Corrección"],
        ["1", "lanzamientos_total y soportes_total se calculaban con COUNT(DISTINCT) por fila y luego se sumaban.",
         "El KPI principal contaba lanzamientos repetidos (3,2 M en lugar de los valores únicos).",
         "Regla de asignación a la primera pista con ROW_NUMBER(); control de conciliación contra Silver."],
        ["2", "Si un lanzamiento no tenía fecha, se usaba el año de inicio del artista o la fecha de edición del registro.",
         "Anacronismos: CD o digital fechados en 1920 o 1950.",
         "Sin fecha real → clave 0 «Sin fecha». Los gráficos de tendencia muestran 1950–2025."],
        ["3", "dim_idioma usaba un CASE con IDs escritos a mano que no coincidían con MusicBrainz.",
         "Etiquetas falsas: «Húngaro» era japonés; «Japonés» era «varios idiomas».",
         "Se cargó el catálogo oficial silver.language (7.846 idiomas) y se resuelve con JOIN."],
        ["4", "Los lanzamientos con idioma nulo se renombraban como «Otro Idioma (0)».",
         "La fila desconocida perdía su significado.",
         "La clave 0 se restablece como «Idioma No Especificado»."],
    ], [0.7 * cm, 5.4 * cm, 5.0 * cm, 5.3 * cm]))
    story.append(Spacer(1, 6))
    story.append(P("Controles automáticos (meta.data_quality_log)", "h2"))
    orphan_rows = [["Control", "Resultado"]]
    for dim, n in m["orphans"].items():
        orphan_rows.append([f"Integridad referencial hecho → {dim}", f"{fmt_int(n)} huérfanos"])
    orphan_rows += [
        ["Conciliación lanzamientos únicos (Gold vs Silver)", f"{fmt_int(m['lanzamientos'])} = {fmt_int(m['unicos_silver'])}"],
        ["Conciliación soportes únicos (Gold vs Silver)", f"{fmt_int(m['soportes'])} = {fmt_int(m['soportes_silver'])}"],
        ["Conciliación pistas (hecho principal vs distribución)", f"{fmt_int(m['pistas'])} = {fmt_int(m['dist_pistas'])}"],
    ]
    story.append(table(orphan_rows, [10.4 * cm, 6.0 * cm]))
    story.append(Spacer(1, 6))
    story.append(P("Datos especiales de MusicBrainz tratados en el dashboard", "h2"))
    story += bullets([
        "Artistas especiales como <font name='Courier'>[unknown]</font>, <font name='Courier'>[anonymous]</font> o "
        "<font name='Courier'>[no artist]</font> no son artistas reales; se excluyen del Top 20 (filtro «no empieza con [»).",
        "El ranking de países usa solo <font name='Courier'>tipo_area = 'País'</font>, para no mezclar países con regiones.",
        "Las series de tiempo terminan en 2025: 2026 está incompleto y el catálogo contiene fechas futuras anunciadas.",
    ])

    # 9. Modelo semántico
    section(story, "Sección 9", "Modelo semántico en Power BI")
    story.append(P("Relaciones", "h2"))
    story += bullets([
        "Todas las relaciones son <b>1:N con filtro en una sola dirección</b> (de la dimensión al hecho). Es la configuración "
        "recomendada para un esquema en estrella: evita ambigüedades y resultados inesperados.",
        "Power BI había detectado dos caminos hacia dim_geografia (directo desde el hecho y a través de dim_artista.area_id). "
        "Se desactivó el camino por artista y se activó el directo: así «país» significa país del lanzamiento. "
        "El país de origen del artista sigue disponible como atributo en dim_artista.",
        "Se ocultaron claves técnicas y columnas numéricas del hecho, y se desactivó la suma automática de claves y años, para que "
        "el usuario solo use medidas explícitas.",
        "Se desactivó «Fecha/hora automática», que creaba tablas de calendario ocultas por cada columna de fecha.",
    ])
    story.append(P("Medidas DAX (tabla _Medidas)", "h2"))
    story.append(P(
        "Las medidas se agrupan en carpetas: Volumen, Duración, Calidad, Formatos, Tendencia y Distribución. El catálogo completo "
        "con su código está en el Anexo A. Tres decisiones técnicas importantes:"
    ))
    story += bullets([
        "<b>DIVIDE</b> en lugar de «/»: devuelve vacío cuando el denominador es cero en lugar de un error.",
        "<b>Promedio ponderado:</b> la duración promedio es SUM(segundos) / SUM(pistas con duración), no un promedio de promedios. "
        "Un promedio de promedios daría el mismo peso a un día con 1 pista que a uno con 10.000.",
        "<b>ALLSELECTED</b> en los porcentajes de participación: el denominador respeta los filtros que el usuario eligió, así que los "
        "porcentajes siempre suman 100 % dentro de la selección.",
    ])

    # 10. Diseño del dashboard
    section(story, "Sección 10", "Diseño del dashboard")
    story.append(P("Principios aplicados", "h2"))
    story += bullets([
        "<b>Regla 3-30-300:</b> en 3 segundos se entiende el propósito (título y KPIs), en 30 segundos los hallazgos (gráficos "
        "principales) y en 300 segundos se puede explorar el detalle (segmentadores, tabla y página de análisis).",
        "<b>Jerarquía visual (Stephen Few):</b> arriba los filtros, luego los KPIs, después la tendencia y al final el desglose. "
        "La lectura sigue el patrón en Z, de arriba a la izquierda hacia abajo a la derecha.",
        "<b>Relación datos-tinta (Edward Tufte):</b> sin efectos 3D, sin sombras y con cuadrícula tenue. En los rankings se muestra el "
        "valor sobre la barra y se elimina el eje numérico redundante.",
        "<b>Una pregunta por página:</b> el Resumen ejecutivo responde «¿cuánto y cómo cambió la industria?»; el Análisis detallado "
        "responde «¿qué la caracteriza por época, país, idioma y artista?».",
        "<b>Lienzo de 1280 × 720 px</b> con márgenes de 15 px y separación de 5 px, validado sin superposiciones.",
    ])
    story.append(P("Teoría del color", "h2"))
    story.append(table([
        ["Elemento", "Color", "Razón"],
        ["CD óptico", "Azul #2A78D6", "Formato dominante del período físico; color base del informe."],
        ["Digital / Streaming", "Naranja #EB6834", "Complementario del azul: máximo contraste para los dos protagonistas de la transición."],
        ["Vinilo", "Verde agua #1BAF7A", "Tercer tono de la paleta categórica, distinguible del azul y del naranja."],
        ["Magnético", "Ámbar #EDA100", "Cuarto tono; categoría minoritaria."],
        ["Otros formatos", "Gris #9B9A94", "Neutro a propósito: «Otros» no debe competir por atención."],
        ["Banner y títulos", "Azul marino #0D366B / tinta #1B2433", "Análogos al azul de los datos: armonía monocromática."],
        ["Fondo", "#F4F6F9 con tarjetas blancas", "Fondo claro de estilo SaaS; las tarjetas separan bloques sin líneas pesadas."],
    ], [3.4 * cm, 4.6 * cm, 8.4 * cm], first_col_bold=True))
    story.append(Spacer(1, 6))
    story += bullets([
        "<b>El color sigue a la entidad, no al gráfico:</b> cada formato conserva su color en todas las páginas, así el usuario lo "
        "reconoce sin volver a leer la leyenda.",
        "<b>Validación de daltonismo:</b> la paleta se verificó con simulación de protanopía, deuteranopía y tritanopía. La "
        "separación mínima entre colores adyacentes es ΔE ≈ 9,1 (objetivo ≥ 8). Los textos van en gris y tinta, nunca en el color "
        "de la serie, y todos los gráficos tienen leyenda o etiqueta directa.",
        "<b>Un solo color en gráficos de una serie</b> (rankings, histograma, dispersión): agregar colores sin significado "
        "confundiría al lector.",
        "<b>Sin rojo y verde para datos:</b> se reservan para estados (bueno/malo) y no se mezclan con las categorías.",
    ])

    # 11. Justificación de gráficos
    section(story, "Sección 11", "Justificación de cada gráfico")
    story.append(P(
        "Cada gráfico se eligió según el <b>tipo de pregunta estadística</b> que responde, siguiendo el selector de gráficos de "
        "Andrew Abela. Esa taxonomía clasifica las preguntas en cuatro tipos: <b>comparación</b>, <b>composición</b>, "
        "<b>distribución</b> y <b>relación</b>. El dashboard cubre los cuatro."
    ))
    story.append(table([
        ["Gráfico", "Pregunta de negocio", "Tipo (Abela)", "Por qué este gráfico"],
        ["Tarjetas KPI", "¿Cuál es la magnitud del catálogo?", "Valor único", "Un número clave no necesita eje; la tarjeta se lee en un segundo."],
        ["Área apilada por año y formato", "¿Cómo creció la producción y cómo cambió su mezcla?", "Composición en el tiempo (muchos períodos)",
         "Muestra a la vez el total (altura) y la composición (capas) en 76 años."],
        ["Líneas Digital vs CD", "¿Cuándo el digital superó al físico?", "Comparación en el tiempo (pocas series)",
         "Dos líneas en el mismo eje de % muestran el cruce con precisión."],
        ["Barras horizontales (países, tipo de artista, idiomas)", "¿Quién produce más?", "Comparación entre categorías",
         "La longitud es el atributo que mejor se compara; la orientación horizontal deja leer nombres largos; se ordenan de mayor a menor."],
        ["Histograma de duración", "¿Cuánto dura una canción típica?", "Distribución",
         "Las barras contiguas representan clases continuas; muestran forma, moda y asimetría."],
        ["Columnas 100 % apiladas por década", "¿Qué formato dominó cada época?", "Composición relativa (pocos períodos)",
         "Normaliza cada década al 100 % para comparar proporciones aunque el volumen cambie."],
        ["Dispersión por país (eje X logarítmico)", "¿Más volumen implica más digitalización?", "Relación entre dos variables",
         "Cada punto es un país; la nube revela si existe asociación y muestra los casos atípicos."],
        ["Tabla Top 20 artistas", "¿Cuáles son los valores exactos de los principales artistas?", "Consulta de detalle",
         "Cuando se necesitan cifras exactas de varias métricas, la tabla es más precisa que un gráfico."],
    ], [3.4 * cm, 3.8 * cm, 3.2 * cm, 6.0 * cm], first_col_bold=True))
    story.append(Spacer(1, 8))
    story.append(P("Gráficos descartados y por qué", "h2"))
    story += bullets([
        "<b>Gráfico de torta:</b> el ojo compara mal ángulos y áreas; con cinco formatos y diferencias pequeñas, las barras o el "
        "100 % apilado son más precisos.",
        "<b>Doble eje Y:</b> dos escalas en un mismo gráfico sugieren correlaciones que dependen de cómo se elige cada escala. Cada "
        "medida va en su propio gráfico.",
        "<b>Mapa coroplético:</b> el país dominante (Estados Unidos) saturaría la escala, y las áreas grandes con pocos datos "
        "(por ejemplo, Rusia o Canadá) distorsionan la percepción. El ranking en barras es más honesto.",
        "<b>Promedio de duración por década (línea):</b> se reemplazó por el histograma, que muestra la distribución completa y no "
        "solo su centro.",
    ])
    story.append(KeepTogether([P("Evidencia: transición digital", "h3"), line_chart_digital(m),
                               P("Figura 2. Participación de lanzamientos por año, Digital vs CD óptico (1990–2025). Datos en vivo de gold.", "caption")]))
    story.append(KeepTogether([P("Evidencia: principales países", "h3"), bar_chart_countries(m),
                               P("Figura 3. Top 10 países por lanzamientos únicos (solo áreas de tipo País).", "caption")]))

    # 12. Estadística
    section(story, "Sección 12", "Fundamentos estadísticos")
    story.append(table([
        ["Estadística", "Fórmula / medida", "Por qué se usa"],
        ["Total (suma)", "SUM(lanzamientos_total)", "Magnitud aditiva del catálogo; válida en cualquier filtro."],
        ["Conteo distinto", "DISTINCTCOUNT(artista_key)", "Artistas únicos: no se suma, se cuenta sobre el contexto filtrado."],
        ["Proporción", "DIVIDE(parte, total)", "Coberturas y participaciones (ISRC, digital, pistas largas)."],
        ["Media ponderada", "Σ duración / Σ pistas con duración", "Evita sesgo del promedio de promedios."],
        ["Frecuencia relativa", "pistas en banda / pistas totales", "Base del histograma; permite comparar selecciones de distinto tamaño."],
        ["Moda y mediana", "banda más frecuente / banda del percentil 50", "Tendencia central robusta frente a valores extremos."],
        ["Correlación de Pearson (r)", "corr(año, duración media)", "Mide la fuerza y el signo de una relación lineal entre −1 y 1."],
        ["Pendiente (regresión lineal)", "regr_slope(duración, año)", "Traduce la correlación a segundos por año."],
        ["Escala logarítmica", "log10(lanzamientos) en el eje X", f"Variables con varios órdenes de magnitud (Top 30: de {fmt_int(m['paises'][-1][1])} a {fmt_int(m['paises'][0][1])})."],
    ], [3.6 * cm, 5.2 * cm, 7.6 * cm], first_col_bold=True))
    story.append(Spacer(1, 6))
    story.append(P("Distribución de la duración (histograma)", "h2"))
    story.append(KeepTogether([histogram_drawing(m),
                               P("Figura 4. Frecuencia relativa de pistas por banda de duración de 30 s (excluye pistas sin duración).", "caption")]))
    story += bullets([
        f"<b>Moda:</b> {m['moda_banda']} ({fmt_pct(m['moda_pct'])} de las pistas). <b>Mediana:</b> banda {m['mediana_banda']}. "
        f"<b>Media:</b> {fmt_mmss(m['dist_media_min'])} min.",
        "<b>Asimetría positiva:</b> la media es mayor que la mediana porque una cola de pistas muy largas (música clásica, mezclas, "
        f"grabaciones en vivo) la desplaza hacia la derecha; el {fmt_pct(m['mayor_10_pct'])} supera los 10 minutos.",
        "<b>Lectura de negocio:</b> el formato estándar de canción popular (3 a 4,5 minutos) concentra la mayor parte del catálogo.",
    ])
    story.append(P("Correlación año–duración (RF05)", "h2"))
    story.append(table([
        ["Período", "r de Pearson", "Pendiente", "Años (n)", "Interpretación"],
        *[[f"{lo}–{hi}", fmt_dec(r), f"{fmt_dec(sl)} s/año", str(n), interpret_r(r)] for lo, hi, r, sl, n in m["pearson"]],
    ], [2.6 * cm, 2.4 * cm, 2.6 * cm, 1.8 * cm, 7.0 * cm], first_col_bold=True))
    story.append(Spacer(1, 6))
    story.append(callout(
        "La hipótesis original de RF05 («demostrar el acortamiento en la era del streaming») <b>se cumple solo parcialmente</b>. En el "
        "largo plazo la relación es positiva; el acortamiento aparece desde que el digital domina. Además, la correlación usa medias "
        f"anuales (n = {p_stream[4]} en el período reciente), <b>no prueba causalidad</b> y se calcula sobre el subconjunto cargado. Se "
        "presenta como evidencia descriptiva, no como conclusión definitiva.",
        tone="orange", title="Lectura honesta del resultado",
    ))

    # 13. Trazabilidad
    section(story, "Sección 13", "Trazabilidad de requisitos")
    story.append(table([
        ["Requisito", "Dónde se responde", "Estado"],
        ["RF01 · Ranking Top N", "Tabla Top 20 artistas, Top 10 países; segmentadores de país y década", "Cubierto"],
        ["RF02 · Métricas por formato e idioma", "KPI de duración con segmentador de idioma; Top idiomas; mezcla de formatos", "Cubierto"],
        ["RF03 · Drill-down geográfico y temporal", "Segmentadores de año, década y país; jerarquías no publicadas como drill-down", "Parcial"],
        ["RF04 · Digital vs físico y pistas largas", "Líneas Digital vs CD, área apilada, KPI % pistas > 5 min", "Cubierto"],
        ["RF05 · Correlación año–duración", "Sección 12 (SQL corr()); histograma de duración en el dashboard", "Cubierto en documento"],
        ["RF06 · Formalización ISRC", "KPI de cobertura ISRC; columna ISRC en Top 20 con segmentadores de país y tipo", "Parcial"],
        ["RF07 · Densidad de pistas", "KPI de pistas por lanzamiento; pistas por soporte no visualizado", "Parcial"],
        ["RF08 · Artistas emergentes", "No incluido en el dashboard actual", "Pendiente"],
    ], [5.2 * cm, 8.6 * cm, 2.6 * cm], first_col_bold=True))

    # 14. Limitaciones
    section(story, "Sección 14", "Limitaciones y trabajo futuro")
    story += bullets([
        "<b>Cobertura parcial:</b> solo se cargaron las primeras 15 M de pistas del volcado; no es una muestra aleatoria.",
        "<b>Asignación a la primera pista:</b> un lanzamiento con varios artistas o formatos se atribuye a los de su primera pista.",
        "<b>País con respaldo:</b> si el lanzamiento no tiene país, se usa el área de origen del artista.",
        "<b>Nombres de idioma en inglés:</b> provienen del catálogo oficial de MusicBrainz; traducirlos a mano fue la causa del "
        "defecto 3.",
        "<b>Histograma sin artista:</b> el segmentador de tipo de artista no lo filtra.",
        "<b>Trabajo futuro:</b> publicar jerarquías de drill-down (siglo → década → año; país → tipo de área → área), completar RF06–RF08 "
        "y cargar el volcado completo de pistas.",
    ])

    # 15. Preguntas probables
    section(story, "Sección 15", "Preguntas probables del profesor")
    qa = [
        ("¿Por qué un esquema en estrella y no un copo de nieve?",
         "Porque minimiza joins, es más fácil de entender para negocio y es el modelo que mejor aprovecha Power BI. Las jerarquías "
         "(país → área, año → mes) se desnormalizan dentro de cada dimensión."),
        ("¿Cuál es el grano y por qué ese?",
         "Día × artista × perfil × país × formato × idioma. Es el nivel más fino que necesitan las preguntas; desde ahí cualquier "
         "agregación (año, década, país) es una simple suma."),
        ("¿Son realmente aditivas todas sus métricas?",
         "Sí, después de la corrección. Los conteos de lanzamientos, soportes y grabaciones se asignan a una sola fila; por eso la "
         "suma coincide con el conteo distinto en Silver. Los artistas activos son un conteo distinto y por eso se calculan como "
         "medida DISTINCTCOUNT, no como columna sumable."),
        ("¿Qué es la fila con clave 0?",
         "Es el miembro desconocido de cada dimensión. Garantiza cero huérfanos: los totales del hecho siempre cuadran y el usuario "
         "ve explícitamente cuánto dato falta."),
        ("¿Por qué no usó un gráfico de torta para los formatos?",
         "Porque los humanos comparamos longitudes con mucha más precisión que ángulos. Para composición usé área apilada y columnas "
         "100 %, que además muestran la evolución en el tiempo."),
        ("¿Por qué el eje X de la dispersión es logarítmico?",
         "Porque los lanzamientos por país van de miles a cientos de miles. En escala lineal, Estados Unidos aplasta al resto en "
         "una esquina; la escala logarítmica muestra todos los países con la misma resolución relativa."),
        ("¿Cómo sabe que los números son correctos?",
         "Por controles automáticos: integridad referencial (0 huérfanos), conciliación de lanzamientos, soportes y pistas contra "
         "Silver, y validación de las medidas con consultas DAX independientes."),
        ("¿La correlación de Pearson prueba que el streaming acortó las canciones?",
         "No. Pearson mide asociación lineal, no causalidad, y se calculó sobre medias anuales. Los datos muestran alargamiento a "
         "largo plazo y un leve acortamiento en el período reciente; lo presento como evidencia descriptiva."),
    ]
    for q, a in qa:
        story.append(KeepTogether([P(f"<b>P:</b> {q}", "h3"), P(f"<b>R:</b> {a}")]))

    # 16. Guion
    section(story, "Sección 16", "Guion para la junta directiva")
    story.append(P(
        "Duración estimada: <b>8 minutos</b>. Tono: un ingeniero de datos que traduce hallazgos técnicos en decisiones de negocio. "
        "Las frases en cursiva son para decir; las indicaciones entre corchetes son acciones en pantalla."
    ))
    guion = [
        ("0:00 – 0:45 · Apertura", "[Página Resumen ejecutivo, sin filtros]",
         "«Buenos días. En los próximos minutos les voy a mostrar qué nos dicen quince millones de pistas de producción "
         "musical sobre hacia dónde va la industria, y qué decisiones podemos tomar con eso. Todo lo que van a ver sale de un "
         "Data Warehouse que construimos y verificamos sobre el catálogo público de MusicBrainz.»"),
        ("0:45 – 1:45 · El tamaño del catálogo", "[Señalar la fila de tarjetas KPI]",
         f"«Estamos hablando de {fmt_int(m['lanzamientos'])} lanzamientos, {fmt_int(m['pistas'])} pistas y casi "
         f"{fmt_int(round(m['artistas'], -3))} artistas activos. Hay dos indicadores que quiero que retengan: hoy solo el "
         f"{fmt_pct(m['isrc_pct'])} de las pistas tiene código ISRC, el identificador que permite rastrear regalías, y el "
         f"{fmt_pct(dig_pct)} de toda la historia del catálogo ya es digital.»"),
        ("1:45 – 3:15 · La gran transición", "[Señalar el área apilada y luego la línea Digital vs CD]",
         f"«Este gráfico cuenta la historia de 75 años de música. La capa azul es el CD, que dominó desde los noventa. La naranja es "
         f"el digital. Fíjense en la línea de la derecha: en {m['cruce']} el digital superó al CD, y desde entonces la brecha no "
         f"dejó de crecer. En 2025, {fmt_pct(last_year[0])} de los lanzamientos son digitales y apenas {fmt_pct(last_year[1])} "
         "salen en CD. Para nosotros esto significa que la distribución digital ya no es un canal alternativo: es el canal.»"),
        ("3:15 – 4:15 · Dónde se produce", "[Señalar Top 10 países y tipo de artista]",
         f"«La producción está concentrada: {top3} encabezan el ranking. Los solistas y las bandas "
         "explican casi toda la producción. Si buscamos alianzas de catálogo, estos son los mercados con más volumen.»"),
        ("4:15 – 5:30 · Qué caracteriza a la música", "[Cambiar a Análisis detallado; señalar el histograma]",
         f"«Este histograma muestra cuánto dura una canción. La mayoría está entre tres y cuatro minutos y medio, con el pico en "
         f"{m['moda_banda']}. Es el formato que el mercado prefiere. Y algo interesante: tras décadas de canciones cada vez más "
         "largas, desde que domina el streaming la duración empezó a bajar levemente. Lo seguiremos monitoreando.»"),
        ("5:30 – 6:30 · Volumen no es lo mismo que digitalización", "[Señalar la dispersión por país]",
         "«Cada punto es un país. Si más volumen significara más digitalización, veríamos los puntos subir hacia la derecha, y no "
         + (f"pasa. Corea del Sur, con poco volumen, tiene {fmt_pct(corea[2])} de lanzamientos digitales. " if corea else "pasa. ")
         + "Esos mercados pequeños y muy digitales son una oportunidad de entrada con menos competencia.»"),
        ("6:30 – 7:15 · Por qué pueden confiar en estos números", "[Sin cambio de pantalla]",
         "«Antes de traerles este tablero lo auditamos. Encontramos y corregimos errores reales, como un conteo que duplicaba "
         "lanzamientos y un catálogo de idiomas mal mapeado. Hoy cada cifra se concilia automáticamente con la fuente y no hay "
         "registros huérfanos.»"),
        ("7:15 – 8:00 · Recomendaciones y cierre", "[Volver al Resumen ejecutivo]",
         "«Tres recomendaciones. Primero, priorizar la distribución digital, que ya es el canal principal. Segundo, impulsar el "
         "registro de códigos ISRC: con solo una de cada cinco pistas identificada, estamos dejando regalías sin rastrear. Tercero, "
         "explorar mercados pequeños y muy digitalizados. El tablero queda disponible para que cada área filtre por su país, "
         "formato o época. ¿Preguntas?»"),
    ]
    for when, action, say in guion:
        story.append(KeepTogether([
            P(when, "script_time"),
            P(action, "body_muted"),
            P(say, "script_say"),
            Spacer(1, 4),
        ]))
    story.append(callout(
        "Hablar de decisiones, no de herramientas (la junta no necesita oír «DAX» ni «VertiPaq»). Apoyar cada afirmación en un "
        "gráfico visible. Decir los números redondeados y con contexto («una de cada cinco»). Cerrar con una acción concreta.",
        title="Consejos de presentación",
    ))

    # Anexo A
    story.append(PageBreak())
    section(story, "Anexo A", "Catálogo de medidas DAX")
    medidas = [
        ("Total Lanzamientos", "SUM('gold fact_produccion_musical'[lanzamientos_total])"),
        ("Total Soportes", "SUM('gold fact_produccion_musical'[soportes_total])"),
        ("Total Pistas", "SUM('gold fact_produccion_musical'[pistas_total])"),
        ("Artistas Activos", "DISTINCTCOUNT('gold fact_produccion_musical'[artista_key])"),
        ("Pistas por Lanzamiento", "DIVIDE([Total Pistas], [Total Lanzamientos])"),
        ("% del Total Lanzamientos", "DIVIDE([Total Lanzamientos], CALCULATE([Total Lanzamientos], ALLSELECTED()))"),
        ("Duracion Total (Horas)", "DIVIDE(SUM('gold fact_produccion_musical'[duracion_total_minutos]), 60)"),
        ("Duracion Promedio por Pista (min)", "DIVIDE(SUM(...[duracion_total_segundos]), SUM(...[pistas_completas_total])) / 60"),
        ("Pistas con ISRC", "SUM('gold fact_produccion_musical'[pistas_con_isrc_total])"),
        ("Cobertura ISRC %", "DIVIDE([Pistas con ISRC], [Total Pistas])"),
        ("Pistas Largas (>5 min)", "SUM('gold fact_produccion_musical'[pistas_largas_total])"),
        ("% Pistas Largas", "DIVIDE([Pistas Largas (>5 min)], [Total Pistas])"),
        ("Lanzamientos Digitales", "CALCULATE([Total Lanzamientos], 'gold dim_formato'[categoria_formato] = \"Digital / Streaming\")"),
        ("Lanzamientos Vinilo", "CALCULATE([Total Lanzamientos], 'gold dim_formato'[categoria_formato] = \"Físico / Vinilo\")"),
        ("Lanzamientos CD Optico", "CALCULATE([Total Lanzamientos], 'gold dim_formato'[categoria_formato] = \"Físico / Óptico\")"),
        ("Participacion Digital %", "DIVIDE([Lanzamientos Digitales], [Total Lanzamientos])"),
        ("Participacion Vinilo %", "DIVIDE([Lanzamientos Vinilo], [Total Lanzamientos])"),
        ("Participacion CD Optico %", "DIVIDE([Lanzamientos CD Optico], [Total Lanzamientos])"),
        ("Lanzamientos Anio Anterior", "VAR a = SELECTEDVALUE('gold dim_fecha'[anio]) RETURN IF(a > 1900, CALCULATE([Total Lanzamientos], REMOVEFILTERS('gold dim_fecha'), 'gold dim_fecha'[anio] = a - 1))"),
        ("Variacion Interanual %", "DIVIDE([Total Lanzamientos] - [Lanzamientos Anio Anterior], [Lanzamientos Anio Anterior])"),
        ("Pistas (Distribucion)", "SUM('gold fact_distribucion_duracion'[pistas_total])"),
        ("% Pistas (Distribucion)", "DIVIDE([Pistas (Distribucion)], CALCULATE([Pistas (Distribucion)], ALLSELECTED('gold dim_rango_duracion')))"),
    ]
    code_style = ParagraphStyle("code_cell", fontName="Courier", fontSize=7.2, leading=9.4, textColor=INK)
    rows_ = [["Medida", "Expresión DAX"]]
    for name, expr in medidas:
        rows_.append([name, Paragraph(expr.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"), code_style)])
    story.append(table(rows_, [5.0 * cm, 11.4 * cm], first_col_bold=True))

    # Anexo B
    section(story, "Anexo B", "Glosario")
    story.append(table([
        ["Término", "Definición"],
        ["Grano", "Nivel de detalle que representa una fila de la tabla de hechos."],
        ["Dimensión conformada", "Dimensión compartida por varios hechos con el mismo significado y claves."],
        ["Clave subrogada", "Identificador entero generado por el DW, independiente de la clave de la fuente."],
        ["Métrica aditiva", "Valor numérico que se puede sumar correctamente en cualquier dimensión."],
        ["SCD Tipo 1", "Actualización de una dimensión que sobrescribe el valor anterior sin guardar historial."],
        ["Junk / profile dimension", "Dimensión que agrupa combinaciones de atributos de baja cardinalidad."],
        ["Band dimension", "Dimensión que discretiza una medida continua en rangos (bandas)."],
        ["ISRC", "International Standard Recording Code: identificador único de una grabación, usado para regalías."],
        ["Partition pruning", "Capacidad del motor de descartar particiones que no cumplen el filtro de la consulta."],
        ["DAX", "Lenguaje de fórmulas del modelo semántico de Power BI."],
    ], [4.2 * cm, 12.2 * cm], first_col_bold=True))
    return story


def main():
    output = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_OUTPUT
    output.parent.mkdir(parents=True, exist_ok=True)
    metrics = fetch_metrics()
    doc = DefensaDoc(str(output), title="DWMusicBrainz · Defensa de la capa Gold y dashboard",
                     author="Juan Sebastián Rincón Farelo", subject="Data Warehouse MusicBrainz")
    doc.multiBuild(build_story(metrics))
    print(f"[OK] PDF generado: {output}")


if __name__ == "__main__":
    main()
