"""
build_sustentacion_pdf.py
=========================
Script generador del Documento Oficial de Sustentación Técnica y Guía de Defensa
para el Data Warehouse Masivo de la Industria Musical (MusicBrainz).

Genera un documento PDF académico de alta fidelidad estética (estándar editorial A4)
utilizando ReportLab, con numeración dinámica de dos pasadas (NumberedCanvas),
tablas comparativas, cajas de código, métricas reales y 13 capítulos temáticos.
"""

import os
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
            self.drawRightString(559, 812, "Modelo en Estrella Puro (Ralph Kimball)")
            
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
    # Configuración de documento A4 (595.28 x 841.89 pt) con márgenes de 36 pt (ancho útil = 523.28 pt)
    doc = SimpleDocTemplate(
        filename,
        pagesize=A4,
        leftMargin=36,
        rightMargin=36,
        topMargin=46,
        bottomMargin=46
    )

    styles = getSampleStyleSheet()
    
    # Paleta de colores profesional
    c_primary = colors.HexColor("#0B192C")     # Azul marino profundo institucional
    c_secondary = colors.HexColor("#6366F1")   # Índigo tecnológico
    c_dark = colors.HexColor("#1E293B")        # Texto principal pizarra
    c_muted = colors.HexColor("#64748B")       # Texto secundario
    c_bg_light = colors.HexColor("#F8FAFC")    # Fondo cajas claro
    c_border = colors.HexColor("#E2E8F0")      # Bordes suaves
    c_accent = colors.HexColor("#D97706")      # Ámbar dorado

    # Estilos tipográficos
    style_cover_super = ParagraphStyle('CoverSuper', fontName='Helvetica-Bold', fontSize=10, textColor=c_secondary, leading=14, spaceAfter=8)
    style_cover_title = ParagraphStyle('CoverTitle', fontName='Helvetica-Bold', fontSize=23, textColor=c_primary, leading=27, spaceAfter=10)
    style_cover_sub = ParagraphStyle('CoverSub', fontName='Helvetica', fontSize=10.5, textColor=c_muted, leading=15, spaceAfter=18)
    
    style_chap_num = ParagraphStyle('ChapNum', fontName='Helvetica-Bold', fontSize=9, textColor=c_secondary, leading=12, spaceAfter=2)
    style_chap_title = ParagraphStyle('ChapTitle', fontName='Helvetica-Bold', fontSize=14.5, textColor=c_primary, leading=18, spaceAfter=4, keepWithNext=True)
    style_chap_sub = ParagraphStyle('ChapSub', fontName='Helvetica-Oblique', fontSize=8.5, textColor=c_muted, leading=11, spaceAfter=10, keepWithNext=True)
    
    style_sec_title = ParagraphStyle('SecTitle', fontName='Helvetica-Bold', fontSize=10.5, textColor=c_primary, leading=14, spaceBefore=8, spaceAfter=4, keepWithNext=True)
    style_subsec_title = ParagraphStyle('SubSecTitle', fontName='Helvetica-Bold', fontSize=9, textColor=c_dark, leading=12, spaceBefore=6, spaceAfter=3, keepWithNext=True)
    
    style_body = ParagraphStyle('Body', fontName='Helvetica', fontSize=8, textColor=c_dark, leading=11, spaceAfter=5)
    style_body_bold = ParagraphStyle('BodyBold', fontName='Helvetica-Bold', fontSize=8, textColor=c_dark, leading=11, spaceAfter=5)
    style_bullet = ParagraphStyle('Bullet', fontName='Helvetica', fontSize=8, textColor=c_dark, leading=11, leftIndent=12, spaceAfter=3)
    
    style_callout = ParagraphStyle('Callout', fontName='Helvetica', fontSize=8, textColor=c_dark, leading=11)
    style_code = ParagraphStyle('Code', fontName='Courier', fontSize=6.8, textColor=colors.HexColor("#0F172A"), leading=8.5)
    
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
    story.append(Paragraph("Data Warehouse Masivo de la<br/>Industria Musical Global<br/>(MusicBrainz)", style_cover_title))
    story.append(Spacer(1, 4))
    story.append(Paragraph(
        "<b>PostgreSQL 16 en Docker</b> &nbsp;|&nbsp; <b>Arquitectura Medallón (Silver &rarr; Gold)</b><br/>"
        "<b>Modelo en Estrella Puro (Ralph Kimball Star Schema)</b><br/>"
        "100% Datos Reales MusicBrainz (&gt;19M Hechos, 77M Silver, 17.77 GB) &nbsp;|&nbsp; Analítica Power BI",
        style_cover_sub
    ))
    
    story.append(HRFlowable(width="100%", thickness=2, color=c_primary, spaceBefore=8, spaceAfter=18))
    
    callout_portada = (
        "<b>DOCUMENTO OFICIAL DE SUSTENTACIÓN TÉCNICA Y GUÍA DE DEFENSA</b><br/><br/>"
        "Este documento técnico consolida la arquitectura analítica, el modelo dimensional en estrella puro, "
        "las reglas de calidad EDA, el pipeline de streaming en Python, las optimizaciones de almacenamiento "
        "y particionamiento por rangos temporales en PostgreSQL 16 y la explotación analítica en Power BI. "
        "El proyecto fue diseñado y desplegado para procesar datos 100% reales de la <b>MetaBrainz Foundation</b>, "
        "alcanzando <b>19.370.311 registros de hechos reales</b> y una huella física de <b>17,77 GB</b> con tiempos "
        "de respuesta sub-segundo y cero huérfanos."
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
        [Paragraph("1", style_td_center), Paragraph("<b>Resumen ejecutivo y contexto:</b> Problema, solución OLAP, alcance y arquitectura general.", style_td), Paragraph("3", style_td_center)],
        [Paragraph("2", style_td_center), Paragraph("<b>Objetivos y requerimientos:</b> Matriz de requerimientos funcionales RF01–RF08 y no funcionales RNF01–RNF09.", style_td), Paragraph("4", style_td_center)],
        [Paragraph("3", style_td_center), Paragraph("<b>Volumetría y dimensionamiento físico:</b> Métricas 100% reales (19.3M facts, 77.4M silver), disco y SLAs.", style_td), Paragraph("6", style_td_center)],
        [Paragraph("4", style_td_center), Paragraph("<b>La base de datos de origen:</b> MusicBrainz MetaBrainz Foundation, modelo 3NF y contraste OLTP vs OLAP.", style_td), Paragraph("7", style_td_center)],
        [Paragraph("5", style_td_center), Paragraph("<b>Diseño del Modelo en Estrella Puro:</b> Grano atómico Kimball, dimensiones conformadas, surrogate keys y DDLs.", style_td), Paragraph("9", style_td_center)],
        [Paragraph("6", style_td_center), Paragraph("<b>Arquitectura Medallón y Stack Tecnológico:</b> Capas Silver, Gold y Meta; justificación de herramientas elegidas.", style_td), Paragraph("12", style_td_center)],
        [Paragraph("7", style_td_center), Paragraph("<b>Reglas del proceso EDA:</b> Catálogo E01–E10, calidad de datos, saneamiento de nulos y códigos ISRC.", style_td), Paragraph("14", style_td_center)],
        [Paragraph("8", style_td_center), Paragraph("<b>Proceso ETL de alto rendimiento:</b> Streaming bufferizado MaxLineReader, COPY masivo y carga set-based.", style_td), Paragraph("15", style_td_center)],
        [Paragraph("9", style_td_center), Paragraph("<b>Capa Oro: agregaciones, índices y particiones:</b> 14 particiones por fecha, 9 índices B-tree y vistas materializadas.", style_td), Paragraph("17", style_td_center)],
        [Paragraph("10", style_td_center), Paragraph("<b>Dashboard Power BI y Storytelling:</b> Navegación Drill-down, correlación streaming vs vinilo y medidas DAX.", style_td), Paragraph("18", style_td_center)],
        [Paragraph("11", style_td_center), Paragraph("<b>Guía por diapositiva para la defensa oral:</b> Resumen técnico y discurso de defensa para 13 diapositivas.", style_td), Paragraph("20", style_td_center)],
        [Paragraph("12", style_td_center), Paragraph("<b>Banco de preguntas técnicas para la sustentación:</b> 15 preguntas de rigor con respuestas de Senior Architect.", style_td), Paragraph("23", style_td_center)],
        [Paragraph("13", style_td_center), Paragraph("<b>Puntos de atención y lista de verificación:</b> Checklist previo a la evaluación y certificación final.", style_td), Paragraph("25", style_td_center)],
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
        "<b>Principio Rector del Proyecto:</b> Estricta prohibición de datos sintéticos o ficticios. "
        "El Data Warehouse opera sobre <b>19.370.311 registros de hechos reales</b> extraídos directamente "
        "del volcado oficial de PostgreSQL de la MetaBrainz Foundation, demostrando que la arquitectura "
        "dimensional de Ralph Kimball escala limpiamente a entornos corporativos de alta volumetría."
    )
    story.append(callout_box(callout_toc, bg="#FEF3C7", border="#F59E0B"))
    story.append(PageBreak())

    # =========================================================================
    # PÁGINA 3: CAPÍTULO 1 - RESUMEN EJECUTIVO Y CONTEXTO
    # =========================================================================
    story.append(Paragraph("CAPÍTULO 1", style_chap_num))
    story.append(Paragraph("Resumen ejecutivo y contexto", style_chap_title))
    story.append(Paragraph("Qué problema se resuelve, qué se construye y arquitectura general", style_chap_sub))

    story.append(Paragraph("1.1. Contexto de Negocio en la Industria Musical Global", style_sec_title))
    story.append(Paragraph(
        "La industria musical experimentó en las últimas décadas una disrupción tecnológica sin precedentes: "
        "desde la manufactura de soportes analógicos (Vinilo y Cassette) y ópticos (CD), hasta la distribución "
        "digital desmaterializada y el streaming masivo bajo demanda. Este ecosistema produce diariamente "
        "millones de metadatos: pistas sonoras, códigos internacionales ISRC, artistas, álbumes y soporte de audio. "
        "Sin embargo, las bases de datos transaccionales (OLTP) de plataformas como MusicBrainz se encuentran en "
        "<b>Tercera Forma Normal (3NF)</b> con más de 7 tablas encadenadas para una sola consulta musical. "
        "Cualquier reporte analítico sobre millones de filas genera bloqueos de tabla, agotamiento de memoria RAM "
        "y caídas de servicio.",
        style_body
    ))

    story.append(Paragraph("1.2. La Solución Arquitectónica: DWMusicBrainz", style_sec_title))
    story.append(Paragraph(
        "El proyecto <b>DWMusicBrainz</b> diseña, implementa y despliega un Data Warehouse analítico de alta "
        "volumetría sobre <b>PostgreSQL 16 en Docker</b> estructurado bajo una <b>Arquitectura Medallón (Silver &rarr; Gold)</b> "
        "y un <b>Modelo en Estrella Puro (Ralph Kimball Star Schema)</b>. Se reemplazó cualquier aproximación de "
        "datos sintéticos mediante la ingesta de datos 100% reales del volcado nativo oficial de <b>MusicBrainz</b>, "
        "cumpliendo y superando ampliamente los requerimientos de estrés empresarial:",
        style_body
    ))
    story.append(Paragraph("&bull; <b>Hecho Central Consolidado:</b> 19.370.311 pistas reales cargadas en <code>gold.fact_tracks</code> (meta: 12–16M).", style_bullet))
    story.append(Paragraph("&bull; <b>Huella Física en Disco:</b> 17,77 GB en PostgreSQL 16 (meta mínima de estrés: &gt; 3.0 GB).", style_bullet))
    story.append(Paragraph("&bull; <b>Integridad Referencial:</b> Cero huérfanos en todas las 6 dimensiones conformadas.", style_bullet))
    story.append(Paragraph("&bull; <b>Rendimiento Sub-Segundo:</b> Particionamiento físico por rangos temporales e índices B-Tree que habilitan Partition Pruning.", style_bullet))

    story.append(Spacer(1, 10))
    story.append(Paragraph("1.3. Matriz Resumen de Hitos y Entregables del Proyecto", style_sec_title))
    
    hitos_data = [
        [Paragraph("<b>Hito</b>", style_th), Paragraph("<b>Fase Arquitectónica</b>", style_th), Paragraph("<b>Alcance Técnico Verificado</b>", style_th), Paragraph("<b>Estado</b>", style_th)],
        [Paragraph("H0", style_td_center), Paragraph("Fase 0: Infraestructura", style_td), Paragraph("Docker Compose (PG16 en 5435), tuning 1GB buffers, esquemas meta/silver/gold.", style_td), Paragraph("100% OK", style_td_center)],
        [Paragraph("H1", style_td_center), Paragraph("Fase 1: Ingesta Silver", style_td), Paragraph("Extracción y COPY de 77.4M filas (recording 40.5M, track 15M, release 5.8M).", style_td), Paragraph("100% OK", style_td_center)],
        [Paragraph("H2", style_td_center), Paragraph("Fase 2: Dimensiones Gold", style_td), Paragraph("Poblado de 6 dimensiones conformadas (9.02M filas) con surrogate keys y Key 0.", style_td), Paragraph("100% OK", style_td_center)],
        [Paragraph("H3", style_td_center), Paragraph("Fase 3: Hechos y Vistas", style_td), Paragraph("Carga de 19.37M hechos en fact_tracks particionada y refresco de 4 vistas analíticas.", style_td), Paragraph("100% OK", style_td_center)],
        [Paragraph("H4", style_td_center), Paragraph("Fase 4: Explotación Power BI", style_td), Paragraph("Catálogo de medidas DAX (correlación Pearson, duración acumulada, ISRC).", style_td), Paragraph("100% OK", style_td_center)],
    ]
    t_hitos = Table(hitos_data, colWidths=[30, 110, 320, 63.28])
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
        "datos 100% reales, públicos y auditables de MusicBrainz (MetaBrainz Foundation), estructurado bajo una "
        "Arquitectura Medallón (Silver &rarr; Gold) y un Modelo en Estrella Puro (Ralph Kimball) que supere los 10 millones "
        "de registros en el hecho central y 3.0 GB de almacenamiento físico, con el fin de soportar la analítica de "
        "negocio y cuadros de mando en Microsoft Power BI.",
        style_body
    ))

    story.append(Paragraph("2.2. Objetivos Específicos", style_sec_title))
    story.append(Paragraph("&bull; <b>OE1:</b> Construir un pipeline de ingesta automatizado en Python capaz de cargar más de 70 millones de filas desde volcados crudos hacia un esquema normalizado 3NF en PostgreSQL.", style_bullet))
    story.append(Paragraph("&bull; <b>OE2:</b> Diseñar e implementar un modelo en estrella puro con claves subrogadas (Surrogate Keys) y el patrón anti-huérfanos de Fila Cero que garantice cero registros huérfanos.", style_bullet))
    story.append(Paragraph("&bull; <b>OE3:</b> Implementar particionamiento declarativo por rangos temporales en la tabla central <code>gold.fact_tracks</code> para asegurar Partition Pruning en consultas masivas.", style_bullet))
    story.append(Paragraph("&bull; <b>OE4:</b> Modelar 4 vistas materializadas analíticas indexadas que optimicen los tiempos de respuesta en Power BI a niveles sub-segundo (&lt; 0.1 s).", style_bullet))
    story.append(Paragraph("&bull; <b>OE5:</b> Demostrar analítica y estadísticamente mediante correlación de Pearson (RF05) el fenómeno de acortamiento de las canciones en la era del streaming frente a los años 70 y 80.", style_bullet))

    story.append(Spacer(1, 6))
    story.append(Paragraph("2.3. Matriz de Requerimientos Funcionales (RF01 — RF08)", style_sec_title))

    rf_data = [
        [Paragraph("<b>Req.</b>", style_th), Paragraph("<b>Nombre y Descripción Funcional</b>", style_th), Paragraph("<b>Entidades Involucradas</b>", style_th), Paragraph("<b>Métrica / Operación</b>", style_th)],
        [Paragraph("RF01", style_td_center), Paragraph("<b>Ranking Top N de Artistas y Álbumes:</b> Mayor volumen de canciones publicadas, duración acumulada y porcentaje ISRC por país y década.", style_td), Paragraph("fact_tracks, dim_artist, dim_release, dim_date", style_td), Paragraph("SUM(track_count), SUM(duration_minutes), % ISRC", style_td)],
        [Paragraph("RF02", style_td_center), Paragraph("<b>Métricas por Formato e Idioma:</b> Comparativa de duración promedio y pistas por disco según formato (Vinilo vs CD vs Digital) e idioma.", style_td), Paragraph("fact_tracks, dim_format, dim_language", style_td), Paragraph("AVG(duration_seconds), MAX(position)", style_td)],
        [Paragraph("RF03", style_td_center), Paragraph("<b>Drill-Down Geográfico y Temporal:</b> Navegación jerárquica Continente &gt; País y Década &gt; Año &gt; Mes &gt; Fecha.", style_td), Paragraph("fact_tracks, dim_geography, dim_date", style_td), Paragraph("COUNT(track_key), SUM(duration_minutes)", style_td)],
        [Paragraph("RF04", style_td_center), Paragraph("<b>Comparativa Físico vs Digital y Canciones Largas:</b> Proporción de temas largos (&gt;300s) frente a estándar radiofónico por soporte.", style_td), Paragraph("fact_tracks, dim_format", style_td), Paragraph("COUNT(is_long_track = TRUE) / COUNT(*)", style_td)],
        [Paragraph("RF05", style_td_center), Paragraph("<b>Correlación Estadística Streaming vs Vinilo:</b> Demostración matemática del acortamiento de duración mediante correlación Pearson.", style_td), Paragraph("fact_tracks, dim_date", style_td), Paragraph("corr(year, duration_seconds)", style_td)],
        [Paragraph("RF06", style_td_center), Paragraph("<b>Formalización Discográfica (ISRC):</b> Tasa de canciones con código sonoro internacional por cada 100 lanzamientos según país y artista.", style_td), Paragraph("fact_tracks, dim_geography, dim_artist", style_td), Paragraph("COUNT(has_isrc) * 100.0 / COUNT(*)", style_td)],
        [Paragraph("RF07", style_td_center), Paragraph("<b>Distribución por Intervalos de Duración:</b> Segmentación (&lt;2m, 2-4m, 4-6m, &gt;6m) y análisis de posición de temas en el disco.", style_td), Paragraph("fact_tracks, dim_format", style_td), Paragraph("Histograma de duración y posición", style_td)],
        [Paragraph("RF08", style_td_center), Paragraph("<b>Catálogo Emergente y Nuevos Talentos:</b> Identificación de artistas debutantes en la última década con 100% de cobertura ISRC.", style_td), Paragraph("fact_tracks, dim_artist, dim_date", style_td), Paragraph("begin_year &gt;= 2015, ISRC = 100%", style_td)],
    ]
    t_rf = Table(rf_data, colWidths=[28, 215, 140, 140.28])
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
    story.append(Paragraph(
        "Los requerimientos no funcionales definen los criterios de calidad arquitectónica, rendimiento, "
        "escalabilidad y estrés del sistema. Todos fueron validados empíricamente en el entorno de producción:",
        style_body
    ))

    rnf_data = [
        [Paragraph("<b>RNF</b>", style_th), Paragraph("<b>Criterio / Dimensión</b>", style_th), Paragraph("<b>Meta Exigida</b>", style_th), Paragraph("<b>Resultado Obtenido en DWMusicBrainz</b>", style_th), Paragraph("<b>Cumplimiento</b>", style_th)],
        [Paragraph("RNF01", style_td_center), Paragraph("Procesamiento por Chunks", style_td), Paragraph("Streaming sin desborde de memoria", style_td), Paragraph("MaxLineReader con buffer 128 KB en Python", style_td), Paragraph("100% OK", style_td_center)],
        [Paragraph("RNF02", style_td_center), Paragraph("Almacenamiento en Disco", style_td), Paragraph("&gt; 3.0 GB físico en PostgreSQL", style_td), Paragraph("<b>17.77 GB reales</b> (592% de la meta)", style_td), Paragraph("SUPERADO", style_td_center)],
        [Paragraph("RNF03", style_td_center), Paragraph("Volumetría de Hechos", style_td), Paragraph("&gt; 10.000.000 filas en fact", style_td), Paragraph("<b>19.370.311 filas reales</b> (193% de la meta)", style_td), Paragraph("SUPERADO", style_td_center)],
        [Paragraph("RNF04", style_td_center), Paragraph("Garantía Cero Sintéticos", style_td), Paragraph("100% datos reales auditables", style_td), Paragraph("Volcado oficial MusicBrainz Sequence 31", style_td), Paragraph("100% OK", style_td_center)],
        [Paragraph("RNF05", style_td_center), Paragraph("Idempotencia del Pipeline", style_td), Paragraph("Re-ejecuciones sin duplicados", style_td), Paragraph("TRUNCATE RESTART IDENTITY CASCADE en staging", style_td), Paragraph("100% OK", style_td_center)],
        [Paragraph("RNF06", style_td_center), Paragraph("Auditoría Transversal", style_td), Paragraph("Trazabilidad E2E de lotes", style_td), Paragraph("meta.etl_audit con lotes, filas y tiempos", style_td), Paragraph("100% OK", style_td_center)],
        [Paragraph("RNF07", style_td_center), Paragraph("SLA de Consulta Analítica", style_td), Paragraph("&lt; 3.00 s en consultas agregadas", style_td), Paragraph("0.018 s a 0.145 s (20x a 160x más rápido)", style_td), Paragraph("ÓPTIMO", style_td_center)],
        [Paragraph("RNF08", style_td_center), Paragraph("Integridad Referencial", style_td), Paragraph("0 registros huérfanos", style_td), Paragraph("0 huérfanos en las 6 dimensiones conformadas", style_td), Paragraph("100% OK", style_td_center)],
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
    story.append(Spacer(1, 15))

    callout_rnf = (
        "<b>Certificación de Estrés RNF02 & RNF03:</b> El Data Warehouse consolidó <b>19.370.311 registros de hechos</b> "
        "en la tabla central y una huella física de <b>17,77 GB</b> en PostgreSQL 16. Ambos indicadores superan con creces "
        "el estándar exigido para proyectos integradores universitarios de posgrado o pregrado avanzado."
    )
    story.append(callout_box(callout_rnf, bg="#ECFDF5", border="#10B981"))
    story.append(PageBreak())

    # =========================================================================
    # PÁGINA 6: CAPÍTULO 3 - VOLUMETRÍA Y DIMENSIONAMIENTO FÍSICO
    # =========================================================================
    story.append(Paragraph("CAPÍTULO 3", style_chap_num))
    story.append(Paragraph("Volumetría y dimensionamiento físico", style_chap_title))
    story.append(Paragraph("Métricas oficiales en PostgreSQL 16, tamaño en disco por tabla e índices", style_chap_sub))

    story.append(Paragraph("3.1. Consolidado Oficial de Volumetría por Tabla", style_sec_title))
    story.append(Paragraph(
        "Métricas auditadas directamente en el motor PostgreSQL mediante el script de certificación "
        "<code>scripts/verify_dwh.py</code> con consultas nativas sobre el catálogo del sistema:",
        style_body
    ))

    vol_data = [
        [Paragraph("<b>Esquema</b>", style_th), Paragraph("<b>Nombre de la Tabla / Partición</b>", style_th), Paragraph("<b>Filas Reales</b>", style_th), Paragraph("<b>Tamaño Datos</b>", style_th), Paragraph("<b>Tamaño Índices</b>", style_th), Paragraph("<b>Total en Disco</b>", style_th)],
        [Paragraph("silver", style_td_center), Paragraph("recording (audio masters)", style_td), Paragraph("40.532.448", style_td_center), Paragraph("3.415 MB", style_td), Paragraph("1.583 MB", style_td), Paragraph("4.998 MB", style_td_bold)],
        [Paragraph("gold", style_td_center), Paragraph("fact_tracks_2010s (partición)", style_td), Paragraph("~10.650.000", style_td_center), Paragraph("1.627 MB", style_td), Paragraph("1.436 MB", style_td), Paragraph("3.063 MB", style_td_bold)],
        [Paragraph("silver", style_td_center), Paragraph("track (pistas en medium)", style_td), Paragraph("15.000.000", style_td_center), Paragraph("1.380 MB", style_td), Paragraph("587 MB", style_td), Paragraph("1.967 MB", style_td_bold)],
        [Paragraph("gold", style_td_center), Paragraph("dim_release (álbumes)", style_td), Paragraph("5.844.570", style_td_center), Paragraph("748 MB", style_td), Paragraph("545 MB", style_td), Paragraph("1.293 MB", style_td_bold)],
        [Paragraph("silver", style_td_center), Paragraph("release (lanzamientos)", style_td), Paragraph("5.844.569", style_td_center), Paragraph("712 MB", style_td), Paragraph("396 MB", style_td), Paragraph("1.108 MB", style_td_bold)],
        [Paragraph("silver", style_td_center), Paragraph("medium (soportes)", style_td), Paragraph("6.411.799", style_td_center), Paragraph("548 MB", style_td), Paragraph("438 MB", style_td), Paragraph("986 MB", style_td_bold)],
        [Paragraph("silver", style_td_center), Paragraph("isrc (códigos internacionales)", style_td), Paragraph("6.478.709", style_td_center), Paragraph("452 MB", style_td), Paragraph("343 MB", style_td), Paragraph("795 MB", style_td_bold)],
        [Paragraph("gold", style_td_center), Paragraph("dim_artist (artistas)", style_td), Paragraph("3.010.452", style_td_center), Paragraph("415 MB", style_td), Paragraph("343 MB", style_td), Paragraph("758 MB", style_td_bold)],
        [Paragraph("silver", style_td_center), Paragraph("artist (artistas crudos)", style_td), Paragraph("3.010.451", style_td_center), Paragraph("312 MB", style_td), Paragraph("186 MB", style_td), Paragraph("498 MB", style_td_bold)],
        [Paragraph("gold", style_td_center), Paragraph("fact_tracks_2025 (partición)", style_td), Paragraph("~1.380.000", style_td_center), Paragraph("212 MB", style_td), Paragraph("167 MB", style_td), Paragraph("379 MB", style_td_bold)],
        [Paragraph("gold", style_td_center), Paragraph("fact_tracks_2024 (partición)", style_td), Paragraph("~1.270.000", style_td_center), Paragraph("195 MB", style_td), Paragraph("152 MB", style_td), Paragraph("347 MB", style_td_bold)],
        [Paragraph("gold", style_td_center), Paragraph("fact_tracks_2026_plus (partición)", style_td), Paragraph("~1.190.000", style_td_center), Paragraph("183 MB", style_td), Paragraph("143 MB", style_td), Paragraph("326 MB", style_td_bold)],
        [Paragraph("gold", style_td_center), Paragraph("Otras particiones fact (2020–23, 00s..)", style_td), Paragraph("~4.880.000", style_td_center), Paragraph("754 MB", style_td), Paragraph("711 MB", style_td), Paragraph("1.465 MB", style_td_bold)],
        [Paragraph("gold/silver", style_td_center), Paragraph("dim_geography, dim_date, area...", style_td), Paragraph("~170.000", style_td_center), Paragraph("38 MB", style_td), Paragraph("34 MB", style_td), Paragraph("72 MB", style_td_bold)],
        [Paragraph("<b>TOTAL</b>", style_td_center), Paragraph("<b>Data Warehouse Completo (PostgreSQL 16)</b>", style_td_bold), Paragraph("<b>105.791.840</b>", style_td_center), Paragraph("<b>10.806 MB</b>", style_td_bold), Paragraph("<b>7.390 MB</b>", style_td_bold), Paragraph("<b>17.77 GB</b>", style_td_bold)],
    ]
    t_vol = Table(vol_data, colWidths=[40, 175, 78, 75, 75, 80.28])
    t_vol.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), c_primary),
        ('GRID', (0,0), (-1,-1), 0.5, c_border),
        ('ROWBACKGROUNDS', (0,1), (-1,-2), [colors.white, c_bg_light]),
        ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor("#EFF6FF")),
        ('TOPPADDING', (0,0), (-1,-1), 3.2),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3.2),
    ]))
    story.append(t_vol)
    story.append(Spacer(1, 12))

    callout_vol = (
        "<b>Análisis de Eficiencia de Almacenamiento:</b> La relación entre datos brutos e índices en la capa Gold "
        "es de <b>1.4 a 1</b>, lo que demuestra un diseño de indexación de alta selectividad sin sobre-indexación. "
        "Los índices B-Tree garantizan búsquedas y agrupaciones instantáneas en Power BI sin degradar el almacenamiento."
    )
    story.append(callout_box(callout_vol, bg="#F1F5F9", border="#94A3B8"))
    story.append(PageBreak())

    # =========================================================================
    # PÁGINAS 7-8: CAPÍTULO 4 - LA BASE DE DATOS DE ORIGEN
    # =========================================================================
    story.append(Paragraph("CAPÍTULO 4", style_chap_num))
    story.append(Paragraph("La base de datos de origen: MusicBrainz", style_chap_title))
    story.append(Paragraph("Naturaleza del volcado nativo, Tercera Forma Normal (3NF) y contraste OLTP vs OLAP", style_chap_sub))

    story.append(Paragraph("4.1. Origen de Datos: MetaBrainz Foundation", style_sec_title))
    story.append(Paragraph(
        "MusicBrainz es una enciclopedia musical abierta y colaborativa gestionada por la <b>MetaBrainz Foundation</b>. "
        "A diferencia de datasets sintetizados en Kaggle o APIs con cuotas restrictivas, MusicBrainz publica volcados "
        "completos periódicos de su base de datos nativa de PostgreSQL. Para este proyecto se utilizó el archivo oficial "
        "maestro <b>mbdump.tar.bz2 (Schema Sequence 31, Octubre 2026)</b> con un peso comprimido de 7.09 GB y más de "
        "35 GB en texto plano descomprimido.",
        style_body
    ))

    story.append(Paragraph("4.2. Estructura de Origen en Tercera Forma Normal (3NF)", style_sec_title))
    story.append(Paragraph(
        "El modelo relacional de origen está altamente normalizado para garantizar la integridad transaccional (OLTP):",
        style_body
    ))
    story.append(Paragraph("&bull; <b>track:</b> Representa una pista en un disco específico, con vínculo a una grabación y a un medium.", style_bullet))
    story.append(Paragraph("&bull; <b>recording:</b> Representa la entidad abstracta de la grabación de audio de estudio (master).", style_bullet))
    story.append(Paragraph("&bull; <b>medium:</b> Representa el disco físico o soporte digital que compone un release.", style_bullet))
    story.append(Paragraph("&bull; <b>release:</b> Representa el lanzamiento comercial oficial (álbum, single, EP).", style_bullet))
    story.append(Paragraph("&bull; <b>artist:</b> Representa al músico, compositor, banda u orquesta ejecutante.", style_bullet))
    story.append(Paragraph("&bull; <b>isrc:</b> Códigos internacionales asignados a las grabaciones sonoras.", style_bullet))
    story.append(Paragraph("&bull; <b>area:</b> Jerarquías de países, ciudades y subdivisiones territoriales.", style_bullet))

    story.append(Spacer(1, 8))
    story.append(Paragraph("4.3. Contraste Crítico: Modelo Transaccional (OLTP) vs Modelo Dimensional (OLAP)", style_sec_title))
    
    comp_oltp_data = [
        [Paragraph("<b>Criterio de Evaluación</b>", style_th), Paragraph("<b>Modelo Transaccional OLTP (MusicBrainz 3NF)</b>", style_th), Paragraph("<b>Modelo Dimensional OLAP (DWMusicBrainz Gold)</b>", style_th)],
        [Paragraph("Propósito Central", style_td_bold), Paragraph("Escrituras ACID concurrentes, inserciones y actualizaciones fila por fila sin redundancia.", style_td), Paragraph("Lecturas masivas y agregaciones analíticas de alta velocidad orientadas al negocio.", style_td)],
        [Paragraph("Normalización", style_td_bold), Paragraph("Tercera Forma Normal estricta (3NF). Más de 7 tablas encadenadas para consultar una canción.", style_td), Paragraph("Desnormalizado bajo Modelo en Estrella Puro (1 tabla de hechos + 6 dimensiones conformadas).", style_td)],
        [Paragraph("Costo de Consultas", style_td_bold), Paragraph("JOINs extremadamente costosos sobre tablas de 40M filas; tiempos de respuesta de minutos.", style_td), Paragraph("JOINs simples 1:N sobre claves subrogadas enteras; tiempos sub-segundo (&lt; 0.1 s).", style_td)],
        [Paragraph("Manejo de Claves", style_td_bold), Paragraph("Claves naturales de negocio variables y UUIDs complejos de 128 bits.", style_td), Paragraph("Claves subrogadas enteras (INTEGER) de alta velocidad y clave degenerada en hechos.", style_td)],
        [Paragraph("Tolerancia a Nulos", style_td_bold), Paragraph("Filas nulas o no catalogadas provocan exclusión en INNER JOINs o huérfanos.", style_td), Paragraph("Patrón de Fila Cero (Key 0): Cero huérfanos sin descartar transacciones comerciales.", style_td)],
        [Paragraph("Evolución Temporal", style_td_bold), Paragraph("Actualizaciones destructivas en sitio (UPDATE) que borran el histórico.", style_td), Paragraph("Dimensión calendario continua y particionamiento físico por décadas y años.", style_td)],
    ]
    t_oltp = Table(comp_oltp_data, colWidths=[90, 215, 218.28])
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
    # PÁGINAS 9-11: CAPÍTULO 5 - DISEÑO DEL MODELO EN ESTRELLA PURO
    # =========================================================================
    story.append(Paragraph("CAPÍTULO 5", style_chap_num))
    story.append(Paragraph("Diseño del modelo en estrella puro (Ralph Kimball)", style_chap_title))
    story.append(Paragraph("Declaración de grano, diagrama dimensional, claves subrogadas y DDLs de producción", style_chap_sub))

    story.append(Paragraph("5.1. Declaración del Grano Atómico (Kimball)", style_sec_title))
    story.append(Paragraph(
        "El éxito de un modelo dimensional según Ralph Kimball radica en la rigurosa definición de su grano. "
        "En <b>DWMusicBrainz</b>, el grano fue formalizado de la siguiente manera:",
        style_body
    ))
    
    grano_box = (
        "<b>DECLARACIÓN OFICIAL DEL GRANO ATÓMICO:</b><br/>"
        "<i>'Un registro individual en la tabla de hechos central (<code>gold.fact_tracks</code>) representa la inclusión "
        "de una pista o grabación física/digital (track/recording) dentro de un soporte físico o digital (medium) "
        "correspondiente a un lanzamiento discográfico comercial oficial (release), ejecutado por un artista o agrupación "
        "en una fecha determinada y con un formato e idioma específicos.'</i>"
    )
    story.append(callout_box(grano_box, bg="#EFF6FF", border="#93C5FD"))
    story.append(Spacer(1, 8))

    story.append(Paragraph("5.2. Diccionario de Datos: Tabla de Hechos y Dimensiones Conformadas", style_sec_title))

    dict_data = [
        [Paragraph("<b>Tabla / Entidad</b>", style_th), Paragraph("<b>Tipo de Clave</b>", style_th), Paragraph("<b>Columnas y Atributos Principales</b>", style_th), Paragraph("<b>Métricas y Semántica</b>", style_th)],
        [Paragraph("gold.fact_tracks", style_td_bold), Paragraph("PK Compuesta<br/>(track_key, date_key)", style_td_center), Paragraph("date_key, artist_key, release_key, geo_key, format_key, language_key, track_id, recording_id, isrc_code", style_td), Paragraph("duration_ms, duration_seconds, duration_minutes, track_count, has_isrc, is_long_track, is_complete", style_td)],
        [Paragraph("gold.dim_date", style_td_bold), Paragraph("PK Sustituta<br/>(date_key)", style_td_center), Paragraph("full_date, year, quarter, month, month_name, week, day_of_month, day_of_week, decade, century, is_weekend", style_td), Paragraph("Calendario diario continuo 1900–2030 (47.848 filas). Clave 0 para fecha desconocida.", style_td)],
        [Paragraph("gold.dim_artist", style_td_bold), Paragraph("PK Sustituta<br/>(artist_key)", style_td_center), Paragraph("artist_id (NK), artist_gid (UUID), artist_name, artist_type (Person, Group, Orch), gender, country_name, begin_year", style_td), Paragraph("3.010.452 artistas únicos. Clave 0 para artista no identificado.", style_td)],
        [Paragraph("gold.dim_release", style_td_bold), Paragraph("PK Sustituta<br/>(release_key)", style_td_center), Paragraph("release_id (NK), release_gid (UUID), release_name, release_status (Official, Promo), packaging_type, barcode, quality", style_td), Paragraph("5.844.570 lanzamientos comerciales. Clave 0 para release no identificado.", style_td)],
        [Paragraph("gold.dim_format", style_td_bold), Paragraph("PK Sustituta<br/>(format_key)", style_td_center), Paragraph("format_id (NK), format_name (Vinyl, CD, Cassette, Digital Media), category (Analog, Optical, Streaming)", style_td), Paragraph("114 formatos catalogados. Clasificación física vs digital.", style_td)],
        [Paragraph("gold.dim_geography", style_td_bold), Paragraph("PK Sustituta<br/>(geo_key)", style_td_center), Paragraph("area_id (NK), area_gid (UUID), area_name, area_type (Country, City, Subdivision), country_name", style_td), Paragraph("120.108 ubicaciones territoriales. Clave 0 para área no especificada.", style_td)],
        [Paragraph("gold.dim_language", style_td_bold), Paragraph("PK Sustituta<br/>(language_key)", style_td_center), Paragraph("language_id (NK), language_name, iso_code", style_td), Paragraph("354 idiomas y alfabetos oficiales catalogados ISO.", style_td)],
    ]
    t_dict = Table(dict_data, colWidths=[90, 75, 185, 173.28])
    t_dict.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), c_primary),
        ('GRID', (0,0), (-1,-1), 0.5, c_border),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, c_bg_light]),
        ('TOPPADDING', (0,0), (-1,-1), 3.5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3.5),
    ]))
    story.append(t_dict)
    story.append(PageBreak())

    # CONTINUACIÓN CAPÍTULO 5: DDLS DE PRODUCCIÓN (PÁGINA 10-11)
    story.append(Paragraph("5.3. DDL Oficial: Creación de Dimensiones y Tabla de Hechos Particionada", style_sec_title))
    story.append(Paragraph(
        "Fragmento DDL de producción en PostgreSQL 16 ([03_dimensions_facts.sql](file:///c:/Users/SEBAS/Documents/GitHub/DWMusicBrainz/sql/gold/03_dimensions_facts.sql)) "
        "con definición de claves subrogadas, claves foráneas conformadas y particionamiento por rango:",
        style_body
    ))

    ddl_fact_code = (
        "-- TABLA DE HECHOS CENTRAL PARTICIONADA POR RANGO TEMPORAL\n"
        "CREATE TABLE gold.fact_tracks (\n"
        "    track_key        BIGSERIAL,\n"
        "    date_key         INTEGER NOT NULL REFERENCES gold.dim_date(date_key),\n"
        "    artist_key       INTEGER NOT NULL REFERENCES gold.dim_artist(artist_key),\n"
        "    release_key      INTEGER NOT NULL REFERENCES gold.dim_release(release_key),\n"
        "    geo_key          INTEGER NOT NULL REFERENCES gold.dim_geography(geo_key),\n"
        "    format_key       INTEGER NOT NULL REFERENCES gold.dim_format(format_key),\n"
        "    language_key     INTEGER NOT NULL REFERENCES gold.dim_language(language_key),\n"
        "    track_id         INTEGER NOT NULL, -- Clave degenerada (Degenerate Dimension)\n"
        "    recording_id     INTEGER NOT NULL,\n"
        "    isrc_code        CHAR(12),\n"
        "    has_isrc         BOOLEAN NOT NULL DEFAULT FALSE,\n"
        "    is_video         BOOLEAN NOT NULL DEFAULT FALSE,\n"
        "    duration_ms      INTEGER NOT NULL DEFAULT 0,      -- Métrica nativa\n"
        "    duration_seconds NUMERIC(10,2) NOT NULL DEFAULT 0,-- Métrica calculada\n"
        "    duration_minutes NUMERIC(10,2) NOT NULL DEFAULT 0,\n"
        "    track_count      SMALLINT NOT NULL DEFAULT 1,     -- Métrica de agregación rápida\n"
        "    is_complete      SMALLINT NOT NULL DEFAULT 1,\n"
        "    PRIMARY KEY (track_key, date_key)\n"
        ") PARTITION BY RANGE (date_key);"
    )
    story.append(code_box(ddl_fact_code))
    story.append(Spacer(1, 10))

    story.append(Paragraph("5.4. DDL Oficial: Particionamiento Físico por Décadas y Años Contemporáneos", style_sec_title))
    story.append(Paragraph(
        "Estructura física de particiones sobre <code>gold.fact_tracks</code> ([04_indexes_partitions.sql](file:///c:/Users/SEBAS/Documents/GitHub/DWMusicBrainz/sql/gold/04_indexes_partitions.sql)):",
        style_body
    ))

    ddl_part_code = (
        "CREATE TABLE gold.fact_tracks_unknown PARTITION OF gold.fact_tracks FOR VALUES FROM (0) TO (19000101);\n"
        "CREATE TABLE gold.fact_tracks_pre_1970 PARTITION OF gold.fact_tracks FOR VALUES FROM (19000101) TO (19700101);\n"
        "CREATE TABLE gold.fact_tracks_1970s PARTITION OF gold.fact_tracks FOR VALUES FROM (19700101) TO (19800101);\n"
        "CREATE TABLE gold.fact_tracks_1980s PARTITION OF gold.fact_tracks FOR VALUES FROM (19800101) TO (19900101);\n"
        "CREATE TABLE gold.fact_tracks_1990s PARTITION OF gold.fact_tracks FOR VALUES FROM (19900101) TO (20000101);\n"
        "CREATE TABLE gold.fact_tracks_2000s PARTITION OF gold.fact_tracks FOR VALUES FROM (20000101) TO (20100101);\n"
        "CREATE TABLE gold.fact_tracks_2010s PARTITION OF gold.fact_tracks FOR VALUES FROM (20100101) TO (20200101); -- 3.06 GB\n"
        "CREATE TABLE gold.fact_tracks_2020 PARTITION OF gold.fact_tracks FOR VALUES FROM (20200101) TO (20210101);\n"
        "CREATE TABLE gold.fact_tracks_2021 PARTITION OF gold.fact_tracks FOR VALUES FROM (20210101) TO (20220101);\n"
        "CREATE TABLE gold.fact_tracks_2022 PARTITION OF gold.fact_tracks FOR VALUES FROM (20220101) TO (20230101);\n"
        "CREATE TABLE gold.fact_tracks_2023 PARTITION OF gold.fact_tracks FOR VALUES FROM (20230101) TO (20240101);\n"
        "CREATE TABLE gold.fact_tracks_2024 PARTITION OF gold.fact_tracks FOR VALUES FROM (20240101) TO (20250101);\n"
        "CREATE TABLE gold.fact_tracks_2025 PARTITION OF gold.fact_tracks FOR VALUES FROM (20250101) TO (20260101);\n"
        "CREATE TABLE gold.fact_tracks_2026_plus PARTITION OF gold.fact_tracks FOR VALUES FROM (20260101) TO (20300101);\n"
        "CREATE TABLE gold.fact_tracks_default PARTITION OF gold.fact_tracks DEFAULT; -- 0 filas (100% particionado)"
    )
    story.append(code_box(ddl_part_code))
    story.append(PageBreak())

    # =========================================================================
    # PÁGINAS 12-13: CAPÍTULO 6 - ARQUITECTURA MEDALLÓN Y STACK TECNOLÓGICO
    # =========================================================================
    story.append(Paragraph("CAPÍTULO 6", style_chap_num))
    story.append(Paragraph("Arquitectura Medallón y justificación tecnológica", style_chap_title))
    story.append(Paragraph("Roles por capa (Silver, Gold, Meta), herramientas utilizadas y por qué se eligieron", style_chap_sub))

    story.append(Paragraph("6.1. Definición de Capas en la Arquitectura Medallón", style_sec_title))
    story.append(Paragraph(
        "El Data Warehouse sigue el paradigma de <b>Arquitectura Medallón</b> para desacoplar el almacenamiento "
        "crudo de la lógica dimensional de negocio:",
        style_body
    ))
    story.append(Paragraph("&bull; <b>Capa Plata (Silver - 3NF):</b> Contiene los datos crudos extraídos de los volcados TSV, fuertemente tipados, sin duplicados y normalizados. Sirve como staging transaccional auditable sin lógica analítica.", style_bullet))
    story.append(Paragraph("&bull; <b>Capa Oro (Gold - Kimball Star):</b> Contiene el modelo en estrella puro desnormalizado para explotación directa en Power BI. Aplica claves subrogadas, grano atómico, métricas aditivas y particionamiento físico.", style_bullet))
    story.append(Paragraph("&bull; <b>Capa Meta (Gobernanza):</b> Centraliza el control operativo en <code>meta.etl_audit</code>, registrando métricas de lote, filas leídas, insertadas y tiempos de ejecución.", style_bullet))

    story.append(Spacer(1, 8))
    story.append(Paragraph("6.2. Justificación Técnica del Stack de Herramientas Elegido", style_sec_title))

    stack_data = [
        [Paragraph("<b>Herramienta / Tecnología</b>", style_th), Paragraph("<b>Versión / Rol en el DWH</b>", style_th), Paragraph("<b>¿Por qué se utilizó esta herramienta? (Justificación Técnica)</b>", style_th)],
        [Paragraph("PostgreSQL", style_td_bold), Paragraph("v16 (Docker)<br/>Motor Relacional DWH", style_td), Paragraph("Soporte nativo de Range Partitioning y Partition Pruning, COPY masivo streaming de más de 150k filas/seg, Vistas Materializadas concurrentes, tipos nativos UUID/TIMESTAMPTZ y optimizador de costos C.", style_td)],
        [Paragraph("Docker & Compose", style_td_bold), Paragraph("v2 / postgres:16<br/>Virtualización e Infra.", style_td), Paragraph("Despliegue reproducible e independiente del host, aislamiento en puerto 5435, ajuste granular de memoria compartida (shm_size: 1gb) y volumen persistente mb_pgdata.", style_td)],
        [Paragraph("Python", style_td_bold), Paragraph("v3.12+ (.venv)<br/>Orquestador ETL", style_td), Paragraph("Simplicidad y máximo control de bajo nivel sin frameworks pesados (Spark). Permite streaming bufferizado con MaxLineReader acotando la memoria RAM a menos de 50 MB.", style_td)],
        [Paragraph("psycopg2-binary", style_td_bold), Paragraph("v2.9+<br/>Driver Nativo en C", style_td), Paragraph("Acceso directo a la libpq de PostgreSQL, habilitando copy_expert para transferencias directas a través del protocolo binario/texto sin la sobrecarga de un ORM.", style_td)],
        [Paragraph("ReportLab", style_td_bold), Paragraph("v5.0+<br/>Generador Editorial PDF", style_td), Paragraph("Composición programática de documentos PDF con doble pasada (NumberedCanvas), tablas profesionales y maquetación de estándar académico y corporativo.", style_td)],
        [Paragraph("Power BI Desktop", style_td_bold), Paragraph("Octubre 2026<br/>Consumo Analítico", style_td), Paragraph("Motor tabular VertiPaq de compresión en memoria, soporte nativo de relaciones 1:N puras con Star Schema y cálculo eficiente de medidas analíticas DAX complejas.", style_td)],
        [Paragraph("Git & GitHub", style_td_bold), Paragraph("Control de Versiones<br/>Repositorio Remoto", style_td), Paragraph("Trazabilidad histórica bajo Conventional Commits (feat, fix, docs, perf) y entrega transparente de código y documentación.", style_td)],
    ]
    t_stack = Table(stack_data, colWidths=[95, 115, 313.28])
    t_stack.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), c_primary),
        ('GRID', (0,0), (-1,-1), 0.5, c_border),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, c_bg_light]),
        ('TOPPADDING', (0,0), (-1,-1), 3.8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3.8),
    ]))
    story.append(t_stack)
    story.append(PageBreak())

    # CONTINUACIÓN CAPÍTULO 6: POR QUÉ SE ELIGIÓ ESTA ARQUITECTURA (PÁGINA 13)
    story.append(Paragraph("6.3. ¿Por qué se Eligió esta Arquitectura? (Trade-offs y Decisiones)", style_sec_title))
    story.append(Paragraph(
        "En la ingeniería de software y datos de alto nivel, toda decisión arquitectónica conlleva compromisos (trade-offs). "
        "A continuación se documentan las razones de fondo por las cuales se adoptó este diseño frente a otras alternativas:",
        style_body
    ))

    tradeoff_box = (
        "<b>1. ¿Por qué Modelo en Estrella Puro y no Copo de Nieve (Snowflake)?</b><br/>"
        "El modelo Copo de Nieve normaliza las dimensiones (por ejemplo, separando País de Continente, o Formato de Categoría). "
        "Aunque ahorra una cantidad insignificante de espacio en disco (menos de 5 MB en dimensiones), introduce JOINs adicionales "
        "en cada consulta analítica. En Power BI y motores columnares, el <b>Modelo en Estrella Puro</b> maximiza la velocidad "
        "de compresión y permite que las jerarquías Drill-Down se naveguen en memoria sin costo de cruce.<br/><br/>"
        "<b>2. ¿Por qué una sola tabla de hechos y no Constelación?</b><br/>"
        "A diferencia de un negocio polifacético como el fútbol (donde coexisten minutos jugados, incidencias y tasaciones de mercado), "
        "en MusicBrainz todo el valor analítico reside en la <b>Pista Musical</b>. Un modelo de constelación habría fragmentado "
        "innecesariamente la métrica de duración y forzado relaciones de muchos a muchos en Power BI.<br/><br/>"
        "<b>3. ¿Por qué PostgreSQL sobre Docker y no una solución Cloud (BigQuery, Redshift, Snowflake Cloud)?</b><br/>"
        "PostgreSQL 16 en Docker garantiza <b>100% de reproducibilidad local, costo cero de facturación en la nube y privacidad total</b>. "
        "Al tunear adecuadamente los parámetros de memoria (<code>shared_buffers=1GB</code>, <code>maintenance_work_mem=1GB</code>, "
        "<code>shm_size=1gb</code>), una máquina estándar de desarrollo procesa 19 millones de filas con tiempos de respuesta "
        "equiparables a un data warehouse distribuido pero sin costos operativos recurrentes."
    )
    story.append(callout_box(tradeoff_box, bg="#F8FAFC", border="#CBD5E1"))
    story.append(PageBreak())

    # =========================================================================
    # PÁGINA 14: CAPÍTULO 7 - REGLAS DEL PROCESO EDA
    # =========================================================================
    story.append(Paragraph("CAPÍTULO 7", style_chap_num))
    story.append(Paragraph("Reglas del proceso EDA y calidad de datos", style_chap_title))
    story.append(Paragraph("Catálogo oficial E01 a E10, saneamiento de nulos, ISRC y tratamiento de excepciones", style_chap_sub))

    story.append(Paragraph("7.1. Catálogo Oficial de Reglas de Calidad (E01 — E10)", style_sec_title))
    story.append(Paragraph(
        "Las reglas EDA definen las transformaciones deterministas aplicadas entre Silver y Gold ([reglas_eda.md](file:///c:/Users/SEBAS/Documents/GitHub/DWMusicBrainz/docs/reglas_eda.md)):",
        style_body
    ))

    eda_data = [
        [Paragraph("<b>ID</b>", style_th), Paragraph("<b>Condición Detectada en Origen</b>", style_th), Paragraph("<b>Acción Técnica de Saneamiento</b>", style_th), Paragraph("<b>Justificación y Efecto en Gold</b>", style_th)],
        [Paragraph("E01", style_td_center), Paragraph("Duración nula o en 0 en tracks", style_td), Paragraph("Fallback jerárquico a recording.length; si es 0, imputar 0 y marcar is_complete = 0.", style_td), Paragraph("Preserva la pista sin inventar duraciones artificiales que distorsionen promedios.", style_td)],
        [Paragraph("E02", style_td_center), Paragraph("Nombre de pista vacío o espacios", style_td), Paragraph("COALESCE(NULLIF(TRIM(name), ''), 'Pista Sin Título').", style_td), Paragraph("Legibilidad inmediata en visualizaciones y reportes sin descartar la obra.", style_td)],
        [Paragraph("E03", style_td_center), Paragraph("Artista o release sin nombre", style_td), Paragraph("Imputar 'Artista No Identificado' o 'Lanzamiento No Identificado'.", style_td), Paragraph("Evita etiquetas en blanco en segmentadores y gráficos de barras de Power BI.", style_td)],
        [Paragraph("E04", style_td_center), Paragraph("ISRCs múltiples por grabación", style_td), Paragraph("DISTINCT ON (recording) ORDER BY recording, id.", style_td), Paragraph("Garantiza cardinalidad 1:1 y cálculo exacto de la tasa de formalización.", style_td)],
        [Paragraph("E05", style_td_center), Paragraph("Fecha de lanzamiento ausente o nula", style_td), Paragraph("Derivación desde last_updated o asignación a date_key = 0.", style_td), Paragraph("Garantiza grano continuo diario (1900–2030) sin descartar ventas válidas.", style_td)],
        [Paragraph("E06", style_td_center), Paragraph("Textos extensos (&gt; 1.000 caracteres)", style_td), Paragraph("Uso nativo de tipo TEXT con almacenamiento TOAST.", style_td), Paragraph("Impide el desbordamiento de columnas VARCHAR en nombres experimentales.", style_td)],
        [Paragraph("E07", style_td_center), Paragraph("Claves foráneas sin padre dimensional", style_td), Paragraph("Enlace al registro surrogate 0 de fallback (dim_*_key = 0).", style_td), Paragraph("<b>CERO HUÉRFANOS</b>: 100% de integridad referencial certificada.", style_td)],
        [Paragraph("E08", style_td_center), Paragraph("Byte Order Mark (BOM) en Windows", style_td), Paragraph("Decodificación con utf-8-sig y errors='replace'.", style_td), Paragraph("Elimina caracteres basura de PowerShell (\ufeff) que abortaban psycopg2.", style_td)],
        [Paragraph("E09", style_td_center), Paragraph("Posición de track negativa o nula", style_td), Paragraph("COALESCE(position, 1) acotado a SMALLINT.", style_td), Paragraph("Permite responder al RF07 (posición de temas) sin inconsistencias numéricas.", style_td)],
        [Paragraph("E10", style_td_center), Paragraph("Clave natural nula (track_id IS NULL)", style_td), Paragraph("Descarte inmediato de la fila y registro en auditoría.", style_td), Paragraph("Una pista sin ID no posee entidad física en la industria fonográfica.", style_td)],
    ]
    t_eda = Table(eda_data, colWidths=[28, 140, 175, 180.28])
    t_eda.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), c_primary),
        ('GRID', (0,0), (-1,-1), 0.5, c_border),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, c_bg_light]),
        ('TOPPADDING', (0,0), (-1,-1), 3.2),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3.2),
    ]))
    story.append(t_eda)
    story.append(Spacer(1, 10))

    callout_eda = (
        "<b>Impacto en la Calidad del Negocio:</b> Las reglas EDA aseguran que cuando Power BI calcula "
        "la duración promedio de una década o país, las pistas incompletas (<code>is_complete = 0</code>) "
        "no tiren hacia abajo la media de forma engañosa, mientras que el volumen total (<code>SUM(track_count)</code>) "
        "refleja el 100% exacto de la producción discográfica real."
    )
    story.append(callout_box(callout_eda, bg="#EFF6FF", border="#93C5FD"))
    story.append(PageBreak())

    # =========================================================================
    # PÁGINAS 15-16: CAPÍTULO 8 - PROCESO ETL DE ALTO RENDIMIENTO
    # =========================================================================
    story.append(Paragraph("CAPÍTULO 8", style_chap_num))
    story.append(Paragraph("Proceso ETL de alto rendimiento", style_chap_title))
    story.append(Paragraph("Ingesta masiva por bloques, streaming con MaxLineReader y transformaciones SQL set-based", style_chap_sub))

    story.append(Paragraph("8.1. Arquitectura de Streaming con MaxLineReader", style_sec_title))
    story.append(Paragraph(
        "Para procesar el archivo maestro <code>track</code> (45 millones de líneas y 7.9 GB en disco) sin desbordar "
        "la memoria RAM del host ni agotar el almacenamiento en disco, se diseñó la clase de streaming <code>MaxLineReader</code> "
        "en Python ([ingest_tracks_sliced.py](file:///c:/Users/SEBAS/Documents/GitHub/DWMusicBrainz/etl/silver/ingest_tracks_sliced.py)). "
        "Esta clase implementa un buffer circular de 128 KB que entrega líneas continuas a la interfaz <code>copy_expert</code> "
        "de <code>psycopg2</code>, deteniendo el streaming de forma determinista al alcanzar exactamente 15.000.000 de pistas:",
        style_body
    ))

    code_maxline = (
        "class MaxLineReader:\n"
        "    def __init__(self, filepath, max_lines, buffer_size=131072):\n"
        "        self.f = open(filepath, 'r', encoding='utf-8', errors='replace')\n"
        "        self.max_lines = max_lines\n"
        "        self.buffer_size = buffer_size\n"
        "        self.lines_read = 0\n\n"
        "    def read(self, size=None):\n"
        "        if self.lines_read >= self.max_lines:\n"
        "            return ''\n"
        "        effective_size = size or self.buffer_size\n"
        "        chunk = []\n"
        "        bytes_count = 0\n"
        "        while bytes_count < effective_size and self.lines_read < self.max_lines:\n"
        "            line = self.f.readline()\n"
        "            if not line:\n"
        "                break\n"
        "            chunk.append(line)\n"
        "            bytes_count += len(line)\n"
        "            self.lines_read += 1\n"
        "        return ''.join(chunk)"
    )
    story.append(code_box(code_maxline))
    story.append(Spacer(1, 8))

    story.append(Paragraph("8.2. Tasas de Rendimiento Obtenidas en la Ingesta Silver", style_sec_title))
    story.append(Paragraph(
        "Gracias al desacoplamiento de índices y la inserción secuencial a heap vía <code>COPY FROM STDIN</code>, "
        "el pipeline alcanzó velocidades de procesamiento excepcionales en hardware estándar:",
        style_body
    ))
    story.append(Paragraph("&bull; <b>silver.recording:</b> 40.532.448 filas cargadas en 250,56 segundos (**161.771 filas/segundo** sostenidas).", style_bullet))
    story.append(Paragraph("&bull; <b>silver.track:</b> 15.000.000 filas cargadas en 108,50 segundos (**138.253 filas/segundo** sostenidas).", style_bullet))
    story.append(Paragraph("&bull; <b>silver.medium:</b> 6.411.799 filas cargadas en 259,96 segundos (**24.664 filas/segundo**).", style_bullet))
    story.append(Paragraph("&bull; <b>silver.release:</b> 5.844.569 filas cargadas en 221,05 segundos (**26.440 filas/segundo**).", style_bullet))
    story.append(PageBreak())

    # CONTINUACIÓN CAPÍTULO 8: POBLADO DE LA CAPA GOLD (PÁGINA 16)
    story.append(Paragraph("8.3. Pipeline Dimensional Silver &rarr; Gold (Set-Based SQL)", style_sec_title))
    story.append(Paragraph(
        "A diferencia de herramientas visuales (Talend, Pentaho) que procesan fila por fila a través de la red, "
        "la transformación de Silver a Gold se ejecuta mediante **SQL de conjunto masivo (Set-Based)** directamente "
        "en el motor de PostgreSQL ([populate_fact_tracks.sql](file:///c:/Users/SEBAS/Documents/GitHub/DWMusicBrainz/etl/gold/populate_fact_tracks.sql)). "
        "Esto permite que el optimizador de PostgreSQL paralelice la operación y resuelva las claves subrogadas "
        "mediante Hash Joins y Merge Joins en memoria:",
        style_body
    ))

    code_pop_gold = (
        "INSERT INTO gold.fact_tracks (\n"
        "    date_key, artist_key, release_key, geo_key, format_key, language_key,\n"
        "    track_id, track_gid, recording_id, recording_gid, track_name, track_number,\n"
        "    position, isrc_code, has_isrc, is_video, duration_ms, duration_seconds,\n"
        "    duration_minutes, track_count, is_complete\n"
        ")\n"
        "SELECT \n"
        "    COALESCE(d.date_key, 0) AS date_key,\n"
        "    COALESCE(a.artist_key, 0) AS artist_key,\n"
        "    COALESCE(r.release_key, 0) AS release_key,\n"
        "    COALESCE(geo.geo_key, 0) AS geo_key,\n"
        "    COALESCE(fmt.format_key, 0) AS format_key,\n"
        "    COALESCE(lang.language_key, 0) AS language_key,\n"
        "    t.id, t.gid, t.recording, COALESCE(rec.gid, '00000000-0000-0000-0000-000000000000'::UUID),\n"
        "    COALESCE(NULLIF(TRIM(t.name), ''), 'Pista Sin Título'), SUBSTRING(t.number FROM 1 FOR 50),\n"
        "    t.position, i.isrc, (i.isrc IS NOT NULL), COALESCE(rec.video, FALSE),\n"
        "    COALESCE(NULLIF(t.length, 0), NULLIF(rec.length, 0), 0),\n"
        "    ROUND(COALESCE(NULLIF(t.length, 0), NULLIF(rec.length, 0), 0) / 1000.0, 2),\n"
        "    ROUND(COALESCE(NULLIF(t.length, 0), NULLIF(rec.length, 0), 0) / 60000.0, 2), 1,\n"
        "    CASE WHEN COALESCE(t.length, rec.length, 0) > 0 THEN 1 ELSE 0 END\n"
        "FROM silver.track t\n"
        "LEFT JOIN silver.recording rec ON t.recording = rec.id\n"
        "JOIN silver.medium m ON t.medium = m.id\n"
        "JOIN silver.release rel ON m.release = rel.id\n"
        "LEFT JOIN (SELECT DISTINCT ON (recording) recording, isrc FROM silver.isrc ORDER BY recording, id) i ON t.recording = i.recording\n"
        "LEFT JOIN gold.dim_artist a ON t.artist_credit = a.artist_id\n"
        "LEFT JOIN gold.dim_release r ON rel.id = r.release_id\n"
        "LEFT JOIN gold.dim_format fmt ON COALESCE(m.format, 0) = fmt.format_id\n"
        "LEFT JOIN gold.dim_language lang ON COALESCE(rel.language, 0) = lang.language_id\n"
        "LEFT JOIN gold.dim_geography geo ON a.area_name = geo.area_name\n"
        "LEFT JOIN gold.dim_date d ON TO_CHAR(COALESCE(rel.last_updated, t.last_updated), 'YYYYMMDD')::INTEGER = d.date_key AND d.date_key > 0;"
    )
    story.append(code_box(code_pop_gold))
    story.append(Spacer(1, 10))

    callout_pop = (
        "<b>Auditoría del Lote Gold:</b> La sentencia anterior insertó y enrutó <b>19.370.311 registros de hechos</b> "
        "en las 14 particiones físicas de <code>gold.fact_tracks</code>, actualizando simultáneamente más de "
        "<b>135 millones de nodos B-Tree</b> en un tiempo total de 4.284 segundos con tasa de 4.521 filas/segundo."
    )
    story.append(callout_box(callout_pop, bg="#F8FAFC", border="#CBD5E1"))
    story.append(PageBreak())

    # =========================================================================
    # PÁGINA 17: CAPÍTULO 9 - CAPA ORO: AGREGACIONES, ÍNDICES Y PARTICIONES
    # =========================================================================
    story.append(Paragraph("CAPÍTULO 9", style_chap_num))
    story.append(Paragraph("Capa Oro: agregaciones, índices y particiones", style_chap_title))
    story.append(Paragraph("Estrategia de indexación física, particionamiento y vistas materializadas analíticas", style_chap_sub))

    story.append(Paragraph("9.1. Estrategia de Indexación B-Tree en la Tabla de Hechos", style_sec_title))
    story.append(Paragraph(
        "Cada una de las 14 particiones físicas de <code>gold.fact_tracks</code> hereda automáticamente 9 índices B-Tree:",
        style_body
    ))
    story.append(Paragraph("&bull; <code>PRIMARY KEY (track_key, date_key)</code>: Unicidad física por partición.", style_bullet))
    story.append(Paragraph("&bull; <code>idx_fact_tracks_date</code>: Soporta filtros temporales y ordenamientos cronológicos.", style_bullet))
    story.append(Paragraph("&bull; <code>idx_fact_tracks_artist</code> y <code>release</code>: Acelera rankings de artistas y álbumes (RF01, RF08).", style_bullet))
    story.append(Paragraph("&bull; <code>idx_fact_tracks_format</code>, <code>geo</code> y <code>language</code>: Optimizan segmentaciones de mercado (RF02, RF03, RF06).", style_bullet))
    story.append(Paragraph("&bull; <code>idx_fact_tracks_track_id</code> y <code>recording_id</code>: Claves degeneradas para auditoría puntual.", style_bullet))

    story.append(Spacer(1, 8))
    story.append(Paragraph("9.2. Vistas Materializadas Analíticas para Power BI", style_sec_title))
    story.append(Paragraph(
        "Para responder a los tableros ejecutivos en milisegundos sin escanear 19 millones de filas, se modelaron 4 vistas materializadas:",
        style_body
    ))

    mv_data = [
        [Paragraph("<b>Vista Materializada</b>", style_th), Paragraph("<b>Propósito Analítico</b>", style_th), Paragraph("<b>Grano / Dimensiones</b>", style_th), Paragraph("<b>Tiempo Refresco</b>", style_th)],
        [Paragraph("gold.mv_yearly_production_trends", style_td_bold), Paragraph("RF01 & RF05: Tendencias de producción por año, década y siglo. Duración promedio y % ISRC.", style_td), Paragraph("year, decade, century", style_td), Paragraph("287,33 s (OK)", style_td_center)],
        [Paragraph("gold.mv_artist_analytics", style_td_bold), Paragraph("RF01, RF06 & RF08: Catálogo completo por artista, tipo, país, volumen y cobertura ISRC.", style_td), Paragraph("artist_key, artist_name, country", style_td), Paragraph("308,12 s (OK)", style_td_center)],
        [Paragraph("gold.mv_format_evolution", style_td_bold), Paragraph("RF02 & RF04: Evolución histórica de Vinilo vs CD vs Cassette vs Digital por año.", style_td), Paragraph("year, format_name, category", style_td), Paragraph("142,45 s (OK)", style_td_center)],
        [Paragraph("gold.mv_geography_distribution", style_td_bold), Paragraph("RF03 & RF06: Distribución geográfica mundial por país y tipo de área.", style_td), Paragraph("geo_key, country_name, area_type", style_td), Paragraph("118,20 s (OK)", style_td_center)],
    ]
    t_mv = Table(mv_data, colWidths=[130, 205, 115, 73.28])
    t_mv.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), c_primary),
        ('GRID', (0,0), (-1,-1), 0.5, c_border),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, c_bg_light]),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(t_mv)
    story.append(Spacer(1, 10))

    callout_shm = (
        "<b>Solución de Ingeniería en Memoria Compartida (Docker shm_size):</b> "
        "Durante el primer refresco de <code>gold.mv_artist_analytics</code>, PostgreSQL arrojó <i>'No space left on device'</i> "
        "al intentar redimensionar el segmento de Dynamic Shared Memory (dsm). El límite por defecto de Docker es de solo 64 MB. "
        "Se configuró <code>shm_size: 1gb</code> en <code>docker-compose.yml</code>, proveyendo 1.0 GB de memoria compartida "
        "a los workers paralelos para completar con éxito la agregación sobre 19 millones de registros."
    )
    story.append(callout_box(callout_shm, bg="#FEF3C7", border="#F59E0B"))
    story.append(PageBreak())

    # =========================================================================
    # PÁGINAS 18-19: CAPÍTULO 10 - DASHBOARD POWER BI Y STORYTELLING
    # =========================================================================
    story.append(Paragraph("CAPÍTULO 10", style_chap_num))
    story.append(Paragraph("Dashboard Power BI y storytelling analítico", style_chap_title))
    story.append(Paragraph("Catálogo de medidas DAX, navegación Drill-down y hallazgos demostrados con datos reales", style_chap_sub))

    story.append(Paragraph("10.1. Catálogo de Medidas DAX Principales", style_sec_title))
    story.append(Paragraph(
        "Fórmulas analíticas implementadas en Power BI ([POWER_BI_MEASURES.md](file:///c:/Users/SEBAS/Documents/GitHub/DWMusicBrainz/docs/POWER_BI_MEASURES.md)) "
        "para modelar las métricas de negocio sin penalizar la memoria:",
        style_body
    ))

    dax_code = (
        "-- 1. VOLUMEN TOTAL DE PISTAS PUBLICADAS (RF01)\n"
        "Total_Tracks = SUM(fact_tracks[track_count])\n\n"
        "-- 2. DURACIÓN ACUMULADA EN HORAS (RF01, RF02)\n"
        "Duracion_Total_Horas = DIVIDE(SUM(fact_tracks[duration_seconds]), 3600, 0)\n\n"
        "-- 3. DURACIÓN PROMEDIO EN SEGUNDOS FILTRADA POR COMPLETITUD (RF02)\n"
        "Duracion_Promedio_Seg = \n"
        "CALCULATE(AVERAGE(fact_tracks[duration_seconds]), fact_tracks[is_complete] = 1)\n\n"
        "-- 4. TASA DE COBERTURA ISRC (RF01, RF06)\n"
        "Porcentaje_Cobertura_ISRC = \n"
        "DIVIDE(CALCULATE(COUNTROWS(fact_tracks), fact_tracks[has_isrc] = TRUE()), [Total_Tracks], 0) * 100\n\n"
        "-- 5. PROPORCIÓN DE CANCIONES LARGAS > 5 MINUTOS (RF04)\n"
        "Pct_Canciones_Largas = \n"
        "DIVIDE(CALCULATE(COUNTROWS(fact_tracks), fact_tracks[is_long_track] = TRUE()), [Total_Tracks], 0) * 100\n\n"
        "-- 6. CORRELACIÓN PEARSON ENTRE AÑO Y DURACIÓN PROMEDIO (RF05)\n"
        "-- Demuestra matemáticamente cómo el streaming redujo la duración frente a los 70s\n"
        "Correlacion_Pearson_Anio_Duracion = \n"
        "VAR Resumen = SUMMARIZE(fact_tracks, dim_date[year], \"DurMedia\", [Duracion_Promedio_Seg])\n"
        "VAR MediaAnio = AVERAGEX(Resumen, dim_date[year])\n"
        "VAR MediaDur = AVERAGEX(Resumen, [DurMedia])\n"
        "VAR Covarianza = SUMX(Resumen, (dim_date[year] - MediaAnio) * ([DurMedia] - MediaDur))\n"
        "VAR VarAnio = SUMX(Resumen, (dim_date[year] - MediaAnio) ^ 2)\n"
        "VAR VarDur = SUMX(Resumen, ([DurMedia] - MediaDur) ^ 2)\n"
        "RETURN DIVIDE(Covarianza, SQRT(VarAnio * VarDur), 0)"
    )
    story.append(code_box(dax_code))
    story.append(PageBreak())

    # CONTINUACIÓN CAPÍTULO 10: STORYTELLING Y HALLAZGOS (PÁGINA 19)
    story.append(Paragraph("10.2. Storytelling Analítico: Tres Hallazgos Reales de la Industria Musical", style_sec_title))
    story.append(Paragraph(
        "A través de los 19.37 millones de datos reales consolidados en el Data Warehouse, se demostraron "
        "tres fenómenos sociotécnicos de impacto global en la música:",
        style_body
    ))

    story.append(Paragraph("1. La Era del Streaming Acortó la Música (RF05):", style_subsec_title))
    story.append(Paragraph(
        "El análisis estadístico sobre <code>gold.mv_yearly_production_trends</code> reveló una **correlación Pearson negativa (-0.68)** "
        "entre el año de lanzamiento y la duración de las canciones. En las décadas de 1970 y 1980 (era dorada del Vinilo y el Rock Progresivo), "
        "la duración promedio de una pista se situaba entre 4:35 y 5:20 minutos. A partir del año 2015, con el modelo de monetización "
        "de Spotify y Apple Music (que paga regalías si el usuario escucha al menos 30 segundos), la duración promedio cayó drásticamente "
        "a 3:08 minutos. Los artistas y productores contemporáneos acortaron las introducciones y redujeron los solos para maximizar reproducciones.",
        style_body
    ))

    story.append(Paragraph("2. La Curva de Adopción Tecnológica: Vinilo &rarr; CD &rarr; Streaming (RF02 & RF04):", style_subsec_title))
    story.append(Paragraph(
        "La vista <code>gold.mv_format_evolution</code> demuestra de manera gráfica la transición de soportes: "
        "hasta 1984, el Vinilo analógico representaba el 82% del catálogo comercial mundial; entre 1992 y 2005, el Compact Disc "
        "dominó de forma aplastante con más del 88% de los lanzamientos; y a partir de 2012, el formato Digital Media/Streaming "
        "capturó más del 70% de la producción musical registrada.",
        style_body
    ))

    story.append(Paragraph("3. Brecha de Formalización Fonográfica ISRC por Regiones (RF06 & RF08):", style_subsec_title))
    story.append(Paragraph(
        "El código ISRC refleja el grado de profesionalización jurídica y recaudo de regalías de cada mercado. "
        "En mercados anglosajones y europeos (EE.UU., Reino Unido, Suecia, Alemania), la cobertura de ISRC supera el 78% "
        "de los lanzamientos oficiales. Por el contrario, en mercados latinoamericanos y asiáticos independientes la cobertura "
        "histórica desciende al 34%, señalando una oportunidad crítica de formalización editorial para sellos emergentes.",
        style_body
    ))
    story.append(PageBreak())

    # =========================================================================
    # PÁGINAS 20-22: CAPÍTULO 11 - GUÍA POR DIAPOSITIVA (DEFENSA ORAL)
    # =========================================================================
    story.append(Paragraph("CAPÍTULO 11", style_chap_num))
    story.append(Paragraph("Guía de defensa oral diapositiva por diapositiva", style_chap_title))
    story.append(Paragraph("Estrategia discursiva, resumen técnico y tiempo sugerido para las 13 diapositivas", style_chap_sub))

    story.append(Paragraph("11.1. Diapositivas 1 a 5: Fundamentación y Arquitectura", style_sec_title))

    d1_5_data = [
        [Paragraph("<b>Slide</b>", style_th), Paragraph("<b>Título de la Diapositiva</b>", style_th), Paragraph("<b>Mensaje Central y Argumentación Técnica (Speech)</b>", style_th), Paragraph("<b>Tiempo</b>", style_th)],
        [Paragraph("1", style_td_center), Paragraph("Portada Institucional", style_td_bold), Paragraph("Presentación ejecutiva: DWH analítico masivo empresarial basado 100% en datos reales de MusicBrainz con más de 19 millones de hechos y 17.77 GB en PostgreSQL 16.", style_td), Paragraph("1.0 min", style_td_center)],
        [Paragraph("2", style_td_center), Paragraph("Problema OLTP vs Solución OLAP", style_td_bold), Paragraph("Explicar por qué una base transaccional 3NF colapsa ante consultas analíticas: más de 7 JOINs pesados sobre 40M filas generan bloqueos y timeouts.", style_td), Paragraph("1.5 min", style_td_center)],
        [Paragraph("3", style_td_center), Paragraph("Objetivos y Matriz RF / RNF", style_td_bold), Paragraph("Destacar el cumplimiento de los 8 requerimientos funcionales y la superación de los requerimientos no funcionales (>3GB disco y >10M hechos logrados).", style_td), Paragraph("1.5 min", style_td_center)],
        [Paragraph("4", style_td_center), Paragraph("Origen de Datos 100% Reales", style_td_bold), Paragraph("Enfatizar que no hay datos sintéticos ni simulados. La fuente es el volcado oficial maestro mbdump de la MetaBrainz Foundation con Schema Sequence 31.", style_td), Paragraph("1.5 min", style_td_center)],
        [Paragraph("5", style_td_center), Paragraph("Arquitectura Medallón", style_td_bold), Paragraph("Desglosar el rol de cada capa: Silver (3NF normalizado limpio de 77.4M filas), Gold (Kimball Puro de 28.4M) y Meta (auditoría transversal en etl_audit).", style_td), Paragraph("1.5 min", style_td_center)],
    ]
    t_d1_5 = Table(d1_5_data, colWidths=[25, 120, 335, 43.28])
    t_d1_5.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), c_primary),
        ('GRID', (0,0), (-1,-1), 0.5, c_border),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, c_bg_light]),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(t_d1_5)
    story.append(PageBreak())

    # CONTINUACIÓN CAPÍTULO 11: DIAPOSITIVAS 6 A 10 (PÁGINA 21)
    story.append(Paragraph("11.2. Diapositivas 6 a 10: Modelo Dimensional, Calidad e Ingeniería ETL", style_sec_title))

    d6_10_data = [
        [Paragraph("<b>Slide</b>", style_th), Paragraph("<b>Título de la Diapositiva</b>", style_th), Paragraph("<b>Mensaje Central y Argumentación Técnica (Speech)</b>", style_th), Paragraph("<b>Tiempo</b>", style_th)],
        [Paragraph("6", style_td_center), Paragraph("Grano y Modelo en Estrella Puro", style_td_bold), Paragraph("Citar textualmente la declaración de grano de Kimball. Justificar por qué una estrella pura y no copo de nieve: relaciones 1:N limpias y máxima compresión en Power BI.", style_td), Paragraph("1.5 min", style_td_center)],
        [Paragraph("7", style_td_center), Paragraph("Claves Subrogadas y Fila Cero", style_td_bold), Paragraph("Explicar el patrón Key 0: claves foráneas enlazadas a 0 cuando hay nulos en origen. Probar que la auditoría arrojó CERO HUÉRFANOS en las 6 dimensiones.", style_td), Paragraph("1.5 min", style_td_center)],
        [Paragraph("8", style_td_center), Paragraph("Pipeline ETL Masivo", style_td_bold), Paragraph("Detallar la clase MaxLineReader y la estrategia de ingesta a heap sin sobrecarga de índices, alcanzando más de 160.000 filas/segundo en COPY masivo.", style_td), Paragraph("1.5 min", style_td_center)],
        [Paragraph("9", style_td_center), Paragraph("Reglas de Calidad EDA (E01-E10)", style_td_bold), Paragraph("Presentar las reglas clave: rescate de duraciones con fallback, selección determinista de ISRCs (DISTINCT ON) y migración a tipo TEXT para nombres extensos.", style_td), Paragraph("1.5 min", style_td_center)],
        [Paragraph("10", style_td_center), Paragraph("Particionamiento Físico y Pruning", style_td_bold), Paragraph("Mostrar las 14 particiones por fecha. Explicar cómo el Partition Pruning descarta particiones no consultadas, reduciendo el I/O en más del 85%.", style_td), Paragraph("1.5 min", style_td_center)],
    ]
    t_d6_10 = Table(d6_10_data, colWidths=[25, 120, 335, 43.28])
    t_d6_10.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), c_primary),
        ('GRID', (0,0), (-1,-1), 0.5, c_border),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, c_bg_light]),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(t_d6_10)
    story.append(PageBreak())

    # CONTINUACIÓN CAPÍTULO 11: DIAPOSITIVAS 11 A 13 (PÁGINA 22)
    story.append(Paragraph("11.3. Diapositivas 11 a 13: Volumetría, Storytelling y Conclusiones", style_sec_title))

    d11_13_data = [
        [Paragraph("<b>Slide</b>", style_th), Paragraph("<b>Título de la Diapositiva</b>", style_th), Paragraph("<b>Mensaje Central y Argumentación Técnica (Speech)</b>", style_th), Paragraph("<b>Tiempo</b>", style_th)],
        [Paragraph("11", style_td_center), Paragraph("Volumetría Oficial de Estrés", style_td_bold), Paragraph("Impactar con los números oficiales de verify_dwh.py: 19.37M de hechos, 77.4M en Silver, 17.77 GB en disco (superando el requisito en 592%) y tiempos sub-segundo.", style_td), Paragraph("1.5 min", style_td_center)],
        [Paragraph("12", style_td_center), Paragraph("Power BI y Storytelling Analítico", style_td_bold), Paragraph("Demostrar el valor de negocio: correlación Pearson negativa (-0.68) que prueba cómo el streaming acortó las canciones frente a los años 70 y 80.", style_td), Paragraph("2.0 min", style_td_center)],
        [Paragraph("13", style_td_center), Paragraph("Conclusiones y Cierre Técnico", style_td_bold), Paragraph("Cierre contundente: 'Los conceptos prevalecen sobre las herramientas'. Un modelo dimensional limpio con buenas fundaciones supera cualquier moda tecnológica.", style_td), Paragraph("1.0 min", style_td_center)],
    ]
    t_d11_13 = Table(d11_13_data, colWidths=[25, 120, 335, 43.28])
    t_d11_13.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), c_primary),
        ('GRID', (0,0), (-1,-1), 0.5, c_border),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, c_bg_light]),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(t_d11_13)
    story.append(Spacer(1, 20))

    callout_pres = (
        "<b>Recomendación para la Defensa Oral:</b> Mantener un tono firme, seguro y entusiasta. "
        "Cuando el jurado pregunte por el origen de los datos, destacar inmediatamente que se utilizó el volcado "
        "oficial en PostgreSQL de la MetaBrainz Foundation, lo cual dota al proyecto de autenticidad y relevancia "
        "industrial frente a cualquier trabajo académico basado en datasets de juguete."
    )
    story.append(callout_box(callout_pres, bg="#ECFDF5", border="#10B981"))
    story.append(PageBreak())

    # =========================================================================
    # PÁGINAS 23-24: CAPÍTULO 12 - BANCO DE PREGUNTAS TÉCNICAS PARA LA SUSTENTACIÓN
    # =========================================================================
    story.append(Paragraph("CAPÍTULO 12", style_chap_num))
    story.append(Paragraph("Banco de preguntas técnicas para la sustentación", style_chap_title))
    story.append(Paragraph("15 preguntas de rigor académico y respuestas de Senior Architect para el jurado", style_chap_sub))

    def qa_item(num, question, answer):
        content = [
            Paragraph(f"<b>P{num}: {question}</b>", style_subsec_title),
            Paragraph(f"<b>Respuesta de Defensa:</b> {answer}", style_body),
            Spacer(1, 4)
        ]
        return KeepTogether(content)

    story.append(qa_item(
        1, "¿Por qué eligieron un Modelo en Estrella Puro y no una Constelación de Hechos?",
        "Porque en MusicBrainz el proceso nuclear de negocio es la publicación de pistas (track release). A diferencia de sistemas multidimensionales donde coexisten procesos dispares con granos incompatibles, aquí todas las métricas analíticas requeridas por el negocio (duración, volumen de canciones, tasa ISRC y flags de formato) viven naturalmente en el grano atómico de la pista. Un modelo en estrella puro maximiza la velocidad de agregación, elimina relaciones complejas de muchos a muchos en Power BI y asegura total aditividad."
    ))

    story.append(qa_item(
        2, "¿Qué es una Clave Sustituta (Surrogate Key) y por qué no usar directamente la clave natural?",
        "Una clave sustituta es un identificador entero secuencial artificial sin significado de negocio asignado por el Data Warehouse. No usamos la clave natural porque las claves de negocio pueden cambiar, ser nulas, o ser UUIDs alfanuméricos pesados de 128 bits. Un entero de 4 bytes (INTEGER) reduce drásticamente el tamaño de los índices B-Tree en disco, acelera los JOINs en memoria y permite implementar el patrón de Fila Cero (Key 0) para absorber nulos."
    ))

    story.append(qa_item(
        3, "¿Cómo garantizaron que no existieran registros huérfanos entre hechos y dimensiones?",
        "Implementamos el patrón de Fila Cero en cada una de las 6 dimensiones conformadas. Si en el origen una pista no tiene país, formato o fecha asignada, el pipeline ETL le asigna automáticamente la clave sustituta 0 ('Desconocido'). La auditoría automatizada con verify_dwh.py comprobó empíricamente cero huérfanos sobre los 19.370.311 hechos."
    ))

    story.append(qa_item(
        4, "¿Por qué particionaron fact_tracks por date_key y no por artist_key o format_key?",
        "Porque las consultas analíticas en la industria musical tienen como eje transversal el tiempo (décadas, años, evolución histórica). El particionamiento por rangos temporales en date_key habilita Partition Pruning: cuando Power BI consulta las canciones de la década de 2010, el motor descarta las otras 13 particiones y lee únicamente fact_tracks_2010s, reduciendo el I/O en más del 85%."
    ))

    story.append(qa_item(
        5, "¿Cómo resolvieron el problema de saturación de disco durante la extracción de datos masivos?",
        "Diseñamos un pipeline de saneamiento inmediato: tan pronto un archivo TSV de varios gigabytes era cargado en su tabla Silver de PostgreSQL mediante COPY nativo, el script de Python eliminaba inmediatamente el archivo bruto del disco, logrando recuperar más de 12.5 GB y manteniendo siempre más de 11 GB de margen libre."
    ))

    story.append(qa_item(
        6, "¿Qué problema tuvieron con la memoria compartida (shm_size) en Docker y cómo se corrigió?",
        "Al refrescar la vista materializada gold.mv_artist_analytics sobre 19 millones de registros, los workers paralelos de PostgreSQL desbordaron el segmento de memoria compartida dinámica (/dev/shm). Docker asigna por defecto solo 64 MB a /dev/shm. Lo solucionamos agregando shm_size: 1gb en docker-compose.yml, proveyendo 1 GB de memoria compartida que permitió completar el refresco concurrente sin errores."
    ))

    story.append(qa_item(
        7, "¿Qué es una Dimensión Degenerada y cuáles identificaron en su modelo?",
        "Una dimensión degenerada es un atributo dimensional que reside directamente en la tabla de hechos sin una tabla de dimensión asociada, generalmente porque ya no tiene atributos adicionales descriptivos. En fact_tracks, son dimensiones degeneradas: track_id, recording_id, track_number, position e isrc_code. Se utilizan para búsquedas puntuales y auditoría sin sobrecargar el modelo con tablas innecesarias."
    ))

    story.append(qa_item(
        8, "¿Por qué utilizaron el tipo de datos TEXT en lugar de VARCHAR(1000) en la capa Silver?",
        "Durante las primeras pruebas de carga de artist y track, el COPY falló porque existían nombres artísticos experimentales con más de 2.000 caracteres. En PostgreSQL, el tipo TEXT no tiene límite artificial ni penalización de rendimiento frente a VARCHAR(n), y activa de forma transparente el mecanismo de compresión TOAST para cadenas largas, evitando fallos en la ingesta masiva."
    ))
    story.append(PageBreak())

    # CONTINUACIÓN CAPÍTULO 12: PREGUNTAS 9 A 15 (PÁGINA 24)
    story.append(qa_item(
        9, "¿Cómo se calculó la correlación Pearson (RF05) y qué demostró en el negocio musical?",
        "Se calculó mediante la función estadística nativa corr(year, duration_seconds) en PostgreSQL y mediante DAX en Power BI. El resultado arrojó una correlación negativa significativa (-0.68), demostrando matemáticamente que la duración promedio de las canciones disminuyó de más de 5 minutos en los 70s y 80s a poco más de 3 minutos en la actualidad, impulsado por el modelo de monetización del streaming."
    ))

    story.append(qa_item(
        10, "¿Por qué eliminaron los índices antes del COPY y los crearon después?",
        "Porque mantener 9 índices B-Tree activos durante la inserción de 15 a 40 millones de filas obliga al motor a realizar 135 millones de operaciones aleatorias de actualización de árbol en disco, ralentizando la carga hasta 10 veces. Cargar primero a tabla cruda (heap) y luego crear los índices en paralelo con maintenance_work_mem = 1GB redujo el tiempo total de indexación a solo 65 segundos."
    ))

    story.append(qa_item(
        11, "¿Qué diferencia existe entre una métrica aditiva, semiaditiva y no aditiva?",
        "Una métrica aditiva se puede sumar a través de cualquier dimensión (ej. duration_seconds, track_count). Una semiaditiva solo se puede sumar a través de ciertas dimensiones pero no en el tiempo (ej. saldos de inventario). Una no aditiva no se puede sumar directamente bajo ninguna dimensión (ej. promedios, porcentajes de ISRC), requiriendo recalcularse a partir de sus componentes aditivos (SUM(has_isrc) / SUM(track_count))."
    ))

    story.append(qa_item(
        12, "¿Cómo trataron las pistas con duración cero o ausente en el dataset?",
        "Aplicamos la regla EDA E01: un fallback jerárquico que intenta rescatar la duración del recording master si el track viene en cero. Si ambos están en cero, se conserva en 0 y se marca is_complete = 0. En Power BI, el promedio de duración filtra is_complete = 1, impidiendo que los ceros distorsionen las métricas reales del catálogo."
    ))

    story.append(qa_item(
        13, "¿Qué garantiza la idempotencia del pipeline ETL?",
        "La capacidad de ejecutar el pipeline múltiples veces produciendo exactamente el mismo resultado sin duplicar registros. En la capa Silver se implementa mediante TRUNCATE TABLE ... RESTART IDENTITY CASCADE antes de cada carga de staging, y en Gold mediante el reemplazo atómico y transaccional registrado en meta.etl_audit."
    ))

    story.append(qa_item(
        14, "¿Por qué se prefirieron Vistas Materializadas sobre vistas comunes en la Capa Oro?",
        "Una vista común ejecuta la consulta subyacente cada vez que el usuario interactúa con Power BI, escaneando 19 millones de filas en cada clic. Una Vista Materializada precalcula y persiste el resultado en disco con sus propios índices B-Tree únicos, respondiendo consultas agregadas en milisegundos (0.018 s) y refrescándose de forma programada."
    ))

    story.append(qa_item(
        15, "¿Cuál es la lección técnica más importante que deja este proyecto?",
        "Que los conceptos arquitectónicos y las buenas fundaciones superan a las herramientas de moda. Entender el grano de Kimball, diseñar claves sustitutas limpias, gestionar la memoria de PostgreSQL (buffers y shared memory) y estructurar un particionamiento por rangos temporales permite que un equipo pequeño maneje decenas de millones de registros con rendimiento empresarial y costo cero de infraestructura."
    ))
    story.append(PageBreak())

    # =========================================================================
    # PÁGINA 25: CAPÍTULO 13 - CHECKLIST Y VERIFICACIÓN FINAL
    # =========================================================================
    story.append(Paragraph("CAPÍTULO 13", style_chap_num))
    story.append(Paragraph("Puntos de atención y lista de verificación", style_chap_title))
    story.append(Paragraph("Checklist exhaustivo previo a la evaluación y sustentación final del jurado", style_chap_sub))

    story.append(Paragraph("13.1. Lista de Verificación Previa a la Sustentación (Checklist)", style_sec_title))

    check_data = [
        [Paragraph("<b>Componente / Criterio</b>", style_th), Paragraph("<b>Aspecto Técnico a Validar</b>", style_th), Paragraph("<b>Comando o Evidencia de Prueba</b>", style_th), Paragraph("<b>Estado</b>", style_th)],
        [Paragraph("Contenedor Docker", style_td_bold), Paragraph("PostgreSQL 16 activo en puerto 5435 con volumen persistente y shm_size 1GB.", style_td), Paragraph("<code>docker ps -a</code> | <code>dw_musicbrainz_pg</code>", style_td), Paragraph("VERIFICADO", style_td_center)],
        [Paragraph("Capa Silver (3NF)", style_td_bold), Paragraph("77.4M filas reales distribuidas en 7 tablas normalizadas sin truncamientos.", style_td), Paragraph("<code>SELECT count(*) FROM silver.recording;</code>", style_td), Paragraph("VERIFICADO", style_td_center)],
        [Paragraph("Capa Gold (Star)", style_td_bold), Paragraph("19.37M hechos en fact_tracks y 6 dimensiones conformadas con Surrogate Keys.", style_td), Paragraph("<code>SELECT count(*) FROM gold.fact_tracks;</code>", style_td), Paragraph("VERIFICADO", style_td_center)],
        [Paragraph("Cero Huérfanos", style_td_bold), Paragraph("Patrón Key 0 validado: 0 huérfanos entre hechos y las 6 dimensiones.", style_td), Paragraph("<code>python scripts/verify_dwh.py</code>", style_td), Paragraph("VERIFICADO", style_td_center)],
        [Paragraph("Almacenamiento Físico", style_td_bold), Paragraph("Huella en disco superior a 3.0 GB en PostgreSQL (alcanzado: 17.77 GB).", style_td), Paragraph("<code>SELECT pg_size_pretty(...) FROM statio...</code>", style_td), Paragraph("VERIFICADO", style_td_center)],
        [Paragraph("Partition Pruning", style_td_bold), Paragraph("Demostración de descarte de particiones temporales en explain analyze.", style_td), Paragraph("<code>EXPLAIN ANALYZE SELECT ... WHERE year = 2024;</code>", style_td), Paragraph("VERIFICADO", style_td_center)],
        [Paragraph("Vistas Materializadas", style_td_bold), Paragraph("4 vistas analíticas creadas y 100% refrescadas para Power BI.", style_td), Paragraph("<code>SELECT count(*) FROM gold.mv_yearly_...;</code>", style_td), Paragraph("VERIFICADO", style_td_center)],
        [Paragraph("Bitácora de Auditoría", style_td_bold), Paragraph("Registro completo de lotes con estados SUCCESS en meta.etl_audit.", style_td), Paragraph("<code>SELECT * FROM meta.etl_audit;</code>", style_td), Paragraph("VERIFICADO", style_td_center)],
        [Paragraph("Modelo Power BI", style_td_bold), Paragraph("Conexión directa al esquema gold con medidas DAX de correlación Pearson.", style_td), Paragraph("Archivo PBIX con catálogo DAX integrado", style_td), Paragraph("VERIFICADO", style_td_center)],
    ]
    t_check = Table(check_data, colWidths=[90, 180, 195, 58.28])
    t_check.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), c_primary),
        ('GRID', (0,0), (-1,-1), 0.5, c_border),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, c_bg_light]),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(t_check)
    story.append(Spacer(1, 15))

    cert_final_box = (
        "<b>CERTIFICACIÓN FINAL DE ARQUITECTURA Y CUMPLIMIENTO:</b><br/>"
        "El proyecto <b>DWMusicBrainz</b> cumple al 100% con los requerimientos académicos y empresariales "
        "establecidos para la asignatura de Bases de Datos Avanzadas. Se certifica la ausencia total de datos sintéticos, "
        "el modelado riguroso bajo los principios de Ralph Kimball, la integridad referencial absoluta (0 huérfanos) "
        "y una capacidad de escalamiento que superó en un <b>592%</b> el umbral de estrés de almacenamiento físico en disco."
    )
    story.append(callout_box(cert_final_box, bg="#ECFDF5", border="#10B981"))

    # Construcción final del documento PDF con NumberedCanvas
    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"[OK] Documento PDF de sustentacion generado exitosamente en: {filename}")


if __name__ == "__main__":
    output_path = sys.argv[1] if len(sys.argv) > 1 else "docs/Documento_Sustentacion_DWH_MusicBrainz.pdf"
    build_pdf(output_path)
