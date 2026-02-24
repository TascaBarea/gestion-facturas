#!/usr/bin/env python3
"""Test específico para borboton.py"""
import os
import sys

# Añadir carpeta padre al path
RUTA_PADRE = r"C:\_ARCHIVOS\TRABAJO\Facturas\Parseo"
sys.path.insert(0, RUTA_PADRE)

print("=" * 60)
print("TEST EXTRACTOR BORBOTON")
print("=" * 60)

try:
    # Importar
    import importlib.util
    ruta = r"C:\_ARCHIVOS\TRABAJO\Facturas\Parseo\extractores\borboton.py"
    
    print(f"\n1. Archivo existe: {os.path.exists(ruta)}")
    
    spec = importlib.util.spec_from_file_location("borboton", ruta)
    modulo = importlib.util.module_from_spec(spec)
    sys.modules["borboton"] = modulo
    spec.loader.exec_module(modulo)
    
    print("2. Módulo cargado ✓")
    
    # Buscar clase
    clase = None
    for nombre in dir(modulo):
        obj = getattr(modulo, nombre)
        if isinstance(obj, type) and nombre.startswith('Extractor') and nombre != 'ExtractorBase':
            clase = obj
            print(f"3. Clase encontrada: {nombre} ✓")
            break
    
    if clase:
        instancia = clase()
        print(f"4. Instancia creada ✓")
        print(f"5. Tiene método extraer: {hasattr(instancia, 'extraer')}")
        
        # Ver qué métodos tiene
        metodos = [m for m in dir(instancia) if not m.startswith('_') and callable(getattr(instancia, m))]
        print(f"6. Métodos disponibles: {metodos}")
    
except Exception as e:
    print(f"\n❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
