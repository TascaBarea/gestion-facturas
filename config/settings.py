"""
Configuración global de ParsearFacturas.

IMPORTANTE: VERSION se define SOLO aquí.
main.py y otros módulos importan VERSION de este archivo.
"""
from pathlib import Path

# ==============================================================================
# VERSIÓN (FUENTE ÚNICA DE VERDAD)
# ==============================================================================
VERSION = "5.14"

# ==============================================================================
# DATOS DE LA EMPRESA
# ==============================================================================
CIF_PROPIO = "B87760575"  # CIF de TASCA BAREA S.L.L.

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

# Configuración OCR (Tesseract)
TESSERACT_CMD = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
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
