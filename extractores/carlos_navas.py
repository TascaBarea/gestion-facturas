"""
Extractor para QUESOS NAVAS S.L (Carlos Navas)

Quesería de Peñaranda de Bracamonte (Salamanca)
CIF: B37416419
IBAN: REDACTED_IBAN

Formato factura (pdfplumber):
- Líneas producto: CODIGO ARTICULO LOTE CANTIDAD PRECIO IVA SUBTOTAL
- IVA: 4% (quesos)

Variantes nombre: CARLOS NAVAS, QUESOS NAVAS, QUESERIA NAVAS

Creado: 19/12/2025
"""
from extractores.base import ExtractorBase
from extractores import registrar
from typing import List, Dict, Optional
import re


@registrar('CARLOS NAVAS', 'QUESOS NAVAS', 'QUESERIA NAVAS', 'QUESOS NAVAS S.L', 'QUESOS NAVAS, S.L')
class ExtractorCarlosNavas(ExtractorBase):
    """Extractor para facturas de QUESOS NAVAS S.L."""
    
    nombre = 'CARLOS NAVAS'
    cif = 'B37416419'
    iban = 'REDACTED_IBAN'
    metodo_pdf = 'pdfplumber'
    
    def extraer_lineas(self, texto: str) -> List[Dict]:
        """
        Extrae líneas INDIVIDUALES de productos.
        
        Formato:
        CODIGO ARTICULO LOTE CANTIDAD PRECIO IVA SUBTOTAL
        6 QUESO OVEJA INVIERNO 2 AÑOS 0723 9,020 25,860 4,00 233,26
        """
        lineas = []
        
        # Patrón para líneas de producto
        # El código puede ser 1-2 dígitos, el lote 3-5 dígitos
        # Cantidad y precio usan coma como decimal (formato europeo)
        # Ejemplo: 6 QUESO OVEJA INVIERNO 2 AÑOS 0723 9,020 25,860 4,00 233,26
        
        patron_linea = re.compile(
            r'^(\d{1,2})\s+'                    # Código (1-2 dígitos)
            r'(.+?)\s+'                          # Artículo (cualquier texto)
            r'(\d{3,5})\s+'                      # Lote (3-5 dígitos)
            r'(\d+,\d{3})\s+'                    # Cantidad (X,XXX kg)
            r'(\d+,\d{2,3})\s+'                  # Precio (€/kg)
            r'(\d+,\d{2})\s+'                    # IVA %
            r'(\d+,\d{2})\s*$'                   # Subtotal
        , re.MULTILINE)
        
        for match in patron_linea.finditer(texto):
            codigo = match.group(1)
            articulo = match.group(2).strip()
            # lote = match.group(3)  # No lo usamos
            cantidad = self._convertir_europeo(match.group(4))
            precio = self._convertir_europeo(match.group(5))
            iva = int(float(self._convertir_europeo(match.group(6))))
            subtotal = self._convertir_europeo(match.group(7))
            
            lineas.append({
                'codigo': codigo,
                'articulo': articulo[:50],
                'cantidad': round(cantidad, 3),
                'precio_ud': round(precio, 2),
                'iva': iva,
                'base': round(subtotal, 2)
            })
        
        return lineas
    
    def _convertir_europeo(self, texto: str) -> float:
        """Convierte formato europeo (1.234,56) a float."""
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
        """Extrae total de la factura."""
        # Buscar "TOTAL FACTURA" seguido del importe
        # Formato: TOTAL FACTURA\n429,56 €
        patron = re.search(
            r'TOTAL\s+FACTURA\s*[\n\r]+\s*(\d+,\d{2})\s*€',
            texto, re.IGNORECASE
        )
        if patron:
            return self._convertir_europeo(patron.group(1))
        
        # Alternativa: buscar en vencimientos
        patron2 = re.search(r'Vencimientos\s*:\s*\d{2}/\d{2}/\d{4}\s+(\d+,\d{2})€', texto)
        if patron2:
            return self._convertir_europeo(patron2.group(1))
        
        return None
    
    def extraer_fecha(self, texto: str) -> Optional[str]:
        """Extrae fecha de la factura."""
        # Buscar después de "Fecha" en la cabecera
        patron = re.search(r'A/\d+\s+(\d{2}/\d{2}/\d{4})', texto)
        if patron:
            return patron.group(1)
        return None
    
    def extraer_numero_factura(self, texto: str) -> Optional[str]:
        """Extrae número de factura."""
        patron = re.search(r'(A/\d+)', texto)
        if patron:
            return patron.group(1)
        return None
