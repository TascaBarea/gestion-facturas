# -*- coding: utf-8 -*-
"""
CONFIGURACIÓN MÓDULO GMAIL v1.1
Gestión de facturas - TASCA BAREA S.L.L.
"""

import os
import platform
from datetime import datetime

# =============================================================================
# RUTAS DEL SISTEMA
# =============================================================================

_ES_WINDOWS = platform.system() == "Windows"

# Base del proyecto — detección automática Windows/Linux
PROYECTO_BASE = os.environ.get(
    "GESTION_FACTURAS_DIR",
    r"C:\_ARCHIVOS\TRABAJO\Facturas\gestion-facturas" if _ES_WINDOWS else "/opt/gestion-facturas"
)

# Carpetas del proyecto
GMAIL_DIR = os.path.join(PROYECTO_BASE, "gmail")
DATOS_DIR = os.path.join(PROYECTO_BASE, "datos")
OUTPUTS_DIR = os.path.join(PROYECTO_BASE, "outputs")

# Archivos maestros
MAESTRO_PROVEEDORES = os.path.join(DATOS_DIR, "MAESTRO_PROVEEDORES.xlsx")

# Archivos de control
EMAILS_PROCESADOS = os.path.join(OUTPUTS_DIR, "emails_procesados.json")

# Carpeta backup temporal
TEMP_BACKUP_DIR = os.path.join(OUTPUTS_DIR, "temp_backup")

# =============================================================================
# DROPBOX
# =============================================================================

DROPBOX_BASE = os.environ.get(
    "DROPBOX_BASE",
    r"C:\Users\jaime\Dropbox\File inviati\TASCA BAREA S.L.L\CONTABILIDAD" if _ES_WINDOWS else ""
)

# Subcarpetas (se construyen dinámicamente según año/trimestre)
# Ejemplo: FACTURAS 2026/FACTURAS RECIBIDAS/1 TRIMESTRE 2026/

# =============================================================================
# GMAIL
# =============================================================================

GMAIL_EMAIL = "tascabarea@gmail.com"
GMAIL_IMAP_SERVER = "imap.gmail.com"
GMAIL_IMAP_PORT = 993

# Etiquetas
ETIQUETA_ENTRADA = "FACTURAS"
ETIQUETA_PROCESADO = "FACTURAS_PROCESADAS"

# =============================================================================
# UMBRALES Y CONSTANTES
# =============================================================================

# Fuzzy matching
UMBRAL_FUZZY_PROVEEDOR = 85  # Porcentaje mínimo para match automático
UMBRAL_FUZZY_INDICAR = 70    # Porcentaje mínimo para sugerir

# Extensiones válidas para adjuntos
EXTENSIONES_VALIDAS = {'.pdf', '.jpg', '.jpeg', '.png'}
EXTENSIONES_IGNORAR = {'.xlsx', '.xls', '.doc', '.docx', '.zip', '.rar', '.html'}

# Palabras clave para identificar facturas
PALABRAS_FACTURA_NOMBRE = ['factura', 'invoice', 'fra', 'proforma', 'recibo', 'ticket']
PALABRAS_FACTURA_CONTENIDO = ['factura', 'invoice', 'total', 'iva', 'base imponible', 
                              'importe', 'nif', 'cif', 'fecha']

# =============================================================================
# NOMENCLATURA ARCHIVOS
# =============================================================================

# Tipos de pago (del MAESTRO_PROVEEDORES)
TIPOS_PAGO = {'TF', 'TJ', 'RC', 'EF'}
TIPOS_PAGO_TRANSFERENCIA = {'TF'}  # Solo estos van al Excel PAGOS

# Prefijos especiales
PREFIJO_ATRASADA = "ATRASADA"
PREFIJO_PROFORMA = "PROFORMA"

# =============================================================================
# COLORES EXCEL (para openpyxl)
# =============================================================================

COLOR_ROJO = "FF0000"      # Errores críticos (no pagar)
COLOR_NARANJA = "FFA500"   # Advertencias (revisar)
COLOR_AMARILLO = "FFFF00"  # Info (IBAN extraído de PDF)
COLOR_VERDE = "90EE90"     # OK

# =============================================================================
# FUNCIONES AUXILIARES DE CONFIGURACIÓN
# =============================================================================

def obtener_fecha_hoy():
    """Devuelve fecha actual en formato YYYY-MM-DD."""
    return datetime.now().strftime("%Y-%m-%d")

def obtener_nombre_archivo_salida(tipo: str) -> str:
    """
    Genera nombre de archivo de salida con fecha.
    
    Args:
        tipo: 'pagos', 'log_txt', 'log_json'
    
    Returns:
        Nombre del archivo (sin ruta)
    """
    fecha = obtener_fecha_hoy()
    
    if tipo == 'pagos':
        return f"PAGOS_{fecha}.xlsx"
    elif tipo == 'log_txt':
        return f"gmail_{fecha}.txt"
    elif tipo == 'log_json':
        return f"gmail_{fecha}.json"
    else:
        raise ValueError(f"Tipo de archivo desconocido: {tipo}")

