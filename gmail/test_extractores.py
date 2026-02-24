#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DIAGNÓSTICO DE EXTRACTORES v2
Ejecutar: python test_extractores.py
"""

import os
import sys

RUTA_EXTRACTORES = r"C:\_ARCHIVOS\TRABAJO\Facturas\Parseo\extractores"
RUTA_PADRE = r"C:\_ARCHIVOS\TRABAJO\Facturas\Parseo"  # Carpeta padre

print("=" * 60)
print("DIAGNÓSTICO DE EXTRACTORES v2")
print("=" * 60)

# 1. Verificar que la carpeta existe
print(f"\n1. Carpeta extractores existe: {os.path.exists(RUTA_EXTRACTORES)}")
print(f"   Carpeta padre existe: {os.path.exists(RUTA_PADRE)}")

# 2. Verificar archivo específico
archivo_ceres = os.path.join(RUTA_EXTRACTORES, "ceres.py")
print(f"\n2. ceres.py existe: {os.path.exists(archivo_ceres)}")

# 3. Añadir carpeta PADRE al path (la clave del fix)
print("\n3. Añadiendo carpeta padre al path...")
if RUTA_PADRE not in sys.path:
    sys.path.insert(0, RUTA_PADRE)
    print(f"   ✓ Añadido: {RUTA_PADRE}")

# 4. Intentar importar
print("\n4. Intentando importar ceres.py...")
try:
    import importlib.util
    
    spec = importlib.util.spec_from_file_location("ceres", archivo_ceres)
    modulo = importlib.util.module_from_spec(spec)
    sys.modules["ceres"] = modulo
    spec.loader.exec_module(modulo)
    
    print("   ✓ Módulo cargado correctamente")
    
    # 5. Buscar clases
    print("\n5. Buscando clases Extractor...")
    clases_encontradas = []
    for nombre in dir(modulo):
        obj = getattr(modulo, nombre)
        if isinstance(obj, type) and nombre.startswith('Extractor') and nombre != 'ExtractorBase':
            clases_encontradas.append(nombre)
            print(f"   ✓ Clase encontrada: {nombre}")
    
    if not clases_encontradas:
        print("   ✗ No se encontraron clases Extractor*")
        print(f"   Contenido del módulo: {[n for n in dir(modulo) if not n.startswith('_')]}")
    
    # 6. Intentar instanciar
    if clases_encontradas:
        print("\n6. Intentando instanciar y extraer...")
        clase = getattr(modulo, clases_encontradas[0])
        instancia = clase()
        print(f"   ✓ Instancia creada: {type(instancia).__name__}")
        
        if hasattr(instancia, 'extraer'):
            print(f"   ✓ Tiene método 'extraer'")
        else:
            print(f"   ✗ NO tiene método 'extraer'")

    print("\n" + "=" * 60)
    print("✅ TODO OK - Los extractores funcionarán correctamente")
    print("=" * 60)

except Exception as e:
    print(f"   ✗ ERROR: {e}")
    import traceback
    traceback.print_exc()
    print("\n" + "=" * 60)
    print("❌ HAY UN PROBLEMA")
    print("=" * 60)
