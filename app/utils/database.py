import os
import urllib.parse
from typing import List
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
from app.config.db_config import DB_NAMES, ENVIRONMENT, BotConfig

load_dotenv()

DB_HOST = os.getenv('DB_HOST')
DB_PORT = os.getenv('DB_PORT', '3306')
DB_USER = os.getenv('DB_USER')
DB_PASSWORD = urllib.parse.quote_plus(os.getenv('DB_PASSWORD', ''))

# URL base
DATABASE_URL_TEMPLATE = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}"

# Primera BD de la lista
DATABASE_URL = f"{DATABASE_URL_TEMPLATE}/{DB_NAMES[0]}" if DB_NAMES else None

GOOGLE_API_KEY = BotConfig.get_google_api_key()


def get_database_url(db_name: str) -> str:
    """
    Genera la URL de conexión para una base de datos específica
    
    Args:
        db_name: Nombre de la base de datos
        
    Returns:
        str: URL de conexión completa
    """
    return f"{DATABASE_URL_TEMPLATE}/{db_name}"


def get_all_database_urls() -> dict:
    """
    Obtiene URLs de conexión para todas las bases de datos configuradas
    
    Returns:
        dict: {db_name: database_url}
    """
    return {db_name: get_database_url(db_name) for db_name in DB_NAMES}


def test_database_connections() -> dict:
    """
    Prueba la conexión a todas las bases de datos
    
    Returns:
        dict: {db_name: {'status': 'ok'|'error', 'message': str}}
    """
    results = {}
    
    for db_name in DB_NAMES:
        try:
            engine = create_engine(get_database_url(db_name), echo=False, pool_pre_ping=True)
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            results[db_name] = {'status': 'ok', 'message': 'Conexión exitosa'}
            engine.dispose()
        except Exception as e:
            results[db_name] = {'status': 'error', 'message': str(e)}
    
    return results


def print_database_config():
    """Imprime la configuración de bases de datos"""
    print("=" * 80)
    print("📊 CONFIGURACIÓN DE BASES DE DATOS")
    print("=" * 80)
    print(f"🌍 Ambiente: {ENVIRONMENT}")
    print(f"DB_HOST: {DB_HOST}")
    print(f"DB_PORT: {DB_PORT}")
    print(f"DB_USER: {DB_USER}")
    print(f"\n📚 Bases de datos configuradas: {len(DB_NAMES)}")
    for i, db_name in enumerate(DB_NAMES, 1):
        print(f"   {i}.{db_name}")
    print("=" * 80)


if __name__ == "__main__":
    print_database_config()
    
    print("\n🔍 Probando conexiones...")
    results = test_database_connections()
    
    for db_name, result in results.items():
        status_icon = "✅" if result['status'] == 'ok' else "❌"
        print(f"{status_icon} {db_name}: {result['message']}")