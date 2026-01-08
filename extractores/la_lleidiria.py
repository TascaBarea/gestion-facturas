# -*- coding: utf-8 -*-
"""
Extractor para LA LLEIDIRIA, S.L.

Quesería artesanal de Cantabria
CIF: B42953455
IBAN: ES93 0049 5975 6927 1601 8322

Formato factura tabla:
DESCRIPCIÓN    CANTIDAD    FORMATO    PRECIO    IMPUESTO    SUBTOTAL
Lolo - Lolo      2.845       KG      19.00€/KG    4.00       54.06€
Coste de entrega   -          -          -        21.00       0.00€

Productos: Lolo, Origen, Siso, Carmina, Siso en Cernaa (todos quesos)

IVA: 4% (quesos)
Categoria fija: QUESOS

NOTA: El coste de entrega (cuando > 0) se reparte proporcionalmente
entre los articulos, sumandolo a su base.

Creado: 04/01/2026
Corregido: 04/01/2026 - Codificación UTF-8
"""
from extractores.base import ExtractorBase
from extractores import registrar
from typing import List, Dict, Optional
import re
import pdfplumber


@registrar('LA LLEIDIRIA', 'LA LLELDIRIA', 'LLEIDIRIA', 'LLELDIRIA',
           'LA LLILDIRIA', 'LLILDIRIA')
class ExtractorLaLleidiria(ExtractorBase):
    """Extractor para facturas de LA LLEIDIRIA."""
    
    nombre = 'LA LLEIDIRIA'
    cif = 'B42953455'
    iban = 'ES93 0049 5975 6927 1601 8322'
    metodo_pdf = 'pdfplumber'
    categoria_fija = 'QUESOS'
    
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
                texto = pytesseract.image_to_string(
                    img, 
                    lang='spa',
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
        Extrae lineas de productos (quesos).
        
        Formato OCR:
        Lolo - Lolo 2.845 KG 19.00 €/KG 54.06 €
        Coste de entrega (se ignora, ya incluido o 0)
        """
        lineas = []
        coste_entrega = 0.0
        
        # Buscar coste de entrega (para futuro uso)
        patron_entrega = re.search(
            r'Coste\s+de\s+entrega.*?(\d+[\.,]\d+)\s*(?:€|EUR)',
            texto, re.IGNORECASE
        )
        if patron_entrega:
            coste_entrega = self._convertir_numero(patron_entrega.group(1))
        
        # Patron para productos: Nombre - Nombre CANTIDAD KG PRECIO €/KG SUBTOTAL €
        # Acepta tanto € como sin símbolo
        patron_producto = re.compile(
            r'([A-Za-z]+)\s*-\s*([A-Za-z][A-Za-z\s]*?)\s+'
            r'(\d+[\.,]\d+)\s*KG\s+'
            r'(\d+[\.,]\d+)\s*(?:€|EUR)?/?KG\s+'
            r'(\d+[\.,]\d+)\s*(?:€|EUR)?'
        , re.IGNORECASE)
        
        productos_temp = []
        for match in patron_producto.finditer(texto):
            nombre = match.group(2).strip()
            cantidad = self._convertir_numero(match.group(3))
            precio = self._convertir_numero(match.group(4))
            subtotal = self._convertir_numero(match.group(5))
            
            if subtotal > 0:
                productos_temp.append({
                    'nombre': nombre,
                    'cantidad': cantidad,
                    'precio': precio,
                    'subtotal': subtotal
                })
        
        # Calcular suma total para proporcionalidad
        suma_subtotales = sum(p['subtotal'] for p in productos_temp)
        
        # Repartir coste de entrega proporcionalmente (cuando > 0)
        for prod in productos_temp:
            base = prod['subtotal']
            
            if coste_entrega > 0 and suma_subtotales > 0:
                proporcion = prod['subtotal'] / suma_subtotales
                # Transporte viene con IVA 21%, quitarlo antes de sumar
                transporte_sin_iva = coste_entrega / 1.21
                base += transporte_sin_iva * proporcion
            
            lineas.append({
                'codigo': '',
                'articulo': prod['nombre'][:50],
                'cantidad': round(prod['cantidad'], 3),
                'precio_ud': round(prod['precio'], 2),
                'iva': 4,
                'base': round(base, 2),
                'categoria': self.categoria_fija
            })
        
        return lineas
    
    def _convertir_numero(self, texto: str) -> float:
        """Convierte texto a float."""
        if not texto:
            return 0.0
        texto = str(texto).strip()
        texto = texto.replace('€', '').replace('EUR', '').replace(',', '.').strip()
        try:
            return float(texto)
        except:
            return 0.0
    
    def extraer_total(self, texto: str) -> Optional[float]:
        """Extrae total de la factura."""
        # Formato tabla: TOTAL seguido de importe
        patron = re.search(r'TOTAL\s+(\d+[\.,]\d+)\s*(?:€|EUR)?', texto)
        if patron:
            return self._convertir_numero(patron.group(1))
        
        return None
    
    def extraer_fecha(self, texto: str) -> Optional[str]:
        """Extrae fecha de la factura."""
        # Formato: FECHA EMISIÓN seguido de DD/MM/YYYY
        patron = re.search(r'FECHA\s+EMISI[OÓ]N\s+(\d{2}/\d{2}/\d{4})', texto, re.IGNORECASE)
        if patron:
            return patron.group(1)
        
        # Alternativa en tabla
        patron2 = re.search(r'(\d{2}/\d{2}/\d{4})', texto)
        if patron2:
            return patron2.group(1)
        
        return None
    
    def extraer_numero_factura(self, texto: str) -> Optional[str]:
        """Extrae numero de factura."""
        # Formato: Nº FACTURA seguido de LLNNN
        patron = re.search(r'N[º°o]\s*FACTURA\s+([A-Z]+\d+)', texto, re.IGNORECASE)
        if patron:
            return patron.group(1)
        
        # Alternativa: LL seguido de numeros
        patron2 = re.search(r'\b(LL\d+)\b', texto)
        if patron2:
            return patron2.group(1)
        
        return None
