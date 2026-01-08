# -*- coding: utf-8 -*-
"""
Extractor para CONTROLPLAGA (Javier Alborés Rey)

Servicio de desinsectación y desratización
NIF: REDACTED_DNI (persona física)
IBAN: REDACTED_IBAN

Formato factura simple:
DESCRIPCIÓN                              PRECIO CONVENIDO
Tratamiento desinsectación y desratización    90.00
COMESTIBLES BAREA

IVA: 21%
Categoria fija: DESINSECTACION

Creado: 04/01/2026
"""
from extractores.base import ExtractorBase
from extractores import registrar
from typing import List, Dict, Optional
import re
import pdfplumber


@registrar('CONTROLPLAGA', 'CONTROL PLAGA', 'JAVIER ALBORES', 'JAVIER ALBORÉS',
           'JAVIER ARBORES', 'JAVIER ARBOLES', 'ALBORÉS REY', 'ALBORES REY')
class ExtractorControlplaga(ExtractorBase):
    """Extractor para facturas de CONTROLPLAGA (Javier Alborés Rey)."""
    
    nombre = 'CONTROLPLAGA'
    cif = 'REDACTED_DNI'
    iban = 'REDACTED_IBAN'
    metodo_pdf = 'pdfplumber'
    categoria_fija = 'DESINSECTACION'
    
    def extraer_texto(self, pdf_path: str) -> str:
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
    
    def extraer_lineas(self, texto: str) -> List[Dict]:
        """
        Extrae lineas de servicios.
        
        Formato:
        Tratamiento desinsectación y desratización    90.00
        COMESTIBLES BAREA (opcional, segunda línea)
        """
        lineas = []
        
        # Buscar línea con precio (formato: descripcion + precio)
        # El precio está en formato XX.XX (punto decimal)
        patron = re.compile(
            r'(Tratamiento\s+desinsectaci[oó]n\s+y\s+desratizaci[oó]n)\s+(\d+\.\d{2})',
            re.IGNORECASE
        )
        
        match = patron.search(texto)
        if match:
            descripcion = match.group(1).strip()
            precio = float(match.group(2))
            
            # Buscar si hay "COMESTIBLES BAREA" después
            if 'COMESTIBLES BAREA' in texto.upper():
                descripcion += ' - COMESTIBLES BAREA'
            
            lineas.append({
                'codigo': '',
                'articulo': descripcion[:50],
                'cantidad': 1,
                'precio_ud': round(precio, 2),
                'iva': 21,
                'base': round(precio, 2),
                'categoria': self.categoria_fija
            })
        
        return lineas
    
    def extraer_total(self, texto: str) -> Optional[float]:
        """Extrae total de la factura."""
        # Formato: TOTAL FACTURA 108.90
        patron = re.search(r'TOTAL\s+FACTURA\s+(\d+\.\d{2})', texto, re.IGNORECASE)
        if patron:
            return float(patron.group(1))
        
        return None
    
    def extraer_fecha(self, texto: str) -> Optional[str]:
        """Extrae fecha de la factura."""
        # Formato: Madrid, 20 DE noviembre DE 2025
        meses = {
            'enero': '01', 'febrero': '02', 'marzo': '03', 'abril': '04',
            'mayo': '05', 'junio': '06', 'julio': '07', 'agosto': '08',
            'septiembre': '09', 'octubre': '10', 'noviembre': '11', 'diciembre': '12'
        }
        patron = re.search(
            r'Madrid,\s*(\d{1,2})\s+DE\s+(\w+)\s+DE\s+(\d{4})',
            texto, re.IGNORECASE
        )
        if patron:
            dia = patron.group(1).zfill(2)
            mes = meses.get(patron.group(2).lower(), '01')
            anio = patron.group(3)
            return f"{dia}/{mes}/{anio}"
        
        # Alternativa: Fecha vencimiento DD/MM/YY
        patron2 = re.search(r'Fecha\s+vencimiento\s+(\d{2}/\d{2}/\d{2})', texto)
        if patron2:
            fecha = patron2.group(1)
            partes = fecha.split('/')
            return f"{partes[0]}/{partes[1]}/20{partes[2]}"
        
        return None
    
    def extraer_numero_factura(self, texto: str) -> Optional[str]:
        """Extrae numero de factura."""
        # Formato: Nº factura 20250410
        patron = re.search(r'Nº\s*factura\s+(\d+)', texto, re.IGNORECASE)
        if patron:
            return patron.group(1)
        
        return None
