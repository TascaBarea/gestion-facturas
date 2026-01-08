"""
Extractor para TIRSO PAPEL Y BOLSAS SL

Proveedor de material de papelería, bolsas y embalaje.

CIF: B-86005006
Dirección: Jesús y María 4 - 28012 MADRID
IVA: 21% (material papelería)
Categoría: PAPELERIA Y EMBALAJE

IMPORTANTE: Este proveedor envía facturas ESCANEADAS que requieren OCR.
La tasa de extracción automática es aproximadamente 25-30%.
Las facturas que no cuadran requieren REVISIÓN MANUAL.

Productos típicos:
- Papel parafinado / charcutería
- Papel cristal / manila
- Bolsas kraft con ventana
- Rollo celofán
- Etiquetas kraft / cartón
- Bobina hilo algodón
- Carteras celulosa

Formato factura:
- Escaneada (imagen, no texto)
- Cuadro fiscal: BASE IMPONIBLE | IVA 21% | IMPORTE TOTAL

Creado: 01/01/2026
Validado: 3/13 facturas (23% - LIMITADO por calidad OCR)
"""
from extractores.base import ExtractorBase
from extractores import registrar
from typing import List, Dict, Optional, Tuple
import re
from collections import Counter

# Dependencias OCR
try:
    from pdf2image import convert_from_path
    import pytesseract
    from PIL import Image, ImageEnhance, ImageFilter
    OCR_DISPONIBLE = True
except ImportError:
    OCR_DISPONIBLE = False


@registrar('TIRSO', 'TIRSO PAPEL Y BOLSAS', 'TIRSO PAPEL Y BOLSAS SL',
           'BOLSAS TIRSO', 'TIRSO PAPEL', 'PAPEL Y BOLSAS SL')
