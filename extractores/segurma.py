"""
Extractor para SEGURMA SA

Servicio de alarma y seguridad.
CIF: A48198626
Método de pago: Domiciliación

Formato factura:
Subtotal 39,86 €
IVA 21% 8,37 €
Total 48,23 €

IVA: 21%
Categoría fija: ALARMA

Creado: 26/12/2025
"""
from extractores.base import ExtractorBase
from extractores import registrar
from typing import List, Dict, Optional
import re


@registrar('SEGURMA', 'SEGURMA SA', 'SEGURMA S.A.')
class ExtractorSegurma(ExtractorBase):
    """Extractor para facturas de SEGURMA."""
    
    nombre = 'SEGURMA'
    cif = 'A48198626'
    metodo_pdf = 'pdfplumber'
    categoria_fija = 'ALARMA'
    
    def extraer_lineas(self, texto: str) -> List[Dict]:
        """Extrae línea de servicio de alarma."""
        lineas = []
        
        # Buscar Subtotal (base imponible): "Subtotal 39,86 €"
        match = re.search(
            r'Subtotal\s+([\d.,]+)\s*€',
            texto,
            re.IGNORECASE
        )
        
        if match:
            base = self._convertir_europeo(match.group(1))
            
            # Buscar período
            periodo_match = re.search(r'(\d{2}-\d{2}-\d{4})\s*-\s*(\d{2}-\d{2}-\d{4})', texto)
            periodo = ''
            if periodo_match:
                periodo = f"{periodo_match.group(1)} a {periodo_match.group(2)}"
            
            lineas.append({
                'codigo': '',
                'articulo': f'SERVICIO ALARMA {periodo}'.strip(),
                'cantidad': 1,
                'precio_ud': round(base, 2),
                'iva': 21,
                'base': round(base, 2),
                'categoria': self.categoria_fija
            })
        
        return lineas
    
    def _convertir_europeo(self, texto: str) -> float:
        """Convierte formato europeo a float."""
        if not texto:
            return 0.0
        texto = texto.strip()
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
        # "Total 48,23 €"
        m = re.search(r'^Total\s+([\d.,]+)\s*€', texto, re.MULTILINE | re.IGNORECASE)
        if m:
            return self._convertir_europeo(m.group(1))
        return None
    
    def extraer_fecha(self, texto: str) -> Optional[str]:
        """Extrae fecha de factura."""
        # "Fecha de factura: 01/12/2025"
        m = re.search(r'Fecha\s+de\s+factura:\s*(\d{2})/(\d{2})/(\d{4})', texto)
        if m:
            return f"{m.group(1)}/{m.group(2)}/{m.group(3)}"
        return None
    
    def extraer_referencia(self, texto: str) -> Optional[str]:
        """Extrae número de factura."""
        # "Factura C/2025/12/015690"
        m = re.search(r'Factura\s+(C/\d+/\d+/\d+)', texto)
        if m:
            return m.group(1)
        return None
