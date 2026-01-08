# -*- coding: utf-8 -*-
"""
Extractor para ALFARERIA ANGEL Y LOLI (Lorenzo Lores García)

Alfarería artesanal de Níjar (Almería).
NIF: REDACTED_DNI

Formato factura (pdfplumber):
ARTÍCULO         CANTIDAD  PRECIO  TOTAL
PLATO LLANO      20        5,70    114,00
CUENCO 10 CM     15        2,07    31,05

Cuadro fiscal:
TIPO    IMPORTE   DESCUENTO   PORTES   BASE      I.V.A.    R.E.
21,00   549,50               45,00    594,50   124,85

IMPORTANTE v5.12:
- PORTES se suman proporcionalmente a cada línea
- DESCUENTO se resta proporcionalmente de cada línea
- Se detecta automáticamente si hay PORTES o DESCUENTO según:
  - Si IMPORTE + val2 ≈ BASE → val2 es PORTES
  - Si IMPORTE - val2 ≈ BASE → val2 es DESCUENTO

IVA: 21%
Categoría fija: CACHARRERIA

Creado: 26/12/2025
Actualizado: 06/01/2026 - Manejo correcto de portes vs descuentos
"""
from extractores.base import ExtractorBase
from extractores import registrar
from typing import List, Dict, Optional
import re


@registrar('ALFARERIA ANGEL Y LOLI', 'ANGEL Y LOLI', 'LORENZO LORES')
class ExtractorAngelLoli(ExtractorBase):
    """Extractor para facturas de ALFARERIA ANGEL Y LOLI."""
    
    nombre = 'ALFARERIA ANGEL Y LOLI'
    cif = 'REDACTED_DNI'
    iban = ''
    metodo_pdf = 'pdfplumber'
    categoria_fija = 'CACHARRERIA'
    
    def _convertir_europeo(self, texto: str) -> float:
        """Convierte formato europeo a float."""
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
    
    def _extraer_cuadro_fiscal(self, texto: str) -> Dict:
        """
        Extrae cuadro fiscal detectando automáticamente PORTES vs DESCUENTO.
        
        Detección:
        - Si IMPORTE + val2 ≈ BASE → val2 es PORTES
        - Si IMPORTE - val2 ≈ BASE → val2 es DESCUENTO
        """
        match = re.search(
            r'21,00\s+([\d.,]+)\s+([\d.,]+)\s+([\d.,]+)\s+([\d.,]+)',
            texto
        )
        
        if not match:
            return {'importe': 0, 'descuento': 0, 'portes': 0, 'base': 0, 'iva': 0}
        
        importe = self._convertir_europeo(match.group(1))
        val2 = self._convertir_europeo(match.group(2))
        base = self._convertir_europeo(match.group(3))
        iva = self._convertir_europeo(match.group(4))
        
        if abs((importe + val2) - base) < 0.10:
            return {'importe': importe, 'descuento': 0, 'portes': val2, 'base': base, 'iva': iva}
        elif abs((importe - val2) - base) < 0.10:
            return {'importe': importe, 'descuento': val2, 'portes': 0, 'base': base, 'iva': iva}
        else:
            return {'importe': importe, 'descuento': 0, 'portes': val2, 'base': base, 'iva': iva}
    
    def extraer_lineas(self, texto: str) -> List[Dict]:
        """Extrae líneas de productos y aplica portes/descuentos prorrateados."""
        lineas = []
        cuadro = self._extraer_cuadro_fiscal(texto)
        
        patron = re.compile(r'^(.+?)\s+(\d+)\s+(\d+[.,]\d{2})\s+(\d+[.,]\d{2})$')
        
        palabras_ignorar = [
            'ARTÍCULO', 'CANTIDAD', 'PRECIO', 'DOCUMENTO', 'NÚMERO', 'PÁGINA',
            'FECHA', 'OBSERVACIONES', 'TOTAL:', 'TIPO', 'IMPORTE', 'DESCUENTO',
            'PORTES', 'BASE', 'I.V.A', 'R.E.', 'FACTURA', 'LORENZO', 'LORES',
            'ALFARERÍA', 'ÁNGEL', 'LOLI', 'NÍJAR', 'ALMERIA', 'TASCA', 'RODAS',
            'MADRID', '75727068', 'B-87760575', '722 63', '04100', '28031',
            'LAS ERAS', 'ERAS 31'
        ]
        
        for linea in texto.split('\n'):
            linea = linea.strip()
            if not linea or any(x.upper() in linea.upper() for x in palabras_ignorar):
                continue
            
            match = patron.match(linea)
            if match:
                descripcion = match.group(1).strip()
                cantidad = int(match.group(2))
                precio = self._convertir_europeo(match.group(3))
                total = self._convertir_europeo(match.group(4))
                
                if total > 0 and cantidad > 0 and len(descripcion) >= 3:
                    lineas.append({
                        'codigo': '',
                        'articulo': descripcion[:50],
                        'cantidad': cantidad,
                        'precio_ud': round(precio, 2),
                        'iva': 21,
                        'base': round(total, 2),
                        'categoria': self.categoria_fija
                    })
        
        # Aplicar descuento y portes prorrateados
        if lineas:
            total_productos = sum(l['base'] for l in lineas)
            if total_productos > 0:
                for linea in lineas:
                    proporcion = linea['base'] / total_productos
                    if cuadro['descuento'] > 0:
                        linea['base'] -= cuadro['descuento'] * proporcion
                    if cuadro['portes'] > 0:
                        linea['base'] += cuadro['portes'] * proporcion
                    linea['base'] = round(linea['base'], 2)
                    if linea['cantidad'] > 0:
                        linea['precio_ud'] = round(linea['base'] / linea['cantidad'], 2)
        
        return lineas
    
    def extraer_total(self, texto: str) -> Optional[float]:
        """Extrae total de la factura."""
        m = re.search(r'TOTAL[:\s]*([\d.,]+)', texto, re.MULTILINE)
        if m:
            return self._convertir_europeo(m.group(1))
        return None
    
    def extraer_fecha(self, texto: str) -> Optional[str]:
        """Extrae fecha de la factura."""
        m = re.search(r'(\d{2})/(\d{2})/(\d{4})', texto)
        if m:
            return f"{m.group(1)}/{m.group(2)}/{m.group(3)}"
        return None
    
    def extraer_numero_factura(self, texto: str) -> Optional[str]:
        """Extrae número de factura."""
        m = re.search(r'(\d{6})\s+\d+\s+\d{2}/\d{2}/\d{4}', texto)
        if m:
            return m.group(1)
        return None
