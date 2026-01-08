"""
Extractores varios restantes.
MARITA COSTA, PILAR RODRIGUEZ, PANIFIESTO, JULIO GARCIA VIVAS, LA BARRA DULCE, 
PORVAZ, MARTIN ABENZA, CARRASCAL, BIELLEBI, FERRIOL, ABBATI, MIGUEZ CAL, 
ROSQUILLERIA, MANIPULADOS ABELLAN, PC COMPONENTES, OPENAI, AMAZON

Actualizado: 18/12/2025 - pdfplumber (excepto OCR donde indicado)
"""
from extractores.base import ExtractorBase
from extractores import registrar
from typing import List, Dict
import re


@registrar('MARITA COSTA')
class ExtractorMaritaCosta(ExtractorBase):
    nombre = 'MARITA COSTA'
    cif = 'REDACTED_DNI'
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


@registrar('PILAR RODRIGUEZ', 'EL MAJADAL', 'HUEVOS EL MAJADAL')
class ExtractorPilarRodriguez(ExtractorBase):
    nombre = 'PILAR RODRIGUEZ'
    cif = 'REDACTED_DNI'
    iban = 'REDACTED_IBAN'
    metodo_pdf = 'pdfplumber'
    
    def extraer_lineas(self, texto: str) -> List[Dict]:
        lineas = []
        patron = re.compile(r'^(.+?)\s+(\d+)\s+([\d,]+)\s+([\d,]+)$', re.MULTILINE)
        for match in patron.finditer(texto):
            desc, uds, precio, importe = match.groups()
            if 'DESCRIPCION' in desc.upper() or len(desc.strip()) < 3:
                continue
            lineas.append({'codigo': '', 'articulo': desc.strip(), 'cantidad': int(uds), 'precio_ud': self._convertir_importe(precio), 'iva': 4, 'base': self._convertir_importe(importe)})
        return lineas


@registrar('PANIFIESTO', 'PANIFIESTO LAVAPIES')
class ExtractorPanifiesto(ExtractorBase):
    nombre = 'PANIFIESTO'
    cif = 'B87874327'
    iban = ''
    metodo_pdf = 'pdfplumber'
    
    def extraer_lineas(self, texto: str) -> List[Dict]:
        lineas = []
        patron = re.compile(r'^(.+?)\s+(\d+)\s+([\d,]+)\s+([\d,]+)$', re.MULTILINE)
        for match in patron.finditer(texto):
            desc, uds, precio, importe = match.groups()
            if 'DESCRIPCION' in desc.upper() or len(desc.strip()) < 3:
                continue
            lineas.append({'codigo': '', 'articulo': desc.strip(), 'cantidad': int(uds), 'precio_ud': self._convertir_importe(precio), 'iva': 4, 'base': self._convertir_importe(importe)})
        return lineas


@registrar('JULIO GARCIA VIVAS', 'GARCIA VIVAS')
class ExtractorJulioGarciaVivas(ExtractorBase):
    nombre = 'JULIO GARCIA VIVAS'
    cif = 'REDACTED_DNI'
    iban = ''
    metodo_pdf = 'pdfplumber'
    
    def extraer_lineas(self, texto: str) -> List[Dict]:
        lineas = []
        patron = re.search(r'Base\s*Imponible[:\s]*([\d,]+)', texto, re.IGNORECASE)
        if patron:
            base = self._convertir_importe(patron.group(1))
            lineas.append({'codigo': '', 'articulo': 'Verduras', 'iva': 4, 'base': base})
        return lineas


@registrar('LA BARRA DULCE', 'BARRA DULCE')
class ExtractorBarraDulce(ExtractorBase):
    nombre = 'LA BARRA DULCE'
    cif = 'B19981141'
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


@registrar('PORVAZ', 'PORVAZ VILAGARCIA', 'CONSERVAS TITO', 'TITO')
class ExtractorPorvaz(ExtractorBase):
    nombre = 'PORVAZ'
    cif = 'B36281087'
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


