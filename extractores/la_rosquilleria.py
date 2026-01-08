# -*- coding: utf-8 -*-
"""
Extractor para LA ROSQUILLERIA S.L.U. (El Torro)

Rosquillas marineras artesanales de Santomera (Murcia)
CIF: B73814949

ESTRATEGIA SIMPLIFICADA:
- Extraer TOTAL del PDF
- Determinar IVA segun fecha (10% antes 2025, 4% desde 2025)
- BASE = TOTAL / (1 + IVA/100)
- Articulo fijo: ROSQUILLAS MURCIANAS
- Categoria fija: ROSQUILLAS MARINERAS
- Los portes estan incluidos en el total (NO se extraen aparte)

Creado: 04/01/2026
"""
from extractores.base import ExtractorBase
from extractores import registrar
from typing import List, Dict, Optional
import re
import pdfplumber

# OCR imports
try:
    from pdf2image import convert_from_path
    import pytesseract
    OCR_DISPONIBLE = True
except ImportError:
    OCR_DISPONIBLE = False


@registrar('LA ROSQUILLERIA', 'ROSQUILLERIA', 'EL TORRO', 'ROSQUILLAS EL TORRO')
class ExtractorLaRosquilleria(ExtractorBase):
    """Extractor para facturas de LA ROSQUILLERIA."""
    
    nombre = 'LA ROSQUILLERIA'
    cif = 'B73814949'
    iban = ''
    metodo_pdf = 'pdfplumber'
    categoria_fija = 'ROSQUILLAS MARINERAS'
    
    def extraer_texto(self, pdf_path: str) -> str:
        """Extrae texto del PDF. Usa OCR si es imagen escaneada."""
        try:
            # Intentar pdfplumber primero
            texto_completo = []
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    texto = page.extract_text()
                    if texto:
                        texto_completo.append(texto)
            
            resultado = '\n'.join(texto_completo)
            
            # Si no hay texto y OCR disponible, usar OCR
            if not resultado.strip() and OCR_DISPONIBLE:
                resultado = self._extraer_con_ocr(pdf_path)
            
            return resultado
        except Exception as e:
            print(f"[LA ROSQUILLERIA] Error extrayendo texto: {e}")
            return ''
    
    def _extraer_con_ocr(self, pdf_path: str) -> str:
        """Extrae texto usando OCR (Tesseract)."""
        try:
            imagenes = convert_from_path(pdf_path, dpi=300)
            textos = []
            for img in imagenes:
                try:
                    texto = pytesseract.image_to_string(img, lang='spa')
                except:
                    texto = pytesseract.image_to_string(img, lang='eng')
                textos.append(texto)
            return '\n'.join(textos)
        except Exception as e:
            print(f"[LA ROSQUILLERIA] Error OCR: {e}")
            return ''
    
    def _convertir_importe(self, texto: str) -> float:
        """Convierte texto a float (formato europeo)."""
        if not texto:
            return 0.0
        texto = str(texto).strip().replace(' ', '').replace('\u20ac', '').replace('€', '')
        if '.' in texto and ',' in texto:
            texto = texto.replace('.', '').replace(',', '.')
        elif ',' in texto:
            texto = texto.replace(',', '.')
        try:
            return float(texto)
        except:
            return 0.0
    
    def _extraer_ano_factura(self, texto: str) -> int:
        """Extrae el ano de la factura para determinar IVA."""
        # Buscar fecha en formato DD/MM/YYYY
        m = re.search(r'(\d{2})/(\d{2})/(\d{4})', texto)
        if m:
            return int(m.group(3))
        return 2025  # Default
    
    def _determinar_iva(self, texto: str) -> int:
        """Determina el tipo de IVA segun la fecha."""
        ano = self._extraer_ano_factura(texto)
        if ano < 2025:
            return 10  # IVA 10% antes de 2025
        else:
            return 4   # IVA 4% desde 2025
    
    def extraer_lineas(self, texto: str) -> List[Dict]:
        """
        Extrae una unica linea con el total de la factura.
        BASE = TOTAL / (1 + IVA/100)
        """
        lineas = []
        
        total = self.extraer_total(texto)
        if not total or total <= 0:
            return []
        
        iva = self._determinar_iva(texto)
        base = round(total / (1 + iva / 100), 2)
        
        lineas.append({
            'articulo': 'ROSQUILLAS MURCIANAS',
            'cantidad': 1,
            'precio_ud': base,
            'iva': iva,
            'base': base,
            'categoria': 'ROSQUILLAS MARINERAS'
        })
        
        return lineas
    
    def extraer_total(self, texto: str) -> Optional[float]:
        """Extrae el TOTAL de la factura."""
        # Patron: TOTAL: XX,XX o TOTAL: XX,XX €
        m = re.search(r'TOTAL:\s*([\d.,]+)\s*', texto, re.IGNORECASE)
        if m:
            return self._convertir_importe(m.group(1))
        return None
    
    def extraer_fecha(self, texto: str) -> Optional[str]:
        """Extrae fecha de la factura (formato DD/MM/YYYY)."""
        m = re.search(r'(\d{2}/\d{2}/\d{4})', texto)
        if m:
            return m.group(1)
        return None
    
    def extraer_numero_factura(self, texto: str) -> Optional[str]:
        """Extrae numero de factura."""
        # Formato: Numero XXXXXXX en la cabecera
        m = re.search(r'N[uú]mero\s+(\d+)', texto)
        if m:
            return m.group(1)
        return None
    
    # Alias
    extraer_referencia = extraer_numero_factura
