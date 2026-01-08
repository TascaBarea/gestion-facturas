"""
Extractor para ECOFICUS S.L.

Higos ecológicos y derivados.
CIF: B10214021

Formato factura (pdfplumber):
CODIGO DESCRIPCION LOTE F.C.P. CAJAS CANTIDAD PRECIO IMPORTE
FB6E Estuche Bombón de Higo ecológico 6uds. 017/04325 12/03/26 1,00 12,00 6,880€/uni 82,56

Tiene:
- Productos con IVA 10%
- Portes con IVA 21%
- Muestras gratuitas (0,000€/uni) que hay que ignorar

TOTAL FACTURA = productos (IVA 10%) + portes (IVA 21%)

Creado: 19/12/2025
"""
from extractores.base import ExtractorBase
from extractores import registrar
from typing import List, Dict, Optional
import re


@registrar('ECOFICUS', 'ECO FICUS')
class ExtractorEcoficus(ExtractorBase):
    """Extractor para facturas de ECOFICUS."""
    
    nombre = 'ECOFICUS'
    cif = 'B10214021'
    iban = 'REDACTED_IBAN'
    metodo_pdf = 'pdfplumber'
    
    def extraer_lineas(self, texto: str) -> List[Dict]:
        """
        Extrae líneas individuales de productos.
        
        Formato:
        FB6E Estuche Bombón... 017/04325 12/03/26 1,00 12,00 6,880€/uni 82,56
        """
        lineas = []
        
        # Patrón para líneas de producto con importe > 0
        # CODIGO DESCRIPCION LOTE FECHA CAJAS CANTIDAD PRECIO IMPORTE
        patron_linea = re.compile(
            r'^([A-Z0-9]{2,10})\s+'                    # Código (FB6E, LB18, PH200NFB)
            r'(.+?)\s+'                                # Descripción
            r'\d{2,3}/\d{5}\s+'                        # Lote (017/04325)
            r'\d{2}/\d{2}/\d{2}\s+'                    # Fecha caducidad
            r'(\d+,\d{2})\s+'                          # Cajas
            r'(\d+,\d{2})\s+'                          # Cantidad
            r'(\d+,\d{3})€/uni\s+'                     # Precio (3 decimales)
            r'(\d+,\d{2})'                             # Importe
        , re.MULTILINE)
        
        for match in patron_linea.finditer(texto):
            codigo = match.group(1)
            descripcion = match.group(2).strip()
            cantidad = self._convertir_europeo(match.group(4))
            precio = self._convertir_europeo(match.group(5))
            importe = self._convertir_europeo(match.group(6))
            
            # Ignorar muestras gratuitas (precio = 0)
            if precio < 0.01 or importe < 0.50:
                continue
            
            lineas.append({
                'codigo': codigo,
                'articulo': descripcion[:50],
                'cantidad': int(cantidad) if cantidad == int(cantidad) else cantidad,
                'precio_ud': round(precio, 2),
                'iva': 10,  # Productos alimentarios
                'base': round(importe, 2)
            })
        
        # Añadir portes (siempre IVA 21%)
        portes = self._extraer_portes(texto)
        if portes > 0:
            lineas.append({
                'codigo': 'PORTES',
                'articulo': 'PORTES',
                'cantidad': 1,
                'precio_ud': round(portes, 2),
                'iva': 21,
                'base': round(portes, 2)
            })
        
        return lineas
    
    def _extraer_portes(self, texto: str) -> float:
        """Extrae el importe de portes."""
        # Buscar en desglose: BASE 21,00 CUOTA
        patron = re.search(r'(\d+,\d{2})\s+21,00\s+(\d+,\d{2})', texto)
        if patron:
            base_portes = self._convertir_europeo(patron.group(1))
            return base_portes
        
        # Alternativo: Portes\nXX,XX
        patron2 = re.search(r'Portes\s*\n\s*(\d+,\d{2})', texto)
        if patron2:
            return self._convertir_europeo(patron2.group(1))
        
        return 0.0
    
    def _convertir_europeo(self, texto: str) -> float:
        if not texto:
            return 0.0
        texto = texto.strip().replace('€', '').replace('/uni', '')
        if '.' in texto and ',' in texto:
            texto = texto.replace('.', '').replace(',', '.')
        elif ',' in texto:
            texto = texto.replace(',', '.')
        try:
            return float(texto)
        except:
            return 0.0
    
    def extraer_total(self, texto: str) -> Optional[float]:
        patron = re.search(r'TOTAL\s+FACTURA\s+(\d+,\d{2})\s*€', texto, re.IGNORECASE)
        if patron:
            return self._convertir_europeo(patron.group(1))
        return None
