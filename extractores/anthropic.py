"""
Extractor para ANTHROPIC, PBC

Suscripción Claude Pro/Max.
Sin CIF (empresa USA)
IVA: 0% (reverse charge - extranjero)
Categoría fija: GASTOS VARIOS
Moneda: EUR

Nota: Se extrae el importe neto final (una línea)

Creado: 26/12/2025
"""
from extractores.base import ExtractorBase
from extractores import registrar
from typing import List, Dict, Optional
import re


@registrar('ANTHROPIC', 'ANTHROPIC PBC', 'CLAUDE')
class ExtractorAnthropic(ExtractorBase):
    """Extractor para facturas de ANTHROPIC."""
    
    nombre = 'ANTHROPIC'
    cif = ''  # Empresa USA, sin CIF
    metodo_pdf = 'pdfplumber'
    categoria_fija = 'GASTOS VARIOS'
    
    def extraer_lineas(self, texto: str) -> List[Dict]:
        """Extrae línea de servicio de ANTHROPIC (importe neto)."""
        lineas = []
        
        # Buscar Amount due en EUR (importe neto final)
        m = re.search(r'Amount\s+due\s+€?([\d,.]+)', texto, re.IGNORECASE)
        if m:
            base = self._convertir_europeo(m.group(1))
            
            # Buscar descripción (Claude Pro o Max plan)
            if 'Max plan' in texto:
                descripcion = 'SUSCRIPCION CLAUDE MAX'
            else:
                descripcion = 'SUSCRIPCION CLAUDE PRO'
            
            lineas.append({
                'codigo': '',
                'articulo': descripcion,
                'cantidad': 1,
                'precio_ud': round(base, 2),
                'iva': 0,
                'base': round(base, 2),
                'categoria': self.categoria_fija
            })
        
        return lineas
    
    def _convertir_europeo(self, texto: str) -> float:
        """Convierte formato europeo a float."""
        if not texto:
            return 0.0
        texto = texto.strip()
        if ',' in texto and '.' in texto:
            texto = texto.replace('.', '').replace(',', '.')
        elif ',' in texto:
            texto = texto.replace(',', '.')
        try:
            return float(texto)
        except:
            return 0.0
    
    def extraer_total(self, texto: str) -> Optional[float]:
        """Extrae total de la factura."""
        m = re.search(r'Amount\s+due\s+€?([\d,.]+)', texto, re.IGNORECASE)
        if m:
            return self._convertir_europeo(m.group(1))
        return None
    
    def extraer_fecha(self, texto: str) -> Optional[str]:
        """Extrae fecha de la factura."""
        # "Date of issue November 8, 2025"
        m = re.search(r'Date\s+of\s+issue\s+(\w+)\s+(\d+),?\s+(\d{4})', texto)
        if m:
            meses = {'January': '01', 'February': '02', 'March': '03', 'April': '04',
                     'May': '05', 'June': '06', 'July': '07', 'August': '08',
                     'September': '09', 'October': '10', 'November': '11', 'December': '12'}
            mes = meses.get(m.group(1), '01')
            return f"{m.group(2).zfill(2)}/{mes}/{m.group(3)}"
        return None
    
    def extraer_referencia(self, texto: str) -> Optional[str]:
        """Extrae número de factura."""
        m = re.search(r'Invoice\s+number\s+([\w\-]+)', texto)
        if m:
            return m.group(1)
        return None
