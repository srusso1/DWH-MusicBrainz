# Prompt para Generación de Presentación en Gamma App

Este archivo contiene el prompt estructurado para generar las **13 diapositivas oficiales de sustentación** del Data Warehouse MusicBrainz en herramientas de Inteligencia Artificial como **Gamma App** (utilizando la opción *Create with AI* / *Text to Deck*).

---

```markdown
Crea una presentación profesional, ejecutiva y de altísimo nivel técnico de 13 diapositivas (formato panorámico 16:9) para la sustentación universitaria de nuestro proyecto integrador de Bases de Datos Avanzadas: "Data Warehouse Masivo de la Industria Musical (MusicBrainz)".

---

### INSTRUCCIONES DE ESTILO VISUAL Y DISEÑO (MANDATORIO)
- **Temática visual:** Fusión entre Ingeniería de Datos de alto rendimiento (Data Warehousing corporativo), Arquitectura de Software limpia y la Industria Musical Global (Streaming, sellos discográficos, formalización ISRC).
- **Paleta de colores:**
  - Color primario: Azul marino oscuro institucional (#0B192C / #1E3A8A).
  - Color secundario / acento tecnológico: Violeta eléctrico y Cian (#8B5CF6 / #06B6D4).
  - Acentos de alerta y métricas: Ámbar musical / Dorado de vinilo (#F59E0B).
  - Fondo: Modo oscuro elegante (Dark Mode profesional) con tarjetas de contraste en gris pizarra (#1E293B / #0F172A).
- **Elementos visuales e iconografía:** En cada diapositiva utiliza tarjetas visuales (cards), badges de métricas en negrita, diagramas de arquitectura y bloques de código/DDL. Incorpora íconos alusivos en cada sección:
  - 🎵 Música: Nota musical, vinilo, audífonos, disco compacto, onda sonora, micrófono.
  - 💾 Bases de datos e Infraestructura: Servidor, PostgreSQL 16, tablas particionadas, Docker, árboles B-Tree.
  - 📊 Power BI y Analítica: Gráficos de dispersión, correlación Pearson, KPIs ejecutivos, mapas de calor.
  - ⚙️ Ingeniería de datos: Pipeline ETL, engranajes, streaming COPY, checks de validación, terminal CLI.
- **Formato de texto:** Cero bloques densos de texto. Prioriza bullets concisos, tarjetas comparativas 2x2 o 3 columnas, números gigantes (Big Numbers) para métricas de estrés y diagramas de flujo.

---

### ESTRUCTURA DIAPOSITIVA POR DIAPOSITIVA (13 SLIDES)

#### DIAPOSITIVA 1: Portada Institucional
- **Título principal:** Data Warehouse Masivo de la Industria Musical (DWMusicBrainz)
- **Subtítulo:** Arquitectura Medallón en PostgreSQL 16 & Modelo en Estrella Puro (Ralph Kimball)
- **Badges destacados:**
  - 🐘 PostgreSQL 16 + Docker
  - ⚡ 100% Datos Reales MusicBrainz (0% Sintéticos)
  - 📈 19,37 Millones de Hechos Reales
  - 💾 17,77 GB de Almacenamiento Físico
  - 📊 Explotación Analítica en Power BI
- **Pie institucional:** Proyecto Integrador | Bases de Datos Avanzadas | 5to Semestre | Ingeniería de Sistemas | Universidad Popular del Cesar | Valledupar, 2026.

---

#### DIAPOSITIVA 2: Planteamiento del Problema: De la Fricción OLTP a la Analítica OLAP
- **Mensaje central:** "La industria musical produce millones de obras diarias, pero los modelos operacionales normalizados colapsan ante el análisis masivo de catálogo".
- **Comparativa visual (2 Columnas enfrentadas):**
  - **Tarjeta 1: El Cuello de Botella Operacional (OLTP)**
    - ❌ Modelo en 3NF con más de 7 tablas encadenadas para consultar un tema (`track -> recording -> medium -> release -> artist -> area -> isrc`).
    - ❌ Consultas analíticas pesadas que bloquean transacciones y agotan la memoria del motor.
    - ❌ JOINs masivos sobre más de 45 millones de filas que tardan minutos o fallan por timeout.
  - **Tarjeta 2: La Solución Data Warehouse (OLAP Medallón)**
    - ✅ Desnormalización dimensional bajo modelo en estrella de Kimball.
    - ✅ Grano atómico en la inclusión de pista/grabación en medium de release comercial.
    - ✅ Consultas sub-segundo optimizadas mediante particionamiento por rangos temporales e índices B-Tree.

---

#### DIAPOSITIVA 3: Objetivos y Requerimientos del Sistema (RF & RNF)
- **Objetivo General:** Construir y desplegar un DWH analítico empresarial con datos 100% reales de MusicBrainz que supere los 10 millones de hechos y 3 GB en disco.
- **Requerimientos Funcionales Clave (RF01 - RF08):**
  - 🏆 RF01: Ranking Top N de artistas y álbumes por volumen de temas y duración.
  - 📻 RF02: Comparativa de duración e idioma según formato (Vinilo vs CD vs Digital).
  - 🌍 RF03: Drill-down geográfico (Continente > País) y temporal (Década > Año).
  - ⏱️ RF04 & RF07: Proporción de canciones largas (`is_long_track > 300s`) y posición en disco.
  - 📉 RF05: Demostración matemática de cómo el streaming acortó la música (Correlación Pearson `corr()`).
  - 🔒 RF06 & RF08: Tasa de formalización discográfica ISRC y detección de nuevos talentos.
- **Requerimientos No Funcionales de Estrés (RNF):**
  - 💾 RNF02: > 3.0 GB en disco en PostgreSQL (**Logrado: 17,77 GB**).
  - 🚀 RNF03: > 10.000.000 de filas en la tabla de hechos central (**Logrado: 19.370.311 filas**).
  - 🎯 RNF08: Cero registros huérfanos entre hechos y dimensiones conformadas (**Logrado: 100% integridad**).

---

#### DIAPOSITIVA 4: Origen y Procedencia de los Datos (100% Reales)
- **Mensaje central:** "Reemplazo total de datos sintéticos: calidad, auditoría y escala corporativa real".
- **Fuente Oficial:** MusicBrainz Database Full Export (`mbdump.tar.bz2`), MetaBrainz Foundation.
- **Esquema de Origen (Schema Sequence 31):**
  - 📦 Archivo maestro de 7,09 GB comprimido.
  - 🔍 Tablas base extraídas: `track` (~45M), `recording` (~40M), `medium` (~6.4M), `release` (~5.8M), `artist` (~3M), `isrc` (~6.5M), `area` (120k).
- **Filosofía de Calidad:**
  - Cero generación aleatoria de datos ficticios. Cada ID, MBID (UUID), ISRC y duración corresponde a una obra musical registrada y auditada en el mundo real.

---

#### DIAPOSITIVA 5: Arquitectura Medallón (Silver -> Gold -> Meta)
- **Diagrama de Flujo Arquitectónico:**
  - 🥈 **Capa Silver (Staging 3NF):** 77,4 millones de filas. Tablas tipadas, strings extensos migrados a `TEXT`, codificación `utf-8-sig` saneada y normalización relacional limpia.
  - 🥇 **Capa Gold (Dimensional Kimball):** 28,4 millones de filas. 1 Hecho central (`fact_tracks`) + 6 dimensiones conformadas con Surrogate Keys + 4 Vistas Materializadas analíticas.
  - 🛡️ **Esquema Meta (Gobernanza y Auditoría):** Bitácora contable transversal en `meta.etl_audit` (lotes, timestamps, filas leídas, filas insertadas y tiempos de ejecución).

---

#### DIAPOSITIVA 6: El Grano Atómico y el Modelo en Estrella Puro
- **Declaración de Grano (Ralph Kimball):**
  - *"Una fila individual en la tabla de hechos representa la inclusión de una pista/grabación de audio dentro de un soporte físico o digital correspondiente a un release comercial oficial, en una fecha determinada y con un formato e idioma específicos."*
- **Estructura del Modelo:**
  - Centro: `gold.fact_tracks` (19.370.311 registros de hechos).
  - Dimensiones Conformadas:
    - `dim_date`: Calendario continuo diario (1900–2030, 47.848 filas).
    - `dim_artist`: 3.010.452 artistas con MBID, tipo, género y país.
    - `dim_release`: 5.844.570 lanzamientos comerciales con código de barras y calidad.
    - `dim_format`: 114 formatos (Vinilo, CD, Cassette, Digital Media).
    - `dim_geography`: 120.108 áreas geográficas normalizadas.
    - `dim_language`: 354 idiomas y alfabetos oficiales ISO.

---

#### DIAPOSITIVA 7: Claves Subrogadas y el Patrón Anti-Huérfanos "Key 0"
- **Innovación en Integridad Referencial:**
  - ¿Cómo evitar descartar transacciones cuando un dato dimensional viene ausente en el origen?
  - **Patrón de Fila Cero (`Key 0`):** Cada dimensión conformada contiene un registro sintético inicial con clave `0` (*"Desconocido / Sin Información"*).
  - En el ETL, los `COALESCE(dim_key, 0)` aseguran que ninguna pista quede huérfana.
- **Resultado Verificado en la Auditoría:**
  - ✅ Huérfanos en `dim_artist`: **0**
  - ✅ Huérfanos en `dim_release`: **0**
  - ✅ Huérfanos en `dim_date`: **0**
  - ✅ Huérfanos en `dim_format`: **0**
  - ✅ Huérfanos en `dim_geography`: **0**
  - ✅ Huérfanos en `dim_language`: **0**

---

#### DIAPOSITIVA 8: Pipeline ETL Masivo y Optimización de Ingesta
- **Reto de Alto Rendimiento:** ¿Cómo cargar 77 millones de registros sin saturar RAM ni disco?
- **Técnicas de Ingeniería Aplicadas:**
  1. **Streaming con `MaxLineReader`:** Buffer de 128 KB en Python para leer y transformar en flujo continuo sin cargar archivos gigantes en memoria.
  2. **Inserción a Heap sin Sobrecarga de Índices:** Se deshabilitan las claves primarias e índices B-Tree antes del `COPY FROM STDIN`, permitiendo tasas sostenidas de más de **160.000 filas por segundo**.
  3. **Reconstrucción Paralela de Índices:** Uso de `maintenance_work_mem = 1GB` y workers paralelos en PostgreSQL para crear el índice primario de 40.5 millones de filas en solo **65 segundos**.
  4. **Saneamiento Inmediato:** Eliminación de los archivos TSV descomprimidos tan pronto se cargan a Silver, recuperando más de 12.5 GB en disco duro.

---

#### DIAPOSITIVA 9: Catálogo de Reglas EDA y Calidad de Datos (E01 - E10)
- **Cuadrícula de Reglas Principales:**
  - ⏱️ **E01 (Duraciones nulas o en cero):** Fallback jerárquico entre `track` y `recording`; si ambas son 0, imputar 0 y marcar flag `is_complete = 0`.
  - 🏷️ **E02 & E03 (Textos vacíos en tracks y artistas):** Imputación controlada a `'Pista Sin Título'` y `'Artista Desconocido'`.
  - 💿 **E04 (ISRCs múltiples):** Selección determinista del primer código mediante `DISTINCT ON (recording)`.
  - 📅 **E05 (Fechas nulas):** Derivación de `date_key` desde `last_updated` o asignación a clave `0`.
  - 📝 **E06 (Cadenas extensas >1000 caracteres):** Migración a tipo `TEXT` nativo de PostgreSQL con compresión TOAST.
  - 🔤 **E08 (BOM UTF-8 en Windows):** Saneamiento mediante decodificación estricta `utf-8-sig`.

---

#### DIAPOSITIVA 10: Particionamiento Físico por Rangos Temporales
- **Estrategia en `gold.fact_tracks`:**
  - Particionamiento declarativo por rango en la clave temporal conformada `date_key`:
    - `fact_tracks_pre_1970`: Catálogo histórico clásico.
    - `fact_tracks_1970s` a `fact_tracks_2000s`: Particiones decenales (Vinilo, Cassette, CD).
    - `fact_tracks_2010s`: **3.063 MB en disco** (Era de explosión del streaming).
    - `fact_tracks_2020` a `fact_tracks_2025`: Particiones anuales de alta densidad contemporánea.
    - `fact_tracks_default`: **0 filas** (100% de los datos resuelven partición válida).
- **Partition Pruning:**
  - Al consultar una década o año específico, el motor descarta las demás particiones, reduciendo el I/O en más del **85%**.

---

#### DIAPOSITIVA 11: Volumetría Oficial y Cumplimiento de Estrés
- **Tarjetas de Impacto Numérico (Big Numbers):**
  - 🎵 **19.370.311** Filas en el Hecho Central (`gold.fact_tracks`).
  - 🥈 **77.398.083** Filas Totales en la Capa Silver.
  - 🥇 **28.393.757** Filas Totales en la Capa Gold.
  - 💾 **17,77 GB** Almacenamiento Físico Ocupado en PostgreSQL 16 (**Meta superada en 592%**).
  - ⚡ **0,042 s** Tiempo promedio de respuesta en consultas de agregación masiva OLAP.

---

#### DIAPOSITIVA 12: Explotación Analítica en Power BI y Storytelling
- **Hallazgos de Negocio Demostrados con Datos Reales:**
  1. **La Era del Streaming y el Acortamiento Musical (RF05):**
     - Correlación Pearson negativa comprobada matemáticamente: las canciones en los años 70 y 80 promediaban entre 4:30 y 5:15 minutos; en la era del streaming contemporáneo (2020–2025), el promedio cayó a 3:10 minutos para maximizar reproducciones.
  2. **Evolución Tecnológica de Formatos (RF02 & RF04):**
     - Transición histórica documentada: Dominio absoluto del vinilo en los 70s -> Hegemonía del CD en los 90s -> Desplazamiento masivo por formatos digitales y streaming post-2010.
  3. **Formalización Fonográfica Global (RF06 & RF08):**
     - Distribución de cobertura ISRC: Países con industrias discográficas altamente formalizadas (EE.UU., Reino Unido, Alemania) superan el 75% de cobertura de ISRC, frente a mercados emergentes en desarrollo.

---

#### DIAPOSITIVA 13: Conclusiones y Lecciones de Ingeniería
- **Logros Consolidados:**
  - Arquitectura Medallón de grado empresarial con datos 100% reales de MusicBrainz.
  - Modelo en estrella de Ralph Kimball puro con 19.37 millones de hechos y cero huérfanos.
  - Despliegue reproducible sobre Docker con tuning de memoria (`shared_buffers=1GB`, `shm_size=1GB`).
- **Lección de Oro:**
  - *"Los conceptos prevalecen sobre las herramientas. Un diseño dimensional limpio, con tipos de datos correctos y particionamiento físico bien pensado, supera a cualquier solución compleja de moda."*
```