class ExtractorTirso(ExtractorBase):
    """
    Extractor para facturas de TIRSO PAPEL Y BOLSAS SL.
    
    NOTA: Este extractor usa OCR para facturas escaneadas.
    La tasa de éxito es ~25-30%. Las facturas que no cuadran
    deben revisarse manualmente.
    """
    
    nombre = 'TIRSO PAPEL Y BOLSAS'
    cif = 'B86005006'
    iban = None  # Pago en efectivo/tarjeta típicamente
    metodo_pdf = 'ocr'  # Requiere OCR
    categoria_fija = 'PAPELERIA Y EMBALAJE'
    
    def _convertir_importe(self, texto: str) -> float:
        """Convierte texto a float (formato europeo)."""
        if not texto:
            return 0.0
        texto = str(texto).strip().replace(' ', '').replace('€', '')
        if ',' in texto:
            texto = texto.replace('.', '').replace(',', '.')
        try:
            return float(texto)
        except:
            return 0.0
    
    def _preprocesar_imagen(self, img, contraste: float = 2.0):
        """Preprocesa imagen para mejorar OCR."""
        img = img.convert('L')  # Escala de grises
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(contraste)
        img = img.filter(ImageFilter.SHARPEN)
        return img
    
    def _extraer_texto_ocr(self, pdf_path: str) -> str:
        """Extrae texto de PDF escaneado usando OCR."""
        if not OCR_DISPONIBLE:
            return ""
        
        try:
            images = convert_from_path(pdf_path, dpi=350)
            img = self._preprocesar_imagen(images[0], 2.5)
            config = '--oem 3 --psm 3'
            return pytesseract.image_to_string(img, config=config)
        except Exception as e:
            print(f"Error OCR: {e}")
            return ""
    
    def extraer_total(self, texto: str) -> Optional[float]:
        """
        Extrae el total de la factura usando múltiples estrategias OCR.
        
        Devuelve None si no puede extraer con confianza.
        """
        if not OCR_DISPONIBLE:
            return None
        
        # Buscar números con formato precio y €
        numeros = re.findall(r'(\d{1,3}[,\.]\d{2})\s*€', texto)
        numeros_float = [self._convertir_importe(n) for n in numeros]
        
        # Filtrar valores válidos (entre 3 y 150€, típico de TIRSO)
        validos = [n for n in numeros_float if 3 < n < 150]
        
        if not validos:
            # Buscar sin € explícito
            numeros = re.findall(r'(\d{1,3}[,\.]\d{2})', texto)
            numeros_float = [self._convertir_importe(n) for n in numeros]
            validos = [n for n in numeros_float if 3 < n < 150]
        
        if not validos:
            return None
        
        # El total es típicamente el número que más se repite
        conteo = Counter(validos)
        mas_comun = conteo.most_common(1)[0]
        
        # Solo devolver si tiene suficiente confianza (aparece 2+ veces)
        if mas_comun[1] >= 2:
            return mas_comun[0]
        
        # Si no hay repeticiones, devolver el máximo
        return max(validos)
    
    def extraer_total_con_confianza(self, pdf_path: str) -> Tuple[Optional[float], float]:
        """
        Extrae el total con un índice de confianza.
        
        Returns:
            Tuple de (total, confianza) donde confianza es 0.0-1.0
        """
        if not OCR_DISPONIBLE:
            return None, 0.0
        
        try:
            images = convert_from_path(pdf_path, dpi=350)
        except Exception:
            return None, 0.0
        
        candidatos = []
        
        # Probar múltiples configuraciones
        for contraste in [2.0, 2.5, 3.0]:
            img_proc = self._preprocesar_imagen(images[0], contraste)
            for psm in [3, 4]:
                config = f'--oem 3 --psm {psm}'
                try:
                    texto = pytesseract.image_to_string(img_proc, config=config)
                    numeros = re.findall(r'(\d{1,3}[,\.]\d{2})\s*€', texto)
                    for n in numeros:
                        val = self._convertir_importe(n)
                        if 3 < val < 150:
                            candidatos.append(val)
                except:
                    pass
        
        if not candidatos:
            return None, 0.0
        
        conteo = Counter(candidatos)
        mas_comun = conteo.most_common(1)[0]
        confianza = min(mas_comun[1] / 4, 1.0)  # 100% con 4+ repeticiones
        
        return mas_comun[0], confianza
    
    def extraer_referencia(self, texto: str) -> Optional[str]:
        """Extrae número de factura."""
        # Formato: "FACTURA N°... 76405" o "FACTURA NRO... 68929"
        m = re.search(r'FACTURA\s*N[°ºO]?\.{0,3}\s*(\d{4,6})', texto, re.IGNORECASE)
        if m:
            return m.group(1)
        return None
    
    def extraer_fecha(self, texto: str) -> Optional[str]:
        """Extrae fecha de la factura."""
        # Formato: "Madrid, 5 de diciembre de 2025"
        meses = {
            'enero': '01', 'febrero': '02', 'marzo': '03', 'abril': '04',
            'mayo': '05', 'junio': '06', 'julio': '07', 'agosto': '08',
            'septiembre': '09', 'octubre': '10', 'noviembre': '11', 'diciembre': '12'
        }
        
        m = re.search(r'(\d{1,2})\s+de\s+(\w+)\s+de\s+(\d{4})', texto, re.IGNORECASE)
        if m:
            dia = m.group(1).zfill(2)
            mes_nombre = m.group(2).lower()
            anio = m.group(3)
            mes = meses.get(mes_nombre, '01')
            return f"{dia}/{mes}/{anio}"
        
        return None
    
    def extraer_lineas(self, texto: str) -> List[Dict]:
        """
        Intenta extraer líneas de productos.
        
        NOTA: La extracción de líneas individuales es muy poco fiable
        con OCR. Se recomienda usar solo el total.
        """
        lineas = []
        
        # Buscar patrones de líneas: CANTIDAD DESCRIPCION IMPORTE TOTAL
        # Ej: "2 MANO PAPEL CRISTAL 7,50 € 15,00 €"
        patron = re.compile(
            r'^(\d{1,2})\s+'                          # Cantidad
            r'([A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ\s\d]+?)\s+'      # Descripción
            r'(\d+[,\.]\d{2})\s*€?\s+'                 # Precio unitario
            r'(\d+[,\.]\d{2})\s*€?',                   # Total
            re.MULTILINE
        )
        
        for m in patron.finditer(texto):
            cantidad, descripcion, precio, total = m.groups()
            lineas.append({
                'codigo': '',
                'articulo': descripcion.strip()[:50],
                'cantidad': int(cantidad),
                'precio_ud': self._convertir_importe(precio),
                'iva': 21,
                'base': self._convertir_importe(total),
                'categoria': self.categoria_fija
            })
        
        return lineas
    
    def extraer_cuadro_fiscal(self, texto: str) -> List[Dict]:
        """Extrae cuadro fiscal (IVA 21%)."""
        cuadros = []
        
        # Buscar BASE IMPONIBLE e IVA
        base = re.search(r'BASE\s*IMPONIBLE[:\s]*([\d,.]+)', texto, re.IGNORECASE)
        iva = re.search(r'IVA\s*21\s*%?[:\s]*([\d,.]+)', texto, re.IGNORECASE)
        
        if base:
            base_val = self._convertir_importe(base.group(1))
            cuota_val = self._convertir_importe(iva.group(1)) if iva else base_val * 0.21
            cuadros.append({
                'iva': 21,
                'base': base_val,
                'cuota': round(cuota_val, 2)
            })
        
        return cuadros
    
    def requiere_revision_manual(self) -> bool:
        """
        Indica si este extractor típicamente requiere revisión manual.
        
        Para TIRSO, la respuesta es SÍ debido a la baja tasa de OCR.
        """
        return True
