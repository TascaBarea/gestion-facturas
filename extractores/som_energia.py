"""
Extractor para SOM ENERGIA SCCL

Suministro eléctrico.
CIF: F55091367
Método de pago: Domiciliación

IMPORTANTE - Categoría según N.º de contrato:
- Contrato 0251846 → ELECTRICIDAD COMESTIBLES
- Contrato 0070841 → ELECTRICIDAD TASCA

Formato factura (página 2):
IVA 21% 173,98 € (BASE IMPONIBLE) 36,54 €
TOTAL FACTURA 210,52 €

IVA: 21%

Creado: 26/12/2025
"""
from extractores.base import ExtractorBase
from extractores import registrar
from typing import List, Dict, Optional
import re


@registrar('SOM ENERGIA', 'SOM ENERGIA SCCL', 'SOMENERGIA')
class ExtractorSomEnergia(ExtractorBase):
    """Extractor para facturas de SOM ENERGIA."""
    
    nombre = 'SOM ENERGIA'
    cif = 'F55091367'
    metodo_pdf = 'pdfplumber'
    
    # Mapeo de contratos a categorías
    CONTRATOS_CATEGORIAS = {
        '0251846': 'ELECTRICIDAD COMESTIBLES',
        '0070841': 'ELECTRICIDAD TASCA',
    }
    
    def extraer_lineas(self, texto: str) -> List[Dict]:
        """Extrae línea de electricidad con categoría según contrato."""
        lineas = []
        
        # Determinar categoría según N.º de contrato
        categoria = 'ELECTRICIDAD'  # Por defecto
        
        match_contrato = re.search(r'N\.º de contrato:\s*(\d+)', texto)
        if match_contrato:
            num_contrato = match_contrato.group(1)
            categoria = self.CONTRATOS_CATEGORIAS.get(num_contrato, 'ELECTRICIDAD')
        
        # Buscar base imponible: "173,98 € (BASE IMPONIBLE)"
        match_base = re.search(
            r'([\d.,]+)\s*€\s*\(BASE\s+IMPONIBLE\)',
            texto,
            re.IGNORECASE
        )
        
        if match_base:
            base = self._convertir_europeo(match_base.group(1))
            
            # Buscar período facturado
            periodo_match = re.search(r'Per[ií]odo\s+facturado:\s*del\s+([^\n]+)', texto)
            periodo = periodo_match.group(1).strip() if periodo_match else ''
            
            lineas.append({
                'codigo': '',
                'articulo': f'SUMINISTRO ELECTRICO {periodo}'.strip(),
                'cantidad': 1,
                'precio_ud': round(base, 2),
                'iva': 21,
                'base': round(base, 2),
                'categoria': categoria
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
        # "TOTAL IMPORTE FACTURA 210,52 €" o "TOTAL FACTURA 210,52 €"
        m = re.search(r'TOTAL\s+(?:IMPORTE\s+)?FACTURA\s+([\d.,]+)\s*€', texto, re.IGNORECASE)
        if m:
            return self._convertir_europeo(m.group(1))
        return None
    
    def extraer_fecha(self, texto: str) -> Optional[str]:
        """Extrae fecha de la factura."""
        # "Fecha de la factura: 01/12/2025"
        m = re.search(r'Fecha\s+de\s+la\s+factura:\s*(\d{2})/(\d{2})/(\d{4})', texto)
        if m:
            return f"{m.group(1)}/{m.group(2)}/{m.group(3)}"
        return None
    
    def extraer_referencia(self, texto: str) -> Optional[str]:
        """Extrae número de factura."""
        # "N.º de factura:FE2501314182"
        m = re.search(r'N[.º°]\s*de\s+factura:\s*(\S+)', texto)
        if m:
            return m.group(1)
        return None
