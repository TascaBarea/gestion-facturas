"""
Extractor para TRUCCO COPIAS (ISAAC RODRIGUEZ PACHA)

Servicio de impresión y copistería.
NIF: REDACTED_DNI
Método de pago: Efectivo (FACTURA COBRADA)

Formato factura:
Total Base Imponible: 12,89 €
IVA 21%: 2,71 €
TOTAL: 15,60 €

IVA: 21%
Categoría fija: OTROS GASTOS

Creado: 26/12/2025
"""
from extractores.base import ExtractorBase
from extractores import registrar
from typing import List, Dict, Optional
import re


@registrar('TRUCCO COPIAS', 'TRUCCO', 'ISAAC RODRIGUEZ', 'ISAAC RODRIGUEZ PACHA',
           'ISAAC RODRÍGUEZ', 'ISAAC RODRÍGUEZ PACHA', 'ISSAC RODRIGUEZ')
class ExtractorTrucco(ExtractorBase):
    """Extractor para facturas de TRUCCO COPIAS."""
    
    nombre = 'TRUCCO COPIAS'
    cif = 'REDACTED_DNI'
    metodo_pdf = 'pdfplumber'
    categoria_fija = 'OTROS GASTOS'
    
    def extraer_lineas(self, texto: str) -> List[Dict]:
        """Extrae línea de servicio de impresión."""
        lineas = []
        
        # Buscar "Total Base Imponible: X €"
        match = re.search(
            r'Total\s+Base\s+Imponible:\s*([\d.,]+)\s*€',
            texto,
            re.IGNORECASE
        )
        
        if match:
            base = self._convertir_europeo(match.group(1))
            
            # Buscar concepto
            concepto_match = re.search(r'Concepto\s+Cantidad\s+Base\s+imp\.\s+IVA\s*\n([^\n]+)', texto)
            if concepto_match:
                concepto = concepto_match.group(1).strip()
                # Limpiar cantidad del concepto (ej: "IMPRESIONES 1 x 6,45 €" -> "IMPRESIONES")
                concepto = re.sub(r'\s+\d+\s*x\s*[\d.,]+\s*€.*$', '', concepto).strip()
            else:
                concepto = 'TRABAJOS DE IMPRESION'
            
            lineas.append({
                'codigo': '',
                'articulo': concepto.upper() if concepto else 'TRABAJOS DE IMPRESION',
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
        # "TOTAL: 15,60 €"
        m = re.search(r'TOTAL:\s*([\d.,]+)\s*€', texto, re.IGNORECASE)
        if m:
            return self._convertir_europeo(m.group(1))
        return None
    
    def extraer_fecha(self, texto: str) -> Optional[str]:
        """Extrae fecha de la factura."""
        # "Fecha: 29/10/2025"
        m = re.search(r'Fecha:\s*(\d{2})/(\d{2})/(\d{4})', texto)
        if m:
            return f"{m.group(1)}/{m.group(2)}/{m.group(3)}"
        return None
    
    def extraer_referencia(self, texto: str) -> Optional[str]:
        """Extrae número de factura."""
        # "Número de factura: 2025-3928"
        m = re.search(r'N[uú]mero\s+de\s+factura:\s*(\S+)', texto)
        if m:
            return m.group(1)
        return None
