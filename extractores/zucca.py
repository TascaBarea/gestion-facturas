# -*- coding: utf-8 -*-
"""
Extractor para FORMAGGIARTE SL (Quesería ZUCCA)

Quesos italianos artesanales.
CIF: B42861948
IBAN: ES05 1555 0001 2000 1157 7624

Formato factura:
CÓDIGO DESCRIPCIÓN CANTIDAD PRECIO SUBTOTAL TOTAL

Ejemplo:
00042 Burrata Individual SN 8,00 3,40 27,20 27,20

IVA por producto:
- Quesos (Burrata, Ciliegine, Scamorza, Stracciatella) → 4%
- Yogur de Oveja → 10%

Categorías:
- Quesos → QUESO PARA TABLA
- Yogur → DESPENSA
- Portes → se prorratean entre productos (no línea separada)

IMPORTANTE: 
- La columna TOTAL del PDF muestra BASE sin IVA
- El campo 'base' que devolvemos es SIN IVA
- main.py/validar_cuadre() aplica el IVA después

Creado: 02/01/2026
Actualizado: 08/01/2026 - Nombre unificado a ZUCCA + extraer_referencia
"""
from extractores.base import ExtractorBase
from extractores import registrar
from typing import List, Dict, Optional
import re
import pdfplumber


@registrar('QUESERIA ZUCCA', 'ZUCCA', 'FORMAGGIARTE', 'FORMAGGIARTE SL', 
           'ZUCCA FORMAGGIARTE', 'FORMAGGIARTE ZUCCA', 'QUESOS ZUCCA')
class ExtractorZucca(ExtractorBase):
    """Extractor para facturas de QUESERÍA ZUCCA / FORMAGGIARTE."""
    
    # v5.14: Nombre unificado a ZUCCA (antes era QUESERIA ZUCCA)
    nombre = 'ZUCCA'
    cif = 'B42861948'
    iban = 'ES0515500001200011577624'
    metodo_pdf = 'pdfplumber'
    
    # Productos con IVA 10% (el resto va al 4%)
    PRODUCTOS_IVA_10 = ['yogur', 'yogurt']
    
    # Palabras clave para detectar portes/envío
    PALABRAS_PORTES = ['envio', 'eenvio', 'seur', 'porte', 'portes', 'transporte', 'frio 13:30']
    
    # Categorías por tipo de producto
    CATEGORIA_QUESO = 'QUESO PARA TABLA'
    CATEGORIA_YOGUR = 'DESPENSA'
    
    def extraer_texto_pdfplumber(self, pdf_path: str) -> str:
        """Extrae texto del PDF."""
        texto_completo = []
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    texto = page.extract_text()
                    if texto:
                        texto_completo.append(texto)
        except Exception as e:
            pass
        return '\n'.join(texto_completo)
    
    def _es_linea_portes(self, descripcion: str) -> bool:
        """Detecta si una línea es de portes/envío."""
        desc_lower = descripcion.lower()
        return any(palabra in desc_lower for palabra in self.PALABRAS_PORTES)
    
    def _determinar_categoria(self, descripcion: str) -> str:
        """Determina la categoría según el producto."""
        desc_lower = descripcion.lower()
        if any(prod in desc_lower for prod in self.PRODUCTOS_IVA_10):
            return self.CATEGORIA_YOGUR
        return self.CATEGORIA_QUESO
    
    def _determinar_iva(self, descripcion: str) -> int:
        """Determina el IVA según el producto."""
        desc_lower = descripcion.lower()
        if any(prod in desc_lower for prod in self.PRODUCTOS_IVA_10):
            return 10
        return 4
    
    def extraer_lineas(self, texto: str) -> List[Dict]:
        """
        Extrae líneas de productos con prorrateo de portes.
        
        Formato: CÓDIGO DESCRIPCIÓN CANTIDAD PRECIO SUBTOTAL TOTAL
        
        Los portes se prorratean proporcionalmente entre los productos.
        """
        lineas_raw = []
        total_portes = 0.0
        
        # Patrón para líneas de producto
        patron = re.compile(
            r'^(\d{2,5})\s+'                        # Código (00042, 07, etc.)
            r'(.+?)\s+'                              # Descripción
            r'(\d+,\d{2})\s+'                        # Cantidad
            r'(\d+,\d{2})\s+'                        # Precio unitario
            r'(\d+,\d{2})\s+'                        # Subtotal
            r'(\d+,\d{2})$'                          # Total (BASE sin IVA)
        )
        
        for linea in texto.split('\n'):
            linea = linea.strip()
            match = patron.match(linea)
            if match:
                codigo = match.group(1)
                descripcion = match.group(2).strip()
                cantidad = self._convertir_europeo(match.group(3))
                precio = self._convertir_europeo(match.group(4))
                importe_base = self._convertir_europeo(match.group(6))
                
                # Filtrar líneas con importe muy bajo
                if importe_base < 0.50:
                    continue
                
                # Detectar si es línea de portes
                if self._es_linea_portes(descripcion):
                    total_portes += importe_base
                    continue  # No añadir como línea separada
                
                lineas_raw.append({
                    'codigo': codigo,
                    'articulo': descripcion[:50],
                    'cantidad': int(cantidad) if cantidad == int(cantidad) else round(cantidad, 2),
                    'precio_ud': round(precio, 2),
                    'iva': self._determinar_iva(descripcion),
                    'base': round(importe_base, 2),
                    'categoria': self._determinar_categoria(descripcion)
                })
        
        # Prorratear portes entre productos
        if total_portes > 0 and lineas_raw:
            suma_bases = sum(l['base'] for l in lineas_raw)
            if suma_bases > 0:
                for linea in lineas_raw:
                    # Prorratear proporcionalmente
                    proporcion = linea['base'] / suma_bases
                    incremento = round(total_portes * proporcion, 2)
                    linea['base'] = round(linea['base'] + incremento, 2)
                    # Recalcular precio unitario si cantidad > 0
                    if linea['cantidad'] > 0:
                        linea['precio_ud'] = round(linea['base'] / linea['cantidad'], 2)
        
        return lineas_raw
    
    def _convertir_europeo(self, texto: str) -> float:
        """Convierte formato europeo (1.234,56) a float."""
        if not texto:
            return 0.0
        texto = str(texto).strip()
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
        patron = re.search(r'TOTAL:\s*([\d.,]+)', texto, re.IGNORECASE)
        if patron:
            return self._convertir_europeo(patron.group(1))
        return None
    
    def extraer_fecha(self, texto: str) -> Optional[str]:
        """Extrae fecha de la factura."""
        patron = re.search(r'Factura\s+\d+\s+\d+\s+\d+\s+(\d{2}/\d{2}/\d{4})', texto)
        if patron:
            return patron.group(1)
        return None
    
    def extraer_referencia(self, texto: str) -> Optional[str]:
        """
        Extrae número de factura.
        
        v5.14: Renombrado de extraer_numero_factura a extraer_referencia
        para compatibilidad con main.py
        """
        patron = re.search(r'Factura\s+1\s+(\d+)\s+1', texto)
        if patron:
            return patron.group(1)
        return None
