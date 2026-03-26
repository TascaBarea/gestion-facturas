# -*- coding: utf-8 -*-
"""
GUARDAR.PY - Módulo de guardado en Dropbox
Gestión de facturas - TASCA BAREA S.L.L.

Estructura Dropbox:
  BAREA/FACTURAS/1T26/
  BAREA/FACTURAS/4T25/
  BAREA/FACTURAS/ATRASADAS/4T25/  (opcional, si prefieres separar)
"""

import os
import shutil
from datetime import datetime
from typing import Optional

from gmail_config import DROPBOX_FACTURAS_BASE


# =============================================================================
# RUTAS DE DESTINO
# =============================================================================

def obtener_carpeta_trimestre(trimestre: str) -> str:
    """
    Obtiene la ruta de la carpeta de Dropbox para un trimestre.
    
    Args:
        trimestre: Trimestre en formato "1T26", "4T25", etc.
    
    Returns:
        Ruta completa de la carpeta
    """
    carpeta = os.path.join(DROPBOX_FACTURAS_BASE, trimestre)
    return carpeta


def asegurar_carpeta_existe(ruta: str) -> bool:
    """
    Crea la carpeta si no existe.
    
    Args:
        ruta: Ruta de la carpeta
    
    Returns:
        True si existe o se creó correctamente
    """
    try:
        os.makedirs(ruta, exist_ok=True)
        return True
    except Exception as e:
        print(f"Error creando carpeta {ruta}: {e}")
        return False


# =============================================================================
# GUARDADO DE ARCHIVOS
# =============================================================================

def guardar_en_dropbox(
    ruta_origen: str,
    nombre_nuevo: str,
    trimestre: str,
    sobrescribir: bool = False
) -> dict:
    """
    Guarda un archivo en la carpeta de Dropbox correspondiente.
    
    Args:
        ruta_origen: Ruta del archivo en backup temporal
        nombre_nuevo: Nombre de archivo con nomenclatura
        trimestre: Trimestre destino ("1T26", "4T25", etc.)
        sobrescribir: Si True, sobrescribe archivos existentes
    
    Returns:
        Dict con resultado del guardado
    """
    resultado = {
        'exito': False,
        'ruta_destino': None,
        'error': None,
        'ya_existia': False
    }
    
    # Verificar origen existe
    if not os.path.exists(ruta_origen):
        resultado['error'] = f"Archivo origen no existe: {ruta_origen}"
        return resultado
    
    # Obtener carpeta destino
    carpeta_destino = obtener_carpeta_trimestre(trimestre)
    
    # Crear carpeta si no existe
    if not asegurar_carpeta_existe(carpeta_destino):
        resultado['error'] = f"No se pudo crear carpeta: {carpeta_destino}"
        return resultado
    
    # Ruta completa destino
    ruta_destino = os.path.join(carpeta_destino, nombre_nuevo)
    resultado['ruta_destino'] = ruta_destino
    
    # Verificar si ya existe
    if os.path.exists(ruta_destino):
        resultado['ya_existia'] = True
        if not sobrescribir:
            resultado['error'] = "Archivo ya existe (no sobrescribir)"
            return resultado
    
    # Copiar archivo
    try:
        shutil.copy2(ruta_origen, ruta_destino)
        resultado['exito'] = True
    except Exception as e:
        resultado['error'] = f"Error copiando: {e}"
    
    return resultado


def mover_a_dropbox(
    ruta_origen: str,
    nombre_nuevo: str,
    trimestre: str,
    sobrescribir: bool = False
) -> dict:
    """
    Mueve un archivo a Dropbox (elimina el origen).
    
    Args:
        ruta_origen: Ruta del archivo en backup temporal
        nombre_nuevo: Nombre de archivo con nomenclatura
        trimestre: Trimestre destino
        sobrescribir: Si True, sobrescribe archivos existentes
    
    Returns:
        Dict con resultado
    """
    # Primero copiar
    resultado = guardar_en_dropbox(ruta_origen, nombre_nuevo, trimestre, sobrescribir)
    
    # Si éxito, eliminar origen
    if resultado['exito']:
        try:
            os.remove(ruta_origen)
        except Exception as e:
            # No es crítico, solo avisar
            print(f"      ⚠️ No se pudo eliminar backup: {e}")
    
    return resultado


