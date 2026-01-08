"""
Módulo de extracción de texto desde PDFs.

Soporta tres métodos:
1. pypdf (rápido, para PDFs digitales)
2. pdfplumber (mejor para tablas)
3. OCR con Tesseract (para PDFs escaneados)

Uso:
    from nucleo.pdf import extraer_texto_pdf
    
    texto = extraer_texto_pdf('factura.pdf', metodo='pypdf')
"""
from pathlib import Path
from typing import Optional
import re

# Importar configuración
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from config.settings import TESSERACT_CMD, OCR_DPI, OCR_CONTRASTE, OCR_IDIOMA
except ImportError:
    TESSERACT_CMD = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
    OCR_DPI = 300
    OCR_CONTRASTE = 2.0
    OCR_IDIOMA = 'spa'

# =============================================================================
# VERIFICAR DISPONIBILIDAD DE LIBRERÍAS
# =============================================================================

# pypdf
try:
    from pypdf import PdfReader
    PYPDF_DISPONIBLE = True
except ImportError:
    try:
        from PyPDF2 import PdfReader
        PYPDF_DISPONIBLE = True
    except ImportError:
        PYPDF_DISPONIBLE = False
        print("⚠️ pypdf no disponible. Instalar con: pip install pypdf")

# pdfplumber
try:
    import pdfplumber
    PDFPLUMBER_DISPONIBLE = True
except ImportError:
    PDFPLUMBER_DISPONIBLE = False
    print("⚠️ pdfplumber no disponible. Instalar con: pip install pdfplumber")

# OCR (pytesseract + pdf2image)
try:
    import pytesseract
    from pdf2image import convert_from_path
    from PIL import Image, ImageEnhance
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD
    OCR_DISPONIBLE = True
except ImportError:
    OCR_DISPONIBLE = False
    print("⚠️ OCR no disponible. Instalar con: pip install pytesseract pdf2image pillow")


# =============================================================================
# FUNCIONES DE EXTRACCIÓN
# =============================================================================

def extraer_texto_pypdf(ruta: Path) -> str:
    """
    Extrae texto usando pypdf.
    
    Mejor para PDFs digitales simples.
    
    Args:
        ruta: Ruta al archivo PDF
        
    Returns:
        Texto extraído del PDF
    """
    if not PYPDF_DISPONIBLE:
        raise RuntimeError("pypdf no está disponible")
    
    try:
        reader = PdfReader(str(ruta))
        texto = ""
        for page in reader.pages:
            texto += (page.extract_text() or "") + "\n"
        return texto
    except Exception as e:
        raise RuntimeError(f"Error extrayendo texto con pypdf: {e}")


def extraer_texto_pdfplumber(ruta: Path) -> str:
    """
    Extrae texto usando pdfplumber.
    
    Mejor para PDFs con tablas o formato complejo.
    
    Args:
        ruta: Ruta al archivo PDF
        
    Returns:
        Texto extraído del PDF
    """
    if not PDFPLUMBER_DISPONIBLE:
        raise RuntimeError("pdfplumber no está disponible")
    
    try:
        texto = ""
        with pdfplumber.open(str(ruta)) as pdf:
            for page in pdf.pages:
                texto += (page.extract_text() or "") + "\n"
        return texto
    except Exception as e:
        raise RuntimeError(f"Error extrayendo texto con pdfplumber: {e}")


def extraer_texto_ocr(ruta: Path) -> str:
    """
    Extrae texto usando OCR (Tesseract).
    
    Para PDFs escaneados o con imágenes.
    
    Args:
        ruta: Ruta al archivo PDF
        
    Returns:
        Texto extraído mediante OCR
    """
    if not OCR_DISPONIBLE:
        raise RuntimeError("OCR no está disponible. Instalar pytesseract y pdf2image")
    
    try:
        # Convertir PDF a imágenes
        imagenes = convert_from_path(str(ruta), dpi=OCR_DPI)
        
        texto_completo = ""
        for imagen in imagenes:
            # Preprocesar imagen para mejorar OCR
            imagen_procesada = _preprocesar_imagen_ocr(imagen)
            
            # Extraer texto con Tesseract
            texto = pytesseract.image_to_string(
                imagen_procesada,
                lang=OCR_IDIOMA,
                config='--psm 6'  # Assume uniform block of text
            )
            texto_completo += texto + "\n"
        
        return texto_completo
    except Exception as e:
        raise RuntimeError(f"Error en OCR: {e}")


