"""
Extractor para WEBEMPRESA Europa S.L.U.

Hosting y dominios.
CIF: B65739856
IVA: 21%
Categoría fija: GASTOS VARIOS

Creado: 26/12/2025
"""
from extractores.base import ExtractorBase
from extractores import registrar
from typing import List, Dict, Optional
import re


@registrar('WEBEMPRESA', 'WEBEMPRESA EUROPA', 'WEBEMPRESA EUROPA SLU')
class ExtractorWebempresa(ExtractorBase):
    """Extractor para facturas de WEBEMPRESA."""
    
    nombre = 'WEBEMPRESA'
    cif = 'B65739856'
    metodo_pdf = 'pdfplumber'
    categoria_fija = 'GASTOS VARIOS'
    
    def extraer_lineas(self, texto: str) -> List[Dict]:
        """Extrae líneas de servicio de WEBEMPRESA."""
        lineas = []
        
        # Buscar Sub Total (base imponible)
        m = re.search(r'Sub\s*Total\s+([\d,.]+)\s*EUR', texto, re.IGNORECASE)
        if m:
            base = self._convertir_europeo(m.group(1))
            
            # Buscar descripción del servicio
            desc_match = re.search(r'Descripción\s+Total\s*\n(.+?)\s+[\d,.]+\s*EUR', texto, re.DOTALL)
            if desc_match:
                descripcion = desc_match.group(1).strip().split('\n')[0].strip()
            else:
                descripcion = 'SERVICIO WEB/HOSTING'
            
            lineas.append({
                'codigo': '',
                'articulo': descripcion,
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
        m = re.search(r'Total\s+([\d,.]+)\s*EUR', texto, re.IGNORECASE)
        if m:
            return self._convertir_europeo(m.group(1))
        return None
    
    def extraer_fecha(self, texto: str) -> Optional[str]:
        """Extrae fecha de la factura."""
        m = re.search(r'Fecha\s+de\s+Factura:?\s*(\d{2})-(\d{2})-(\d{4})', texto)
        if m:
            return f"{m.group(1)}/{m.group(2)}/{m.group(3)}"
        return None
    
    def extraer_referencia(self, texto: str) -> Optional[str]:
        """Extrae número de factura."""
        m = re.search(r'Factura\s+n[ºo°]?(F[\d\-]+)', texto)
        if m:
            return m.group(1)
        return None
