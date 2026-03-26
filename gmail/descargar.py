# -*- coding: utf-8 -*-
"""
DESCARGAR.PY - Módulo de descarga de adjuntos
Gestión de facturas - TASCA BAREA S.L.L.
"""

import os
import re
from datetime import datetime
from typing import Optional
from email.message import Message

from gmail_config import (
    EXTENSIONES_VALIDAS,
    EXTENSIONES_IGNORAR,
    PALABRAS_FACTURA_NOMBRE,
    TEMP_BACKUP_DIR,
    OUTPUTS_DIR
)


# =============================================================================
# FILTRADO DE ADJUNTOS
# =============================================================================

def es_extension_valida(nombre_archivo: str) -> bool:
    """
    Verifica si el archivo tiene extensión válida (PDF, JPG, etc.).
    
    Args:
        nombre_archivo: Nombre del archivo con extensión
    
    Returns:
        True si es extensión válida
    """
    if not nombre_archivo:
        return False
    
    ext = os.path.splitext(nombre_archivo.lower())[1]
    return ext in EXTENSIONES_VALIDAS


def es_extension_ignorar(nombre_archivo: str) -> bool:
    """
    Verifica si el archivo debe ser ignorado (XLS, DOC, etc.).
    
    Args:
        nombre_archivo: Nombre del archivo con extensión
    
    Returns:
        True si debe ignorarse
    """
    if not nombre_archivo:
        return True
    
    ext = os.path.splitext(nombre_archivo.lower())[1]
    return ext in EXTENSIONES_IGNORAR


def es_imagen_firma(nombre_archivo: str, tamaño: int) -> bool:
    """
    Detecta si una imagen es probablemente una firma/logo (no factura).
    
    Criterios:
    - Nombre genérico: image001.jpg, Outlook-xxx.png
    - Tamaño muy pequeño (< 50KB para imágenes)
    
    Args:
        nombre_archivo: Nombre del archivo
        tamaño: Tamaño en bytes
    
    Returns:
        True si parece firma/logo
    """
    nombre_lower = nombre_archivo.lower()
    
    # Patrones de imágenes de firma/logo
    patrones_firma = [
        r'^image\d+\.',           # image001.jpg, image012.png
        r'^outlook-',             # Outlook-xxx.png
        r'^logo',                 # logo.png, logo_empresa.jpg
        r'^firma',                # firma.png
        r'^signature',            # signature.png
    ]
    
    for patron in patrones_firma:
        if re.match(patron, nombre_lower):
            return True
    
    # Imágenes muy pequeñas (< 30KB) probablemente son iconos/firmas
    ext = os.path.splitext(nombre_lower)[1]
    if ext in {'.png', '.jpg', '.jpeg', '.gif'} and tamaño < 30000:
        return True
    
    return False


def es_comprobante_transferencia(nombre_archivo: str, remitente: str) -> bool:
    """
    Detecta si es un comprobante de transferencia (no factura de proveedor).
    
    Args:
        nombre_archivo: Nombre del archivo
        remitente: Email del remitente
    
    Returns:
        True si es comprobante de transferencia
    """
    nombre_lower = nombre_archivo.lower()
    
    # Comprobantes de transferencia propios
    if 'transfer' in nombre_lower and 'tascabarea' in remitente.lower():
        return True
    
    return False


def parece_factura(nombre_archivo: str) -> bool:
    """
    Verifica si el nombre sugiere que es una factura.
    
    Args:
        nombre_archivo: Nombre del archivo
    
    Returns:
        True si parece factura por el nombre
    """
    nombre_lower = nombre_archivo.lower()
    
    for palabra in PALABRAS_FACTURA_NOMBRE:
        if palabra in nombre_lower:
            return True
    
    # También aceptar PDFs con códigos/números (probablemente facturas)
    # Ej: FAG3564.pdf, F260025.pdf, 064062613175.PDF
    if nombre_lower.endswith('.pdf'):
        # Si tiene números, probablemente es factura
        if re.search(r'\d{3,}', nombre_archivo):
            return True
    
    return False


def clasificar_adjunto(adjunto: dict, remitente: str) -> dict:
    """
    Clasifica un adjunto y decide si procesarlo.
    
    Args:
        adjunto: Dict con 'nombre', 'tipo', 'tamaño', 'datos'
        remitente: Email del remitente
    
    Returns:
        Dict con clasificación añadida
    """
    nombre = adjunto.get('nombre', '')
    tamaño = adjunto.get('tamaño', 0)
    
    resultado = adjunto.copy()
    resultado['procesar'] = False
    resultado['razon'] = ''
    resultado['tipo_archivo'] = 'desconocido'
    
    # 1. Verificar extensión
    if es_extension_ignorar(nombre):
        resultado['razon'] = 'Extensión ignorada (xls, doc, etc.)'
        resultado['tipo_archivo'] = 'ignorar'
        return resultado
    
    if not es_extension_valida(nombre):
        resultado['razon'] = 'Extensión no válida'
        resultado['tipo_archivo'] = 'ignorar'
        return resultado
    
    # 2. Verificar si es imagen de firma/logo
    if es_imagen_firma(nombre, tamaño):
        resultado['razon'] = 'Parece imagen de firma/logo'
        resultado['tipo_archivo'] = 'firma'
        return resultado
    
    # 3. Verificar si es comprobante de transferencia propio
    if es_comprobante_transferencia(nombre, remitente):
        resultado['razon'] = 'Comprobante de transferencia propio'
        resultado['tipo_archivo'] = 'transferencia'
        return resultado
    
    # 4. Verificar si parece factura
    if parece_factura(nombre):
        resultado['procesar'] = True
        resultado['razon'] = 'Parece factura'
        resultado['tipo_archivo'] = 'factura'
        return resultado
    
    # 5. PDF sin nombre claro - procesar con precaución
    ext = os.path.splitext(nombre.lower())[1]
    if ext == '.pdf':
        resultado['procesar'] = True
        resultado['razon'] = 'PDF (verificar contenido)'
        resultado['tipo_archivo'] = 'pdf_verificar'
        return resultado
    
    # 6. Imagen grande - podría ser factura escaneada
    if ext in {'.jpg', '.jpeg'} and tamaño > 50000:
        resultado['procesar'] = True
        resultado['razon'] = 'Imagen grande (posible factura escaneada)'
        resultado['tipo_archivo'] = 'imagen_factura'
        return resultado
    
    # Por defecto, no procesar
    resultado['razon'] = 'No identificado como factura'
    return resultado


