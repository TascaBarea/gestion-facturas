"""
Extractor para LA MOLIENDA VERDE S.L.U.
Mermeladas y conservas artesanales.
CIF: B06936140 | IBAN: REDACTED_IBAN

Actualizado: 18/12/2025 - limpieza encoding
"""
from extractores.base import ExtractorBase
from extractores import registrar
from typing import List, Dict
import re


@registrar('LA MOLIENDA VERDE', 'MOLIENDA VERDE')
class ExtractorMoliendaVerde(ExtractorBase):
    nombre = 'LA MOLIENDA VERDE'
    cif = 'B06936140'
    iban = 'REDACTED_IBAN'
    metodo_pdf = 'pdfplumber'
    
    def extraer_lineas(self, texto: str) -> List[Dict]:
        lineas = []
        lineas_texto = texto.split('\n')
        
        # Preprocesar: unir líneas partidas
        lineas_unidas = []
        i = 0
        while i < len(lineas_texto):
            linea = lineas_texto[i].strip()
            if re.match(r'^\d{3}\s+', linea):
                if re.search(r'\d+\s+\d+[.,]\d{2}\s+\d+\s+\d+\s+\d+[.,]\d{2}$', linea):
                    lineas_unidas.append(linea)
                else:
                    if i + 1 < len(lineas_texto):
                        siguiente = lineas_texto[i + 1].strip()
                        if re.search(r'\d+\s+\d+[.,]\d{2}\s+\d+\s+\d+\s+\d+[.,]\d{2}$', siguiente):
                            lineas_unidas.append(linea + ' ' + siguiente)
                            i += 1
                        else:
                            lineas_unidas.append(linea)
                    else:
                        lineas_unidas.append(linea)
            elif 'PORTES' in linea.upper():
                lineas_unidas.append(linea)
            i += 1
        
        patron = re.compile(
            r'^(\d{3})\s+(.+?)\s+(\d+)\s+(\d+[.,]\d{2})\s+(\d+)\s+(\d+)\s+(\d+[.,]\d{2})$'
        )
        
        for linea in lineas_unidas:
            m = patron.match(linea)
            if m:
                codigo, desc, cant, precio, dto, iva, importe = m.groups()
                lineas.append({
                    'codigo': codigo,
                    'articulo': desc.strip(),
                    'cantidad': int(cant),
                    'precio_ud': self._convertir_importe(precio),
                    'iva': int(iva),
                    'base': self._convertir_importe(importe)
                })
        
        # PORTES
        patron_portes = re.compile(
            r'PORTES?\s+(\d+)\s+(\d+[.,]\d{2})\s+(\d+)\s+(\d+)\s+(\d+[.,]\d{2})',
            re.IGNORECASE
        )
        m = patron_portes.search(texto)
        if m:
            cant, precio, dto, iva, importe = m.groups()
            lineas.append({
                'codigo': 'PORTES',
                'articulo': 'PORTES',
                'cantidad': int(cant),
                'precio_ud': self._convertir_importe(precio),
                'iva': int(iva),
                'base': self._convertir_importe(importe)
            })
        
        return lineas
