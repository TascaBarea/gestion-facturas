"""
Sistema de extractores de facturas.

Cada extractor es una clase que hereda de ExtractorBase y se registra
automaticamente con el decorador @registrar.

Actualizado: 02/01/2026 (v5.10 - CARGA AUTOMATICA)

Este __init__.py carga AUTOMATICAMENTE todos los archivos .py
de la carpeta extractores (excepto los de legacy/).
"""

# Registro global de extractores
_EXTRACTORES = {}


def registrar(*nombres):
    """
    Decorador para registrar un extractor con uno o mas nombres.
    """
    def decorator(cls):
        for nombre in nombres:
            _EXTRACTORES[nombre.upper()] = cls
        return cls
    return decorator


def obtener_extractor(proveedor: str):
    """Obtiene el extractor adecuado para un proveedor."""
    if not proveedor:
        return None
    
    proveedor_upper = proveedor.upper().strip()
    
    # Busqueda exacta
    if proveedor_upper in _EXTRACTORES:
        return _EXTRACTORES[proveedor_upper]()
    
    # Busqueda parcial
    for nombre, clase in _EXTRACTORES.items():
        if nombre in proveedor_upper or proveedor_upper in nombre:
            return clase()
    
    return None


def listar_extractores() -> dict:
    """Lista todos los extractores registrados."""
    return _EXTRACTORES.copy()


def tiene_extractor(proveedor: str) -> bool:
    """Comprueba si existe un extractor para el proveedor."""
    return obtener_extractor(proveedor) is not None


# Constante para acceso externo
EXTRACTORES = _EXTRACTORES


# Importar la clase base
from extractores.base import ExtractorBase


# ============================================================
# CARGA AUTOMATICA DE EXTRACTORES
# ============================================================
# Carga todos los archivos .py de la carpeta extractores/
# Ignora: base.py, generico.py, _plantilla.py, __init__.py
# Ignora: carpeta legacy/

import importlib
import os
from pathlib import Path

# Obtener la carpeta de extractores
_extractores_dir = Path(__file__).parent

# Archivos a ignorar
_ignorar = {'base.py', 'generico.py', '_plantilla.py', '__init__.py', '__init__Antiguo.py'}

# Cargar cada archivo .py
_errores = []
for _archivo in sorted(_extractores_dir.glob('*.py')):
    if _archivo.name in _ignorar:
        continue
    if _archivo.name.startswith('_'):
        continue
    
    _modulo = _archivo.stem  # nombre sin .py
    try:
        importlib.import_module(f'extractores.{_modulo}')
    except Exception as e:
        _errores.append(f"{_modulo}: {e}")

# Cargar generico al final (menor prioridad)
try:
    from extractores import generico
except ImportError:
    pass

# Mostrar errores si los hay (solo en modo debug)
# if _errores:
#     print(f"Errores cargando extractores:")
#     for err in _errores:
#         print(f"  - {err}")


__all__ = [
    'ExtractorBase',
    'registrar',
    'obtener_extractor',
    'listar_extractores',
    'tiene_extractor',
    'EXTRACTORES'
]