# =============================================================================
# DESCARGA DE ARCHIVOS
# =============================================================================

def crear_carpeta_backup(fecha: datetime = None) -> str:
    """
    Crea carpeta de backup temporal para la fecha.
    
    Args:
        fecha: Fecha para la carpeta (default: hoy)
    
    Returns:
        Ruta de la carpeta creada
    """
    if fecha is None:
        fecha = datetime.now()
    
    fecha_str = fecha.strftime("%Y-%m-%d")
    carpeta = os.path.join(TEMP_BACKUP_DIR, fecha_str)
    
    os.makedirs(carpeta, exist_ok=True)
    
    return carpeta


def guardar_adjunto_temporal(adjunto: dict, email_id: str, carpeta_backup: str) -> Optional[str]:
    """
    Guarda un adjunto en la carpeta temporal de backup.
    
    Args:
        adjunto: Dict con 'nombre', 'datos'
        email_id: ID del email (para evitar colisiones)
        carpeta_backup: Ruta de la carpeta de backup
    
    Returns:
        Ruta del archivo guardado o None si error
    """
    nombre = adjunto.get('nombre', 'sin_nombre')
    datos = adjunto.get('datos')
    
    if not datos:
        return None
    
    # Nombre único: email_id + nombre original
    nombre_seguro = re.sub(r'[<>:"/\\|?*]', '_', nombre)
    nombre_archivo = f"{email_id}_{nombre_seguro}"
    
    ruta_completa = os.path.join(carpeta_backup, nombre_archivo)
    
    try:
        with open(ruta_completa, 'wb') as f:
            f.write(datos)
        return ruta_completa
    except Exception as e:
        print(f"Error guardando {nombre}: {e}")
        return None


# =============================================================================
# PROCESAMIENTO DE EMAIL
# =============================================================================

def procesar_adjuntos_email(adjuntos: list[dict], remitente: str, email_id: str, 
                            carpeta_backup: str) -> dict:
    """
    Procesa todos los adjuntos de un email.
    
    Args:
        adjuntos: Lista de adjuntos
        remitente: Email del remitente
        email_id: ID único del email
        carpeta_backup: Carpeta para guardar backups
    
    Returns:
        Dict con resumen del procesamiento
    """
    resultado = {
        'total': len(adjuntos),
        'procesados': 0,
        'ignorados': 0,
        'errores': 0,
        'archivos': []
    }
    
    for adj in adjuntos:
        # Clasificar
        clasificado = clasificar_adjunto(adj, remitente)
        
        info_archivo = {
            'nombre_original': adj.get('nombre', ''),
            'tamaño': adj.get('tamaño', 0),
            'procesar': clasificado['procesar'],
            'tipo': clasificado['tipo_archivo'],
            'razon': clasificado['razon'],
            'ruta_backup': None
        }
        
        if clasificado['procesar']:
            # Guardar en backup temporal
            ruta = guardar_adjunto_temporal(adj, email_id, carpeta_backup)
            if ruta:
                info_archivo['ruta_backup'] = ruta
                resultado['procesados'] += 1
            else:
                resultado['errores'] += 1
        else:
            resultado['ignorados'] += 1
        
        resultado['archivos'].append(info_archivo)
    
    return resultado


# =============================================================================
# TEST
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("TEST MÓDULO DESCARGAR")
    print("=" * 60)
    
    # Test clasificación
    test_adjuntos = [
        {'nombre': 'Factura 123.pdf', 'tamaño': 50000},
        {'nombre': 'image001.jpg', 'tamaño': 2000},
        {'nombre': 'Outlook-xxx.png', 'tamaño': 15000},
        {'nombre': 'transfer - 2026-01-15.pdf', 'tamaño': 90000},
        {'nombre': 'FAG3564.pdf', 'tamaño': 6000},
        {'nombre': 'PROVEEDOR 2025.XLS', 'tamaño': 200000},
        {'nombre': 'documento.pdf', 'tamaño': 100000},
    ]
    
    print("\nClasificación de adjuntos de prueba:")
    print("-" * 60)
    
    for adj in test_adjuntos:
        resultado = clasificar_adjunto(adj, 'proveedor@ejemplo.com')
        estado = "✅ PROCESAR" if resultado['procesar'] else "❌ IGNORAR"
        print(f"{estado} | {adj['nombre']}")
        print(f"         Razón: {resultado['razon']}")
        print()
    
    # Test con remitente Tasca Barea (comprobantes propios)
    print("\nTest comprobante transferencia propio:")
    adj_transfer = {'nombre': 'transfer - 2026-01-15.pdf', 'tamaño': 90000}
    resultado = clasificar_adjunto(adj_transfer, 'tascabarea@gmail.com')
    print(f"Remitente: tascabarea@gmail.com")
    print(f"Resultado: {'IGNORAR' if not resultado['procesar'] else 'PROCESAR'}")
    print(f"Razón: {resultado['razon']}")
