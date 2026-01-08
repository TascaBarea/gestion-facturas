# -*- coding: utf-8 -*-
"""
Extractor para EL CARRASCAL (Jose Luis Sanchez Martin)

Conservas artesanas de Extremadura
CIF: REDACTED_DNI
IBAN: REDACTED_IBAN

Formato factura (PDF digital):
- Lineas: Cantidad Codigo Articulo Precio IVA Subtotal
- Ejemplo: 6,000 00046 CAJA PIQUILLOS BOTES CRISTAL TROZOS 45,000 10,00 270,000

IVA: 10% (conservas)
Categorizacion: Por diccionario (multiples categorias)

Creado: 04/01/2026
"""
from extractores.base import ExtractorBase
from extractores import registrar
from typing import List, Dict, Optional
import re


@registrar('EL CARRASCAL', 'CARRASCAL', 'JOSE LUIS SANCHEZ', 'JOSE LUIS SANCHEZ MARTIN', 
           'JOSE LUIS SANCHEZ EL CARRASCAL', 'J.L. SANCHEZ', 'JL SANCHEZ')
class ExtractorElCarrascal(ExtractorBase):
    """Extractor para facturas de EL CARRASCAL."""

    nombre = 'EL CARRASCAL'
    cif = 'REDACTED_DNI'
    iban = 'REDACTED_IBAN'
    metodo_pdf = 'pdfplumber'

    def extraer_lineas(self, texto: str) -> List[Dict]:
        """
        Extrae lineas de productos.

        Formato:
        6,000 00046 CAJA PIQUILLOS BOTES CRISTAL TROZOS 45,000 10,00 270,000
        """
        lineas = []

        # Patron: Cantidad Codigo Articulo Precio IVA Subtotal
        patron = re.compile(
            r'(\d+,\d{3})\s+'          # Cantidad (3 decimales)
            r'(\d{5})\s+'              # Codigo (5 digitos)
            r'(.+?)\s+'                # Articulo
            r'(\d+,\d{3})\s+'          # Precio
            r'(\d+,\d{2})\s+'          # IVA %
            r'(\d+,\d{3})'             # Subtotal (base)
        )

        for match in patron.finditer(texto):
            cantidad = self._convertir_europeo(match.group(1))
            codigo = match.group(2)
            articulo = match.group(3).strip()
            precio = self._convertir_europeo(match.group(4))
            iva = int(self._convertir_europeo(match.group(5)))
            base = self._convertir_europeo(match.group(6))

            # Ignorar lineas de LOTE
            if 'LOTE' in articulo.upper():
                continue

            # Ignorar lineas con cantidad 0
            if cantidad == 0:
                continue

            if base > 0:
                lineas.append({
                    'codigo': codigo,
                    'articulo': articulo,
                    'cantidad': round(cantidad, 3),
                    'precio_ud': round(precio, 2),
                    'iva': iva if iva > 0 else 10,
                    'base': round(base, 2)
                })

        return lineas

    def _convertir_europeo(self, texto: str) -> float:
        """Convierte formato europeo (1.234,56) a float."""
        if not texto:
            return 0.0
        texto = texto.strip()
        texto = texto.replace('.', '').replace(',', '.')
        try:
            return float(texto)
        except:
            return 0.0

    def extraer_total(self, texto: str) -> Optional[float]:
        """Extrae total de la factura."""
        patron = re.search(r'TOTAL\s+FACTURA\s*[\n\s]*(\d+[.,]\d+)', texto, re.IGNORECASE)
        if patron:
            return self._convertir_europeo(patron.group(1))
        return None

    def extraer_fecha(self, texto: str) -> Optional[str]:
        """Extrae fecha de la factura."""
        patron = re.search(r'(\d{2}/\d{2}/\d{4})', texto)
        if patron:
            return patron.group(1)
        return None

    def extraer_referencia(self, texto: str) -> Optional[str]:
        """Extrae numero de factura."""
        patron = re.search(r'^(A/\d+)', texto, re.MULTILINE)
        if patron:
            return patron.group(1)
        return None
