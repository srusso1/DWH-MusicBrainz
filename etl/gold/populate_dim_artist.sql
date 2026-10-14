-- ============================================================================
-- POBLADO DE DIMENSIÓN CONFORMADA: gold.dim_artist
-- ============================================================================

-- Registro para artista desconocido / no identificado (Clave 0)
INSERT INTO gold.dim_artist (
    artist_key, artist_id, artist_gid, artist_name, sort_name, 
    artist_type, gender, area_name, country_name, begin_year, end_year, is_ended
) VALUES (
    0, 0, '00000000-0000-0000-0000-000000000000'::UUID, 'Artista Desconocido', 'Artista Desconocido',
    'Desconocido', 'Desconocido', 'Sin Área Registrada', 'Sin País Registrado', NULL, NULL, FALSE
) ON CONFLICT (artist_id) DO NOTHING;

-- Poblado masivo desde silver.artist enriquecido con silver.area
INSERT INTO gold.dim_artist (
    artist_id,
    artist_gid,
    artist_name,
    sort_name,
    artist_type,
    gender,
    area_name,
    country_name,
    begin_year,
    end_year,
    is_ended
)
SELECT 
    a.id AS artist_id,
    a.gid AS artist_gid,
    COALESCE(NULLIF(TRIM(a.name), ''), 'Sin Nombre') AS artist_name,
    a.sort_name,
    CASE a.type
        WHEN 1 THEN 'Persona / Solista'
        WHEN 2 THEN 'Grupo / Banda'
        WHEN 3 THEN 'Otro'
        WHEN 4 THEN 'Personaje Ficticio'
        WHEN 5 THEN 'Orquesta'
        WHEN 6 THEN 'Coro'
        ELSE 'No Clasificado'
    END AS artist_type,
    CASE a.gender
        WHEN 1 THEN 'Masculino'
        WHEN 2 THEN 'Femenino'
        WHEN 3 THEN 'No Binario'
        WHEN 4 THEN 'Otro'
        ELSE 'Desconocido'
    END AS gender,
    COALESCE(ar.name, 'Sin Área Registrada') AS area_name,
    CASE 
        WHEN ar.type = 1 THEN ar.name
        ELSE 'No Aplica'
    END AS country_name,
    NULLIF(a.begin_date_year, 0) AS begin_year,
    NULLIF(a.end_date_year, 0) AS end_year,
    COALESCE(a.ended, FALSE) AS is_ended
FROM silver.artist a
LEFT JOIN silver.area ar ON a.area = ar.id
ON CONFLICT (artist_id) DO NOTHING;