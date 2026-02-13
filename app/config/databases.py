"""
Configuración de bases de datos (simplificado)
Ahora solo importa desde db_config
"""
import os
from dotenv import load_dotenv

load_dotenv()

ENVIRONMENT = os.getenv('ENVIRONMENT', 'production').lower()

from app.config.db_config import BotConfig, DB_NAMES

def get_databases():
    """Obtiene lista de BDs (wrapper para compatibilidad)"""
    return BotConfig.get_databases()


if __name__ == "__main__": 
    print(f"Ambiente: {ENVIRONMENT}")
    print(f"Bases de datos: {DB_NAMES}")