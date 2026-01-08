"""
Extractor para PILAR RODRIGUEZ GARCIA / HUEVOS EL MAJADAL

Proveedor de huevos de Maello (Ávila)
NIF: REDACTED_DNI
IBAN: REDACTED_IBAN

Formato factura (pdfplumber):
- Líneas producto: FECHA Docenas de huevos CANTIDAD PRECIO IMPORTE €
- Ejemplo: 3-2-2025 Docenas de huevos 12 3,50 42,00 €
- IVA: 4% (huevos - superreducido)

Creado: 19/12/2025
"""
from extractores.base import ExtractorBase
from extractores import registrar
from typing import List, Dict, Optional
import re


@registrar('PILAR RODRIGUEZ', 'EL MAJADAL', 'HUEVOS EL MAJADAL', 'PILAR RODRIGUEZ GARCIA', 
           'MAJADAL', 'HUEVOS MAJADAL')
class ExtractorPilarRodriguez(ExtractorBase):
    """Extractor para facturas de PILAR RODRIGUEZ / HUEVOS EL MAJADAL."""
    
    nombre = 'PILAR RODRIGUEZ'
    cif = 'REDACTED_DNI'
    iban = 'REDACTED_IBAN'
    metodo_pdf = 'pdfplumber'
    categoria_fija = 'HUEVOS'
    
    def extraer_lineas(self, texto: str) -> List[Dict]:
        """
        Extrae líneas INDIVIDUALES de productos.
        
        Formato:
        FECHA Docenas de huevos CANTIDAD PRECIO IMPORTE €
        3-2-2025 Docenas de huevos 12 3,50 42,00 €
        """
        lineas = []
        
        # Patrón para líneas de producto
        # La fecha puede estar cortada (17-2-202 en una línea, 5 en la siguiente)
        # Buscamos: "Docenas de huevos" seguido de CANTIDAD PRECIO IMPORTE
        patron_linea = re.compile(
            r'Docenas\s+de\s+huevos\s+'       # Descripción fija
            r'(\d+)\s+'                        # Cantidad (entero)
            r'(\d+,\d{2})\s+'                  # Precio
            r'(\d+,\d{2})\s*€'                 # Importe con €
        )
        
        for match in patron_linea.finditer(texto):
            cantidad = int(match.group(1))
            precio = self._convertir_europeo(match.group(2))
            importe = self._convertir_europeo(match.group(3))
            
            lineas.append({
                'codigo': '',
                'articulo': 'Docenas de huevos',
                'cantidad': cantidad,
                'precio_ud': round(precio, 2),
                'iva': 4,
                'base': round(importe, 2)
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
        # Buscar en línea de totales: Base imponible % IVA IVA TOTAL
        # Formato: BASE 4 IVA TOTAL €
        patron = re.search(r'(\d+,\d{2})\s*€\s*$', texto, re.MULTILINE)
        if patron:
            # Buscar el TOTAL que está al final después del IVA
            # Patrón más específico: IVA seguido de TOTAL
            patron_total = re.search(r'(\d+,\d{2})\s+4\s+(\d+,\d{2})\s+(\d+,\d{2})\s*€', texto)
            if patron_total:
                return self._convertir_europeo(patron_total.group(3))
        
        # Alternativa: buscar TOTAL seguido de importe
        patron_alt = re.search(r'TOTAL\s*\n?\s*(\d+,\d{2})\s*€', texto)
        if patron_alt:
            return self._convertir_europeo(patron_alt.group(1))
        
        return None
    
    def extraer_fecha(self, texto: str) -> Optional[str]:
        """Extrae fecha de la factura."""
        # Formato: Fecha: DD/MM/YYYY
        patron = re.search(r'Fecha:\s*(\d{2}/\d{2}/\d{4})', texto)
        if patron:
            return patron.group(1)
        return None
    
    def extraer_numero_factura(self, texto: str) -> Optional[str]:
        """Extrae número de factura."""
        # Formato: Número: 25F00015
        patron = re.search(r'Número:\s*(\d+F\d+)', texto)
        if patron:
            return patron.group(1)
        return None
