"""
Variantes de ciudades para comparación y búsqueda.

Lee los grupos de variantes desde bot_config (BD bot_asignacion_config).
Si no existe la clave 'city_variants' o hay error, usa variantes por defecto (Bogotá, Cúcuta, Itagüí).
"""
from typing import List, Set

# Variantes por defecto (fallback si no hay config en BD)
DEFAULT_CITY_VARIANTS = [
    ["BOGOTA", "BOGOTÁ", "BOGOTA D.C.", "BOGOTÁ D.C.", "BOGOTA, D.C.", "BOGOTÁ, D.C.",
     "BOGOTA DC", "BOGOTÁ DC", "BOGOTA D C", "BOGOTÁ D C"],
    ["CÚCUTA", "CUCUTA", "SAN JOSÉ DE CÚCUTA", "SAN JOSE DE CUCUTA",
     "SAN JOSÉ DE CUCUTA", "SAN JOSE DE CÚCUTA"],
    ["ITAGÜI", "ITAGUI", "ITAGÜÍ"],
]


def _get_city_variant_sets() -> List[Set[str]]:
    """
    Obtiene los conjuntos de variantes de ciudades (desde BD o por defecto).
    
    Returns:
        Lista de sets; cada set contiene los nombres equivalentes de una ciudad.
    """
    try:
        from app.config.db_config import BotConfig
        raw = BotConfig.get_city_variants()
        if not raw:
            return [set(group) for group in DEFAULT_CITY_VARIANTS]
        return [set(group) for group in raw]
    except Exception:
        return [set(group) for group in DEFAULT_CITY_VARIANTS]


def normalize_city(city: str) -> str | None:
    """Normalizar nombre de ciudad (mayúsculas, sin espacios extra)."""
    if not city:
        return None
    return city.strip().upper()


def cities_match(city1: str, city2: str) -> bool:
    """
    Compara dos ciudades considerando variantes equivalentes (Bogotá, Cúcuta, etc.).

    Args:
        city1: Primera ciudad a comparar
        city2: Segunda ciudad a comparar

    Returns:
        True si las ciudades son equivalentes, False si no
    """
    if not city1 or not city2:
        return False

    city1_norm = normalize_city(city1)
    city2_norm = normalize_city(city2)
    if city1_norm == city2_norm:
        return True

    variant_sets = _get_city_variant_sets()
    for variant_set in variant_sets:
        if city1_norm in variant_set and city2_norm in variant_set:
            return True
    return False


def get_city_search_variants(city: str) -> List[str]:
    """
    Obtiene las variantes de búsqueda para una ciudad.
    Para ciudades con grupo definido (Bogotá, Cúcuta, Itagüí) devuelve todas las variantes;
    para el resto, solo la normalizada.

    Args:
        city: Nombre de la ciudad

    Returns:
        Lista de variantes de búsqueda para usar en queries (OR en SQL).
    """
    if not city:
        return []

    normalized = normalize_city(city)
    variant_sets = _get_city_variant_sets()

    for variant_set in variant_sets:
        if normalized in variant_set:
            return list(variant_set)

    return [normalized]
