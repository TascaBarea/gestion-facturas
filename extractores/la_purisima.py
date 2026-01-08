"""
Extractor para LA PURISIMA (Cooperativa del Vino de Yecla)

Bodega de vinos.
CIF: F30005193
IVA: 21% (vinos)
Categoría: Por diccionario

Creado: 26/12/2025
"""
from extractores.base import ExtractorBase
from extractores import registrar
from typing import List, Dict, Optional
import re


@registrar('LA PURISIMA', 'BODEGAS LA PURISIMA', 'COOPERATIVA DEL VINO DE YECLA')
class ExtractorLaPurisima(ExtractorBase):
    """Extractor para facturas de LA PURISIMA."""
    
    nombre = 'LA PURISIMA'
    cif = 'F30005193'
    metodo_pdf = 'pdfplumber'
    usa_diccionario = True
    
    def extraer_lineas(self, texto: str) -> List[Dict]:
        """Extrae líneas de productos de LA PURISIMA."""
        lineas = []
        
        # Patrón: CODIGO DESCRIPCION(termina en año) UNIDADES PRECIO IMPORTE
        patron = re.compile(
            r'(\d{9})\s+'                      # Código (9 dígitos)
            r'([A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ0-9\s.,]+?\d{4})'  # Descripción (termina en año)
            r'\s+(\d+)\s+'                      # Unidades
            r'([\d,.]+)\s+'                     # Precio
            r'([\d,.]+)'                        # Importe
        )
        
        for match in patron.finditer(texto):
            codigo = match.group(1)
            descripcion = match.group(2).strip()
            cantidad = float(match.group(3))
            precio = self._convertir_europeo(match.group(4))
            importe = self._convertir_europeo(match.group(5))
            
            # Limpiar descripción
            descripcion = re.sub(r'\s+\d{4}\s*$', '', descripcion).strip()
            
            if importe > 0:
                lineas.append({
                    'codigo': codigo,
                    'articulo': descripcion,
                    'cantidad': cantidad,
                    'precio_ud': precio,
                    'iva': 21,
                    'base': round(importe, 2),
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
        m = re.search(r'IMPORTE\s+FACTURA:?\s*([\d,.]+)\s*EUR', texto, re.IGNORECASE)
        if m:
            return self._convertir_europeo(m.group(1))
        return None
    
    def extraer_fecha(self, texto: str) -> Optional[str]:
        """Extrae fecha de la factura."""
        m = re.search(r'Fecha\s+factura:?\s*(\d{2}/\d{2}/\d{4})', texto)
        if m:
            return m.group(1)
        return None
    
    def extraer_referencia(self, texto: str) -> Optional[str]:
        """Extrae número de factura."""
        m = re.search(r'N[uú]mero\s+factura:?\s*([\d\-]+)', texto)
        if m:
            return m.group(1)
        return None
