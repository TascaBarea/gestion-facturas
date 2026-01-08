# -*- coding: utf-8 -*-
"""
Extractor para EMBUTIDOS FERRIOL, S.L.

Embutidos mallorquines de Sineu (Mallorca)
CIF: B57955098
IBAN: REDACTED_IBAN

Formato factura:
CANT COD DESCRIPCION PRECIO_UD TOTAL LOTE
3,6 07 KG CAMAYOT 12,40 44,64 06
-1,1 07 KG CAMAYOT ABONO POR LISTERIA 13,00 -14,30 06

IVA: 10% (productos alimenticios)
Categoria fija: CHACINAS

Sistema dual: pdfplumber + OCR para facturas escaneadas

VERSIÓN: v5.16 - 07/01/2026
- FIX: Patrón mejorado para precio con espacio (13, 90)
- FIX: Lote con = además de - (28=32 vs 28-32)
- FIX: Extracción de fecha y número de factura
- FIX: Total con símbolo € corrupto en OCR

Creado: 04/01/2026
Actualizado: 07/01/2026
"""
from extractores.base import ExtractorBase
from extractores import registrar
from typing import List, Dict, Optional
import re
import pdfplumber


@registrar('EMBUTIDOS FERRIOL', 'FERRIOL', 'EMBOTITS FERRIOL', 
           'EMBUTIDOS FERRIOL SL', 'EMBUTIDOS FERRIOL S.L.')
