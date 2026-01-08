"""
Extractor para MERCADONA S.A.

Supermercado.
CIF: A46103834
IVA: Por línea (4%, 10%, 21%)
Categoría: Por diccionario

Creado: 26/12/2025
"""
from extractores.base import ExtractorBase
from extractores import registrar
from typing import List, Dict, Optional
import re


@registrar('MERCADONA', 'MERCADONA S.A.', 'MERCADONA SA')
class ExtractorMercadona(ExtractorBase):
    """Extractor para facturas de MERCADONA."""
    
    nombre = 'MERCADONA'
    cif = 'A46103834'
    metodo_pdf = 'pdfplumber'
    usa_diccionario = True
    
    def extraer_lineas(self, texto: str) -> List[Dict]:
        """Extrae líneas de productos de MERCADONA."""
        lineas = []
        
        # Patrón flexible: DESCRIPCION UNID P.UNITARIO B.IMP IVA% CUOTA_IVA IMPORTE
        patron = re.compile(
            r'^(.+?)\s+'                                 # Descripción
            r'(\d+)\s+'                                  # Unidades
            r'([\d,.]+)\s+'                              # P.Unitario
            r'([\d,.]+)\s+'                              # B.Imp
            r'(\d+)%\s+'                                 # IVA %
            r'[\d,.]+\s+'                                # Cuota IVA
            r'([\d,.]+)\s*$',                            # Importe
            re.MULTILINE
        )
        
        for match in patron.finditer(texto):
            descripcion = match.group(1).strip()
            cantidad = float(match.group(2))
            precio_ud = self._convertir_europeo(match.group(3))
            base = self._convertir_europeo(match.group(4))
            iva = int(match.group(5))
            
            # Ignorar si es línea de total (descripción es solo número/porcentaje)
            if descripcion.strip().replace('%', '').replace(' ', '').isdigit():
                continue
            
            if base > 0:
                lineas.append({
                    'codigo': '',
                    'articulo': descripcion,
                    'cantidad': cantidad,
                    'precio_ud': precio_ud,
                    'iva': iva,
                    'base': round(base, 2),
                    'categoria': ''  # Se asignará por diccionario
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
        m = re.search(r'Total\s+Factura\s*([\d,.]+)\s*€', texto, re.IGNORECASE)
        if m:
            return self._convertir_europeo(m.group(1))
        return None
    
    def extraer_fecha(self, texto: str) -> Optional[str]:
        """Extrae fecha de la factura."""
        m = re.search(r'Fecha\s+Factura:?\s*(\d{2}/\d{2}/\d{4})', texto)
        if m:
            return m.group(1)
        return None
    
    def extraer_referencia(self, texto: str) -> Optional[str]:
        """Extrae número de factura."""
        m = re.search(r'N[ºo°]\s*Factura:?\s*([\w\-]+)', texto)
        if m:
            return m.group(1)
        return None
