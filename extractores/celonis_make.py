# -*- coding: utf-8 -*-
"""
Extractor para CELONIS INC. (Make.com)
Plataforma de automatización SaaS

Proveedor: Celonis Inc.
US EIN: 61-1797223
Producto: Make Core plan
Moneda: USD (sin IVA - empresa americana)

Formato factura:
- Invoice number: 556A1AE0-0011
- Date of issue: December 15, 2025
- Amount due: $10.59 USD

Nota: Los PDFs tienen caracteres nulos en lugar de guiones,
hay que limpiar el texto antes de procesar.

Creado: 28/12/2025
Actualizado: 08/01/2026 - extraer_referencia + fecha corregidos
"""
from extractores.base import ExtractorBase
from extractores import registrar
from typing import List, Dict, Optional
import re
import pdfplumber


@registrar('CELONIS', 'CELONIS INC', 'CELONIS INC.', 'MAKE', 'MAKE.COM')
class ExtractorCelonisMake(ExtractorBase):
    """Extractor para facturas de Celonis Inc. (Make.com)."""
    
    nombre = 'CELONIS INC.'
    cif = ''  # Empresa USA, no tiene CIF español
    iban = ''
    metodo_pdf = 'pdfplumber'
    categoria_fija = 'GASTOS VARIOS'
    
    # Meses en inglés para conversión de fechas
    MESES_EN = {
        'january': '01', 'february': '02', 'march': '03', 'april': '04',
        'may': '05', 'june': '06', 'july': '07', 'august': '08',
        'september': '09', 'october': '10', 'november': '11', 'december': '12',
        'jan': '01', 'feb': '02', 'mar': '03', 'apr': '04',
        'jun': '06', 'jul': '07', 'aug': '08', 'sep': '09', 
        'oct': '10', 'nov': '11', 'dec': '12'
    }
    
    def extraer_texto(self, pdf_path: str) -> str:
        """Extrae texto del PDF y limpia caracteres nulos."""
        try:
            with pdfplumber.open(pdf_path) as pdf:
                textos = []
                for page in pdf.pages:
                    texto = page.extract_text()
                    if texto:
                        # Limpiar caracteres nulos (aparecen como \x00)
                        texto = texto.replace('\x00', '-')
                        textos.append(texto)
                return '\n'.join(textos)
        except:
            return ''
    
    def extraer_referencia(self, texto: str) -> Optional[str]:
        """
        Extrae el número de factura.
        
        Formato: Invoice number 556A1AE0-0011
        
        v5.14: Renombrado de extraer_numero_factura a extraer_referencia
        """
        # Patrón para Invoice number
        patron = re.search(r'Invoice\s+number\s+([A-Z0-9]+-\d+)', texto, re.IGNORECASE)
        if patron:
            return patron.group(1)
        
        # Patrón alternativo (Receipt)
        patron2 = re.search(r'Receipt\s+number\s+(\d+-\d+)', texto, re.IGNORECASE)
        if patron2:
            return patron2.group(1)
        
        return None
    
    def extraer_fecha(self, texto: str) -> Optional[str]:
        """
        Extrae la fecha de emisión.
        
        Formato: Date of issue December 15, 2025
        También: Date paid April 15, 2025
        """
        # Patrón principal: Date of issue/Date paid + mes nombre
        patron = re.search(
            r'(?:Date\s+of\s+issue|Date\s+paid|Date\s+due)\s+([A-Za-z]+)\s+(\d{1,2}),?\s+(\d{4})',
            texto, re.IGNORECASE
        )
        if patron:
            mes_nombre = patron.group(1).lower()
            dia = patron.group(2).zfill(2)
            año = patron.group(3)
            mes = self.MESES_EN.get(mes_nombre, '01')
            return f"{dia}/{mes}/{año}"
        
        # Patrón alternativo: DD/MM/YYYY
        patron2 = re.search(r'(\d{1,2})/(\d{1,2})/(\d{4})', texto)
        if patron2:
            return patron2.group(0)
        
        return None
    
    def extraer_total(self, texto: str) -> Optional[float]:
        """Extrae el total de la factura en USD."""
        patrones = [
            r'Amount\s+(?:due|paid)\s+\$(\d+[,.]?\d*)\s*USD',
            r'Amount\s+(?:due|paid)\s+\$(\d+[,.]?\d*)',
            r'Total\s+\$(\d+[,.]?\d*)',
            r'\$(\d+[,.]?\d*)\s+USD\s+(?:due|paid)',
        ]
        
        for patron_str in patrones:
            match = re.search(patron_str, texto, re.IGNORECASE)
            if match:
                return self._convertir_numero(match.group(1))
        
        return None
    
    def _extraer_periodo(self, texto: str) -> Optional[str]:
        """Extrae el período de suscripción."""
        # Formato: Dec 15, 2025 – Jan 15, 2026
        patron = re.search(
            r'([A-Z][a-z]{2,8})\s+(\d{1,2}),?\s*(\d{4})?\s*[–\-]\s*([A-Z][a-z]{2,8})\s+(\d{1,2}),?\s*(\d{4})',
            texto
        )
        if patron:
            mes_ini = patron.group(1)[:3]
            dia_ini = patron.group(2)
            mes_fin = patron.group(4)[:3]
            dia_fin = patron.group(5)
            año = patron.group(6) or patron.group(3)
            return f"{mes_ini} {dia_ini} - {mes_fin} {dia_fin}, {año}"
        
        return None
    
    def extraer_lineas(self, texto: str) -> List[Dict]:
        """Extrae líneas de la factura."""
        lineas = []
        
        # Buscar importe
        total = self.extraer_total(texto)
        
        if total and total > 0:
            periodo = self._extraer_periodo(texto)
            descripcion = "Suscripción Make.com"
            if periodo:
                descripcion = f"Make Core ({periodo})"
            
            lineas.append({
                'codigo': 'MAKE',
                'articulo': descripcion[:50],
                'cantidad': 1,
                'precio_ud': total,
                'iva': 0,  # Empresa USA, sin IVA
                'base': total,
                'categoria': self.categoria_fija
            })
        
        return lineas
    
    def _convertir_numero(self, texto: str) -> float:
        """Convierte texto a número."""
        if not texto:
            return 0.0
        texto = str(texto).strip()
        texto = texto.replace(',', '').replace('$', '')
        try:
            return float(texto)
        except:
            return 0.0
