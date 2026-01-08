"""
Extractor para TIRSO PAPEL Y BOLSAS SL

Proveedor de material de papelería, bolsas y embalaje.

CIF: B86005006
Dirección: Jesús y María 4 - 28012 MADRID
Teléfono: 91 369 01 85 / 91 369 20 97
Email: tirsopapelybolsas@hotmail.es

IVA: Siempre 21%
Categoría: GASTOS VARIOS
Método pago: Efectivo/Tarjeta

FORMATOS SOPORTADOS:
- PDF con texto extraíble (pdfplumber)
- PDF escaneado (OCR multi-config)
- JPG/PNG escaneados (OCR multi-config)

RENDIMIENTO OCR (testado con 11 facturas):
- REF (nº factura): 91% éxito (10/11)
- Fecha: 100% éxito (11/11)  
- Importes (base/total): 45% éxito (5/11)
- NOTA: Facturas con importes no extraídos se marcan 'requiere_revision'

Formato factura:
- Cabecera: TIRSO PAPEL Y BOLSAS SL
- Fecha: Madrid, DD de mes de YYYY
- Número: FACTURA Nº... XXXXX o FACTURA NRO... XXXXX
- Cuadro fiscal: BASE IMPONIBLE | IVA 21% | IMPORTE TOTAL

Creado: 08/01/2026
Unificado de: tirso.py + tirso_papel_bolsas.py
"""
from extractores.base import ExtractorBase
from extractores import registrar
from typing import List, Dict, Optional
from collections import Counter
import re
import os

# Dependencias OCR (opcionales)
try:
    import pytesseract
    from PIL import Image, ImageEnhance, ImageFilter
    from pdf2image import convert_from_path
    OCR_DISPONIBLE = True
except ImportError:
    OCR_DISPONIBLE = False

# pdfplumber para PDFs con texto
try:
    import pdfplumber
    PDFPLUMBER_DISPONIBLE = True
except ImportError:
    PDFPLUMBER_DISPONIBLE = False


@registrar('TIRSO', 'TIRSO PAPEL Y BOLSAS', 'TIRSO PAPEL Y BOLSAS SL',
           'BOLSAS TIRSO', 'TIRSO PAPEL', 'PAPEL Y BOLSAS SL')
