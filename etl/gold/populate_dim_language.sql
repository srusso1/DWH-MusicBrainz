-- ============================================================================
-- POBLADO DE DIMENSIÓN CONFORMADA: gold.dim_idioma
-- ============================================================================
-- Fuente de verdad: catálogo oficial silver.language (volcado MusicBrainz).
-- Se reemplazó el CASE con IDs escritos a mano porque los IDs no coincidían
-- con el catálogo real (p. ej. 198 = Japanese, no Húngaro; 393 = Spanish).

-- Registro para idioma no especificado o nulo (Clave 0).
-- DO UPDATE corrige cargas previas que lo renombraron como 'Otro Idioma (0)'.
INSERT INTO gold.dim_idioma (idioma_key, idioma_id, nombre_idioma, codigo_iso)
VALUES (0, 0, 'Idioma No Especificado', 'und')
ON CONFLICT (idioma_id) DO UPDATE
SET nombre_idioma = EXCLUDED.nombre_idioma,
    codigo_iso = EXCLUDED.codigo_iso;

-- Idiomas usados por los lanzamientos, resueltos contra el catálogo oficial.
-- ON CONFLICT actualiza nombre/código (SCD Tipo 1) sin alterar idioma_key,
-- por lo que la tabla de hechos no requiere recarga.
INSERT INTO gold.dim_idioma (idioma_id, nombre_idioma, codigo_iso)
SELECT DISTINCT
    rel.language AS idioma_id,
    COALESCE(lang.name, 'Idioma Desconocido (' || rel.language::TEXT || ')') AS nombre_idioma,
    COALESCE(lang.iso_code_3, lang.iso_code_2t, 'und') AS codigo_iso
FROM silver.release rel
LEFT JOIN silver.language lang ON lang.id = rel.language
WHERE rel.language IS NOT NULL
ON CONFLICT (idioma_id) DO UPDATE
SET nombre_idioma = EXCLUDED.nombre_idioma,
    codigo_iso = EXCLUDED.codigo_iso;
