-- ============================================================================
-- POBLADO DE DIMENSIÓN CONFORMADA: gold.dim_release
-- ============================================================================

-- Registro para release no especificado o desconocido (Clave 0)
INSERT INTO gold.dim_release (
    release_key, release_id, release_gid, release_name, 
    release_status, packaging_type, barcode, quality
) VALUES (
    0, 0, '00000000-0000-0000-0000-000000000000'::UUID, 'Lanzamiento Desconocido',
    'Desconocido', 'Desconocido', 'N/A', 'Normal'
) ON CONFLICT (release_id) DO NOTHING;

-- Poblado masivo desde silver.release
INSERT INTO gold.dim_release (
    release_id,
    release_gid,
    release_name,
    release_status,
    packaging_type,
    barcode,
    quality
)
SELECT 
    r.id AS release_id,
    r.gid AS release_gid,
    COALESCE(NULLIF(TRIM(r.name), ''), 'Sin Título') AS release_name,
    CASE r.status
        WHEN 1 THEN 'Oficial'
        WHEN 2 THEN 'Promocional'
        WHEN 3 THEN 'Bootleg / No Oficial'
        WHEN 4 THEN 'Pseudo-Release'
        ELSE 'No Clasificado'
    END AS release_status,
    CASE r.packaging
        WHEN 1 THEN 'Jewel Case'
        WHEN 2 THEN 'Slim Jewel Case'
        WHEN 3 THEN 'Digipak'
        WHEN 4 THEN 'Cardboard Sleeve / Funda'
        WHEN 5 THEN 'Otro Embalaje'
        WHEN 6 THEN 'Keep Case'
        WHEN 7 THEN 'Sin Embalaje (Digital)'
        WHEN 8 THEN 'Gatefold Cover (Vinilo)'
        ELSE 'Estándar / Desconocido'
    END AS packaging_type,
    NULLIF(TRIM(r.barcode), '') AS barcode,
    CASE r.quality
        WHEN -1 THEN 'Baja'
        WHEN 1 THEN 'Alta'
        WHEN 2 THEN 'Desconocida'
        ELSE 'Normal'
    END AS quality
FROM silver.release r
ON CONFLICT (release_id) DO NOTHING;