-- ============================================================================
-- POBLADO DE DIMENSIÓN CONFORMADA: gold.dim_date (1900 a 2030)
-- ============================================================================

-- Registro especial para fechas desconocidas (Clave 0)
INSERT INTO gold.dim_date (
    date_key, full_date, year, quarter, quarter_name, 
    month, month_name, month_name_short, day, 
    day_of_week, day_name, is_weekend, decade, century
) VALUES (
    0, NULL, 0, 0, 'N/A', 
    0, 'Sin Fecha', 'N/A', 0, 
    0, 'Sin Fecha', FALSE, 'Sin Década', 'Sin Siglo'
) ON CONFLICT (date_key) DO NOTHING;

-- Generación de series de fechas desde 1900-01-01 hasta 2030-12-31 (47,847 días)
INSERT INTO gold.dim_date (
    date_key,
    full_date,
    year,
    quarter,
    quarter_name,
    month,
    month_name,
    month_name_short,
    day,
    day_of_week,
    day_name,
    is_weekend,
    decade,
    century
)
SELECT 
    TO_CHAR(d, 'YYYYMMDD')::INTEGER AS date_key,
    d::DATE AS full_date,
    EXTRACT(YEAR FROM d)::INTEGER AS year,
    EXTRACT(QUARTER FROM d)::INTEGER AS quarter,
    'Q' || EXTRACT(QUARTER FROM d)::TEXT AS quarter_name,
    EXTRACT(MONTH FROM d)::INTEGER AS month,
    CASE EXTRACT(MONTH FROM d)::INTEGER
        WHEN 1 THEN 'Enero' WHEN 2 THEN 'Febrero' WHEN 3 THEN 'Marzo'
        WHEN 4 THEN 'Abril' WHEN 5 THEN 'Mayo' WHEN 6 THEN 'Junio'
        WHEN 7 THEN 'Julio' WHEN 8 THEN 'Agosto' WHEN 9 THEN 'Septiembre'
        WHEN 10 THEN 'Octubre' WHEN 11 THEN 'Noviembre' WHEN 12 THEN 'Diciembre'
    END AS month_name,
    CASE EXTRACT(MONTH FROM d)::INTEGER
        WHEN 1 THEN 'Ene' WHEN 2 THEN 'Feb' WHEN 3 THEN 'Mar'
        WHEN 4 THEN 'Abr' WHEN 5 THEN 'May' WHEN 6 THEN 'Jun'
        WHEN 7 THEN 'Jul' WHEN 8 THEN 'Ago' WHEN 9 THEN 'Sep'
        WHEN 10 THEN 'Oct' WHEN 11 THEN 'Nov' WHEN 12 THEN 'Dic'
    END AS month_name_short,
    EXTRACT(DAY FROM d)::INTEGER AS day,
    EXTRACT(ISODOW FROM d)::INTEGER AS day_of_week,
    CASE EXTRACT(ISODOW FROM d)::INTEGER
        WHEN 1 THEN 'Lunes' WHEN 2 THEN 'Martes' WHEN 3 THEN 'Miércoles'
        WHEN 4 THEN 'Jueves' WHEN 5 THEN 'Viernes' WHEN 6 THEN 'Sábado'
        WHEN 7 THEN 'Domingo'
    END AS day_name,
    CASE WHEN EXTRACT(ISODOW FROM d) IN (6, 7) THEN TRUE ELSE FALSE END AS is_weekend,
    (FLOOR(EXTRACT(YEAR FROM d) / 10) * 10)::TEXT || 's' AS decade,
    CASE 
        WHEN EXTRACT(YEAR FROM d) < 2000 THEN 'Siglo XX' 
        ELSE 'Siglo XXI' 
    END AS century
FROM GENERATE_SERIES('1900-01-01'::DATE, '2030-12-31'::DATE, '1 day'::INTERVAL) AS s(d)
ON CONFLICT (date_key) DO NOTHING;