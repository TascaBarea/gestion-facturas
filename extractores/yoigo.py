"""
Extractor para YOIGO (XFERA MÓVILES S.A.U.)

Servicio de telefonía e internet.
CIF: A82528548
Método de pago: Domiciliación

Formato factura:
DESGLOSE FISCAL
Base imponible (21%) 26,45€
IVA 21% 5,55€
Total factura 32,00€

IVA: 21%
Categoría fija: TELEFONO Y COMUNICACIONES

Creado: 26/12/2025
"""
from extractores.base import ExtractorBase
from extractores import registrar
from typing import List, Dict, Optional
import re


@registrar('YOIGO', 'XFERA MOVILES', 'XFERA MÓVILES', 'XFERA')
class ExtractorYoigo(ExtractorBase):
    """Extractor para facturas de YOIGO."""
    
    nombre = 'YOIGO'
    cif = 'A82528548'
    metodo_pdf = 'pdfplumber'
    categoria_fija = 'TELEFONO Y COMUNICACIONES'
    
    def extraer_lineas(self, texto: str) -> List[Dict]:
        """Extrae línea de servicio telefónico."""
        lineas = []
        
        # Buscar base imponible: "Base imponible (21%) 26,45€"
        match = re.search(
            r'Base\s+imponible\s*\(21%\)\s*([\d,]+)\s*€',
            texto,
            re.IGNORECASE
        )
        
        if match:
            base = self._convertir_europeo(match.group(1))
            
            # Buscar descripción del servicio
            desc_match = re.search(r'(FIBRA[^€\n]+)', texto)
            descripcion = desc_match.group(1).strip() if desc_match else 'SERVICIO TELEFONIA E INTERNET'
            
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
        # "TOTAL A PAGAR 32,00€"
        m = re.search(r'TOTAL\s+A\s+PAGAR\s*([\d,]+)\s*€', texto, re.IGNORECASE)
        if m:
            return self._convertir_europeo(m.group(1))
        return None
    
    def extraer_fecha(self, texto: str) -> Optional[str]:
        """Extrae fecha de emisión."""
        # "Fecha de emisión: 01/11/2025"
        m = re.search(r'Fecha\s+de\s+emisi[oó]n:\s*(\d{2})/(\d{2})/(\d{4})', texto)
        if m:
            return f"{m.group(1)}/{m.group(2)}/{m.group(3)}"
        return None
    
    def extraer_referencia(self, texto: str) -> Optional[str]:
        """Extrae número de factura."""
        # "Número de Factura: YC250015669532"
        m = re.search(r'N[uú]mero\s+de\s+Factura:\s*(\S+)', texto)
        if m:
            return m.group(1)
        return None
