/*
 * build_sustentacion_v4.js
 * ========================
 * Genera docs/DWMusicBrainz_Sustentacion_v4.pptx a partir de
 * docs/build/metricas_databricks.json.
 *
 * Dependencias npm: pptxgenjs, react, react-dom, react-icons, sharp.
 * Uso:
 *     node scripts/build_sustentacion_v4.js [ruta_salida.pptx]
 * Opcional: PPTX_APPLY_THEME con la ruta de apply_theme.js para escribir el tema.
 */
const fs = require("fs");
const path = require("path");
const pptxgen = require("pptxgenjs");
const React = require("react");
const ReactDOMServer = require("react-dom/server");
const sharp = require("sharp");
const fa = require("react-icons/fa");

const BASE = path.resolve(__dirname, "..");
const BUILD = path.join(BASE, "docs", "build");
const SALIDA = process.argv[2] || path.join(BASE, "docs", "DWMusicBrainz_Sustentacion_v4.pptx");
const m = JSON.parse(fs.readFileSync(path.join(BUILD, "metricas_databricks.json"), "utf8"));

// Los pastel viven en el tema para poder cambiarlos en un solo lugar desde PowerPoint.
const THEME = {
  name: "DWMusicBrainz Pastel",
  headFontFace: "Cambria",
  bodyFontFace: "Calibri",
  colors: {
    dk1: "23324A", lt1: "FFFFFF", dk2: "56647A", lt2: "F3F6FB",
    accent1: "DCE9F8", accent2: "FCE6D8", accent3: "DAF2E8", accent4: "E9E3F7",
    accent5: "FFF3CF", accent6: "5B8DC9", hlink: "3B6FB0", folHlink: "6E5AA8",
  },
};
// Series validadas con validate_palette.js; solo se usan en gráficos.
const S = { azul: "5B8DC9", naranja: "E08E5B", menta: "4FB39A", lavanda: "9580CC", gris: "A9B4C2", suave: "C5D6EA" };
const REJILLA = "E6EBF2";

const num = (n) => Math.round(n).toString().replace(/\B(?=(\d{3})+(?!\d))/g, ".");
const dec = (x, d = 1) => x.toFixed(d).replace(".", ",");
const pct = (x, d = 1) => `${dec(x * 100, d)} %`;
const mill = (n, d = 1) => `${dec(n / 1e6, d)} M`;
const firmar = (x, d = 3) => `${x >= 0 ? "+" : "−"}${dec(Math.abs(x), d)}`;
const min_seg = (s) => `${Math.floor(s / 60)} min ${s % 60} s`;

const T = m.totales;
const ANT = m.carga_anterior;
const GOLD = m.conteos.gold;
const SILVER_TOTAL = m.conteos.silver_principales_total;
const COMPLETA = m.corridas.completa;
const BLOQUEANTES = m.calidad_log.filter((r) => r.severidad === "ERROR");
const REGLAS_OK = BLOQUEANTES.filter((r) => r.estado === "PASS").reduce((a, r) => a + r.reglas, 0);
const REGLAS_TOTAL = BLOQUEANTES.reduce((a, r) => a + r.reglas, 0);
const REGLAS_FINAL = m.reglas_grupos.filter((r) => r.grupo.startsWith("V")).reduce((a, r) => a + r.reglas, 0);
const REGLAS_SILVER = m.reglas_grupos.filter((r) => r.grupo.startsWith("S")).reduce((a, r) => a + r.reglas, 0);
const [R_LARGO, R_90, R_RECIENTE] = m.pearson;
const LV = JSON.parse(fs.readFileSync(path.join(BASE, "databricks", "dashboards", "DWMusicBrainz.lvdash.json"), "utf8"));
const WIDGETS = LV.pages.reduce((a, p) => a + p.layout.length, 0);

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE";
pres.title = "DWMusicBrainz en Databricks";
pres.subject = "Sustentación del Data Warehouse sobre Spark y Delta Lake";
pres.author = "Juan Sebastián Rincón Farelo";
pres.company = "Universidad Popular del Cesar";
pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
const C = pres.SchemeColor;
const PASTELES = [C.accent1, C.accent3, C.accent2, C.accent4, C.accent5];

pres.defineSlideMaster({
  title: "CONTENIDO",
  background: { color: C.background1 },
  objects: [
    { placeholder: { options: { name: "kicker", type: "body", x: 0.6, y: 0.34, w: 9, h: 0.34, fontSize: 14, bold: true, color: C.text2, margin: 0 }, text: "" } },
    { placeholder: { options: { name: "title", type: "title", x: 0.6, y: 0.68, w: 12.13, h: 0.8, fontSize: 34, bold: true, color: C.text1, align: "left", valign: "middle", margin: 0 }, text: "" } },
    { text: { text: "DWMusicBrainz · Sustentación", options: { x: 0.6, y: 7.02, w: 6, h: 0.28, fontSize: 11, color: C.text2, margin: 0 } } },
  ],
  slideNumber: { x: 12.03, y: 7.02, w: 0.7, h: 0.28, fontSize: 11, color: C.text2, align: "right" },
});
pres.defineSlideMaster({
  title: "PORTADA",
  background: { color: C.background1 },
  objects: [
    { placeholder: { options: { name: "kicker", type: "body", x: 0.7, y: 0.75, w: 6.6, h: 0.4, fontSize: 15, bold: true, color: C.text2, margin: 0 }, text: "" } },
    { placeholder: { options: { name: "title", type: "title", x: 0.7, y: 1.25, w: 6.6, h: 1.9, fontSize: 46, bold: true, color: C.text1, align: "left", valign: "top", margin: 0 }, text: "" } },
    { placeholder: { options: { name: "subtitle", type: "body", x: 0.7, y: 3.25, w: 6.4, h: 1.1, fontSize: 20, color: C.text2, margin: 0 }, text: "" } },
  ],
});

async function iconoPng(Icono, color = "23324A") {
  const svg = ReactDOMServer.renderToStaticMarkup(React.createElement(Icono, { color: `#${color}`, size: 256 }));
  const png = await sharp(Buffer.from(svg)).png().toBuffer();
  return `image/png;base64,${png.toString("base64")}`;
}

const notas = {};
const seccion = (titulo) => { notas.seccion = titulo; pres.addSection({ title: titulo }); };

function diapositiva(kicker, titulo, nota) {
  const s = pres.addSlide({ masterName: "CONTENIDO", sectionTitle: notas.seccion });
  s.addText(kicker, { placeholder: "kicker" });
  s.addText(titulo, { placeholder: "title" });
  s.addNotes(nota);
  return s;
}

function tarjeta(s, x, y, w, h, relleno, nombre) {
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, rectRadius: 0.12, fill: { color: relleno }, line: { color: relleno, width: 0 }, objectName: nombre || "Tarjeta" });
}

function texto(s, contenido, x, y, w, h, o = {}) {
  s.addText(contenido, { x, y, w, h, isTextBox: true, margin: 0, color: C.text1, fontSize: 16, valign: "top", ...o });
}