@registrar('MARTIN ABENZA', 'MARTIN ARBENZA', 'EL MODESTO')
class ExtractorMartinAbenza(ExtractorBase):
    nombre = 'MARTIN ABENZA'
    cif = 'REDACTED_DNI'
    iban = 'REDACTED_IBAN'
    metodo_pdf = 'pdfplumber'
    
    def extraer_lineas(self, texto: str) -> List[Dict]:
        lineas = []
        patron = re.search(r'Base\s*Imponible[:\s]*([\d,]+)', texto, re.IGNORECASE)
        if patron:
            base = self._convertir_importe(patron.group(1))
            lineas.append({'codigo': '', 'articulo': 'Aceite de oliva', 'iva': 4, 'base': base})
        return lineas


@registrar('CARRASCAL', 'EL CARRASCAL', 'JOSE LUIS SANCHEZ')
class ExtractorCarrascal(ExtractorBase):
    nombre = 'EL CARRASCAL'
    cif = 'REDACTED_DNI'
    iban = 'REDACTED_IBAN'
    metodo_pdf = 'pdfplumber'
    
    def extraer_lineas(self, texto: str) -> List[Dict]:
        lineas = []
        patron = re.search(r'Base\s*Imponible[:\s]*([\d,]+)', texto, re.IGNORECASE)
        if patron:
            base = self._convertir_importe(patron.group(1))
            lineas.append({'codigo': '', 'articulo': 'Aceite de oliva', 'iva': 4, 'base': base})
        return lineas


@registrar('BIELLEBI', 'BIELLEBI SRL')
class ExtractorBiellebi(ExtractorBase):
    nombre = 'BIELLEBI'
    cif = '06089700725'
    iban = 'REDACTED_IBAN'
    metodo_pdf = 'pdfplumber'
    
    def extraer_lineas(self, texto: str) -> List[Dict]:
        lineas = []
        patron = re.compile(r'^(.+?)\s+(\d+)\s+([\d,]+)\s+([\d,]+)$', re.MULTILINE)
        for match in patron.finditer(texto):
            desc, uds, precio, importe = match.groups()
            if 'DESCRIPCION' in desc.upper() or len(desc.strip()) < 3:
                continue
            lineas.append({'codigo': '', 'articulo': desc.strip(), 'cantidad': int(uds), 'precio_ud': self._convertir_importe(precio), 'iva': 0, 'base': self._convertir_importe(importe)})
        return lineas


@registrar('EMBUTIDOS FERRIOL', 'EMBOTITS FERRIOL', 'FERRIOL')
class ExtractorFerriol(ExtractorBase):
    nombre = 'FERRIOL'
    cif = 'B57955098'
    iban = 'REDACTED_IBAN'
    metodo_pdf = 'pdfplumber'
    
    def extraer_lineas(self, texto: str) -> List[Dict]:
        lineas = []
        patron = re.compile(r'^(\d{4,6})\s+(.+?)\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)$', re.MULTILINE)
        for match in patron.finditer(texto):
            codigo, desc, cantidad, precio, importe = match.groups()
            if 'DESCRIPCION' in desc.upper():
                continue
            lineas.append({'codigo': codigo, 'articulo': desc.strip(), 'cantidad': self._convertir_importe(cantidad), 'precio_ud': self._convertir_importe(precio), 'iva': 10, 'base': self._convertir_importe(importe)})
        return lineas


@registrar('ABBATI CAFFE', 'ABBATI')
class ExtractorAbbati(ExtractorBase):
    nombre = 'ABBATI'
    cif = 'B82567876'
    iban = ''
    metodo_pdf = 'pdfplumber'
    
    def extraer_lineas(self, texto: str) -> List[Dict]:
        lineas = []
        patron = re.search(r'Base\s*Imponible[:\s]*([\d,]+)', texto, re.IGNORECASE)
        if patron:
            base = self._convertir_importe(patron.group(1))
            lineas.append({'codigo': '', 'articulo': 'Café', 'iva': 10, 'base': base})
        return lineas


