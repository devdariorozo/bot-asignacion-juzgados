"""
Configuración dinámica del bot desde base de datos
Centraliza toda la configuración en la BD bot_asignacion_config
"""
import json
import os
from typing import List, Dict, Any
from sqlalchemy import create_engine, text
import urllib.parse
import pymysql
from dotenv import load_dotenv

load_dotenv()

DB_HOST = os.getenv('DB_HOST')
DB_PORT = os.getenv('DB_PORT', '3306')
DB_USER = os.getenv('DB_USER')
DB_PASSWORD = urllib.parse.quote_plus(os.getenv('DB_PASSWORD', ''))

ENVIRONMENT = os.getenv('ENVIRONMENT', 'production').lower()

CONFIG_DB_NAME = 'bot_asignacion_config'
CONFIG_DB_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{CONFIG_DB_NAME}"


class BotConfig:
    """
    Gestor de configuración dinámica del bot
    
    Lee configuración desde la BD bot_asignacion_config
    según el ambiente actual (ENVIRONMENT)
    """
    
    _cache = {}
    
    @staticmethod
    def _get_config(config_key: str) -> Any:
        """
        Obtiene una configuración de la BD
        
        Args:
            config_key: Tipo de configuración
                - 'databases': Lista de BDs a procesar
                - 'api_limits': Límites de Google Maps API
                - 'log_config': Configuración de logs
                - 'google_api_key': API Key de Google Maps
                - 'city_variants': Lista de grupos de variantes de ciudades (JSON)
                
        Returns:
            Valor de configuración (ya parseado si es JSON)
        """
        cache_key = f"{ENVIRONMENT}_{config_key}"
        
        if cache_key in BotConfig._cache:
            return BotConfig._cache[cache_key]
        
        try: 
            engine = create_engine(CONFIG_DB_URL, echo=False, pool_pre_ping=True)
            
            with engine.connect() as conn:
                query = text("""
                    SELECT config_value 
                    FROM bot_config 
                    WHERE environment = :env 
                    AND config_key = :key
                """)
                
                result = conn.execute(query, {
                    "env":  ENVIRONMENT,
                    "key":  config_key
                }).fetchone()
                
                if not result:
                    raise ValueError(
                        f"❌ No se encontró configuración '{config_key}' "
                        f"para ambiente '{ENVIRONMENT}' en bot_asignacion_config"
                    )
                
                config_value = result[0]
                
                if config_key in ['databases', 'api_limits', 'log_config', 'city_variants']:
                    config_value = json.loads(config_value)
                
                BotConfig._cache[cache_key] = config_value
                
            engine.dispose()
            return config_value
            
        except Exception as e: 
            print(f"❌ Error al obtener configuración '{config_key}': {e}")
            print(f"   Ambiente: {ENVIRONMENT}")
            print(f"   BD Config: {CONFIG_DB_URL}")
            raise
    
    @staticmethod
    def get_databases() -> List[str]:
        """
        Obtiene lista de bases de datos a procesar
        
        Returns: 
            Lista de nombres de BDs según el ambiente
            
        Example:
            >>> BotConfig.get_databases()
            ['miosv2_carteras_QA', 'miosv2_cartera_mirror']
        """
        return BotConfig._get_config('databases')
    
    @staticmethod
    def get_api_limits() -> Dict[str, int]:
        """
        Obtiene límites de llamadas a Google Maps API
        
        Returns: 
            {'daily': int, 'monthly':  int}
            
        Example:
            >>> BotConfig.get_api_limits()
            {'daily': 700, 'monthly': 8000}
        """
        return BotConfig._get_config('api_limits')
    
    @staticmethod
    def get_log_config() -> Dict[str, int]:
        """
        Obtiene configuración de logs
        
        Returns:
            {'max_lines': int, 'rotation_interval': int}
            
        Example:
            >>> BotConfig.get_log_config()
            {'max_lines': 500, 'rotation_interval': 50}
        """
        return BotConfig._get_config('log_config')
    
    @staticmethod
    def get_google_api_key() -> str:
        """
        Obtiene Google Maps API Key para el ambiente actual
        
        Returns:
            API Key como string
            
        Example: 
            >>> BotConfig.get_google_api_key()
            'AIzaSyCgaEWlFt8AJGAj2Zlb7MXQd2StPWvmuXQ'
        """
        return BotConfig._get_config('google_api_key')
    
    @staticmethod
    def get_city_variants() -> List[List[str]]:
        """
        Obtiene los grupos de variantes de ciudades desde bot_config.
        Cada grupo es una lista de nombres equivalentes (ej: Bogotá, BOGOTÁ D.C., etc.).
        
        Returns:
            Lista de listas; cada sublista es un conjunto de variantes para una misma ciudad.
            
        Example:
            >>> BotConfig.get_city_variants()
            [["BOGOTA", "BOGOTÁ", "BOGOTA D.C.", ...], ["CÚCUTA", "CUCUTA", ...], ...]
        """
        return BotConfig._get_config('city_variants')

    @staticmethod
    def clear_cache():
        """
        Limpia el cache de configuración
        
        Útil después de actualizar valores en la BD
        para forzar re-lectura en la próxima consulta
        """
        BotConfig._cache = {}
        print("✅ Cache de configuración limpiado")
    
    @staticmethod
    def print_config():
        """Muestra la configuración actual"""
        print("=" * 70)
        print("⚙️  CONFIGURACIÓN DEL BOT")
        print("=" * 70)
        print(f"🌍 Ambiente: {ENVIRONMENT}")
        print(f"📦 BD Config: {CONFIG_DB_NAME}")
        print()
        
        try:
            databases = BotConfig.get_databases()
            print(f"📚 Bases de datos ({len(databases)}):")
            for i, db in enumerate(databases, 1):
                print(f"   {i}.{db}")
            print()
            
            api_limits = BotConfig.get_api_limits()
            print(f"🔑 Límites de API:")
            print(f"   Diario: {api_limits['daily']} llamadas")
            print(f"   Mensual: {api_limits['monthly']} llamadas")
            print()
            
            log_config = BotConfig.get_log_config()
            print(f"📝 Configuración de Logs:")
            print(f"   Líneas máximas: {log_config['max_lines']}")
            print(f"   Intervalo de rotación: {log_config['rotation_interval']}")
            print()
            
            api_key = BotConfig.get_google_api_key()
            print(f"🗺️  Google Maps API Key: {api_key[:20]}...")
            print()
            
            try:
                city_variants = BotConfig.get_city_variants()
                print(f"🏙️  Variantes de ciudades: {len(city_variants)} grupos")
                for i, group in enumerate(city_variants, 1):
                    print(f"   {i}. {group[0]} (+{len(group) - 1} variantes)")
            except Exception:
                print("🏙️  Variantes de ciudades: (no configurado en BD, se usan por defecto en código)")
            print()
            
        except Exception as e: 
            print(f"❌ Error al cargar configuración: {e}")
        
        print("=" * 70)

DB_NAMES = BotConfig.get_databases()


if __name__ == "__main__": 
    BotConfig.print_config()