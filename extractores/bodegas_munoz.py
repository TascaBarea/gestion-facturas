"""
Extractor para BODEGAS MUÑOZ MARTIN C.B.

Bodega de Navalcarnero (Madrid).
CIF: E83182683
IBAN: REDACTED_IBAN

Productos principales:
- R CAJA 6 BOT. VIÑA JESUSA TINTO -> VINO TEMPRANILLO
- PORTES -> TRANSPORTE

IVA: 21%

Formato factura:
Codigo Descripcion Cant. Precio Dto. Importe
076 R CAJA 6 BOT. VIÑA JESUSA TINTO 8 12,40 99,20 €
093 PORTES 1 13,06 13,06 €

NOTA: Algunas facturas son escaneadas y requieren OCR con Tesseract.
El OCR extrae en columnas separadas, por lo que se usa un patron alternativo.

Creado: 30/12/2025
"""
from extractores.base import ExtractorBase
from extractores import registrar
from typing import List, Dict, Optional
import re
import subprocess
import tempfile
import os


@registrar('BODEGAS MUÑOZ MARTIN', 'BODEGAS MUÑOZ', 'MUÑOZ MARTIN', 'BODEGA MUÑOZ')
class ExtractorBodegasMunoz(ExtractorBase):
    """Extractor para facturas de BODEGAS MUÑOZ MARTIN."""
    
    nombre = 'BODEGAS MUÑOZ MARTIN'
    cif = 'E83182683'
    iban = 'REDACTED_IBAN'
    metodo_pdf = 'pdfplumber'  # Primero intenta pdfplumber, luego OCR si falla
    
    def extraer_lineas(self, texto: str) -> List[Dict]:
        """
        Extrae lineas de productos.
        Intenta primero el formato normal, si no encuentra lineas usa formato OCR.
        """
        # Intentar formato normal (pdfplumber)
        lineas = self._extraer_lineas_normal(texto)
        
        # Si no hay lineas, intentar formato OCR
        if not lineas:
            lineas = self._extraer_lineas_ocr(texto)
        
        return lineas
    
    def _extraer_lineas_normal(self, texto: str) -> List[Dict]:
        """
        Extrae lineas en formato normal (pdfplumber).
        
        Formato:
        076 R CAJA 6 BOT. VIÑA JESUSA TINTO 8 12,40 99,20 €
        093 PORTES 1 13,06 13,06 €
        """
        lineas = []
        
        # Patron: CODIGO DESCRIPCION CANTIDAD PRECIO IMPORTE
        patron = re.compile(
            r'(\d{3})\s+'                           # Codigo (076, 093)
            r'(.+?)\s+'                              # Descripcion
            r'(\d+)\s+'                              # Cantidad
            r'([\d,\.]+)\s+'                         # Precio
            r'([\d,\.]+)\s*€?'                       # Importe
        )
        
        for linea in texto.split('\n'):
            m = patron.search(linea)
            if m:
                codigo = m.group(1)
                descripcion = m.group(2).strip()
                cantidad = int(m.group(3))
                precio = self._convertir_europeo(m.group(4))
                importe = self._convertir_europeo(m.group(5))
                
                # Ignorar lineas de cabecera
                if any(x in descripcion.upper() for x in ['DESCRIPCION', 'CODIGO', 'CANT.']):
                    continue
                
                categoria = self._determinar_categoria(descripcion)
                
                if importe > 0:
                    lineas.append({
                        'codigo': codigo,
                        'articulo': descripcion[:50],
                        'cantidad': cantidad,
                        'precio_ud': round(precio, 2),
                        'iva': 21,
                        'base': round(importe, 2),
                        'categoria': categoria
                    })
        
        return lineas
    
    def _extraer_lineas_ocr(self, texto: str) -> List[Dict]:
        """
        Extrae lineas en formato OCR (columnas separadas).
        
        El OCR de Tesseract extrae las columnas separadas:
        - "12,40 74,38 €" (precio importe)
        - "7,85 7,85 €" (precio importe - cuando son iguales es PORTES)
        
        FILTROS para evitar capturar el cuadro fiscal:
        - Importe entre 5€ y 200€
        - Importe != 21 (% IVA)
        - Precio <= importe (evita base imponible)
        """
        lineas = []
        
        # Patron para lineas de importe: "PRECIO IMPORTE €"
        patron_importe = re.compile(r'^([\d,\.]+)\s+([\d,\.]+)\s*€?\s*$')
        
        for linea in texto.split('\n'):
            m = patron_importe.match(linea.strip())
            if m:
                precio = self._convertir_europeo(m.group(1))
                importe = self._convertir_europeo(m.group(2))
                
                # FILTROS para evitar cuadro fiscal:
                # 1. Importe muy pequeño o muy grande
                if importe < 5 or importe > 200:
                    continue
                
                # 2. Segundo numero es 21 (probablemente % IVA)
                if abs(importe - 21) < 0.5:
                    continue
                
                # 3. Precio muy alto respecto a importe (seria base imponible)
                if precio > importe:
                    continue
                
                # Determinar articulo basado en precio vs importe
                # Si precio == importe, es PORTES (cantidad=1)
                if abs(precio - importe) < 0.10:
                    articulo = 'PORTES'
                    categoria = 'TRANSPORTE'
                    cantidad = 1
                else:
                    articulo = 'R CAJA 6 BOT. VIÑA JESUSA TINTO'
                    categoria = 'VINO TEMPRANILLO'
                    cantidad = round(importe / precio) if precio > 0 else 1
                
                lineas.append({
                    'codigo': '093' if 'PORTE' in articulo else '076',
                    'articulo': articulo,
                    'cantidad': cantidad,
                    'precio_ud': round(precio, 2),
                    'iva': 21,
                    'base': round(importe, 2),
                    'categoria': categoria
                })
        
        return lineas
    
    def _determinar_categoria(self, descripcion: str) -> str:
        """Determina categoria segun descripcion."""
        desc_upper = descripcion.upper()
        if 'PORTE' in desc_upper:
            return 'TRANSPORTE'
        elif 'VERMOUTH' in desc_upper or 'VERMUT' in desc_upper:
            return 'VERMUT BAG IN BOX 5L'
        elif 'BLANCO' in desc_upper:
            return 'VINO BLANCO GENERICO'
        else:
            return 'VINO TEMPRANILLO'
    
    def _convertir_europeo(self, texto: str) -> float:
        """Convierte formato europeo a float."""
        if not texto:
            return 0.0
        texto = texto.strip().replace('€', '').replace(' ', '')
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
        # Formato cuadro fiscal: "112,26 21 23,57 135,83 €"
        m = re.search(r'[\d,\.]+\s+21\s+[\d,\.]+\s+([\d,\.]+)\s*€', texto)
        if m:
            return self._convertir_europeo(m.group(1))
        
        # Formato OCR: "99,50 €" despues de "Total"
        m = re.search(r'Total\s+([\d,\.]+)\s*€', texto, re.IGNORECASE)
        if m:
            return self._convertir_europeo(m.group(1))
        
        # Alternativa OCR: buscar importe mayor de 50€ al final
        importes = re.findall(r'([\d,\.]+)\s*€', texto)
        for imp in reversed(importes):
            valor = self._convertir_europeo(imp)
            if 50 < valor < 500:
                return valor
        
        return None
    
    def extraer_fecha(self, texto: str) -> Optional[str]:
        """Extrae fecha de la factura."""
        # Formato: "Fecha: 06/11/2025" o "06/11/2025"
        m = re.search(r'Fecha:\s*(\d{2}/\d{2}/\d{4})', texto)
        if m:
            return m.group(1)
        
        m = re.search(r'(\d{2}/\d{2}/\d{4})', texto)
        if m:
            return m.group(1)
        
        return None
    
    def extraer_numero_factura(self, texto: str) -> Optional[str]:
        """Extrae numero de factura."""
        # Formato: "Numero: 25F00299" o "25F00299" o albaran "24P00077"
        m = re.search(r'N[uú]mero:\s*(\d+F\d+)', texto)
        if m:
            return m.group(1)
        
        m = re.search(r'(\d+[FP]\d+)', texto)
        if m:
            return m.group(1)
        
        return None
    
    extraer_referencia = extraer_numero_factura
