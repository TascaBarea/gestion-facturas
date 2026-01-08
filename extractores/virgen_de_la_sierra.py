# extractores/virgen_de_la_sierra.py
"""
Extractor para BODEGA VIRGEN DE LA SIERRA S.COOP.
Bodega cooperativa en Villarroya de la Sierra, Zaragoza

CIF: F50019868
Método: pdfplumber + OCR fallback para escaneados

Productos: vinos (Vendimia Seleccionada, Albada), portes
IVA: 21% (bebidas alcohólicas)

VERSIÓN: v5.15 - 07/01/2026
- FIX: Quitar código (XXX-XXXXX) del artículo
- FIX: Quitar año (2022, 2023, 2024) del artículo
- FIX: Soporte OCR para PDFs escaneados
- Nombre normalizado: VIRGEN DE LA SIERRA
"""
from extractores.base import ExtractorBase
from extractores import registrar
from typing import List, Dict, Optional
import re
import pdfplumber

# OCR imports (opcional)
try:
    from pdf2image import convert_from_path
    import pytesseract
    OCR_DISPONIBLE = True
except ImportError:
    OCR_DISPONIBLE = False


@registrar('VIRGEN DE LA SIERRA', 'BODEGA VIRGEN DE LA SIERRA', 'VIRGEN SIERRA', 
           'BODEGA VIRGEN DE LA SIERRA S.COOP.', 'BODEGAS VIRGEN DE LA SIERRA',
           'VIRGEN_DE_LA_SIERRA', 'BODEGA_VIRGEN_DE_LA_SIERRA')
