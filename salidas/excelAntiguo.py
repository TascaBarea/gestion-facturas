"""
Módulo de generación de Excel.

Genera archivos Excel con las facturas procesadas.
"""
import pandas as pd
from pathlib import Path
from typing import List, TYPE_CHECKING
from datetime import datetime

if TYPE_CHECKING:
    from nucleo.factura import Factura


def generar_excel(facturas: List['Factura'], ruta: Path, nombre_hoja: str = 'Facturas') -> int:
    """
    Genera el Excel con las facturas procesadas.
    
    Args:
        facturas: Lista de facturas procesadas
        ruta: Ruta donde guardar el archivo
        nombre_hoja: Nombre de la hoja de Excel
        
    Returns:
        Número de filas generadas
    """
    filas = []
    
    for f in facturas:
        if f.lineas:
            for linea in f.lineas:
                filas.append({
                    '#': f.numero,
                    'FECHA': f.fecha or '',
                    'REF': f.referencia or '',
                    'PROVEEDOR': f.proveedor,
                    'ARTICULO': linea.articulo,
                    'CATEGORIA': linea.categoria or 'PENDIENTE',
                    'ID_CAT': linea.id_categoria or '',
                    'CANTIDAD': linea.cantidad if linea.cantidad else '',
                    'PRECIO_UD': linea.precio_ud if linea.precio_ud else '',
                    'TIPO IVA': linea.iva,
                    'BASE (€)': linea.base,
                    'CUOTA IVA': linea.cuota_iva,
                    'TOTAL FAC': f.total or '',
                    'CUADRE': f.cuadre,
                    'ARCHIVO': f.archivo
                })
        else:
            # Factura sin líneas extraídas
            filas.append({
                '#': f.numero,
                'FECHA': f.fecha or '',
                'REF': f.referencia or '',
                'PROVEEDOR': f.proveedor,
                'ARTICULO': 'VER FACTURA',
                'CATEGORIA': 'PENDIENTE',
                'ID_CAT': '',
                'CANTIDAD': '',
                'PRECIO_UD': '',
                'TIPO IVA': '',
                'BASE (€)': f.total or '',
                'CUOTA IVA': '',
                'TOTAL FAC': f.total or '',
                'CUADRE': f.cuadre,
                'ARCHIVO': f.archivo
            })
    
    # Crear DataFrame y guardar
    df = pd.DataFrame(filas)
    
    # Asegurar que el directorio existe
    ruta.parent.mkdir(parents=True, exist_ok=True)
    
    # Guardar Excel
    df.to_excel(ruta, index=False, sheet_name=nombre_hoja)
    
    return len(filas)


def generar_excel_resumen(facturas: List['Factura'], ruta: Path) -> int:
    """
    Genera un Excel resumen con totales por proveedor.
    
    Args:
        facturas: Lista de facturas procesadas
        ruta: Ruta donde guardar el archivo
        
    Returns:
        Número de filas generadas
    """
    # Agrupar por proveedor
    resumen = {}
    for f in facturas:
        prov = f.proveedor or 'DESCONOCIDO'
        if prov not in resumen:
            resumen[prov] = {
                'facturas': 0,
                'total': 0.0,
                'lineas': 0,
                'ok': 0,
                'errores': 0
            }
        resumen[prov]['facturas'] += 1
        resumen[prov]['total'] += f.total or 0
        resumen[prov]['lineas'] += len(f.lineas)
        if f.cuadre == 'OK':
            resumen[prov]['ok'] += 1
        else:
            resumen[prov]['errores'] += 1
    
    # Convertir a filas
    filas = []
    for prov, datos in sorted(resumen.items()):
        filas.append({
            'PROVEEDOR': prov,
            'FACTURAS': datos['facturas'],
            'TOTAL €': round(datos['total'], 2),
            'LINEAS': datos['lineas'],
            'OK': datos['ok'],
            'ERRORES': datos['errores'],
            '% ÉXITO': f"{100 * datos['ok'] / datos['facturas']:.1f}%" if datos['facturas'] > 0 else '0%'
        })
    
    df = pd.DataFrame(filas)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    df.to_excel(ruta, index=False, sheet_name='Resumen')
    
    return len(filas)


