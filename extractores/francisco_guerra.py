"""
Extractor para FRANCISCO GUERRA OLLER

Aceitunas y encurtidos.
CIF: REDACTED_DNI

Formato factura (pdfplumber):
Referencia Descripción Cantidad Precio Dto% Total
01071 MZ LATAS 5 KG " La Abuela" 3 19,900 59,70
00192 CHUPADEO ZAMBUDIO 3 21,070 63,21

TOTAL 635,09 €

IVA: 10% (alimentación)

Creado: 19/12/2025
"""
from extractores.base import ExtractorBase
from extractores import registrar
from typing import List, Dict, Optional
import re


@registrar('FRANCISCO GUERRA', 'GUERRA', 'ACEITUNAS TIMON')
class ExtractorFranciscoGuerra(ExtractorBase):
    """Extractor para facturas de FRANCISCO GUERRA."""
    
    nombre = 'FRANCISCO GUERRA'
    cif = 'REDACTED_DNI'
    iban = ''
    metodo_pdf = 'pdfplumber'
    
    def extraer_lineas(self, texto: str) -> List[Dict]:
        """
        Extrae líneas individuales de productos.
        
        Formato:
        01071 MZ LATAS 5 KG " La Abuela" 3 19,900 59,70
        """
        lineas = []
        
        # Patrón: CODIGO DESCRIPCION CANTIDAD PRECIO IMPORTE
        # Ejemplo: 01071 MZ LATAS 5 KG " La Abuela" 3 19,900 59,70
        patron_linea = re.compile(
            r'^(\d{4,6})\s+'                          # Código (4-6 dígitos)
            r'(.+?)\s+'                               # Descripción (cualquier texto)
            r'(\d{1,3})\s+'                           # Cantidad
            r'(\d+,\d{2,3})\s+'                       # Precio (puede ser 19,900)
            r'(\d+,\d{2})$'                           # Importe al final de línea
        , re.MULTILINE)
        
        for match in patron_linea.finditer(texto):
            codigo = match.group(1)
            descripcion = match.group(2).strip()
            cantidad = int(match.group(3))
            precio = self._convertir_europeo(match.group(4))
            importe = self._convertir_europeo(match.group(5))
            
            # Filtrar cabeceras
            desc_upper = descripcion.upper()
            if any(x in desc_upper for x in ['REFERENCIA', 'DESCRIPCION', 'CANTIDAD', 'PRECIO', 'TOTAL', 'ALBARAN']):
                continue
            
            if importe < 1.0:
                continue
            
            lineas.append({
                'codigo': codigo,
                'articulo': descripcion[:50],
                'cantidad': cantidad,
                'precio_ud': round(precio, 2),
                'iva': 10,  # Aceitunas y encurtidos siempre 10%
                'base': round(importe, 2)
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
        # Buscar: TOTAL 410,15 € o similar
        patrones = [
            r'TOTAL\s*\n?\s*(\d+,\d{2})\s*€',        # TOTAL\n410,15 €
            r'(\d+,\d{2})\s*€\s*\n.*?HOJA',          # 410,15 €\nHOJA
        ]
        for patron in patrones:
            match = re.search(patron, texto, re.IGNORECASE | re.DOTALL)
            if match:
                return self._convertir_europeo(match.group(1))
        return None
