"""
build_sustentacion_pptx.py
==========================
Generador programático de la presentación oficial de sustentación:
docs/DWMusicBrainz_Sustentacion.pptx

Diseño Estético:
- Paleta de Tonos Pasteles (Pastel Blue, Pastel Lavender, Pastel Mint, Pastel Peach,
  Pastel Rose, Pastel Lemon y fondo Crema/Marfil suave con tipografía Slate oscura de alto contraste).
- Formato Panorámico Widescreen 16:9 (13.333 x 7.5 pulgadas).
- 16 Diapositivas exhaustivas que cumplen el 100% de la rúbrica docente:
  1. Portada Institucional
  2. Contexto OLTP (MusicBrainz 3NF), Problema Operacional y Solución DWH OLAP
  3. Objetivo General (= Título con verbo Bloom) y Objetivos Específicos (Verbos Bloom sin explicación)
  4. Requerimientos Funcionales del Sistema (RF01 a RF08 reales del proyecto)
  5. Requerimientos No Funcionales del Sistema (RNF01 a RNF09 reales del proyecto)
  6. Arquitectura Medallón Utilizada (Raw -> Silver 3NF -> Gold Estrella -> Meta)
  7. Roles del Equipo por Etapa (Ingeniero de Datos, Modelador, Analista de BI) y sus Actividades
  8. Herramientas Implementadas y el Por Qué de su Uso (con iconos/imágenes PNG incrustados)
  9. Volumetría Oficial por Capa y Dimensionamiento Físico en Disco
  10. Diseño del Modelo en Estrella Puro en Español (Grano Histórico Diario y Métricas Aditivas)
  11. Explicación Detallada de las 6 Dimensiones Conformadas y sus Atributos Exactos
  12. Patrón Anti-Huérfanos "Key 0" y Auditoría Referencial (meta.data_quality_log)
  13. Flujo del Pipeline ETL E2E (Extracción, MaxLineReader, COPY y Agregación Histórica)
  14. Catálogo Completo de Reglas EDA Implementadas (E01 a E10)
  15. Particionamiento Físico, Vistas Materializadas y Explotación DAX en Power BI
  16. Conclusiones Técnicas y de Negocio
"""

import os
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE

BASE_DIR = Path(__file__).resolve().parent.parent
ASSETS_DIR = BASE_DIR / "docs" / "assets_tools"

# ============================================================================
# PALETA DE TONOS PASTELES (PASTEL DESIGN SYSTEM)
# ============================================================================
BG_CREAM        = RGBColor(252, 250, 247)  # Fondo general marfil/crema pastel muy suave
CARD_WHITE      = RGBColor(255, 255, 255)  # Blanco puro para tarjetas internas

PASTEL_BLUE     = RGBColor(219, 234, 254)  # Azul cielo pastel (#DBEAFE)
PASTEL_BLUE_BD  = RGBColor(147, 197, 253)  # Borde azul pastel (#93C5FD)

PASTEL_LAVENDER = RGBColor(237, 233, 254)  # Lavanda / Lila pastel (#EDE9FE)
PASTEL_LAV_BD   = RGBColor(196, 181, 253)  # Borde lavanda (#C4B5FD)

PASTEL_MINT     = RGBColor(209, 250, 229)  # Verde menta pastel (#D1FAE5)
PASTEL_MINT_BD  = RGBColor(110, 231, 183)  # Borde menta (#6EE7B7)

PASTEL_PEACH    = RGBColor(255, 237, 213)  # Durazno / Coral pastel (#FFEDD5)
PASTEL_PEACH_BD = RGBColor(253, 186, 116)  # Borde durazno (#FDBA74)

PASTEL_ROSE     = RGBColor(252, 231, 243)  # Rosa pastel (#FCE7F3)
PASTEL_ROSE_BD  = RGBColor(249, 168, 212)  # Borde rosa (#F9A8D4)

PASTEL_LEMON    = RGBColor(254, 249, 195)  # Amarillo limón pastel (#FEF9C3)
PASTEL_LEMON_BD = RGBColor(253, 224, 71)   # Borde limón (#FDE047)

PASTEL_SLATE    = RGBColor(241, 245, 249)  # Gris azulado pastel (#F1F5F9)
PASTEL_SLATE_BD = RGBColor(203, 213, 225)  # Borde gris pastel (#CBD5E1)

TEXT_DARK       = RGBColor(30, 41, 59)     # Gris pizarra profundo (#1E293B) para legibilidad perfecta
TEXT_MUTED      = RGBColor(71, 85, 105)    # Gris medio (#475569)
ACCENT_NAVY     = RGBColor(30, 58, 138)    # Azul profundo para títulos (#1E3A8A)
ACCENT_PURPLE   = RGBColor(91, 33, 182)    # Violeta profundo para subtítulos (#5B21B6)
ACCENT_TEAL     = RGBColor(15, 118, 110)   # Verde azulado oscuro (#0F766E)
ACCENT_ROSE     = RGBColor(157, 23, 77)    # Rosa oscuro (#9D174D)
ACCENT_AMBER    = RGBColor(180, 83, 9)     # Ámbar oscuro (#B45309)


def generate_tool_icons():
    """Genera íconos gráficos PNG de alta resolución (240x240) en tonos pasteles para cada herramienta."""
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    tools = [
        ("postgres", "PG 16", "PostgreSQL", (219, 234, 254), (30, 58, 138), "db"),
        ("docker", "DOCKER", "Compose v2", (224, 242, 254), (3, 105, 161), "whale"),
        ("python", "PY 3.12", "Python ETL", (254, 249, 195), (161, 98, 7), "code"),
        ("psycopg2", "LIBPQ", "psycopg2 C", (209, 250, 229), (15, 118, 110), "plug"),
        ("powerbi", "DAX / BI", "Power BI", (255, 237, 213), (180, 83, 9), "chart"),
        ("dbeaver", "SQL / ER", "DBeaver & Git", (237, 233, 254), (91, 33, 182), "tree"),
    ]
    paths = {}
    for key, badge, label, bg_rgb, fg_rgb, kind in tools:
        img = Image.new("RGBA", (220, 220), (255, 255, 255, 0))
        draw = ImageDraw.Draw(img)
        # Círculo/escudo pastel redondeado
        draw.rounded_rectangle([8, 8, 212, 212], radius=42, fill=bg_rgb + (255,), outline=fg_rgb + (255,), width=5)

        # Dibujo vectorial de ícono representativo según herramienta
        if kind == "db":
            # Cilindro de base de datos
            draw.ellipse([60, 35, 160, 70], fill=fg_rgb + (45,), outline=fg_rgb + (255,), width=4)
            draw.line([60, 52, 60, 125], fill=fg_rgb + (255,), width=4)
            draw.line([160, 52, 160, 125], fill=fg_rgb + (255,), width=4)
            draw.arc([60, 75, 160, 105], 0, 180, fill=fg_rgb + (255,), width=4)
            draw.arc([60, 105, 160, 138], 0, 180, fill=fg_rgb + (255,), width=4)
        elif kind == "whale":
            # Contenedores Docker
            for cx in (68, 98, 128):
                draw.rectangle([cx, 62, cx + 24, 86], fill=fg_rgb + (60,), outline=fg_rgb + (255,), width=3)
            for cx in (83, 113):
                draw.rectangle([cx, 36, cx + 24, 60], fill=fg_rgb + (90,), outline=fg_rgb + (255,), width=3)
            draw.chord([50, 75, 170, 135], 0, 180, fill=fg_rgb + (255,))
        elif kind == "code":
            # Engranaje / serpiente estilizada Python
            draw.rounded_rectangle([65, 38, 135, 85], radius=14, fill=fg_rgb + (200,))
            draw.rounded_rectangle([85, 72, 155, 120], radius=14, fill=(30, 58, 138, 210))
            draw.ellipse([75, 48, 85, 58], fill=(255, 255, 255, 255))
            draw.ellipse([135, 98, 145, 108], fill=(255, 255, 255, 255))
        elif kind == "plug":
            # Rayo de velocidad C / COPY streaming
            draw.polygon([(122, 34), (74, 88), (108, 88), (94, 134), (148, 76), (114, 76)], fill=fg_rgb + (230,))
        elif kind == "chart":
            # Barras ascendentes de Power BI
            draw.rounded_rectangle([62, 88, 86, 130], radius=5, fill=fg_rgb + (130,))
            draw.rounded_rectangle([98, 62, 122, 130], radius=5, fill=fg_rgb + (190,))
            draw.rounded_rectangle([134, 38, 158, 130], radius=5, fill=fg_rgb + (255,))
        elif kind == "tree":
            # Ramas de Git / Modelo ER
            draw.line([75, 45, 75, 120], fill=fg_rgb + (255,), width=5)
            draw.line([75, 75, 140, 55], fill=fg_rgb + (255,), width=5)
            draw.line([75, 95, 140, 115], fill=fg_rgb + (255,), width=5)
            for px, py in ((75, 45), (75, 120), (140, 55), (140, 115)):
                draw.ellipse([px - 11, py - 11, px + 11, py + 11], fill=bg_rgb + (255,), outline=fg_rgb + (255,), width=4)

        # Banda inferior con siglas
        draw.rounded_rectangle([24, 148, 196, 194], radius=12, fill=fg_rgb + (255,))
        try:
            font = ImageFont.truetype("arialbd.ttf", 24)
        except Exception:
            font = ImageFont.load_default()
        bbox = draw.textbbox((0, 0), badge, font=font)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        draw.text(((220 - tw) / 2, 148 + (46 - th) / 2 - 2), badge, fill=(255, 255, 255, 255), font=font)

        out_file = ASSETS_DIR / f"{key}.png"
        img.save(out_file)
        paths[key] = str(out_file)
    return paths


def set_slide_bg(slide, color=BG_CREAM):
    background = slide.background
    fill = background.fill
    fill.solid()
    fill.fore_color.rgb = color