async function iconoCirculo(s, Icono, x, y, d, relleno) {
  s.addShape(pres.shapes.OVAL, { x, y, w: d, h: d, fill: { color: relleno }, line: { color: relleno, width: 0 }, objectName: "Círculo de ícono" });
  const lado = d * 0.52;
  s.addImage({ data: await iconoPng(Icono), x: x + (d - lado) / 2, y: y + (d - lado) / 2, w: lado, h: lado, altText: "Ícono" });
}

function cifra(s, x, y, w, h, relleno, valor, etiqueta, tam = 38) {
  tarjeta(s, x, y, w, h, relleno, `Cifra ${etiqueta}`);
  texto(s, valor, x + 0.25, y + 0.2, w - 0.5, h * 0.55, { fontSize: tam, bold: true, fontFace: "Cambria", valign: "middle" });
  texto(s, etiqueta, x + 0.25, y + h * 0.62, w - 0.5, h * 0.33, { fontSize: 15, color: C.text2 });
}

function lista(items, o = {}) {
  return items.map((t, i) => ({
    text: t,
    options: { bullet: { indent: 14 }, breakLine: i < items.length - 1, paraSpaceAfter: 7, ...o },
  }));
}

function tabla(s, encabezado, filas, x, y, w, anchos, o = {}) {
  const celda = (t, e = {}) => ({ text: String(t), options: { fontSize: o.tam || 14, color: C.text1, valign: "middle", ...e } });
  const rows = [
    encabezado.map((t) => celda(t, { bold: true, fill: { color: C.accent1 } })),
    ...filas.map((f, i) => f.map((t, j) => celda(t, { bold: j === 0, fill: { color: i % 2 ? C.background2 : C.background1 } }))),
  ];
  s.addTable(rows, { x, y, w, colW: anchos, border: { type: "solid", pt: 0.5, color: "E6EBF2" }, rowH: o.alto || 0.5, margin: [0.04, 0.1, 0.04, 0.1], objectName: o.nombre || "Tabla" });
}

const baseGrafico = () => ({
  catAxisLabelColor: "56647A", valAxisLabelColor: "56647A", catAxisLabelFontFace: "+mn-lt", valAxisLabelFontFace: "+mn-lt",
  catAxisLabelFontSize: 12, valAxisLabelFontSize: 12, legendFontFace: "+mn-lt", legendFontSize: 13, legendColor: "23324A",
  dataLabelFontFace: "+mn-lt", dataLabelColor: "23324A", dataLabelFontSize: 13, titleFontFace: "+mn-lt",
  valGridLine: { color: REJILLA, size: 0.75 }, catGridLine: { style: "none" }, showTitle: false,
});

