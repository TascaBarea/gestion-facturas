"""
Extractor para FISHGOURMET S.L.

Ahumados de pescado gourmet
CIF: B85975126
IBAN: ES57 2100 2127 1502 0045 4128 (LA CAIXA)
Direccion: C/ Romero 7, Pol. Ind. La Mata, 28440 Guadarrama (Madrid)

REQUIERE OCR - Las facturas son imagenes PDF
Usa base imponible del resumen fiscal (mas fiable que OCR de lineas)

Productos (todos 10% IVA):
- Salmon ahumado tarrina 350g
- Bacalao ahumado tarrina 350g
- Lomitos de arenque al dulce de vinagre 350g
- Anchoa Cantabrico 00 - tarrina 20 lomos

Creado: 21/12/2025
Validado: 6/6 facturas (1T25, 2T25, 3T25)
"""
from extractores.base import ExtractorBase
from extractores import registrar
from typing import List, Dict, Optional
import re


@registrar('FISHGOURMET', 'FISH GOURMET', 'FISHGOURMET S.L.')
class ExtractorFishgourmet(ExtractorBase):
    """Extractor para facturas de FISHGOURMET S.L. (OCR robusto)."""
    
    nombre = 'FISHGOURMET'
    cif = 'B85975126'
    iban = 'ES57 2100 2127 1502 0045 4128'
    metodo_pdf = 'ocr'
    categoria_fija = 'SALAZONES'
    
    def extraer_texto_ocr(self, pdf_path: str) -> str:
        """Extrae texto usando OCR optimizado."""
        try:
            from pdf2image import convert_from_path
            import pytesseract
            from PIL import ImageEnhance
            
            images = convert_from_path(pdf_path, dpi=300)
            texto = ""
            for img in images:
                gray = img.convert('L')
                enhancer = ImageEnhance.Contrast(gray)
                enhanced = enhancer.enhance(1.5)
                texto += pytesseract.image_to_string(enhanced, lang='eng', 
                    config='--psm 4') + "\n"
            return texto
        except Exception as e:
            return ""
    
    def _convertir_europeo(self, texto: str) -> float:
        """Convierte formato europeo a float."""
        if not texto:
            return 0.0
        texto = str(texto).strip().replace(' ', '')
        if '.' in texto and ',' in texto:
            texto = texto.replace('.', '').replace(',', '.')
        elif ',' in texto:
            texto = texto.replace(',', '.')
        try:
            return float(texto)
        except:
            return 0.0
    
    def extraer_lineas(self, texto: str) -> List[Dict]:
        """
        Extrae lineas de producto.
        
        Usa base imponible del resumen fiscal porque OCR
        no captura bien las tablas de productos.
        """
        lineas = []
        
        # Extraer base imponible del resumen fiscal
        # BASE IMPONIBLE 78,00 €
        m_base = re.search(r'BASE IMPONIBLE\s+([\d,.]+)\s*[€E]', texto)
        if m_base:
            base_fiscal = self._convertir_europeo(m_base.group(1))
            
            if base_fiscal > 0:
                lineas = [{
                    'codigo': '',
                    'articulo': 'AHUMADOS PESCADO',
                    'cantidad': 1,
                    'precio_ud': round(base_fiscal, 2),
                    'iva': 10,
                    'base': round(base_fiscal, 2)
                }]
        
        return lineas
    
    def extraer_total(self, texto: str) -> Optional[float]:
        """
        Extrae total de la factura.
        
        Calcula desde base imponible (mas fiable que OCR del total).
        """
        m_base = re.search(r'BASE IMPONIBLE\s+([\d,.]+)\s*[€E]', texto)
        if m_base:
            base = self._convertir_europeo(m_base.group(1))
            return round(base * 1.10, 2)
        return None
    
    def extraer_fecha(self, texto: str) -> Optional[str]:
        """Extrae fecha de la factura."""
        # Formato: DD/MM/YYYY seguido de numero de factura
        m = re.search(r'(\d{2}/\d{2}/\d{4})\s+\d+', texto)
        return m.group(1) if m else None
    
    def extraer_numero_factura(self, texto: str) -> Optional[str]:
        """Extrae numero de factura."""
        # Formato: fecha seguida de numero (8 digitos)
        m = re.search(r'\d{2}/\d{2}/\d{4}\s+(\d{8})', texto)
        return m.group(1) if m else None