def add_header(slide, slide_num, category, title, subtitle="", accent_bg=PASTEL_BLUE, accent_fg=ACCENT_NAVY):
    set_slide_bg(slide, BG_CREAM)

    # Franja superior pastel decorativa
    top_bar = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), Inches(13.333), Inches(0.12))
    top_bar.fill.solid()
    top_bar.fill.fore_color.rgb = accent_bg
    top_bar.line.fill.background()

    # Pill de categoría
    pill = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.55), Inches(0.28), Inches(3.6), Inches(0.32))
    pill.fill.solid()
    pill.fill.fore_color.rgb = accent_bg
    pill.line.color.rgb = accent_fg
    pill.line.width = Pt(1)
    tf_p = pill.text_frame
    tf_p.word_wrap = False
    tf_p.margin_left = Inches(0.1)
    tf_p.margin_top = Inches(0.03)
    p = tf_p.paragraphs[0]
    p.text = f"DIAPOSITIVA {slide_num:02d}  ·  {category.upper()}"
    p.font.size = Pt(9.5)
    p.font.bold = True
    p.font.color.rgb = accent_fg
    p.font.name = "Segoe UI"

    # Título principal
    tb = slide.shapes.add_textbox(Inches(0.55), Inches(0.62), Inches(11.8), Inches(0.55))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.margin_left = 0
    tf.margin_top = 0
    p_t = tf.paragraphs[0]
    p_t.text = title
    p_t.font.size = Pt(22)
    p_t.font.bold = True
    p_t.font.color.rgb = TEXT_DARK
    p_t.font.name = "Segoe UI"

    if subtitle:
        p_s = tf.add_paragraph()
        p_s.text = subtitle
        p_s.font.size = Pt(11.5)
        p_s.font.color.rgb = TEXT_MUTED
        p_s.font.name = "Segoe UI"

    # Pie de página institucional
    footer = slide.shapes.add_textbox(Inches(0.55), Inches(7.12), Inches(12.2), Inches(0.28))
    tf_f = footer.text_frame
    p_f = tf_f.paragraphs[0]
    p_f.text = f"DWMusicBrainz  |  Ingeniería de Sistemas  ·  Bases de Datos Avanzadas  ·  Universidad Popular del Cesar  |  Pág. {slide_num} de 16"
    p_f.font.size = Pt(8.5)
    p_f.font.color.rgb = TEXT_MUTED
    p_f.font.name = "Segoe UI"


def add_pastel_card(slide, left, top, width, height, bg_color, border_color, title="", bullets=None, title_color=TEXT_DARK, font_size=10.5, header_badge=""):
    card = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(left), Inches(top), Inches(width), Inches(height))
    card.adjustments[0] = 0.04
    card.fill.solid()
    card.fill.fore_color.rgb = bg_color
    card.line.color.rgb = border_color
    card.line.width = Pt(1.5)

    tf = card.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = MSO_ANCHOR.TOP
    tf.margin_left = Inches(0.18)
    tf.margin_right = Inches(0.16)
    tf.margin_top = Inches(0.14)
    tf.margin_bottom = Inches(0.12)

    first_para = True
    if header_badge:
        p_b = tf.paragraphs[0]
        first_para = False
        p_b.text = header_badge
        p_b.font.size = Pt(9)
        p_b.font.bold = True
        p_b.font.color.rgb = title_color
        p_b.font.name = "Segoe UI"
        p_b.space_after = Pt(2)

    if title:
        p_t = tf.paragraphs[0] if first_para else tf.add_paragraph()
        first_para = False
        p_t.text = title
        p_t.font.size = Pt(font_size + 2)
        p_t.font.bold = True
        p_t.font.color.rgb = title_color
        p_t.font.name = "Segoe UI"
        p_t.space_after = Pt(5)

    if bullets:
        for b in bullets:
            p = tf.paragraphs[0] if first_para else tf.add_paragraph()
            first_para = False
            p.text = b
            p.font.size = Pt(font_size)
            p.font.color.rgb = TEXT_DARK
            p.font.name = "Segoe UI"
            p.space_after = Pt(3.5)
    return card


def style_table(table, col_widths, header_bg, row_bg_even=CARD_WHITE, row_bg_odd=PASTEL_SLATE, font_size=9.5):
    for idx, w in enumerate(col_widths):
        table.columns[idx].width = Inches(w)

    for r_idx, row in enumerate(table.rows):
        for c_idx, cell in enumerate(row.cells):
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
            cell.fill.solid()
            if r_idx == 0:
                cell.fill.fore_color.rgb = header_bg
            else:
                cell.fill.fore_color.rgb = row_bg_even if r_idx % 2 == 1 else row_bg_odd

            for p in cell.text_frame.paragraphs:
                p.font.name = "Segoe UI"
                if r_idx == 0:
                    p.font.size = Pt(font_size)
                    p.font.bold = True
                    p.font.color.rgb = TEXT_DARK
                else:
                    p.font.size = Pt(font_size - 0.5)
                    p.font.bold = (c_idx == 0)
                    p.font.color.rgb = TEXT_DARK


