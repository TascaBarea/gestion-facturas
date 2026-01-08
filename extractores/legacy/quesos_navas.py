"""
Extractor para QUESOS NAVAS, S.L. (Carlos Navas)

Quesería artesanal de Peñaranda de Bracamonte (Salamanca).
Quesos de oveja curados y semicurados.

CIF: B37416419
IBAN: REDACTED_IBAN

Productos (IVA 4% - quesos):
- Queso Gran Reserva 10 meses
- Queso Oveja Invierno 2 años
- Queso de Oveja 15 meses mini

Formato líneas:
CODIGO ARTICULO LOTE CANTIDAD PRECIO IVA SUBTOTAL
5 QUESO GRAN RESERVA 10 MESES 8524 6,005 18,170 4,00 109,11

Creado: 18/12/2025
Corregido: 01/01/2026 - Fix orden campos en regex
Validado: 1/1 facturas (1T25)
"""
from extractores.base import ExtractorBase
from extractores import registrar
from typing import List, Dict, Optional
import re


@registrar('CARLOS NAVAS', 'QUESERIA CARLOS NAVAS', 'QUESERIA NAVAS', 
           'QUESOS NAVAS', 'QUESOS CARLOS NAVAS')
class ExtractorQuesosNavas(ExtractorBase):
    """Extractor para facturas de Quesos Navas (Carlos Navas)."""
    
    nombre = 'QUESOS NAVAS'
    cif = 'B37416419'
    iban = 'REDACTED_IBAN'
    metodo_pdf = 'pdfplumber'
    categoria_fija = 'QUESO PARA TABLA'
    
    def _convertir_importe(self, texto: str) -> float:
        """Convierte texto a float (formato europeo)."""
        if not texto:
            return 0.0
        texto = str(texto).strip()
        if '.' in texto and ',' in texto:
            texto = texto.replace('.', '').replace(',', '.')
        elif ',' in texto:
            texto = texto.replace(',', '.')
        try:
            return float(texto)
        except:
            return 0.0
    
    def extraer_lineas(self, texto: str) -> List[Dict]:
        """
        Extrae líneas de productos.
        
        Formato:
        CODIGO ARTICULO LOTE CANTIDAD PRECIO IVA SUBTOTAL
        5 QUESO GRAN RESERVA 10 MESES 8524 6,005 18,170 4,00 109,11
        
        - Código: 1-2 dígitos
        - Artículo: empieza con QUESO
        - Lote: 4-5 dígitos
        - Cantidad: kg con 3 decimales (6,005)
        - Precio: €/kg con 3 decimales (18,170)
        - IVA: con 2 decimales (4,00)
        - Subtotal: con 2 decimales (109,11)
        """
        lineas = []
        
        patron = re.compile(
            r'^(\d{1,2})\s+'                           # Código (1-2 dígitos)
            r'(QUESO[A-ZÑÁÉÍÓÚ\s\d]+?)\s+'             # Artículo
            r'(\d{4,5})\s+'                            # Lote (4-5 dígitos)
            r'(\d+,\d{3})\s+'                          # Cantidad (X,XXX)
            r'(\d+,\d{3})\s+'                          # Precio (XX,XXX)
            r'(\d+,\d{2})\s+'                          # IVA (X,XX)
            r'(\d+,\d{2})',                            # Subtotal (XXX,XX)
            re.MULTILINE
        )
        
        for match in patron.finditer(texto):
            codigo, articulo, lote, cantidad, precio, iva_txt, subtotal = match.groups()
            
            iva_valor = int(self._convertir_importe(iva_txt))
            
            lineas.append({
                'codigo': codigo,
                'articulo': articulo.strip()[:50],
                'cantidad': self._convertir_importe(cantidad),
                'precio_ud': self._convertir_importe(precio),
                'iva': iva_valor,
                'base': self._convertir_importe(subtotal),
                'lote': lote,
                'categoria': self.categoria_fija
            })
        
        return lineas
    
    def extraer_total(self, texto: str) -> Optional[float]:
        """Extrae total de la factura."""
        # Buscar "TOTAL FACTURA" seguido de número
        m = re.search(r'TOTAL\s+FACTURA\s*([\d,.]+)\s*€?', texto)
        if m:
            return self._convertir_importe(m.group(1))
        
        # Buscar en vencimientos: "26/02/2025 666,30€"
        m2 = re.search(r'Vencimientos\s*:\s*[\d/]+\s*([\d,.]+)\s*€', texto)
        if m2:
            return self._convertir_importe(m2.group(1))
        
        return None
    
    def extraer_fecha(self, texto: str) -> Optional[str]:
        """Extrae fecha de la factura."""
        # Buscar en cabecera: "Fecha 26/02/2025"
        m = re.search(r'Fecha\s+(\d{2}/\d{2}/\d{4})', texto)
        if m:
            return m.group(1)
        return None
    
    def extraer_referencia(self, texto: str) -> Optional[str]:
        """Extrae número de factura."""
        # Formato: "Nº Factura A/97"
        m = re.search(r'Nº\s*Factura\s*([A-Z]?/?\.?\d+)', texto)
        if m:
            return m.group(1)
        return None
