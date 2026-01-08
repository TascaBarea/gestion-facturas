# extractores/siete_lindes.py
"""
Extractor para 7 LINDES (Pedro Oscar Rubio Navarro)
Proveedor de vinos: RISUEÑA y CLEMENCIA
NIF: 04610845N

Formato factura:
- Líneas: DESCRIPCIÓN    CANTIDAD    PRECIO    SUBTOTAL
- Productos: RISUEÑA L-X/YYYY, CLEMENCIA L-XX/YYYY (ignorar lote)
- IVA: 21% siempre
- Categorías: RISUEÑA → "RISUEÑA", CLEMENCIA → "VINOS"
"""

import re
from typing import List, Dict, Optional
from extractores.base import ExtractorBase
from extractores import registrar


@registrar('7 LINDES', 'PEDRO OSCAR RUBIO', 'BODEGAS 7 LINDES', 
           'PEDRO_OSCAR_RUBIO', 'BODEGAS_7_LINDES', '7_LINDES', 'SIETE LINDES')
class Extractor7Lindes(ExtractorBase):
    
    nombre = '7 LINDES'
    cif = '04610845N'
    iban = 'ES3915447889726650827817'
    metodo_pdf = 'pdfplumber'
    
    def extraer_lineas(self, texto: str) -> List[Dict]:
        """
        Extrae líneas de productos del PDF.
        Formato: DESCRIPCIÓN    CANTIDAD    PRECIO    SUBTOTAL
        Ejemplo: RISUEÑA L-1/2024    24    6,00€    144,00€
        """
        lineas = []
        
        # Patrón para capturar líneas de producto
        # Grupo 1: nombre producto (RISUEÑA o CLEMENCIA)
        # Grupo 2: lote (L-X/YYYY) - se ignora
        # Grupo 3: cantidad
        # Grupo 4: precio unitario
        # Grupo 5: subtotal (base)
        patron = re.compile(
            r'(RISUEÑA|CLEMENCIA)\s+'      # Nombre producto
            r'L-?\d{1,2}/\d{4}\s+'         # Lote (ignorar)
            r'(\d+)\s+'                     # Cantidad
            r'(\d+[.,]\d{2})\s*€?\s+'       # Precio unitario
            r'(\d+[.,]\d{2})\s*€?',         # Subtotal/base
            re.IGNORECASE
        )
        
        for match in patron.finditer(texto):
            nombre_producto = match.group(1).upper().strip()
            cantidad = float(match.group(2))
            precio_str = match.group(3).replace(',', '.')
            precio_ud = float(precio_str)
            base_str = match.group(4).replace(',', '.')
            base = float(base_str)
            
            # Asignar categoría según producto
            if 'RISUEÑA' in nombre_producto:
                categoria = 'RISUEÑA'
            else:
                categoria = 'VINOS'
            
            lineas.append({
                'codigo': '',
                'articulo': nombre_producto,  # Solo nombre, sin lote
                'cantidad': cantidad,
                'precio_ud': precio_ud,
                'iva': 21,
                'base': base,
                'categoria': categoria
            })
        
        return lineas
    
    def extraer_total(self, texto: str) -> Optional[float]:
        """Extrae el total de la factura."""
        # Buscar "Total" seguido de importe
        patron = re.compile(r'Total\s+(\d+[.,]\d{2})\s*€?', re.IGNORECASE)
        match = patron.search(texto)
        if match:
            total_str = match.group(1).replace(',', '.')
            return float(total_str)
        return None
    
    def extraer_fecha(self, texto: str) -> Optional[str]:
        """Extrae la fecha de la factura (DD/MM/YYYY)."""
        # Buscar "Fecha" seguido de fecha
        patron = re.compile(r'Fecha\s+(\d{2}/\d{2}/\d{4})')
        match = patron.search(texto)
        if match:
            return match.group(1)
        return None
    
    def extraer_referencia(self, texto: str) -> Optional[str]:
        """Extrae el número de factura."""
        # Buscar "Número" o "Número" seguido de F-XX/YYYY
        patron = re.compile(r'N[úu]mero\s+(F-\d+/\d{4})', re.IGNORECASE)
        match = patron.search(texto)
        if match:
            return match.group(1)
        return None
