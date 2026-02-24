
from decimal import Decimal, getcontext, ROUND_HALF_UP
from pydantic import BaseModel, Field
from typing import List, Optional, Literal

getcontext().rounding = ROUND_HALF_UP

TipoIVA = Literal[0, 2, 4, 5, 7.5, 10, 21]

class Linea(BaseModel):
    numero_archivo: str
    fecha: str
    numero_factura: str
    proveedor: str
    descripcion: str
    categoria: Optional[str] = None
    base_imponible: Decimal = Field(...)
    tipo_iva: TipoIVA
    observaciones: List[str] = []

class Factura(BaseModel):
    numero_archivo: str
    fecha: Optional[str] = None
    numero_factura: Optional[str] = None
    proveedor: str
    lineas: List[Linea] = []
    total_con_iva: Optional[Decimal] = None
    es_abono: bool = False

class Metadata(BaseModel):
    periodo: str
    proveedores: int
    facturas: int
    lineas: int
    desglose_iva: dict
    incidencias: List[str] = []
