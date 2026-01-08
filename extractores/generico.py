"""
Extractor genérico - Fallback para proveedores sin extractor específico.

Intenta extraer líneas usando patrones comunes.

Actualizado: 18/12/2025 - pdfplumber + limpieza encoding
"""
from extractores.base import ExtractorBase
from extractores import registrar
from typing import List, Dict
import re


class ExtractorGenerico(ExtractorBase):
    """
    Extractor genérico para facturas sin extractor específico.
    
    Intenta múltiples patrones comunes para extraer líneas.
    """
    nombre = 'GENERICO'
    cif = ''
    iban = ''
    metodo_pdf = 'pdfplumber'
    
    def extraer_lineas(self, texto: str) -> List[Dict]:
        lineas = []
        
        # Método 1: Buscar tabla de IVAs (formato desglose fiscal)
        lineas = self._extraer_desglose_iva(texto)
        if lineas:
            return lineas
        
        # Método 2: Buscar Base Imponible directa
        lineas = self._extraer_base_imponible(texto)
        if lineas:
            return lineas
        
        # Método 3: Patrón genérico de líneas
        lineas = self._extraer_lineas_genericas(texto)
        
        return lineas
    
    def _extraer_desglose_iva(self, texto: str) -> List[Dict]:
        """Extrae líneas del desglose fiscal (IVA% BASE CUOTA)."""
        lineas = []
        
        patron = re.compile(r'(\d{1,2})[,\.]?(?:\d{2})?%\s+([\d,\.]+)\s+([\d,\.]+)')
        
        for match in patron.finditer(texto):
            iva = int(match.group(1))
            base = self._convertir_importe(match.group(2))
            
            if base > 0 and iva in [4, 10, 21]:
                lineas.append({
                    'codigo': '',
                    'articulo': f'PRODUCTOS IVA {iva}%',
                    'iva': iva,
                    'base': round(base, 2)
                })
        
        return lineas
    
    def _extraer_base_imponible(self, texto: str) -> List[Dict]:
        """Extrae línea única de Base Imponible."""
        lineas = []
        
        patron = re.search(r'Base\s*Imponible[:\s]*([\d,\.]+)', texto, re.IGNORECASE)
        if patron:
            base = self._convertir_importe(patron.group(1))
            if base > 0:
                # Detectar IVA
                patron_iva = re.search(r'IVA\s*(\d{1,2})%', texto, re.IGNORECASE)
                iva = int(patron_iva.group(1)) if patron_iva else 21
                
                lineas.append({
                    'codigo': '',
                    'articulo': 'Factura',
                    'iva': iva,
                    'base': round(base, 2)
                })
        
        return lineas
    
    def _extraer_lineas_genericas(self, texto: str) -> List[Dict]:
        """Intenta extraer líneas con patrones genéricos."""
        lineas = []
        
        # Patrón: DESCRIPCION CANTIDAD PRECIO IMPORTE
        patron = re.compile(
            r'^(.{5,50}?)\s+(\d+)\s+([\d,]+)\s+([\d,]+)$',
            re.MULTILINE
        )
        
        for match in patron.finditer(texto):
            desc, cantidad, precio, importe = match.groups()
            desc_limpia = desc.strip()
            
            # Filtrar cabeceras
            if any(x in desc_limpia.upper() for x in ['DESCRIPCION', 'CANTIDAD', 'PRECIO', 'IMPORTE', 'TOTAL']):
                continue
            
            if len(desc_limpia) < 3:
                continue
            
            base = self._convertir_importe(importe)
            if base > 0:
                lineas.append({
                    'codigo': '',
                    'articulo': desc_limpia,
                    'cantidad': int(cantidad),
                    'precio_ud': self._convertir_importe(precio),
                    'iva': 21,  # Por defecto
                    'base': base
                })
        
        return lineas


# Función de utilidad para obtener el extractor genérico
def obtener_extractor_generico():
    """Devuelve una instancia del extractor genérico."""
    return ExtractorGenerico()
