-- ============================================================================
-- POBLADO DE DIMENSIÓN CONFORMADA: gold.dim_geography
-- ============================================================================

-- Registro para geografías no especificadas o nulas (Clave 0)
INSERT INTO gold.dim_geography (
    geo_key, area_id, area_gid, area_name, area_type, country_name
) VALUES (
    0, 0, '00000000-0000-0000-0000-000000000000'::UUID, 'Sin Área Registrada', 'Desconocido', 'Sin País Registrado'
) ON CONFLICT (area_id) DO NOTHING;

-- Poblado masivo desde silver.area
INSERT INTO gold.dim_geography (
    area_id,
    area_gid,
    area_name,
    area_type,
    country_name
)
SELECT 
    a.id AS area_id,
    a.gid AS area_gid,
    a.name AS area_name,
    CASE a.type
        WHEN 1 THEN 'País'
        WHEN 2 THEN 'Subdivisión'
        WHEN 3 THEN 'Condado'
        WHEN 4 THEN 'Municipio'
        WHEN 5 THEN 'Ciudad'
        WHEN 6 THEN 'Distrito'
        WHEN 7 THEN 'Isla'
        ELSE 'Otro / No Clasificado'
    END AS area_type,
    CASE 
        WHEN a.type = 1 THEN a.name 
        ELSE 'No Aplica' 
    END AS country_name
FROM silver.area a
ON CONFLICT (area_id) DO NOTHING;