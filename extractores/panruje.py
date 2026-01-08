"""
Extractor para PANRUJE, SL (Rosquillas La Ermita)

Rosquillas artesanas de Cieza (Murcia).
CIF: B13858014
IBAN: REDACTED_IBAN

Formato factura:
CÓDIGO  CANTIDAD  DETALLE                      LOTE  PRECIO  DTO.  IMPORTE
NOR 7   4,0       CAJAS DE ROSQUILLAS NORMALES  50   16,50   2,00   64,68
POR     1,0       PORTES                              24,60          24,60

TOTAL BRUTO  BASE IMPONIBLE  % I.V.A.  I.V.A.  TOTAL
89,28        89,28           4,0       3,57    92,85

IVA: Normalmente 4% (pan), pero puede ser 10% en algunos pedidos.
Categoría fija: ROSQUILLAS MARINERAS

Creado: 26/12/2025
Corregido: 26/12/2025 - Patrón extraer_total y detección IVA real
Validado: 7/7 facturas (1T25-4T25)
"""
from extractores.base import ExtractorBase
from extractores import registrar
from typing import List, Dict, Optional
import re
import pdfplumber


@registrar('PANRUJE', 'PANRUJE SL', 'PANRUJE, SL', 'LA ERMITA', 'ROSQUILLAS ARTESANAS')
class ExtractorPanruje(ExtractorBase):
    """Extractor para facturas de PANRUJE."""
    
    nombre = 'PANRUJE'
    cif = 'B13858014'
    iban = 'REDACTED_IBAN'
    metodo_pdf = 'pdfplumber'
    categoria_fija = 'ROSQUILLAS MARINERAS'
    
    def _convertir_europeo(self, texto: str) -> float:
        """Convierte formato europeo a float."""
        if not texto:
            return 0.0
        texto = str(texto).strip().replace('€', '').replace(' ', '')
        if ',' in texto and '.' in texto:
            texto = texto.replace('.', '').replace(',', '.')
        elif ',' in texto:
            texto = texto.replace(',', '.')
        try:
            return float(texto)
        except:
            return 0.0
    
    def _extraer_cuadro_fiscal(self, texto: str) -> Optional[Dict]:
        """
        Extrae el cuadro fiscal.
        
        Formato (última línea con 5 números):
        TOTAL_BRUTO  BASE_IMPONIBLE  %IVA  IVA  TOTAL
        89,28        89,28           4,0   3,57 92,85
        """
        # Buscar línea con 5 números al final
        m = re.search(
            r'([\d,]+)\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)\s*$',
            texto,
            re.MULTILINE
        )
        
        if m:
            return {
                'total_bruto': self._convertir_europeo(m.group(1)),
                'base': self._convertir_europeo(m.group(2)),
                'iva_pct': self._convertir_europeo(m.group(3)),
                'iva_importe': self._convertir_europeo(m.group(4)),
                'total': self._convertir_europeo(m.group(5))
            }
        
        return None
    
    def extraer_lineas(self, texto: str) -> List[Dict]:
        """
        Extrae línea única con rosquillas + portes sumados.
        Usa el cuadro fiscal como fuente de verdad.
        """
        lineas = []
        
        cuadro = self._extraer_cuadro_fiscal(texto)
        if not cuadro:
            return lineas
        
        base = cuadro['base']
        iva_pct = cuadro['iva_pct']
        
        # Determinar IVA real (normalmente 4%, pero puede ser 10%)
        iva = int(iva_pct) if iva_pct in [4, 10, 21] else 4
        
        # Buscar cantidad de cajas
        cantidad_match = re.search(
            r'NOR\s*7?\s+([\d,]+)\s+CAJAS',
            texto,
            re.IGNORECASE
        )
        if not cantidad_match:
            cantidad_match = re.search(
                r'([\d,]+)\s+CAJAS\s+DE\s+ROSQUILLAS',
                texto,
                re.IGNORECASE
            )
        
        cantidad = self._convertir_europeo(cantidad_match.group(1)) if cantidad_match else 1
        
        lineas.append({
            'codigo': 'NOR7',
            'articulo': 'CAJAS DE ROSQUILLAS NORMALES + PORTES',
            'cantidad': int(cantidad) if cantidad == int(cantidad) else cantidad,
            'precio_ud': round(base / cantidad, 4) if cantidad > 0 else base,
            'iva': iva,
            'base': round(base, 2),
            'categoria': self.categoria_fija
        })
        
        return lineas
    
    def extraer_total(self, texto: str) -> Optional[float]:
        """
        Extrae total de la factura desde el cuadro fiscal.
        
        El cuadro fiscal está en la última línea con formato:
        TOTAL_BRUTO  BASE  %IVA  IVA  TOTAL
        """
        cuadro = self._extraer_cuadro_fiscal(texto)
        if cuadro:
            return cuadro['total']
        
        # Fallback: buscar "TOTAL" seguido de número
        m = re.search(r'TOTAL\s+([\d,]+)\s*$', texto, re.MULTILINE | re.IGNORECASE)
        if m:
            return self._convertir_europeo(m.group(1))
        
        return None
    
    def extraer_fecha(self, texto: str) -> Optional[str]:
        """Extrae fecha de la factura."""
        # Formato: FT 197 15/12/2025
        m = re.search(r'FT\s+\d+\s+(\d{2}/\d{2}/\d{4})', texto)
        if m:
            return m.group(1)
        
        # Alternativo: FECHA seguida de fecha
        m = re.search(r'FECHA\s+(\d{2}/\d{2}/\d{4})', texto, re.IGNORECASE)
        if m:
            return m.group(1)
        
        return None
    
    def extraer_numero_factura(self, texto: str) -> Optional[str]:
        """Extrae número de factura."""
        m = re.search(r'FT\s+(\d+)', texto)
        if m:
            return f"FT-{m.group(1)}"
        return None