async function construir() {
  // ---------------------------------------------------------------- Apertura
  seccion("Apertura");
  const portada = pres.addSlide({ masterName: "PORTADA", sectionTitle: notas.seccion });
  portada.addShape(pres.shapes.OVAL, { x: 7.6, y: 0.5, w: 5.4, h: 5.4, fill: { color: C.accent1 }, line: { color: C.accent1, width: 0 }, objectName: "Forma de fondo" });
  portada.addShape(pres.shapes.OVAL, { x: 10.2, y: 4.2, w: 2.7, h: 2.7, fill: { color: C.accent2 }, line: { color: C.accent2, width: 0 }, objectName: "Forma de fondo" });
  portada.addShape(pres.shapes.OVAL, { x: 7.3, y: 4.6, w: 2.0, h: 2.0, fill: { color: C.accent3 }, line: { color: C.accent3, width: 0 }, objectName: "Forma de fondo" });
  portada.addText("Proyecto integrador · Bases de Datos Avanzadas", { placeholder: "kicker" });
  portada.addText("DWMusicBrainz en Databricks", { placeholder: "title" });
  portada.addText("Data Warehouse de 58,8 millones de pistas con Spark y Delta Lake", { placeholder: "subtitle" });
  texto(portada, [
    { text: "Integrantes: Juan Rincón, Sebastián Russo, Jesús Figueroa", options: { breakLine: true } },
    { text: "Docente: Amilkar Sierra Romano", options: { breakLine: true } },
    { text: "Ingeniería de Sistemas · Universidad Popular del Cesar", options: { breakLine: true } },
    { text: "Valledupar, noviembre de 2026" },
  ], 0.7, 4.75, 6.4, 1.6, { fontSize: 16, color: C.text2, paraSpaceAfter: 4 });
  texto(portada, num(T.pistas), 8.25, 1.75, 4.2, 0.9, { fontSize: 40, bold: true, fontFace: "Cambria", align: "center" });
  texto(portada, "pistas en la tabla de hechos", 8.25, 2.65, 4.2, 0.4, { fontSize: 18, color: C.text2, align: "center" });
  portada.addNotes("Presentamos la migración de DWMusicBrainz a Databricks. El profesor pidió superar 50 millones de registros, así que dejamos de recortar el volcado y procesamos el catálogo completo de MusicBrainz con Spark en la nube.");

  const s2 = diapositiva("Resumen", "El proyecto en tres cifras",
    `La conclusión primero. Cumplimos el requisito con ${num(T.pistas)} pistas reales, el pipeline completo tardó ${min_seg(COMPLETA.segundos)} y todas las reglas bloqueantes de calidad están aprobadas. El resto de la presentación explica cómo llegamos aquí y qué limitaciones tiene el resultado.`);
  cifra(s2, 0.6, 1.8, 3.9, 2.5, C.accent1, mill(T.pistas), "pistas en fact_pista, por encima de los 50 M exigidos", 48);
  cifra(s2, 4.72, 1.8, 3.9, 2.5, C.accent3, min_seg(COMPLETA.segundos), "pipeline completo en Databricks Free Edition", 40);
  cifra(s2, 8.84, 1.8, 3.9, 2.5, C.accent4, `${REGLAS_OK}/${REGLAS_TOTAL}`, "reglas bloqueantes de calidad aprobadas", 48);
  tarjeta(s2, 0.6, 4.65, 12.13, 1.85, C.background2, "Mensaje central");
  texto(s2, [
    { text: "Mensaje central. ", options: { bold: true } },
    { text: "El mismo modelo en estrella ahora procesa el catálogo completo, con conteos conciliados contra el origen. Al recalcular con todos los datos, varias conclusiones de la entrega anterior cambiaron y aquí se corrigen." },
  ], 0.9, 4.9, 11.5, 1.35, { fontSize: 20, valign: "middle" });

  // ---------------------------------------------------------------- Problema
  seccion("Problema");
  const s3 = diapositiva("El requisito", "De 15 M a 58,8 M de pistas",
    `El requisito nuevo es superar 50 millones de registros. La revisión del proyecto corrigió dos ideas. Solo la tabla track tenía tope, con TARGET_ROWS en 15 millones, y Silver ya sumaba ${mill(ANT.silver_filas)} de filas. El hecho tenía ${mill(ANT.filas_hecho, 2)} de filas por su grano agregado, no por falta de datos. Además, Python solo orquestaba: quien hacía el trabajo era PostgreSQL en un nodo.`);
  s3.addChart(pres.charts.BAR, [{ name: "Pistas (millones)", labels: ["Carga anterior", "Requisito", "Volcado completo"], values: [ANT.pistas / 1e6, 50, T.pistas / 1e6] }], {
    ...baseGrafico(), x: 0.6, y: 1.7, w: 6.1, h: 4.95, barDir: "col", chartColors: [S.suave, S.gris, S.azul], showValue: true, dataLabelPosition: "outEnd",
    dataLabelFormatCode: "0.0", showLegend: false, valAxisHidden: true, valGridLine: { style: "none" }, barGapWidthPct: 60, catAxisLabelFontSize: 14, altText: "Barras de pistas: carga anterior, requisito y volcado completo",
  });
  const p3 = [
    [fa.FaCut, C.accent2, "Solo track tenía tope", `TARGET_ROWS dejaba ${mill(ANT.pistas, 0)} de ${mill(T.pistas)} de pistas.`],
    [fa.FaLayerGroup, C.accent1, "Silver ya era grande", `${mill(ANT.silver_filas)} de filas entre todas sus tablas.`],
    [fa.FaCompressArrowsAlt, C.accent4, "El hecho estaba agregado", `${mill(ANT.filas_hecho, 2)} de filas por su grano diario.`],
    [fa.FaServer, C.accent3, "Python solo orquestaba", "El trabajo pesado lo hacía PostgreSQL."],
  ];
  for (let i = 0; i < p3.length; i++) {
    const y = 1.75 + i * 1.24;
    await iconoCirculo(s3, p3[i][0], 7.1, y, 0.82, p3[i][1]);
    texto(s3, p3[i][2], 8.15, y - 0.03, 4.6, 0.4, { fontSize: 19, bold: true });
    texto(s3, p3[i][3], 8.15, y + 0.39, 4.6, 0.6, { fontSize: 16, color: C.text2 });
  }

  const s4 = diapositiva("El cambio", "Cambió la plataforma, no el modelo",
    "Reemplazamos el motor y el almacenamiento. Se mantienen la arquitectura Medallón, el modelo en estrella de Kimball y los ocho requerimientos funcionales. La entrega anterior sigue intacta en etl y sql.");
  tabla(s4, ["Función", "Entrega anterior", "Ahora"], [
    ["Plataforma", "PostgreSQL local", "Databricks Free Edition"],
    ["Motor", "Un solo nodo", "Apache Spark serverless"],
    ["Lenguaje", "SQL y Python", "PySpark y Spark SQL"],
    ["Almacenamiento", "Tablas PostgreSQL", "Delta Lake con Unity Catalog"],
    ["Orquestación", "Script de Python", "Lakeflow Jobs"],
    ["Rendimiento", "Particiones e índices", "Liquid clustering y agregados"],
    ["Visualización", "Power BI", "Dashboard AI/BI; Power BI se conserva"],
  ], 0.6, 1.7, 12.13, [2.9, 3.9, 5.33], { alto: 0.52, nombre: "Comparación de tecnologías" });
  tarjeta(s4, 0.6, 6.05, 12.13, 0.72, C.accent3, "Lo que se mantiene");
  texto(s4, [{ text: "Se mantiene: ", options: { bold: true } }, { text: "arquitectura Medallón, estrella de Kimball y los requerimientos RF01 a RF08." }], 0.85, 6.05, 11.6, 0.72, { valign: "middle", fontSize: 17 });

  // ---------------------------------------------------------------- Arquitectura
  seccion("Arquitectura");
  const s5 = diapositiva("Arquitectura", "Medallón completo en la nube",
    `El volcado oficial se descarga, se verifica con SHA-256 y sus 11 tablas suben a un Volume de Unity Catalog. Bronze guarda una copia fiel como texto, Silver aplica tipos y calidad, y Gold construye el modelo en estrella. Lakeflow Jobs orquesta cada tarea y el esquema meta registra auditoría y calidad. Bronze y Silver tienen ${num(SILVER_TOTAL)} filas en sus tablas principales.`);
  const pasos = [
    [fa.FaFileArchive, C.accent5, "Volcado", "7,7 GB\n11 tablas TSV"],
    [fa.FaFolderOpen, C.accent2, "Volume", "Archivos crudos\ngobernados"],
    [fa.FaDatabase, C.accent4, "Bronze", `${mill(SILVER_TOTAL, 2)}\ncopia en texto`],
    [fa.FaFilter, C.accent1, "Silver", "Tipos, escapes\ny calidad"],
    [fa.FaStar, C.accent3, "Gold", `3 hechos\n7 dimensiones`],
    [fa.FaChartBar, C.accent2, "Consumo", "AI/BI\ny Power BI"],
  ];
  const ancho5 = 1.76, salto5 = 2.074;
  for (let i = 0; i < pasos.length; i++) {
    const x = 0.6 + i * salto5;
    tarjeta(s5, x, 1.8, ancho5, 3.0, pasos[i][1], `Etapa ${pasos[i][2]}`);
    s5.addImage({ data: await iconoPng(pasos[i][0]), x: x + 0.65, y: 2.03, w: 0.46, h: 0.46, altText: pasos[i][2] });
    texto(s5, pasos[i][2], x + 0.1, 2.62, ancho5 - 0.2, 0.45, { fontSize: 20, bold: true, align: "center" });
    texto(s5, pasos[i][3], x + 0.1, 3.14, ancho5 - 0.2, 1.5, { fontSize: 15, align: "center" });
    if (i < pasos.length - 1) {
      s5.addShape(pres.shapes.CHEVRON, { x: x + ancho5 + 0.06, y: 3.05, w: 0.2, h: 0.32, fill: { color: "A9B4C2" }, line: { color: "A9B4C2", width: 0 }, objectName: "Flecha" });
    }
  }
  tarjeta(s5, 0.6, 5.15, 12.13, 0.72, C.background2, "Gobierno");
  texto(s5, [{ text: "Unity Catalog ", options: { bold: true } }, { text: "gobierna tablas y archivos. " }, { text: "Lakeflow Jobs ", options: { bold: true } }, { text: "orquesta las tareas." }], 0.85, 5.15, 11.6, 0.72, { valign: "middle", fontSize: 17 });
  tarjeta(s5, 0.6, 5.98, 12.13, 0.72, C.background2, "Auditoría");
  texto(s5, [{ text: "Esquema meta: ", options: { bold: true } }, { text: "etl_audit registra cada carga y data_quality_log registra cada regla." }], 0.85, 5.98, 11.6, 0.72, { valign: "middle", fontSize: 17 });

  const s6 = diapositiva("Tecnologías", "Por qué estas tecnologías",
    "Cada pieza responde a una necesidad. Databricks nos da Spark administrado sin instalar un clúster. Delta agrega transacciones e historial, que usamos para comparar versiones con time travel. Unity Catalog gobierna tablas y archivos, y además Databricks ya no recomienda DBFS. Lakeflow Jobs evita mantener un servidor de orquestación. Las razones completas están en la documentación técnica.");
  const techs = [
    [fa.FaCloud, C.accent1, "Databricks", "Spark administrado, sin instalar ni operar un clúster."],
    [fa.FaBolt, C.accent2, "PySpark y Spark SQL", "Procesamiento distribuido y lógica legible en SQL."],
    [fa.FaHistory, C.accent3, "Delta Lake", "ACID e historial: comparamos versiones con time travel."],
    [fa.FaShieldAlt, C.accent4, "Unity Catalog", "Gobierno de tablas y Volumes; DBFS está deprecado."],
    [fa.FaProjectDiagram, C.accent5, "Lakeflow Jobs", "Tareas con dependencias, sin servidor de orquestación."],
    [fa.FaChartPie, C.accent1, "AI/BI y Power BI", "Dashboard en la nube; Power BI como respaldo."],
  ];
  for (let i = 0; i < techs.length; i++) {
    const x = 0.6 + (i % 3) * 4.12, y = 1.75 + Math.floor(i / 3) * 2.52;
    tarjeta(s6, x, y, 3.89, 2.3, C.background2, techs[i][2]);
    await iconoCirculo(s6, techs[i][0], x + 0.25, y + 0.25, 0.75, techs[i][1]);
    texto(s6, techs[i][2], x + 1.15, y + 0.25, 2.6, 0.75, { fontSize: 19, bold: true, valign: "middle" });
    texto(s6, techs[i][3], x + 0.25, y + 1.15, 3.4, 1.0, { fontSize: 16, color: C.text2 });
  }

  const s7 = diapositiva("Decisión", "Alternativas evaluadas",
    "Comparamos opciones de forma cualitativa, con documentación oficial; no hicimos un benchmark. Hay que decirlo con claridad: 58,8 millones de filas no es un volumen extremo y un motor de un nodo como DuckDB probablemente lo resolvería. Usar Spark y Databricks fue una decisión del proyecto, para trabajar con procesamiento distribuido y arquitectura lakehouse.");
  tabla(s7, ["Alternativa", "Por qué se descartó"], [
    ["PostgreSQL local", "Un solo nodo, disco limitado y sin práctica distribuida"],
    ["Spark local", "13,8 GB de RAM y Java 8; muy justo para este volumen"],
    ["DuckDB", "Probablemente alcanza, pero no es procesamiento distribuido"],
    ["Snowflake, Redshift, Fabric", "Pruebas temporales; BigQuery sandbox: 10 GB de almacenamiento"],
    ["Hadoop y Hive", "Exigen operar un clúster; ecosistema más pesado"],
  ], 0.6, 1.7, 12.13, [3.9, 8.23], { alto: 0.58, nombre: "Alternativas descartadas" });
  tarjeta(s7, 0.6, 5.35, 12.13, 1.35, C.accent2, "Aclaración honesta");
  texto(s7, [
    { text: "Aclaración honesta. ", options: { bold: true } },
    { text: "58,8 M de filas no es un volumen extremo y no se midió PostgreSQL contra Spark con los mismos datos. Spark fue una decisión del proyecto, no una conclusión de rendimiento." },
  ], 0.88, 5.35, 11.6, 1.35, { fontSize: 18, valign: "middle" });

  const s8 = diapositiva("Modelo", "Gold tiene dos niveles de grano",
    `El requisito se cumple en fact_pista, una fila por pista. Encima hay hechos agregados para que los dashboards respondan rápido. El ejemplo es real: el lanzamiento ${m.ejemplo_grano.lanzamiento_id}, de Shakira, ocupa ${m.ejemplo_grano.pistas} filas en fact_pista y solo una de ellas cuenta el lanzamiento, así la suma no duplica. En la carga recortada aparecía con 21 pistas y 2 soportes; hoy tiene ${m.ejemplo_grano.pistas} y ${m.ejemplo_grano.soportes}, algo consistente con el corte por líneas.`);
  const niveles = [
    [C.accent1, "fact_pista", num(GOLD.fact_pista), "Una fila por pista: el detalle atómico"],
    [C.accent3, "fact_produccion_musical", num(GOLD.fact_produccion_musical), "Día × artista × perfil × área × formato × idioma"],
    [C.accent4, "fact_distribucion_duracion", num(GOLD.fact_distribucion_duracion), "Año × formato × idioma × área × banda"],
  ];
  niveles.forEach((n, i) => {
    const y = 1.75 + i * 1.65;
    tarjeta(s8, 0.6, y, 7.3, 1.48, n[0], n[1]);
    texto(s8, n[1], 0.85, y + 0.14, 4.3, 0.42, { fontSize: 18, bold: true });
    texto(s8, n[2], 5.05, y + 0.1, 2.65, 0.5, { fontSize: 24, bold: true, fontFace: "Cambria", align: "right" });
    texto(s8, n[3], 0.85, y + 0.7, 6.8, 0.6, { fontSize: 16, color: C.text2 });
  });
  tarjeta(s8, 8.15, 1.75, 4.58, 4.78, C.background2, "Ejemplo real");
  texto(s8, "Ejemplo real", 8.42, 1.95, 4, 0.4, { fontSize: 19, bold: true });
  texto(s8, `Lanzamiento ${m.ejemplo_grano.lanzamiento_id}`, 8.42, 2.38, 4.05, 0.35, { fontSize: 15, color: C.text2 });
  texto(s8, lista([
    `${m.ejemplo_grano.pistas} pistas: ${m.ejemplo_grano.pistas} filas en fact_pista`,
    `${m.ejemplo_grano.soportes} soportes distintos`,
    "Solo 1 fila cuenta el lanzamiento",
    `${m.ejemplo_grano.pistas_isrc} pistas con ISRC`,
  ]), 8.42, 2.85, 4.05, 2.1, { fontSize: 17 });
  texto(s8, "La carga recortada mostraba 21 pistas y 2 soportes.", 8.42, 5.1, 4.05, 1.2, { fontSize: 16, color: C.text2 });

  // ---------------------------------------------------------------- Proceso
  seccion("Proceso");
  const s9 = diapositiva("Proceso", "Del volcado a Gold en seis pasos",
    "Seguimos este orden para reducir riesgo. Primero comprobamos integridad del volcado, después medimos capacidad antes de construir, y recién entonces hicimos el pipeline. Luego llegaron las correcciones de etiquetas y del desempate por país, el dashboard y la publicación.");
  const tl = [
    ["1", "Descarga", "SHA-256 correcto y 11 tablas extraídas"],
    ["2", "Carga", "track dividida en 8 bloques por el límite de 5 GiB"],
    ["3", "Capacidad", "Prueba con todas las pistas antes de construir"],
    ["4", "Pipeline", "Bronze, Silver, Gold, validación y job"],
    ["5", "Correcciones", "Catálogos oficiales y desempate por país"],
    ["6", "Dashboard", "3 páginas AI/BI revisadas en el navegador"],
  ];
  tl.forEach((p, i) => {
    const x = 0.6 + (i % 3) * 4.12, y = 1.8 + Math.floor(i / 3) * 2.45;
    tarjeta(s9, x, y, 3.89, 2.2, PASTELES[i % PASTELES.length], `Paso ${p[0]}`);
    s9.addShape(pres.shapes.OVAL, { x: x + 0.25, y: y + 0.22, w: 0.62, h: 0.62, fill: { color: C.background1 }, line: { color: C.background1, width: 0 }, objectName: "Número" });
    texto(s9, p[0], x + 0.25, y + 0.22, 0.62, 0.62, { fontSize: 20, bold: true, align: "center", valign: "middle" });
    texto(s9, p[1], x + 1.02, y + 0.22, 2.7, 0.62, { fontSize: 21, bold: true, valign: "middle" });
    texto(s9, p[2], x + 0.25, y + 1.02, 3.4, 1.05, { fontSize: 16 });
  });

  const cap = m.prueba_capacidad;
  const bronzeCap = cap.filter((e) => e.etapa.startsWith("bronze.")).reduce((a, e) => a + e.segundos, 0);
  const hechoCap = cap.find((e) => e.etapa === "gold.spike_fact_pista").segundos;
  const chequeo = cap.find((e) => e.etapa === "checks.fact").segundos;
  const consulta = cap.find((e) => e.etapa === "query.year_format").segundos;
  const s10 = diapositiva("Capacidad", "La prueba despejó la duda principal",
    `Antes de escribir el pipeline probamos lo más riesgoso: construir el hecho con todas las pistas en Free Edition. Cargar 9 tablas tomó ${Math.round(bronzeCap)} segundos y el hecho ${Math.round(hechoCap)} segundos, sin perder ninguna pista en los joins. Advertencia: no conocemos cuánta cuota diaria consumió.`);
  s10.addChart(pres.charts.BAR, [{ name: "Segundos", labels: ["Bronze, 9 tablas", "Hecho con todos los joins", "Validaciones", "Agregación"], values: [bronzeCap, hechoCap, chequeo, consulta].map((v) => Math.round(v)) }], {
    ...baseGrafico(), x: 0.6, y: 1.7, w: 7.6, h: 4.95, barDir: "bar", chartColors: [S.azul], showValue: true, dataLabelPosition: "outEnd", dataLabelFormatCode: "0 \"s\"",
    showLegend: false, valAxisHidden: true, valGridLine: { style: "none" }, catAxisOrientation: "maxMin", barGapWidthPct: 55, catAxisLabelFontSize: 14, altText: "Segundos por etapa de la prueba de capacidad",
  });
  cifra(s10, 8.5, 1.8, 4.23, 2.3, C.accent1, num(T.pistas), "pistas tras todos los joins", 34);
  tarjeta(s10, 8.5, 4.3, 4.23, 2.3, C.accent2, "Lo que no se sabe");
  texto(s10, "Sin confirmar", 8.75, 4.5, 3.75, 0.4, { fontSize: 19, bold: true });
  texto(s10, "No se midió cuánta cuota diaria de Free Edition consumió la prueba.", 8.75, 4.95, 3.75, 1.5, { fontSize: 17 });

  const nombres = { pruebas: "Pruebas", bronze: "Bronze", silver: "Silver", gold_dimensiones: "Dimensiones", gold_fact_pista: "Hecho de pista", gold_agregados: "Agregados", validacion: "Validación" };
  const orden = Object.keys(nombres);
  const tareas = orden.map((k) => COMPLETA.tareas.find((t) => t.tarea === k));
  const s11 = diapositiva("Orquestación", `Pipeline completo en ${min_seg(COMPLETA.segundos)}`,
    `El job de Lakeflow encadena sus tareas. La primera corrida completa tenía siete y terminó en ${COMPLETA.segundos} segundos; después se agregó la tarea de catálogos. Bronze fue rápido porque reutilizó las nueve tablas de la prueba de capacidad; solo cargó area y language. Cada tarea es reanudable y registra su resultado en meta.etl_audit.`);
  s11.addChart(pres.charts.BAR, [{ name: "Segundos", labels: tareas.map((t) => nombres[t.tarea]), values: tareas.map((t) => t.segundos) }], {
    ...baseGrafico(), x: 0.6, y: 1.7, w: 7.6, h: 4.95, barDir: "bar", chartColors: [S.menta], showValue: true, dataLabelPosition: "outEnd", dataLabelFormatCode: "0 \"s\"",
    showLegend: false, valAxisHidden: true, valGridLine: { style: "none" }, catAxisOrientation: "maxMin", barGapWidthPct: 45, catAxisLabelFontSize: 14, altText: "Segundos por tarea del job",
  });
  cifra(s11, 8.5, 1.8, 4.23, 2.3, C.accent3, `${COMPLETA.segundos} s`, "duración total de la corrida", 40);
  tarjeta(s11, 8.5, 4.3, 4.23, 2.3, C.background2, "Nota");
  texto(s11, "A tener en cuenta", 8.75, 4.5, 3.75, 0.4, { fontSize: 19, bold: true });
  texto(s11, "Bronze reutilizó 9 tablas de la prueba; solo cargó area y language.", 8.75, 4.95, 3.75, 1.5, { fontSize: 17 });

  const s12 = diapositiva("Validación", "Cómo se comprobó el resultado",
    `Validamos en cuatro niveles. Las reglas de negocio se probaron con datos pequeños, viendo primero la prueba fallar y después pasar. El registro tiene ${REGLAS_TOTAL} reglas bloqueantes aprobadas: ${REGLAS_FINAL} de la validación final y ${REGLAS_SILVER} de Silver. Además, los filtros del dashboard se compararon contra SQL.`);
  const val = [
    [fa.FaVial, C.accent1, `${m.proceso.pruebas_fixtures_verde} de ${m.proceso.pruebas_fixtures_verde}`, "pruebas con datos pequeños, primero en rojo y luego en verde"],
    [fa.FaCheckDouble, C.accent3, `${REGLAS_OK} reglas`, `bloqueantes: ${REGLAS_FINAL} finales y ${REGLAS_SILVER} de Silver`],
    [fa.FaBalanceScale, C.accent2, num(T.pistas), "pistas iguales en volcado, Bronze, Silver y Gold"],
    [fa.FaSlidersH, C.accent4, "2 filtros", "Año y Década coinciden exactamente con SQL"],
  ];
  for (let i = 0; i < val.length; i++) {
    const x = 0.6 + (i % 2) * 6.18, y = 1.8 + Math.floor(i / 2) * 2.45;
    tarjeta(s12, x, y, 5.95, 2.2, C.background2, val[i][2]);
    await iconoCirculo(s12, val[i][0], x + 0.28, y + 0.45, 1.25, val[i][1]);
    texto(s12, val[i][2], x + 1.8, y + 0.32, 3.95, 0.7, { fontSize: 30, bold: true, fontFace: "Cambria", valign: "middle" });
    texto(s12, val[i][3], x + 1.8, y + 1.05, 3.95, 0.95, { fontSize: 16, color: C.text2 });
  }

  // ---------------------------------------------------------------- Resultados
  seccion("Resultados");
  const s13 = diapositiva("Resultados", "Las cifras cambiaron con todos los datos",
    "Esta es la comparación con la entrega anterior. El cambio no es solo de escala: la correlación reciente se debilitó y el cruce digital se adelantó un año. Por eso las conclusiones anteriores se reemplazan. Recordemos que la carga de 15 millones era por orden de archivo y no una muestra aleatoria.");
  tabla(s13, ["Métrica", "Carga de 15 M", "Volcado completo"], [
    ["Pistas", num(ANT.pistas), num(T.pistas)],
    ["Lanzamientos", num(ANT.lanzamientos), num(T.lanzamientos)],
    ["Soportes", num(ANT.soportes), num(T.soportes)],
    ["Filas del hecho agregado", num(ANT.filas_hecho), num(GOLD.fact_produccion_musical)],
    ["Correlación año-duración 1950–2025", firmar(ANT.r_1950_2025, 2), firmar(R_LARGO.r)],
    ["Correlación año-duración 2013–2025", firmar(ANT.r_2013_2025, 2), firmar(R_RECIENTE.r)],
    ["Digital supera a óptico", String(ANT.cruce_digital), String(m.cruce_digital)],
  ], 0.6, 1.7, 12.13, [6.13, 3, 3], { alto: 0.58, nombre: "Cifras antes y ahora" });
  texto(s13, "La carga de 15 M seguía el orden del archivo: no era una muestra aleatoria.", 0.6, 6.42, 12.13, 0.4, { fontSize: 16, color: C.text2 });

  const serie = m.anual.filter((a) => a.anio >= 1990);
  const s14 = diapositiva("RF04", `Digital supera a óptico en ${m.cruce_digital}`,
    `La categoría óptica incluye CD, DVD y formatos similares, por eso decimos óptico y no solo CD. El cruce ocurre en ${m.cruce_digital}. En 2025, digital representa ${pct(m.ultimo_anio.digital)} de los lanzamientos con fecha y óptico ${pct(m.ultimo_anio.optico)}.`);
  s14.addChart(pres.charts.LINE, [
    { name: "Digital", labels: serie.map((a) => String(a.anio)), values: serie.map((a) => a.digital) },
    { name: "Óptico (CD, DVD y similares)", labels: serie.map((a) => String(a.anio)), values: serie.map((a) => a.optico) },
  ], {
    ...baseGrafico(), x: 0.6, y: 1.7, w: 8.5, h: 4.95, chartColors: [S.azul, S.naranja], lineSize: 3, lineDataSymbol: "none", showLegend: true, legendPos: "b",
    valAxisLabelFormatCode: "0%", valAxisMaxVal: 1, valAxisMinVal: 0, valAxisMajorUnit: 0.25, catAxisLabelFrequency: 5, altText: "Cuota anual de digital y óptico entre 1990 y 2025",
  });
  cifra(s14, 9.35, 1.8, 3.38, 2.3, C.accent1, pct(m.ultimo_anio.digital), "digital en 2025", 36);
  cifra(s14, 9.35, 4.3, 3.38, 2.3, C.accent2, pct(m.ultimo_anio.optico), "óptico en 2025", 36);

  const h = m.histograma;
  const dos = h.bandas.slice().sort((a, b) => b.pistas - a.pistas).slice(0, 2).map((b) => b.banda);
  const s15 = diapositiva("RF02", "La duración típica está entre 3 y 4 minutos",
    `El histograma muestra una distribución unimodal con cola larga a la derecha. La moda es ${h.moda_banda} y las dos bandas más frecuentes concentran ${pct(h.dos_mayores_pct)} de las pistas con duración. La media es ${dec(h.media_min, 2)} minutos y ${pct(h.mayor_10_pct)} supera los 10 minutos.`);
  s15.addChart(pres.charts.BAR, [{ name: "Pistas (millones)", labels: h.bandas.map((b) => b.banda.split("–")[0]), values: h.bandas.map((b) => b.pistas / 1e6) }], {
    ...baseGrafico(), x: 0.6, y: 1.7, w: 8.5, h: 4.95, barDir: "col", chartColors: h.bandas.map((b) => (dos.includes(b.banda) ? S.azul : S.suave)), showLegend: false,
    barGapWidthPct: 12, valAxisLabelFormatCode: "0", showCatAxisTitle: true, catAxisTitle: "Inicio de la banda (min:s)", catAxisTitleColor: "56647A", catAxisTitleFontSize: 13,
    showValAxisTitle: true, valAxisTitle: "Millones de pistas", valAxisTitleColor: "56647A", valAxisTitleFontSize: 13, altText: "Histograma de duración por bandas de 30 segundos",
  });
  cifra(s15, 9.35, 1.8, 3.38, 2.3, C.accent1, pct(h.dos_mayores_pct), "de las pistas entre 3:00 y 4:00", 36);
  cifra(s15, 9.35, 4.3, 3.38, 2.3, C.accent3, `${dec(h.media_min, 2)} min`, "duración media por pista", 34);

  const s16 = diapositiva("RF05", "El acortamiento reciente es débil",
    `A largo plazo la duración media crece con el año: r de ${firmar(R_LARGO.r)}. Entre 2013 y 2025 el signo cambia, pero r es ${firmar(R_RECIENTE.r)} con ${R_RECIENTE.n} años, por debajo del valor crítico de 0,553 para esa muestra. No podemos afirmar que el streaming acortó las canciones. Pearson usa medias anuales y no prueba causalidad.`);
  [[R_LARGO, C.accent1, "Tendencia fuerte al alza"], [R_90, C.accent3, "Alza fuerte"], [R_RECIENTE, C.accent2, "Descenso débil, no concluyente"]].forEach(([p, c, t], i) => {
    const x = 0.6 + i * 4.12;
    tarjeta(s16, x, 1.8, 3.89, 2.75, c, `Período ${p.inicio}`);
    texto(s16, `${p.inicio}–${p.fin}`, x + 0.28, 2.0, 3.3, 0.4, { fontSize: 18, bold: true });
    texto(s16, `r = ${firmar(p.r)}`, x + 0.28, 2.45, 3.4, 0.95, { fontSize: 38, bold: true, fontFace: "Cambria", valign: "middle" });
    texto(s16, t, x + 0.28, 3.42, 3.4, 0.4, { fontSize: 16 });
    texto(s16, `${firmar(p.pendiente_s, 2)} s por año · ${p.n} años`, x + 0.28, 3.85, 3.4, 0.4, { fontSize: 15, color: C.text2 });
  });
  tarjeta(s16, 0.6, 4.85, 12.13, 1.8, C.background2, "Lectura");
  texto(s16, lista([
    `Con ${R_RECIENTE.n} años, |r| debe superar 0,553 para ser significativo al 5 %.`,
    "La hipótesis de canciones más cortas por el streaming no queda demostrada.",
    "Pearson usa medias anuales: mide asociación, no causalidad.",
  ]), 0.9, 5.05, 11.5, 1.45, { fontSize: 17 });

  const s17 = diapositiva("RF03", "El mayor bloque no es un país",
    `Los lanzamientos multiterritoriales quedan en [Worldwide], con ${num(m.especiales.lanzamientos_worldwide)} lanzamientos. Es más del doble que Estados Unidos, el primer país, con ${num(m.paises[0].lanzamientos)}. Por eso se comparan los países por separado de esa categoría.`);
  const top = [{ pais: "[Worldwide]", lanzamientos: m.especiales.lanzamientos_worldwide }, ...m.paises.slice(0, 7)];
  s17.addChart(pres.charts.BAR, [{ name: "Lanzamientos", labels: top.map((p) => p.pais), values: top.map((p) => p.lanzamientos) }], {
    ...baseGrafico(), x: 0.6, y: 1.7, w: 8.5, h: 4.95, barDir: "bar", chartColors: top.map((p, i) => (i === 0 ? S.gris : i === 1 ? S.azul : S.suave)), showValue: true, dataLabelPosition: "outEnd",
    dataLabelFormatCode: "#,##0", showLegend: false, valAxisHidden: true, valGridLine: { style: "none" }, catAxisOrientation: "maxMin", barGapWidthPct: 40, catAxisLabelFontSize: 14, altText: "Lanzamientos por área",
  });
  const corea = m.paises.find((p) => p.pais === "South Korea");
  cifra(s17, 9.35, 1.8, 3.38, 2.3, C.background2, mill(m.especiales.lanzamientos_worldwide, 2), "en [Worldwide]", 34);
  cifra(s17, 9.35, 4.3, 3.38, 2.3, C.accent1, pct(corea.digital), "digital en Corea del Sur, la más alta del Top 30", 34);

  const dec_isrc = m.decadas;
  const s18 = diapositiva("RF06", `Solo ${pct(T.isrc_pct)} de las pistas tiene ISRC`,
    `El ISRC identifica grabaciones y permite rastrear su uso. La cobertura total es ${pct(T.isrc_pct)}. El gráfico muestra la cobertura por década, de 1950 a 2020. Cuidado al interpretarla: indica cuántas pistas registradas en MusicBrainz tienen código, no el registro real en la industria.`);
  s18.addChart(pres.charts.BAR, [{ name: "Cobertura ISRC", labels: dec_isrc.map((d) => d.decada), values: dec_isrc.map((d) => d.isrc) }], {
    ...baseGrafico(), x: 0.6, y: 1.7, w: 8.5, h: 4.95, barDir: "col", chartColors: [S.lavanda], showValue: true, dataLabelPosition: "outEnd", dataLabelFormatCode: "0%",
    showLegend: false, valAxisHidden: true, valGridLine: { style: "none" }, barGapWidthPct: 45, catAxisLabelFontSize: 14, altText: "Cobertura ISRC por década",
  });
  cifra(s18, 9.35, 1.8, 3.38, 2.3, C.accent4, num(T.pistas_isrc), "pistas con código ISRC", 30);
  cifra(s18, 9.35, 4.3, 3.38, 2.3, C.background2, num(m.emergentes.total), "artistas emergentes desde 2015", 30);

  // ---------------------------------------------------------------- Calidad
  seccion("Errores");
  const s19 = diapositiva("Gobierno del dato", "Errores hallados y corregidos",
    "Aquí está lo que falló y cómo lo resolvimos. Lo importante es la última columna: dos errores graves, las etiquetas y el desempate por país, pasaron las validaciones iniciales. Las reglas comprobaban integridad, no significado. Por eso los detectamos inspeccionando los resultados y después agregamos reglas bloqueantes para cada uno.");
  tabla(s19, ["Error", "Corrección", "Se detectó por"], [
    ["Columnas de medium invertidas", "Orden real del volcado", "Inspección de archivos"],
    ["Etiquetas heredadas erróneas", "Catálogos oficiales y regla V08", "Inspección, no por reglas"],
    ["Desempate por menor ID de país", "Regla nueva y validación V12", "Inspección, no por reglas"],
    ["Límite de 5 GiB al subir track", "8 bloques de 1 GB", "Error de la CLI"],
    ["Año 0 en el filtro", "Fila sin fecha fuera del rango", "Revisión visual"],
    ["Dispersión sin cargar", "Cálculo movido a SQL", "Revisión visual"],
    ["Resultados en caché", "Actualización forzada", "Revisión en el navegador"],
  ], 0.6, 1.7, 12.13, [4.9, 4.0, 3.23], { alto: 0.56, nombre: "Errores corregidos" });
  texto(s19, "Las reglas iniciales revisaban integridad, no significado: por eso dos errores pasaron.", 0.6, 6.42, 12.13, 0.4, { fontSize: 16, color: C.text2 });

  const antes = m.proceso.afganistan_antes;
  const s20 = diapositiva("Caso de estudio", "Afghanistan: un dato raro era un error",
    `Afghanistan aparecía con ${num(antes.lanzamientos)} lanzamientos de ${num(antes.artistas)} artistas. La causa: lanzamientos publicados en muchos países con la misma fecha, y el desempate elegía el menor ID, que es el de Afghanistan. La regla nueva envía empates de 10 o más países a [Worldwide]. Bajó a ${num(m.especiales.afganistan_lanzamientos)}, y los totales no cambiaron.`);
  cifra(s20, 0.6, 1.8, 3.1, 2.4, C.accent2, num(antes.lanzamientos), "lanzamientos antes", 40);
  await iconoCirculo(s20, fa.FaArrowRight, 3.93, 2.57, 0.85, C.background2);
  cifra(s20, 5.0, 1.8, 3.1, 2.4, C.accent3, num(m.especiales.afganistan_lanzamientos), "lanzamientos después", 40);
  tarjeta(s20, 8.35, 1.8, 4.38, 2.4, C.background2, "Causa");
  texto(s20, "Causa", 8.6, 2.0, 3.9, 0.4, { fontSize: 19, bold: true });
  texto(s20, "En cada empate de fecha ganaba el menor ID de país: Afghanistan es el 1.", 8.6, 2.45, 3.9, 1.55, { fontSize: 17 });
  tabla(s20, ["Países empatados", "Regla nueva", "Lanzamientos"], [
    ["10 o más", "Pasa a [Worldwide]", num(m.proceso.caminos_evento.diez_o_mas)],
    ["2 a 9", "País con más lanzamientos", num(m.proceso.caminos_evento.dos_a_nueve)],
    ["[Worldwide] entre los empatados", "Se conserva [Worldwide]", num(m.proceso.caminos_evento.worldwide_explicito)],
  ], 0.6, 4.5, 12.13, [5.13, 4.5, 2.5], { alto: 0.5, nombre: "Regla de desempate" });

  // ---------------------------------------------------------------- Dashboard
  seccion("Dashboard");
  const s21 = diapositiva("Dashboard", "Tres páginas en Databricks AI/BI",
    "El dashboard tiene tres páginas: resumen ejecutivo, análisis detallado y calidad y catálogo. Lo revisamos abierto en el navegador y comparamos sus filtros con SQL. Corre sobre el warehouse, así no depende de importar 11,5 millones de filas a nuestros equipos.");
  [["dash_resumen.png", "Resumen ejecutivo"], ["dash_detallado.png", "Análisis detallado"], ["dash_calidad.png", "Calidad y catálogo"]].forEach(([f, t], i) => {
    const x = 0.6 + i * 4.12;
    tarjeta(s21, x, 1.7, 3.89, 4.95, C.background2, t);
    texto(s21, t, x + 0.2, 1.84, 3.5, 0.4, { fontSize: 18, bold: true });
    s21.addImage({ path: path.join(BUILD, f), x: x + 0.17, y: 2.35, w: 3.55, h: 3.14, altText: `Captura de ${t}` });
  });
  texto(s21, `${LV.pages.length} páginas`, 1.15, 5.65, 2.8, 0.75, { fontSize: 24, bold: true, fontFace: "Cambria", align: "center", valign: "middle" });
  texto(s21, `${WIDGETS} widgets`, 5.27, 5.65, 2.8, 0.75, { fontSize: 24, bold: true, fontFace: "Cambria", align: "center", valign: "middle" });
  texto(s21, `${LV.datasets.length} datasets`, 9.39, 5.65, 2.8, 0.75, { fontSize: 24, bold: true, fontFace: "Cambria", align: "center", valign: "middle" });

  const s22 = diapositiva("Diseño", "Color y gráficos con un criterio",
    "El dashboard usa azul para el dato principal, naranja como contraste y tonos suaves para el contexto. La paleta pasó un validador de daltonismo y contraste. Cada gráfico responde a un tipo de pregunta según Abela: comparación, composición, distribución o relación. Eliminamos colores sin significado, como los 30 tonos que tenía la dispersión.");
  tabla(s22, ["Pregunta", "Gráfico", "Uso"], [
    ["Comparación", "Barras horizontales", "Rankings de países, idiomas y artistas"],
    ["Composición", "Área y barras al 100 %", "Mezcla de formatos en el tiempo"],
    ["Distribución", "Histograma", "Duración en bandas de 30 s"],
    ["Relación", "Dispersión logarítmica", "Volumen contra digitalización"],
  ], 0.6, 1.7, 7.75, [2.1, 2.65, 3.0], { alto: 0.72, tam: 15, nombre: "Gráficos por pregunta" });
  cifra(s22, 8.6, 1.8, 4.13, 2.2, C.accent1, "1 acento", "resalta lo importante; el resto queda suave", 34);
  cifra(s22, 8.6, 4.2, 4.13, 2.3, C.accent3, "Validada", "paleta revisada para daltonismo y contraste", 34);
  texto(s22, "Clasificación según el selector de gráficos de Andrew Abela.", 0.6, 5.75, 7.75, 0.5, { fontSize: 16, color: C.text2 });

  // ---------------------------------------------------------------- Cierre
  seccion("Cierre");
  const s23 = diapositiva("Límites", "Lo que este trabajo no resuelve",
    "Preferimos declarar los límites antes de que nos los pregunten. El dashboard no tiene el drill-down de Power BI y los Top no se recalculan con filtros. El reporte de Power BI ya apunta a Databricks, pero falta comprobar la carga completa. Las fechas anteriores a 1900 pasan a sin fecha, y no medimos el beneficio del liquid clustering ni el consumo de cuota.");
  [
    ["Datos", C.accent2, ["Fechas anteriores a 1900 van a «sin fecha»", `${num(m.especiales.pistas_fecha_futura)} pistas con años futuros`, "Niveles de calidad y categorías: criterio propio"]],
    ["Dashboard", C.accent1, ["Sin drill-down ni filtrado por clic", "Top N no se recalcula con filtros", "Tablas sin separador de miles"]],
    ["Sin medir", C.accent4, ["PostgreSQL contra Spark", "Beneficio del liquid clustering", "Cuota usada y Power BI con 11,5 M"]],
  ].forEach(([t, c, items], i) => {
    const x = 0.6 + i * 4.12;
    tarjeta(s23, x, 1.75, 3.89, 3.95, c, t);
    texto(s23, t, x + 0.28, 1.95, 3.3, 0.5, { fontSize: 22, bold: true, fontFace: "Cambria" });
    texto(s23, lista(items), x + 0.28, 2.55, 3.35, 3.0, { fontSize: 18 });
  });
  tarjeta(s23, 0.6, 5.9, 12.13, 0.8, C.accent5, "Estado de Power BI");
  texto(s23, [{ text: "Power BI ya apunta a Databricks, sin carga completa comprobada. ", options: { bold: true } }, { text: "El dashboard vigente con datos completos es AI/BI." }], 0.88, 5.9, 11.6, 0.8, { fontSize: 18, valign: "middle" });

  const s24 = diapositiva("Conclusiones", "Conclusiones y próximos pasos",
    "Cerramos con lo esencial. El requisito está cumplido con datos reales y validados. Las nuevas cifras corrigen conclusiones anteriores. Y el proceso mostró que la validación de integridad no basta: hay que revisar el significado de los datos. Como siguiente paso, falta comprobar la carga completa en Power BI y medir lo que quedó pendiente.");
  texto(s24, "Conclusiones", 0.6, 1.72, 7.2, 0.45, { fontSize: 22, bold: true, fontFace: "Cambria" });
  const concl = [
    [fa.FaCheckCircle, C.accent3, `Requisito cumplido: ${num(T.pistas)} pistas reales`],
    [fa.FaSyncAlt, C.accent1, "Los resultados corrigen conclusiones anteriores"],
    [fa.FaEye, C.accent4, "Validar integridad no basta: también el significado"],
  ];
  for (let i = 0; i < concl.length; i++) {
    const y = 2.35 + i * 1.42;
    await iconoCirculo(s24, concl[i][0], 0.6, y, 0.95, concl[i][1]);
    texto(s24, concl[i][2], 1.8, y, 6.0, 0.95, { fontSize: 20, valign: "middle" });
  }
  tarjeta(s24, 8.15, 1.75, 4.58, 4.9, C.accent5, "Próximos pasos");
  texto(s24, "Próximos pasos", 8.45, 2.0, 4, 0.45, { fontSize: 22, bold: true, fontFace: "Cambria" });
  texto(s24, lista(["Validar la carga en Power BI", "Medir PostgreSQL contra Spark", "Medir el liquid clustering", "Agregar drill-down al dashboard"], { paraSpaceAfter: 16 }), 8.45, 2.75, 4.0, 3.6, { fontSize: 20 });

  await pres.writeFile({ fileName: SALIDA });
  if (process.env.PPTX_APPLY_THEME) {
    const { applyTheme } = require(process.env.PPTX_APPLY_THEME);
    await applyTheme(SALIDA, THEME);
  }
  console.log(`[OK] ${SALIDA}`);
}

construir().catch((e) => { console.error(e); process.exit(1); });
