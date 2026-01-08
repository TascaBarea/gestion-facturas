"""
Módulo núcleo del sistema ParsearFacturas.

Contiene las funciones principales de procesamiento:
- factura: Clases Factura y LineaFactura
- pdf: Extracción de texto de PDFs
- parser: Parseo de fecha, CIF, IBAN, total, referencia
- validacion: Cuadre y detección de duplicados

Uso:
    from nucleo import Factura, LineaFactura
    from nucleo import extraer_texto_pdf
    from nucleo import extraer_fecha, extraer_cif, extraer_total
    from nucleo import validar_cuadre, detectar_duplicado
"""

# Clases de datos
from .factura import Factura, LineaFactura

# Extracción de texto
from .pdf import (
    extraer_texto_pdf,
    extraer_texto_pypdf,
    extraer_texto_pdfplumber,
    extraer_texto_ocr,
    verificar_disponibilidad,
    obtener_metodo_recomendado,
)

# Parseo
from .parser import (
    parsear_nombre_archivo,
    extraer_fecha,
    extraer_cif,
    extraer_iban,
    extraer_todos_ibans,
    extraer_total,
    extraer_referencia,
    detectar_proveedor_por_cif,
    detectar_proveedor_por_contenido,
)

# Validación
from .validacion import (
    validar_cuadre,
    calcular_total_lineas,
    calcular_base_total,
    generar_clave_factura,
    detectar_duplicado,
    cargar_registro,
    guardar_registro,
    agregar_al_registro,
    validar_factura,
    es_factura_valida,
)

__all__ = [
    # Clases
    'Factura',
    'LineaFactura',
    # PDF
    'extraer_texto_pdf',
    'extraer_texto_pypdf',
    'extraer_texto_pdfplumber',
    'extraer_texto_ocr',
    'verificar_disponibilidad',
    'obtener_metodo_recomendado',
    # Parser
    'parsear_nombre_archivo',
    'extraer_fecha',
    'extraer_cif',
    'extraer_iban',
    'extraer_todos_ibans',
    'extraer_total',
    'extraer_referencia',
    'detectar_proveedor_por_cif',
    'detectar_proveedor_por_contenido',
    # Validación
    'validar_cuadre',
    'calcular_total_lineas',
    'calcular_base_total',
    'generar_clave_factura',
    'detectar_duplicado',
    'cargar_registro',
    'guardar_registro',
    'agregar_al_registro',
    'validar_factura',
    'es_factura_valida',
]
