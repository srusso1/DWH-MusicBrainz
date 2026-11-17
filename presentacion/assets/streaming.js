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
    [pick("productor.eventos_entregados", "eventos_producidos"), "eventos publicados en Kafka, 0 fallidos"],
    [pick("consumidos_validos"), "eventos válidos procesados por Spark"],
    [pick("enviados_dlq"), "eventos inválidos enviados a la DLQ"],
    [pick("postgres.filas_lanzamientos_evento"), "filas en PostgreSQL tras matar Spark, 0 duplicados"],
  ];

  document.querySelectorAll("[data-stream-stats]").forEach((box) => {
    box.innerHTML = items
      .map(([v, l], i) => `<div class="card stat r-scale" style="--i:${i + 2}"><div class="num sm">${v == null ? "—" : es(v)}</div><div class="lbl">${l}</div></div>`)
      .join("");
  });

  const R = S.prueba_reinicio || {};
  const lat = (S.postgres && S.postgres.latencia_extremo_a_extremo_s) || {};
  const fecha = (S.timestamp || "").slice(0, 10);
  const note = S.ejecutado
    ? `<b class="ok">Demo ejecutada</b> el ${fecha}. ` +
      (R.ejecutada
        ? `Matamos Spark con SIGKILL a mitad del flujo con ${es(R.filas_postgres_al_matar)} filas escritas; al reiniciar desde el checkpoint terminó en ${es(R.filas_postgres_final)} de ${es(R.esperadas)} y ${es(R.duplicados_mbid)} duplicados. `
        : "") +
      (lat.p50 != null ? `Latencia mediana de punta a punta: ${String(lat.p50).replace(".", ",")} s, con micro-lotes cada 10 s.` : "")
    : `<b class="coral">Pendiente.</b> La demo aún no se ha ejecutado en este equipo${S.motivo ? `: ${S.motivo}` : ""}. Se corre con <code>streaming/demo.sh</code>.`;
  document.querySelectorAll("[data-stream-note]").forEach((el) => (el.innerHTML = note));
})();