def build_presentation(output_path="docs/DWMusicBrainz_Sustentacion.pptx"):
    icons = generate_tool_icons()
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    blank_layout = prs.slide_layouts[6]

    # =========================================================================
    # SLIDE 1: PORTADA INSTITUCIONAL EN TONOS PASTELES
    # =========================================================================
    s1 = prs.slides.add_slide(blank_layout)
    set_slide_bg(s1, BG_CREAM)

    # Bloques decorativos pasteles suaves en el lateral derecho
    deco1 = s1.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(8.6), Inches(0.55), Inches(4.2), Inches(2.0))
    deco1.fill.solid()
    deco1.fill.fore_color.rgb = PASTEL_BLUE
    deco1.line.color.rgb = PASTEL_BLUE_BD

    deco2 = s1.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(8.6), Inches(2.75), Inches(4.2), Inches(2.0))
    deco2.fill.solid()
    deco2.fill.fore_color.rgb = PASTEL_LAVENDER
    deco2.line.color.rgb = PASTEL_LAV_BD

    deco3 = s1.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(8.6), Inches(4.95), Inches(4.2), Inches(2.0))
    deco3.fill.solid()
    deco3.fill.fore_color.rgb = PASTEL_MINT
    deco3.line.color.rgb = PASTEL_MINT_BD

    add_pastel_card(
        s1, 8.75, 0.7, 3.9, 1.7, PASTEL_BLUE, PASTEL_BLUE_BD,
        title="100% Datos Reales MusicBrainz",
        bullets=[
            "• Volcado oficial mbdump.tar.bz2 (7,1 GB).",
            "• Schema Sequence 31 (Octubre 2026).",
            "• Cero datos sintéticos o ficticios."
        ],
        title_color=ACCENT_NAVY, font_size=10, header_badge=" CAPA ORIGEN & SILVER (3NF)"
    )
    add_pastel_card(
        s1, 8.75, 2.9, 3.9, 1.7, PASTEL_LAVENDER, PASTEL_LAV_BD,
        title="Modelo Estrella Puro en Español",
        bullets=[
            "• 6 Dimensiones Conformadas (Patrón Key 0).",
            "• Hecho Histórico Diario: fact_produccion_musical.",
            "• 11 Métricas Numéricas 100% Aditivas (SUM)."
        ],
        title_color=ACCENT_PURPLE, font_size=10, header_badge=" CAPA GOLD (RALPH KIMBALL)"
    )
    add_pastel_card(
        s1, 8.75, 5.1, 3.9, 1.7, PASTEL_MINT, PASTEL_MINT_BD,
        title="Alto Rendimiento & Gobernanza",
        bullets=[
            "• ~98,6 M filas Silver | ~16 GB en disco.",
            "• 15 Particiones por fecha_key + 4 Vistas Mat.",
            "• Auditoría en meta.etl_audit y data_quality_log."
        ],
        title_color=ACCENT_TEAL, font_size=10, header_badge=" POSTGRESQL 16 + DOCKER + POWER BI"
    )

    # Panel principal de portada a la izquierda
    add_pastel_card(
        s1, 0.55, 0.55, 7.75, 6.4, CARD_WHITE, PASTEL_LAV_BD,
        title="", bullets=[]
    )
    tb1 = s1.shapes.add_textbox(Inches(0.85), Inches(0.85), Inches(7.2), Inches(5.8))
    tf1 = tb1.text_frame
    tf1.word_wrap = True

    p = tf1.paragraphs[0]
    p.text = "PROYECTO INTEGRADOR  ·  BASES DE DATOS AVANZADAS"
    p.font.size = Pt(11)
    p.font.bold = True
    p.font.color.rgb = ACCENT_PURPLE

    p2 = tf1.add_paragraph()
    p2.text = "\nImplementar un Data Warehouse Analítico de Alta Volumetría para la Industria Musical Global (DWMusicBrainz)"
    p2.font.size = Pt(24)
    p2.font.bold = True
    p2.font.color.rgb = ACCENT_NAVY
    p2.space_after = Pt(10)

    p3 = tf1.add_paragraph()
    p3.text = "Arquitectura Medallón (Silver 3NF → Gold Estrella Puro en Español) sobre PostgreSQL 16 en Docker y Explotación Analítica en Microsoft Power BI"
    p3.font.size = Pt(13)
    p3.font.color.rgb = TEXT_MUTED
    p3.space_after = Pt(20)

    p4 = tf1.add_paragraph()
    p4.text = (
        "• Autores: Juan Sebastián Rincón Farelo y equipo de Ingeniería de Datos\n"
        "• Programa: Ingeniería de Sistemas  —  5to Semestre Académico\n"
        "• Institución: Universidad Popular del Cesar (UPC)\n"
        "• Ubicación y Fecha: Valledupar, Cesar, Colombia  ·  Octubre de 2026"
    )
    p4.font.size = Pt(11.5)
    p4.font.color.rgb = TEXT_DARK

    # =========================================================================
    # SLIDE 2: CONTEXTO OLTP, PROBLEMA OPERACIONAL Y SOLUCIÓN DWH OLAP
    # =========================================================================
    s2 = prs.slides.add_slide(blank_layout)
    add_header(
        s2, 2, "Introducción y Planteamiento del Problema",
        "De la Base de Datos Transaccional (OLTP) al Data Warehouse (OLAP)",
        "Contexto de MusicBrainz en 3NF, el problema de usarlo para analítica y cómo nuestro DWH en estrella lo soluciona",
        PASTEL_ROSE, ACCENT_ROSE
    )

    add_pastel_card(
        s2, 0.55, 1.45, 3.9, 5.45, PASTEL_BLUE, PASTEL_BLUE_BD,
        header_badge="1 · CONTEXTO DE LA BD ORIGEN (OLTP)",
        title="MusicBrainz en 3ra Forma Normal",
        bullets=[
            "• Enciclopedia musical global mantenida por la MetaBrainz Foundation (Schema Sequence 31).",
            "• Diseñada para transacciones operacionales (OLTP): inserciones y ediciones comunitarias ACID.",
            "• Alta fragmentación relacional en 10 tablas normalizadas:",
            "  - area (120k), artist (3.02M), artist_credit_name (7.30M).",
            "  - release (5.86M), release_country (13.34M), release_unknown_country (484k).",
            "  - medium (6.43M), recording (40.60M), track (15M), isrc (6.50M).",
            "• Total procesado en origen: ~98,6 millones de registros."
        ],
        title_color=ACCENT_NAVY, font_size=10
    )

    add_pastel_card(
        s2, 4.7, 1.45, 3.9, 5.45, PASTEL_ROSE, PASTEL_ROSE_BD,
        header_badge="2 · PROBLEMA DE USAR UN OLTP PARA BI",
        title="Cuello de Botella en Consultas Masivas",
        bullets=[
            "• Encadenamiento de 8 a 10 JOINs por consulta: para relacionar una pista con su fecha real, país, formato y artista principal hay que cruzar decenas de millones de filas.",
            "• Ausencia de grano histórico consolidado: las tablas OLTP guardan entidades sueltas con flags booleanos y textos largos, no resúmenes históricos diarios.",
            "• Penalización severa de I/O y RAM: calcular tendencias por década o cobertura ISRC sobre 40,6M de grabaciones y 15M de pistas en 3NF agota la memoria y tarda minutos.",
            "• Riesgo de Fan Traps: cruzar por nombres de áreas o múltiples ISRCs duplica conteos si no se pre-agrega."
        ],
        title_color=ACCENT_ROSE, font_size=10
    )

    add_pastel_card(
        s2, 8.85, 1.45, 3.9, 5.45, PASTEL_MINT, PASTEL_MINT_BD,
        header_badge="3 · CÓMO NUESTRO DWH OLAP LO SOLUCIONA",
        title="Estrella Pura Histórica en Español",
        bullets=[
            "• Desacoplamiento Medallón (Silver → Gold): Silver limpia y tipa las 10 tablas 3NF; Gold consolida el modelo dimensional en español.",
            "• Tabla de Hechos Histórica Diaria (gold.fact_produccion_musical): agrupa por día (fecha_key) y las 5 dimensiones conformadas.",
            "• Cero textos y cero booleanos en hechos: solo llaves foráneas enteras y 11 métricas numéricas 100% aditivas (SUM).",
            "• Particionamiento por rango en fecha_key (15 particiones) + 4 Vistas Materializadas: consultas en < 0,10 s."
        ],
        title_color=ACCENT_TEAL, font_size=10
    )

    # =========================================================================
    # SLIDE 3: OBJETIVO GENERAL Y OBJETIVOS ESPECÍFICOS (TAXONOMÍA DE BLOOM)
    # =========================================================================
    s3 = prs.slides.add_slide(blank_layout)
    add_header(
        s3, 3, "Formulación Metodológica del Proyecto",
        "Objetivo General y Objetivos Específicos (Taxonomía de Bloom)",
        "El Objetivo General corresponde al título del proyecto; los Objetivos Específicos se formulan con verbos de Bloom sin explicación",
        PASTEL_LAVENDER, ACCENT_PURPLE
    )

    add_pastel_card(
        s3, 0.55, 1.45, 12.2, 1.45, PASTEL_LAVENDER, PASTEL_LAV_BD,
        header_badge="OBJETIVO GENERAL (ALINEADO AL TÍTULO DEL PROYECTO  ·  NIVEL CREAR / IMPLEMENTAR — BLOOM)",
        title="Implementar un Data Warehouse analítico de alta volumetría para la industria musical global (DWMusicBrainz) bajo arquitectura Medallón y modelo en estrella puro de Ralph Kimball en PostgreSQL 16.",
        bullets=[],
        title_color=ACCENT_PURPLE, font_size=12.5
    )

    # 6 Tarjetas para Objetivos Específicos (verbos de Bloom en infinitivo, directos y sin explicación adicional)
    bloom_objectives = [
        ("OBJETIVO ESPECÍFICO 1  ·  NIVEL APLICAR (BLOOM)", "Extraer los conjuntos de datos transaccionales reales del volcado oficial de MusicBrainz (Schema Sequence 31) hacia la capa de almacenamiento intermedio Silver en Tercera Forma Normal.", PASTEL_BLUE, PASTEL_BLUE_BD, ACCENT_NAVY),
        ("OBJETIVO ESPECÍFICO 2  ·  NIVEL ANALIZAR (BLOOM)", "Estandarizar la calidad de los datos mediante la aplicación de diez reglas de limpieza, tipado nativo, resolución de fechas históricas reales y vinculación de créditos de autoría.", PASTEL_MINT, PASTEL_MINT_BD, ACCENT_TEAL),
        ("OBJETIVO ESPECÍFICO 3  ·  NIVEL CREAR (BLOOM)", "Diseñar el modelo dimensional en estrella puro en español conformado por seis dimensiones con claves subrogadas y una tabla de hechos histórica diaria con métricas aditivas.", PASTEL_PEACH, PASTEL_PEACH_BD, ACCENT_AMBER),
        ("OBJETIVO ESPECÍFICO 4  ·  NIVEL APLICAR (BLOOM)", "Construir el pipeline automatizado de extracción, transformación y carga (ETL) mediante streaming en Python y sentencias SQL de agregación histórica por conjuntos.", PASTEL_ROSE, PASTEL_ROSE_BD, ACCENT_ROSE),
        ("OBJETIVO ESPECÍFICO 5  ·  NIVEL EVALUAR (BLOOM)", "Optimizar el rendimiento de las consultas analíticas mediante particionamiento físico declarativo por rangos de fecha, indexación B-Tree y cuatro vistas materializadas.", PASTEL_LEMON, PASTEL_LEMON_BD, ACCENT_AMBER),
        ("OBJETIVO ESPECÍFICO 6  ·  NIVEL EVALUAR (BLOOM)", "Validar la integridad referencial de cero huérfanos, la volumetría física en disco y las métricas aditivas para su explotación visual mediante medidas DAX en Power BI.", PASTEL_BLUE, PASTEL_BLUE_BD, ACCENT_NAVY),
    ]

    for idx, (badge, text_obj, bg, bd, col) in enumerate(bloom_objectives):
        col_i = idx % 2
        row_i = idx // 2
        left = 0.55 + col_i * 6.2
        top = 3.12 + row_i * 1.28
        add_pastel_card(
            s3, left, top, 5.95, 1.15, bg, bd,
            header_badge=badge,
            title="",
            bullets=[text_obj],
            title_color=col, font_size=10.5
        )

    # =========================================================================
    # SLIDE 4: REQUERIMIENTOS FUNCIONALES (RF01 A RF08 REALES DEL PROYECTO)
    # =========================================================================
    s4 = prs.slides.add_slide(blank_layout)
    add_header(
        s4, 4, "Especificación de Requerimientos Analíticos",
        "Requerimientos Funcionales del Sistema (RF01 — RF08)",
        "Alineados estrictamente con las vistas materializadas, dimensiones en español y métricas aditivas implementadas",
        PASTEL_BLUE, ACCENT_NAVY
    )

    rf_items = [
        ("RF01 · Ranking Top N de Catálogo y Producción", "Obtener el ranking de artistas con mayor volumen de lanzamientos (SUM(lanzamientos_total)), pistas (SUM(pistas_total)), duración acumulada y cobertura ISRC por país y década.", PASTEL_BLUE, PASTEL_BLUE_BD, ACCENT_NAVY),
        ("RF02 · Métricas por Formato e Idioma", "Comparar la duración promedio ponderada (SUM(duracion_total_segundos) / SUM(pistas_completas_total)) y el volumen de producción según formato (Vinilo, CD, Digital) e idioma (dim_idioma).", PASTEL_LAVENDER, PASTEL_LAV_BD, ACCENT_PURPLE),
        ("RF03 · Drill-Down Geográfico y Temporal", "Permitir la navegación jerárquica geográfica (nombre_pais → tipo_area → nombre_area en dim_geografia) y temporal (siglo → decada → anio → trimestre → mes → dia en dim_fecha).", PASTEL_MINT, PASTEL_MINT_BD, ACCENT_TEAL),
        ("RF04 · Penetración Digital vs Físico y Pistas Largas", "Cuantificar la transición entre soportes físicos y digitales en dim_formato y la proporción de canciones largas mayores a 5 minutos (SUM(pistas_largas_total) / SUM(pistas_total)).", PASTEL_PEACH, PASTEL_PEACH_BD, ACCENT_AMBER),
        ("RF05 · Correlación Estadística Año vs Duración", "Calcular matemáticamente la correlación de Pearson (corr()) entre el año histórico de publicación (anio) y la duración promedio para demostrar el acortamiento en la era del streaming.", PASTEL_ROSE, PASTEL_ROSE_BD, ACCENT_ROSE),
        ("RF06 · Tasa de Formalización Fonográfica ISRC", "Determinar el porcentaje de pistas registradas con código internacional ISRC (SUM(pistas_con_isrc_total) * 100 / SUM(pistas_total)) segmentado por país y tipo de artista.", PASTEL_LEMON, PASTEL_LEMON_BD, ACCENT_AMBER),
        ("RF07 · Densidad de Pistas y Soportes por Lanzamiento", "Analizar la relación aditiva de pistas por lanzamiento (SUM(pistas_total) / SUM(lanzamientos_total)) y pistas por soporte (SUM(pistas_total) / SUM(soportes_total)) según el perfil de empaque.", PASTEL_BLUE, PASTEL_BLUE_BD, ACCENT_NAVY),
        ("RF08 · Detección de Catálogo y Artistas Emergentes", "Identificar los artistas debutantes en la última década (anio_inicio >= 2015 en dim_artista) con mayor producción acumulada y 100% de formalización ISRC.", PASTEL_MINT, PASTEL_MINT_BD, ACCENT_TEAL),
    ]

    for idx, (title_rf, desc_rf, bg, bd, col) in enumerate(rf_items):
        col_i = idx % 2
        row_i = idx // 2
        left = 0.55 + col_i * 6.2
        top = 1.42 + row_i * 1.38
        add_pastel_card(
            s4, left, top, 5.95, 1.26, bg, bd,
            title=title_rf,
            bullets=[desc_rf],
            title_color=col, font_size=9.8
        )

    # =========================================================================
    # SLIDE 5: REQUERIMIENTOS NO FUNCIONALES (RNF01 A RNF09 REALES)
    # =========================================================================
    s5 = prs.slides.add_slide(blank_layout)
    add_header(
        s5, 5, "Calidad, Rendimiento y Estrés Físico",
        "Requerimientos No Funcionales del Proyecto (RNF01 — RNF09)",
        "Criterios técnicos verificados mediante los scripts del repositorio (ingest_tracks_sliced.py, run_gold_pipeline.py, verify_dwh.py)",
        PASTEL_MINT, ACCENT_TEAL
    )

    rnf_rows = [
        ["Código", "Criterio Técnico", "Requisito Exigido en el Proyecto", "Implementación Real en DWMusicBrainz", "Estado"],
        ["RNF01", "Ingesta por Streaming", "Lectura por bloques sin desbordar la memoria RAM del host.", "Clase MaxLineReader con buffer de 128 KB hacia COPY FROM STDIN.", "CUMPLIDO"],
        ["RNF02", "Huella Física en Disco", "Almacenamiento físico en PostgreSQL superior a 3,0 GB.", "~16 GB consolidados en disco entre capas Silver, Gold y Meta.", "SUPERADO"],
        ["RNF03", "Alta Volumetría Real", "Procesar más de 10 millones de registros musicales reales.", "~98,6 M de filas en Silver (10 tablas) y 15 M de pistas agregadas en Gold.", "SUPERADO"],
        ["RNF04", "Cero Datos Sintéticos", "Prohibición absoluta de datos simulados o generados al azar.", "100% extraído del dump oficial mbdump.tar.bz2 (Schema Sequence 31).", "CUMPLIDO"],
        ["RNF05", "Idempotencia ETL", "Re-ejecución limpia del pipeline sin duplicar registros.", "TRUNCATE RESTART IDENTITY CASCADE y ON CONFLICT DO UPDATE.", "CUMPLIDO"],
        ["RNF06", "Auditoría y Linaje", "Bitácora automática de lotes, filas, tiempos y reglas de calidad.", "Tablas meta.etl_audit y meta.data_quality_log pobladas en Python.", "CUMPLIDO"],
        ["RNF07", "SLA de Consultas OLAP", "Tiempo de respuesta inferior a 3,0 segundos en agregaciones.", "< 0,10 segundos mediante Partition Pruning y 4 Vistas Materializadas.", "ÓPTIMO"],
        ["RNF08", "Integridad Referencial", "Cero registros huérfanos entre la tabla de hechos y dimensiones.", "Patrón Fila Cero (Key 0) en las 6 dimensiones + COALESCE(key, 0).", "0 HUÉRFANOS"],
        ["RNF09", "Portabilidad y Tuning", "Infraestructura aislada y reproducible con memoria optimizada.", "Docker Compose (postgres:16, puerto 5435, shared_buffers=1GB, shm=1gb).", "CUMPLIDO"],
    ]

    t_shape5 = s5.shapes.add_table(len(rnf_rows), 5, Inches(0.55), Inches(1.45), Inches(12.2), Inches(5.45))
    table5 = t_shape5.table
    for r_i, row in enumerate(rnf_rows):
        for c_i, val in enumerate(row):
            table5.cell(r_i, c_i).text = val
    style_table(table5, [0.85, 1.95, 3.4, 4.7, 1.3], PASTEL_MINT, CARD_WHITE, PASTEL_SLATE, font_size=9.5)

    # =========================================================================
    # SLIDE 6: ARQUITECTURA MEDALLÓN UTILIZADA
    # =========================================================================
    s6 = prs.slides.add_slide(blank_layout)
    add_header(
        s6, 6, "Diseño Arquitectónico del Sistema",
        "Arquitectura Medallón Implementada (Raw → Silver → Gold + Meta)",
        "Separación física y lógica en esquemas de PostgreSQL 16 para garantizar trazabilidad, limpieza 3NF y modelo estrella puro",
        PASTEL_PEACH, ACCENT_AMBER
    )

    add_pastel_card(
        s6, 0.55, 1.45, 2.85, 4.15, PASTEL_PEACH, PASTEL_PEACH_BD,
        header_badge="1 · ORIGEN (BRONZE / RAW)",
        title="Volcado Oficial TSV",
        bullets=[
            "• Archivo maestro: mbdump.tar.bz2 (7,1 GB comprimido).",
            "• Extracción quirúrgica bajo demanda hacia data/raw/mbdump/.",
            "• 11 archivos TSV planos (incluye el catálogo language) sin encabezados y con nulos representados como \\N.",
            "• metadatos verificados: SCHEMA_SEQUENCE = 31."
        ],
        title_color=ACCENT_AMBER, font_size=9.8
    )

    add_pastel_card(
        s6, 3.65, 1.45, 2.85, 4.15, PASTEL_BLUE, PASTEL_BLUE_BD,
        header_badge="2 · CAPA PLATA (ESQUEMA silver)",
        title="Staging Relacional 3NF",
        bullets=[
            "• 10 tablas normalizadas en 3NF (~98,6 M de filas).",
            "• Tipado fuerte nativo (INTEGER, SMALLINT, UUID, BOOLEAN, TIMESTAMPTZ).",
            "• Uso de tipo TEXT (TOAST) para soportar títulos de > 2.000 caracteres.",
            "• Incluye release_country y artist_credit_name."
        ],
        title_color=ACCENT_NAVY, font_size=9.8
    )

    add_pastel_card(
        s6, 6.75, 1.45, 2.85, 4.15, PASTEL_LAVENDER, PASTEL_LAV_BD,
        header_badge="3 · CAPA ORO (ESQUEMA gold)",
        title="Estrella Pura en Español",
        bullets=[
            "• 6 Dimensiones Conformadas en español con Surrogate Keys y Fila Cero (Key 0).",
            "• 1 Tabla de Hechos Histórica Diaria (fact_produccion_musical) particionada por fecha_key.",
            "• Solo FKs y 11 métricas numéricas 100% aditivas.",
            "• 4 Vistas Materializadas indexadas."
        ],
        title_color=ACCENT_PURPLE, font_size=9.8
    )

    add_pastel_card(
        s6, 9.85, 1.45, 2.9, 4.15, PASTEL_MINT, PASTEL_MINT_BD,
        header_badge="4 · CONSUMO BI (POWER BI)",
        title="Analítica & Medidas DAX",
        bullets=[
            "• Conexión a PostgreSQL (esquema gold) en modo Import.",
            "• Relaciones 1:* unidireccionales desde las 6 dimensiones hacia el hecho.",
            "• Medidas DAX basadas en SUM() directo sobre métricas aditivas.",
            "• Respuesta a los requerimientos RF01 a RF08."
        ],
        title_color=ACCENT_TEAL, font_size=9.8
    )

    # Barra transversal inferior: Esquema Meta
    add_pastel_card(
        s6, 0.55, 5.78, 12.2, 1.18, PASTEL_ROSE, PASTEL_ROSE_BD,
        header_badge="CAPA TRANSVERSAL DE GOBERNANZA Y AUDITORÍA  ·  ESQUEMA meta (sql/meta/01_schema_meta.sql)",
        title="Control Contable de Lotes (meta.etl_audit) y Certificación de Calidad (meta.data_quality_log)",
        bullets=[
            "Registra cada ejecución por capa (RAW_TO_SILVER, SILVER_TO_GOLD), tabla destino, operación (BULK_COPY, HISTORICAL_AGGREGATION), filas leídas/insertadas, duración en segundos y pruebas automáticas de 0 huérfanos."
        ],
        title_color=ACCENT_ROSE, font_size=9.5
    )

    # =========================================================================
    # SLIDE 7: ROLES EN CADA ETAPA (INGENIERO DE DATOS, MODELADOR, ANALISTA DE BI)
    # =========================================================================
    s7 = prs.slides.add_slide(blank_layout)
    add_header(
        s7, 7, "Organización del Equipo y Responsabilidades",
        "Roles en Cada Etapa del Proyecto y sus Actividades Específicas",
        "Distribución de actividades para los 3 roles oficiales: Ingeniero de Datos, Modelador y Analista de BI",
        PASTEL_LAVENDER, ACCENT_PURPLE
    )

    roles_matrix = [
        [
            "Rol del Proyecto",
            "Etapa 1: Infraestructura e Ingesta (Raw → Silver)",
            "Etapa 2: Transformación y Calidad (Silver → Gold)",
            "Etapa 3: Optimización y Explotación (Gold → Power BI)"
        ],
        [
            "1. Ingeniero de Datos\n(Data Engineer)",
            "• Configurar el contenedor Docker con PostgreSQL 16 (puerto 5435) y tuning de memoria (shared_buffers=1GB, shm_size=1gb).\n• Desarrollar ingest_silver.py para extraer bajo demanda los 10 TSV desde mbdump.tar.bz2.\n• Implementar MaxLineReader (buffer 128 KB) en ingest_tracks_sliced.py para cargar 15M de pistas vía COPY sin saturar RAM.",
            "• Codificar las reglas de limpieza EDA (E01 a E10) en SQL set-based (utf-8-sig, TEXT TOAST, deduplicación ISRC).\n• Construir el orquestador run_gold_pipeline.py con registro transaccional en meta.etl_audit.\n• Automatizar las 10 pruebas de calidad en meta.data_quality_log.",
            "• Ejecutar el refresco de las 4 vistas materializadas (REFRESH MATERIALIZED VIEW).\n• Auditar la huella física en disco (~16 GB) y tiempos de ejecución con scripts/verify_dwh.py."
        ],
        [
            "2. Modelador\n(Dimensional Modeler)",
            "• Analizar el modelo relacional 3NF de MusicBrainz (Schema Sequence 31).\n• Identificar la necesidad de incluir release_country, release_unknown_country y artist_credit_name en Silver para no perder fechas reales ni autoría.",
            "• Definir el Grano Histórico Diario de la tabla de hechos gold.fact_produccion_musical.\n• Diseñar las 6 dimensiones conformadas en español (dim_fecha, dim_artista, dim_lanzamiento, dim_geografia, dim_formato, dim_idioma) con Surrogate Keys y Fila Cero (Key 0).\n• Eliminar textos y booleanos del hecho, definiendo las 11 métricas aditivas.",
            "• Diseñar las 15 particiones físicas por rango en fecha_key (04_indexes_partitions.sql) y los índices B-Tree.\n• Certificar el cumplimiento de Cero Huérfanos y la eliminación de Fan Traps (JOIN por area_id)."
        ],
        [
            "3. Analista de BI\n(BI Analyst)",
            "• Definir las preguntas de negocio de la industria musical y traducirlas en los requerimientos funcionales RF01 a RF08.\n• Establecer los umbrales de SLA (< 3,0 s) para los tableros.",
            "• Especificar las jerarquías analíticas de navegación Drill-Down: temporal (Siglo > Década > Año > Mes > Día) y geográfica (País > Tipo de Área > Área).\n• Definir las categorías comerciales de dim_formato y los perfiles de dim_lanzamiento.",
            "• Diseñar las 4 vistas materializadas analíticas (05_aggregations.sql).\n• Programar el catálogo de medidas DAX 100% aditivas (SUM) en Power BI (POWER_BI_MEASURES.md) y elaborar el storytelling de hallazgos (correlación Pearson, transición digital e ISRC)."
        ]
    ]

    t_shape7 = s7.shapes.add_table(4, 4, Inches(0.55), Inches(1.42), Inches(12.2), Inches(5.55))
    table7 = t_shape7.table
    for r_i, row in enumerate(roles_matrix):
        for c_i, val in enumerate(row):
            table7.cell(r_i, c_i).text = val
    style_table(table7, [1.8, 3.45, 3.55, 3.4], PASTEL_LAVENDER, CARD_WHITE, PASTEL_BLUE, font_size=8.8)

    # =========================================================================
    # SLIDE 8: HERRAMIENTAS IMPLEMENTADAS Y EL POR QUÉ DE SU USO (CON IMÁGENES)
    # =========================================================================
    s8 = prs.slides.add_slide(blank_layout)
    add_header(
        s8, 8, "Stack Tecnológico e Infraestructura",
        "Herramientas Implementadas y Justificación Técnica de su Uso",
        "Cada herramienta responde a una necesidad arquitectónica específica de rendimiento, aislamiento o explotación OLAP",
        PASTEL_BLUE, ACCENT_NAVY
    )

    tools_cards = [
        (
            "postgres", "PostgreSQL 16 (Motor DWH)", PASTEL_BLUE, PASTEL_BLUE_BD, ACCENT_NAVY,
            [
                "• ¿Por qué se usó?: Soporte nativo de Particionamiento Declarativo por Rango (fecha_key) con Partition Pruning.",
                "• Ingesta ultrarrápida vía protocolo COPY FROM STDIN (> 130.000 filas/seg) y tipo TEXT con compresión TOAST.",
                "• Soporta Vistas Materializadas indexadas y paralelismo."
            ]
        ),
        (
            "docker", "Docker & Docker Compose v2", PASTEL_MINT, PASTEL_MINT_BD, ACCENT_TEAL,
            [
                "• ¿Por qué se usó?: Garantiza portabilidad y aislamiento en el puerto 5435 sin contaminar el sistema operativo host.",
                "• Permite configurar shm_size: 1gb para evitar fallos de Dynamic Shared Memory al agrupar millones de filas.",
                "• Persistencia asegurada en el volumen mb_pgdata."
            ]
        ),
        (
            "python", "Python 3.12+ (Orquestador ETL)", PASTEL_LEMON, PASTEL_LEMON_BD, ACCENT_AMBER,
            [
                "• ¿Por qué se usó?: Orquestación directa y liviana sin la sobrecarga de memoria de una JVM (Spark/Hadoop).",
                "• Permite implementar la clase MaxLineReader con buffer de 128 KB para filtrar 15M de pistas en flujo continuo.",
                "• Automatiza la extracción desde mbdump.tar.bz2."
            ]
        ),
        (
            "psycopg2", "psycopg2-binary (Driver C libpq)", PASTEL_PEACH, PASTEL_PEACH_BD, ACCENT_AMBER,
            [
                "• ¿Por qué se usó?: Driver compilado en C que expone el método copy_expert() sobre la API nativa libpq.",
                "• Transfiere bloques de datos desde Python hacia el heap de PostgreSQL sin pasar por cursores INSERT fila a fila.",
                "• Manejo transaccional de auditoría en meta.etl_audit."
            ]
        ),
        (
            "powerbi", "Microsoft Power BI Desktop (DAX)", PASTEL_ROSE, PASTEL_ROSE_BD, ACCENT_ROSE,
            [
                "• ¿Por qué se usó?: Su motor columnar in-memory VertiPaq comprime de forma óptima los modelos en estrella puros.",
                "• Aprovecha las relaciones 1:* en español y evalúa todas las métricas mediante funciones SUM() de alta velocidad.",
                "• Soporta navegación Drill-Down y correlación Pearson."
            ]
        ),
        (
            "dbeaver", "DBeaver, psql & Git / GitHub", PASTEL_LAVENDER, PASTEL_LAV_BD, ACCENT_PURPLE,
            [
                "• ¿Por qué se usó?: DBeaver y psql permiten inspeccionar los planes físicos EXPLAIN ANALYZE y verificar el Partition Pruning.",
                "• Git y GitHub aseguran control de versiones bajo Conventional Commits y trazabilidad del código SQL/Python.",
                "• ReportLab genera la documentación editorial en PDF."
            ]
        ),
    ]

    for idx, (icon_key, t_title, bg, bd, col, t_bullets) in enumerate(tools_cards):
        col_i = idx % 2
        row_i = idx // 2
        left = 0.55 + col_i * 6.2
        top = 1.42 + row_i * 1.82

        add_pastel_card(s8, left, top, 5.95, 1.68, bg, bd, title="", bullets=[])
        # Insertar imagen PNG de la herramienta a la izquierda de la tarjeta
        s8.shapes.add_picture(icons[icon_key], Inches(left + 0.14), Inches(top + 0.22), width=Inches(1.22), height=Inches(1.22))

        tb_t = s8.shapes.add_textbox(Inches(left + 1.45), Inches(top + 0.08), Inches(4.4), Inches(1.52))
        tf_t = tb_t.text_frame
        tf_t.word_wrap = True
        p0 = tf_t.paragraphs[0]
        p0.text = t_title
        p0.font.size = Pt(11.5)
        p0.font.bold = True
        p0.font.color.rgb = col
        p0.space_after = Pt(3)
        for b in t_bullets:
            pb = tf_t.add_paragraph()
            pb.text = b
            pb.font.size = Pt(8.8)
            pb.font.color.rgb = TEXT_DARK
            pb.space_after = Pt(2)

    # =========================================================================
    # SLIDE 9: VOLUMETRÍA OFICIAL Y DIMENSIONAMIENTO FÍSICO
    # =========================================================================
    s9 = prs.slides.add_slide(blank_layout)
    add_header(
        s9, 9, "Métricas de Escala y Almacenamiento",
        "Volumetría Oficial por Capa y Dimensionamiento en Disco",
        "Consolidado de las 10 tablas de la capa Silver (~98,6 M de filas) y las entidades del Modelo Estrella en Gold (~16 GB)",
        PASTEL_MINT, ACCENT_TEAL
    )

    vol_silver = [
        ["Tabla Capa Silver (3NF)", "Filas Reales", "Disco", "Propósito en el DWH"],
        ["silver.recording", "40.595.893", "5.854 MB", "Grabación maestra (duración y video)"],
        ["silver.track", "15.000.000", "2.865 MB", "Pista en soporte (base de agregación)"],
        ["silver.isrc", "6.502.252", "798 MB", "Código internacional ISRC por grabación"],
        ["silver.medium", "6.426.136", "988 MB", "Soporte físico/digital y formato"],
        ["silver.artist_credit_name", "7.301.698", "741 MB", "Vínculo exacto a artist.id (position=0)"],
        ["silver.release", "5.858.206", "1.110 MB", "Lanzamiento (estado, empaque, idioma)"],
        ["silver.release_country", "13.337.269", "1.299 MB", "Fecha histórica real (año/mes/día) y país"],
        ["silver.artist", "3.015.712", "499 MB", "Músicos solistas, bandas y orquestas"],
        ["silver.release_unknown_country", "484.343", "36 MB", "Fecha histórica real sin país asignado"],
        ["silver.area", "120.108", "16 MB", "Países, regiones y ciudades"],
        ["TOTAL CAPA SILVER (10 Tablas)", "98.641.617", "14.206 MB", "Staging Relacional Completo 3NF"],
    ]

    t_s9_left = s9.shapes.add_table(len(vol_silver), 4, Inches(0.55), Inches(1.42), Inches(6.25), Inches(5.5))
    style_table(t_s9_left.table, [1.95, 1.15, 0.9, 2.25], PASTEL_BLUE, CARD_WHITE, PASTEL_SLATE, font_size=8.5)
    for r_i, row in enumerate(vol_silver):
        for c_i, val in enumerate(row):
            t_s9_left.table.cell(r_i, c_i).text = val
    style_table(t_s9_left.table, [1.95, 1.15, 0.9, 2.25], PASTEL_BLUE, CARD_WHITE, PASTEL_SLATE, font_size=8.5)

    vol_gold = [
        ["Objeto Capa Gold (Español)", "Filas / Reg.", "Disco", "Grano / Rol Dimensional"],
        ["gold.fact_produccion_musical", "2.967.681", "570 MB", "Hecho diario (consolida 15M pistas)"],
        ["gold.dim_artista", "3.015.713", "1.476 MB", "Artistas únicos + Key 0"],
        ["gold.dim_geografia", "120.109", "19 MB", "Áreas geográficas y países + Key 0"],
        ["gold.dim_fecha", "47.847", "6 MB", "Calendario diario 1900–2030 + Key 0"],
        ["gold.dim_idioma", "354", "< 1 MB", "Idiomas ISO 639-3 + Key 0"],
        ["gold.dim_lanzamiento", "313", "< 1 MB", "Perfiles (Estado + Empaque + Calidad)"],
        ["gold.dim_formato", "115", "< 1 MB", "Formatos y categoría física/digital"],
        ["gold.mv_analitica_artistas", "690.454", "131 MB", "Vista Mat. RF01, RF06 y RF08"],
        ["Otras 3 Vistas Materializadas", "4.711", "< 1 MB", "Tendencias anuales, formatos y geo"],
    ]

    t_s9_right = s9.shapes.add_table(len(vol_gold), 4, Inches(7.0), Inches(1.42), Inches(5.75), Inches(3.9))
    for r_i, row in enumerate(vol_gold):
        for c_i, val in enumerate(row):
            t_s9_right.table.cell(r_i, c_i).text = val
    style_table(t_s9_right.table, [1.9, 1.05, 0.85, 1.95], PASTEL_LAVENDER, CARD_WHITE, PASTEL_SLATE, font_size=8.5)

    add_pastel_card(
        s9, 7.0, 5.48, 5.75, 1.44, PASTEL_MINT, PASTEL_MINT_BD,
        header_badge="CUMPLIMIENTO HOLGADO DEL RNF02 Y RNF03",
        title="Huella Total ~16 GB en PostgreSQL 16 (Meta: > 3,0 GB)",
        bullets=[
            "• Supera más de 5 veces el umbral mínimo de almacenamiento físico exigido.",
            "• Al modelar dim_lanzamiento por perfil (313 filas en vez de 5,8M), Power BI opera en memoria con máxima compresión."
        ],
        title_color=ACCENT_TEAL, font_size=9.2
    )

    # =========================================================================
    # SLIDE 10: DISEÑO DEL MODELO EN ESTRELLA PURO EN ESPAÑOL
    # =========================================================================
    s10 = prs.slides.add_slide(blank_layout)
    add_header(
        s10, 10, "Modelado Dimensional (Ralph Kimball)",
        "Diseño del Modelo en Estrella Puro en Español (Capa Gold)",
        "Tabla de hechos histórica diaria centrada exclusivamente en Claves Foráneas (FKs) y 11 Métricas Numéricas 100% Aditivas",
        PASTEL_LAVENDER, ACCENT_PURPLE
    )

    # Tarjeta central: Tabla de Hechos
    add_pastel_card(
        s10, 4.15, 1.45, 5.0, 5.48, PASTEL_LAVENDER, ACCENT_PURPLE,
        header_badge="TABLA DE HECHOS HISTÓRICA DIARIA (PARTICIONADA)",
        title="gold.fact_produccion_musical",
        bullets=[
            "🔑 CLAVE PRIMARIA Y FORÁNEAS CONFORMADAS:",
            "  • hecho_key (BIGSERIAL) + fecha_key (PK Compuesta)",
            "  • fecha_key (INTEGER)  →  gold.dim_fecha",
            "  • artista_key (INTEGER)  →  gold.dim_artista",
            "  • lanzamiento_key (INTEGER)  →  gold.dim_lanzamiento",
            "  • geografia_key (INTEGER)  →  gold.dim_geografia",
            "  • formato_key (INTEGER)  →  gold.dim_formato",
            "  • idioma_key (INTEGER)  →  gold.dim_idioma",
            "📊 11 MÉTRICAS NUMÉRICAS 100% ADITIVAS (SUM):",
            "  1. lanzamientos_total (INTEGER)",
            "  2. soportes_total (INTEGER)",
            "  3. pistas_total (INTEGER)",
            "  4. grabaciones_unicas_total (INTEGER)",
            "  5. duracion_total_ms (BIGINT)",
            "  6. duracion_total_segundos (NUMERIC(14,2))",
            "  7. duracion_total_minutos (NUMERIC(14,2))",
            "  8. pistas_con_isrc_total (INTEGER)",
            "  9. pistas_largas_total (INTEGER  ·  > 5 min)",
            "  10. pistas_video_total (INTEGER)",
            "  11. pistas_completas_total (INTEGER  ·  duración > 0)"
        ],
        title_color=ACCENT_PURPLE, font_size=9.1
    )

    # 3 Dimensiones a la izquierda
    add_pastel_card(
        s10, 0.55, 1.45, 3.35, 1.72, PASTEL_BLUE, PASTEL_BLUE_BD,
        header_badge="DIMENSIÓN 1  ·  1:N (fecha_key)",
        title="gold.dim_fecha (47.847 filas)",
        bullets=[
            "• Grano diario continuo (1900 a 2030).",
            "• Jerarquía: siglo → decada → anio → trimestre → mes → dia."
        ],
        title_color=ACCENT_NAVY, font_size=9.2
    )
    add_pastel_card(
        s10, 0.55, 3.33, 3.35, 1.72, PASTEL_MINT, PASTEL_MINT_BD,
        header_badge="DIMENSIÓN 2  ·  1:N (artista_key)",
        title="gold.dim_artista (3,02 M filas)",
        bullets=[
            "• Solistas, bandas, coros y orquestas.",
            "• Atributos: nombre_artista, tipo_artista, genero, nombre_pais, anio_inicio."
        ],
        title_color=ACCENT_TEAL, font_size=9.2
    )
    add_pastel_card(
        s10, 0.55, 5.21, 3.35, 1.72, PASTEL_PEACH, PASTEL_PEACH_BD,
        header_badge="DIMENSIÓN 3  ·  1:N (lanzamiento_key)",
        title="gold.dim_lanzamiento (313)",
        bullets=[
            "• Perfil analítico del lanzamiento.",
            "• Combina estado_lanzamiento, tipo_empaque y calidad_datos."
        ],
        title_color=ACCENT_AMBER, font_size=9.2
    )

    # 3 Dimensiones a la derecha
    add_pastel_card(
        s10, 9.4, 1.45, 3.35, 1.72, PASTEL_ROSE, PASTEL_ROSE_BD,
        header_badge="DIMENSIÓN 4  ·  1:N (geografia_key)",
        title="gold.dim_geografia (120.109)",
        bullets=[
            "• Ubicación geográfica normalizada.",
            "• Atributos: area_id, nombre_area, tipo_area, nombre_pais."
        ],
        title_color=ACCENT_ROSE, font_size=9.2
    )
    add_pastel_card(
        s10, 9.4, 3.33, 3.35, 1.72, PASTEL_LEMON, PASTEL_LEMON_BD,
        header_badge="DIMENSIÓN 5  ·  1:N (formato_key)",
        title="gold.dim_formato (115 filas)",
        bullets=[
            "• Soportes físicos, ópticos y digitales.",
            "• Atributos: nombre_formato, categoria_formato."
        ],
        title_color=ACCENT_AMBER, font_size=9.2
    )
    add_pastel_card(
        s10, 9.4, 5.21, 3.35, 1.72, PASTEL_BLUE, PASTEL_BLUE_BD,
        header_badge="DIMENSIÓN 6  ·  1:N (idioma_key)",
        title="gold.dim_idioma (354 filas)",
        bullets=[
            "• Estándar ISO 639-3 de publicación.",
            "• Atributos: idioma_id, nombre_idioma, codigo_iso."
        ],
        title_color=ACCENT_NAVY, font_size=9.2
    )

    # =========================================================================
    # SLIDE 11: EXPLICACIÓN DE LAS 6 DIMENSIONES Y SUS ATRIBUTOS EXACTOS
    # =========================================================================
    s11 = prs.slides.add_slide(blank_layout)
    add_header(
        s11, 11, "Diccionario Dimensional Exacto",
        "Explicación de las 6 Dimensiones Conformadas y sus Atributos",
        "Visualización exhaustiva de todas las columnas creadas en sql/gold/03_dimensions_facts.sql",
        PASTEL_BLUE, ACCENT_NAVY
    )

    dims_detail = [
        (
            "1. gold.dim_fecha (47.847 filas)", PASTEL_BLUE, PASTEL_BLUE_BD, ACCENT_NAVY,
            [
                "• PK: fecha_key (INTEGER YYYYMMDD, 0 = 'Sin Fecha').",
                "• Atributos: fecha_completa (DATE), anio (INT), trimestre (INT), nombre_trimestre ('Q1'..'Q4'), mes (INT), nombre_mes ('Enero'..), nombre_mes_corto ('Ene'..), dia (INT), dia_semana (1..7), nombre_dia ('Lunes'..), es_fin_de_semana (BOOL), decada ('1970s'..), siglo ('Siglo XX' / 'Siglo XXI').",
                "• Rol: Eje temporal continuo 1900–2030 alimentado con las fechas reales de release_country."
            ]
        ),
        (
            "2. gold.dim_artista (3.015.713 filas)", PASTEL_MINT, PASTEL_MINT_BD, ACCENT_TEAL,
            [
                "• PK: artista_key (SERIAL)  |  BK: artista_id (INTEGER UK).",
                "• Atributos: artista_gid (UUID), nombre_artista (TEXT), nombre_orden (TEXT), tipo_artista ('Persona / Solista', 'Grupo / Banda', 'Orquesta', 'Coro'), genero ('Masculino', 'Femenino', 'No Binario'), area_id (INT), nombre_area (TEXT), nombre_pais (TEXT), anio_inicio, anio_fin, finalizado (BOOL), creado_en.",
                "• Rol: Autoría musical resuelta vía artist_credit_name (position = 0)."
            ]
        ),
        (
            "3. gold.dim_lanzamiento (313 perfiles)", PASTEL_LAVENDER, PASTEL_LAV_BD, ACCENT_PURPLE,
            [
                "• PK: lanzamiento_key (SERIAL)  |  UK: (estado_id, empaque_id, calidad_id).",
                "• Atributos: estado_lanzamiento ('Oficial', 'Promocional', 'Bootleg / No Oficial', 'Pseudo-Release'), tipo_empaque ('Jewel Case', 'Digipak', 'Gatefold Cover (Vinilo)', 'Sin Embalaje (Digital)'), calidad_datos ('Alta', 'Normal', 'Baja'), creado_en.",
                "• Rol: Agrupa por perfil comercial para que lanzamientos_total sume múltiples álbumes por día."
            ]
        ),
        (
            "4. gold.dim_geografia (120.109 filas)", PASTEL_PEACH, PASTEL_PEACH_BD, ACCENT_AMBER,
            [
                "• PK: geografia_key (SERIAL)  |  BK: area_id (INTEGER UK).",
                "• Atributos: area_gid (UUID), nombre_area (TEXT), tipo_area ('País', 'Subdivisión', 'Condado', 'Municipio', 'Ciudad', 'Distrito', 'Isla'), nombre_pais (TEXT), creado_en.",
                "• Rol: Ubicación del evento de lanzamiento (release_country.country) o procedencia del artista (artist.area), unida por area_id entero."
            ]
        ),
        (
            "5. gold.dim_formato (115 filas)", PASTEL_ROSE, PASTEL_ROSE_BD, ACCENT_ROSE,
            [
                "• PK: formato_key (SERIAL)  |  BK: formato_id (INTEGER UK).",
                "• Atributos: nombre_formato ('CD', 'Vinilo 12\"', 'Digital Media', 'Cassette', 'FLAC', 'MP3', 'Blu-ray'), categoria_formato ('Digital / Streaming', 'Físico / Vinilo', 'Físico / Óptico', 'Físico / Magnético', 'Otros Formatos').",
                "• Rol: Permite analizar la evolución tecnológica del soporte físico al streaming."
            ]
        ),
        (
            "6. gold.dim_idioma (354 filas)", PASTEL_LEMON, PASTEL_LEMON_BD, ACCENT_AMBER,
            [
                "• PK: idioma_key (SERIAL)  |  BK: idioma_id (INTEGER UK).",
                "• Atributos: nombre_idioma (nombre oficial del catálogo silver.language: 'English', 'Spanish', 'Japanese', 'German', 'French', '[No linguistic content]', '[Multiple languages]'; clave 0 = 'Idioma No Especificado'), codigo_iso ISO 639-3 ('eng', 'spa', 'jpn', 'zxx', 'mul', 'und').",
                "• Rol: Clasificación lingüística ISO 639-3, resuelta con JOIN al catálogo oficial silver.language (7.846 idiomas)."
            ]
        ),
    ]

    for idx, (d_title, bg, bd, col, d_bullets) in enumerate(dims_detail):
        col_i = idx % 2
        row_i = idx // 2
        left = 0.55 + col_i * 6.2
        top = 1.42 + row_i * 1.84
        add_pastel_card(
            s11, left, top, 5.95, 1.72, bg, bd,
            title=d_title, bullets=d_bullets, title_color=col, font_size=8.9
        )

    # =========================================================================
    # SLIDE 12: PATRÓN ANTI-HUÉRFANOS KEY 0 Y AUDITORÍA DE CALIDAD
    # =========================================================================
    s12 = prs.slides.add_slide(blank_layout)
    add_header(
        s12, 12, "Integridad Referencial en el Modelo Estrella",
        "Patrón de Fila Cero (Key 0) y Garantía de Cero Huérfanos",
        "Cómo se preservan el 100% de los hechos históricos cuando un atributo dimensional es nulo en el origen",
        PASTEL_MINT, ACCENT_TEAL
    )

    add_pastel_card(
        s12, 0.55, 1.45, 5.6, 5.45, PASTEL_MINT, PASTEL_MINT_BD,
        header_badge="FUNDAMENTO ARQUITECTÓNICO DE RALPH KIMBALL",
        title="¿Por qué usar la Clave Subrogada 0?",
        bullets=[
            "• En bases relacionales OLTP, muchas grabaciones o lanzamientos carecen de idioma asignado, formato específico o fecha completa.",
            "• Si usáramos INNER JOIN sin fila por defecto, descartaríamos millones de pistas reales, alterando los totales históricos de producción.",
            "• Si dejáramos NULL en las claves foráneas de la tabla de hechos, violaríamos la integridad referencial y romperíamos los filtros en Power BI.",
            "• Solución implementada: cada script populate_dim_*.sql inserta explícitamente un registro con Surrogate Key = 0.",
            "• En populate_fact_tracks.sql se aplica COALESCE(dim_key, 0) en las 6 dimensiones conformadas.",
            "• Resultado certificado en meta.data_quality_log: 0 violaciones de integridad referencial en las 6 dimensiones."
        ],
        title_color=ACCENT_TEAL, font_size=10
    )

    key0_rows = [
        ["Dimensión Gold", "Clave PK = 0", "Etiqueta Descriptiva Asignada", "Validación en meta.data_quality_log"],
        ["gold.dim_fecha", "fecha_key = 0", "'Sin Fecha' / 'Sin Década' / 'Sin Siglo'", "INTEGRIDAD_FK_DIM_FECHA: 0 huérfanos"],
        ["gold.dim_artista", "artista_key = 0", "'Artista Desconocido' / 'Sin País Registrado'", "INTEGRIDAD_FK_DIM_ARTISTA: 0 huérfanos"],
        ["gold.dim_lanzamiento", "lanzamiento_key = 0", "'No Clasificado' / 'Estándar / Desconocido'", "INTEGRIDAD_FK_DIM_LANZAMIENTO: 0 huérfanos"],
        ["gold.dim_geografia", "geografia_key = 0", "'Sin Área Registrada' / 'Sin País Registrado'", "INTEGRIDAD_FK_DIM_GEOGRAFIA: 0 huérfanos"],
        ["gold.dim_formato", "formato_key = 0", "'Formato No Especificado' / 'Desconocido'", "INTEGRIDAD_FK_DIM_FORMATO: 0 huérfanos"],
        ["gold.dim_idioma", "idioma_key = 0", "'Idioma No Especificado' (codigo_iso = 'und')", "INTEGRIDAD_FK_DIM_IDIOMA: 0 huérfanos"],
    ]

    t_s12 = s12.shapes.add_table(len(key0_rows), 4, Inches(6.4), Inches(1.45), Inches(6.35), Inches(5.45))
    for r_i, row in enumerate(key0_rows):
        for c_i, val in enumerate(row):
            t_s12.table.cell(r_i, c_i).text = val
    style_table(t_s12.table, [1.5, 1.15, 1.95, 1.75], PASTEL_BLUE, CARD_WHITE, PASTEL_SLATE, font_size=9)

    # =========================================================================
    # SLIDE 13: FLUJO DEL PIPELINE ETL E2E
    # =========================================================================
    s13 = prs.slides.add_slide(blank_layout)
    add_header(
        s13, 13, "Ingeniería de Datos y Procesamiento Masivo",
        "Flujo E2E del Pipeline ETL (Extracción, Streaming y Agregación)",
        "Secuencia automatizada desde el archivo comprimido mbdump.tar.bz2 hasta la tabla de hechos y vistas materializadas",
        PASTEL_PEACH, ACCENT_AMBER
    )

    etl_steps = [
        (
            "ETAPA 1 · Inicialización DDL", "scripts/setup_database.py", PASTEL_BLUE, PASTEL_BLUE_BD, ACCENT_NAVY,
            [
                "• Conecta a PostgreSQL 16 (puerto 5435).",
                "• Ejecuta en orden los 6 archivos DDL:",
                "  1. 01_schema_meta.sql",
                "  2. 02_create_silver_tables.sql (11 tablas)",
                "  3. 03_dimensions_facts.sql (Estrella Español)",
                "  4. 04_indexes_partitions.sql (15 particiones)",
                "  5. 05/06: vistas mat. y distribución"
            ]
        ),
        (
            "ETAPA 2 · Ingesta Silver Masiva", "etl/silver/ingest_silver.py", PASTEL_MINT, PASTEL_MINT_BD, ACCENT_TEAL,
            [
                "• Verifica cada archivo en data/raw/mbdump/.",
                "• Si falta alguno, lo extrae bajo demanda desde mbdump.tar.bz2 usando tar.exe.",
                "• Ejecuta TRUNCATE RESTART IDENTITY y carga vía COPY FROM STDIN con utf-8-sig.",
                "• Audita lotes y velocidades en meta.etl_audit."
            ]
        ),
        (
            "ETAPA 3 · Streaming de Pistas", "etl/silver/ingest_tracks_sliced.py", PASTEL_PEACH, PASTEL_PEACH_BD, ACCENT_AMBER,
            [
                "• Procesa el archivo masivo track mediante la clase MaxLineReader (buffer circular de 128 KB).",
                "• Acota de forma determinista exactamente 15.000.000 de pistas reales hacia silver.track.",
                "• Mantiene el consumo de RAM de Python por debajo de 50 MB."
            ]
        ),
        (
            "ETAPA 4 · Agregación Gold & DQ", "etl/gold/run_gold_pipeline.py", PASTEL_LAVENDER, PASTEL_LAV_BD, ACCENT_PURPLE,
            [
                "• Puebla las 7 dimensiones (populate_dim_*.sql).",
                "• populate_fact_tracks.sql agrega por día 11 métricas aditivas; cada lanzamiento cuenta una sola vez.",
                "• Puebla el hecho de distribución, refresca las MVs y concilia contra Silver."
            ]
        ),
    ]

    for idx, (st_title, st_script, bg, bd, col, st_bullets) in enumerate(etl_steps):
        left = 0.55 + idx * 3.1
        add_pastel_card(
            s13, left, 1.45, 2.92, 5.45, bg, bd,
            header_badge=st_script, title=st_title, bullets=st_bullets, title_color=col, font_size=9.5
        )

    # =========================================================================
    # SLIDE 14: REGLAS EDA IMPLEMENTADAS (CATÁLOGO COMPLETO E01 A E10)
    # =========================================================================
    s14 = prs.slides.add_slide(blank_layout)
    add_header(
        s14, 14, "Saneamiento y Calidad de Datos",
        "Catálogo Completo de Reglas EDA Implementadas (E01 — E10)",
        "Transformaciones deterministas aplicadas entre Silver y Gold (documentadas en docs/reglas_eda.md)",
        PASTEL_ROSE, ACCENT_ROSE
    )

    eda_rows = [
        ["ID", "Regla de Calidad EDA", "Acción Técnica Implementada en SQL / Python", "Justificación Arquitectónica en el DWH"],
        ["E01", "Duraciones nulas o en cero", "GREATEST(COALESCE(NULLIF(t.length,0), NULLIF(rec.length,0), 0), 0).", "Rescata la duración del recording master y suma en pistas_completas_total."],
        ["E02", "Fechas históricas reales", "Prioridad: release_country → release_unknown_country → 0 (Sin Fecha). No se imputa con el año del artista.", "Garantiza que dim_fecha refleje el año/mes/día real de publicación (1900–2030)."],
        ["E03", "Resolución de artist_credit", "LEFT JOIN silver.artist_credit_name con filtro position = 0.", "Vincula el lanzamiento y la pista con el artist.id principal real."],
        ["E04", "Deduplicación de ISRC", "Subconsulta SELECT DISTINCT recording FROM silver.isrc.", "Evita multiplicar filas por múltiples códigos ISRC y suma en pistas_con_isrc_total."],
        ["E05", "Cero booleanos en Hechos", "Conversión de flags a SUM(CASE WHEN ... THEN 1 ELSE 0 END).", "Reemplaza booleanos por métricas enteras aditivas (pistas_largas_total, video)."],
        ["E06", "Cadenas > 1.000 caracteres", "Uso nativo de tipo TEXT con compresión TOAST en Silver y Gold.", "Evita errores de truncamiento en títulos de obras clásicas o experimentales."],
        ["E07", "Claves foráneas huérfanas", "Imputación al registro surrogate 0 mediante COALESCE(dim_key, 0).", "Garantiza Cero Huérfanos en las 6 dimensiones sin descartar hechos."],
        ["E08", "Saneamiento UTF-8 BOM", "Decodificación con encoding='utf-8-sig' y errors='replace'.", "Elimina caracteres Byte Order Mark (\\ufeff) en entornos Windows."],
        ["E09", "JOIN geográfico por ID", "Unión exacta por clave entera area_id hacia gold.dim_geografia.", "Elimina el Fan Trap causado por ciudades o regiones con nombres homónimos."],
        ["E10", "Auditoría automatizada DQ", "Ejecución de 10 reglas críticas al cierre de run_gold_pipeline.py.", "Persiste evidencia auditable de 0 violaciones en meta.data_quality_log."],
    ]

    t_s14 = s14.shapes.add_table(len(eda_rows), 4, Inches(0.55), Inches(1.42), Inches(12.2), Inches(5.52))
    for r_i, row in enumerate(eda_rows):
        for c_i, val in enumerate(row):
            t_s14.table.cell(r_i, c_i).text = val
    style_table(t_s14.table, [0.65, 2.35, 4.6, 4.6], PASTEL_ROSE, CARD_WHITE, PASTEL_SLATE, font_size=8.8)

    # =========================================================================
    # SLIDE 15: PARTICIONAMIENTO, VISTAS MATERIALIZADAS Y POWER BI (DAX)
    # =========================================================================
    s15 = prs.slides.add_slide(blank_layout)
    add_header(
        s15, 15, "Optimización Física y Explotación Analítica",
        "Particionamiento por Rango, Vistas Materializadas y Power BI",
        "Diseño de alto rendimiento en sql/gold/04_indexes_partitions.sql, 05_aggregations.sql y medidas DAX aditivas",
        PASTEL_LEMON, ACCENT_AMBER
    )

    add_pastel_card(
        s15, 0.55, 1.45, 3.9, 5.45, PASTEL_BLUE, PASTEL_BLUE_BD,
        header_badge="1 · PARTICIONAMIENTO DECLARATIVO",
        title="15 Particiones por fecha_key",
        bullets=[
            "• gold.fact_produccion_musical está particionada por RANGE (fecha_key):",
            "  - fact_produccion_unknown (0)",
            "  - fact_produccion_pre_1970 (1900–1969)",
            "  - Décadas: 1970s, 1980s, 1990s, 2000s, 2010s.",
            "  - Anuales: 2020, 2021, 2022, 2023, 2024, 2025.",
            "  - fact_produccion_2026_plus y default.",
            "• Partition Pruning: descarta más del 85% del I/O al filtrar por década o año."
        ],
        title_color=ACCENT_NAVY, font_size=9.5
    )

    add_pastel_card(
        s15, 4.7, 1.45, 3.9, 5.45, PASTEL_LAVENDER, PASTEL_LAV_BD,
        header_badge="2 · VISTAS MATERIALIZADAS EN ESPAÑOL",
        title="4 Agregaciones Pre-Calculadas",
        bullets=[
            "• gold.mv_tendencias_produccion_anual (RF01, RF05): evolución por anio, decada y siglo.",
            "• gold.mv_analitica_artistas (RF01, RF06, RF08): catálogo acumulado por artista, tipo y país.",
            "• gold.mv_evolucion_formatos (RF02, RF04): matriz temporal por formato y categoría.",
            "• gold.mv_distribucion_geografica (RF03, RF06): producción por país y tipo de área.",
            "• Cada vista posee índices únicos B-Tree."
        ],
        title_color=ACCENT_PURPLE, font_size=9.5
    )

    add_pastel_card(
        s15, 8.85, 1.45, 3.9, 5.45, PASTEL_PEACH, PASTEL_PEACH_BD,
        header_badge="3 · EXPLOTACIÓN EN POWER BI (DAX)",
        title="Medidas 100% Aditivas (SUM)",
        bullets=[
            "• Total Lanzamientos =",
            "  SUM(fact_produccion_musical[lanzamientos_total])",
            "• Total Pistas =",
            "  SUM(fact_produccion_musical[pistas_total])",
            "• Duración Promedio (Seg) =",
            "  DIVIDE(SUM([duracion_total_segundos]), SUM([pistas_completas_total]), 0)",
            "• Cobertura ISRC % =",
            "  DIVIDE(SUM([pistas_con_isrc_total]), [Total Pistas], 0)",
            "• Evidencia la transición Vinilo → CD → Digital (el digital supera al CD en 2012) y una duración que crece a largo plazo (r = 0,89) y se acorta desde 2013 (r = -0,57)."
        ],
        title_color=ACCENT_AMBER, font_size=9.2
    )

    # =========================================================================
    # SLIDE 16: CONCLUSIONES TÉCNICAS Y DE NEGOCIO
    # =========================================================================
    s16 = prs.slides.add_slide(blank_layout)
    add_header(
        s16, 16, "Síntesis Final y Cierre de Sustentación",
        "Conclusiones Técnicas, Arquitectónicas y de Negocio",
        "Logros consolidados tras el rediseño del Modelo en Estrella Puro en Español bajo los lineamientos de Ralph Kimball",
        PASTEL_MINT, ACCENT_TEAL
    )

    conclusions = [
        (
            "1 · Rigor en el Modelo en Estrella (Kimball)", PASTEL_LAVENDER, PASTEL_LAV_BD, ACCENT_PURPLE,
            [
                "• Se replanteó la tabla de hechos (gold.fact_produccion_musical) como un verdadero almacenamiento histórico diario.",
                "• Al eliminar todos los textos y booleanos de la tabla de hechos y dejar únicamente las 6 FKs conformadas más 11 métricas numéricas aditivas, todas las consultas analíticas operan mediante funciones SUM() puras.",
                "• El modelado de dim_lanzamiento por perfil conformado permitió consolidar múltiples lanzamientos diarios en lanzamientos_total."
            ]
        ),
        (
            "2 · Fidelidad Histórica con Datos 100% Reales", PASTEL_BLUE, PASTEL_BLUE_BD, ACCENT_NAVY,
            [
                "• La incorporación de silver.release_country, silver.release_unknown_country y silver.artist_credit_name desde el dump oficial mbdump.tar.bz2 (Schema Sequence 31) dotó al Data Warehouse de fechas de publicación y autorías 100% verídicas.",
                "• Se procesaron ~98,6 millones de registros en Silver y se alcanzaron 16 GB en disco, cumpliendo con creces los requisitos no funcionales de estrés."
            ]
        ),
        (
            "3 · Calidad de Datos y Cero Huérfanos", PASTEL_MINT, PASTEL_MINT_BD, ACCENT_TEAL,
            [
                "• La aplicación sistemática del catálogo de reglas EDA (E01 a E10), el cruce geográfico por clave entera (area_id) y el patrón de Fila Cero (Key 0) garantizaron 0 registros huérfanos y la erradicación de Fan Traps.",
                "• La auditoría automatizada en meta.etl_audit y meta.data_quality_log asegura trazabilidad. Una auditoría posterior detectó y corrigió conteos no aditivos, fechas imputadas con el año del artista y un mapeo de idiomas erróneo."
            ]
        ),
        (
            "4 · Valor Analítico para la Industria Musical", PASTEL_PEACH, PASTEL_PEACH_BD, ACCENT_AMBER,
            [
                "• La combinación de particionamiento declarativo por rango en fecha_key (15 particiones) y 4 vistas materializadas permite responder en milisegundos a los requerimientos RF01–RF08.",
                "• En Power BI (3 páginas, 26 medidas DAX) se evidencian la sustitución de formatos físicos por digitales (cruce en 2012), una duración que crece a largo plazo y se acorta levemente desde 2013, y las brechas regionales de formalización ISRC."
            ]
        ),
    ]

    for idx, (c_title, bg, bd, col, c_bullets) in enumerate(conclusions):
        col_i = idx % 2
        row_i = idx // 2
        left = 0.55 + col_i * 6.2
        top = 1.45 + row_i * 2.72
        add_pastel_card(
            s16, left, top, 5.95, 2.52, bg, bd,
            title=c_title, bullets=c_bullets, title_color=col, font_size=9.8
        )

    out_file = BASE_DIR / output_path
    prs.save(out_file)
    print(f"[OK] Presentacion PPTX en tonos pasteles generada exitosamente en: {out_file}")


if __name__ == "__main__":
    out_arg = sys.argv[1] if len(sys.argv) > 1 else "docs/DWMusicBrainz_Sustentacion.pptx"
    build_presentation(out_arg)

