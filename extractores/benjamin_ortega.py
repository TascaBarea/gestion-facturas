# -*- coding: utf-8 -*-
"""
Extractor para BENJAMIN ORTEGA ALONSO.
Alquiler local Calle Rodas 2, Madrid.

NIF: REDACTED_DNI
Método: pdfplumber

Formato factura:
- Base: 500,00€ (SUBTOTAL)
- IVA: 21% = 105,00€
- Retención IRPF: 19% = -95,00€
- TOTAL A PAGAR: 510,00€

IMPORTANTE: La retención se modela como línea negativa con IVA 0%
para que el cuadre funcione: 500×1.21 + (-95)×1.00 = 510€ ✓

Creado: 21/12/2025
Corregido: 01/01/2026 - Retención como línea negativa
"""
from extractores.base import ExtractorBase
from extractores import registrar
from typing import List, Dict, Optional
import re


@registrar(
    'BENJAMIN ORTEGA',
    'BENJAMIN ORTEGA ALONSO',
    'BENJAMIN ORTEGA  OJO RETENCION',
    'BENJAMIN ORTEGA OJO RETENCION'
)
class ExtractorBenjaminOrtega(ExtractorBase):
    """Extractor para BENJAMIN ORTEGA ALONSO (alquiler local)."""
    
    nombre = 'BENJAMIN ORTEGA ALONSO'
    cif = 'REDACTED_DNI'
    iban = ''
    metodo_pdf = 'pdfplumber'
    categoria_fija = 'ALQUILER LOCAL'
    RETENCION_PORCENTAJE = 19
    
    def extraer_lineas(self, texto: str) -> List[Dict]:
        """Extrae líneas incluyendo la retención como línea negativa."""
        if not texto:
            return []
        
        lineas = []
        
        # Extraer base (SUBTOTAL)
        base = self._extraer_subtotal(texto)
        if not base:
            return []
        
        # Extraer descripción
        descripcion = self._extraer_descripcion(texto)
        
        # Línea 1: Alquiler con IVA 21%
        lineas.append({
            'codigo': '',
            'articulo': descripcion,
            'cantidad': 1,
            'precio_ud': base,
            'iva': 21,
            'base': base
        })
        
        # Línea 2: Retención IRPF como línea NEGATIVA con IVA 0%
        retencion = round(base * self.RETENCION_PORCENTAJE / 100, 2)
        lineas.append({
            'codigo': '',
            'articulo': f'RETENCION IRPF {self.RETENCION_PORCENTAJE}%',
            'cantidad': 1,
            'precio_ud': -retencion,
            'iva': 0,
            'base': -retencion
        })
        
        return lineas
    
    def _extraer_subtotal(self, texto: str) -> Optional[float]:
        """Extrae el subtotal (base imponible)."""
        patron = re.search(r'SUBTOTAL\s+(\d+[,\.]\d+)\s*€?', texto, re.IGNORECASE)
        if patron:
            return self._convertir_europeo(patron.group(1))
        
        patron2 = re.search(r'Alquiler.*?(\d+[,\.]\d+)\s*€', texto, re.IGNORECASE)
        if patron2:
            return self._convertir_europeo(patron2.group(1))
        
        return None
    
    def _extraer_descripcion(self, texto: str) -> str:
        """Extrae la descripción del servicio."""
        patron = re.search(r'(Alquiler\s+mensual\s+local[^\n\d]*)', texto, re.IGNORECASE)
        if patron:
            return patron.group(1).strip()[:50]
        return 'ALQUILER LOCAL RODAS 2'
    
    def extraer_total(self, texto: str) -> Optional[float]:
        """Extrae el total a pagar (después de retención)."""
        if not texto:
            return None
        
        # Usar lookbehind negativo para excluir SUBTOTAL
        patron = re.search(r'(?<!SUB)TOTAL\s+(\d+[,\.]\d+)\s*€?', texto, re.IGNORECASE)
        if patron:
            return self._convertir_europeo(patron.group(1))
        
        return None
    
    def extraer_fecha(self, texto: str) -> Optional[str]:
        """Extrae la fecha de la factura."""
        if not texto:
            return None
        
        patron = re.search(r'Fecha:\s*(\d{2})-(\d{2})-(\d{2})', texto, re.IGNORECASE)
        if patron:
            dia = patron.group(1)
            mes = patron.group(2)
            ano = patron.group(3)
            return f"{dia}/{mes}/20{ano}"
        
        return None
    
    def extraer_numero_factura(self, texto: str) -> Optional[str]:
        """Extrae el número de factura."""
        if not texto:
            return None
        
        patron = re.search(r'N[.º°]\s*de\s+factura:\s*([^\n]+)', texto, re.IGNORECASE)
        if patron:
            return patron.group(1).strip()
        
        return None
    
    def _convertir_europeo(self, texto: str) -> float:
        """Convierte formato europeo a float."""
        if not texto:
            return 0.0
        texto = str(texto).strip()
        if ',' in texto and '.' in texto:
            texto = texto.replace('.', '').replace(',', '.')
        elif ',' in texto:
            texto = texto.replace(',', '.')
        try:
            return float(texto)
        except:
            return 0.0
