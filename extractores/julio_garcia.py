# -*- coding: utf-8 -*-
"""
Extractor para JULIO GARCIA VIVAS (Ay Madre!)

Verdulería del Mercado de San Fernando (Embajadores).
NIF: REDACTED_DNI

ESTRATEGIA HÍBRIDA:
1. Intentar pdfplumber primero (más rápido y preciso)
2. Si no hay texto suficiente → usar OCR como fallback

Formato factura (pdfplumber):
- Línea 0: Número factura (8 dígitos)
- Línea 1: Fecha (DD/MM/YYYY)
- Últimas líneas: BASE, IVA, "BASE IVA 0,00 0,00", TOTAL

Formato factura (OCR):
BASE IMPONIBLE    I.V.A.    R.E.
36,72    4%    1,47    0,5%    0,00
0,59    10%   0,06    1,4%    0,00

ARTÍCULOS Y CATEGORÍAS:
- IVA 4%:  "Verduras Ay Madre al 4"   → GENERICO PARA VERDURAS
- IVA 10%: "Compras Ay Madre al 10"   → GENERICO PARA COMIDA
- IVA 21%: "Compras Ay Madre al 21"   → GENERICO PARA COMIDA

Creado: 26/12/2025
Actualizado: 07/01/2026 - Estrategia híbrida pdfplumber/OCR, nombres correctos
"""
from extractores.base import ExtractorBase
from extractores import registrar
from typing import List, Dict, Optional
import re
import pdfplumber

# Intentar importar dependencias OCR
try:
    import pytesseract
    from pdf2image import convert_from_path
    OCR_DISPONIBLE = True
except ImportError:
    OCR_DISPONIBLE = False


