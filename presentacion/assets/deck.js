/* =====================================================================
   DWMusicBrainz · Presentation controller
   - Scales a fixed 1600x900 stage to the viewport
   - Keyboard, wheel, touch and click navigation; hash routing (#/n)
   - Step fragments (.f), animated counters ([data-count]), lazy charts ([data-chart])
   - Speaker notes (N), overview (O), fullscreen (F), print to PDF (Ctrl+P)
   ===================================================================== */
(() => {
  "use strict";

  const deck = document.querySelector(".deck");
  const slides = Array.from(deck.querySelectorAll(":scope > .slide"));
  const bar = document.querySelector(".chrome .bar");
  const counter = document.querySelector(".hud .count");
  const notesPanel = document.querySelector(".notes-panel");
  const charts = new Map();
  let index = 0;
  let wheelLock = false;

  /* ---------- Formatting helpers (Spanish locale) ---------- */
  const fmt = {
    int: (n) => Math.round(n).toLocaleString("es-CO"),
    dec: (n, d = 1) => n.toLocaleString("es-CO", { minimumFractionDigits: d, maximumFractionDigits: d }),
  };
  window.FMT = fmt;

  /* ---------- Fill [data-m] bindings from window.M ---------- */
  const read = (path) => path.split(".").reduce((o, k) => (o == null ? o : o[k]), window.M);
  document.querySelectorAll("[data-m]").forEach((el) => {
    const v = read(el.dataset.m);
    if (v == null) return;
    const kind = el.dataset.fmt || "int";
    el.textContent =
      kind === "pct" ? `${fmt.dec(v * 100, +(el.dataset.d || 1))} %`
      : kind === "mill" ? `${fmt.dec(v / 1e6, +(el.dataset.d || 1))} M`
      : kind === "dec" ? fmt.dec(v, +(el.dataset.d || 1))
      : kind === "raw" ? String(v)
      : fmt.int(v);
  });

  /* ---------- Stage scaling ---------- */
  function fit() {
    const s = Math.min(window.innerWidth / 1600, window.innerHeight / 900);
    document.documentElement.style.setProperty("--scale", s.toFixed(4));
  }

  /* ---------- Counters ---------- */
  function runCounters(slide) {
    slide.querySelectorAll("[data-count]").forEach((el) => {
      const target = parseFloat(el.dataset.count);
      const decimals = +(el.dataset.d || 0);
      const suffix = el.dataset.suffix || "";
      const start = performance.now();
      const dur = 1600;
      const reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;
      const step = (t) => {
        const p = reduce ? 1 : Math.min(1, (t - start) / dur);
        const eased = 1 - Math.pow(1 - p, 4);
        const v = target * eased;
        el.textContent = (decimals ? fmt.dec(v, decimals) : fmt.int(v)) + suffix;
        if (p < 1) requestAnimationFrame(step);
      };
      requestAnimationFrame(step);
    });
  }

  /* ---------- Charts (Chart.js, rebuilt on each visit so they animate) ---------- */
  function runCharts(slide) {
    if (!window.Chart || !window.CHARTS) return;
    slide.querySelectorAll("canvas[data-chart]").forEach((cv) => {
      const build = window.CHARTS[cv.dataset.chart];
      if (!build) return;
      if (charts.has(cv)) charts.get(cv).destroy();
      charts.set(cv, new Chart(cv, build(window.M)));
    });
  }

  /* ---------- Fragments ---------- */
  const frags = (slide) => Array.from(slide.querySelectorAll(".f"));
  const shown = (slide) => frags(slide).filter((f) => f.classList.contains("on")).length;

  function setNotes() {
    const n = slides[index].querySelector(".notes");
    notesPanel.innerHTML = `<h4>Notas del orador · ${index + 1}</h4>${n ? n.innerHTML : "<p>Sin notas.</p>"}`;
  }

  function go(i, fromBack = false) {
    i = Math.max(0, Math.min(slides.length - 1, i));
    slides.forEach((s, k) => {
      s.classList.toggle("active", k === i);
      s.classList.toggle("past", k < i);
      s.setAttribute("aria-hidden", k === i ? "false" : "true");
    });
    const changed = i !== index || !slides[i].dataset.seen;
    index = i;
    const fs = frags(slides[i]);
    fs.forEach((f) => f.classList.toggle("on", fromBack));
    if (changed) {
      slides[i].dataset.seen = "1";
      runCounters(slides[i]);
      runCharts(slides[i]);
    }
    bar.style.width = `${((i + 1) / slides.length) * 100}%`;
    counter.textContent = `${String(i + 1).padStart(2, "0")} / ${String(slides.length).padStart(2, "0")}`;
    history.replaceState(null, "", `#/${i + 1}`);
    setNotes();
  }

  function next() {
    const fs = frags(slides[index]);
    const n = shown(slides[index]);
    if (n < fs.length) { fs[n].classList.add("on"); return; }
    if (index < slides.length - 1) go(index + 1);
  }
  function prev() {
    const fs = frags(slides[index]);
    const n = shown(slides[index]);
    if (n > 0) { fs[n - 1].classList.remove("on"); return; }
    if (index > 0) go(index - 1, true);
  }

  /* ---------- Overview ---------- */
  function toggleOverview() {
    document.body.classList.toggle("overview");
    if (!document.body.classList.contains("overview")) fit();
  }
  slides.forEach((s, k) => s.addEventListener("click", () => {
    if (document.body.classList.contains("overview")) { toggleOverview(); go(k); }
  }));

  /* ---------- Input ---------- */
  document.addEventListener("keydown", (e) => {
    if (e.ctrlKey || e.metaKey || e.altKey) return;
    const k = e.key;
    if (["ArrowRight", "ArrowDown", "PageDown", " ", "Enter"].includes(k)) { e.preventDefault(); next(); }
    else if (["ArrowLeft", "ArrowUp", "PageUp", "Backspace"].includes(k)) { e.preventDefault(); prev(); }
    else if (k === "Home") go(0);
    else if (k === "End") go(slides.length - 1);
    else if (k === "n" || k === "N") notesPanel.classList.toggle("open");
    else if (k === "o" || k === "O" || k === "Escape") toggleOverview();
    else if (k === "f" || k === "F") {
      if (!document.fullscreenElement) document.documentElement.requestFullscreen?.();
      else document.exitFullscreen?.();
    }
  });

  window.addEventListener("wheel", (e) => {
    if (document.body.classList.contains("overview") || wheelLock || Math.abs(e.deltaY) < 30) return;
    wheelLock = true;
    setTimeout(() => (wheelLock = false), 650);
    e.deltaY > 0 ? next() : prev();
  }, { passive: true });

  let touchX = null, touchY = null;
  window.addEventListener("touchstart", (e) => { touchX = e.touches[0].clientX; touchY = e.touches[0].clientY; }, { passive: true });
  window.addEventListener("touchend", (e) => {
    if (touchX == null) return;
    const dx = e.changedTouches[0].clientX - touchX;
    const dy = e.changedTouches[0].clientY - touchY;
    if (Math.abs(dx) > 45 && Math.abs(dx) > Math.abs(dy)) (dx < 0 ? next : prev)();
    touchX = touchY = null;
  });

  document.querySelector("[data-act=prev]")?.addEventListener("click", prev);
  document.querySelector("[data-act=next]")?.addEventListener("click", next);
  document.querySelector("[data-act=notes]")?.addEventListener("click", () => notesPanel.classList.toggle("open"));
  document.querySelector("[data-act=grid]")?.addEventListener("click", toggleOverview);

  /* Print: show every chart before the browser lays out pages */
  window.addEventListener("beforeprint", () => slides.forEach((s) => { runCharts(s); s.querySelectorAll(".f").forEach((f) => f.classList.add("on")); }));

  window.DECK = { go: (n) => go(n - 1), total: slides.length };
  window.addEventListener("hashchange", () => {
    const n = parseInt((location.hash.match(/#\/(\d+)/) || [])[1], 10);
    if (Number.isFinite(n) && n - 1 !== index) go(n - 1);
  });
  window.addEventListener("resize", fit);
  fit();
  const fromHash = parseInt((location.hash.match(/#\/(\d+)/) || [])[1], 10);
  go(Number.isFinite(fromHash) ? fromHash - 1 : 0);
})();
