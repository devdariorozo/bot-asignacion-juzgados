"""
Variantes de ciudades para comparación y búsqueda.

Dos conceptos:
- Normalización de escritura: mismo nombre con/sin tilde, mayúsculas/minúsculas
  (ej. Cartagena, cartagena, CARTAGENA, cartagéna) → se estandarizan antes de comparar.
- Variantes de nombre: mismo lugar con nombres distintos (ej. Bogotá vs Bogota D.C.,
  Cartagena vs Cartagena de Indias). Esas equivalencias se configuran en BD.

Las variantes se leen siempre desde bot_config (BD bot_asignacion_config).
No se queman listas en código; el seed/BD define los grupos (scripts/seed_city_variants_bot_config.sql).
"""
import unicodedata
from typing import List, Set


def _remove_accents(s: str) -> str:
    """Quita tildes/acentos (NFD y elimina caracteres combinables)."""
    nfd = unicodedata.normalize("NFD", s)
    return "".join(c for c in nfd if unicodedata.category(c) != "Mn")


def normalize_city(city: str) -> str | None:
    """
    Estandariza el nombre de ciudad para comparación: sin espacios de más,
    mayúsculas y sin tildes. Así "Cartagena", "cartagena", "CARTAGENA", "cartagéna"
    se tratan como el mismo nombre.
    """
    if not city or not isinstance(city, str):
        return None
    t = city.strip().upper()
    if not t:
        return None
    return _remove_accents(t)


def _get_city_variant_sets() -> List[Set[str]]:
    """
    Obtiene los conjuntos de variantes de ciudades desde la BD (bot_config, key city_variants).
    Cada set contiene nombres ya NORMALIZADOS (upper + sin tildes).
    Si no hay config o falla la lectura, devuelve lista vacía (solo aplica normalización de escritura).
    """
    try:
        from app.config.db_config import BotConfig
        raw = BotConfig.get_city_variants()
    except Exception:
        raw = None
    if not raw:
        return []

    return [
        set(n for v in group if (n := normalize_city(v)))
        for group in raw
    ]


def cities_match(city1: str, city2: str) -> bool:
    """
    Compara dos ciudades: primero estandariza escritura (tildes, mayúsculas);
    luego considera variantes de nombre (Bogotá/Bogota D.C., Cartagena/Cartagena de Indias).
    """
    if not city1 or not city2:
        return False

    n1 = normalize_city(city1)
    n2 = normalize_city(city2)
    if not n1 or not n2:
        return False
    if n1 == n2:
        return True

    for variant_set in _get_city_variant_sets():
        if n1 in variant_set and n2 in variant_set:
            return True
    return False


def is_city_in_any_variant_group(city: str) -> bool:
    """
    Indica si el nombre (normalizado) está en algún grupo de variantes.
    Útil en geocode: si administrative_area_level_1 está en un grupo, se puede
    usar como ciudad en lugar de la locality (evita ambigüedades como San Cristóbal).
    """
    n = normalize_city(city)
    if not n:
        return False
    for variant_set in _get_city_variant_sets():
        if n in variant_set:
            return True
    return False


def get_city_search_variants(city: str) -> List[str]:
    """
    Devuelve las variantes de búsqueda para una ciudad (normalizadas).
    Para usar en SQL: comparar con UPPER(TRIM(dc.city)); si la BD usa collation
    que ignora acentos (ej. utf8mb4_unicode_ci), una sola forma por concepto basta.
    """
    if not city:
        return []

    normalized = normalize_city(city)
    if not normalized:
        return []

    for variant_set in _get_city_variant_sets():
        if normalized in variant_set:
            return list(variant_set)

    return [normalized]
