-- ============================================================================
-- POBLADO DE DIMENSIÓN CONFORMADA: gold.dim_lanzamiento (Perfil de Lanzamiento)
-- Agrupa las combinaciones únicas de Estado Comercial, Empaque y Calidad
-- para permitir que la tabla de hechos consolide múltiples lanzamientos por día.
-- ============================================================================

-- Registro para perfil de lanzamiento desconocido o no especificado (Clave 0)
INSERT INTO gold.dim_lanzamiento (
    lanzamiento_key, estado_id, empaque_id, calidad_id,
    estado_lanzamiento, tipo_empaque, calidad_datos
) VALUES (
    0, 0, 0, 0,
    'No Clasificado', 'Estándar / Desconocido', 'Normal'
) ON CONFLICT (estado_id, empaque_id, calidad_id) DO NOTHING;

-- Poblado de todos los perfiles únicos de lanzamientos presentes en silver.release
INSERT INTO gold.dim_lanzamiento (
    estado_id,
    empaque_id,
    calidad_id,
    estado_lanzamiento,
    tipo_empaque,
    calidad_datos
)
SELECT DISTINCT
    COALESCE(r.status, 0) AS estado_id,
    COALESCE(r.packaging, 0) AS empaque_id,
    COALESCE(r.quality, 0) AS calidad_id,
    CASE COALESCE(r.status, 0)
        WHEN 1 THEN 'Oficial'
        WHEN 2 THEN 'Promocional'
        WHEN 3 THEN 'Bootleg / No Oficial'
        WHEN 4 THEN 'Pseudo-Release'
        WHEN 5 THEN 'Retirado / Withdrawn'
        WHEN 6 THEN 'Cancelado'
        ELSE 'No Clasificado'
    END AS estado_lanzamiento,
    CASE COALESCE(r.packaging, 0)
        WHEN 1 THEN 'Jewel Case'
        WHEN 2 THEN 'Slim Jewel Case'
        WHEN 3 THEN 'Digipak'
        WHEN 4 THEN 'Cardboard Sleeve / Funda'
        WHEN 5 THEN 'Otro Embalaje'
        WHEN 6 THEN 'Keep Case'
        WHEN 7 THEN 'Sin Embalaje (Digital)'
        WHEN 8 THEN 'Gatefold Cover (Vinilo)'
        ELSE 'Estándar / Desconocido'
    END AS tipo_empaque,
    CASE COALESCE(r.quality, 0)
        WHEN -1 THEN 'Baja'
        WHEN 1 THEN 'Alta'
        WHEN 2 THEN 'Desconocida'
        ELSE 'Normal'
    END AS calidad_datos
FROM silver.release r
ON CONFLICT (estado_id, empaque_id, calidad_id) DO UPDATE
SET estado_lanzamiento = EXCLUDED.estado_lanzamiento,
    tipo_empaque = EXCLUDED.tipo_empaque,
    calidad_datos = EXCLUDED.calidad_datos;