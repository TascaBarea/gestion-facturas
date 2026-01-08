"""
Extractor para PRODUCTOS MANIPULADOS ABELLAN S.L.

Marca comercial: El Labrador / Pepejo
Productor de conservas vegetales artesanales
CIF: B30473326
IBAN: REDACTED_IBAN (CaixaBank)

REQUIERE OCR - Las facturas son imagenes escaneadas
Usa fallback a resumen fiscal cuando OCR falla

Productos (todos 10% IVA - conservas vegetales):
- Tomate asado lena 720ml
- Tomate rallado especial tostadas 720ml
- Tomate confitado 370ml
- Mermelada de tomate/higos 370ml
- Tomates secos con aceite 370ml
- Pisto murciano 370ml
- Tomate frito con/sin huevo 370ml

Creado: 21/12/2025
Validado: 6/6 facturas (1T25-4T25)
"""
from extractores.base import ExtractorBase
from extractores import registrar
from typing import List, Dict, Optional
import re


@registrar('MANIPULADOS ABELLAN', 'ABELLAN', 'EL LABRADOR', 'PEPEJO', 
           'PEPEJOLABRADOR', 'PRODUCTOS MANIPULADOS')
class ExtractorManipuladosAbellan(ExtractorBase):
    """Extractor para facturas de MANIPULADOS ABELLAN (OCR robusto)."""
    
    nombre = 'MANIPULADOS ABELLAN'
    cif = 'B30473326'
    iban = 'REDACTED_IBAN'
    metodo_pdf = 'ocr'
    categoria_fija = 'CONSERVAS VEGETALES'
    
    def extraer_texto_ocr(self, pdf_path: str) -> str:
        """Extrae texto con OCR optimizado."""
        try:
            from pdf2image import convert_from_path
            import pytesseract
            from PIL import ImageEnhance
            
            images = convert_from_path(pdf_path, dpi=350)
            mejor_texto = ""
            mejor_lineas = 0
            
            # Probar diferentes configuraciones
            for psm in [4, 6]:
                for contraste in [1.5, 2.0]:
                    img = images[0]
                    gray = img.convert('L')
                    enhancer = ImageEnhance.Contrast(gray)
                    enhanced = enhancer.enhance(contraste)
                    
                    texto = pytesseract.image_to_string(enhanced, lang='eng', 
                        config=f'--psm {psm}')
                    
                    # Contar lineas de producto
                    count = len(re.findall(
                        r'\d+[,.]\d{2}\s+[A-Z].*?\d+[,.]\d{4}\s+\d+[,.]\d{2}', 
                        texto))
                    if count > mejor_lineas:
                        mejor_lineas = count
                        mejor_texto = texto
            
            return mejor_texto
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
        Extrae lineas de producto con OCR.
        Si OCR falla, usa base imponible del resumen fiscal.
        """
        lineas = []
        
        # Intentar extraer lineas individuales
        for line in texto.split('\n'):
            line = line.strip()
            
            m = re.match(
                r'^(\d+)[,.]00\s+'           # Cantidad
                r'(.+?)\s+'                   # Producto
                r'(\d+[,.]\d{4})\s+'          # Precio
                r'(\d+[,.]\d{2})$',           # Importe
                line
            )
            
            if m:
                cantidad = int(m.group(1))
                articulo = m.group(2).strip()
                precio = self._convertir_europeo(m.group(3))
                importe = self._convertir_europeo(m.group(4))
                
                # Limpiar nombre
                articulo = re.sub(r'\s+EL[- ]LABRADOR$', '', articulo)
                articulo = re.sub(r'\s+370\s+ML$', ' 370ML', articulo)
                articulo = re.sub(r'\s+720\s+ML$', ' 720ML', articulo)
                # Corregir errores OCR comunes
                articulo = re.sub(r'^[TJO]TOMATE', 'TOMATE', articulo)
                articulo = re.sub(r'^OMATE', 'TOMATE', articulo)
                articulo = re.sub(r'^JTOMATE', 'TOMATE', articulo)
                articulo = re.sub(r'^ISTO', 'PISTO', articulo)
                articulo = re.sub(r'MeRMELADA', 'MERMELADA', articulo)
                
                if importe > 5:
                    lineas.append({
                        'codigo': '',
                        'articulo': articulo[:50],
                        'cantidad': cantidad,
                        'precio_ud': round(precio, 4),
                        'iva': 10,
                        'base': round(importe, 2)
                    })
        
        # Extraer base fiscal del resumen
        base_fiscal = None
        for line in texto.split('\n'):
            m = re.search(
                r'(\d{2,3}[,.]\d{2})\s+10\s+(\d+[,.]\d{2})\s+(\d{2,3}[,.]\d{2})', 
                line)
            if m:
                base_fiscal = self._convertir_europeo(m.group(1))
                break
        
        # Si lineas no cuadran con base fiscal, usar fallback
        suma_lineas = sum(l['base'] for l in lineas)
        if base_fiscal and abs(suma_lineas - base_fiscal) > 10:
            lineas = [{
                'codigo': '',
                'articulo': 'CONSERVAS VEGETALES',
                'cantidad': 1,
                'precio_ud': round(base_fiscal, 2),
                'iva': 10,
                'base': round(base_fiscal, 2)
            }]
        
        return lineas
    
    def extraer_total(self, texto: str) -> Optional[float]:
        """Extrae total del resumen fiscal."""
        for line in texto.split('\n'):
            m = re.search(
                r'(\d{2,3}[,.]\d{2})\s+10\s+(\d+[,.]\d{2})\s+(\d{2,3}[,.]\d{2})', 
                line)
            if m:
                return self._convertir_europeo(m.group(3))
        return None
    
    def extraer_fecha(self, texto: str) -> Optional[str]:
        """Extrae fecha de la factura."""
        m = re.search(r'(\d{2}/\d{2}/\d{4})', texto)
        return m.group(1) if m else None
    
    def extraer_numero_factura(self, texto: str) -> Optional[str]:
        """Extrae numero de factura."""
        m = re.search(r'F25/\d+', texto)
        return m.group(0) if m else None
