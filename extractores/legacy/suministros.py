"""
Extractores para facturas de suministros y servicios.
YOIGO, SOM ENERGIA, LUCERA, SEGURMA, KINEMA, ISTA

Actualizado: 18/12/2025 - pdfplumber
"""
from extractores.base import ExtractorBase
from extractores import registrar
from typing import List, Dict
import re


@registrar('YOIGO', 'XFERA')
class ExtractorYoigo(ExtractorBase):
    nombre = 'YOIGO'
    cif = 'A82528548'
    iban = ''
    metodo_pdf = 'pdfplumber'
    
    def extraer_lineas(self, texto: str) -> List[Dict]:
        lineas = []
        patrones = [
            r'\(21%\)\s*([\d,]+)\s*€?\s*Base\s*imponible',
            r'Base\s*imponible\s*\(?21%?\)?\s*([\d,]+)\s*€?',
        ]
        for patron in patrones:
            match = re.search(patron, texto, re.IGNORECASE)
            if match:
                base = self._convertir_importe(match.group(1))
                lineas.append({'codigo': 'YOIGO', 'articulo': 'Teléfono e Internet', 'iva': 21, 'base': base})
                break
        return lineas


@registrar('SOM ENERGIA')
class ExtractorSomEnergia(ExtractorBase):
    nombre = 'SOM ENERGIA'
    cif = 'F55091367'
    iban = ''
    metodo_pdf = 'pdfplumber'
    
    def extraer_lineas(self, texto: str) -> List[Dict]:
        lineas = []
        patron_iva = re.search(r'IVA\s*(\d+)%\s*([\d,]+)\s*€?', texto)
        iva = 21
        importe_iva = 0
        if patron_iva:
            iva = int(patron_iva.group(1))
            importe_iva = self._convertir_importe(patron_iva.group(2))
        
        patron_base = re.search(r'([\d,]+)\s*€?\s*\(?BASE\s*IMPONIBLE\)?', texto, re.IGNORECASE)
        base = None
        if patron_base:
            base = self._convertir_importe(patron_base.group(1))
        
        if base is None:
            patron_total = re.search(r'TOTAL\s*(?:IMPORTE\s*)?FACTURA[:\s]*([\d,]+)\s*€?', texto, re.IGNORECASE)
            if patron_total and importe_iva > 0:
                total = self._convertir_importe(patron_total.group(1))
                base = total - importe_iva
        
        if base and base > 0:
            lineas.append({'codigo': 'SOM', 'articulo': 'ELECTRICIDAD', 'iva': iva, 'base': round(base, 2)})
        return lineas


@registrar('LUCERA')
class ExtractorLucera(ExtractorBase):
    nombre = 'LUCERA'
    cif = 'B98670003'
    iban = ''
    metodo_pdf = 'pdfplumber'
    
    def extraer_lineas(self, texto: str) -> List[Dict]:
        lineas = []
        patron_base = re.search(r'IVA\s*21%\s*\(sobre\s*([\d,]+)\s*€?\)', texto)
        if patron_base:
            base = self._convertir_importe(patron_base.group(1))
            lineas.append({'codigo': 'LUCERA', 'articulo': 'ELECTRICIDAD', 'iva': 21, 'base': base})
        return lineas


@registrar('SEGURMA')
class ExtractorSegurma(ExtractorBase):
    nombre = 'SEGURMA'
    cif = 'A48198626'
    iban = ''
    metodo_pdf = 'pdfplumber'
    
    def extraer_lineas(self, texto: str) -> List[Dict]:
        lineas = []
        patron = re.search(r'Subtotal\s*([\d,]+)\s*€', texto)
        if patron:
            base = self._convertir_importe(patron.group(1))
            lineas.append({'codigo': 'SEGURMA', 'articulo': 'Alarma', 'iva': 21, 'base': base})
        return lineas


@registrar('KINEMA')
class ExtractorKinema(ExtractorBase):
    nombre = 'KINEMA'
    cif = 'F84600022'
    iban = ''
    metodo_pdf = 'pdfplumber'
    
    def extraer_lineas(self, texto: str) -> List[Dict]:
        lineas = []
        patron = re.search(r'Base Imponible[:\s]*([\d,]+)\s*€?', texto, re.IGNORECASE)
        if patron:
            base = self._convertir_importe(patron.group(1))
            lineas.append({'codigo': 'KINEMA', 'articulo': 'Cuota socio Kinema', 'iva': 21, 'base': base})
        return lineas


@registrar('ISTA')
class ExtractorIsta(ExtractorBase):
    nombre = 'ISTA'
    cif = 'A50090133'
    iban = ''
    metodo_pdf = 'pdfplumber'
    
    def extraer_lineas(self, texto: str) -> List[Dict]:
        lineas = []
        patron = re.search(r'Base\s+Imponible[:\s]*([\d,]+)', texto, re.IGNORECASE)
        if patron:
            base = self._convertir_importe(patron.group(1))
            lineas.append({'codigo': 'ISTA', 'articulo': 'Lectura contadores agua', 'iva': 21, 'base': base})
        return lineas
