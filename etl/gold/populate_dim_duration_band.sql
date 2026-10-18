-- ============================================================================
-- POBLADO DE DIMENSIÓN: gold.dim_rango_duracion
-- 20 bandas de 30 s (0:00–10:00), banda abierta 10:00+ y clave 0.
-- ============================================================================

INSERT INTO gold.dim_rango_duracion (rango_duracion_key, orden, etiqueta_rango, limite_inferior_seg, limite_superior_seg)
VALUES (0, 0, 'Sin duración', NULL, NULL)
ON CONFLICT (rango_duracion_key) DO UPDATE
SET orden = EXCLUDED.orden,
    etiqueta_rango = EXCLUDED.etiqueta_rango,
    limite_inferior_seg = EXCLUDED.limite_inferior_seg,
    limite_superior_seg = EXCLUDED.limite_superior_seg;

INSERT INTO gold.dim_rango_duracion (rango_duracion_key, orden, etiqueta_rango, limite_inferior_seg, limite_superior_seg)
SELECT
    n + 1 AS rango_duracion_key,
    n + 1 AS orden,
    (n * 30 / 60) || ':' || LPAD(((n * 30) % 60)::TEXT, 2, '0')
        || '–' || ((n + 1) * 30 / 60) || ':' || LPAD((((n + 1) * 30) % 60)::TEXT, 2, '0') AS etiqueta_rango,
    n * 30 AS limite_inferior_seg,
    (n + 1) * 30 AS limite_superior_seg
FROM generate_series(0, 19) AS n
UNION ALL
SELECT 21, 21, '10:00+', 600, NULL
ON CONFLICT (rango_duracion_key) DO UPDATE
SET orden = EXCLUDED.orden,
    etiqueta_rango = EXCLUDED.etiqueta_rango,
    limite_inferior_seg = EXCLUDED.limite_inferior_seg,
    limite_superior_seg = EXCLUDED.limite_superior_seg;