def _preprocesar_imagen_ocr(imagen: 'Image.Image') -> 'Image.Image':
    """
    Preprocesa una imagen para mejorar la calidad del OCR.
    
    Args:
        imagen: Imagen PIL
        
    Returns:
        Imagen procesada
    """
    # Convertir a escala de grises
    if imagen.mode != 'L':
        imagen = imagen.convert('L')
    
    # Aumentar contraste
    enhancer = ImageEnhance.Contrast(imagen)
    imagen = enhancer.enhance(OCR_CONTRASTE)
    
    return imagen


# =============================================================================
# FUNCIÓN PRINCIPAL
# =============================================================================

def extraer_texto_pdf(
    ruta: Path,
    metodo: str = 'pypdf',
    fallback: bool = True
) -> str:
    """
    Extrae texto de un PDF usando el método especificado.
    
    Args:
        ruta: Ruta al archivo PDF
        metodo: Método de extracción ('pypdf', 'pdfplumber', 'ocr')
        fallback: Si True, intenta otros métodos si el principal falla
        
    Returns:
        Texto extraído del PDF
        
    Raises:
        FileNotFoundError: Si el archivo no existe
        RuntimeError: Si no se puede extraer el texto
    """
    ruta = Path(ruta)
    
    if not ruta.exists():
        raise FileNotFoundError(f"Archivo no encontrado: {ruta}")
    
    metodo = metodo.lower()
    texto = ""
    
    # Orden de métodos a intentar
    if metodo == 'ocr':
        metodos = ['ocr', 'pdfplumber', 'pypdf']
    elif metodo == 'pdfplumber':
        metodos = ['pdfplumber', 'pypdf', 'ocr']
    else:  # pypdf por defecto
        metodos = ['pypdf', 'pdfplumber', 'ocr']
    
    if not fallback:
        metodos = [metodo]
    
    errores = []
    for m in metodos:
        try:
            if m == 'pypdf' and PYPDF_DISPONIBLE:
                texto = extraer_texto_pypdf(ruta)
            elif m == 'pdfplumber' and PDFPLUMBER_DISPONIBLE:
                texto = extraer_texto_pdfplumber(ruta)
            elif m == 'ocr' and OCR_DISPONIBLE:
                texto = extraer_texto_ocr(ruta)
            else:
                continue
            
            # Verificar que se extrajo algo
            if texto and len(texto.strip()) > 50:
                return _limpiar_texto(texto)
                
        except Exception as e:
            errores.append(f"{m}: {e}")
            continue
    
    # Si llegamos aquí, ningún método funcionó
    if errores:
        raise RuntimeError(f"No se pudo extraer texto. Errores: {'; '.join(errores)}")
    else:
        raise RuntimeError("No hay métodos de extracción disponibles")


def _limpiar_texto(texto: str) -> str:
    """
    Limpia el texto extraído.
    
    Args:
        texto: Texto a limpiar
        
    Returns:
        Texto limpio
    """
    # Eliminar múltiples espacios
    texto = re.sub(r'[ \t]+', ' ', texto)
    
    # Eliminar múltiples líneas vacías
    texto = re.sub(r'\n\s*\n', '\n\n', texto)
    
    # Eliminar espacios al inicio/final de líneas
    lineas = [linea.strip() for linea in texto.split('\n')]
    texto = '\n'.join(lineas)
    
    return texto.strip()


# =============================================================================
# FUNCIONES DE UTILIDAD
# =============================================================================

def verificar_disponibilidad() -> dict:
    """
    Verifica qué métodos de extracción están disponibles.
    
    Returns:
        Diccionario con la disponibilidad de cada método
    """
    return {
        'pypdf': PYPDF_DISPONIBLE,
        'pdfplumber': PDFPLUMBER_DISPONIBLE,
        'ocr': OCR_DISPONIBLE,
    }


def obtener_metodo_recomendado(proveedor: str = '') -> str:
    """
    Obtiene el método de extracción recomendado para un proveedor.
    
    Args:
        proveedor: Nombre del proveedor
        
    Returns:
        Método recomendado ('pypdf', 'pdfplumber', 'ocr')
    """
    try:
        from config.proveedores import obtener_metodo_pdf
        return obtener_metodo_pdf(proveedor)
    except ImportError:
        return 'pypdf'


# =============================================================================
# TEST
# =============================================================================

if __name__ == '__main__':
    print("=== Verificación de disponibilidad ===")
    disp = verificar_disponibilidad()
    for metodo, disponible in disp.items():
        estado = '✅' if disponible else '❌'
        print(f"  {estado} {metodo}")