class ExtractorVirgenDeLaSierra(ExtractorBase):
    """Extractor para facturas de Bodega Virgen de la Sierra."""
    
    nombre = 'VIRGEN DE LA SIERRA'
    cif = 'F50019868'
    iban = ''
    metodo_pdf = 'pdfplumber'
    
    def extraer_texto(self, pdf_path: str) -> str:
        """Extrae texto del PDF con pdfplumber, fallback a OCR si es escaneado."""
        try:
            texto_completo = []
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    texto = page.extract_text()
                    if texto:
                        texto_completo.append(texto)
            
            resultado = '\n'.join(texto_completo)
            
            # Si no hay texto suficiente y OCR está disponible, usar OCR
            if len(resultado.strip()) < 100 and OCR_DISPONIBLE:
                print(f"[VIRGEN] PDF escaneado detectado, usando OCR...")
                resultado = self._extraer_con_ocr(pdf_path)
            
            return resultado
        except Exception as e:
            print(f"[VIRGEN] Error extrayendo texto: {e}")
            return ''
    
    def _extraer_con_ocr(self, pdf_path: str) -> str:
        """Extrae texto usando OCR (Tesseract) con configuración para tablas."""
        try:
            imagenes = convert_from_path(pdf_path, dpi=300)
            textos = []
            custom_config = r'--oem 3 --psm 6'  # Config para tablas
            
            for img in imagenes:
                # Usar inglés (más fiable para números)
                try:
                    texto = pytesseract.image_to_string(img, lang='spa', config=custom_config)
                except:
                    texto = pytesseract.image_to_string(img, lang='eng', config=custom_config)
                textos.append(texto)
            
            return '\n'.join(textos)
        except Exception as e:
            print(f"[VIRGEN] Error OCR: {e}")
            return ''
    
    def extraer_lineas(self, texto: str) -> List[Dict]:
        """
        Extrae líneas de productos.
        
        Formato PDF:
        201-02023 C.P. VENDIMIA SELECCIONADA 2023 48,00 4,600000 220,80
        202-00025 ALBADA PARAJE CAÑADILLA 2,00 8,000000 16,00
        115-10004 PORTES TRANSPORTE 1,00 25,000000 25,00
        
        Salida esperada (artículo limpio, sin código ni año):
        - C.P. VENDIMIA SELECCIONADA
        - ALBADA PARAJE CAÑADILLA
        - PORTES TRANSPORTE
        """
        lineas = []
        
        if not texto:
            return lineas
        
        # Patrón para líneas de producto
        # Código: XXX-XXXXX (3 dígitos - 5 dígitos)
        # Descripción: texto variable (puede incluir año)
        # Cantidad: XX,XX
        # Precio: XX,XXXXXX (6 decimales)
        # Importe: XXX,XX
        patron_linea = re.compile(
            r'^(\d{3}-\d{5})\s+'              # Código (grupo 1) - se descarta
            r'(.+?)\s+'                        # Descripción (grupo 2)
            r'(\d+,\d{2})\s+'                  # Cantidad (grupo 3)
            r'(\d+,\d{6})\s+'                  # Precio 6 decimales (grupo 4)
            r'(\d+,\d{2})$',                   # Importe (grupo 5)
            re.MULTILINE
        )
        
        for match in patron_linea.finditer(texto):
            codigo = match.group(1)  # Se guarda pero no se usa en artículo
            descripcion = match.group(2).strip()
            cantidad = self._convertir_europeo(match.group(3))
            precio = self._convertir_europeo(match.group(4))
            importe = self._convertir_europeo(match.group(5))
            
            # Limpiar descripción: quitar año al final (2020-2029)
            articulo = self._limpiar_articulo(descripcion)
            
            if importe > 0:
                lineas.append({
                    'codigo': codigo,
                    'articulo': articulo[:50],
                    'cantidad': cantidad,
                    'precio_ud': round(precio, 4),
                    'iva': 21,  # Vinos siempre 21%
                    'base': round(importe, 2)
                })
        
        return lineas
    
    def _limpiar_articulo(self, desc: str) -> str:
        """
        Limpia la descripción del producto:
        - Quita año al final (2020, 2021, 2022, 2023, 2024, 2025, etc.)
        - Quita "Uds. X" si aparece
        - Normaliza espacios
        """
        # Quitar año al final (formato: espacio + 4 dígitos empezando por 20)
        desc = re.sub(r'\s+20\d{2}$', '', desc)
        
        # Quitar "Uds. X" si aparece
        desc = re.sub(r'\s+Uds\.\s*\d+', '', desc)
        
        # Normalizar espacios
        desc = ' '.join(desc.split())
        
        return desc.strip()
    
    def extraer_total(self, texto: str) -> Optional[float]:
        """Extrae el total de la factura."""
        if not texto:
            return None
        
        # Patrón 1: XXX,XX€ (sin espacio)
        patron1 = re.search(r'(\d+,\d{2})€', texto)
        if patron1:
            return self._convertir_europeo(patron1.group(1))
        
        # Patrón 2: XXX,XX € (con espacio)
        patron2 = re.search(r'(\d+,\d{2})\s*€', texto)
        if patron2:
            return self._convertir_europeo(patron2.group(1))
        
        # Patrón 3: Calcular desde cuadro fiscal: BASE + IVA
        patron_fiscal = re.search(
            r'(\d+,\d{2})\s+21,00\s+(\d+,\d{2})',
            texto
        )
        if patron_fiscal:
            base = self._convertir_europeo(patron_fiscal.group(1))
            iva = self._convertir_europeo(patron_fiscal.group(2))
            return round(base + iva, 2)
        
        # Patrón 4 (OCR): Buscar fecha vencimiento seguida de importe
        # Formato: DD-MM-YYYY XXX,XX (típico en facturas escaneadas)
        patron_ocr = re.search(
            r'\d{2}-\d{2}-\d{4}\s+(\d+,\d{2})',
            texto
        )
        if patron_ocr:
            return self._convertir_europeo(patron_ocr.group(1))
        
        return None
    
    def extraer_fecha(self, texto: str) -> Optional[str]:
        """Extrae fecha de emisión (formato DD-MM-YYYY -> DD/MM/YYYY)."""
        if not texto:
            return None
        
        patron = re.search(r'(\d{2})-(\d{2})-(\d{4})', texto)
        if patron:
            return f"{patron.group(1)}/{patron.group(2)}/{patron.group(3)}"
        return None
    
    def extraer_referencia(self, texto: str) -> Optional[str]:
        """Extrae número de factura (formato FV00250XXX)."""
        if not texto:
            return None
        
        # Patrón estándar
        patron = re.search(r'(FV\d{8,})', texto)
        if patron:
            return patron.group(1)
        
        # Patrón OCR: puede tener espacios o caracteres extra
        patron_ocr = re.search(r'FV\s*0*(\d{6,})', texto)
        if patron_ocr:
            return f"FV{patron_ocr.group(1).zfill(8)}"
        
        return None
    
    def _convertir_europeo(self, texto: str) -> float:
        """Convierte formato europeo (1.234,56) a float."""
        if not texto:
            return 0.0
        texto = str(texto).strip()
        # Si tiene punto y coma, es formato europeo completo
        if '.' in texto and ',' in texto:
            texto = texto.replace('.', '').replace(',', '.')
        # Si solo tiene coma, la coma es decimal
        elif ',' in texto:
            texto = texto.replace(',', '.')
        try:
            return float(texto)
        except:
            return 0.0