class ExtractorEmbutidosFerriol(ExtractorBase):
    """Extractor para facturas de EMBUTIDOS FERRIOL."""
    
    nombre = 'EMBUTIDOS FERRIOL'
    cif = 'B57955098'
    iban = 'REDACTED_IBAN'
    metodo_pdf = 'pdfplumber'
    categoria_fija = 'CHACINAS'
    
    def extraer_texto(self, pdf_path: str) -> str:
        """
        Extrae texto del PDF.
        Intenta pdfplumber primero, si falla usa OCR.
        """
        texto = self._extraer_pdfplumber(pdf_path)
        
        # Si no hay texto suficiente, intentar OCR
        if len(texto.strip()) < 100:
            texto_ocr = self._extraer_ocr(pdf_path)
            if len(texto_ocr) > len(texto):
                return texto_ocr
        
        return texto
    
    def _extraer_pdfplumber(self, pdf_path: str) -> str:
        """Extrae texto con pdfplumber."""
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
    
    def _extraer_ocr(self, pdf_path: str) -> str:
        """Extrae texto con OCR (pytesseract)."""
        try:
            from pdf2image import convert_from_path
            import pytesseract
            
            # Convertir PDF a imagenes
            images = convert_from_path(pdf_path, dpi=300)
            
            texto_completo = []
            for img in images:
                # Usar inglés si español no está disponible
                try:
                    texto = pytesseract.image_to_string(
                        img, 
                        lang='spa',
                        config='--psm 6'
                    )
                except:
                    texto = pytesseract.image_to_string(
                        img, 
                        lang='eng',
                        config='--psm 6'
                    )
                if texto:
                    texto_completo.append(texto)
            
            return '\n'.join(texto_completo)
        except ImportError:
            return ''
        except Exception as e:
            return ''
    
    def extraer_lineas(self, texto: str) -> List[Dict]:
        """
        Extrae lineas de productos.
        
        Formato:
        CANT COD DESCRIPCION PRECIO_UD TOTAL LOTE
        3,6 07 KG CAMAYOT 12,40 44,64 06
        -1,1 07 KG CAMAYOT ABONO POR LISTERIA 13,00 -14,30 06
        """
        lineas = []
        
        # Patrón mejorado para líneas de producto (incluye negativos para abonos)
        # - Precio puede tener espacio por OCR: "13, 90"
        # - Lote puede usar = en vez de - por OCR: "28=32" vs "28-32"
        patron = re.compile(
            r'^\s*(-?\d+,\d)\s+'           # Cantidad (puede ser negativa)
            r'(\d{2})\s+'                   # Codigo (2 digitos)
            r'(.+?)\s+'                     # Descripcion
            r'(\d+,\s?\d{2})\s+'            # Precio unitario (puede tener espacio)
            r'(-?\d+,\d{2})\s+'             # Total (puede ser negativo)
            r'(\d+(?:[-=]\d+)?)\s*$'        # Lote (puede ser rango con - o =)
        , re.MULTILINE)
        
        for match in patron.finditer(texto):
            cantidad = self._convertir_europeo(match.group(1))
            codigo = match.group(2)
            descripcion = match.group(3).strip()
            precio_str = match.group(4).replace(' ', '')  # Quitar espacio si existe
            precio = self._convertir_europeo(precio_str)
            total = self._convertir_europeo(match.group(5))
            
            # Limpiar descripcion - quitar "KG " al inicio si existe
            if descripcion.upper().startswith('KG '):
                descripcion = descripcion[3:]
            
            # Filtrar cabeceras (buscar palabras completas, no subcadenas)
            palabras = descripcion.upper().split()
            if any(x in palabras for x in ['CANT', 'COD', 'DESCRIPCION', 'PRECIO', 'PRECIO_UD']):
                continue
            
            lineas.append({
                'codigo': codigo,
                'articulo': descripcion[:50],
                'cantidad': round(cantidad, 1),
                'precio_ud': round(precio, 2),
                'iva': 10,
                'base': round(total, 2),
                'categoria': self.categoria_fija
            })
        
        return lineas
    
    def _convertir_europeo(self, texto: str) -> float:
        """Convierte formato europeo (1.234,56) a float."""
        if not texto:
            return 0.0
        texto = str(texto).strip()
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
        # Formato: TOTAL FACT seguido de importe
        # El € puede aparecer como €, como caracter corrupto, o al final de línea
        patrones = [
            r'TOTAL\s+FACT\s*\n?\s*.*?(\d+,\d{2})\s*€',
            r'TOTAL\s+FACT\s*\n?\s*(\d+,\d{2})',
            r'(\d+,\d{2})\s*€\s*$',
        ]
        
        for patron in patrones:
            match = re.search(patron, texto, re.IGNORECASE | re.MULTILINE)
            if match:
                return self._convertir_europeo(match.group(1))
        
        return None
    
    def extraer_fecha(self, texto: str) -> Optional[str]:
        """Extrae fecha de la factura."""
        # Formato: NN/NNNN DD/MM/YY (número factura seguido de fecha)
        patron = re.search(r'\d{2}/\d{4}\s+(\d{2}/\d{2}/\d{2})', texto)
        if patron:
            fecha = patron.group(1)
            # Convertir YY a YYYY
            partes = fecha.split('/')
            if len(partes) == 3 and len(partes[2]) == 2:
                partes[2] = '20' + partes[2]
            return '/'.join(partes)
        
        # Alternativa: buscar fecha después de "Fecha"
        patron2 = re.search(r'Fecha\s+(\d{2}/\d{2}/\d{2})', texto)
        if patron2:
            fecha = patron2.group(1)
            partes = fecha.split('/')
            if len(partes[2]) == 2:
                partes[2] = '20' + partes[2]
            return '/'.join(partes)
        
        return None
    
    def extraer_numero_factura(self, texto: str) -> Optional[str]:
        """Extrae numero de factura."""
        # Formato: YY/NNNN (antes de la fecha)
        patron = re.search(r'(\d{2}/\d{4})\s+\d{2}/\d{2}/\d{2}', texto)
        if patron:
            return patron.group(1)
        
        # Alternativa: buscar después de "Factura"
        patron2 = re.search(r'Factura\s*\n?\s*(\d{2}/\d{4})', texto, re.IGNORECASE)
        if patron2:
            return patron2.group(1)
        
        return None
