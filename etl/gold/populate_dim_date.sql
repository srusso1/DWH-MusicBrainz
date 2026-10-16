-- ============================================================================
-- POBLADO DE DIMENSIÓN CONFORMADA: gold.dim_fecha (1900 a 2030)
-- ============================================================================

-- Registro especial para fechas desconocidas (Clave 0)
INSERT INTO gold.dim_fecha (
    fecha_key, fecha_completa, anio, trimestre, nombre_trimestre, 
    mes, nombre_mes, nombre_mes_corto, dia, 
    dia_semana, nombre_dia, es_fin_de_semana, decada, siglo
) VALUES (
    0, NULL, 0, 0, 'N/A', 
    0, 'Sin Fecha', 'N/A', 0, 
    0, 'Sin Fecha', FALSE, 'Sin Década', 'Sin Siglo'
) ON CONFLICT (fecha_key) DO NOTHING;

-- Generación de series de fechas desde 1900-01-01 hasta 2030-12-31 (47,847 días)
INSERT INTO gold.dim_fecha (
    fecha_key,
    fecha_completa,
    anio,
    trimestre,
    nombre_trimestre,
    mes,
    nombre_mes,
    nombre_mes_corto,
    dia,
    dia_semana,
    nombre_dia,
    es_fin_de_semana,
    decada,
    siglo
)
SELECT 
    TO_CHAR(d, 'YYYYMMDD')::INTEGER AS fecha_key,
    d::DATE AS fecha_completa,
    EXTRACT(YEAR FROM d)::INTEGER AS anio,
    EXTRACT(QUARTER FROM d)::INTEGER AS trimestre,
    'Q' || EXTRACT(QUARTER FROM d)::TEXT AS nombre_trimestre,
    EXTRACT(MONTH FROM d)::INTEGER AS mes,
    CASE EXTRACT(MONTH FROM d)::INTEGER
        WHEN 1 THEN 'Enero' WHEN 2 THEN 'Febrero' WHEN 3 THEN 'Marzo'
        WHEN 4 THEN 'Abril' WHEN 5 THEN 'Mayo' WHEN 6 THEN 'Junio'
        WHEN 7 THEN 'Julio' WHEN 8 THEN 'Agosto' WHEN 9 THEN 'Septiembre'
        WHEN 10 THEN 'Octubre' WHEN 11 THEN 'Noviembre' WHEN 12 THEN 'Diciembre'
    END AS nombre_mes,
    CASE EXTRACT(MONTH FROM d)::INTEGER
        WHEN 1 THEN 'Ene' WHEN 2 THEN 'Feb' WHEN 3 THEN 'Mar'
        WHEN 4 THEN 'Abr' WHEN 5 THEN 'May' WHEN 6 THEN 'Jun'
        WHEN 7 THEN 'Jul' WHEN 8 THEN 'Ago' WHEN 9 THEN 'Sep'
        WHEN 10 THEN 'Oct' WHEN 11 THEN 'Nov' WHEN 12 THEN 'Dic'
    END AS nombre_mes_corto,
    EXTRACT(DAY FROM d)::INTEGER AS dia,
    EXTRACT(ISODOW FROM d)::INTEGER AS dia_semana,
    CASE EXTRACT(ISODOW FROM d)::INTEGER
        WHEN 1 THEN 'Lunes' WHEN 2 THEN 'Martes' WHEN 3 THEN 'Miércoles'
        WHEN 4 THEN 'Jueves' WHEN 5 THEN 'Viernes' WHEN 6 THEN 'Sábado'
        WHEN 7 THEN 'Domingo'
    END AS nombre_dia,
    CASE WHEN EXTRACT(ISODOW FROM d) IN (6, 7) THEN TRUE ELSE FALSE END AS es_fin_de_semana,
    (FLOOR(EXTRACT(YEAR FROM d) / 10) * 10)::TEXT || 's' AS decada,
    CASE 
        WHEN EXTRACT(YEAR FROM d) < 2000 THEN 'Siglo XX' 
        ELSE 'Siglo XXI' 
    END AS siglo
FROM GENERATE_SERIES('1900-01-01'::DATE, '2030-12-31'::DATE, '1 day'::INTERVAL) AS s(d)
ON CONFLICT (fecha_key) DO NOTHING;