# -*- coding: utf-8 -*-
"""
Extractor para LICORES MADRUEÑO S.L.

Distribuidor de licores y vinos.
CIF: B86705126
IBAN: ES21 2100 2865 5113 0088 6738

Formato factura (con pdfplumber):
CÓDIGO DESCRIPCIÓN UNIDADES PRECIO DTO % IMPORTE
1594 FEVER-TREE 24 0,80 19,20
1764 XIC DAL FONS 12 3,60 43,20
134 J&B 1 10,15 10,15

TOTAL €: 782,33

IVA: Siempre 21% (licores)

VERSIÓN: v5.16 - 07/01/2026
- FIX: Patrón simplificado con .+? que acepta cualquier carácter (J&B)
- FIX: Soporta cantidades e importes NEGATIVOS (devoluciones)
- FIX: Extrae descuento comercial (DTO.COM.)
"""
from extractores.base import ExtractorBase
from extractores import registrar
from typing import List, Dict, Optional
import re


@registrar('LICORES MADRUEÑO', 'MADRUEÑO', 'MARIANO MADRUEÑO', 'LICORES MADRUENO', 'MADRUENO',
           'LICORES_MADRUEÑO', 'LICORES_MADRUENO')
class ExtractorMadrueño(ExtractorBase):
    """Extractor para facturas de LICORES MADRUEÑO."""
    
    nombre = 'LICORES MADRUEÑO'
    cif = 'B86705126'
    iban = 'ES21 2100 2865 5113 0088 6738'
    metodo_pdf = 'pdfplumber'
    
    def extraer_lineas(self, texto: str) -> List[Dict]:
        """
        Extrae líneas individuales de productos.
        
        Formato pdfplumber:
        1594 FEVER-TREE 24 0,80 19,20
        134 J&B 1 10,15 10,15
        
        Returns:
            Lista de diccionarios con:
            - codigo: Código del producto
            - articulo: Nombre del artículo
            - cantidad: Unidades
            - precio_ud: Precio unitario
            - iva: 21 (licores siempre)
            - base: Importe (sin IVA, ya viene así en factura)
        """
        lineas = []
        
        # Patrón mejorado: buscar líneas completas que terminen con importe
        # v5.15: Usa .+? non-greedy para descripción, soporta cualquier carácter
        # v5.16: Soporta cantidades e importes NEGATIVOS (devoluciones)
        patron_linea = re.compile(
            r'^(\d{2,5})\s+'                              # Código (2-5 dígitos)
            r'(.+?)\s+'                                    # Descripción (cualquier carácter, non-greedy)
            r'(-?\d{1,3})\s+'                             # Unidades (puede ser negativo)
            r'(\d{1,3},\d{2})\s+'                         # Precio unitario (formato europeo)
            r'(-?\d{1,3}(?:\.\d{3})*,\d{2})$'            # Importe (puede ser negativo) AL FINAL DE LÍNEA
        , re.MULTILINE)
        
        for match in patron_linea.finditer(texto):
            codigo = match.group(1)
            descripcion = match.group(2).strip()
            cantidad = int(match.group(3))  # Puede ser negativo (devolución)
            precio_str = match.group(4)
            importe_str = match.group(5)    # Puede ser negativo (devolución)
            
            # Convertir formato europeo a float
            precio_ud = self._convertir_europeo(precio_str)
            importe = self._convertir_europeo(importe_str)
            
            # Filtrar líneas de cabecera, totales o direcciones
            desc_upper = descripcion.upper()
            if any(x in desc_upper for x in [
                'DESCRIPCION', 'CÓDIGO', 'UNIDADES', 'PRECIO', 'IMPORTE',
                'TOTAL', 'BRUTO', 'SUMA', 'SIGUE', 'BASE', 'IVA', 'ALBARAN',
                'CLIENTE', 'FECHA', 'FACTURA', 'VENTA', 'MADRID', 'BARCELONA'
            ]):
                continue
            
            # Ignorar si importe muy pequeño (pero permitir negativos)
            if abs(importe) < 0.50:
                continue
            
            lineas.append({
                'codigo': codigo,
                'articulo': descripcion[:50],  # Limitar longitud
                'cantidad': cantidad,          # Mantener signo (negativo = devolución)
                'precio_ud': round(precio_ud, 2),
                'iva': 21,  # Licores siempre 21%
                'base': round(importe, 2)      # Mantener signo (negativo = devolución)
            })
        
        # Añadir descuento comercial si existe
        descuento = self.extraer_descuento(texto)
        if descuento != 0:
            lineas.append({
                'codigo': 'DTO',
                'articulo': 'DESCUENTO COMERCIAL',
                'cantidad': 1,
                'precio_ud': round(descuento, 2),
                'iva': 21,
                'base': round(descuento, 2)  # Negativo
            })
        
        return lineas
    
    def _convertir_europeo(self, texto: str) -> float:
        """
        Convierte formato europeo a float.
        
        Ejemplos:
        - '0,80' → 0.80
        - '19,20' → 19.20
        - '1.234,56' → 1234.56
        """
        if not texto:
            return 0.0
        
        texto = texto.strip()
        
        # Si tiene punto Y coma, el punto es separador de miles
        if '.' in texto and ',' in texto:
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
        
        Formatos:
        - TOTAL €: 782,33
        - 782,33 €
        - TOTAL €: 1.273,71
        """
        patrones = [
            r'TOTAL\s*€[:\s]*(\d{1,3}(?:\.\d{3})*,\d{2})',  # TOTAL €: 1.273,71
            r'TOTAL[:\s]+(\d{1,3}(?:\.\d{3})*,\d{2})\s*€',  # TOTAL: 782,33 €
            r'(\d{1,3}(?:\.\d{3})*,\d{2})\s*€\s*\n.*?DATOS\s*BANCARIOS',  # 782,33 €\nDATOS
        ]
        
        for patron in patrones:
            match = re.search(patron, texto, re.IGNORECASE | re.DOTALL)
            if match:
                return self._convertir_europeo(match.group(1))
        
        return None
    
    def extraer_fecha(self, texto: str) -> Optional[str]:
        """Extrae fecha de la factura (DD/MM/YYYY)."""
        # Buscar en cabecera: 31/05/2025
        patron = re.search(r'(\d{2}/\d{2}/\d{4})', texto)
        if patron:
            return patron.group(1)
        return None
    
    def extraer_descuento(self, texto: str) -> float:
        """
        Extrae descuento comercial de la factura.
        
        Formato: DTO.COM.: 5,55 % -70,41
        O: TOTAL CARGOS/DTOS.: -70,41
        
        Returns:
            Importe del descuento (negativo)
        """
        if not texto:
            return 0.0
        
        # Patrón 1: DTO.COM.: X,XX % -YY,YY
        patron1 = re.search(
            r'DTO\.?\s*COM\.?[:\s]+[\d,]+\s*%?\s*(-?\d+,\d{2})',
            texto, re.IGNORECASE
        )
        if patron1:
            return self._convertir_europeo(patron1.group(1))
        
        # Patrón 2: TOTAL CARGOS/DTOS.: -70,41
        patron2 = re.search(
            r'TOTAL\s+CARGOS/DTOS\.?[:\s]+(-?\d+,\d{2})',
            texto, re.IGNORECASE
        )
        if patron2:
            return self._convertir_europeo(patron2.group(1))
        
        return 0.0
    
    def extraer_referencia(self, texto: str) -> Optional[str]:
        """Extrae número de factura."""
        # Buscar NÚMERO seguido de serie y número: 02F 3803
        patron = re.search(r'NÚMERO\s*\n\s*(\d{2}[A-Z])\s+(\d+)', texto, re.IGNORECASE)
        if patron:
            return f"{patron.group(1)}-{patron.group(2)}"
        
        # Alternativa: solo el número
        patron2 = re.search(r'(\d{4,})\s*$', texto[:500], re.MULTILINE)
        if patron2:
            return patron2.group(1)
        
        return None