def generar_excel_errores(facturas: List['Factura'], ruta: Path) -> int:
    """
    Genera un Excel con las facturas que tienen errores.
    
    Args:
        facturas: Lista de facturas procesadas
        ruta: Ruta donde guardar el archivo
        
    Returns:
        Número de filas generadas
    """
    filas = []
    
    for f in facturas:
        if f.tiene_errores or f.cuadre != 'OK':
            filas.append({
                '#': f.numero,
                'ARCHIVO': f.archivo,
                'PROVEEDOR': f.proveedor,
                'FECHA': f.fecha or '',
                'TOTAL': f.total or '',
                'CUADRE': f.cuadre,
                'ERRORES': ', '.join(f.errores) if f.errores else '',
                'LINEAS': len(f.lineas),
                'RUTA': str(f.ruta) if f.ruta else ''
            })
    
    if filas:
        df = pd.DataFrame(filas)
        ruta.parent.mkdir(parents=True, exist_ok=True)
        df.to_excel(ruta, index=False, sheet_name='Errores')
    
    return len(filas)


def generar_excel_multihoja(facturas: List['Factura'], ruta: Path) -> dict:
    """
    Genera un Excel con múltiples hojas:
    - Detalle: todas las líneas
    - Resumen: totales por proveedor
    - Errores: facturas con problemas
    
    Args:
        facturas: Lista de facturas procesadas
        ruta: Ruta donde guardar el archivo
        
    Returns:
        Dict con conteo de filas por hoja
    """
    ruta.parent.mkdir(parents=True, exist_ok=True)
    
    with pd.ExcelWriter(ruta, engine='openpyxl') as writer:
        # Hoja 1: Detalle
        filas_detalle = []
        for f in facturas:
            if f.lineas:
                for linea in f.lineas:
                    filas_detalle.append({
                        '#': f.numero,
                        'FECHA': f.fecha or '',
                        'PROVEEDOR': f.proveedor,
                        'ARTICULO': linea.articulo,
                        'CATEGORIA': linea.categoria or 'PENDIENTE',
                        'CANTIDAD': linea.cantidad if linea.cantidad else '',
                        'PRECIO_UD': linea.precio_ud if linea.precio_ud else '',
                        'IVA': linea.iva,
                        'BASE': linea.base,
                        'TOTAL FAC': f.total or '',
                        'CUADRE': f.cuadre
                    })
            else:
                filas_detalle.append({
                    '#': f.numero,
                    'FECHA': f.fecha or '',
                    'PROVEEDOR': f.proveedor,
                    'ARTICULO': 'VER FACTURA',
                    'CATEGORIA': 'PENDIENTE',
                    'CANTIDAD': '',
                    'PRECIO_UD': '',
                    'IVA': '',
                    'BASE': f.total or '',
                    'TOTAL FAC': f.total or '',
                    'CUADRE': f.cuadre
                })
        
        df_detalle = pd.DataFrame(filas_detalle)
        df_detalle.to_excel(writer, index=False, sheet_name='Detalle')
        
        # Hoja 2: Resumen
        resumen = {}
        for f in facturas:
            prov = f.proveedor or 'DESCONOCIDO'
            if prov not in resumen:
                resumen[prov] = {'facturas': 0, 'total': 0.0, 'ok': 0}
            resumen[prov]['facturas'] += 1
            resumen[prov]['total'] += f.total or 0
            if f.cuadre == 'OK':
                resumen[prov]['ok'] += 1
        
        filas_resumen = [
            {'PROVEEDOR': p, 'FACTURAS': d['facturas'], 'TOTAL': round(d['total'], 2), 
             'OK': d['ok'], '%': f"{100*d['ok']/d['facturas']:.0f}%"}
            for p, d in sorted(resumen.items())
        ]
        df_resumen = pd.DataFrame(filas_resumen)
        df_resumen.to_excel(writer, index=False, sheet_name='Resumen')
        
        # Hoja 3: Errores
        filas_errores = [
            {'ARCHIVO': f.archivo, 'PROVEEDOR': f.proveedor, 'CUADRE': f.cuadre, 
             'ERRORES': ', '.join(f.errores)}
            for f in facturas if f.tiene_errores or f.cuadre != 'OK'
        ]
        df_errores = pd.DataFrame(filas_errores)
        df_errores.to_excel(writer, index=False, sheet_name='Errores')
    
    return {
        'Detalle': len(filas_detalle),
        'Resumen': len(filas_resumen),
        'Errores': len(filas_errores)
    }
