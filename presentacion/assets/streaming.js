/* =====================================================================
   Fills the streaming evidence slides from window.M.streaming
   (docs/build/metricas_streaming.json). Never invents numbers: if the
   demo was not executed, the slide says so.
   ===================================================================== */
(() => {
  "use strict";
  const S = (window.M && window.M.streaming) || { ejecutado: false };
  const es = (n) => (typeof n === "number" ? n.toLocaleString("es-CO") : n);

  /* First key present wins, so the slide tolerates small naming differences. */
  const pick = (...keys) => {
    for (const k of keys) {
      const v = k.split(".").reduce((o, p) => (o == null ? o : o[p]), S);
      if (v != null) return v;
    }
    return null;
  };

  const items = [
    [pick("eventos_producidos", "producidos", "productor.enviados"), "eventos publicados en Kafka"],
    [pick("eventos_validos", "consumidos_validos", "consumidor.validos"), "eventos válidos procesados por Spark"],
    [pick("eventos_dlq", "enviados_dlq", "dlq"), "eventos inválidos enviados a la DLQ"],
    [pick("filas_postgres", "postgres.lanzamientos_evento", "filas_evento"), "filas en PostgreSQL tras el reinicio"],
  ];

  document.querySelectorAll("[data-stream-stats]").forEach((box) => {
    box.innerHTML = items
      .map(([v, l], i) => `<div class="card stat r-scale" style="--i:${i + 2}"><div class="num sm">${v == null ? "—" : es(v)}</div><div class="lbl">${l}</div></div>`)
      .join("");
  });

  const restart = pick("prueba_reinicio.resultado", "reinicio.resultado", "prueba_reinicio");
  const note = S.ejecutado
    ? `<b class="ok">Demo ejecutada</b> el ${S.generado_utc || S.timestamp || "día de la corrida"}. ` +
      (restart ? `Prueba de reinicio del consumidor: ${typeof restart === "string" ? restart : "sin duplicados"}.` : "")
    : `<b class="coral">Pendiente.</b> La demo aún no se ha ejecutado en este equipo${S.motivo ? `: ${S.motivo}` : ""}. Se corre con <code>streaming/demo.sh</code>.`;
  document.querySelectorAll("[data-stream-note]").forEach((el) => (el.innerHTML = note));
})();
