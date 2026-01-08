"""
Extractor para QUESOS FELIX (Armando Sanz S.L.)

Quesos de Valladolid - IGP y especiales.

Formato factura:
20/01/2025 25 00026
...
LOTE DESCRIPCION UDS CANTIDAD PRECIO IMPORTE
4195 QUESO IGP FELIX. SEMICURADO GRANDE 1 3,100 14,00 43,40 E
4188 QUESO FELIX. Especial PATAMULO GRANDE 1 5,850 15,00 87,75 E
...
TOTAL FACTURA 136,40 E

NOTA: El importe de linea = CANTIDAD (kg) x PRECIO (E/kg)
      IVA reducido: 4% (quesos)

CIF: B47440136
IBAN: REDACTED_IBAN

Creado: 19/12/2025
"""
from extractores.base import ExtractorBase
from extractores import registrar
from typing import List, Dict, Optional
import re


@registrar('QUESOS FELIX')
class ExtractorQuesosFelix(ExtractorBase):
    """Extractor para facturas de Quesos Felix."""
    
    nombre = 'QUESOS FELIX'
    cif = 'B47440136'
    iban = 'REDACTED_IBAN'
    metodo_pdf = 'pdfplumber'
    
    def extraer_lineas(self, texto: str) -> List[Dict]:
        """
        Extrae lineas de la factura.
        
        Formato:
        4195 QUESO IGP FELIX. SEMICURADO GRANDE 1 3,100 14,00 43,40 E
        LOTE DESCRIPCION                        UDS CANTIDAD PRECIO IMPORTE
        
        - puede no tener lote (linea empieza con -)
        """
        lineas = []
        
        # Patron para lineas con lote numerico
        # 4195 QUESO IGP FELIX. SEMICURADO GRANDE 1 3,100 14,00 43,40 E
        patron_con_lote = re.compile(
            r'^(\d{4})\s+'                        # Lote (4 digitos)
            r'(QUESO[^€]+?)\s+'                   # Descripcion
            r'(\d+)\s+'                           # UDS
            r'(\d+,\d{3})\s+'                     # Cantidad (kg con 3 decimales)
            r'(\d+,\d{2})\s+'                     # Precio
            r'(\d+,\d{2})\s*€'                    # Importe
        , re.MULTILINE)
        
        for match in patron_con_lote.finditer(texto):
            lote = match.group(1)
            descripcion = match.group(2).strip()
            uds = int(match.group(3))
            cantidad = self._convertir_europeo(match.group(4))
            precio = self._convertir_europeo(match.group(5))
            importe = self._convertir_europeo(match.group(6))
            
            lineas.append({
                'codigo': lote,
                'articulo': descripcion,
                'cantidad': cantidad,
                'precio_ud': precio,
                'iva': 4,  # Quesos tienen IVA reducido
                'base': round(importe, 2)
            })
        
        # Patron para lineas sin lote (empiezan con -)
        # - QUESO FELIX. Especial PATAMULO GRANDE 3 5,250 15,00 78,75 E
        patron_sin_lote = re.compile(
            r'^-\s+'                              # Guion inicial
            r'(QUESO[^€]+?)\s+'                   # Descripcion
            r'(\d+)\s+'                           # UDS
            r'(\d+,\d{3})\s+'                     # Cantidad
            r'(\d+,\d{2})\s+'                     # Precio
            r'(\d+,\d{2})\s*€'                    # Importe
        , re.MULTILINE)
        
        for match in patron_sin_lote.finditer(texto):
            descripcion = match.group(1).strip()
            uds = int(match.group(2))
            cantidad = self._convertir_europeo(match.group(3))
            precio = self._convertir_europeo(match.group(4))
            importe = self._convertir_europeo(match.group(5))
            
            lineas.append({
                'codigo': '',
                'articulo': descripcion,
                'cantidad': cantidad,
                'precio_ud': precio,
                'iva': 4,
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
        """
        Total en formato: TOTAL FACTURA 136,40 E
        O en linea de vencimiento: 19/02/2025 136,40 E
        """
        # Buscar TOTAL FACTURA
        patron = re.search(r'TOTAL\s+FACTURA\s*\n?\s*(\d+,\d{2})\s*€', texto, re.IGNORECASE)
        if patron:
            return self._convertir_europeo(patron.group(1))
        
        # Buscar en linea de importe (ultimo valor con E antes de TOTAL)
        patron2 = re.search(r'Importe:\s*(\d+,\d{2})\s*€', texto)
        if patron2:
            return self._convertir_europeo(patron2.group(1))
        
        # Buscar valor despues de vencimiento
        patron3 = re.search(r'\d{2}/\d{2}/\d{4}\s+(\d+,\d{2})\s*€\s+Total\s+Retenci', texto)
        if patron3:
            return self._convertir_europeo(patron3.group(1))
        
        return None
    
    def extraer_fecha(self, texto: str) -> Optional[str]:
        """
        Fecha en formato: 20/01/2025 25 00026
        """
        patron = re.search(r'^(\d{2})/(\d{2})/(\d{4})\s+\d{2}\s+\d{5}', texto, re.MULTILINE)
        if patron:
            return f"{patron.group(1)}/{patron.group(2)}/{patron.group(3)}"
        
        # Alternativo: buscar fecha despues de FECHA
        patron2 = re.search(r'FECHA[^\d]*(\d{2})/(\d{2})/(\d{4})', texto)
        if patron2:
            return f"{patron2.group(1)}/{patron2.group(2)}/{patron2.group(3)}"
        
        return None
