"""
Extractores para facturas de quesos.
QUESOS FELIX, QUESOS ROYCA, QUESOS CATI, SILVA CORDERO

Actualizado: 18/12/2025 - pdfplumber
"""
from extractores.base import ExtractorBase
from extractores import registrar
from typing import List, Dict
import re


@registrar('QUESOS FELIX', 'ARMANDO SANZ', 'FELIX')
class ExtractorQuesosFelix(ExtractorBase):
    nombre = 'QUESOS FELIX'
    cif = 'B47440136'
    iban = 'REDACTED_IBAN'
    metodo_pdf = 'pdfplumber'
    
    def extraer_lineas(self, texto: str) -> List[Dict]:
        lineas = []
        patron = re.compile(r'^(.+?)\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)$', re.MULTILINE)
        
        for match in patron.finditer(texto):
            desc, cantidad, precio, dto, importe = match.groups()
            if 'DESCRIPCION' in desc.upper() or 'CANTIDAD' in desc.upper():
                continue
            if len(desc.strip()) < 5:
                continue
            lineas.append({'codigo': '', 'articulo': desc.strip(), 'cantidad': self._convertir_importe(cantidad), 'precio_ud': self._convertir_importe(precio), 'iva': 4, 'base': self._convertir_importe(importe)})
        return lineas


@registrar('QUESOS ROYCA', 'COMERCIAL ROYCA', 'ROYCA')
class ExtractorQuesosRoyca(ExtractorBase):
    nombre = 'QUESOS ROYCA'
    cif = 'E06388631'
    iban = ''
    metodo_pdf = 'pdfplumber'
    
    def extraer_lineas(self, texto: str) -> List[Dict]:
        lineas = []
        patron = re.compile(r'^(.+?)\s+([\d,]+)\s*kg\s+([\d,]+)\s+([\d,]+)$', re.MULTILINE | re.IGNORECASE)
        
        for match in patron.finditer(texto):
            desc, kg, precio, importe = match.groups()
            if 'DESCRIPCION' in desc.upper():
                continue
            lineas.append({'codigo': '', 'articulo': desc.strip(), 'cantidad': self._convertir_importe(kg), 'precio_ud': self._convertir_importe(precio), 'iva': 4, 'base': self._convertir_importe(importe)})
        return lineas


@registrar('QUESOS DEL CATI', 'QUESOS CATI')
class ExtractorQuesosCati(ExtractorBase):
    nombre = 'QUESOS DEL CATI'
    cif = 'F12499455'
    iban = 'REDACTED_IBAN'
    metodo_pdf = 'pdfplumber'
    
    def extraer_lineas(self, texto: str) -> List[Dict]:
        lineas = []
        patron = re.compile(r'^(.+?)\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)$', re.MULTILINE)
        
        for match in patron.finditer(texto):
            desc, cantidad, precio, importe = match.groups()
            if 'DESCRIPCION' in desc.upper() or 'IMPORTE' in desc.upper():
                continue
            lineas.append({'codigo': '', 'articulo': desc.strip(), 'cantidad': self._convertir_importe(cantidad), 'precio_ud': self._convertir_importe(precio), 'iva': 4, 'base': self._convertir_importe(importe)})
        return lineas


@registrar('SILVA CORDERO', 'QUESOS SILVA CORDERO', 'ACEHUCHE')
class ExtractorSilvaCordero(ExtractorBase):
    nombre = 'SILVA CORDERO'
    cif = 'B09861535'
    iban = 'REDACTED_IBAN'
    metodo_pdf = 'pdfplumber'
    
    def extraer_lineas(self, texto: str) -> List[Dict]:
        lineas = []
        patron = re.compile(r'^(.+?)\s+([\d,]+)\s*kg\s+([\d,]+)\s+([\d,]+)$', re.MULTILINE | re.IGNORECASE)
        
        for match in patron.finditer(texto):
            desc, kg, precio, importe = match.groups()
            if 'DESCRIPCION' in desc.upper():
                continue
            lineas.append({'codigo': '', 'articulo': desc.strip(), 'cantidad': self._convertir_importe(kg), 'precio_ud': self._convertir_importe(precio), 'iva': 4, 'base': self._convertir_importe(importe)})
        return lineas