# =============================================================================
# PROCESAMIENTO POR LOTES
# =============================================================================

def guardar_lote_dropbox(archivos_procesados: list, modo_test: bool = False) -> dict:
    """
    Guarda un lote de archivos en Dropbox.
    
    Args:
        archivos_procesados: Lista de dicts con info de archivos
            Cada dict debe tener: ruta_backup, nuevo, trimestre (de fecha)
        modo_test: Si True, no guarda realmente (solo simula)
    
    Returns:
        Dict con resumen del proceso
    """
    resumen = {
        'total': len(archivos_procesados),
        'guardados': 0,
        'errores': 0,
        'ya_existian': 0,
        'sin_ruta': 0,
        'detalles': []
    }
    
    for arch in archivos_procesados:
        ruta_backup = arch.get('ruta_backup')
        nombre_nuevo = arch.get('nuevo')
        fecha = arch.get('fecha')
        
        # Validar datos
        if not ruta_backup or not nombre_nuevo:
            resumen['sin_ruta'] += 1
            continue
        
        # Calcular trimestre desde fecha
        if fecha:
            from gmail_config import calcular_trimestre
            trimestre = calcular_trimestre(fecha)
        else:
            # Fallback: trimestre actual
            trimestre = calcular_trimestre(datetime.now())
        
        if modo_test:
            # Solo simular
            carpeta = obtener_carpeta_trimestre(trimestre)
            print(f"      [TEST] {nombre_nuevo} → {carpeta}")
            resumen['guardados'] += 1
            continue
        
        # Guardar realmente
        resultado = guardar_en_dropbox(
            ruta_origen=ruta_backup,
            nombre_nuevo=nombre_nuevo,
            trimestre=trimestre,
            sobrescribir=False
        )
        
        if resultado['exito']:
            resumen['guardados'] += 1
        elif resultado['ya_existia']:
            resumen['ya_existian'] += 1
        else:
            resumen['errores'] += 1
            resumen['detalles'].append({
                'archivo': nombre_nuevo,
                'error': resultado['error']
            })
    
    return resumen


# =============================================================================
# VERIFICACIÓN DE DROPBOX
# =============================================================================

def verificar_dropbox() -> tuple[bool, str]:
    """
    Verifica que la carpeta base de Dropbox existe y es accesible.
    
    Returns:
        Tuple (éxito, mensaje)
    """
    if not os.path.exists(DROPBOX_FACTURAS_BASE):
        return False, f"No existe: {DROPBOX_FACTURAS_BASE}"
    
    if not os.path.isdir(DROPBOX_FACTURAS_BASE):
        return False, f"No es directorio: {DROPBOX_FACTURAS_BASE}"
    
    # Intentar crear carpeta de prueba
    test_dir = os.path.join(DROPBOX_FACTURAS_BASE, "_test_write_")
    try:
        os.makedirs(test_dir, exist_ok=True)
        os.rmdir(test_dir)
    except Exception as e:
        return False, f"Sin permisos de escritura: {e}"
    
    return True, f"OK: {DROPBOX_FACTURAS_BASE}"


# =============================================================================
# TEST
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("TEST MÓDULO GUARDAR (DROPBOX)")
    print("=" * 60)
    
    # Verificar Dropbox
    print("\n1. Verificando carpeta Dropbox...")
    exito, mensaje = verificar_dropbox()
    if exito:
        print(f"   ✅ {mensaje}")
    else:
        print(f"   ❌ {mensaje}")
        print("\n   Verifica la ruta en config.py: DROPBOX_FACTURAS_BASE")
        exit(1)
    
    # Listar carpetas existentes
    print("\n2. Carpetas de trimestres existentes:")
    for item in sorted(os.listdir(DROPBOX_FACTURAS_BASE)):
        ruta = os.path.join(DROPBOX_FACTURAS_BASE, item)
        if os.path.isdir(ruta) and item[0].isdigit():
            num_archivos = len([f for f in os.listdir(ruta) if f.endswith('.pdf')])
            print(f"   📁 {item}/ ({num_archivos} PDFs)")
    
    # Test de ruta
    print("\n3. Test obtener carpeta:")
    for trim in ['1T26', '4T25', '3T25']:
        carpeta = obtener_carpeta_trimestre(trim)
        existe = "✅" if os.path.exists(carpeta) else "❌"
        print(f"   {existe} {trim} → {carpeta}")
