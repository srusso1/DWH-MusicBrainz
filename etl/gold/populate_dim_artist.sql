-- ============================================================================
-- POBLADO DE DIMENSIÓN CONFORMADA: gold.dim_artista
-- ============================================================================

-- Registro para artista desconocido / no identificado (Clave 0)
INSERT INTO gold.dim_artista (
    artista_key, artista_id, artista_gid, nombre_artista, nombre_orden, 
    tipo_artista, genero, area_id, nombre_area, nombre_pais, anio_inicio, anio_fin, finalizado
) VALUES (
    0, 0, '00000000-0000-0000-0000-000000000000'::UUID, 'Artista Desconocido', 'Artista Desconocido',
    'Desconocido', 'Desconocido', 0, 'Sin Área Registrada', 'Sin País Registrado', NULL, NULL, FALSE
) ON CONFLICT (artista_id) DO NOTHING;

-- Poblado masivo desde silver.artist enriquecido con silver.area por clave exacta
INSERT INTO gold.dim_artista (
    artista_id,
    artista_gid,
    nombre_artista,
    nombre_orden,
    tipo_artista,
    genero,
    area_id,
    nombre_area,
    nombre_pais,
    anio_inicio,
    anio_fin,
    finalizado
)
SELECT 
    a.id AS artista_id,
    a.gid AS artista_gid,
    COALESCE(NULLIF(TRIM(a.name), ''), 'Sin Nombre') AS nombre_artista,
    a.sort_name AS nombre_orden,
    CASE a.type
        WHEN 1 THEN 'Persona / Solista'
        WHEN 2 THEN 'Grupo / Banda'
        WHEN 3 THEN 'Otro'
        WHEN 4 THEN 'Personaje Ficticio'
        WHEN 5 THEN 'Orquesta'
        WHEN 6 THEN 'Coro'
        ELSE 'No Clasificado'
    END AS tipo_artista,
    CASE a.gender
        WHEN 1 THEN 'Masculino'
        WHEN 2 THEN 'Femenino'
        WHEN 3 THEN 'No Binario'
        WHEN 4 THEN 'Otro'
        ELSE 'Desconocido'
    END AS genero,
    COALESCE(a.area, 0) AS area_id,
    COALESCE(ar.name, 'Sin Área Registrada') AS nombre_area,
    CASE 
        WHEN ar.type = 1 THEN ar.name
        ELSE 'No Aplica'
    END AS nombre_pais,
    NULLIF(a.begin_date_year, 0) AS anio_inicio,
    NULLIF(a.end_date_year, 0) AS anio_fin,
    COALESCE(a.ended, FALSE) AS finalizado
FROM silver.artist a
LEFT JOIN silver.area ar ON a.area = ar.id
ON CONFLICT (artista_id) DO UPDATE
SET nombre_artista = EXCLUDED.nombre_artista,
    tipo_artista = EXCLUDED.tipo_artista,
    genero = EXCLUDED.genero,
    area_id = EXCLUDED.area_id,
    nombre_area = EXCLUDED.nombre_area,
    nombre_pais = EXCLUDED.nombre_pais;