def obtener_ruta_archivo_salida(tipo: str) -> str:
    """Devuelve ruta completa del archivo de salida."""
    nombre = obtener_nombre_archivo_salida(tipo)
    return os.path.join(OUTPUTS_DIR, nombre)

def calcular_trimestre(fecha: datetime) -> str:
    """
    Calcula trimestre en formato XTYY.
    
    Args:
        fecha: Objeto datetime
    
    Returns:
        String como "1T26", "4T25", etc.
    """
    mes = fecha.month
    año = fecha.year % 100  # Últimos 2 dígitos
    
    if mes <= 3:
        trimestre = 1
    elif mes <= 6:
        trimestre = 2
    elif mes <= 9:
        trimestre = 3
    else:
        trimestre = 4
    
    return f"{trimestre}T{año:02d}"

def obtener_carpeta_trimestre(fecha_proceso: datetime, fecha_factura: datetime) -> tuple[str, bool]:
    """
    Determina la carpeta destino y si es atrasada.
    
    Args:
        fecha_proceso: Fecha de ejecución del script
        fecha_factura: Fecha de la factura
    
    Returns:
        Tuple (ruta_carpeta, es_atrasada)
    """
    trimestre_proceso = calcular_trimestre(fecha_proceso)
    trimestre_factura = calcular_trimestre(fecha_factura)
    
    año_proceso = fecha_proceso.year
    num_trimestre = int(trimestre_proceso[0])
    
    # Buscar carpeta (puede ser "1 TRIMESTRE 2026" o "1 TRI 2026")
    carpeta_año = os.path.join(DROPBOX_BASE, f"FACTURAS {año_proceso}", "FACTURAS RECIBIDAS")
    
    # Intentar diferentes formatos de nombre de carpeta
    posibles_nombres = [
        f"{num_trimestre} TRIMESTRE {año_proceso}",
        f"{num_trimestre} TRI {año_proceso}",
    ]
    
    carpeta_trimestre = None
    for nombre in posibles_nombres:
        ruta = os.path.join(carpeta_año, nombre)
        if os.path.exists(ruta):
            carpeta_trimestre = ruta
            break
    
    if carpeta_trimestre is None:
        # Usar el formato por defecto
        carpeta_trimestre = os.path.join(carpeta_año, f"{num_trimestre} TRIMESTRE {año_proceso}")
    
    # Determinar si es atrasada
    es_atrasada = trimestre_factura != trimestre_proceso
    
    if es_atrasada:
        carpeta_final = os.path.join(carpeta_trimestre, "ATRASADAS")
    else:
        carpeta_final = carpeta_trimestre
    
    return carpeta_final, es_atrasada


# =============================================================================
# VALIDACIÓN DE CONFIGURACIÓN
# =============================================================================

def validar_configuracion() -> tuple[bool, list[str]]:
    """
    Valida que la configuración básica es correcta.
    
    Returns:
        Tuple (es_valida, lista_errores)
    """
    errores = []
    
    # Verificar carpetas críticas
    if not os.path.exists(PROYECTO_BASE):
        errores.append(f"No existe carpeta proyecto: {PROYECTO_BASE}")
    
    if not os.path.exists(DATOS_DIR):
        errores.append(f"No existe carpeta datos: {DATOS_DIR}")
    
    if not os.path.exists(OUTPUTS_DIR):
        errores.append(f"No existe carpeta outputs: {OUTPUTS_DIR}")
    
    if not os.path.exists(MAESTRO_PROVEEDORES):
        errores.append(f"No existe MAESTRO_PROVEEDORES: {MAESTRO_PROVEEDORES}")
    
    if not os.path.exists(DROPBOX_BASE):
        errores.append(f"No existe carpeta Dropbox: {DROPBOX_BASE}")
    
    return len(errores) == 0, errores


if __name__ == "__main__":
    # Test de configuración
    print("=" * 60)
    print("TEST DE CONFIGURACIÓN - GMAIL v1.1")
    print("=" * 60)
    
    print(f"\nPROYECTO_BASE: {PROYECTO_BASE}")
    print(f"DROPBOX_BASE: {DROPBOX_BASE}")
    print(f"MAESTRO_PROVEEDORES: {MAESTRO_PROVEEDORES}")
    
    print(f"\nFecha hoy: {obtener_fecha_hoy()}")
    print(f"Trimestre actual: {calcular_trimestre(datetime.now())}")
    
    print(f"\nArchivos de salida:")
    print(f"  - {obtener_nombre_archivo_salida('pagos')}")
    print(f"  - {obtener_nombre_archivo_salida('log_txt')}")
    print(f"  - {obtener_nombre_archivo_salida('log_json')}")
    
    print("\nValidando configuración...")
    es_valida, errores = validar_configuracion()
    
    if es_valida:
        print("✅ Configuración válida")
    else:
        print("❌ Errores encontrados:")
        for error in errores:
            print(f"   - {error}")
