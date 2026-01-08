"""
Extractor para AGRÍCOLA DE MONTBRIÓ DEL CAMP, SCCL (MONTEBRIONE)

Cooperativa agrícola: vermuts, aceites, vinagres, aceitunas.
CIF: F43011998
IBAN: ES76 3183 6554 2820 0457 9120

Formato factura (pdfplumber):
CÓDIGO DESCRIPCIÓN LITROS BULTOS CANTIDAD PRECIO [DTO%] %IVA IMPORTE
0205009 VERMUT NEGRE 2 LITRES MONTEBRIONE 0,00 1 12,00 9,091 10,00% 21,00 98,19

IVA: 4% (aceites), 10% (aceitunas, vinagre), 21% (vermuts, portes)

PORTES: Se prorratean proporcionalmente SOLO entre productos del mismo tipo de IVA
(portes son 21%, así que se reparten entre vermuts y otros productos 21%)

Creado: 27/12/2025
"""
from extractores.base import ExtractorBase
from extractores import registrar
from typing import List, Dict, Optional
import re
import pdfplumber


@registrar('MONTBRIONE', 'MONTEBRIONE', 'COOPERATIVA MONTBRIONE', 'COOPERATIVA MONTEBRIONE',
           'AGRICOLA MONTBRIO', 'AGRICOLA DE MONTBRIO', 'AGRICOLA DE MONTBRIÓ DEL CAMP')
class ExtractorMontbrione(ExtractorBase):
    """Extractor para facturas de COOPERATIVA MONTBRIONE."""
    
    nombre = 'MONTBRIONE'
    cif = 'F43011998'
    iban = 'ES76 3183 6554 2820 0457 9120'
    metodo_pdf = 'pdfplumber'
    
    def extraer_lineas(self, texto: str) -> List[Dict]:
        """
        Extrae líneas individuales de productos.
        
        Formato:
        CÓDIGO DESC LITROS BULTOS CANTIDAD PRECIO [DTO%] %IVA IMPORTE
        
        Los portes (SERVEIS TRANSPORTS) se prorratean entre productos
        del mismo tipo de IVA (normalmente 21%).
        """
        lineas = []
        portes_base = 0
        portes_iva = 21
        
        # Patrón para líneas de producto
        # Ejemplo: 0205009 VERMUT NEGRE 2 LITRES MONTEBRIONE 0,00 1 12,00 9,091 10,00% 21,00 98,19
        patron = re.compile(
            r'^(\d{7})\s+'                              # Código 7 dígitos
            r'(.+?)\s+'                                  # Descripción
            r'(\d+,\d{2})\s+'                            # Litros
            r'(\d+)\s+'                                  # Bultos
            r'(\d+,\d{2})\s+'                            # Cantidad
            r'([\d,]+)\s+'                               # Precio
            r'(?:(\d+,\d{2})%\s+)?'                      # DTO% (opcional)
            r'(\d+,\d{2})\s+'                            # %IVA
            r'(\d+,\d{2})$'                              # Importe
        , re.MULTILINE)
        
        for match in patron.finditer(texto):
            codigo = match.group(1)
            descripcion = match.group(2).strip()
            cantidad = self._convertir_europeo(match.group(5))
            precio = self._convertir_europeo(match.group(6))
            iva = int(self._convertir_europeo(match.group(8)))
            importe = self._convertir_europeo(match.group(9))
            
            # Detectar portes (SERVEIS TRANSPORTS)
            if 'TRANSPORT' in descripcion.upper() or 'SERVEIS' in descripcion.upper():
                portes_base = importe
                portes_iva = iva
                continue
            
            # Filtrar líneas con importe muy bajo
            if importe < 0.10:
                continue
            
            lineas.append({
                'codigo': codigo,
                'articulo': descripcion[:50],
                'cantidad': int(cantidad) if cantidad == int(cantidad) else round(cantidad, 2),
                'precio_ud': round(precio, 4),
                'iva': iva,
                'base': round(importe, 2)
            })
        
        # Prorratear portes SOLO entre productos del mismo IVA
        if portes_base > 0 and lineas:
            productos_mismo_iva = [l for l in lineas if l['iva'] == portes_iva]
            if productos_mismo_iva:
                base_mismo_iva = sum(l['base'] for l in productos_mismo_iva)
                if base_mismo_iva > 0:
                    for linea in productos_mismo_iva:
                        proporcion = linea['base'] / base_mismo_iva
                        incremento = portes_base * proporcion
                        linea['base'] = round(linea['base'] + incremento, 2)
        
        return lineas
    
    def _convertir_europeo(self, texto: str) -> float:
        """Convierte formato europeo (1.234,56) a float."""
        if not texto:
            return 0.0
        texto = str(texto).strip().replace('€', '').replace('%', '')
        if '.' in texto and ',' in texto:
            texto = texto.replace('.', '').replace(',', '.')
        elif ',' in texto:
            texto = texto.replace(',', '.')
        try:
            return float(texto)
        except:
            return 0.0
    
    def extraer_total(self, texto: str) -> Optional[float]:
        """Extrae total de la factura."""
        # Buscar "TOTAL FACTURA 314,50 €"
        patron = re.search(r'TOTAL\s+FACTURA\s+([\d.,]+)\s*€', texto, re.IGNORECASE)
        if patron:
            return self._convertir_europeo(patron.group(1))
        
        # Alternativa: "TOTAL A PAGAR"
        patron2 = re.search(r'TOTAL\s+A\s+PAGAR\s+([\d.,]+)\s*€', texto, re.IGNORECASE)
        if patron2:
            return self._convertir_europeo(patron2.group(1))
        
        return None
    
    def extraer_fecha(self, texto: str) -> Optional[str]:
        """Extrae fecha de la factura."""
        # Buscar "Data: 09/10/2025" o "FECHA: 27/02/2025"
        patron = re.search(r'(?:Data|FECHA):\s*(\d{2}/\d{2}/\d{4})', texto, re.IGNORECASE)
        if patron:
            return patron.group(1)
        return None
