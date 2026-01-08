"""
Funciones de validación de facturas.
"""
from typing import List, Optional, Dict, Any, TYPE_CHECKING
from config.settings import TOLERANCIA_CUADRE

if TYPE_CHECKING:
    from nucleo.factura import Factura, LineaFactura


def validar_cuadre(lineas: List['LineaFactura'], total: Optional[float], tolerancia: float = None) -> str:
    """
    Valida que la suma de líneas cuadre con el total.
    
    Args:
        lineas: Lista de líneas de factura
        total: Total declarado en la factura
        tolerancia: Tolerancia en euros (default: TOLERANCIA_CUADRE)
        
    Returns:
        'OK', 'SIN_TOTAL', 'SIN_LINEAS', o 'DESCUADRE_X.XX'
    """
    if tolerancia is None:
        tolerancia = TOLERANCIA_CUADRE
    
    if total is None or total == 0:
        return 'SIN_TOTAL'
    
    if not lineas:
        return 'SIN_LINEAS'
    
    # Calcular suma de bases
    suma_bases = sum(linea.base for linea in lineas)
    
    # Calcular suma con IVA
    suma_con_iva = sum(linea.base * (1 + linea.iva / 100) for linea in lineas)
    
    # Intentar cuadrar con suma de bases (facturas que muestran base)
    diff_base = abs(suma_bases - total)
    if diff_base <= tolerancia:
        return 'OK'
    
    # Intentar cuadrar con suma con IVA (facturas que muestran total)
    diff_total = abs(suma_con_iva - total)
    if diff_total <= tolerancia:
        return 'OK'
    
    # No cuadra
    diff = min(diff_base, diff_total)
    return f'DESCUADRE_{diff:.2f}'


def calcular_total_lineas(lineas: List['LineaFactura']) -> float:
    """Calcula la suma de bases de las líneas."""
    return sum(linea.base for linea in lineas)


def calcular_base_total(lineas: List['LineaFactura']) -> float:
    """Alias de calcular_total_lineas."""
    return calcular_total_lineas(lineas)


def validar_factura(factura: 'Factura') -> List[str]:
    """
    Valida una factura y devuelve lista de errores.
    
    Args:
        factura: Objeto Factura a validar
        
    Returns:
        Lista de códigos de error
    """
    errores = []
    
    # Validar proveedor
    if not factura.proveedor or factura.proveedor in ['DESCONOCIDO', 'PENDIENTE', '']:
        errores.append('PROVEEDOR_PENDIENTE')
    
    # Validar fecha
    if not factura.fecha:
        errores.append('FECHA_PENDIENTE')
    
    # Validar CIF
    if not factura.cif:
        errores.append('CIF_PENDIENTE')
    
    # Validar total
    if factura.total is None or factura.total == 0:
        errores.append('SIN_TOTAL')
    
    # Validar líneas
    if not factura.lineas:
        errores.append('SIN_LINEAS')
    
    # Validar cuadre
    if factura.cuadre and factura.cuadre.startswith('DESCUADRE'):
        errores.append(factura.cuadre)
    
    return errores


def es_factura_valida(factura: 'Factura') -> bool:
    """
    Determina si una factura es válida (sin errores críticos).
    
    Args:
        factura: Objeto Factura
        
    Returns:
        True si la factura es válida
    """
    errores = validar_factura(factura)
    
    # Errores críticos
    criticos = ['SIN_TOTAL', 'SIN_LINEAS']
    
    for error in errores:
        if error in criticos or error.startswith('DESCUADRE'):
            return False
    
    return True


def generar_clave_factura(factura: 'Factura') -> str:
    """
    Genera una clave única para detectar duplicados.
    
    Formato: PROVEEDOR|FECHA|TOTAL
    """
    proveedor = (factura.proveedor or '').upper().strip()
    fecha = factura.fecha or ''
    total = f"{factura.total:.2f}" if factura.total else '0.00'
    
    return f"{proveedor}|{fecha}|{total}"


def detectar_duplicado(factura: 'Factura', registro: Dict[str, Any]) -> bool:
    """
    Detecta si una factura ya está en el registro.
    
    Args:
        factura: Factura a verificar
        registro: Diccionario con facturas procesadas
        
    Returns:
        True si es duplicado
    """
    clave = generar_clave_factura(factura)
    return clave in registro


def cargar_registro(ruta) -> Dict[str, Any]:
    """Carga registro de facturas procesadas."""
    import json
    from pathlib import Path
    
    ruta = Path(ruta)
    if ruta.exists():
        with open(ruta, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def guardar_registro(registro: Dict[str, Any], ruta) -> None:
    """Guarda registro de facturas procesadas."""
    import json
    from pathlib import Path
    
    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with open(ruta, 'w', encoding='utf-8') as f:
        json.dump(registro, f, ensure_ascii=False, indent=2)


def agregar_al_registro(factura: 'Factura', registro: Dict[str, Any]) -> None:
    """Agrega una factura al registro."""
    clave = generar_clave_factura(factura)
    registro[clave] = {
        'archivo': factura.archivo,
        'proveedor': factura.proveedor,
        'fecha': factura.fecha,
        'total': factura.total,
        'procesado': factura.procesado_at
    }
