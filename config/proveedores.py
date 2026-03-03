"""
Datos de proveedores conocidos.

Este archivo contiene:
- Funciones de consulta de proveedores (CIF, IBAN, metodo PDF)
- Alias y normalizacion de nombres
- Metodo de extraccion PDF por proveedor

Los datos sensibles (IBANs, CIFs) se cargan de config/datos_sensibles.py
que NO esta en git. Ver datos_sensibles.py.example para la plantilla.

Actualizado: 03/03/2026 - v5.0 (datos sensibles externalizados)
"""

from config.datos_sensibles import (
    CIF_PROPIO,
    PROVEEDORES_CONOCIDOS,
    CIF_A_PROVEEDOR,
)

# Bancos a evitar en IBAN (cuando hay varios)
BANCOS_EVITAR = ["0049"]

# =============================================================================
# ALIAS DE PROVEEDORES
# =============================================================================

# Para búsqueda en diccionario de categorías
PROVEEDOR_ALIAS_DICCIONARIO = {
    'JAMONES BERNAL': 'EMBUTIDOS BERNAL',
    'BERNAL': 'EMBUTIDOS BERNAL',
}

# Para normalización de nombre en salida
PROVEEDOR_NOMBRE_SALIDA = {
    'JAVIER ALBORES': 'CONTROLPLAGA',
    'JAVIER ARBORES': 'CONTROLPLAGA',
    'ALBORES': 'CONTROLPLAGA',
    'ARBORES': 'CONTROLPLAGA',
}


# =============================================================================
# MÉTODO DE EXTRACCIÓN PDF POR PROVEEDOR
# =============================================================================

EXTRACTOR_PDF_PROVEEDOR = {
    # Proveedores que funcionan mejor con pdfplumber
    'CERES': 'pdfplumber',
    'BODEGAS BORBOTON': 'pdfplumber',
    'BORBOTON': 'pdfplumber',
    'FELISA GOURMET': 'pdfplumber',
    'FELISA': 'pdfplumber',
    'DISTRIBUCIONES LAVAPIES': 'pdfplumber',
    'LAVAPIES': 'pdfplumber',
    'LIDL': 'pdfplumber',
    'BODEGAS MUÑOZ MARTIN': 'pdfplumber',
    'MUÑOZ MARTIN': 'pdfplumber',
    'EMJAMESA': 'pdfplumber',
    'MOLIENDA VERDE': 'pdfplumber',
    'LA MOLIENDA VERDE': 'pdfplumber',
    'ZUBELZU': 'pdfplumber',
    'IBARRAKO PIPARRAK': 'pdfplumber',
    'IBARRAKO PIPARRA': 'pdfplumber',
    'IBARRAKO': 'pdfplumber',
    
    # Proveedores OCR (PDFs escaneados)
    'JIMELUZ': 'ocr',
    'LA ROSQUILLERIA': 'ocr',
    'ROSQUILLERIA': 'ocr',
    'MANIPULADOS ABELLAN': 'ocr',
    'FISHGOURMET': 'ocr',
    'MARIA LINAREJOS': 'ocr',
}


def obtener_datos_proveedor(nombre: str) -> dict:
    """
    Obtiene CIF e IBAN de un proveedor.
    
    Args:
        nombre: Nombre del proveedor
        
    Returns:
        {'cif': '...', 'iban': '...'} o {'cif': '', 'iban': ''} si no existe
    """
    nombre_upper = nombre.upper()
    
    # Buscar coincidencia exacta
    if nombre_upper in PROVEEDORES_CONOCIDOS:
        return PROVEEDORES_CONOCIDOS[nombre_upper]
    
    # Buscar coincidencia parcial
    for clave, datos in PROVEEDORES_CONOCIDOS.items():
        if clave in nombre_upper or nombre_upper in clave:
            return datos
    
    return {'cif': '', 'iban': ''}


def obtener_proveedor_por_cif(cif: str) -> str:
    """
    Obtiene el nombre del proveedor a partir de su CIF.
    
    Args:
        cif: CIF del proveedor
        
    Returns:
        Nombre del proveedor o cadena vacía si no existe
    """
    # Limpiar CIF
    cif_limpio = cif.replace('-', '').replace(' ', '').upper()
    
    return CIF_A_PROVEEDOR.get(cif_limpio, '')


def obtener_metodo_pdf(proveedor: str) -> str:
    """
    Obtiene el método de extracción PDF para un proveedor.
    
    Args:
        proveedor: Nombre del proveedor
        
    Returns:
        'pypdf', 'pdfplumber' u 'ocr'
    """
    proveedor_upper = proveedor.upper()
    
    return EXTRACTOR_PDF_PROVEEDOR.get(proveedor_upper, 'pypdf')
