-- ============================================================================
-- POBLADO DE DIMENSIÓN CONFORMADA: gold.dim_language
-- ============================================================================

-- Registro para idioma no especificado o nulo (Clave 0)
INSERT INTO gold.dim_language (language_key, language_id, language_name, iso_code)
VALUES (0, 0, 'Idioma No Especificado', 'und')
ON CONFLICT (language_id) DO NOTHING;

-- Mapeo estructurado de idiomas según estándar ISO 639-3 / MusicBrainz
INSERT INTO gold.dim_language (language_id, language_name, iso_code)
SELECT DISTINCT
    COALESCE(language, 0) AS language_id,
    CASE COALESCE(language, 0)
        WHEN 120 THEN 'Inglés'
        WHEN 402 THEN 'Español'
        WHEN 284 THEN 'Japonés'
        WHEN 152 THEN 'Alemán'
        WHEN 145 THEN 'Francés'
        WHEN 357 THEN 'Ruso'
        WHEN 228 THEN 'Italiano'
        WHEN 333 THEN 'Portugués'
        WHEN 486 THEN 'Chino'
        WHEN 238 THEN 'Coreano'
        WHEN 484 THEN 'Sin Contenido Lingüístico / Instrumental'
        WHEN 485 THEN 'Múltiples Idiomas'
        WHEN 480 THEN 'Indeterminado / Desconocido'
        WHEN 131 THEN 'Finés'
        WHEN 392 THEN 'Sueco'
        WHEN 313 THEN 'Polaco'
        WHEN 296 THEN 'Neerlandés'
        WHEN 311 THEN 'Noruego'
        WHEN 98  THEN 'Danés'
        WHEN 165 THEN 'Griego'
        WHEN 198 THEN 'Húngaro'
        WHEN 440 THEN 'Turco'
        WHEN 18  THEN 'Árabe'
        WHEN 182 THEN 'Hebreo'
        WHEN 180 THEN 'Hindi'
        ELSE 'Otro Idioma (' || COALESCE(language::TEXT, '0') || ')'
    END AS language_name,
    CASE COALESCE(language, 0)
        WHEN 120 THEN 'eng'
        WHEN 402 THEN 'spa'
        WHEN 284 THEN 'jpn'
        WHEN 152 THEN 'deu'
        WHEN 145 THEN 'fra'
        WHEN 357 THEN 'rus'
        WHEN 228 THEN 'ita'
        WHEN 333 THEN 'por'
        WHEN 486 THEN 'zho'
        WHEN 238 THEN 'kor'
        WHEN 484 THEN 'zxx'
        WHEN 485 THEN 'mul'
        WHEN 480 THEN 'und'
        ELSE 'und'
    END AS iso_code
FROM silver.release
ON CONFLICT (language_id) DO UPDATE
SET language_name = EXCLUDED.language_name,
    iso_code = EXCLUDED.iso_code;