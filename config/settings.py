"""
Configuración global de ParsearFacturas.

IMPORTANTE: VERSION se resuelve desde el Parseo canónico.
main.py y otros módulos importan VERSION de este archivo.
"""
from pathlib import Path
import importlib.util as _importlib_util
import os as _os

# ==============================================================================
# VERSIÓN (FUENTE ÚNICA DE VERDAD)
# ==============================================================================
_PARSEO_ROOT = Path(_os.getenv("PARSEO_ROOT", Path(__file__).resolve().parent.parent.parent / "Parseo"))
_PARSEO_SETTINGS = _PARSEO_ROOT / "config" / "settings.py"

if not _PARSEO_SETTINGS.exists():
    raise RuntimeError(
        f"No se encontro el settings canonico de Parseo en: {_PARSEO_SETTINGS}"
    )

_spec = _importlib_util.spec_from_file_location("parseo_settings_canon", _PARSEO_SETTINGS)
if _spec is None or _spec.loader is None:
    raise RuntimeError(f"No se pudo cargar el settings canonico de Parseo: {_PARSEO_SETTINGS}")

_parseo_settings = _importlib_util.module_from_spec(_spec)
_spec.loader.exec_module(_parseo_settings)

VERSION = str(getattr(_parseo_settings, "VERSION", ""))
if not VERSION:
    raise RuntimeError(f"El settings canonico de Parseo no define VERSION: {_PARSEO_SETTINGS}")

# ==============================================================================
# DATOS DE LA EMPRESA
# ==============================================================================
# Resolución robusta: Streamlit secrets → env var → datos_sensibles.py → "".
# Evita ModuleNotFoundError en Streamlit Cloud (donde datos_sensibles.py no
# está, por estar gitignored). Ver config/loader.py.
from config.loader import get as _get_config  # noqa: E402
CIF_PROPIO = _get_config("CIF_PROPIO", "")

# ==============================================================================
# RUTAS POR DEFECTO
# ==============================================================================
# Ruta al diccionario de categorías
DICCIONARIO_DEFAULT = r"C:\_ARCHIVOS\TRABAJO\Facturas\ParsearFacturas-main\datos\DiccionarioProveedoresCategoria.xlsx"

# Directorio base del proyecto
BASE_DIR = Path(__file__).parent.parent

# ==============================================================================
# CONFIGURACIÓN PDF
# ==============================================================================
# Métodos de extracción disponibles: 'pypdf', 'pdfplumber', 'ocr'
METODO_PDF_DEFAULT = 'pypdf'

# Configuración OCR (Tesseract) - detección automática Windows/Linux
import platform as _platform
if _platform.system() == 'Windows':
    TESSERACT_CMD = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
else:
    TESSERACT_CMD = '/usr/bin/tesseract'
OCR_DPI = 300
OCR_CONTRASTE = 1.5
OCR_IDIOMA = 'spa'

# ==============================================================================
# CONFIGURACIÓN DE VALIDACIÓN
# ==============================================================================
# Tolerancia para validación de cuadre (en euros)
TOLERANCIA_CUADRE = 0.05

# IVAs válidos en España
IVAS_VALIDOS = [0, 4, 10, 21]

# ==============================================================================
# BANCOS A EXCLUIR (son del cliente, no del proveedor)
# ==============================================================================
BANCOS_EXCLUIR = ['0049']  # Santander

# ==============================================================================
# CONFIGURACIÓN DE SALIDAS
# ==============================================================================
# Nombre de la hoja de Excel por defecto
EXCEL_HOJA_DEFAULT = 'Facturas'

# Formato de fecha para logs
FORMATO_FECHA_LOG = '%Y-%m-%d %H:%M:%S'
