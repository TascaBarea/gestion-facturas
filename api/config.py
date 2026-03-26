"""
api/config.py — Configuración del servidor API desde .env
"""

import os
from dotenv import load_dotenv

# Cargar .env del directorio api/
_API_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(_API_DIR, ".env"))

API_KEY = os.getenv("API_KEY", "")
API_HOST = os.getenv("API_HOST", "127.0.0.1")
API_PORT = int(os.getenv("API_PORT", "8000"))

# Directorio raíz del proyecto (gestion-facturas/)
PROJECT_ROOT = os.path.dirname(_API_DIR)
