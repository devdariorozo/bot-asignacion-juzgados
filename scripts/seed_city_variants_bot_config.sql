-- ============================================================
-- Seed: city_variants en bot_config (BD: bot_asignacion_config)
-- ============================================================
-- Ejecutar contra la base de datos bot_asignacion_config.
-- Añade la clave 'city_variants' para cada ambiente (local, qa, staging, production).
-- Formato: JSON array de grupos; cada grupo es un array de nombres equivalentes de ciudad.
-- ============================================================

USE bot_asignacion_config;

-- Valor JSON común para todos los ambientes (Bogotá, Cúcuta, Itagüí)
SET @city_variants_json = '[
  ["BOGOTA", "BOGOTÁ", "BOGOTA D.C.", "BOGOTÁ D.C.", "BOGOTA, D.C.", "BOGOTÁ, D.C.", "BOGOTA DC", "BOGOTÁ DC", "BOGOTA D C", "BOGOTÁ D C"],
  ["CÚCUTA", "CUCUTA", "SAN JOSÉ DE CÚCUTA", "SAN JOSE DE CUCUTA", "SAN JOSÉ DE CUCUTA", "SAN JOSE DE CÚCUTA"],
  ["ITAGÜI", "ITAGUI", "ITAGÜÍ"]
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