@registrar('MIGUEZ CAL', 'FORPLAN')
class ExtractorMiguezCal(ExtractorBase):
    nombre = 'MIGUEZ CAL'
    cif = 'B79868006'
    iban = 'REDACTED_IBAN'
    metodo_pdf = 'pdfplumber'
    
    def extraer_lineas(self, texto: str) -> List[Dict]:
        lineas = []
        patron = re.search(r'Base\s*Imponible[:\s]*([\d,]+)', texto, re.IGNORECASE)
        if patron:
            base = self._convertir_importe(patron.group(1))
            lineas.append({'codigo': '', 'articulo': 'Formación/Consultoría', 'iva': 21, 'base': base})
        return lineas


@registrar('LA ROSQUILLERIA', 'ROSQUILLERIA')
class ExtractorRosquilleria(ExtractorBase):
    nombre = 'LA ROSQUILLERIA'
    cif = 'B73814949'
    iban = 'REDACTED_IBAN'
    metodo_pdf = 'ocr'  # Mantiene OCR
    
    def extraer_lineas(self, texto: str) -> List[Dict]:
        lineas = []
        patron = re.search(r'Base\s*Imponible[:\s]*([\d,]+)', texto, re.IGNORECASE)
        if patron:
            base = self._convertir_importe(patron.group(1))
            lineas.append({'codigo': '', 'articulo': 'Rosquillas artesanas', 'iva': 4, 'base': base})
        return lineas


@registrar('MANIPULADOS ABELLAN', 'ABELLAN', 'EL LABRADOR')
class ExtractorManipuladosAbellan(ExtractorBase):
    nombre = 'MANIPULADOS ABELLAN'
    cif = 'B30473326'
    iban = 'REDACTED_IBAN'
    metodo_pdf = 'ocr'  # Mantiene OCR
    
    def extraer_lineas(self, texto: str) -> List[Dict]:
        lineas = []
        patron = re.compile(r'^(.+?)\s+(\d+)\s+([\d,]+)\s+([\d,]+)$', re.MULTILINE)
        for match in patron.finditer(texto):
            desc, uds, precio, importe = match.groups()
            if 'DESCRIPCION' in desc.upper() or len(desc.strip()) < 3:
                continue
            lineas.append({'codigo': '', 'articulo': desc.strip(), 'cantidad': int(uds), 'precio_ud': self._convertir_importe(precio), 'iva': 10, 'base': self._convertir_importe(importe)})
        return lineas


@registrar('PC COMPONENTES')
class ExtractorPCComponentes(ExtractorBase):
    nombre = 'PC COMPONENTES'
    cif = 'B73347494'
    iban = ''
    metodo_pdf = 'pdfplumber'
    
    def extraer_lineas(self, texto: str) -> List[Dict]:
        lineas = []
        patron = re.search(r'Base\s*Imponible[:\s]*([\d,]+)', texto, re.IGNORECASE)
        if patron:
            base = self._convertir_importe(patron.group(1))
            lineas.append({'codigo': '', 'articulo': 'Material informático', 'iva': 21, 'base': base})
        return lineas


@registrar('OPENAI')
class ExtractorOpenAI(ExtractorBase):
    nombre = 'OPENAI'
    cif = ''
    iban = ''
    metodo_pdf = 'pdfplumber'
    
    def extraer_lineas(self, texto: str) -> List[Dict]:
        lineas = []
        patron = re.search(r'(?:Subtotal|Amount)[:\s]*\$?([\d,\.]+)', texto, re.IGNORECASE)
        if patron:
            base = self._convertir_importe(patron.group(1))
            lineas.append({'codigo': '', 'articulo': 'Servicios API OpenAI', 'iva': 21, 'base': base})
        return lineas


@registrar('AMAZON')
class ExtractorAmazon(ExtractorBase):
    nombre = 'AMAZON'
    cif = 'W0184081H'
    iban = ''
    metodo_pdf = 'pdfplumber'
    
    def extraer_lineas(self, texto: str) -> List[Dict]:
        lineas = []
        patron = re.search(r'Base\s*Imponible[:\s]*([\d,]+)', texto, re.IGNORECASE)
        if patron:
            base = self._convertir_importe(patron.group(1))
            lineas.append({'codigo': '', 'articulo': 'Compra Amazon', 'iva': 21, 'base': base})
        return lineas
