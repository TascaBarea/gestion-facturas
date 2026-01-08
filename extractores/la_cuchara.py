"""
Extractor para LA CUCHARA GOURMET SL

Ensaladillas rusas y productos preparados.
CIF: B67775619
Dirección: C/Mesón de Paredes, 19 - 28012 Madrid

IMPORTANTE: Todas las facturas de LA CUCHARA son tickets fotografiados (JPG) o PDF escaneados.
Este extractor usa OCR (Tesseract) para extraer el texto.

LÓGICA DE CATEGORÍAS:
- Archivos JPG → Ensaladilla rusa (RUSA TASCA) → categoría 'ENSALADILLA RUSA'
- Archivos PDF → Envases → categoría 'ENVASES'

REQUISITOS:
  pip install pytesseract pdf2image Pillow
  
  Windows:
  - Tesseract: https://github.com/UB-Mannheim/tesseract/wiki
    (instalar con idioma español: spa)
  - Poppler: https://github.com/oschwartz10612/poppler-windows/releases
    (añadir bin/ al PATH)

Formato ticket:
  FACTURA SIMPLIFICADA 1-XXXXXX
  Fecha: DD/MM/YY HH:MM
  
  Un.    Descripción           Total
  ----------------------------------
  19     RUSA TASCA      (55)  1.045,00
  400    ENVASE 470ML    (,12) 48,00
  
  IVA 10%        (950,00):     95,00
  
  TOTAL 1.045,00 E

IVA: 10% (alimentación)

IMPORTANTE: "IVA incl. en los precios"
Los totales de línea YA incluyen IVA.
Para calcular la base: total_linea / 1.10

Creado: 04/01/2026
Actualizado: 06/01/2026 - JPG=ENSALADILLA RUSA, PDF=ENVASES
"""
from extractores.base import ExtractorBase
from extractores import registrar
from typing import List, Dict, Optional
import re
import os

# Intentar importar dependencias OCR
try:
    import pytesseract
    from PIL import Image
    from pdf2image import convert_from_path
    OCR_DISPONIBLE = True
except ImportError:
    OCR_DISPONIBLE = False


