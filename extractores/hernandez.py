"""
Extractor para HERNÁNDEZ SUMINISTROS HOSTELEROS.
CIF: B78987138

Proveedor de menaje/hostelería. Las facturas tienen el IBAN en una línea
que puede confundirse con el total si no se tiene cuidado.

IMPORTANTE: El IBAN aparece como "TRANSFERENCIA ES49 0049 2662 97 2614316514"
y el número de cuenta (2614316514) NO debe confundirse con el total.

El total real aparece en la tabla de impuestos como "TOTAL FACTURA".

Creado: 01/01/2026
Corregido: 04/01/2026 - Bug filtro subcadenas
"""
from extractores.base import ExtractorBase
from extractores import registrar
from typing import List, Dict, Optional
import re


@registrar('HERNANDEZ', 'HERNÁNDEZ', 'HERNANDEZ SUMINISTROS', 'HERNÁNDEZ SUMINISTROS',
           'HERNANDEZ SUMINISTROS HOSTELEROS', 'HERNÁNDEZ SUMINISTROS HOSTELEROS',
           'HERNANDEZ SUM HOSTELEROS')
class ExtractorHernandez(ExtractorBase):
    """Extractor para facturas de HERNÁNDEZ SUMINISTROS HOSTELEROS."""
    
    nombre = 'HERNANDEZ SUMINISTROS'
    cif = 'B78987138'
    iban = 'ES49 0049 2662 97 2614316514'
    metodo_pdf = 'pdfplumber'
    
    def _convertir_importe(self, texto: str) -> float:
        """Convierte texto a float (formato europeo)."""
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
    
    def extraer_total(self, texto: str) -> Optional[float]:
        """
        Extrae total de la factura.
        CUIDADO: No confundir con el IBAN que aparece como número largo.
        
        Estructura típica:
        - Línea cabecera: "IMPORTE BRUTO IVA IMPORTE IVA TOTAL IMPUESTOS TOTAL FACTURA"
        - Línea valores:  "86,16 21 18,09 104,25 €"
        El total es el ÚLTIMO número antes de €
        """
        # Método 1: Buscar línea con € y extraer el número justo antes
        for linea in texto.split('\n'):
            if '€' in linea and 'IBAN' not in linea.upper() and 'TRANSFERENCIA' not in linea.upper():
                # Buscar el último número antes de €
                m = re.search(r'(\d+[.,]\d{2})\s*€', linea)
                if m:
                    total = self._convertir_importe(m.group(1))
                    # Validación: total razonable (entre 1€ y 50,000€)
                    if 1 < total < 50000:
                        return total
        
        # Método 2: Buscar línea después de "TOTAL FACTURA" en cabecera
        lineas = texto.split('\n')
        for i, linea in enumerate(lineas):
            if 'TOTAL FACTURA' in linea.upper() and i + 1 < len(lineas):
                # La siguiente línea tiene los valores
                siguiente = lineas[i + 1]
                numeros = re.findall(r'(\d+[.,]\d{2})', siguiente)
                if numeros:
                    # El último número es el total
                    total = self._convertir_importe(numeros[-1])
                    if 1 < total < 50000:
                        return total
        
        # Método 3: Buscar "TOTAL FACTURA" en la misma línea que el valor
        m = re.search(r'TOTAL\s+FACTURA[^\d]*(\d+[.,]\d{2})', texto, re.IGNORECASE)
        if m:
            total = self._convertir_importe(m.group(1))
            if 1 < total < 50000:
                return total
        
        return None
    
    def extraer_lineas(self, texto: str) -> List[Dict]:
        """Extrae líneas de productos de la factura."""
        lineas = []
        
        # Patrón para líneas de producto:
        # CODIGO DESCRIPCIÓN UNIDADES PVP IMPORTE
        # Ej: "ACVASO PINTA VASO AGUA DE 36 CL.PINTA 12 0,79 9,48"
        patron = re.compile(
            r'^([A-Z]{2}[A-Z0-9\s]+?)\s+'  # Código
            r'(.+?)\s+'                      # Descripción
            r'(\d+)\s+'                      # Unidades
            r'(\d+[.,]\d{2})\s+'            # PVP
            r'(\d+[.,]\d{2})$',             # Importe
            re.MULTILINE
        )
        
        for m in patron.finditer(texto):
            codigo, desc, uds, pvp, importe = m.groups()
            lineas.append({
                'articulo': desc.strip()[:50],
                'codigo': codigo.strip(),
                'cantidad': int(uds),
                'precio_ud': self._convertir_importe(pvp),
                'base': self._convertir_importe(importe),
                'iva': 21,  # Por defecto menaje es 21%
                'categoria': 'MENAJE'
            })
        
        # Si no encontró con el patrón complejo, intentar patrón simple
        if not lineas:
            for linea in texto.split('\n'):
                # Buscar líneas con formato: DESCRIPCIÓN CANTIDAD PRECIO IMPORTE
                m = re.match(r'^(.{10,40}?)\s+(\d+)\s+(\d+[.,]\d{2})\s+(\d+[.,]\d{2})$', linea.strip())
                if m:
                    desc, cant, precio, importe = m.groups()
                    # Filtrar líneas que no son productos (usar palabras completas)
                    palabras = desc.upper().split()
                    if not any(x in palabras for x in ['TOTAL', 'BASE', 'IVA', 'IMPORTE', 'FACTURA']):
                        lineas.append({
                            'articulo': desc.strip()[:50],
                            'cantidad': int(cant),
                            'precio_ud': self._convertir_importe(precio),
                            'base': self._convertir_importe(importe),
                            'iva': 21,
                            'categoria': 'MENAJE'
                        })
        
        return lineas
    
    def extraer_fecha(self, texto: str) -> Optional[str]:
        """Extrae fecha de la factura."""
        # Formato: DD/MM/YYYY o DD-MM-YYYY
        m = re.search(r'FECHA\s*[:\s]*(\d{2})[/-](\d{2})[/-](\d{4})', texto, re.IGNORECASE)
        if m:
            dia, mes, año = m.groups()
            return f"{dia}-{mes}-{año}"
        
        # Formato corto: DD/MM/YY
        m2 = re.search(r'(\d{2})[/-](\d{2})[/-](\d{2})\s', texto)
        if m2:
            dia, mes, año = m2.groups()
            return f"{dia}-{mes}-{año}"
        
        return None
    
    def extraer_referencia(self, texto: str) -> Optional[str]:
        """Extrae número de factura."""
        m = re.search(r'FACTURA\s*[:\s]*([A-Z]?\d+[/-]?\d*)', texto, re.IGNORECASE)
        if m:
            return m.group(1)
        return None
