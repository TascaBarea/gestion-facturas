"""
Extractor para SILVA CORDERO (Quesos de Acehuche)

Queseria tradicional de Extremadura
CIF: B09861535
IBAN: REDACTED_IBAN (BBVA)

Productos (IVA 4% - quesos):
- D.O.P Queso de Acehuche
- Mini pasta dura
- Queso sobado con manteca iberica
- Queso la cabra azul

IMPORTANTE: Los portes (IVA 21%) se PRORRATEAN entre los productos.
No se crea linea separada de portes.

Categoria: QUESO PARA TABLA

CAMBIOS v5.14 (07/01/2026):
- FIX: Patron flexible para codigos con puntos (D.O.P) y pegados (QUESOAZUL)
- FIX: Lotes de 6-7 digitos (antes solo 6)
- FIX: Prorrateo de portes entre productos (antes linea separada)
- FIX: Limpieza de descripcion (quitar D.O.P duplicado)

Creado: 30/12/2025
Actualizado: 07/01/2026
"""
from extractores.base import ExtractorBase
from extractores import registrar
from typing import List, Dict, Optional
import re


@registrar('SILVA CORDERO', 'QUESOS SILVA CORDERO', 'QUESOS DE ACEHUCHE',
           'SILVA', 'CORDERO')
