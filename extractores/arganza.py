"""
Extractor para VINOS DE ARGANZA

Bodega del Bierzo (Leon)
CIF: B24416869
IBAN: REDACTED_IBAN

Formato factura (pdfplumber):
CODIGO DESCRIPCION CANTIDAD PRECIO DESCUENTO IMPORTE
P063 LEGADO DE FARRO SELECCION 2023 48,00 2,500 0,00 120,00
SE99 SERVICIO DE TRANSPORTE 1,00 21,000 0,00 21,00

IVA: 21% (vinos y transporte)
Categoria: VINOS
Portes: SE99 - se distribuyen proporcionalmente

Creado: 21/12/2025
"""
from extractores.base import ExtractorBase
from extractores import registrar
from typing import List, Dict, Optional
import re
import pdfplumber


@registrar('VINOS DE ARGANZA', 'ARGANZA', 'VINOS ARGANZA')
class ExtractorArganza(ExtractorBase):
    """Extractor para facturas de VINOS DE ARGANZA."""
    
    nombre = 'VINOS DE ARGANZA'
    cif = 'B24416869'
    iban = 'REDACTED_IBAN'
    metodo_pdf = 'pdfplumber'
    
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
        Portes (SE99) se distribuyen proporcionalmente.
        """
        lineas = []
        portes = 0.0
        
        # Patron: P063 DESCRIPCION 48,00 2,500 0,00 120,00
        patron = re.compile(
            r'^(P\d{2,4}|SE\d{2})\s+'         # Codigo (P063, P130, SE99)
            r'(.+?)\s+'                        # Descripcion
            r'(\d+[.,]\d{2})\s+'               # Cantidad
            r'(\d+[.,]\d{3})\s+'               # Precio (3 decimales)
            r'(\d+[.,]\d{2})\s+'               # Descuento
            r'(\d+[.,]\d{2})',                 # Importe
            re.MULTILINE
        )
        
        for match in patron.finditer(texto):
            codigo = match.group(1)
            descripcion = match.group(2).strip()
            cantidad = self._convertir_europeo(match.group(3))
            precio = self._convertir_europeo(match.group(4))
            importe = self._convertir_europeo(match.group(6))
            
            # Filtrar cabeceras
            if any(x in descripcion.upper() for x in ['DESCRIPCION', 'CANTIDAD', 'PRECIO']):
                continue
            
            # Si es transporte, guardar para distribuir
            if 'TRANSPORTE' in descripcion.upper() or codigo == 'SE99':
                portes = importe
                continue
            
            # Limpiar descripcion (quitar codigo de lote y anio)
            descripcion = re.sub(r'\s+\d{4}\s*$', '', descripcion)
            descripcion = re.sub(r'\s+L\d{2}[A-Z]{2,3}\s*$', '', descripcion)
            descripcion = re.sub(r'\s+\d{4}\s+L\d{2}[A-Z]{2,3}\s*$', '', descripcion)
            
            lineas.append({
                'codigo': codigo,
                'articulo': descripcion[:50],
                'cantidad': int(cantidad),
                'precio_ud': round(precio, 3),
                'iva': 21,
                'base': round(importe, 2)
            })
        
        # Distribuir portes proporcionalmente entre productos
        if portes > 0 and lineas:
            base_productos = sum(l['base'] for l in lineas)
            for linea in lineas:
                proporcion = linea['base'] / base_productos
                linea['base'] = round(linea['base'] + portes * proporcion, 2)
        
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
        patron = re.search(r'(\d{3,}[.,]\d{2})\s*Euros', texto, re.IGNORECASE)
        if patron:
            return self._convertir_europeo(patron.group(1))
        return None
    
    def extraer_fecha(self, texto: str) -> Optional[str]:
        """Extrae fecha de la factura (formato dd/mm/yyyy)."""
        patron = re.search(r'(\d{2}/\d{2}/\d{4})', texto)
        if patron:
            return patron.group(1)
        return None
    
    def extraer_numero_factura(self, texto: str) -> Optional[str]:
        """Extrae numero de factura (formato F25/123)."""
        patron = re.search(r'(F\d+/\d+)', texto)
        if patron:
            return patron.group(1)
        return None
