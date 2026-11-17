/* =====================================================================
   Animated SVG architecture diagrams, injected into <div data-diagram="...">.
   Nodes pop in one after another; flows show moving packets (animateMotion).
   ===================================================================== */
(() => {
  "use strict";
  const COL = { gold: "#d9b26f", teal: "#57c7b5", blue: "#6fa8e8", coral: "#e7836b", violet: "#a594ea", bronze: "#c08a4e", silver: "#c3ccd8", muted: "#9aa3b2" };
  let seq = 0;

  const esc = (s) => String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;");

  /* A rounded node with a coloured top rule, a title and up to 2 subtitle lines. */
  function node(x, y, w, h, title, sub, color, i, extra = "") {
    const lines = (sub || "").split("\n").filter(Boolean);
    const ty = y + h / 2 - (lines.length ? 10 + lines.length * 9 : -7);
    return `<g class="node pop" style="--i:${i}">
      <rect x="${x}" y="${y}" width="${w}" height="${h}" rx="14" style="stroke:${color}55"/>
      <rect x="${x + 18}" y="${y}" width="${w - 36}" height="3" rx="1.5" fill="${color}"/>
      <text x="${x + w / 2}" y="${ty}" text-anchor="middle" font-size="19" font-weight="700">${esc(title)}</text>
      ${lines.map((l, k) => `<text x="${x + w / 2}" y="${ty + 26 + k * 21}" text-anchor="middle" font-size="15" fill="${COL.muted}">${esc(l)}</text>`).join("")}
      ${extra}
    </g>`;
  }

  /* Animated connector with travelling packets. */
  function flow(d, color, i, packets = 2, dur = 2.4) {
    const id = `p${++seq}`;
    let dots = "";
    for (let k = 0; k < packets; k++) {
      dots += `<circle r="5" fill="${color}" stroke="#07090f" stroke-width="2">
        <animateMotion dur="${dur}s" begin="${(k * dur) / packets}s" repeatCount="indefinite" rotate="auto"><mpath href="#${id}"/></animateMotion></circle>`;
    }
    return `<g class="pop" style="--i:${i}">
      <path id="${id}" d="${d}" fill="none" stroke="${color}" stroke-opacity=".25" stroke-width="2"/>
      <path d="${d}" class="flow" stroke="${color}" stroke-opacity=".75"/>
      ${dots}
    </g>`;
  }

  function region(x, y, w, h, label, color, i) {
    return `<g class="pop" style="--i:${i}">
      <rect x="${x}" y="${y}" width="${w}" height="${h}" rx="22" fill="${color}0d" stroke="${color}" stroke-opacity=".45" stroke-dasharray="6 7"/>
      <text x="${x + 22}" y="${y + 30}" class="lbl" style="fill:${color}">${esc(label)}</text>
    </g>`;
  }

  const svg = (vb, body) => `<svg class="diagram" viewBox="${vb}" role="img" preserveAspectRatio="xMidYMid meet">${body}</svg>`;

  const D = {
    /* Full Lambda architecture: batch layer (Databricks) + speed layer (Kafka -> Spark Streaming). */
    lambda: () => svg("0 0 1420 640", `
      ${region(230, 20, 860, 270, "Capa batch · Databricks · Spark + Delta Lake + Lakeflow Jobs", COL.gold, 0)}
      ${region(230, 330, 860, 290, "Capa de velocidad · Docker · Kafka + Spark Structured Streaming", COL.teal, 1)}
      ${node(10, 95, 190, 120, "Volcado oficial", "MusicBrainz · 7,7 GB\n11 tablas TSV", COL.violet, 2)}
      ${node(10, 420, 190, 120, "API MusicBrainz", "WS/2 en vivo\nlanzamientos reales", COL.violet, 3)}
      ${node(260, 95, 150, 120, "Volume", "Unity Catalog\narchivos crudos", COL.muted, 4)}
      ${node(440, 95, 150, 120, "Bronze", "copia fiel\ntodo como texto", COL.bronze, 5)}
      ${node(620, 95, 150, 120, "Silver", "tipos, escapes\ny calidad", COL.silver, 6)}
      ${node(800, 95, 260, 120, "Gold · estrella", "3 hechos · 7 dimensiones\n58,8 M de pistas", COL.gold, 7)}
      ${node(260, 420, 150, 120, "Productor", "Python\nidempotente", COL.coral, 8)}
      ${node(440, 405, 200, 150, "Kafka", "tópico de lanzamientos\n3 particiones", COL.teal, 9,
        [0, 1, 2].map((k) => `<rect x="${462 + k * 54}" y="510" width="46" height="12" rx="3" fill="${COL.teal}" opacity="${0.35 + k * 0.2}"/>`).join(""))}
      ${node(670, 420, 180, 120, "Spark Streaming", "from_json, ventanas\nwatermark", COL.gold, 10)}
      ${node(880, 360, 190, 76, "PostgreSQL", "esquema streaming", COL.blue, 11)}
      ${node(880, 452, 190, 76, "Lago Bronze", "parquet por fecha", COL.bronze, 12)}
      ${node(880, 544, 190, 66, "Tópico DLQ", "", COL.coral, 13)}
      ${node(1150, 160, 250, 130, "Dashboard AI/BI", "3 páginas · drill-down\nconsumo batch", COL.gold, 14)}
      ${node(1150, 420, 250, 130, "Consulta en vivo", "ventanas de 1 minuto\npor país y formato", COL.teal, 15)}
      ${flow("M200 155 H260", COL.violet, 16)}
      ${flow("M410 155 H440", COL.gold, 16)}
      ${flow("M590 155 H620", COL.gold, 17)}
      ${flow("M770 155 H800", COL.gold, 17)}
      ${flow("M1060 155 C1110 155 1100 225 1150 225", COL.gold, 18)}
      ${flow("M200 480 H260", COL.violet, 18)}
      ${flow("M410 480 H440", COL.coral, 19, 3, 1.6)}
      ${flow("M640 480 H670", COL.teal, 19, 3, 1.6)}
      ${flow("M850 470 C865 470 860 398 880 398", COL.blue, 20)}
      ${flow("M850 485 H880", COL.bronze, 20)}
      ${flow("M850 500 C865 500 860 577 880 577", COL.coral, 21, 1, 3)}
      ${flow("M1070 398 C1110 398 1110 485 1150 485", COL.teal, 21)}
    `),

    /* Batch DAG as orchestrated by Lakeflow Jobs. */
    batch: () => {
      const tareas = [
        ["Pruebas", "26 fixtures", COL.muted], ["Bronze", "11 tablas", COL.bronze], ["Silver", "tipos + calidad", COL.silver],
        ["Catálogos", "etiquetas oficiales", COL.violet], ["Dimensiones", "7 con fila 0", COL.blue], ["Hecho pista", "58,8 M filas", COL.gold],
        ["Agregados", "hechos + mv_*", COL.teal], ["Validación", "116 reglas", COL.coral],
      ];
      let body = region(10, 10, 1400, 330, "Lakeflow Job · 8 tareas encadenadas · auditoría en meta.etl_audit", COL.gold, 0);
      tareas.forEach(([t, s, c], i) => {
        const x = 40 + i * 172;
        body += node(x, 120, 146, 130, t, s, c, i + 1);
        if (i < tareas.length - 1) body += flow(`M${x + 146} 185 H${x + 172}`, COL.gold, i + 2, 1, 1.4);
      });
      return svg("0 0 1420 350", body);
    },

    /* Detailed streaming flow with fault-tolerance features. */
    streaming: () => svg("0 0 1420 560", `
      ${node(10, 200, 210, 150, "Productor", "acks=all · idempotente\nclave = MBID", COL.coral, 0)}
      ${region(270, 60, 400, 440, "Broker Kafka · KRaft", COL.teal, 1)}
      ${[0, 1, 2].map((k) => `<g class="pop" style="--i:${2 + k}">
          <rect x="300" y="${120 + k * 92}" width="340" height="70" rx="12" fill="#0e1420" stroke="${COL.teal}55"/>
          <text x="320" y="${150 + k * 92}" font-size="17" font-weight="700">Partición ${k}</text>
          ${Array.from({ length: 7 }, (_, j) => `<rect x="${430 + j * 28}" y="${132 + k * 92}" width="22" height="46" rx="4" fill="${COL.teal}" opacity="${0.15 + j * 0.11}"/>`).join("")}
        </g>`).join("")}
      ${node(300, 410, 340, 66, "Tópico DLQ · eventos inválidos", "", COL.coral, 5)}
      ${node(730, 170, 260, 210, "Spark Structured Streaming", "readStream kafka\nfrom_json + validación\nwatermark 2 min\nventana 1 min\ncheckpoints", COL.gold, 6)}
      ${node(1060, 60, 340, 110, "PostgreSQL · streaming", "UPSERT idempotente\nON CONFLICT", COL.blue, 7)}
      ${node(1060, 220, 340, 110, "Lago Bronze", "parquet particionado\npor fecha de ingesta", COL.bronze, 8)}
      ${node(1060, 380, 340, 110, "Checkpoints", "offsets + estado\nreanudación sin duplicados", COL.violet, 9)}
      ${flow("M220 275 H300", COL.coral, 10, 3, 1.6)}
      ${flow("M640 245 C690 245 690 275 730 275", COL.teal, 11, 3, 1.6)}
      ${flow("M860 380 C860 445 760 443 640 443", COL.coral, 12, 1, 2.6)}
      ${flow("M990 230 C1030 230 1020 115 1060 115", COL.blue, 13)}
      ${flow("M990 275 H1060", COL.bronze, 13)}
      ${flow("M990 330 C1030 330 1020 435 1060 435", COL.violet, 14, 1, 3)}
    `),

    /* Star schema: fact_pista in the centre, 7 conformed dimensions around it. */
    star: () => {
      const cx = 700, cy = 300;
      const dims = [
        ["dim_fecha", "47.848 días · 1900–2030"], ["dim_artista", "3,03 M artistas"], ["dim_lanzamiento", "314 perfiles"],
        ["dim_geografia", "120.121 áreas"], ["dim_formato", "115 formatos"], ["dim_idioma", "355 idiomas"], ["dim_rango_duracion", "22 bandas"],
      ];
      let body = "";
      dims.forEach(([t, s], i) => {
        const a = (-90 + i * (360 / dims.length)) * (Math.PI / 180);
        const x = cx + Math.cos(a) * 520, y = cy + Math.sin(a) * 230;
        body += `<line class="draw" style="--i:${i}" x1="${cx}" y1="${cy}" x2="${x}" y2="${y}" stroke="${COL.gold}" stroke-opacity=".5" stroke-width="2"/>`;
        body += node(x - 120, y - 42, 240, 84, t, s, COL.blue, i + 2);
      });
      body += `<g class="pop" style="--i:1">
        <circle cx="${cx}" cy="${cy}" r="120" fill="${COL.gold}14" stroke="${COL.gold}" stroke-width="2"/>
        <circle cx="${cx}" cy="${cy}" r="140" fill="none" stroke="${COL.gold}" stroke-opacity=".25" stroke-dasharray="3 8"/>
        <text x="${cx}" y="${cy - 14}" text-anchor="middle" font-size="26" font-weight="700" fill="${COL.gold}">fact_pista</text>
        <text x="${cx}" y="${cy + 16}" text-anchor="middle" font-size="16" fill="${COL.muted}">1 fila = 1 pista</text>
        <text x="${cx}" y="${cy + 40}" text-anchor="middle" font-size="16" fill="${COL.muted}">58.809.976 filas</text>
      </g>`;
      return svg("0 0 1400 600", body);
    },

    /* Medallion layers with what each one guarantees. */
    medallion: () => {
      const capas = [
        ["Bronze", "Copia fiel del volcado", "todo como texto · sin perder nada · reprocesable", COL.bronze],
        ["Silver", "Datos confiables", "tipos, escapes revertidos, 22 reglas S01–S02", COL.silver],
        ["Gold", "Listo para decidir", "estrella Kimball · 3 hechos · 7 dimensiones", COL.gold],
      ];
      let body = "";
      capas.forEach(([t, s, d, c], i) => {
        const x = 20 + i * 470;
        body += `<g class="pop" style="--i:${i * 2}">
          <rect x="${x}" y="40" width="420" height="280" rx="24" fill="${c}10" stroke="${c}" stroke-opacity=".6"/>
          <circle cx="${x + 60}" cy="100" r="26" fill="${c}"/>
          <text x="${x + 110}" y="110" font-size="34" font-weight="700" font-family="Fraunces, serif" fill="${c}">${t}</text>
          <text x="${x + 34}" y="190" font-size="23" font-weight="700">${s}</text>
          <foreignObject x="${x + 34}" y="210" width="360" height="90"><div xmlns="http://www.w3.org/1999/xhtml" style="color:#9aa3b2;font:17px/1.5 Manrope,sans-serif">${d}</div></foreignObject>
        </g>`;
        if (i < 2) body += flow(`M${x + 420} 180 H${x + 470}`, c, i * 2 + 1, 2, 1.4);
      });
      return svg("0 0 1420 340", body);
    },
  };

  document.querySelectorAll("[data-diagram]").forEach((el) => {
    const make = D[el.dataset.diagram];
    if (make) el.innerHTML = make();
  });
})();