class ExtractorSilvaCordero(ExtractorBase):
    """Extractor para facturas de SILVA CORDERO."""
    
    nombre = 'SILVA CORDERO'
    cif = 'B09861535'
    iban = 'REDACTED_IBAN'
    metodo_pdf = 'pdfplumber'
    categoria_fija = 'QUESO PARA TABLA'
    
    def extraer_lineas(self, texto: str) -> List[Dict]:
        """
        Extrae lineas de producto con portes prorrateados.
        
        Formato productos:
        CODIGO DESCRIPCION LOTE CADUC CAJAS PIEZAS CANTIDAD PRECIO DTO IMPORTE
        Ej: 0006 MINI PASTA DURA 250717 20/09/26 1 6 3,360 18,900000E/kg. 0,00 63,50
        
        Casos especiales:
        - D.O.P D.O.P QUESO DE ACEHUCHE... (codigo con puntos)
        - QUESOAZULQUESO LA CABRA AZUL... (codigo pegado a descripcion)
        - MINI DOP D.O.P MINI QUESO... (DOP en descripcion)
        
        Los PORTES se prorratean entre productos, NO se añaden como linea.
        """
        lineas = []
        
        # Patron flexible: captura todo antes del lote
        # Lote puede ser 6 o 7 digitos
        patron_producto = re.compile(
            r'^(.+?)\s+'                           # Todo antes del lote (codigo + descripcion)
            r'(\d{6,7})\s+'                        # Lote (6-7 digitos)
            r'(\d{2}/\d{2}/\d{2})\s+'              # Fecha caducidad
            r'(\d+)\s+(\d+)\s+'                    # Cajas + Piezas
            r'([\d,]+)\s+'                         # Cantidad (kg)
            r'([\d,]+)(?:E|€)/kg\.\s+'             # Precio/kg
            r'([\d,]+)\s+'                         # Descuento
            r'([\d,]+)$',                          # Importe
            re.MULTILINE | re.IGNORECASE
        )
        
        productos_raw = []
        
        for match in patron_producto.finditer(texto):
            texto_inicio = match.group(1).strip()
            cantidad_kg = float(match.group(6).replace(',', '.'))
            importe = float(match.group(9).replace(',', '.'))
            
            # Separar codigo de descripcion
            codigo, descripcion = self._separar_codigo_descripcion(texto_inicio)
            
            productos_raw.append({
                'codigo': codigo,
                'articulo': descripcion[:50],
                'cantidad': cantidad_kg,
                'precio_ud': round(importe / cantidad_kg, 4) if cantidad_kg > 0 else importe,
                'iva': 4,  # Quesos IVA reducido
                'base': importe,
                'categoria': self.categoria_fija
            })
        
        lineas = productos_raw
        
        # Extraer PORTES como línea separada
        # main.py detectará esta línea y la prorrateará automáticamente
        # usando la función prorratear_portes() que convierte IVA correctamente
        m_portes = re.search(r'PORTES\s+([\d,]+)', texto)
        if m_portes:
            importe_porte = float(m_portes.group(1).replace(',', '.'))
            if importe_porte > 0:
                lineas.append({
                    'codigo': 'PORTE',
                    'articulo': 'PORTES',  # main.py detecta esta palabra
                    'cantidad': 1,
                    'precio_ud': importe_porte,
                    'iva': 21,  # Portes IVA general
                    'base': importe_porte,
                    'categoria': 'TRANSPORTE'
                })
        
        # Si no encontro productos, intentar patron alternativo
        if not lineas:
            lineas = self._extraer_patron_flexible(texto)
        
        return lineas
    
    def _separar_codigo_descripcion(self, texto_inicio: str) -> tuple:
        """
        Separa codigo de descripcion en el texto inicial.
        
        Casos:
        - "BLACK01 CABRA CON CARBON..." -> ("BLACK01", "CABRA CON CARBON...")
        - "QUESOAZULQUESO LA CABRA..." -> ("QUESOAZUL", "QUESO LA CABRA...")
        - "MINI DOP D.O.P MINI QUESO..." -> ("MINI", "MINI QUESO...")
        - "D.O.P D.O.P QUESO DE ACEHUCHE..." -> ("D.O.P", "QUESO DE ACEHUCHE...")
        """
        codigo = ''
        descripcion = texto_inicio
        
        # Caso 1: Codigo pegado a QUESO (ej: QUESOAZULQUESO LA CABRA)
        m_pegado = re.match(r'^([A-Z]+\d*)(QUESO.+)$', texto_inicio, re.IGNORECASE)
        if m_pegado:
            codigo = m_pegado.group(1)
            descripcion = m_pegado.group(2)
        else:
            # Caso 2: Separacion normal por espacio
            m_codigo = re.match(r'^([A-Z0-9.]+)\s+(.+)$', texto_inicio)
            if m_codigo:
                codigo = m_codigo.group(1)
                descripcion = m_codigo.group(2)
                
                # Limpiar "DOP" o "D.O.P" si sigue en descripcion
                if descripcion.upper().startswith('DOP '):
                    descripcion = descripcion[4:].strip()
                elif descripcion.upper().startswith('D.O.P '):
                    descripcion = descripcion[6:].strip()
        
        # Limpiar D.O.P duplicado al inicio de descripcion
        descripcion = re.sub(r'^D\.?O\.?P\.?\s*D\.?O\.?P\.?\s*', '', descripcion, flags=re.IGNORECASE)
        descripcion = re.sub(r'^D\.?O\.?P\.?\s+', '', descripcion, flags=re.IGNORECASE)
        
        return codigo, descripcion.strip()
    
    def _extraer_patron_flexible(self, texto: str) -> List[Dict]:
        """Patron alternativo si el principal no encuentra nada."""
        lineas = []
        
        # Buscar lineas que terminen en importe tipo "0,00 XX,XX"
        patron_flex = re.compile(
            r'^(.+?)\s+\d{6,7}\s+\d{2}/\d{2}/\d{2}\s+.+?\s+0,00\s+([\d,]+)$',
            re.MULTILINE
        )
        
        for match in patron_flex.finditer(texto):
            texto_inicio = match.group(1).strip()
            importe = float(match.group(2).replace(',', '.'))
            
            codigo, descripcion = self._separar_codigo_descripcion(texto_inicio)
            
            lineas.append({
                'codigo': codigo,
                'articulo': descripcion[:50],
                'cantidad': 1,
                'precio_ud': importe,
                'iva': 4,
                'base': importe,
                'categoria': self.categoria_fija
            })
        
        return lineas
    
    def extraer_total(self, texto: str) -> Optional[float]:
        """Extrae TOTAL FACTURA del PDF."""
        # Buscar "TOTAL FACTURA XXX,XX"
        m = re.search(r'TOTAL\s+FACTURA\s+([\d.,]+)\s*[E€]?', texto, re.IGNORECASE)
        if m:
            return self._convertir_europeo(m.group(1))
        
        # Buscar ultimo importe con euro
        matches = re.findall(r'([\d.,]+)\s*€', texto)
        if matches:
            return self._convertir_europeo(matches[-1])
        
        return None
    
    def _convertir_europeo(self, texto: str) -> float:
        """Convierte formato europeo a float."""
        if not texto:
            return 0.0
        texto = re.sub(r'[^\d,.]', '', str(texto))
        if '.' in texto and ',' in texto:
            texto = texto.replace('.', '').replace(',', '.')
        elif ',' in texto:
            texto = texto.replace(',', '.')
        try:
            return float(texto)
        except:
            return 0.0
    
    def extraer_fecha(self, texto: str) -> Optional[str]:
        """Extrae fecha de la factura."""
        m = re.search(r'Fecha\s+(\d{2}/\d{2}/\d{4})', texto)
        return m.group(1) if m else None
    
    def extraer_numero_factura(self, texto: str) -> Optional[str]:
        """Extrae numero de factura."""
        m = re.search(r'(F25/\d+)', texto)
        return m.group(1) if m else None
    
    extraer_referencia = extraer_numero_factura
