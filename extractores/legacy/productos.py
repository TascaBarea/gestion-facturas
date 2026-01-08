"""
Extractores para productos varios.
MOLLETES, ZUBELZU, IBARRAKO, PRODUCTOS ADELL, ECOFICUS, ANA CABALLO, GRUPO CAMPERO

Actualizado: 18/12/2025 - pdfplumber
"""
from extractores.base import ExtractorBase
from extractores import registrar
from typing import List, Dict
import re


@registrar('MOLLETES', 'MOLLETES ARTESANOS')
class ExtractorMolletes(ExtractorBase):
    nombre = 'MOLLETES ARTESANOS'
    cif = 'B93662708'
    iban = 'REDACTED_IBAN'
    metodo_pdf = 'pdfplumber'
    
    def extraer_lineas(self, texto: str) -> List[Dict]:
        lineas = []
        patron = re.compile(r'^(\d{5})\s+(.+?)(?:\s+-\s+CAD\.?:\s*\d{2}/\d{2}/\d{4})?\s+(\d+)\s+([\d,]+)\s+([\d,]+)\s+[\d,]+\s+([\d,]+)$', re.MULTILINE)
        
        for match in patron.finditer(texto):
            codigo, desc, cajas, uds, precio, importe = match.groups()
            if 'DESCRIPCIÓN' in desc or 'DESCRIPCION' in desc:
                continue
            lineas.append({'codigo': codigo, 'articulo': desc.strip(), 'iva': 4, 'base': self._convertir_importe(importe)})
        return lineas


@registrar('ZUBELZU', 'ZUBELZU PIPARRAK')
class ExtractorZubelzu(ExtractorBase):
    nombre = 'ZUBELZU'
    cif = 'B75079608'
    iban = 'REDACTED_IBAN'
    metodo_pdf = 'pdfplumber'
    
    def extraer_lineas(self, texto: str) -> List[Dict]:
        lineas = []
        patron = re.compile(r'^(.+?)\s+(\d+)\s+([\d,]+)\s+([\d,]+)$', re.MULTILINE)
        
        for match in patron.finditer(texto):
            desc, uds, precio, importe = match.groups()
            if 'DESCRIPCION' in desc.upper() or len(desc.strip()) < 3:
                continue
            lineas.append({'codigo': '', 'articulo': desc.strip(), 'cantidad': int(uds), 'precio_ud': self._convertir_importe(precio), 'iva': 10, 'base': self._convertir_importe(importe)})
        return lineas


@registrar('IBARRAKO PIPARRAK', 'IBARRAKO PIPARRA', 'IBARRAKO')
class ExtractorIbarrako(ExtractorBase):
    nombre = 'IBARRAKO PIPARRAK'
    cif = 'F20532297'
    iban = 'REDACTED_IBAN'
    metodo_pdf = 'pdfplumber'
    
    def extraer_lineas(self, texto: str) -> List[Dict]:
        lineas = []
        patron = re.compile(r'^(\d{2,4})\s+(.+?)\s+(\d+)\s+([\d,]+)\s+([\d,]+)$', re.MULTILINE)
        
        for match in patron.finditer(texto):
            codigo, desc, uds, precio, importe = match.groups()
            if 'DESCRIPCION' in desc.upper():
                continue
            lineas.append({'codigo': codigo, 'articulo': desc.strip(), 'cantidad': int(uds), 'precio_ud': self._convertir_importe(precio), 'iva': 10, 'base': self._convertir_importe(importe)})
        return lineas


@registrar('PRODUCTOS ADELL', 'CROQUELLANAS')
class ExtractorProductosAdell(ExtractorBase):
    nombre = 'PRODUCTOS ADELL'
    cif = 'B12711636'
    iban = 'REDACTED_IBAN'
    metodo_pdf = 'pdfplumber'
    
    def extraer_lineas(self, texto: str) -> List[Dict]:
        lineas = []
        patron = re.compile(r'^(\d{4,6})\s+(.+?)\s+(\d+)\s+([\d,]+)\s+([\d,]+)$', re.MULTILINE)
        
        for match in patron.finditer(texto):
            codigo, desc, uds, precio, importe = match.groups()
            if 'DESCRIPCION' in desc.upper():
                continue
            lineas.append({'codigo': codigo, 'articulo': desc.strip(), 'cantidad': int(uds), 'precio_ud': self._convertir_importe(precio), 'iva': 10, 'base': self._convertir_importe(importe)})
        return lineas


@registrar('ECOFICUS')
class ExtractorEcoficus(ExtractorBase):
    nombre = 'ECOFICUS'
    cif = 'B10214021'
    iban = 'REDACTED_IBAN'
    metodo_pdf = 'pdfplumber'
    
    def extraer_lineas(self, texto: str) -> List[Dict]:
        lineas = []
        patron = re.compile(r'^(.+?)\s+(\d+)\s+([\d,]+)\s+([\d,]+)$', re.MULTILINE)
        
        for match in patron.finditer(texto):
            desc, uds, precio, importe = match.groups()
            if 'DESCRIPCION' in desc.upper() or len(desc.strip()) < 3:
                continue
            lineas.append({'codigo': '', 'articulo': desc.strip(), 'cantidad': int(uds), 'precio_ud': self._convertir_importe(precio), 'iva': 10, 'base': self._convertir_importe(importe)})
        return lineas


@registrar('ANA CABALLO', 'ANA CABALLO VERMOUTH')
class ExtractorAnaCaballo(ExtractorBase):
    nombre = 'ANA CABALLO'
    cif = 'B87925970'
    iban = 'REDACTED_IBAN'
    metodo_pdf = 'pdfplumber'
    
    def extraer_lineas(self, texto: str) -> List[Dict]:
        lineas = []
        patron = re.compile(r'^(.+?)\s+(\d+)\s+([\d,]+)\s+([\d,]+)$', re.MULTILINE)
        
        for match in patron.finditer(texto):
            desc, uds, precio, importe = match.groups()
            if 'DESCRIPCION' in desc.upper() or len(desc.strip()) < 3:
                continue
            lineas.append({'codigo': '', 'articulo': desc.strip(), 'cantidad': int(uds), 'precio_ud': self._convertir_importe(precio), 'iva': 21, 'base': self._convertir_importe(importe)})
        return lineas


@registrar('GRUPO TERRITORIO CAMPERO', 'TERRITORIO CAMPERO', 'GRUPO CAMPERO')
class ExtractorGrupoCampero(ExtractorBase):
    nombre = 'GRUPO CAMPERO'
    cif = 'B16690141'
    iban = 'REDACTED_IBAN'
    metodo_pdf = 'pdfplumber'
    
    def extraer_lineas(self, texto: str) -> List[Dict]:
        lineas = []
        patron = re.compile(r'^(\d{4,6})\s+(.+?)\s+(\d+)\s+([\d,]+)\s+([\d,]+)$', re.MULTILINE)
        
        for match in patron.finditer(texto):
            codigo, desc, uds, precio, importe = match.groups()
            if 'DESCRIPCION' in desc.upper():
                continue
            lineas.append({'codigo': codigo, 'articulo': desc.strip(), 'cantidad': int(uds), 'precio_ud': self._convertir_importe(precio), 'iva': 10, 'base': self._convertir_importe(importe)})
        return lineas
