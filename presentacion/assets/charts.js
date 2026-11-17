/* =====================================================================
   Chart definitions. Each builder receives window.M (real pipeline metrics)
   and returns a Chart.js config. Charts are rebuilt each time a slide is shown.
   ===================================================================== */
(() => {
  "use strict";
  if (!window.Chart) return;

  const C = {
    gold: "#d9b26f", gold2: "#f3d79f", teal: "#57c7b5", blue: "#6fa8e8", coral: "#e7836b",
    violet: "#a594ea", muted: "#9aa3b2", faint: "rgba(255,255,255,.07)", soft: "rgba(154,163,178,.35)",
  };
  Chart.defaults.color = C.muted;
  Chart.defaults.font.family = "Manrope, system-ui, sans-serif";
  Chart.defaults.font.size = 15;
  Chart.defaults.borderColor = C.faint;
  Chart.defaults.animation.duration = 1400;
  Chart.defaults.animation.easing = "easeOutQuart";
  Chart.defaults.plugins.legend.labels.boxWidth = 14;
  Chart.defaults.plugins.legend.labels.boxHeight = 14;
  Chart.defaults.plugins.legend.labels.usePointStyle = true;
  Chart.defaults.plugins.tooltip.backgroundColor = "rgba(10,13,20,.95)";
  Chart.defaults.plugins.tooltip.borderColor = "rgba(217,178,111,.5)";
  Chart.defaults.plugins.tooltip.borderWidth = 1;
  Chart.defaults.plugins.tooltip.padding = 12;
  Chart.defaults.maintainAspectRatio = false;

  const es = (n, d = 0) => n.toLocaleString("es-CO", { minimumFractionDigits: d, maximumFractionDigits: d });
  const pct = (v) => `${es(v * 100, 0)} %`;

  /* Draws value labels on top of bars (no external plugin needed). */
  const labels = (formatter, color = "#efe9de") => ({
    id: "valueLabels",
    afterDatasetsDraw(chart) {
      const { ctx } = chart;
      ctx.save();
      ctx.fillStyle = color;
      ctx.font = "600 15px 'JetBrains Mono', monospace";
      chart.data.datasets.forEach((ds, di) => {
        const meta = chart.getDatasetMeta(di);
        if (meta.hidden) return;
        meta.data.forEach((el, i) => {
          const v = ds.data[i];
          const horizontal = chart.options.indexAxis === "y";
          ctx.textAlign = horizontal ? "left" : "center";
          ctx.textBaseline = horizontal ? "middle" : "bottom";
          const x = horizontal ? el.x + 10 : el.x;
          const y = horizontal ? el.y : el.y - 8;
          ctx.fillText(formatter(v, i), x, y);
        });
      });
      ctx.restore();
    },
  });

  const noGrid = { grid: { display: false }, border: { display: false } };
  const hidden = { display: false };

  window.CHARTS = {
    requisito: (M) => ({
      type: "bar",
      data: {
        labels: ["Carga anterior", "Requisito", "Volcado completo"],
        datasets: [{
          data: [M.carga_anterior.pistas / 1e6, 50, M.totales.pistas / 1e6],
          backgroundColor: [C.soft, "rgba(231,131,107,.55)", C.gold],
          borderRadius: 12, barPercentage: 0.62,
        }],
      },
      options: {
        layout: { padding: { top: 34 } },
        plugins: { legend: hidden, tooltip: { callbacks: { label: (c) => `${es(c.raw, 1)} M de pistas` } } },
        scales: { x: { ...noGrid, ticks: { font: { size: 17 } } }, y: hidden },
      },
      plugins: [labels((v) => `${es(v, 1)} M`)],
    }),

    capacidad: (M) => {
      const cap = M.prueba_capacidad;
      const sum = (p) => cap.filter((e) => e.etapa.startsWith(p)).reduce((a, e) => a + e.segundos, 0);
      const get = (n) => (cap.find((e) => e.etapa === n) || { segundos: 0 }).segundos;
      return {
        type: "bar",
        data: {
          labels: ["Bronze · 9 tablas", "Hecho con todos los joins", "Validaciones", "Agregación"],
          datasets: [{ data: [sum("bronze."), get("gold.spike_fact_pista"), get("checks.fact"), get("query.year_format")].map(Math.round), backgroundColor: [C.blue, C.gold, C.teal, C.violet], borderRadius: 10, barPercentage: 0.6 }],
        },
        options: {
          indexAxis: "y", layout: { padding: { right: 70 } },
          plugins: { legend: hidden },
          scales: { x: hidden, y: { ...noGrid, ticks: { font: { size: 17 }, color: "#efe9de" } } },
        },
        plugins: [labels((v) => `${v} s`)],
      };
    },

    orquestacion: (M) => {
      const nombres = { pruebas: "Pruebas", bronze: "Bronze", silver: "Silver", catalogos: "Catálogos", gold_dimensiones: "Dimensiones", gold_fact_pista: "Hecho de pista", gold_agregados: "Agregados", validacion: "Validación" };
      const tareas = Object.keys(nombres).map((k) => M.corridas.completa.tareas.find((t) => t.tarea === k)).filter(Boolean);
      return {
        type: "bar",
        data: {
          labels: tareas.map((t) => nombres[t.tarea]),
          datasets: [{ data: tareas.map((t) => t.segundos), backgroundColor: tareas.map((_, i) => [C.teal, C.blue, C.violet, C.gold, C.coral][i % 5]), borderRadius: 10, barPercentage: 0.62 }],
        },
        options: {
          indexAxis: "y", layout: { padding: { right: 70 } },
          plugins: { legend: hidden },
          scales: { x: hidden, y: { ...noGrid, ticks: { font: { size: 17 }, color: "#efe9de" } } },
        },
        plugins: [labels((v) => `${v} s`)],
      };
    },

    formatos: (M) => {
      const datos = M.formatos.slice(0, 6);
      return {
        type: "doughnut",
        data: {
          labels: datos.map((f) => f.categoria),
          datasets: [{ data: datos.map((f) => f.lanzamientos), backgroundColor: [C.gold, C.blue, C.teal, C.soft, C.violet, C.coral], borderColor: "#07090f", borderWidth: 4, hoverOffset: 10 }],
        },
        options: {
          cutout: "66%",
          plugins: {
            legend: { position: "right", labels: { color: "#efe9de", font: { size: 16 }, padding: 16 } },
            tooltip: { callbacks: { label: (c) => ` ${es(c.raw)} lanzamientos` } },
          },
        },
      };
    },

    digital_optico: (M) => {
      const serie = M.anual.filter((a) => a.anio >= 1980);
      const ds = (label, key, color, fill) => ({
        label, data: serie.map((a) => a[key]), borderColor: color, backgroundColor: fill || "transparent", fill: !!fill,
        tension: 0.35, borderWidth: 3.5, pointRadius: 0, pointHoverRadius: 6,
      });
      return {
        type: "line",
        data: {
          labels: serie.map((a) => a.anio),
          datasets: [
            ds("Digital", "digital", C.gold, "rgba(217,178,111,.12)"),
            ds("Óptico (CD, DVD y similares)", "optico", C.blue),
            ds("Vinilo", "vinilo", C.teal),
          ],
        },
        options: {
          interaction: { mode: "index", intersect: false },
          plugins: { legend: { position: "top", align: "start", labels: { color: "#efe9de", font: { size: 16 } } }, tooltip: { callbacks: { label: (c) => ` ${c.dataset.label}: ${pct(c.raw)}` } } },
          scales: {
            x: { ...noGrid, ticks: { maxTicksLimit: 10 } },
            y: { min: 0, max: 1, ticks: { callback: (v) => pct(v), stepSize: 0.25 }, border: { display: false } },
          },
        },
      };
    },

    histograma: (M) => {
      const b = M.histograma.bandas;
      const top = b.slice().sort((x, y) => y.pistas - x.pistas).slice(0, 2).map((x) => x.banda);
      return {
        type: "bar",
        data: {
          labels: b.map((x) => x.banda.split("–")[0]),
          datasets: [{ data: b.map((x) => x.pistas / 1e6), backgroundColor: b.map((x) => (top.includes(x.banda) ? C.gold : "rgba(111,168,232,.45)")), borderRadius: 5, barPercentage: 0.92, categoryPercentage: 0.95 }],
        },
        options: {
          plugins: { legend: hidden, tooltip: { callbacks: { title: (c) => b[c[0].dataIndex].banda, label: (c) => ` ${es(c.raw, 2)} M de pistas` } } },
          scales: {
            x: { ...noGrid, title: { display: true, text: "Inicio de la banda (min:s)", color: C.muted }, ticks: { maxRotation: 0, autoSkip: true, maxTicksLimit: 12 } },
            y: { border: { display: false }, title: { display: true, text: "Millones de pistas", color: C.muted } },
          },
        },
      };
    },

    paises: (M) => {
      const top = [{ pais: "[Worldwide]", lanzamientos: M.especiales.lanzamientos_worldwide }, ...M.paises.slice(0, 7)];
      return {
        type: "bar",
        data: {
          labels: top.map((p) => p.pais),
          datasets: [{ data: top.map((p) => p.lanzamientos), backgroundColor: top.map((_, i) => (i === 0 ? C.gold : i === 1 ? C.blue : "rgba(111,168,232,.4)")), borderRadius: 8, barPercentage: 0.7 }],
        },
        options: {
          indexAxis: "y", layout: { padding: { right: 110 } },
          plugins: { legend: hidden },
          scales: { x: hidden, y: { ...noGrid, ticks: { font: { size: 17 }, color: "#efe9de" } } },
        },
        plugins: [labels((v) => es(v))],
      };
    },

    isrc: (M) => ({
      type: "bar",
      data: {
        labels: M.decadas.map((d) => d.decada),
        datasets: [{ data: M.decadas.map((d) => d.isrc), backgroundColor: M.decadas.map((d, i, a) => (i === a.length - 1 ? C.gold : "rgba(165,148,234,.55)")), borderRadius: 10, barPercentage: 0.6 }],
      },
      options: {
        layout: { padding: { top: 34 } },
        plugins: { legend: hidden },
        scales: { x: { ...noGrid, ticks: { font: { size: 17 } } }, y: hidden },
      },
      plugins: [labels((v) => pct(v))],
    }),

    idiomas: (M) => ({
      type: "bar",
      data: {
        labels: M.idiomas.map((d) => d.idioma),
        datasets: [{ data: M.idiomas.map((d) => d.lanzamientos), backgroundColor: M.idiomas.map((_, i) => (i === 0 ? C.gold : "rgba(87,199,181,.5)")), borderRadius: 8, barPercentage: 0.7 }],
      },
      options: {
        indexAxis: "y", layout: { padding: { right: 110 } },
        plugins: { legend: hidden },
        scales: { x: { type: "logarithmic", display: false }, y: { ...noGrid, ticks: { color: "#efe9de" } } },
      },
      plugins: [labels((v) => es(v))],
    }),

    capas: (M) => ({
      type: "bar",
      data: {
        labels: ["Bronze", "Silver", "Gold · fact_pista"],
        datasets: [{
          data: [Object.values(M.conteos.bronze).reduce((a, b) => a + b, 0) / 1e6, M.conteos.silver_principales_total / 1e6, M.conteos.gold.fact_pista / 1e6],
          backgroundColor: ["#b0793f", "#c3ccd8", C.gold], borderRadius: 12, barPercentage: 0.6,
        }],
      },
      options: {
        layout: { padding: { top: 34 } },
        plugins: { legend: hidden },
        scales: { x: { ...noGrid, ticks: { font: { size: 17 }, color: "#efe9de" } }, y: hidden },
      },
      plugins: [labels((v) => `${es(v, 1)} M`)],
    }),
  };
})();
