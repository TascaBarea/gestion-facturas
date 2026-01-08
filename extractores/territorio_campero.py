"""
Extractor para GRUPO TERRITORIO CAMPERO

Patatas fritas artesanas
CIF: B16690141
IBAN: ES53 0182 6035 4102 0152 8536

Formato factura (pdfplumber):
Cantidad Producto Precio/Ud IVA Suma Base
12 PATATAS FRITAS ARTESANAS 9.90 EUR 10% 118.80 EUR

IVA: siempre 10%
Categoria: PATATAS FRITAS APERITIVO

Creado: 21/12/2025
"""
from extractores.base import ExtractorBase
from extractores import registrar
from typing import List, Dict, Optional
import re
import pdfplumber


@registrar('GRUPO TERRITORIO CAMPERO', 'TERRITORIO CAMPERO', 'CAMPERO')
class ExtractorTerritorioCampero(ExtractorBase):
    """Extractor para facturas de GRUPO TERRITORIO CAMPERO."""
    
    nombre = 'GRUPO TERRITORIO CAMPERO'
    cif = 'B16690141'
    iban = 'ES53 0182 6035 4102 0152 8536'
    metodo_pdf = 'pdfplumber'
    categoria_fija = 'PATATAS FRITAS APERITIVO'
    
    def extraer_texto_pdfplumber(self, pdf_path: str) -> str:
        """Extrae texto del PDF."""
        texto_completo = []
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    texto = page.extract_text()
                    if texto:
                        texto_completo.append(texto)
        except Exception as e:
            pass
        return '\n'.join(texto_completo)
    
    def extraer_lineas(self, texto: str) -> List[Dict]:
        """
        Extrae lineas de productos.
        Formato: 12 PATATAS FRITAS ARTESANAS 9.90 EUR 10% 118.80 EUR
        """
        lineas = []
        
        # Patron para lineas de producto
        patron = re.compile(
            r'^(\d+)\s+'                    # Cantidad
            r'(.+?)\s+'                     # Producto
            r'(\d+[.,]\d{2})\s*(?:EUR|€)\s*'  # Precio/Ud
            r'(\d+)%\s+'                    # IVA
            r'(\d+[.,]\d{2})\s*(?:EUR|€)',  # Suma Base
            re.MULTILINE
        )
        
        for match in patron.finditer(texto):
            cantidad = int(match.group(1))
            producto = match.group(2).strip()
            precio = self._convertir_europeo(match.group(3))
            iva = int(match.group(4))
            base = self._convertir_europeo(match.group(5))
            
            # Filtrar cabeceras
            if any(x in producto for x in ['Producto', 'Cantidad', 'Precio']):
                continue
            
            if base < 0.01:
                continue
            
            lineas.append({
                'codigo': '',
                'articulo': producto[:50],
                'cantidad': cantidad,
                'precio_ud': round(precio, 2),
                'iva': iva,
                'base': round(base, 2)
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
        patron = re.search(r'TOTAL:\s*(\d+[.,]\d{2})\s*(?:EUR|€)', texto, re.IGNORECASE)
        if patron:
            return self._convertir_europeo(patron.group(1))
        return None
    
    def extraer_fecha(self, texto: str) -> Optional[str]:
        """Extrae fecha de la factura. Formato: 31 de Enero del 2025"""
        meses = {
            'enero': '01', 'febrero': '02', 'marzo': '03', 'abril': '04',
            'mayo': '05', 'junio': '06', 'julio': '07', 'agosto': '08',
            'septiembre': '09', 'octubre': '10', 'noviembre': '11', 'diciembre': '12'
        }
        patron = re.search(r'(\d+)\s+de\s+(\w+)\s+del?\s+(\d{4})', texto, re.IGNORECASE)
        if patron:
            dia = patron.group(1).zfill(2)
            mes = meses.get(patron.group(2).lower(), '01')
            anio = patron.group(3)
            return f"{dia}/{mes}/{anio}"
        return None
    
    def extraer_numero_factura(self, texto: str) -> Optional[str]:
        """Extrae numero de factura."""
        patron = re.search(r'NUMERO DE FACTURA:\s*(\d+)', texto, re.IGNORECASE)
        if patron:
            return patron.group(1)
        return None
