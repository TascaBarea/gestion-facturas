"""
Extractor para MRM (Industrias Cárnicas MRM-2, S.A.U)

Productos cárnicos: salmón ahumado, patés, mousses, foie gras.
NIF: A80280845
IVA: 10% (reducido)
Categoría: Buscar en diccionario

Formato factura:
 2,00 1,304 377 - SALMON AHUMADO P 37,650 37,650 49,100
        PRECOR. 600 A 800 C/EST

Base Imponible TOTAL : 49,10
10,00 % IVA Reducido sobre 49,10 4,910

Creado: 26/12/2025
"""
from extractores.base import ExtractorBase
from extractores import registrar
from typing import List, Dict, Optional
import re


@registrar('MRM', 'MRM-2', 'MRM 2', 'INDUSTRIAS CARNICAS MRM', 'INDUSTRIAS CÁRNICAS MRM')
class ExtractorMRM(ExtractorBase):
    """Extractor para facturas de MRM."""
    
    nombre = 'MRM'
    cif = 'A80280845'
    metodo_pdf = 'pdfplumber'
    usa_diccionario = True
    
    def extraer_lineas(self, texto: str) -> List[Dict]:
        """Extrae líneas de productos de MRM."""
        lineas = []
        
        # Patrón para líneas de producto MRM
        # Formato: CANT PESO COD - DESCRIPCION U/P PRECIO PRECIO IMPORTE
        # Ejemplo: 2,00 1,304 377 - SALMON AHUMADO P 37,650 37,650 49,100
        patron = re.compile(
            r'(\d+[,.]?\d*)\s+'           # Cantidad (puede ser 2,00 o 6,00)
            r'[\d,.]+'                     # Peso (ignorar)
            r'\s+(\d+)\s+-\s+'             # Código
            r'([A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ0-9\s.,]+?)'  # Descripción
            r'\s+[UP]\s+'                  # U o P (unidad/peso)
            r'[\d,.]+\s+'                  # Precio unitario
            r'[\d,.]+\s+'                  # Precio (repetido)
            r'([\d,.]+)'                   # Importe total
        )
        
        for match in patron.finditer(texto):
            cantidad_str = match.group(1).replace(',', '.')
            codigo = match.group(2)
            descripcion = match.group(3).strip()
            importe_str = match.group(4)
            
            cantidad = float(cantidad_str)
            base = self._convertir_europeo(importe_str)
            
            # Limpiar descripción (quitar líneas adicionales como "PRECOR...")
            descripcion = re.sub(r'\s+', ' ', descripcion).strip()
            # Quitar sufijos como "200" o "grs"
            descripcion = re.sub(r'\s+\d+\s*$', '', descripcion).strip()
            
            if base > 0:
                lineas.append({
                    'codigo': codigo,
                    'articulo': descripcion,
                    'cantidad': cantidad,
                    'precio_ud': round(base / cantidad, 4) if cantidad > 0 else base,
                    'iva': 10,
                    'base': round(base, 2),
                    'categoria': ''  # Se asignará por diccionario
                })
        
        return lineas
    
    def _convertir_europeo(self, texto: str) -> float:
        """Convierte formato europeo a float."""
        if not texto:
            return 0.0
        texto = texto.strip()
        # MRM usa punto como separador de miles y coma decimal
        # Pero en este caso parece usar coma decimal
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
        # "Importe Líquido : 54,01 €"
        m = re.search(r'Importe\s+L[ií]quido\s*:\s*([\d.,]+)\s*€', texto, re.IGNORECASE)
        if m:
            return self._convertir_europeo(m.group(1))
        return None
    
    def extraer_fecha(self, texto: str) -> Optional[str]:
        """Extrae fecha de la factura."""
        # "27/11/2025" después de ALBARÁN / FACTURA
        m = re.search(r'ALBAR[AÁ]N\s*/\s*FACTURA\s+[\d\-]+\s+(\d{2}/\d{2}/\d{4})', texto)
        if m:
            return m.group(1)
        return None
    
    def extraer_referencia(self, texto: str) -> Optional[str]:
        """Extrae número de factura."""
        # "ALBARÁN / FACTURA 1-2025 -54.667"
        m = re.search(r'ALBAR[AÁ]N\s*/\s*FACTURA\s+([\d\-]+\s*[\-\d.]+)', texto)
        if m:
            return m.group(1).strip()
        return None