@registrar('LA CUCHARA', 'LA CUCHARA GOURMET', 'CUCHARA LAVAPIES', 'LA CUCHARA LAVAPIES')
class ExtractorLaCuchara(ExtractorBase):
    """Extractor para facturas de LA CUCHARA GOURMET (OCR)."""
    
    nombre = 'LA CUCHARA GOURMET'
    cif = 'B67775619'
    metodo_pdf = 'ocr'  # Indica que usa OCR
    
    def __init__(self):
        super().__init__()
        self._texto_ocr = None
        self._es_imagen = False  # True si es JPG/PNG, False si es PDF
    
    def extraer_texto_ocr(self, ruta_archivo: str) -> str:
        """Extrae texto usando OCR (Tesseract)."""
        if not OCR_DISPONIBLE:
            raise ImportError("Dependencias OCR no instaladas: pip install pytesseract pdf2image Pillow")
        
        extension = os.path.splitext(ruta_archivo)[1].lower()
        
        try:
            if extension in ['.jpg', '.jpeg', '.png', '.bmp', '.tiff']:
                # Imagen directa → ENSALADILLA RUSA
                self._es_imagen = True
                img = Image.open(ruta_archivo)
                try:
                    texto = pytesseract.image_to_string(img, lang='spa')
                except:
                    texto = pytesseract.image_to_string(img)
            elif extension == '.pdf':
                # PDF → ENVASES
                self._es_imagen = False
                images = convert_from_path(ruta_archivo, dpi=300)
                try:
                    texto = pytesseract.image_to_string(images[0], lang='spa')
                except:
                    texto = pytesseract.image_to_string(images[0])
            else:
                return ""
            
            return texto
        except Exception as e:
            print(f"Error OCR: {e}")
            return ""
    
    def _determinar_categoria(self) -> str:
        """
        Determina la categoría según el tipo de archivo.
        - JPG/imágenes → ENSALADILLA RUSA (producto principal)
        - PDF → ENVASES
        """
        if self._es_imagen:
            return 'ENSALADILLA RUSA'
        else:
            return 'ENVASES'
    
    def procesar(self, ruta_archivo: str) -> Dict:
        """Procesa factura LA CUCHARA usando OCR."""
        # Determinar tipo de archivo ANTES de OCR
        extension = os.path.splitext(ruta_archivo)[1].lower()
        self._es_imagen = extension in ['.jpg', '.jpeg', '.png', '.bmp', '.tiff']
        
        # Extraer texto con OCR
        self._texto_ocr = self.extraer_texto_ocr(ruta_archivo)
        
        if not self._texto_ocr:
            return {
                'proveedor': self.nombre,
                'cif': self.cif,
                'fecha': None,
                'total': None,
                'lineas': []
            }
        
        # Extraer datos
        return {
            'proveedor': self.nombre,
            'cif': self.cif,
            'fecha': self.extraer_fecha(self._texto_ocr),
            'total': self.extraer_total(self._texto_ocr),
            'lineas': self.extraer_lineas(self._texto_ocr)
        }
    
    def extraer_lineas(self, texto: str) -> List[Dict]:
        """
        Extrae líneas de productos del ticket.
        
        Categoría según tipo de archivo:
        - JPG → ENSALADILLA RUSA
        - PDF → ENVASES
        """
        lineas = []
        categoria = self._determinar_categoria()
        
        # Determinar descripción según categoría
        if categoria == 'ENSALADILLA RUSA':
            descripcion_default = 'RUSA TASCA'
        else:
            descripcion_default = 'ENVASES LA CUCHARA'
        
        # Primero intentar extraer desde el desglose fiscal (más fiable)
        patron_iva = re.search(
            r'IVA\s*10\s*%?\s*\(?([\d.,]+)\)?[:\s]*([\d.,]+)',
            texto, re.IGNORECASE
        )
        
        if patron_iva:
            base = self._convertir_europeo(patron_iva.group(1))
            if base and base > 0:
                # Buscar cantidad si es RUSA TASCA
                cantidad = 1
                if categoria == 'ENSALADILLA RUSA':
                    match_rusa = re.search(r'(\d{1,3})\s+RUSA\s+TASCA', texto, re.IGNORECASE)
                    if match_rusa:
                        cantidad = int(match_rusa.group(1))
                else:
                    # Para envases, buscar cantidad
                    match_envase = re.search(r'(\d{1,4})\s+ENVASE', texto, re.IGNORECASE)
                    if match_envase:
                        cantidad = int(match_envase.group(1))
                
                lineas.append({
                    'codigo': 'CUCHARA',
                    'articulo': descripcion_default,
                    'cantidad': cantidad,
                    'precio_ud': round(base / cantidad, 2) if cantidad > 0 else base,
                    'iva': 10,
                    'base': round(base, 2),
                    'categoria': categoria
                })
                return lineas
        
        # Si no hay desglose, calcular desde total
        total = self.extraer_total(texto)
        if total and total > 0:
            base = round(total / 1.10, 2)
            
            # Buscar cantidad
            cantidad = 1
            if categoria == 'ENSALADILLA RUSA':
                match_rusa = re.search(r'(\d{1,3})\s+RUSA\s+TASCA', texto, re.IGNORECASE)
                if match_rusa:
                    cantidad = int(match_rusa.group(1))
            else:
                match_envase = re.search(r'(\d{1,4})\s+ENVASE', texto, re.IGNORECASE)
                if match_envase:
                    cantidad = int(match_envase.group(1))
            
            lineas.append({
                'codigo': 'CUCHARA',
                'articulo': descripcion_default,
                'cantidad': cantidad,
                'precio_ud': round(base / cantidad, 2) if cantidad > 0 else base,
                'iva': 10,
                'base': base,
                'categoria': categoria
            })
        
        return lineas
    
    def _convertir_europeo(self, texto: str) -> float:
        """Convierte formato europeo (1.234,56) a float."""
        if not texto:
            return 0.0
        texto = str(texto).strip()
        # Eliminar símbolos
        texto = texto.replace('€', '').replace('E', '').strip()
        
        # Formato europeo: 1.045,00 → 1045.00
        if '.' in texto and ',' in texto:
            texto = texto.replace('.', '').replace(',', '.')
        elif ',' in texto:
            texto = texto.replace(',', '.')
        
        try:
            return float(texto)
        except:
            return 0.0
    
    def extraer_total(self, texto: str) -> Optional[float]:
        """Extrae el total de la factura."""
        patrones = [
            r'TOTAL\s+([\d.,]+)\s*E',
            r'TOTAL[:\s]+([\d.,]+)',
            r'Vale[:\s]+([\d.,]+)',
        ]
        
        for patron in patrones:
            match = re.search(patron, texto, re.IGNORECASE)
            if match:
                total = self._convertir_europeo(match.group(1))
                if total and total > 0:
                    return total
        
        return None
    
    def extraer_fecha(self, texto: str) -> Optional[str]:
        """Extrae la fecha de la factura."""
        patron = re.search(r'Fecha[:\s]*(\d{2}/\d{2}/\d{2})', texto, re.IGNORECASE)
        
        if patron:
            fecha = patron.group(1)
            partes = fecha.split('/')
            if len(partes) == 3:
                dia, mes, año = partes
                if len(año) == 2:
                    año = '20' + año
                return f"{dia}/{mes}/{año}"
        
        return None
    
    def extraer_numero_factura(self, texto: str) -> Optional[str]:
        """Extrae el número de factura simplificada."""
        patron = re.search(r'FACTURA\s*SIMPLIFICADA\s*(\d+-\d+)', texto, re.IGNORECASE)
        if patron:
            return patron.group(1)
        return None
