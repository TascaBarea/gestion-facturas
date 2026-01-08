"""
Extractor para MARTIN ABENZA TORRANO (Conservas El Modesto)

Conservas artesanas de Murcia - alcachofas, piparras, escalivada.

Formato factura:
124/25 03/03/2025 C/ RODAS 2
...
CANTIDAD CONCEPTO - REFERENCIA PRECIO IMPORTE
10 LOTES CONSERVAS VARIADAS 21,84 218,40 E
PORTE 19,00
...
TOTAL BRUTO DESCUENTO IVA R.EQUIVALENCIA IRFP
218,40 IMPORTE IMPORTE 21,84 E IMPORTE IMPORTE 259,24 E

NOTAS:
- IVA: 10% (conservas alimenticias)
- El PORTE es un importe fijo SIN IVA que se suma al total
- Formula: (Total Bruto * 1.10) + Porte = Total Final
- Variantes nombre: MARTIN ABENZA, MARTIN ARBENZA, EL MODESTO

NIF: REDACTED_DNI

Creado: 19/12/2025
"""
from extractores.base import ExtractorBase
from extractores import registrar
from typing import List, Dict, Optional
import re


@registrar('MARTIN ABENZA', 'MARTIN ARBENZA', 'EL MODESTO', 'CONSERVAS EL MODESTO')
class ExtractorMartinAbenza(ExtractorBase):
    """Extractor para facturas de Martin Abenza (Conservas El Modesto)."""
    
    nombre = 'MARTIN ABENZA'
    cif = 'REDACTED_DNI'
    iban = ''
    metodo_pdf = 'pdfplumber'
    categoria_fija = 'CONSERVAS'
    
    def extraer_lineas(self, texto: str) -> List[Dict]:
        """
        Extrae lineas de la factura.
        
        Formato:
        10 LOTES CONSERVAS VARIADAS 21,84 218,40 E
        3 CAJAS PIPARRAS 31,80 95,40 E
        CANTIDAD DESCRIPCION PRECIO IMPORTE
        """
        lineas = []
        
        # Patron para lineas de producto
        # CANTIDAD DESCRIPCION PRECIO IMPORTE
        patron = re.compile(
            r'^(\d+)\s+'                          # Cantidad
            r'((?:CAJA[S]?|LOTE[S]?)\s+.+?)\s+'   # Descripcion (CAJA/LOTE + texto)
            r'(\d+,\d{2})\s+'                     # Precio
            r'(\d+,\d{2})\s*€?'                   # Importe
        , re.MULTILINE)
        
        for match in patron.finditer(texto):
            cantidad = int(match.group(1))
            descripcion = match.group(2).strip()
            precio = self._convertir_europeo(match.group(3))
            importe = self._convertir_europeo(match.group(4))
            
            lineas.append({
                'codigo': '',
                'articulo': descripcion,
                'cantidad': cantidad,
                'precio_ud': precio,
                'iva': 10,
                'base': round(importe, 2)
            })
        
        # Extraer PORTE (sin IVA, se anade como linea separada con IVA 0)
        porte_match = re.search(r'PORTE\s+(\d+,\d{2})\s*€?', texto)
        if porte_match:
            porte = self._convertir_europeo(porte_match.group(1))
            if porte > 0:
                lineas.append({
                    'codigo': '',
                    'articulo': 'PORTE',
                    'cantidad': 1,
                    'precio_ud': porte,
                    'iva': 0,  # El porte no lleva IVA
                    'base': round(porte, 2)
                })
        
        return lineas
    
    def _convertir_europeo(self, texto: str) -> float:
        if not texto:
            return 0.0
        texto = texto.strip()
        if '.' in texto and ',' in texto:
            texto = texto.replace('.', '').replace(',', '.')
        elif ',' in texto:
            texto = texto.replace(',', '.')
        try:
            return float(texto)
        except:
            return 0.0
    
    def extraer_total(self, texto: str) -> Optional[float]:
        """
        Total en la linea de totales, es el ultimo valor con E:
        218,40 IMPORTE IMPORTE 21,84 E IMPORTE IMPORTE 259,24 E
        """
        # Buscar linea con multiples IMPORTE y extraer el ultimo valor
        patron = re.search(r'IMPORTE\s+IMPORTE\s+[\d,]+\s*€?\s+IMPORTE\s+IMPORTE\s+(\d+,\d{2})\s*€', texto)
        if patron:
            return self._convertir_europeo(patron.group(1))
        
        # Alternativo: buscar todos los valores con E y tomar el mayor
        valores = re.findall(r'(\d+,\d{2})\s*€', texto)
        if valores:
            valores_num = [self._convertir_europeo(v) for v in valores]
            return max(valores_num)
        
        return None
    
    def extraer_fecha(self, texto: str) -> Optional[str]:
        """
        Fecha en formato: Fecha Factura: ... 03/03/2025
        O en linea: 124/25 03/03/2025
        """
        # Buscar fecha completa DD/MM/YYYY
        patron = re.search(r'(\d{2})/(\d{2})/(\d{4})', texto)
        if patron:
            return f"{patron.group(1)}/{patron.group(2)}/{patron.group(3)}"
        
        return None
