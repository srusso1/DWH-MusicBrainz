"""
build_sustentacion_pdf.py
=========================
Script generador del Documento Oficial de Sustentación Técnica y Guía de Defensa
para el Data Warehouse Masivo de la Industria Musical (DWMusicBrainz).

Actualizado al 100% con:
- Arquitectura Medallón (10 tablas en Silver 3NF -> Modelo en Estrella Puro en Español en Gold).
- Tabla de hechos histórica diaria `gold.fact_produccion_musical` (exclusivamente FKs + 11 métricas numéricas aditivas, cero textos y cero booleanos).
- 6 Dimensiones conformadas en español (`dim_fecha`, `dim_artista`, `dim_lanzamiento`, `dim_geografia`, `dim_formato`, `dim_idioma`) con visualización exacta de todos sus atributos.
- Fechas históricas reales (`release_country` / `release_unknown_country`) y resolución exacta de créditos (`artist_credit_name`).
"""

import sys
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle


class NumberedCanvas(canvas.Canvas):
    """Canvas de dos pasadas para calcular dinámicamente el número total de páginas y encabezados."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        if self._pageNumber > 1:
            self.saveState()
            # Encabezado superior
            self.setFont("Helvetica-Bold", 7.5)
            self.setFillColor(colors.HexColor("#0B192C"))
            self.drawString(36, 812, "DWMusicBrainz")
            self.setFont("Helvetica", 7.5)
            self.setFillColor(colors.HexColor("#64748B"))
            self.drawString(110, 812, "|   Bases de Datos Avanzadas   |   Documento de Sustentación Técnica")
            self.drawRightString(559, 812, "Modelo en Estrella Puro en Español (Ralph Kimball)")
            
            self.setStrokeColor(colors.HexColor("#CBD5E1"))
            self.setLineWidth(0.6)
            self.line(36, 806, 559, 806)

            # Pie de página inferior
            self.line(36, 36, 559, 36)
            self.setFont("Helvetica", 7.5)
            self.setFillColor(colors.HexColor("#64748B"))
            self.drawString(36, 26, "Universidad Popular del Cesar  |  Ingeniería de Sistemas  |  5to Semestre")
            self.drawRightString(559, 26, f"Página {self._pageNumber} de {page_count}")
            self.restoreState()


def build_pdf(filename="docs/Documento_Sustentacion_DWH_MusicBrainz.pdf"):
    doc = SimpleDocTemplate(
        filename,
        pagesize=A4,
        leftMargin=36,
        rightMargin=36,
        topMargin=46,
        bottomMargin=46
    )

    styles = getSampleStyleSheet()
    
    c_primary = colors.HexColor("#0B192C")
    c_secondary = colors.HexColor("#6366F1")
    c_dark = colors.HexColor("#1E293B")
    c_muted = colors.HexColor("#64748B")
    c_bg_light = colors.HexColor("#F8FAFC")
    c_border = colors.HexColor("#E2E8F0")

    style_cover_super = ParagraphStyle('CoverSuper', fontName='Helvetica-Bold', fontSize=10, textColor=c_secondary, leading=14, spaceAfter=8)
    style_cover_title = ParagraphStyle('CoverTitle', fontName='Helvetica-Bold', fontSize=23, textColor=c_primary, leading=27, spaceAfter=10)
    style_cover_sub = ParagraphStyle('CoverSub', fontName='Helvetica', fontSize=10.5, textColor=c_muted, leading=15, spaceAfter=18)
    
    style_chap_num = ParagraphStyle('ChapNum', fontName='Helvetica-Bold', fontSize=9, textColor=c_secondary, leading=12, spaceAfter=2)
    style_chap_title = ParagraphStyle('ChapTitle', fontName='Helvetica-Bold', fontSize=14.5, textColor=c_primary, leading=18, spaceAfter=4, keepWithNext=True)
    style_chap_sub = ParagraphStyle('ChapSub', fontName='Helvetica-Oblique', fontSize=8.5, textColor=c_muted, leading=11, spaceAfter=10, keepWithNext=True)
    
    style_sec_title = ParagraphStyle('SecTitle', fontName='Helvetica-Bold', fontSize=10.5, textColor=c_primary, leading=14, spaceBefore=8, spaceAfter=4, keepWithNext=True)
    style_subsec_title = ParagraphStyle('SubSecTitle', fontName='Helvetica-Bold', fontSize=9, textColor=c_dark, leading=12, spaceBefore=6, spaceAfter=3, keepWithNext=True)
    
    style_body = ParagraphStyle('Body', fontName='Helvetica', fontSize=8, textColor=c_dark, leading=11, spaceAfter=5)
    style_bullet = ParagraphStyle('Bullet', fontName='Helvetica', fontSize=8, textColor=c_dark, leading=11, leftIndent=12, spaceAfter=3)
    
    style_callout = ParagraphStyle('Callout', fontName='Helvetica', fontSize=8, textColor=c_dark, leading=11)
    style_code = ParagraphStyle('Code', fontName='Courier', fontSize=6.6, textColor=colors.HexColor("#0F172A"), leading=8.3)
    
    style_th = ParagraphStyle('TH', fontName='Helvetica-Bold', fontSize=7.5, textColor=colors.white, leading=9.5, alignment=1)
    style_td = ParagraphStyle('TD', fontName='Helvetica', fontSize=7, textColor=c_dark, leading=8.8)
    style_td_bold = ParagraphStyle('TDBold', fontName='Helvetica-Bold', fontSize=7, textColor=c_dark, leading=8.8)
    style_td_center = ParagraphStyle('TDCenter', fontName='Helvetica', fontSize=7, textColor=c_dark, leading=8.8, alignment=1)

    story = []

    def callout_box(text, bg="#F1F5F9", border="#CBD5E1"):
        p = Paragraph(text, style_callout)
        t = Table([[p]], colWidths=[523.28])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor(bg)),
            ('BOX', (0,0), (-1,-1), 0.7, colors.HexColor(border)),
            ('LEFTPADDING', (0,0), (-1,-1), 10),
            ('RIGHTPADDING', (0,0), (-1,-1), 10),
            ('TOPPADDING', (0,0), (-1,-1), 6),
            ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ]))
        return t

    def code_box(code_text):
        p = Paragraph(code_text.replace('\n', '<br/>').replace(' ', '&nbsp;'), style_code)
        t = Table([[p]], colWidths=[523.28])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#F8FAFC")),
            ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor("#E2E8F0")),
            ('LEFTPADDING', (0,0), (-1,-1), 8),
            ('RIGHTPADDING', (0,0), (-1,-1), 8),
            ('TOPPADDING', (0,0), (-1,-1), 5),
            ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ]))
        return t

    # =========================================================================
    # PÁGINA 1: PORTADA INSTITUCIONAL
    # =========================================================================
    story.append(Spacer(1, 35))
    story.append(Paragraph("PROYECTO INTEGRADOR &nbsp;|&nbsp; BASES DE DATOS AVANZADAS", style_cover_super))
    story.append(Spacer(1, 8))
    story.append(Paragraph("Data Warehouse Masivo de la<br/>Industria Musical Global<br/>(DWMusicBrainz)", style_cover_title))
    story.append(Spacer(1, 4))
    story.append(Paragraph(
        "<b>PostgreSQL 16 en Docker</b> &nbsp;|&nbsp; <b>Arquitectura Medallón (Silver &rarr; Gold)</b><br/>"
        "<b>Modelo en Estrella Puro en Español (Ralph Kimball Star Schema)</b><br/>"
        "100% Datos Reales MusicBrainz (~89.3M Filas Silver, Hechos Históricos Diarios Aditivos) &nbsp;|&nbsp; Power BI",
        style_cover_sub
    ))
    
    story.append(HRFlowable(width="100%", thickness=2, color=c_primary, spaceBefore=8, spaceAfter=18))
    
    callout_portada = (
        "<b>DOCUMENTO OFICIAL DE SUSTENTACIÓN TÉCNICA Y GUÍA DE DEFENSA</b><br/><br/>"
        "Este documento técnico consolida la arquitectura analítica, el modelo dimensional en estrella puro en español, "
        "la estructura exacta de las 6 dimensiones conformadas y la tabla de hechos histórica diaria "
        "(<code>gold.fact_produccion_musical</code>) diseñada exclusivamente con claves foráneas y 11 métricas numéricas "
        "100% aditivas (cero textos y cero booleanos). Alimentado con el volcado oficial de la <b>MetaBrainz Foundation "
        "(Schema Sequence 31)</b>, incorpora las fechas reales de publicación (<code>release_country</code>) y créditos "
        "autorales (<code>artist_credit_name</code>), superando los <b>14.5 GB</b> en disco y garantizando <b>cero huérfanos</b>."
    )
    story.append(callout_box(callout_portada, bg="#EFF6FF", border="#93C5FD"))
    
    story.append(Spacer(1, 130))
    
    meta_box = [
        [Paragraph("<b>Programa:</b> Ingeniería de Sistemas", style_body), Paragraph("<b>Asignatura:</b> Bases de Datos Avanzadas", style_body)],
        [Paragraph("<b>Semestre:</b> 5to Semestre Académico", style_body), Paragraph("<b>Institución:</b> Universidad Popular del Cesar", style_body)],
        [Paragraph("<b>Integrantes:</b> Juan Sebastián Rincón Farelo y equipo", style_body), Paragraph("<b>Docente:</b> Docente Titular de la Cátedra", style_body)],
        [Paragraph("<b>Fecha:</b> Octubre de 2026", style_body), Paragraph("<b>Ubicación:</b> Valledupar, Cesar, Colombia", style_body)],
    ]
    t_meta = Table(meta_box, colWidths=[261.64, 261.64])
    t_meta.setStyle(TableStyle([
        ('LINEBELOW', (0,0), (-1,-1), 0.5, colors.HexColor("#E2E8F0")),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(t_meta)
    story.append(PageBreak())

    # =========================================================================
    # PÁGINA 2: TABLA DE CONTENIDO (ÍNDICE)
    # =========================================================================
    story.append(Paragraph("ÍNDICE GENERAL DE CONTENIDO", style_chap_title))
    story.append(Paragraph("Estructura capitular del documento de sustentación técnica", style_chap_sub))
    story.append(Spacer(1, 8))

    toc_data = [
        [Paragraph("<b>Capítulo</b>", style_th), Paragraph("<b>Título del Capítulo y Alcance Temático</b>", style_th), Paragraph("<b>Pág.</b>", style_th)],
        [Paragraph("1", style_td_center), Paragraph("<b>Resumen ejecutivo y contexto:</b> Problema OLTP, solución OLAP de grano histórico diario y arquitectura general.", style_td), Paragraph("3", style_td_center)],
        [Paragraph("2", style_td_center), Paragraph("<b>Objetivos y requerimientos:</b> Matriz de requerimientos funcionales RF01–RF08 y no funcionales RNF01–RNF09.", style_td), Paragraph("4", style_td_center)],
        [Paragraph("3", style_td_center), Paragraph("<b>Volumetría y dimensionamiento físico:</b> Las 10 tablas Silver (~89.3M filas) y el Modelo Estrella Gold en español.", style_td), Paragraph("6", style_td_center)],
        [Paragraph("4", style_td_center), Paragraph("<b>La base de datos de origen:</b> MusicBrainz Sequence 31, resolución de fechas reales y créditos de artistas.", style_td), Paragraph("7", style_td_center)],
        [Paragraph("5", style_td_center), Paragraph("<b>Diseño del Modelo en Estrella Puro en Español:</b> Grano histórico diario, atributos exactos de dimensiones y hechos.", style_td), Paragraph("8", style_td_center)],
        [Paragraph("6", style_td_center), Paragraph("<b>Arquitectura Medallón y Stack Tecnológico:</b> Capas Silver, Gold y Meta; justificación de herramientas elegidas.", style_td), Paragraph("11", style_td_center)],
        [Paragraph("7", style_td_center), Paragraph("<b>Reglas del proceso EDA:</b> Catálogo E01–E10, eliminación de booleanos en hechos y fechas reales.", style_td), Paragraph("13", style_td_center)],
        [Paragraph("8", style_td_center), Paragraph("<b>Proceso ETL de alto rendimiento:</b> Extracción bajo demanda, MaxLineReader y agregación histórica set-based.", style_td), Paragraph("14", style_td_center)],
        [Paragraph("9", style_td_center), Paragraph("<b>Capa Oro: agregaciones, índices y particiones:</b> 14 particiones por fecha_key, índices B-tree y 4 vistas materializadas.", style_td), Paragraph("16", style_td_center)],
        [Paragraph("10", style_td_center), Paragraph("<b>Dashboard Power BI y Storytelling:</b> Medidas DAX 100% aditivas (SUM) y hallazgos de negocio.", style_td), Paragraph("17", style_td_center)],
        [Paragraph("11", style_td_center), Paragraph("<b>Guía por diapositiva para la defensa oral:</b> Resumen técnico y discurso de defensa para 13 diapositivas.", style_td), Paragraph("19", style_td_center)],
        [Paragraph("12", style_td_center), Paragraph("<b>Banco de preguntas técnicas para la sustentación:</b> 15 preguntas de rigor con respuestas de Senior Architect.", style_td), Paragraph("22", style_td_center)],
        [Paragraph("13", style_td_center), Paragraph("<b>Puntos de atención y lista de verificación:</b> Checklist previo a la evaluación y certificación final.", style_td), Paragraph("24", style_td_center)],
    ]
    t_toc = Table(toc_data, colWidths=[35, 445, 43.28])
    t_toc.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), c_primary),
        ('ALIGN', (0,0), (-1,0), 'CENTER'),
        ('GRID', (0,0), (-1,-1), 0.5, c_border),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, c_bg_light]),
        ('TOPPADDING', (0,0), (-1,-1), 4.5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4.5),
    ]))
    story.append(t_toc)
    story.append(Spacer(1, 15))

    callout_toc = (
        "<b>Corrección Arquitectónica Clave Implementada:</b> La tabla de hechos central "
        "(<code>gold.fact_produccion_musical</code>) fue rediseñada como un verdadero <b>almacenamiento histórico diario</b> "
        "donde cada registro consolida la producción musical por día (<code>fecha_key</code>) y dimensiones conformadas, "
        "almacenando <b>únicamente claves foráneas y métricas numéricas 100% aditivas</b> (cero booleanos y cero textos)."
    )
    story.append(callout_box(callout_toc, bg="#FEF3C7", border="#F59E0B"))
    story.append(PageBreak())

    # =========================================================================
    # PÁGINA 3: CAPÍTULO 1 - RESUMEN EJECUTIVO Y CONTEXTO
    # =========================================================================
    story.append(Paragraph("CAPÍTULO 1", style_chap_num))
    story.append(Paragraph("Resumen ejecutivo y contexto", style_chap_title))
    story.append(Paragraph("Qué problema se resuelve, cómo se modela el almacenamiento histórico diario y arquitectura general", style_chap_sub))

    story.append(Paragraph("1.1. Contexto de Negocio: Del Catálogo Operacional al Almacenamiento Histórico", style_sec_title))
    story.append(Paragraph(
        "En la industria musical global, bases de datos transaccionales (OLTP) como MusicBrainz normalizan el catálogo "
        "en decenas de tablas en <b>Tercera Forma Normal (3NF)</b>: <code>track</code>, <code>recording</code>, "
        "<code>medium</code>, <code>release</code>, <code>release_country</code>, <code>artist_credit_name</code>, "
        "<code>artist</code>, <code>area</code> e <code>isrc</code>. Un error frecuente al construir un Data Warehouse es "
        "volcar las pistas individuales con sus nombres y booleanos a una tabla llamada 'fact', creando un catálogo "
        "desnormalizado en lugar de una verdadera tabla de hechos histórica.",
        style_body
    ))

    story.append(Paragraph("1.2. La Solución Arquitectónica: DWMusicBrainz (Estrella Pura en Español)", style_sec_title))
    story.append(Paragraph(
        "El proyecto <b>DWMusicBrainz</b> implementa en <b>PostgreSQL 16 (Docker, puerto 5435)</b> una "
        "<b>Arquitectura Medallón (Silver &rarr; Gold)</b> donde la capa Gold está modelada íntegramente en español "
        "bajo las reglas estrictas de <b>Ralph Kimball</b>:",
        style_body
    ))
    story.append(Paragraph("&bull; <b>Grano Histórico Diario + Dimensional:</b> Cada registro en <code>gold.fact_produccion_musical</code> consolida la actividad histórica de un día (<code>fecha_key</code>) cruzada con las 5 dimensiones de contexto (<code>artista_key</code>, <code>lanzamiento_key</code>, <code>geografia_key</code>, <code>formato_key</code>, <code>idioma_key</code>).", style_bullet))
    story.append(Paragraph("&bull; <b>Métricas 100% Aditivas (Cero Textos, Cero Booleanos):</b> La tabla de hechos contiene exclusivamente FKs enteras y 11 métricas cuantitativas aditivas: <code>lanzamientos_total</code>, <code>soportes_total</code>, <code>pistas_total</code>, <code>grabaciones_unicas_total</code>, duraciones acumuladas y conteos aditivos de ISRC, pistas largas, videos y pistas completas.", style_bullet))
    story.append(Paragraph("&bull; <b>Verdad Histórica desde el Dump Oficial:</b> Se extraen de <code>mbdump.tar.bz2</code> (7.1 GB, Sequence 31) las tablas <code>release_country</code> y <code>release_unknown_country</code> para obtener las fechas reales de lanzamiento (1900–2026) y <code>artist_credit_name</code> para resolver el artista principal exacto.", style_bullet))

    story.append(Spacer(1, 10))
    story.append(Paragraph("1.3. Matriz Resumen de Hitos y Entregables del Proyecto", style_sec_title))
    
    hitos_data = [
        [Paragraph("<b>Hito</b>", style_th), Paragraph("<b>Fase Arquitectónica</b>", style_th), Paragraph("<b>Alcance Técnico Verificado</b>", style_th), Paragraph("<b>Estado</b>", style_th)],
        [Paragraph("H0", style_td_center), Paragraph("Fase 0: Infraestructura", style_td), Paragraph("Docker Compose (PG16 en 5435), tuning 1GB buffers y shm_size=1gb, esquemas meta/silver/gold.", style_td), Paragraph("100% OK", style_td_center)],
        [Paragraph("H1", style_td_center), Paragraph("Fase 1: Ingesta Silver (10 Tablas)", style_td), Paragraph("Extracción quirúrgica y COPY de ~89.3M filas (incluyendo release_country y artist_credit_name).", style_td), Paragraph("100% OK", style_td_center)],
        [Paragraph("H2", style_td_center), Paragraph("Fase 2: Dimensiones Gold (Español)", style_td), Paragraph("Poblado de 6 dimensiones conformadas en español con Surrogate Keys y Patrón Fila Cero (Key 0).", style_td), Paragraph("100% OK", style_td_center)],
        [Paragraph("H3", style_td_center), Paragraph("Fase 3: Hechos Históricos y MVs", style_td), Paragraph("Consolidación diaria en fact_produccion_musical (11 métricas aditivas) y 4 vistas materializadas.", style_td), Paragraph("100% OK", style_td_center)],
        [Paragraph("H4", style_td_center), Paragraph("Fase 4: Auditoría y Power BI", style_td), Paragraph("Registro en meta.data_quality_log (0 huérfanos) y medidas DAX basadas 100% en SUM.", style_td), Paragraph("100% OK", style_td_center)],
    ]
    t_hitos = Table(hitos_data, colWidths=[30, 115, 315, 63.28])
    t_hitos.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), c_primary),
        ('GRID', (0,0), (-1,-1), 0.5, c_border),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, c_bg_light]),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(t_hitos)
    story.append(PageBreak())

    # =========================================================================
    # PÁGINAS 4-5: CAPÍTULO 2 - OBJETIVOS Y REQUERIMIENTOS (RF Y RNF)
    # =========================================================================
    story.append(Paragraph("CAPÍTULO 2", style_chap_num))
    story.append(Paragraph("Objetivos y matriz de requerimientos", style_chap_title))
    story.append(Paragraph("Objetivo general, objetivos específicos y catálogo formal RF01–RF08 y RNF01–RNF09", style_chap_sub))

    story.append(Paragraph("2.1. Objetivo General", style_sec_title))
    story.append(Paragraph(
        "Diseñar, implementar y desplegar un Data Warehouse analítico de alta volumetría empresarial utilizando "
        "datos 100% reales de MusicBrainz (MetaBrainz Foundation, Schema Sequence 31), estructurado bajo una "
        "Arquitectura Medallón (Silver &rarr; Gold) y un Modelo en Estrella Puro en español (Ralph Kimball) cuya tabla "
        "de hechos (<code>gold.fact_produccion_musical</code>) consolide el registro histórico diario mediante claves "
        "foráneas conformadas y métricas numéricas 100% aditivas.",
        style_body
    ))

    story.append(Paragraph("2.2. Objetivos Específicos", style_sec_title))
    story.append(Paragraph("&bull; <b>OE1:</b> Ingestar en la capa <code>silver</code> las 10 tablas relacionales clave de MusicBrainz (~89.3 millones de filas totales), incluyendo fechas históricas reales y créditos de artistas.", style_bullet))
    story.append(Paragraph("&bull; <b>OE2:</b> Modelar en la capa <code>gold</code> 6 dimensiones conformadas en español con claves subrogadas y el patrón de Fila Cero (Key 0) garantizando cero huérfanos.", style_bullet))
    story.append(Paragraph("&bull; <b>OE3:</b> Consolidar la tabla de hechos histórica <code>gold.fact_produccion_musical</code> por día y dimensiones, libre de atributos textuales y booleanos, con particionamiento físico por rangos en <code>fecha_key</code>.", style_bullet))
    story.append(Paragraph("&bull; <b>OE4:</b> Construir 4 vistas materializadas analíticas indexadas en español para responder consultas OLAP y tableros de Power BI en menos de 0.1 segundos.", style_bullet))

    story.append(Spacer(1, 6))
    story.append(Paragraph("2.3. Matriz de Requerimientos Funcionales (RF01 — RF08)", style_sec_title))

    rf_data = [
        [Paragraph("<b>Req.</b>", style_th), Paragraph("<b>Nombre y Descripción Funcional</b>", style_th), Paragraph("<b>Tablas Gold Involucradas</b>", style_th), Paragraph("<b>Métrica Aditiva / Operación</b>", style_th)],
        [Paragraph("RF01", style_td_center), Paragraph("<b>Ranking Top N de Artistas y Producción:</b> Volumen de lanzamientos, pistas, duración acumulada y cobertura ISRC por país y década.", style_td), Paragraph("fact_produccion_musical, dim_artista, dim_fecha", style_td), Paragraph("SUM(lanzamientos_total), SUM(pistas_total)", style_td)],
        [Paragraph("RF02", style_td_center), Paragraph("<b>Métricas por Formato e Idioma:</b> Duración promedio ponderada y volumen según formato (Vinilo, CD, Digital) e idioma.", style_td), Paragraph("fact_produccion_musical, dim_formato, dim_idioma", style_td), Paragraph("SUM(duracion_total_segundos) / SUM(pistas_completas_total)", style_td)],
        [Paragraph("RF03", style_td_center), Paragraph("<b>Drill-Down Geográfico y Temporal:</b> Navegación País &gt; Tipo de Área y Siglo &gt; Década &gt; Año &gt; Mes &gt; Día.", style_td), Paragraph("fact_produccion_musical, dim_geografia, dim_fecha", style_td), Paragraph("SUM(lanzamientos_total), SUM(duracion_total_minutos)", style_td)],
        [Paragraph("RF04", style_td_center), Paragraph("<b>Comparativa Físico vs Digital y Canciones Largas:</b> Volumen de pistas largas (&gt;300s) frente al total por categoría de soporte.", style_td), Paragraph("fact_produccion_musical, dim_formato", style_td), Paragraph("SUM(pistas_largas_total) / SUM(pistas_total)", style_td)],
        [Paragraph("RF05", style_td_center), Paragraph("<b>Correlación Estadística Streaming vs Vinilo:</b> Demostración matemática del acortamiento musical por año histórico.", style_td), Paragraph("fact_produccion_musical, dim_fecha", style_td), Paragraph("corr(anio, duracion_promedio_seg)", style_td)],
        [Paragraph("RF06", style_td_center), Paragraph("<b>Formalización Discográfica (ISRC):</b> Tasa de pistas con código internacional ISRC según país y tipo de artista.", style_td), Paragraph("fact_produccion_musical, dim_geografia, dim_artista", style_td), Paragraph("SUM(pistas_con_isrc_total) * 100.0 / SUM(pistas_total)", style_td)],
        [Paragraph("RF07", style_td_center), Paragraph("<b>Densidad de Pistas y Soportes por Lanzamiento:</b> Promedio de pistas por álbum y por soporte físico/digital.", style_td), Paragraph("fact_produccion_musical, dim_lanzamiento, dim_formato", style_td), Paragraph("SUM(pistas_total) / SUM(lanzamientos_total)", style_td)],
        [Paragraph("RF08", style_td_center), Paragraph("<b>Catálogo Emergente y Nuevos Talentos:</b> Artistas debutantes en la última década con mayor volumen y cobertura ISRC.", style_td), Paragraph("fact_produccion_musical, dim_artista, dim_fecha", style_td), Paragraph("anio_inicio &gt;= 2015, SUM(pistas_con_isrc_total)", style_td)],
    ]
    t_rf = Table(rf_data, colWidths=[28, 210, 140, 145.28])
    t_rf.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), c_primary),
        ('GRID', (0,0), (-1,-1), 0.5, c_border),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, c_bg_light]),
        ('TOPPADDING', (0,0), (-1,-1), 3.5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3.5),
    ]))
    story.append(t_rf)
    story.append(PageBreak())

    # CONTINUACIÓN CAPÍTULO 2: REQUERIMIENTOS NO FUNCIONALES (PÁGINA 5)
    story.append(Paragraph("2.4. Matriz de Requerimientos No Funcionales (RNF01 — RNF09)", style_sec_title))
    rnf_data = [
        [Paragraph("<b>RNF</b>", style_th), Paragraph("<b>Criterio / Dimensión</b>", style_th), Paragraph("<b>Meta Exigida</b>", style_th), Paragraph("<b>Implementación en DWMusicBrainz</b>", style_th), Paragraph("<b>Estado</b>", style_th)],
        [Paragraph("RNF01", style_td_center), Paragraph("Procesamiento por Chunks", style_td), Paragraph("Streaming sin saturar RAM", style_td), Paragraph("MaxLineReader con buffer de 128 KB en Python", style_td), Paragraph("100% OK", style_td_center)],
        [Paragraph("RNF02", style_td_center), Paragraph("Almacenamiento en Disco", style_td), Paragraph("&gt; 3.0 GB físico en PostgreSQL", style_td), Paragraph("<b>&gt; 14.5 GB reales</b> entre Silver (10 tablas) y Gold", style_td), Paragraph("SUPERADO", style_td_center)],
        [Paragraph("RNF03", style_td_center), Paragraph("Volumetría Real Procesada", style_td), Paragraph("&gt; 10.000.000 registros base", style_td), Paragraph("<b>~89.3M filas en Silver</b> y 15M pistas consolidadas en hechos", style_td), Paragraph("SUPERADO", style_td_center)],
        [Paragraph("RNF04", style_td_center), Paragraph("Garantía Cero Sintéticos", style_td), Paragraph("100% datos reales auditables", style_td), Paragraph("Volcado oficial MusicBrainz Sequence 31 (mbdump.tar.bz2)", style_td), Paragraph("100% OK", style_td_center)],
        [Paragraph("RNF05", style_td_center), Paragraph("Idempotencia del Pipeline", style_td), Paragraph("Re-ejecuciones sin duplicados", style_td), Paragraph("TRUNCATE RESTART IDENTITY y ON CONFLICT DO UPDATE", style_td), Paragraph("100% OK", style_td_center)],
        [Paragraph("RNF06", style_td_center), Paragraph("Auditoría y Calidad", style_td), Paragraph("Trazabilidad E2E y reglas DQ", style_td), Paragraph("meta.etl_audit + meta.data_quality_log automatizados", style_td), Paragraph("100% OK", style_td_center)],
        [Paragraph("RNF07", style_td_center), Paragraph("SLA de Consulta Analítica", style_td), Paragraph("&lt; 3.00 s en consultas OLAP", style_td), Paragraph("&lt; 0.10 s gracias a métricas pre-sumadas y MVs", style_td), Paragraph("ÓPTIMO", style_td_center)],
        [Paragraph("RNF08", style_td_center), Paragraph("Integridad Referencial", style_td), Paragraph("0 registros huérfanos", style_td), Paragraph("Patrón Key 0 en las 6 dimensiones en español", style_td), Paragraph("100% OK", style_td_center)],
        [Paragraph("RNF09", style_td_center), Paragraph("Despliegue Reproducible", style_td), Paragraph("Contenerización total", style_td), Paragraph("Docker Compose con postgres:16 y shm_size 1GB", style_td), Paragraph("100% OK", style_td_center)],
    ]
    t_rnf = Table(rnf_data, colWidths=[35, 110, 110, 215, 53.28])
    t_rnf.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), c_primary),
        ('GRID', (0,0), (-1,-1), 0.5, c_border),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, c_bg_light]),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(t_rnf)
    story.append(PageBreak())

    # =========================================================================
    # PÁGINA 6: CAPÍTULO 3 - VOLUMETRÍA Y DIMENSIONAMIENTO FÍSICO
    # =========================================================================
    story.append(Paragraph("CAPÍTULO 3", style_chap_num))
    story.append(Paragraph("Volumetría y dimensionamiento físico", style_chap_title))
    story.append(Paragraph("Las 10 tablas de la capa Silver y el Modelo en Estrella Puro de la capa Gold", style_chap_sub))

    story.append(Paragraph("3.1. Consolidado de Tablas por Capa (Silver 3NF y Gold Estrella)", style_sec_title))
    vol_data = [
        [Paragraph("<b>Esquema</b>", style_th), Paragraph("<b>Tabla / Objeto</b>", style_th), Paragraph("<b>Filas Reales / Est.</b>", style_th), Paragraph("<b>Grano y Rol en el Data Warehouse</b>", style_th), Paragraph("<b>Disco Est.</b>", style_th)],
        [Paragraph("silver", style_td_center), Paragraph("recording", style_td_bold), Paragraph("40.532.448", style_td_center), Paragraph("Grabación maestra de estudio (duración master y flag video)", style_td), Paragraph("4.998 MB", style_td_center)],
        [Paragraph("silver", style_td_center), Paragraph("track", style_td_bold), Paragraph("15.000.000", style_td_center), Paragraph("Pista musical en un soporte (base atómica de conteo)", style_td), Paragraph("1.967 MB", style_td_center)],
        [Paragraph("silver", style_td_center), Paragraph("isrc", style_td_bold), Paragraph("6.478.709", style_td_center), Paragraph("Códigos internacionales ISRC por grabación", style_td), Paragraph("795 MB", style_td_center)],
        [Paragraph("silver", style_td_center), Paragraph("medium", style_td_bold), Paragraph("6.411.799", style_td_center), Paragraph("Soporte físico o digital que compone un lanzamiento", style_td), Paragraph("986 MB", style_td_center)],
        [Paragraph("silver", style_td_center), Paragraph("artist_credit_name", style_td_bold), Paragraph("~6.210.000", style_td_center), Paragraph("Vínculo exacto entre artist_credit y artist.id (position=0)", style_td), Paragraph("420 MB", style_td_center)],
        [Paragraph("silver", style_td_center), Paragraph("release", style_td_bold), Paragraph("5.844.569", style_td_center), Paragraph("Lanzamiento discográfico (estado, empaque, idioma, calidad)", style_td), Paragraph("1.108 MB", style_td_center)],
        [Paragraph("silver", style_td_center), Paragraph("release_country", style_td_bold), Paragraph("~5.480.000", style_td_center), Paragraph("Fecha histórica real (año/mes/día) y país de lanzamiento", style_td), Paragraph("385 MB", style_td_center)],
        [Paragraph("silver", style_td_center), Paragraph("artist", style_td_bold), Paragraph("3.010.451", style_td_center), Paragraph("Catálogo de músicos solistas, grupos, coros y orquestas", style_td), Paragraph("498 MB", style_td_center)],
        [Paragraph("silver", style_td_center), Paragraph("release_unknown_country", style_td_bold), Paragraph("~215.000", style_td_center), Paragraph("Fecha histórica real de publicación sin país asignado", style_td), Paragraph("18 MB", style_td_center)],
        [Paragraph("silver", style_td_center), Paragraph("area", style_td_bold), Paragraph("120.107", style_td_center), Paragraph("Países, regiones, subdivisiones y ciudades", style_td), Paragraph("14 MB", style_td_center)],
        [Paragraph("gold", style_td_center), Paragraph("fact_produccion_musical", style_td_bold), Paragraph("~4.5M – 5.8M", style_td_center), Paragraph("Hecho histórico diario (consolida las 15M de pistas en SUMs)", style_td), Paragraph("~2.450 MB", style_td_center)],
        [Paragraph("gold", style_td_center), Paragraph("dim_artista", style_td_bold), Paragraph("3.010.452", style_td_center), Paragraph("Dimensión conformada de artistas con área y país", style_td), Paragraph("758 MB", style_td_center)],
        [Paragraph("gold", style_td_center), Paragraph("dim_geografia", style_td_bold), Paragraph("120.108", style_td_center), Paragraph("Dimensión conformada geográfica (país y tipo de área)", style_td), Paragraph("15 MB", style_td_center)],
        [Paragraph("gold", style_td_center), Paragraph("dim_fecha", style_td_bold), Paragraph("47.848", style_td_center), Paragraph("Calendario diario continuo (1900 a 2030) + Clave 0", style_td), Paragraph("4 MB", style_td_center)],
        [Paragraph("gold", style_td_center), Paragraph("dim_idioma / formato / lanz.", style_td_bold), Paragraph("~620", style_td_center), Paragraph("Dimensiones conformadas de idioma (354), perfil lanz. (~150) y formato (114)", style_td), Paragraph("&lt; 3 MB", style_td_center)],
    ]
    t_vol = Table(vol_data, colWidths=[38, 115, 72, 238, 60.28])
    t_vol.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), c_primary),
        ('GRID', (0,0), (-1,-1), 0.5, c_border),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, c_bg_light]),
        ('TOPPADDING', (0,0), (-1,-1), 3.2),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3.2),
    ]))
    story.append(t_vol)
    story.append(PageBreak())

    # =========================================================================
    # PÁGINA 7: CAPÍTULO 4 - LA BASE DE DATOS DE ORIGEN Y RESOLUCIÓN HISTÓRICA
    # =========================================================================
    story.append(Paragraph("CAPÍTULO 4", style_chap_num))
    story.append(Paragraph("La base de datos de origen: MusicBrainz Sequence 31", style_chap_title))
    story.append(Paragraph("Extracción quirúrgica desde mbdump.tar.bz2, fechas reales y resolución de créditos", style_chap_sub))

    story.append(Paragraph("4.1. Por qué incluimos release_country, release_unknown_country y artist_credit_name", style_sec_title))
    story.append(Paragraph(
        "Al analizar el esquema relacional nativo de MusicBrainz (Schema Sequence 31), detectamos dos particularidades "
        "críticas que todo arquitecto de datos debe resolver al construir el Data Warehouse:",
        style_body
    ))
    story.append(Paragraph(
        "<b>1. La fecha real de lanzamiento NO vive en la tabla release:</b> En <code>silver.release</code> solo existe "
        "la columna <code>last_updated</code> (cuándo un editor modificó la fila). Las fechas históricas reales de publicación "
        "(año, mes y día en que salió el disco a la venta, junto con el país del evento) residen en <code>release_country</code> "
        "(275 MB) y <code>release_unknown_country</code> (8.4 MB). Al incorporarlas en Silver, nuestra dimensión "
        "<code>gold.dim_fecha</code> refleja la historia real de la música desde 1900 hasta 2026.",
        style_bullet
    ))
    story.append(Paragraph(
        "<b>2. El campo artist_credit NO es artist.id:</b> En MusicBrainz, tanto <code>release</code> como <code>track</code> "
        "apuntan a un identificador de crédito artístico (<code>artist_credit</code>) que puede agrupar colaboraciones. "
        "La tabla puente <code>silver.artist_credit_name</code> (232 MB) permite resolver con exactitud el artista principal "
        "(<code>position = 0</code>) hacia <code>silver.artist.id</code>.",
        style_bullet
    ))

    story.append(Spacer(1, 8))
    story.append(Paragraph("4.2. Contraste Crítico: Tabla de Catálogo Desnormalizada vs Tabla de Hechos de Kimball", style_sec_title))
    comp_oltp_data = [
        [Paragraph("<b>Aspecto de Diseño</b>", style_th), Paragraph("<b>Planteamiento Erróneo (Catálogo Desnormalizado)</b>", style_th), Paragraph("<b>Diseño Correcto Implementado (Hechos de Kimball)</b>", style_th)],
        [Paragraph("Grano de la Tabla", style_td_bold), Paragraph("1 fila por canción individual con su título de texto y UUID.", style_td), Paragraph("1 registro histórico por Día (fecha_key) y combinación de las 5 dimensiones.", style_td)],
        [Paragraph("Columnas en la Tabla de Hechos", style_td_bold), Paragraph("Mezcla FKs con strings (track_name, isrc_code) y booleanos (has_isrc, is_video).", style_td), Paragraph("<b>Exclusivamente Claves Foráneas (FKs) y 11 Métricas Numéricas Aditivas.</b>", style_td)],
        [Paragraph("Comportamiento de lanzamientos_total", style_td_bold), Paragraph("Si dim_release tiene 5.8M de álbumes individuales, cada fila vale siempre 1.", style_td), Paragraph("Con dim_lanzamiento por perfil conformado, lanzamientos_total suma los álbumes reales del día.", style_td)],
        [Paragraph("Operación Analítica en Power BI", style_td_bold), Paragraph("Obliga a hacer COUNTROWS filtrando booleanos en 19M de filas.", style_td), Paragraph("Todas las métricas se calculan con <b>SUM() directo</b> a velocidad de memoria.", style_td)],
    ]
    t_oltp = Table(comp_oltp_data, colWidths=[95, 210, 218.28])
    t_oltp.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), c_primary),
        ('GRID', (0,0), (-1,-1), 0.5, c_border),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, c_bg_light]),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(t_oltp)
    story.append(PageBreak())

    # =========================================================================
    # PÁGINAS 8-10: CAPÍTULO 5 - DISEÑO DEL MODELO EN ESTRELLA PURO EN ESPAÑOL
    # =========================================================================
    story.append(Paragraph("CAPÍTULO 5", style_chap_num))
    story.append(Paragraph("Diseño del modelo en estrella puro en español (Ralph Kimball)", style_chap_title))
    story.append(Paragraph("Declaración de grano histórico diario, atributos exactos de cada tabla y DDLs de producción", style_chap_sub))

    story.append(Paragraph("5.1. Declaración Oficial del Grano Histórico Diario", style_sec_title))
    grano_box = (
        "<b>DECLARACIÓN OFICIAL DEL GRANO (KIMBALL GRAIN STATEMENT):</b><br/>"
        "<i>'Un registro individual en la tabla de hechos central (<code>gold.fact_produccion_musical</code>) representa "
        "el resumen histórico diario (<code>fecha_key</code>) de la producción musical consolidada por artista "
        "(<code>artista_key</code>), perfil de lanzamiento (<code>lanzamiento_key</code>), ubicación geográfica "
        "(<code>geografia_key</code>), formato de soporte (<code>formato_key</code>) e idioma (<code>idioma_key</code>), "
        "conteniendo exclusivamente claves foráneas conformadas y métricas numéricas 100% aditivas.'</i>"
    )
    story.append(callout_box(grano_box, bg="#EFF6FF", border="#93C5FD"))
    story.append(Spacer(1, 6))

    story.append(Paragraph("5.2. Visualización Exacta de Atributos del Modelo en Estrella (Capa Gold)", style_sec_title))
    story.append(Paragraph(
        "A continuación se detallan exactamente todas las tablas y columnas que conforman el esquema <code>gold</code> "
        "en PostgreSQL 16 (<code>sql/gold/03_dimensions_facts.sql</code>):",
        style_body
    ))

    dict_data = [
        [Paragraph("<b>Tabla en Esquema Gold</b>", style_th), Paragraph("<b>Clave Primaria (PK)</b>", style_th), Paragraph("<b>Listado Exacto de Columnas / Atributos</b>", style_th), Paragraph("<b>Rol y Naturaleza</b>", style_th)],
        [Paragraph("gold.fact_produccion_musical", style_td_bold), Paragraph("PK Compuesta:<br/>(hecho_key, fecha_key)", style_td_center), Paragraph("<b>FKs:</b> fecha_key, artista_key, lanzamiento_key, geografia_key, formato_key, idioma_key.<br/><b>Métricas Aditivas (11):</b> lanzamientos_total, soportes_total, pistas_total, grabaciones_unicas_total, duracion_total_ms, duracion_total_segundos, duracion_total_minutos, pistas_con_isrc_total, pistas_largas_total, pistas_video_total, pistas_completas_total.", style_td), Paragraph("Tabla de Hechos Histórica Diaria Particionada. Cero textos, cero booleanos.", style_td)],
        [Paragraph("gold.dim_fecha", style_td_bold), Paragraph("fecha_key<br/>(INTEGER YYYYMMDD)", style_td_center), Paragraph("fecha_key, fecha_completa, anio, trimestre, nombre_trimestre, mes, nombre_mes, nombre_mes_corto, dia, dia_semana, nombre_dia, es_fin_de_semana, decada, siglo.", style_td), Paragraph("Dimensión Calendario (1900–2030, 47.848 filas + Key 0).", style_td)],
        [Paragraph("gold.dim_artista", style_td_bold), Paragraph("artista_key<br/>(SERIAL)", style_td_center), Paragraph("artista_key, artista_id (UK), artista_gid, nombre_artista, nombre_orden, tipo_artista, genero, area_id, nombre_area, nombre_pais, anio_inicio, anio_fin, finalizado, creado_en.", style_td), Paragraph("Dimensión Artistas (3.010.452 filas + Key 0).", style_td)],
        [Paragraph("gold.dim_lanzamiento", style_td_bold), Paragraph("lanzamiento_key<br/>(SERIAL)", style_td_center), Paragraph("lanzamiento_key, estado_id, empaque_id, calidad_id, estado_lanzamiento, tipo_empaque, calidad_datos, creado_en.", style_td), Paragraph("Dimensión Perfil de Lanzamiento (~150 combinaciones + Key 0).", style_td)],
        [Paragraph("gold.dim_geografia", style_td_bold), Paragraph("geografia_key<br/>(SERIAL)", style_td_center), Paragraph("geografia_key, area_id (UK), area_gid, nombre_area, tipo_area, nombre_pais, creado_en.", style_td), Paragraph("Dimensión Geográfica (120.108 áreas + Key 0).", style_td)],
        [Paragraph("gold.dim_formato", style_td_bold), Paragraph("formato_key<br/>(SERIAL)", style_td_center), Paragraph("formato_key, formato_id (UK), nombre_formato, categoria_formato.", style_td), Paragraph("Dimensión Formatos Físicos/Digitales (114 filas + Key 0).", style_td)],
        [Paragraph("gold.dim_idioma", style_td_bold), Paragraph("idioma_key<br/>(SERIAL)", style_td_center), Paragraph("idioma_key, idioma_id (UK), nombre_idioma, codigo_iso.", style_td), Paragraph("Dimensión Idiomas ISO 639-3 (354 filas + Key 0).", style_td)],
    ]
    t_dict = Table(dict_data, colWidths=[95, 72, 240, 116.28])
    t_dict.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), c_primary),
        ('GRID', (0,0), (-1,-1), 0.5, c_border),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, c_bg_light]),
        ('TOPPADDING', (0,0), (-1,-1), 3.5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3.5),
    ]))
    story.append(t_dict)
    story.append(PageBreak())

    # CONTINUACIÓN CAPÍTULO 5: DDL EXACTO DE LA TABLA DE HECHOS Y PARTICIONES
    story.append(Paragraph("5.3. DDL Oficial de Producción: gold.fact_produccion_musical", style_sec_title))
    ddl_fact_code = (
        "CREATE TABLE IF NOT EXISTS gold.fact_produccion_musical (\n"
        "    hecho_key                   BIGSERIAL,\n"
        "    -- 1. Claves Foráneas Conformadas (Grano Histórico Diario + Dimensional)\n"
        "    fecha_key                   INTEGER NOT NULL, -- FK -> gold.dim_fecha\n"
        "    artista_key                 INTEGER NOT NULL, -- FK -> gold.dim_artista\n"
        "    lanzamiento_key             INTEGER NOT NULL, -- FK -> gold.dim_lanzamiento\n"
        "    geografia_key               INTEGER NOT NULL, -- FK -> gold.dim_geografia\n"
        "    formato_key                 INTEGER NOT NULL, -- FK -> gold.dim_formato\n"
        "    idioma_key                  INTEGER NOT NULL, -- FK -> gold.dim_idioma\n"
        "    -- 2. Métricas Numéricas 100% Aditivas (Cero textos, cero booleanos)\n"
        "    lanzamientos_total          INTEGER NOT NULL DEFAULT 0,\n"
        "    soportes_total              INTEGER NOT NULL DEFAULT 0,\n"
        "    pistas_total                INTEGER NOT NULL DEFAULT 0,\n"
        "    grabaciones_unicas_total    INTEGER NOT NULL DEFAULT 0,\n"
        "    duracion_total_ms           BIGINT  NOT NULL DEFAULT 0,\n"
        "    duracion_total_segundos     NUMERIC(14, 2) NOT NULL DEFAULT 0.00,\n"
        "    duracion_total_minutos      NUMERIC(14, 2) NOT NULL DEFAULT 0.00,\n"
        "    pistas_con_isrc_total       INTEGER NOT NULL DEFAULT 0,\n"
        "    pistas_largas_total         INTEGER NOT NULL DEFAULT 0,\n"
        "    pistas_video_total          INTEGER NOT NULL DEFAULT 0,\n"
        "    pistas_completas_total      INTEGER NOT NULL DEFAULT 0,\n"
        "    PRIMARY KEY (hecho_key, fecha_key)\n"
        ") PARTITION BY RANGE (fecha_key);"
    )
    story.append(code_box(ddl_fact_code))
    story.append(Spacer(1, 8))

    story.append(Paragraph("5.4. DDL Oficial: Particionamiento Físico por Rango en fecha_key", style_sec_title))
    ddl_part_code = (
        "CREATE TABLE IF NOT EXISTS gold.fact_produccion_unknown   PARTITION OF gold.fact_produccion_musical FOR VALUES FROM (0) TO (19000101);\n"
        "CREATE TABLE IF NOT EXISTS gold.fact_produccion_pre_1970  PARTITION OF gold.fact_produccion_musical FOR VALUES FROM (19000101) TO (19700101);\n"
        "CREATE TABLE IF NOT EXISTS gold.fact_produccion_1970s     PARTITION OF gold.fact_produccion_musical FOR VALUES FROM (19700101) TO (19800101);\n"
        "CREATE TABLE IF NOT EXISTS gold.fact_produccion_1980s     PARTITION OF gold.fact_produccion_musical FOR VALUES FROM (19800101) TO (19900101);\n"
        "CREATE TABLE IF NOT EXISTS gold.fact_produccion_1990s     PARTITION OF gold.fact_produccion_musical FOR VALUES FROM (19900101) TO (20000101);\n"
        "CREATE TABLE IF NOT EXISTS gold.fact_produccion_2000s     PARTITION OF gold.fact_produccion_musical FOR VALUES FROM (20000101) TO (20100101);\n"
        "CREATE TABLE IF NOT EXISTS gold.fact_produccion_2010s     PARTITION OF gold.fact_produccion_musical FOR VALUES FROM (20100101) TO (20200101);\n"
        "CREATE TABLE IF NOT EXISTS gold.fact_produccion_2020      PARTITION OF gold.fact_produccion_musical FOR VALUES FROM (20200101) TO (20210101);\n"
        "CREATE TABLE IF NOT EXISTS gold.fact_produccion_2021      PARTITION OF gold.fact_produccion_musical FOR VALUES FROM (20210101) TO (20220101);\n"
        "CREATE TABLE IF NOT EXISTS gold.fact_produccion_2022      PARTITION OF gold.fact_produccion_musical FOR VALUES FROM (20220101) TO (20230101);\n"
        "CREATE TABLE IF NOT EXISTS gold.fact_produccion_2023      PARTITION OF gold.fact_produccion_musical FOR VALUES FROM (20230101) TO (20240101);\n"
        "CREATE TABLE IF NOT EXISTS gold.fact_produccion_2024      PARTITION OF gold.fact_produccion_musical FOR VALUES FROM (20240101) TO (20250101);\n"
        "CREATE TABLE IF NOT EXISTS gold.fact_produccion_2025      PARTITION OF gold.fact_produccion_musical FOR VALUES FROM (20250101) TO (20260101);\n"
        "CREATE TABLE IF NOT EXISTS gold.fact_produccion_2026_plus PARTITION OF gold.fact_produccion_musical FOR VALUES FROM (20260101) TO (20310101);\n"
        "CREATE TABLE IF NOT EXISTS gold.fact_produccion_default   PARTITION OF gold.fact_produccion_musical DEFAULT;"
    )
    story.append(code_box(ddl_part_code))
    story.append(PageBreak())

    # =========================================================================
    # PÁGINA 11: CAPÍTULO 6 - ARQUITECTURA MEDALLÓN Y STACK TECNOLÓGICO
    # =========================================================================
    story.append(Paragraph("CAPÍTULO 6", style_chap_num))
    story.append(Paragraph("Arquitectura Medallón y justificación tecnológica", style_chap_title))
    story.append(Paragraph("Roles por capa (Silver, Gold, Meta), herramientas utilizadas y decisiones de diseño", style_chap_sub))

    story.append(Paragraph("6.1. Definición de Capas en la Arquitectura Medallón", style_sec_title))
    story.append(Paragraph("&bull; <b>Capa Plata (Silver - 10 Tablas 3NF):</b> Conserva los nombres técnicos de MusicBrainz, aplica tipos fuertes y <code>TEXT</code> TOAST, e incorpora los eventos históricos de publicación (<code>release_country</code>, <code>release_unknown_country</code>) y créditos (<code>artist_credit_name</code>).", style_bullet))
    story.append(Paragraph("&bull; <b>Capa Oro (Gold - Modelo Estrella en Español):</b> Traduce toda la capa de negocio al español (<code>dim_fecha</code>, <code>dim_artista</code>, <code>dim_lanzamiento</code>, <code>dim_geografia</code>, <code>dim_formato</code>, <code>dim_idioma</code> y <code>fact_produccion_musical</code>) con métricas pre-agregadas aditivas.", style_bullet))
    story.append(Paragraph("&bull; <b>Capa Meta (Gobernanza):</b> Registra la auditoría de lotes en <code>meta.etl_audit</code> y los controles de calidad referencial en <code>meta.data_quality_log</code>.", style_bullet))

    story.append(Spacer(1, 8))
    story.append(Paragraph("6.2. Justificación Técnica del Stack de Herramientas Elegido", style_sec_title))
    stack_data = [
        [Paragraph("<b>Herramienta</b>", style_th), Paragraph("<b>Versión / Rol</b>", style_th), Paragraph("<b>Justificación Arquitectónica</b>", style_th)],
        [Paragraph("PostgreSQL", style_td_bold), Paragraph("v16 (Docker)<br/>Motor DWH", style_td), Paragraph("Soporte nativo de Range Partitioning en fecha_key, COPY streaming de alta velocidad, Vistas Materializadas indexadas y paralelismo con shared_buffers=1GB.", style_td)],
        [Paragraph("Docker Compose", style_td_bold), Paragraph("v2 / Puerto 5435<br/>Infraestructura", style_td), Paragraph("Aislamiento total con shm_size=1gb para evitar fallos de Dynamic Shared Memory en agrupaciones masivas.", style_td)],
        [Paragraph("Python + psycopg2", style_td_bold), Paragraph("v3.12+<br/>Orquestador ETL", style_td), Paragraph("Extracción quirúrgica bajo demanda desde mbdump.tar.bz2 y streaming con MaxLineReader (buffer 128 KB) directo a libpq COPY.", style_td)],
        [Paragraph("Power BI Desktop", style_td_bold), Paragraph("Consumo BI<br/>Motor VertiPaq", style_td), Paragraph("Aprovecha las relaciones 1:* del modelo en estrella en español y evalúa todas las medidas con SUM() sobre métricas aditivas.", style_td)],
    ]
    t_stack = Table(stack_data, colWidths=[95, 110, 318.28])
    t_stack.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), c_primary),
        ('GRID', (0,0), (-1,-1), 0.5, c_border),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, c_bg_light]),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(t_stack)
    story.append(PageBreak())

    # =========================================================================
    # PÁGINA 12: CAPÍTULO 7 - REGLAS DEL PROCESO EDA
    # =========================================================================
    story.append(Paragraph("CAPÍTULO 7", style_chap_num))
    story.append(Paragraph("Reglas del proceso EDA y calidad de datos", style_chap_title))
    story.append(Paragraph("Catálogo oficial E01 a E10 aplicado en la transformación Silver -> Gold", style_chap_sub))

    eda_data = [
        [Paragraph("<b>ID</b>", style_th), Paragraph("<b>Regla de Calidad</b>", style_th), Paragraph("<b>Acción Técnica Implementada</b>", style_th), Paragraph("<b>Impacto en el Modelo Estrella</b>", style_th)],
        [Paragraph("E01", style_td_center), Paragraph("Duraciones nulas o en 0", style_td), Paragraph("GREATEST(COALESCE(NULLIF(t.length,0), NULLIF(rec.length,0), 0), 0).", style_td), Paragraph("Rescata la duración del recording master y suma en pistas_completas_total.", style_td)],
        [Paragraph("E02", style_td_center), Paragraph("Fechas reales de publicación", style_td), Paragraph("Prioridad: release_country -> release_unknown_country -> artist.begin_date_year -> 0.", style_td), Paragraph("Asigna la fecha histórica real (YYYYMMDD) en dim_fecha.", style_td)],
        [Paragraph("E03", style_td_center), Paragraph("Resolución de artist_credit", style_td), Paragraph("JOIN con silver.artist_credit_name (position = 0).", style_td), Paragraph("Vincula el lanzamiento y la pista con el artist_id principal real.", style_td)],
        [Paragraph("E04", style_td_center), Paragraph("Deduplicación de ISRC", style_td), Paragraph("Subconsulta SELECT DISTINCT recording FROM silver.isrc.", style_td), Paragraph("Evita duplicar filas por múltiples ISRCs y suma en pistas_con_isrc_total.", style_td)],
        [Paragraph("E05", style_td_center), Paragraph("Cero booleanos en Hechos", style_td), Paragraph("Conversión de flags a SUM(CASE WHEN ... THEN 1 ELSE 0 END).", style_td), Paragraph("Genera métricas enteras 100% aditivas (pistas_largas_total, pistas_video_total).", style_td)],
        [Paragraph("E06", style_td_center), Paragraph("Cadenas > 1.000 caracteres", style_td), Paragraph("Uso de tipo TEXT nativo con compresión TOAST en Silver y Gold.", style_td), Paragraph("Cero abortos por truncamiento en títulos extensos.", style_td)],
        [Paragraph("E07", style_td_center), Paragraph("Patrón Fila Cero (Key 0)", style_td), Paragraph("COALESCE(dim_key, 0) en las 6 claves foráneas del hecho.", style_td), Paragraph("Garantiza <b>CERO HUÉRFANOS</b> sin descartar actividad histórica.", style_td)],
        [Paragraph("E08", style_td_center), Paragraph("Saneamiento UTF-8 BOM", style_td), Paragraph("Lectura con encoding='utf-8-sig' y errors='replace'.", style_td), Paragraph("Compatibilidad total en entornos Windows.", style_td)],
        [Paragraph("E09", style_td_center), Paragraph("Cruce geográfico por ID", style_td), Paragraph("JOIN exacto por area_id entero hacia gold.dim_geografia.", style_td), Paragraph("Elimina el Fan Trap que ocurría al cruzar por nombres de ciudades homónimas.", style_td)],
        [Paragraph("E10", style_td_center), Paragraph("Auditoría en data_quality_log", style_td), Paragraph("Validación automatizada al cierre de run_gold_pipeline.py.", style_td), Paragraph("Deja evidencia persistente de 0 violaciones en meta.data_quality_log.", style_td)],
    ]
    t_eda = Table(eda_data, colWidths=[28, 125, 190, 180.28])
    t_eda.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), c_primary),
        ('GRID', (0,0), (-1,-1), 0.5, c_border),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, c_bg_light]),
        ('TOPPADDING', (0,0), (-1,-1), 3.4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3.4),
    ]))
    story.append(t_eda)
    story.append(PageBreak())

    # =========================================================================
    # PÁGINA 13: CAPÍTULO 8 - PROCESO ETL DE ALTO RENDIMIENTO
    # =========================================================================
    story.append(Paragraph("CAPÍTULO 8", style_chap_num))
    story.append(Paragraph("Proceso ETL de alto rendimiento", style_chap_title))
    story.append(Paragraph("Extracción quirúrgica bajo demanda y consulta SQL de agregación histórica diaria", style_chap_sub))

    story.append(Paragraph("8.1. SQL de Consolidación Histórica Diaria (etl/gold/populate_fact_tracks.sql)", style_sec_title))
    story.append(Paragraph(
        "La carga de <code>gold.fact_produccion_musical</code> resuelve fechas reales, artista principal, perfil de "
        "lanzamiento y agrupa (<code>GROUP BY</code>) por día y dimensiones conformadas:",
        style_body
    ))

    code_pop_gold = (
        "INSERT INTO gold.fact_produccion_musical (\n"
        "    fecha_key, artista_key, lanzamiento_key, geografia_key, formato_key, idioma_key,\n"
        "    lanzamientos_total, soportes_total, pistas_total, grabaciones_unicas_total,\n"
        "    duracion_total_ms, duracion_total_segundos, duracion_total_minutos,\n"
        "    pistas_con_isrc_total, pistas_largas_total, pistas_video_total, pistas_completas_total\n"
        ")\n"
        "SELECT\n"
        "    COALESCE(d.fecha_key, 0), COALESCE(da.artista_key, 0), COALESCE(dl.lanzamiento_key, 0),\n"
        "    COALESCE(dg.geografia_key, 0), COALESCE(df.formato_key, 0), COALESCE(di.idioma_key, 0),\n"
        "    COUNT(DISTINCT dp.release_id)::INTEGER AS lanzamientos_total,\n"
        "    COUNT(DISTINCT dp.medium_id)::INTEGER  AS soportes_total,\n"
        "    COUNT(dp.track_id)::INTEGER            AS pistas_total,\n"
        "    COUNT(DISTINCT dp.recording_id)::INTEGER AS grabaciones_unicas_total,\n"
        "    SUM(dp.duracion_ms)::BIGINT            AS duracion_total_ms,\n"
        "    ROUND(SUM(dp.duracion_ms) / 1000.0, 2) AS duracion_total_segundos,\n"
        "    ROUND(SUM(dp.duracion_ms) / 60000.0, 2) AS duracion_total_minutos,\n"
        "    SUM(dp.tiene_isrc)::INTEGER            AS pistas_con_isrc_total,\n"
        "    SUM(CASE WHEN dp.duracion_ms > 300000 THEN 1 ELSE 0 END)::INTEGER AS pistas_largas_total,\n"
        "    SUM(dp.es_video)::INTEGER              AS pistas_video_total,\n"
        "    SUM(CASE WHEN dp.duracion_ms > 0 THEN 1 ELSE 0 END)::INTEGER AS pistas_completas_total\n"
        "FROM detalle_pistas dp\n"
        "LEFT JOIN gold.dim_fecha d ON dp.fecha_candidata = d.fecha_key\n"
        "LEFT JOIN gold.dim_artista da ON dp.artista_id_resuelto = da.artista_id\n"
        "LEFT JOIN gold.dim_lanzamiento dl ON dp.estado_id = dl.estado_id\n"
        "   AND dp.empaque_id = dl.empaque_id AND dp.calidad_id = dl.calidad_id\n"
        "LEFT JOIN gold.dim_geografia dg ON dp.area_id_resuelta = dg.area_id\n"
        "LEFT JOIN gold.dim_formato df ON dp.formato_id_resuelto = df.formato_id\n"
        "LEFT JOIN gold.dim_idioma di ON dp.idioma_id_resuelto = di.idioma_id\n"
        "GROUP BY 1, 2, 3, 4, 5, 6;"
    )
    story.append(code_box(code_pop_gold))
    story.append(PageBreak())

    # =========================================================================
    # PÁGINA 14: CAPÍTULO 9 Y 10 - VISTAS MATERIALIZADAS Y MEDIDAS DAX EN ESPAÑOL
    # =========================================================================
    story.append(Paragraph("CAPÍTULO 9 & 10", style_chap_num))
    story.append(Paragraph("Vistas Materializadas en Español y Medidas DAX Aditivas", style_chap_title))
    story.append(Paragraph("Optimización OLAP en PostgreSQL 16 y consumo analítico en Power BI", style_chap_sub))

    story.append(Paragraph("9.1. Las 4 Vistas Materializadas Analíticas (sql/gold/05_aggregations.sql)", style_sec_title))
    mv_data = [
        [Paragraph("<b>Vista Materializada en Español</b>", style_th), Paragraph("<b>Requerimientos</b>", style_th), Paragraph("<b>Atributos y Métricas Pre-Calculadas (SUM)</b>", style_th)],
        [Paragraph("gold.mv_tendencias_produccion_anual", style_td_bold), Paragraph("RF01 & RF05", style_td_center), Paragraph("anio, decada, siglo, lanzamientos_total, soportes_total, pistas_total, artistas_activos, duracion_promedio_segundos, cobertura_isrc_pct.", style_td)],
        [Paragraph("gold.mv_analitica_artistas", style_td_bold), Paragraph("RF01, RF06 & RF08", style_td_center), Paragraph("artista_key, nombre_artista, tipo_artista, nombre_pais, anio_inicio, lanzamientos_total, pistas_total, pistas_con_isrc_total, cobertura_isrc_pct.", style_td)],
        [Paragraph("gold.mv_evolucion_formatos", style_td_bold), Paragraph("RF02 & RF04", style_td_center), Paragraph("anio, decada, nombre_formato, categoria_formato, lanzamientos_total, soportes_total, pistas_total, pistas_largas_total, duracion_promedio_segundos.", style_td)],
        [Paragraph("gold.mv_distribucion_geografica", style_td_bold), Paragraph("RF03 & RF06", style_td_center), Paragraph("geografia_key, nombre_pais, nombre_area, tipo_area, artistas_total, lanzamientos_total, pistas_total, pistas_con_isrc_total, duracion_total_horas.", style_td)],
    ]
    t_mv = Table(mv_data, colWidths=[150, 75, 298.28])
    t_mv.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), c_primary),
        ('GRID', (0,0), (-1,-1), 0.5, c_border),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, c_bg_light]),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(t_mv)
    story.append(Spacer(1, 8))

    story.append(Paragraph("10.1. Catálogo de Medidas DAX 100% Aditivas en Power BI", style_sec_title))
    dax_code = (
        "-- 1. VOLUMETRÍA HISTÓRICA ADITIVA\n"
        "Total Lanzamientos = SUM(gold_fact_produccion_musical[lanzamientos_total])\n"
        "Total Soportes     = SUM(gold_fact_produccion_musical[soportes_total])\n"
        "Total Pistas       = SUM(gold_fact_produccion_musical[pistas_total])\n\n"
        "-- 2. DURACIÓN PROMEDIO PONDERADA (SIN DISTORSIÓN POR CEROS)\n"
        "Duracion Promedio por Pista (Segundos) = \n"
        "DIVIDE(\n"
        "    SUM(gold_fact_produccion_musical[duracion_total_segundos]),\n"
        "    SUM(gold_fact_produccion_musical[pistas_completas_total]),\n"
        "    0\n"
        ")\n\n"
        "-- 3. TASA DE FORMALIZACIÓN ISRC Y CANCIONES LARGAS (> 5 MIN)\n"
        "Total Pistas con ISRC = SUM(gold_fact_produccion_musical[pistas_con_isrc_total])\n"
        "Tasa Cobertura ISRC % = DIVIDE([Total Pistas con ISRC], [Total Pistas], 0)\n"
        "Total Pistas Largas   = SUM(gold_fact_produccion_musical[pistas_largas_total])\n"
        "Proporcion Largas %   = DIVIDE([Total Pistas Largas], [Total Pistas], 0)"
    )
    story.append(code_box(dax_code))
    story.append(PageBreak())

    # =========================================================================
    # PÁGINA 15: CAPÍTULO 12 & 13 - DEFENSA ANTE EL DOCENTE Y CHECKLIST
    # =========================================================================
    story.append(Paragraph("CAPÍTULO 12 & 13", style_chap_num))
    story.append(Paragraph("Defensa del Modelo Estrella y Lista de Verificación", style_chap_title))
    story.append(Paragraph("Respuestas clave sobre el rediseño de la tabla de hechos y checklist de ejecución", style_chap_sub))

    def qa_item(num, question, answer):
        return KeepTogether([
            Paragraph(f"<b>P{num}: {question}</b>", style_subsec_title),
            Paragraph(f"<b>Respuesta de Defensa:</b> {answer}", style_body),
            Spacer(1, 4)
        ])

    story.append(qa_item(
        1, "¿Por qué la tabla de hechos ahora se llama gold.fact_produccion_musical y no contiene textos ni booleanos?",
        "Porque siguiendo estrictamente la teoría dimensional de Ralph Kimball y la corrección de la cátedra, una tabla de hechos debe almacenar el registro histórico cuantitativo del proceso de negocio en un grano definido (diario por dimensiones), conteniendo únicamente las claves foráneas (fecha_key, artista_key, lanzamiento_key, geografia_key, formato_key, idioma_key) y métricas numéricas 100% aditivas (lanzamientos_total, soportes_total, pistas_total, pistas_con_isrc_total, etc.)."
    ))
    story.append(qa_item(
        2, "¿Cómo lograron que lanzamientos_total sume múltiples lanzamientos por día en lugar de valer siempre 1?",
        "Transformamos gold.dim_lanzamiento en una Dimensión de Perfil de Lanzamiento conformada por las combinaciones únicas de estado_lanzamiento (Oficial, Promocional, Bootleg), tipo_empaque (Jewel Case, Digipak, Gatefold, Digital) y calidad_datos. Así evitamos una dimensión gigante de 5.8 millones de filas y logramos que todos los álbumes publicados por un artista en una fecha y formato se consoliden sumando el número real de lanzamientos en lanzamientos_total."
    ))
    story.append(qa_item(
        3, "¿De dónde provienen las fechas históricas reales de publicación hacia gold.dim_fecha?",
        "Provienen directamente de las tablas oficiales silver.release_country y silver.release_unknown_country extraídas del dump mbdump.tar.bz2 (Schema Sequence 31), las cuales contienen las columnas date_year, date_month y date_day reales de cada evento de lanzamiento musical."
    ))

    story.append(Spacer(1, 8))
    story.append(Paragraph("Secuencia Oficial de Comandos para Recrear y Certificar el DWH", style_sec_title))
    cmd_code = (
        "# 1. Levantar contenedor PostgreSQL 16 (puerto 5435)\n"
        "docker compose up -d\n\n"
        "# 2. Crear esquemas (meta, silver, gold), 10 tablas Silver y Modelo Estrella en Español\n"
        "python scripts/setup_database.py\n\n"
        "# 3. Ingestar las 10 tablas Silver (extrae automáticamente desde mbdump.tar.bz2 si falta alguna)\n"
        "python etl/silver/ingest_silver.py\n"
        "python etl/silver/ingest_tracks_sliced.py\n\n"
        "# 4. Poblar las 6 dimensiones en español, la tabla de hechos histórica y las 4 vistas materializadas\n"
        "python etl/gold/run_gold_pipeline.py\n\n"
        "# 5. Ejecutar auditoría de volumetría, métricas aditivas y cero huérfanos\n"
        "python scripts/verify_dwh.py"
    )
    story.append(code_box(cmd_code))

    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"[OK] Documento PDF de sustentacion generado exitosamente en: {filename}")


if __name__ == "__main__":
    output_path = sys.argv[1] if len(sys.argv) > 1 else "docs/Documento_Sustentacion_DWH_MusicBrainz.pdf"
    build_pdf(output_path)
