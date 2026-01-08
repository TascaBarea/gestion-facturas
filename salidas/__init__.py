"""
Módulo de salidas.

Genera Excel, logs y reportes de las facturas procesadas.
"""

from salidas.excel import (
    generar_excel,
    generar_excel_resumen,
    generar_excel_errores,
    generar_excel_multihoja
)

from salidas.log import (
    generar_log,
    generar_log_errores,
    generar_log_detallado,
    imprimir_resumen
)

__all__ = [
    # Excel
    'generar_excel',
    'generar_excel_resumen',
    'generar_excel_errores',
    'generar_excel_multihoja',
    # Log
    'generar_log',
    'generar_log_errores',
    'generar_log_detallado',
    'imprimir_resumen'
]