@registrar('JULIO GARCIA VIVAS', 'GARCIA VIVAS JULIO', 'JULIO GARCIA', 'AY MADRE')
class ExtractorJulioGarcia(ExtractorBase):
    """Extractor para facturas de JULIO GARCIA VIVAS."""
    
    nombre = 'JULIO GARCIA VIVAS'
    cif = 'REDACTED_DNI'
    iban = ''
    metodo_pdf = 'pdfplumber'  # Primario, con fallback a OCR
    
    # Configuración de artículos y categorías por tipo de IVA
    CONFIG_IVA = {
        4:  {'articulo': 'Verduras Ay Madre al 4',  'categoria': 'GENERICO PARA VERDURAS'},
        10: {'articulo': 'Compras Ay Madre al 10',  'categoria': 'GENERICO PARA COMIDA'},
        21: {'articulo': 'Compras Ay Madre al 21',  'categoria': 'GENERICO PARA COMIDA'},
    }
    
    def __init__(self):
        super().__init__()
        self._texto = None
        self._usa_ocr = False
    
    def _convertir_europeo(self, texto: str) -> float:
        """Convierte formato europeo a float."""
        if not texto:
            return 0.0
        texto = str(texto).strip()
        texto = texto.replace('€', '').replace(' ', '')
        if '.' in texto and ',' in texto:
            texto = texto.replace('.', '').replace(',', '.')
        elif ',' in texto:
            texto = texto.replace(',', '.')
        try:
            return float(texto)
        except:
            return 0.0
    
    def _extraer_texto_pdfplumber(self, pdf_path: str) -> str:
        """Extrae texto usando pdfplumber."""
        try:
            with pdfplumber.open(pdf_path) as pdf:
                texto = pdf.pages[0].extract_text() or ''
                return texto
        except:
            return ''
    
    def _extraer_texto_ocr(self, pdf_path: str) -> str:
        """Extrae texto usando OCR (Tesseract)."""
        if not OCR_DISPONIBLE:
            return ""
        
        try:
            images = convert_from_path(pdf_path, dpi=300)
            texto = ""
            for img in images:
                try:
                    texto += pytesseract.image_to_string(img, lang='spa')
                except:
                    texto += pytesseract.image_to_string(img)
            return texto
        except Exception as e:
            print(f"Error OCR JULIO GARCIA: {e}")
            return ""
    
    def extraer_texto(self, pdf_path: str) -> str:
        """Extrae texto del PDF, usando pdfplumber o OCR según necesidad."""
        # Intentar pdfplumber primero
        texto = self._extraer_texto_pdfplumber(pdf_path)
        
        # Si no hay texto suficiente, usar OCR
        if len(texto.strip()) < 100:
            texto = self._extraer_texto_ocr(pdf_path)
            self._usa_ocr = True
        else:
            self._usa_ocr = False
        
        self._texto = texto
        return texto
    
    def extraer_numero_factura(self, texto: str) -> Optional[str]:
        """
        Extrae número de factura.
        
        Formato pdfplumber: Primera línea es el número (8 dígitos)
        Formato OCR: FACTURA Nº 28649541
        """
        if not texto:
            return None
        
        lineas = texto.strip().split('\n')
        
        # Formato pdfplumber: primera línea es número de 8 dígitos
        if lineas and re.match(r'^\d{8}$', lineas[0].strip()):
            return lineas[0].strip()
        
        # Formato OCR: FACTURA Nº XXXXXXXX
        match = re.search(r'FACTURA\s*N[°ºo]?\s*(\d{8})', texto, re.IGNORECASE)
        if match:
            return match.group(1)
        
        # Buscar cualquier número de 8 dígitos al principio
        match = re.search(r'^(\d{8})\s*$', texto, re.MULTILINE)
        if match:
            return match.group(1)
        
        return None
    
    def extraer_fecha(self, texto: str) -> Optional[str]:
        """Extrae fecha de la factura."""
        if not texto:
            return None
        
        lineas = texto.strip().split('\n')
        
        # Formato pdfplumber: segunda línea es la fecha
        if len(lineas) > 1:
            match = re.match(r'^(\d{2}/\d{2}/\d{4})$', lineas[1].strip())
            if match:
                return match.group(1)
        
        # Formato OCR: FECHA: DD/MM/YYYY
        match = re.search(r'FECHA[:\s]+(\d{2}/\d{2}/\d{4})', texto, re.IGNORECASE)
        if match:
            return match.group(1)
        
        # Buscar cualquier fecha DD/MM/YYYY
        match = re.search(r'(\d{2}/\d{2}/\d{4})', texto)
        if match:
            return match.group(1)
        
        return None
    
    def extraer_lineas(self, texto: str) -> List[Dict]:
        """
        Extrae líneas de producto desde el cuadro fiscal.
        
        Estrategia:
        1. Si viene de pdfplumber: calcular IVA por ratio
        2. Si viene de OCR: buscar patrón "BASE X% CUOTA"
        """
        if not texto:
            return []
        
        # Detectar si es OCR por presencia de patrones típicos
        es_ocr = bool(re.search(r'\d+[,\.]\d+\s+\d+%\s+\d+[,\.]\d+', texto))
        
        if es_ocr:
            return self._extraer_lineas_ocr(texto)
        else:
            return self._extraer_lineas_pdfplumber(texto)
    
    def _extraer_lineas_pdfplumber(self, texto: str) -> List[Dict]:
        """
        Extrae líneas cuando el texto viene de pdfplumber.
        
        Formato últimas líneas:
        BASE_TOTAL
        IVA_TOTAL
        BASE IVA 0,00 0,00
        TOTAL_FACTURA
        
        Calcula el tipo de IVA por ratio.
        """
        lineas_resultado = []
        lineas = texto.strip().split('\n')
        
        # Buscar línea con formato "BASE IVA 0,00 0,00"
        base_total = 0
        iva_total = 0
        
        for i, linea in enumerate(lineas):
            partes = linea.strip().split()
            if len(partes) == 4:
                try:
                    b = self._convertir_europeo(partes[0])
                    iv = self._convertir_europeo(partes[1])
                    # Verificar que los otros dos son 0,00 (R.E.)
                    if b > 0 and iv > 0:
                        base_total = b
                        iva_total = iv
                        break
                except:
                    pass
        
        if base_total <= 0:
            return []
        
        # Calcular ratio para determinar tipo de IVA
        ratio = (iva_total / base_total) * 100 if base_total > 0 else 0
        
        # Determinar tipo de IVA por ratio
        if ratio < 6:
            tipo_iva = 4
        elif ratio < 15:
            tipo_iva = 10
        else:
            tipo_iva = 21
        
        config = self.CONFIG_IVA.get(tipo_iva, self.CONFIG_IVA[4])
        
        lineas_resultado.append({
            'codigo': '',
            'articulo': config['articulo'],
            'cantidad': 1,
            'precio_ud': round(base_total, 2),
            'iva': tipo_iva,
            'base': round(base_total, 2),
            'categoria': config['categoria']
        })
        
        return lineas_resultado
    
    def _extraer_lineas_ocr(self, texto: str) -> List[Dict]:
        """
        Extrae líneas cuando el texto viene de OCR.
        
        Busca patrones: BASE X% CUOTA
        Ej: "36,72 4% 1,47" o "0,59 10% 0,06"
        """
        lineas_resultado = []
        
        # Patrón: número base + porcentaje + número cuota
        patron = re.compile(
            r'(\d+[,\.]\d{2})\s+(\d{1,2})%\s+(\d+[,\.]\d{2})',
            re.MULTILINE
        )
        
        for match in patron.finditer(texto):
            base = self._convertir_europeo(match.group(1))
            tipo_iva = int(match.group(2))
            
            # Validar tipo de IVA
            if tipo_iva not in [4, 10, 21]:
                continue
            
            if base <= 0:
                continue
            
            config = self.CONFIG_IVA.get(tipo_iva, self.CONFIG_IVA[4])
            
            lineas_resultado.append({
                'codigo': '',
                'articulo': config['articulo'],
                'cantidad': 1,
                'precio_ud': round(base, 2),
                'iva': tipo_iva,
                'base': round(base, 2),
                'categoria': config['categoria']
            })
        
        # Si no encontramos nada, intentar con TOTAL BASE IMPONIBLE
        if not lineas_resultado:
            match = re.search(
                r'TOTAL\s*BASE\s*IMPONIBLE\s*(\d+[,\.]\d{2})',
                texto, re.IGNORECASE
            )
            if match:
                base = self._convertir_europeo(match.group(1))
                if base > 0:
                    config = self.CONFIG_IVA[4]  # Por defecto verduras
                    lineas_resultado.append({
                        'codigo': '',
                        'articulo': config['articulo'],
                        'cantidad': 1,
                        'precio_ud': round(base, 2),
                        'iva': 4,
                        'base': round(base, 2),
                        'categoria': config['categoria']
                    })
        
        return lineas_resultado
    
    def extraer_total(self, texto: str) -> Optional[float]:
        """Extrae total de la factura."""
        if not texto:
            return None
        
        lineas = texto.strip().split('\n')
        
        # Formato pdfplumber: última línea es el total
        if lineas:
            ultimo = lineas[-1].strip()
            if re.match(r'^\d+[,\.]\d{2}$', ultimo):
                return self._convertir_europeo(ultimo)
        
        # Formato OCR: TOTAL FACTURA XX,XX
        patrones = [
            r'TOTAL\s*FACTURA\s*(\d+[,\.]\d{2})',
            r'TOTAL[:\s]+(\d+[,\.]\d{2})\s*$',
        ]
        
        for patron in patrones:
            match = re.search(patron, texto, re.IGNORECASE | re.MULTILINE)
            if match:
                return self._convertir_europeo(match.group(1))
        
        return None
