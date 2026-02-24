"""
Clases de datos para facturas y líneas.
"""
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from pathlib import Path
from datetime import datetime


@dataclass
class LineaFactura:
    """Representa una línea de factura."""
    articulo: str = ''
    base: float = 0.0
    iva: int = 21
    codigo: str = ''
    cantidad: Optional[float] = None
    precio_ud: Optional[float] = None
    categoria: str = 'PENDIENTE'
    id_categoria: str = ''
    
    @property
    def total(self) -> float:
        """Calcula el total con IVA."""
        return round(self.base * (1 + self.iva / 100), 2)
    
    @property
    def cuota_iva(self) -> float:
        """Calcula la cuota de IVA."""
        return round(self.base * self.iva / 100, 2)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte a diccionario."""
        return {
            'codigo': self.codigo,
            'articulo': self.articulo,
            'cantidad': self.cantidad,
            'precio_ud': self.precio_ud,
            'iva': self.iva,
            'base': self.base,
            'cuota_iva': self.cuota_iva,
            'total': self.total,
            'categoria': self.categoria,
            'id_categoria': self.id_categoria
        }


@dataclass
class Factura:
    """Representa una factura completa."""
    archivo: str
    numero: str
    ruta: Optional[Path] = None
    proveedor: str = ''
    cif: str = ''
    iban: str = ''
    fecha: str = ''
    referencia: str = ''
    total: Optional[float] = None
    lineas: List[LineaFactura] = field(default_factory=list)
    cuadre: str = ''
    errores: List[str] = field(default_factory=list)
    metodo_pdf: str = ''
    texto_raw: str = ''
    procesado_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    @property
    def num_lineas(self) -> int:
        return len(self.lineas)
    
    @property
    def tiene_lineas(self) -> bool:
        return len(self.lineas) > 0
    
    @property
    def total_calculado(self) -> float:
        """Suma de bases de todas las líneas."""
        return sum(linea.base for linea in self.lineas)
    
    @property
    def base_total(self) -> float:
        """Alias de total_calculado."""
        return self.total_calculado
    
    @property
    def iva_total(self) -> float:
        """Suma de cuotas IVA."""
        return sum(linea.cuota_iva for linea in self.lineas)
    
    @property
    def es_ok(self) -> bool:
        return self.cuadre == 'OK'
    
    @property
    def tiene_errores(self) -> bool:
        return len(self.errores) > 0
    
    def agregar_linea(self, linea: LineaFactura) -> None:
        """Agrega una línea a la factura."""
        self.lineas.append(linea)
    
    def agregar_linea_dict(self, datos: Dict[str, Any]) -> None:
        """Agrega una línea desde diccionario."""
        linea = LineaFactura(
            articulo=datos.get('articulo', ''),
            base=datos.get('base', 0.0),
            iva=datos.get('iva', 21),
            codigo=datos.get('codigo', ''),
            cantidad=datos.get('cantidad'),
            precio_ud=datos.get('precio_ud'),
            categoria=datos.get('categoria', 'PENDIENTE'),
            id_categoria=datos.get('id_categoria', '')
        )
        self.lineas.append(linea)
    
    def agregar_error(self, error: str) -> None:
        """Agrega un error a la factura."""
        if error not in self.errores:
            self.errores.append(error)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte a diccionario."""
        return {
            'archivo': self.archivo,
            'numero': self.numero,
            'proveedor': self.proveedor,
            'cif': self.cif,
            'iban': self.iban,
            'fecha': self.fecha,
            'referencia': self.referencia,
            'total': self.total,
            'total_calculado': self.total_calculado,
            'cuadre': self.cuadre,
            'errores': self.errores,
            'num_lineas': self.num_lineas,
            'lineas': [l.to_dict() for l in self.lineas]
        }
    
    def to_filas_excel(self) -> List[Dict[str, Any]]:
        """Genera filas para Excel."""
        filas = []
        if self.lineas:
            for linea in self.lineas:
                filas.append({
                    '#': self.numero,
                    'FECHA': self.fecha,
                    'REF': self.referencia,
                    'PROVEEDOR': self.proveedor,
                    'ARTICULO': linea.articulo,
                    'CATEGORIA': linea.categoria,
                    'CANTIDAD': linea.cantidad,
                    'PRECIO_UD': linea.precio_ud,
                    'IVA': linea.iva,
                    'BASE': linea.base,
                    'TOTAL_FAC': self.total,
                    'CUADRE': self.cuadre
                })
        else:
            filas.append({
                '#': self.numero,
                'FECHA': self.fecha,
                'REF': self.referencia,
                'PROVEEDOR': self.proveedor,
                'ARTICULO': 'VER FACTURA',
                'CATEGORIA': 'PENDIENTE',
                'CANTIDAD': '',
                'PRECIO_UD': '',
                'IVA': '',
                'BASE': self.total or '',
                'TOTAL_FAC': self.total,
                'CUADRE': self.cuadre
            })
        return filas
    
    def __str__(self) -> str:
        return f"Factura({self.numero}, {self.proveedor}, {self.total}€, {self.num_lineas} líneas)"
    
    def __repr__(self) -> str:
        return self.__str__()
