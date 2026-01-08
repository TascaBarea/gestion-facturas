"""
Extractor para PRODUCTOS ADELL S.L. (CROQUELLANAS)

Conservas artesanales de Morella (Castellón)
CIF: B12711636
Direccion: Plaza de los Estudios, 9, 12300 Morella
Telefono: 964 160 640 / 603 85 34 68
Email: info@croquellanas.com
Web: www.croquellanas.com

METODO: pdfplumber (PDF texto)

Productos: Alcachofas en aceite, Paté de cecina, Mousse de alcachofa
IVA: 10%
Categoria: CONSERVAS

Forma de pago: Transferencia
IBAN: REDACTED_IBAN (Cajamar)

Creado: 21/12/2025
Validado: 3/3 facturas (1T25-2T25)
"""
from extractores.base import ExtractorBase
from extractores import registrar
from typing import List, Dict, Optional
import re


@registrar('PRODUCTOS ADELL', 'CROQUELLANAS', 'ADELL')
class ExtractorProductosAdell(ExtractorBase):
    """Extractor para facturas de PRODUCTOS ADELL S.L."""
    
    nombre = 'PRODUCTOS ADELL S.L.'
    cif = 'B12711636'
    iban = 'REDACTED_IBAN'
    metodo_pdf = 'pdfplumber'
    categoria_fija = 'CONSERVAS'
    
    def extraer_texto(self, pdf_path: str) -> str:
        """Extrae texto con pdfplumber."""
        import pdfplumber
        
        texto = ""
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                t = page.extract_text()
                if t:
                    texto += t + "\n"
        return texto
    
    def extraer_lineas(self, texto: str) -> List[Dict]:
        """
        Extrae lineas de productos.
        
        Formatos posibles:
        - ARTICULO LOTE - CADUCIDAD CANT PRECIO IVA SUBTOTAL
        - ARTICULO LOTE - CADUCIDAD CANT CAJAS PRECIO IVA SUBTOTAL
        
        Ejemplos:
        ALCACHOFAS EN ACEITE 330 GR 240130 - 30/01/2026 24,000 4,920 10,00 118,08
        ALCACHOFAS EN ACEITE 330 GR 240213 - 13/02/2026 24,000 2 de 12u 4,920 10,00 118,08
        ALCACHOFAS EN ACEITE 330 GR 250128 - 28/01/2027 24,000 2 cajas de 4,920 10,00 118,08
        """
        lineas = []
        
        # Patrón flexible que maneja columna Cajas opcional
        patron = re.compile(
            r'^(.+?)\s+'                              # Artículo
            r'(\d{6})\s+-\s+\d{2}/\d{2}/\d{4}\s+'    # Lote - Caducidad
            r'([\d,]+)\s+'                            # Cantidad
            r'(?:[\d\s]+(?:de\s+\d+u?|cajas?\s+de(?:\s+\d+u)?)\s+)?'  # Cajas (opcional)
            r'([\d,]+)\s+'                            # Precio
            r'[\d,]+\s+'                              # IVA (ignorar)
            r'([\d,]+)\s*$',                          # Subtotal
            re.MULTILINE
        )
        
        for match in patron.finditer(texto):
            articulo = match.group(1).strip()
            cantidad = float(match.group(3).replace(',', '.'))
            precio = float(match.group(4).replace(',', '.'))
            subtotal = float(match.group(5).replace(',', '.'))
            
            lineas.append({
                'codigo': '',
                'articulo': articulo[:50],
                'cantidad': cantidad,
                'precio_ud': round(precio, 2),
                'iva': 10,
                'base': round(subtotal, 2)
            })
        
        return lineas
    
    def extraer_total(self, texto: str) -> Optional[float]:
        """Extrae total de la factura."""
        m = re.search(r'([\d.,]+)\s*€', texto)
        if m:
            return float(m.group(1).replace('.', '').replace(',', '.'))
        return None
    
    def extraer_fecha(self, texto: str) -> Optional[str]:
        """
        Extrae fecha de la factura.
        Formato: A/4 09/01/2025 09/01/2025
        """
        m = re.search(r'A/\d+\s+(\d{2}/\d{2}/\d{4})', texto)
        return m.group(1) if m else None
    
    def extraer_numero_factura(self, texto: str) -> Optional[str]:
        """Extrae numero de factura (formato A/XXX)."""
        m = re.search(r'(A/\d+)', texto)
        return m.group(1) if m else None