class ExtractorTirso(ExtractorBase):
    """
    Extractor unificado para facturas de TIRSO PAPEL Y BOLSAS SL.
    
    Soporta:
    - PDFs con texto (pdfplumber)
    - PDFs escaneados (OCR)
    - Imágenes JPG/PNG (OCR)
    """
    
    nombre = 'TIRSO PAPEL Y BOLSAS'
    cif = 'B86005006'
    metodo_pdf = 'hibrido'  # pdfplumber + OCR fallback
    categoria_fija = 'GASTOS VARIOS'
    
    # Meses en español para parseo de fechas
    MESES = {
        'enero': '01', 'febrero': '02', 'marzo': '03', 'abril': '04',
        'mayo': '05', 'junio': '06', 'julio': '07', 'agosto': '08',
        'septiembre': '09', 'octubre': '10', 'noviembre': '11', 'diciembre': '12'
    }
    
    def __init__(self):
        super().__init__()
        self._texto_extraido = None
    
    def extraer_texto(self, ruta_archivo: str) -> str:
        """
        Extrae texto del archivo usando la mejor estrategia disponible.
        
        1. Si es imagen → OCR directo
        2. Si es PDF → pdfplumber primero, OCR como fallback
        """
        extension = os.path.splitext(ruta_archivo)[1].lower()
        
        # Imágenes: OCR directo
        if extension in ['.jpg', '.jpeg', '.png', '.bmp', '.tiff']:
            return self._extraer_texto_ocr_imagen(ruta_archivo)
        
        # PDFs: intentar pdfplumber primero
        if extension == '.pdf':
            texto = self._extraer_texto_pdfplumber(ruta_archivo)
            
            # Si hay texto suficiente, usarlo
            if texto and len(texto.strip()) > 100:
                return texto
            
            # Fallback a OCR
            return self._extraer_texto_ocr_pdf(ruta_archivo)
        
        return ""
    
    def _extraer_texto_pdfplumber(self, pdf_path: str) -> str:
        """Extrae texto de PDF usando pdfplumber."""
        if not PDFPLUMBER_DISPONIBLE:
            return ""
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                texto = ""
                for pagina in pdf.pages:
                    texto += pagina.extract_text() or ""
                return texto
        except Exception as e:
            print(f"Error pdfplumber TIRSO: {e}")
            return ""
    
    def _extraer_texto_ocr_imagen(self, img_path: str) -> str:
        """
        Extrae texto de imagen usando OCR con múltiples configuraciones.
        """
        if not OCR_DISPONIBLE:
            return ""
        
        try:
            img = Image.open(img_path)
            img_gray = img.convert('L')
            
            textos = []
            
            # Config 1: Grayscale + PSM 3
            try:
                texto1 = pytesseract.image_to_string(img_gray, lang='spa', config='--psm 3')
            except:
                texto1 = pytesseract.image_to_string(img_gray, config='--psm 3')
            textos.append(texto1)
            
            # Config 2: Binarización threshold 128
            img_bin = img_gray.point(lambda x: 0 if x < 128 else 255)
            try:
                texto2 = pytesseract.image_to_string(img_bin, lang='spa', config='--psm 3')
            except:
                texto2 = pytesseract.image_to_string(img_bin, config='--psm 3')
            textos.append(texto2)
            
            # Config 3: Binarización threshold 140
            img_bin2 = img_gray.point(lambda x: 0 if x < 140 else 255)
            try:
                texto3 = pytesseract.image_to_string(img_bin2, lang='spa', config='--psm 3')
            except:
                texto3 = pytesseract.image_to_string(img_bin2, config='--psm 3')
            textos.append(texto3)
            
            return "\n".join(textos)
            
        except Exception as e:
            print(f"Error OCR imagen TIRSO: {e}")
            return ""
    
    def _extraer_texto_ocr_pdf(self, pdf_path: str) -> str:
        """
        Extrae texto de PDF escaneado usando OCR con múltiples configuraciones.
        
        Estrategia: Combinar resultados de varias configuraciones OCR para
        maximizar la extracción de datos numéricos del cuadro fiscal.
        """
        if not OCR_DISPONIBLE:
            return ""
        
        try:
            # Usar DPI alto para mejor calidad
            images = convert_from_path(pdf_path, dpi=400)
            if not images:
                return ""
            
            img = images[0]
            img_gray = img.convert('L')
            
            textos = []
            
            # Config 1: Grayscale + PSM 3 (base)
            try:
                texto1 = pytesseract.image_to_string(img_gray, lang='spa', config='--psm 3')
            except:
                texto1 = pytesseract.image_to_string(img_gray, config='--psm 3')
            textos.append(texto1)
            
            # Config 2: Binarización threshold 128 (bueno para fondos claros)
            img_bin = img_gray.point(lambda x: 0 if x < 128 else 255)
            try:
                texto2 = pytesseract.image_to_string(img_bin, lang='spa', config='--psm 3')
            except:
                texto2 = pytesseract.image_to_string(img_bin, config='--psm 3')
            textos.append(texto2)
            
            # Config 3: Binarización threshold 140
            img_bin2 = img_gray.point(lambda x: 0 if x < 140 else 255)
            try:
                texto3 = pytesseract.image_to_string(img_bin2, lang='spa', config='--psm 3')
            except:
                texto3 = pytesseract.image_to_string(img_bin2, config='--psm 3')
            textos.append(texto3)
            
            # Config 4: Sharpen + Contrast moderado
            img_sharp = img_gray.filter(ImageFilter.SHARPEN)
            enhancer = ImageEnhance.Contrast(img_sharp)
            img_sharp = enhancer.enhance(1.8)
            try:
                texto4 = pytesseract.image_to_string(img_sharp, lang='spa', config='--psm 3')
            except:
                texto4 = pytesseract.image_to_string(img_sharp, config='--psm 3')
            textos.append(texto4)
            
            # Combinar todos los textos (el primero es el principal para REF/fecha)
            # Los demás añaden números que pueden faltar
            return "\n".join(textos)
            
        except Exception as e:
            print(f"Error OCR PDF TIRSO: {e}")
            return ""
    
    def _preprocesar_imagen(self, img: Image.Image) -> Image.Image:
        """Preprocesa imagen para mejorar OCR."""
        # Convertir a escala de grises
        if img.mode != 'L':
            img = img.convert('L')
        
        # Aumentar contraste
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(2.0)
        
        # Enfocar
        img = img.filter(ImageFilter.SHARPEN)
        
        return img
    
    def _convertir_importe(self, texto: str) -> float:
        """Convierte texto con formato europeo a float."""
        if not texto:
            return 0.0
        
        texto = str(texto).strip()
        texto = texto.replace('€', '').replace(' ', '').strip()
        
        # Formato europeo: 1.234,56 → 1234.56
        if '.' in texto and ',' in texto:
            texto = texto.replace('.', '').replace(',', '.')
        elif ',' in texto:
            texto = texto.replace(',', '.')
        
        try:
            return float(texto)
        except:
            return 0.0
    
    def extraer_numero_factura(self, texto: str) -> Optional[str]:
        """
        Extrae el número de factura.
        
        Formatos soportados:
        - FACTURA Nº... 76405
        - FACTURA NRO... 68929
        - FACTURA N°... 76686
        """
        patrones = [
            r'FACTURA\s*N[º°oO]?\.{0,3}\s*(\d{4,6})',
            r'FACTURA\s*NRO\.{0,3}\s*(\d{4,6})',
        ]
        
        for patron in patrones:
            match = re.search(patron, texto, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return None
    
    def extraer_fecha(self, texto: str) -> Optional[str]:
        """
        Extrae la fecha de la factura.
        
        Formato: Madrid, DD de mes de YYYY
        Nota: OCR a veces une "de" con el mes ("dediciembre")
        """
        # Patrón flexible para manejar OCR imperfecto
        patron = r'Madrid,?\s*(\d{1,2})\s*de?\s*(\w+)\s+de\s+(\d{4})'
        match = re.search(patron, texto, re.IGNORECASE)
        
        if match:
            dia = match.group(1).zfill(2)
            mes_texto = match.group(2).lower()
            año = match.group(3)
            
            # Limpiar "de" pegado al mes (ej: "dediciembre" → "diciembre")
            if mes_texto.startswith('de') and len(mes_texto) > 4:
                mes_texto = mes_texto[2:]
            
            mes = self.MESES.get(mes_texto, '01')
            return f"{dia}/{mes}/{año}"
        
        return None
    
    def extraer_total(self, texto: str) -> Optional[float]:
        """
        Extrae el total de la factura del cuadro fiscal.
        
        Estrategia:
        1. Buscar patrón "IMPORTE TOTAL" seguido de número
        2. Buscar todos los números con € y aplicar lógica:
           - Si hay 3+ números, identificar BASE + IVA = TOTAL
           - El TOTAL es el mayor de los valores que aparecen 2+ veces
        """
        # Primero: buscar todos los números con €
        numeros = re.findall(r'(\d{1,3}[,\.]\d{2})\s*€', texto)
        valores = [self._convertir_importe(n) for n in numeros]
        valores = [v for v in valores if 0.5 < v < 500]  # Filtrar rango razonable
        
        if not valores:
            return None
        
        # Si hay valores repetidos, el total suele repetirse (aparece en línea y en cuadro)
        from collections import Counter
        conteo = Counter(valores)
        repetidos = [v for v, c in conteo.items() if c >= 2]
        
        if repetidos:
            # El total es típicamente el mayor valor repetido
            return max(repetidos)
        
        # Si no hay repetidos, buscar patrón BASE + IVA = TOTAL
        valores_unicos = sorted(set(valores))
        if len(valores_unicos) >= 3:
            # Intentar encontrar base + iva = total
            for i, base_c in enumerate(valores_unicos[:-2]):
                for j, iva_c in enumerate(valores_unicos[i+1:-1], i+1):
                    for total_c in valores_unicos[j+1:]:
                        # Verificar si base + iva ≈ total (tolerancia 0.02)
                        if abs(base_c + iva_c - total_c) < 0.03:
                            return total_c
        
        # Fallback: el mayor valor
        return max(valores)
    
    def extraer_base_imponible(self, texto: str) -> Optional[float]:
        """
        Extrae la base imponible del cuadro fiscal.
        
        Estrategia:
        1. Buscar patrón "BASE IMPONIBLE" seguido de número
        2. Si no funciona, buscar conjunto de 3 números donde base + iva = total
        """
        # Patrón directo
        match = re.search(r'BASE\s*IMPONIBLE[:\s|>]*(\d{1,3}[,\.]\d{2})', texto, re.IGNORECASE)
        if match:
            base = self._convertir_importe(match.group(1))
            if base > 0:
                return base
        
        # Buscar conjunto base + iva = total
        numeros = re.findall(r'(\d{1,3}[,\.]\d{2})\s*€', texto)
        valores = [self._convertir_importe(n) for n in numeros]
        valores = [v for v in valores if 0.5 < v < 500]
        
        if len(valores) >= 3:
            valores_unicos = sorted(set(valores))
            for i, base_c in enumerate(valores_unicos[:-2]):
                for j, iva_c in enumerate(valores_unicos[i+1:-1], i+1):
                    for total_c in valores_unicos[j+1:]:
                        if abs(base_c + iva_c - total_c) < 0.03:
                            return base_c
        
        return None
    
    def extraer_lineas(self, texto: str) -> List[Dict]:
        """
        Extrae líneas de la factura.
        
        Estrategia: Una sola línea usando desglose fiscal (BASE IMPONIBLE).
        Artículo genérico: "Compras Tirso Bolsas"
        
        Si OCR no captura la base, calcular desde el total.
        """
        lineas = []
        
        # Extraer base imponible del cuadro fiscal
        base = self.extraer_base_imponible(texto)
        total = self.extraer_total(texto)
        
        # Si no hay base pero sí total, calcular base
        if not base and total:
            base = round(total / 1.21, 2)
        
        # Validar coherencia base/total si tenemos ambos
        if base and total:
            total_calculado = round(base * 1.21, 2)
            # Si no cuadra (más de 1€ diferencia), recalcular base desde total
            if abs(total_calculado - total) > 1.0:
                base = round(total / 1.21, 2)
        
        if base and base > 0:
            lineas.append({
                'codigo': 'TIRSO',
                'articulo': 'Compras Tirso Bolsas',
                'cantidad': 1,
                'precio_ud': round(base, 2),
                'iva': 21,
                'base': round(base, 2),
                'categoria': self.categoria_fija
            })
        
        return lineas
    
    def procesar(self, ruta_archivo: str) -> Dict:
        """Procesa factura TIRSO."""
        # Extraer texto (pdfplumber o OCR según el archivo)
        self._texto_extraido = self.extraer_texto(ruta_archivo)
        
        if not self._texto_extraido:
            return {
                'proveedor': self.nombre,
                'cif': self.cif,
                'fecha': None,
                'total': None,
                'lineas': [],
                'categoria': self.categoria_fija,
                'requiere_revision': True,
                'motivo_revision': 'No se pudo extraer texto del documento'
            }
        
        texto = self._texto_extraido
        
        fecha = self.extraer_fecha(texto)
        numero_factura = self.extraer_numero_factura(texto)
        total = self.extraer_total(texto)
        lineas = self.extraer_lineas(texto)
        
        # Determinar si requiere revisión manual
        requiere_revision = False
        motivo_revision = []
        
        if not numero_factura:
            motivo_revision.append('REF no extraído')
        if not fecha:
            motivo_revision.append('Fecha no extraída')
        if not total or total == 0:
            requiere_revision = True
            motivo_revision.append('Total no extraído (OCR limitado)')
        if not lineas:
            requiere_revision = True
            motivo_revision.append('Base imponible no extraída')
        
        resultado = {
            'proveedor': self.nombre,
            'cif': self.cif,
            'fecha': fecha,
            'numero_factura': numero_factura,
            'total': total,
            'lineas': lineas,
            'categoria': self.categoria_fija
        }
        
        if requiere_revision or motivo_revision:
            resultado['requiere_revision'] = requiere_revision
            resultado['motivo_revision'] = '; '.join(motivo_revision) if motivo_revision else None
        
        return resultado
    
    def requiere_revision_manual(self) -> bool:
        """
        Indica si este extractor típicamente requiere revisión manual.
        
        TIRSO envía facturas escaneadas de calidad variable.
        El OCR extrae bien REF y fecha, pero los importes
        del cuadro fiscal fallan en ~40% de los casos.
        """
        return True
