"""
Clasificadores Mejorados v2.0
Fecha: 26/01/2026

Paquete de clasificadores para el sistema CUADRE.

CLASIFICADORES INCLUIDOS:
- telefono_yoigo.py: YOIGO/XFERA con búsqueda fuzzy
- suscripciones.py: MAKE, OPENAI, LOYVERSE, SPOTIFY
- comunidad_ista.py: COM PROP RODAS + facturas ISTA
- ay_madre.py: AY MADRE LA FRUTA → GARCIA VIVAS JULIO
- alquiler.py: BENJAMIN ORTEGA Y JAIME → facturas mensuales
- router.py: Orquestador de todos los clasificadores
"""

from .router import clasificar_movimiento, reset_todos_clasificadores
from .telefono_yoigo import clasificar_yoigo
from .suscripciones import clasificar_suscripcion
from .comunidad_ista import clasificar_comunidad_ista
from .ay_madre import clasificar_ay_madre
from .alquiler import clasificar_alquiler

__version__ = "2.0"
__date__ = "26/01/2026"
