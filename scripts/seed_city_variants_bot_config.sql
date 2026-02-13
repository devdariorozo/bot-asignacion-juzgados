-- ============================================================
-- Seed: city_variants en bot_config (BD: bot_asignacion_config)
-- ============================================================
-- Ejecutar contra la base de datos bot_asignacion_config.
-- Añade la clave 'city_variants' para cada ambiente (local, qa, staging, production).
-- Formato: JSON array de grupos; cada grupo es un array de nombres equivalentes de ciudad.
-- ============================================================

USE bot_asignacion_config;

-- Valor JSON: solo variantes de NOMBRE (mismo lugar, nombre distinto).
-- Tildes y mayúsculas/minúsculas se normalizan en código antes de comparar.
-- Si admin_area_level_1 (ej. Bogotá D.C.) está en algún grupo, el geocode lo usa como ciudad
-- en lugar de la locality (evita ambigüedades como San Cristóbal en Bogotá vs Medellín).
SET @city_variants_json = '[
  ["BOGOTA", "BOGOTA D.C.", "BOGOTA, D.C.", "BOGOTA DC", "BOGOTA D C"],
  ["CUCUTA", "SAN JOSE DE CUCUTA"],
  ["EL ESPINAL", "ESPINAL"],
  ["CARTAGENA", "CARTAGENA DE INDIAS"]
]';

-- Eliminar registros previos de city_variants (evita duplicados al re-ejecutar)
DELETE FROM bot_config WHERE config_key = 'city_variants';

-- Insertar una fila por ambiente
INSERT INTO bot_config (environment, config_key, config_value, description, updated_at, created_at)
VALUES
  ('local',     'city_variants', @city_variants_json, 'Variantes de nombres de ciudades para comparación y búsqueda (Bogotá, Cúcuta, Itagüí, etc.)', NOW(), NOW()),
  ('qa',        'city_variants', @city_variants_json, 'Variantes de nombres de ciudades para comparación y búsqueda (Bogotá, Cúcuta, Itagüí, etc.)', NOW(), NOW()),
  ('staging',   'city_variants', @city_variants_json, 'Variantes de nombres de ciudades para comparación y búsqueda (Bogotá, Cúcuta, Itagüí, etc.)', NOW(), NOW()),
  ('production','city_variants', @city_variants_json, 'Variantes de nombres de ciudades para comparación y búsqueda (Bogotá, Cúcuta, Itagüí, etc.)', NOW(), NOW());