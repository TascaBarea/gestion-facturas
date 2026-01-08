# -*- coding: utf-8 -*-
"""
Extractor para WELLDONE LÁTICOS (Rodolfo del Río Lameyer)
Quesos artesanos de Sevilla.

Autor: Claude (ParsearFacturas v5.0)
Fecha: 27/12/2025
Corregido: 28/12/2025 - Integración con sistema

PECULIARIDADES:
- IVA 4% para quesos
- Portes con IVA 21% - deben prorratearse entre productos
- El TOTAL de línea incluye IVA (cantidad × precio_con_iva)
- La BASE se calcula como cantidad × precio_unidad
"""
from extractores.base import ExtractorBase
from extractores import registrar
import re
from typing import List, Dict, Optional
import pdfplumber


@registrar('WELLDONE', 'WELLDONE LACTICOS', 'WELLDONE LÁTICOS', 
           'RODOLFO DEL RIO', 'RODOLFO DEL RÍO', 'RODOLFO DEL RIO LAMEYER')
class ExtractorWelldone(ExtractorBase):
    """
    Extractor para facturas de WELLDONE LÁTICOS.
    
    Formato línea:
    CÓDIGO DESCRIPCIÓN LOTE CANTIDAD PRECIO_UNIDAD PRECIO_CON_IVA TOTAL
    QA0006 ALJARAFE wD140925 4,00 7,37 7,6648 30,66
    """
    
    nombre = 'WELLDONE LACTICOS'
    nombre_fiscal = 'Rodolfo del Rio Lameyer'
    cif = '27292516A'
    iban = 'ES55 2100 5789 1202 0015 7915'
    metodo_pdf = 'pdfplumber'
    categoria_fija = 'QUESOS'
    iva_quesos = 4
    iva_portes = 21
    
    def extraer_texto(self, pdf_path: str) -> str:
        """Extrae texto del PDF usando pdfplumber."""
        texto_completo = []
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    texto = page.extract_text()
                    if texto:
                        texto_completo.append(texto)
        except Exception as e:
            print(f"Error extrayendo texto: {e}")
        return '\n'.join(texto_completo)
    
    def extraer_lineas(self, texto: str) -> List[Dict]:
        """
        Extrae líneas de productos.
        
        Formato:
        CÓDIGO DESCRIPCIÓN LOTE CANTIDAD PRECIO_UNIDAD PRECIO_CON_IVA TOTAL
        QA0006 ALJARAFE wD140925 4,00 7,37 7,6648 30,66
        
        IMPORTANTE: 
        - Base = cantidad × precio_unidad
        - Los portes NO se prorratean - se tratan por separado con IVA 21%
        """
        lineas = []
        
        # Patrón para productos (código empieza con Q)
        patron_producto = re.compile(
            r'^(Q[A-Z]\d{4})\s+'           # Código (QA0006, QF0003, etc.)
            r'([A-ZÀ-Ü][A-ZÀ-Ü\s]+?)\s+'   # Descripción (incluye acentos)
            r'wD\d+\s+'                     # Lote (ignorar)
            r'(\d+[.,]\d+)\s+'              # Cantidad
            r'(\d+[.,]\d+)\s+'              # Precio unidad
            r'(\d+[.,]\d+)\s+'              # Precio con IVA (ignorar)
            r'(\d+[.,]\d+)',                # Total con IVA (ignorar)
            re.MULTILINE
        )
        
        # Extraer productos
        for match in patron_producto.finditer(texto):
            codigo = match.group(1)
            descripcion = match.group(2).strip()
            cantidad = self._convertir_europeo(match.group(3))
            precio_ud = self._convertir_europeo(match.group(4))
            
            # Calcular base = cantidad × precio_unidad
            base = round(cantidad * precio_ud, 2)
            
            if base < 0.01 or cantidad < 0.01:
                continue
            
            lineas.append({
                'codigo': codigo,
                'articulo': descripcion[:50],
                'cantidad': cantidad,
                'precio_ud': precio_ud,
                'iva': self.iva_quesos,
                'base': base,
                'categoria': self.categoria_fija
            })
        
        return lineas
    
    def extraer_numero_factura(self, texto: str) -> Optional[str]:
        """Extrae número de factura."""
        patron = re.search(r'Factura\s+\d\s+(\d{6})', texto)
        if patron:
            return patron.group(1)
        return None
    
    def extraer_fecha(self, texto: str) -> Optional[str]:
        """Extrae fecha de factura."""
        patron = re.search(r'Factura\s+\d\s+\d{6}\s+(\d{2}/\d{2}/\d{4})', texto)
        if patron:
            return patron.group(1)
        return None
    
    def extraer_total(self, texto: str) -> Optional[float]:
        """Extrae total de la factura."""
        patron = re.search(r'TOTAL:\s*(\d+[.,]\d{2})', texto)
        if patron:
            return self._convertir_europeo(patron.group(1))
        return None
    
    def extraer_base_imponible(self, texto: str) -> Dict[int, float]:
        """
        Extrae bases imponibles por tipo de IVA.
        Retorna dict {iva: base}
        
        Formato en factura SIN portes:
        21,00
        10,00
        4,00 181,31 7,25
        
        Formato en factura CON portes:
        21,00 11,96 11,96 2,51
        10,00
        4,00 142,90 5,72
        """
        bases = {}
        
        # Procesar línea por línea
        for linea in texto.split('\n'):
            linea = linea.strip()
            
            # Buscar base al 4%
            match_4 = re.match(r'^4[.,]00\s+(\d+[.,]\d+)\s+\d+[.,]\d+', linea)
            if match_4:
                bases[4] = self._convertir_europeo(match_4.group(1))
            
            # Buscar base al 21% (solo si hay 3 valores después)
            match_21 = re.match(r'^21[.,]00\s+(\d+[.,]\d+)\s+(\d+[.,]\d+)\s+(\d+[.,]\d+)', linea)
            if match_21:
                # El segundo valor es la base de portes
                bases[21] = self._convertir_europeo(match_21.group(2))
        
        return bases
    
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
