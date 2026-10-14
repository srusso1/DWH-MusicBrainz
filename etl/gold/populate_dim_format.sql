-- ============================================================================
-- POBLADO DE DIMENSIÓN CONFORMADA: gold.dim_format
-- ============================================================================

-- Registro para formato desconocido o no especificado (Clave 0)
INSERT INTO gold.dim_format (format_key, format_id, format_name, category)
VALUES (0, 0, 'Formato No Especificado', 'Desconocido')
ON CONFLICT (format_id) DO NOTHING;

-- Mapeo estructurado de formatos según estándar MusicBrainz
INSERT INTO gold.dim_format (format_id, format_name, category)
SELECT DISTINCT
    COALESCE(format, 0) AS format_id,
    CASE COALESCE(format, 0)
        WHEN 1 THEN 'CD'
        WHEN 2 THEN 'DualDisc'
        WHEN 3 THEN 'LaserDisc'
        WHEN 4 THEN 'MiniDisc'
        WHEN 5 THEN 'HDCD'
        WHEN 6 THEN 'VCD'
        WHEN 7 THEN 'Vinilo'
        WHEN 8 THEN 'Cassette'
        WHEN 9 THEN 'Cartucho de 8 Pistas'
        WHEN 10 THEN 'DAT (Digital Audio Tape)'
        WHEN 11 THEN 'DCC'
        WHEN 12 THEN 'Digital Media'
        WHEN 13 THEN 'Ogg Vorbis'
        WHEN 14 THEN 'FLAC'
        WHEN 15 THEN 'MP3'
        WHEN 16 THEN 'AAC'
        WHEN 17 THEN 'WMA'
        WHEN 18 THEN 'WAV'
        WHEN 19 THEN 'SACD'
        WHEN 20 THEN 'Enhanced CD'
        WHEN 29 THEN 'Vinilo 7"'
        WHEN 30 THEN 'Vinilo 10"'
        WHEN 31 THEN 'Vinilo 12"'
        WHEN 33 THEN 'DVD-Video'
        WHEN 34 THEN 'VHS'
        WHEN 35 THEN 'DVD-Audio'
        WHEN 42 THEN 'Blu-ray'
        WHEN 54 THEN 'Archivos de Audio Lossless'
        ELSE 'Otro Formato (' || COALESCE(format::TEXT, '0') || ')'
    END AS format_name,
    CASE 
        WHEN COALESCE(format, 0) IN (12, 13, 14, 15, 16, 17, 18, 54) THEN 'Digital / Streaming'
        WHEN COALESCE(format, 0) IN (7, 29, 30, 31) THEN 'Físico / Vinilo'
        WHEN COALESCE(format, 0) IN (1, 2, 3, 4, 5, 6, 19, 20, 33, 35, 42) THEN 'Físico / Óptico'
        WHEN COALESCE(format, 0) IN (8, 9, 10, 11, 34) THEN 'Físico / Magnético'
        ELSE 'Otros Formatos'
    END AS category
FROM silver.medium
ON CONFLICT (format_id) DO UPDATE 
SET format_name = EXCLUDED.format_name,
    category = EXCLUDED.category;