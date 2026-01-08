"""
Extractor para CONSERVAS LA ALACENA, S.L.U

Conservas gourmet de Almansa (Albacete).
CIF: B02488054

Formato factura (pdfplumber):
Cantidad  Lote      Artículo                              Precio  IVA    Subtotal
12,00     2L041 25  POLLITO PICANTON EN ESCABECHE LATA    4,85    10,00  58,20
12,00     A240928952 PATE DE PERDIZ                       1,90    10,00  22,80

IVA: 10% (conservas alimenticias)
Sin categoria fija - se busca en diccionario

CAMBIOS v5.14 (07/01/2026):
- FIX: Soporte para lotes largos sin espacio (A240928952)
- FIX: Deteccion de descuento 100% (base = 0)
- FIX: Ignorar lineas de Subtotal del PDF
- FIX: Sin categoria fija (antes tenia CONSERVAS MONTAÑA por error)

Creado: 26/12/2025
Actualizado: 07/01/2026
"""
from extractores.base import ExtractorBase
from extractores import registrar
from typing import List, Dict, Optional
import re


@registrar('LA ALACENA', 'CONSERVAS LA ALACENA', 'ALACENA')
class ExtractorLaAlacena(ExtractorBase):
    """Extractor para facturas de CONSERVAS LA ALACENA."""
    
    nombre = 'LA ALACENA'
    cif = 'B02488054'
    iban = ''  # Pago anticipado transferencia
    metodo_pdf = 'pdfplumber'
    # Sin categoria_fija - se busca en diccionario
    
    def extraer_lineas(self, texto: str) -> List[Dict]:
        """
        Extrae lineas de productos.
        
        Formatos:
        - Normal: "12,00 2L041 25 POLLITO PICANTON EN ESCABECHE LATA 4,85 10,00 58,20"
        - Lote largo: "12,00 A240928952 PATE DE PERDIZ 1,90 10,00 22,80"
        - Con descuento 100%: "3,00 1L021 25 CARRILLADA DE CERDO EN SALSA 7,05 100,00 10,00"
        """
        lineas = []
        
        for linea in texto.split('\n'):
            linea = linea.strip()
            if not linea:
                continue
            
            # Ignorar cabeceras, totales y lineas no relevantes
            if self._es_linea_ignorable(linea):
                continue
            
            # Intentar extraer producto
            producto = self._extraer_producto(linea)
            if producto:
                lineas.append(producto)
        
        return lineas
    
    def _es_linea_ignorable(self, linea: str) -> bool:
        """Determina si una linea debe ignorarse."""
        linea_upper = linea.upper()
        
        # Palabras clave a ignorar
        ignorar = [
            'CANTIDAD', 'LOTE', 'ARTÍCULO', 'ARTICULO',
            'PRECIO', 'SUBTOTAL', 'DESCRIPCIÓN', 'DESCRIPCION',
            'CONSERVAS LA ALACENA', 'FACTURA', 'NÚMERO', 'NUMERO',
            'FECHA', 'REFERENCIA', 'TASCA BAREA', 'LUGAR DE ENTREGA',
            'ALBARÁN', 'ALBARAN', 'DESCUENTO', 'DTO',
            'BASE IMPONIBLE', 'IMPORTE IVA', 'TOTAL FACTURA',
            'FORMA DE PAGO', 'VENCIMIENTOS', 'TRANS.', 'PAGO',
            'C.I.F', 'CIF', 'PANADEROS', 'ALMANSA', 'CLIENTE',
            'DIRECCIÓN', 'DIRECCION', 'TELEFONO', 'EMAIL',
            'PEDIDO', 'OBSERVACIONES', 'NOTA'
        ]
        
        # Linea de subtotal parcial (ej: "144,00 Subtotal 926,64")
        if 'SUBTOTAL' in linea_upper:
            return True
        
        # Linea de totales con simbolo euro o porcentaje
        if re.match(r'^\d+[.,]\d{2}\s*[€%]', linea):
            return True
        
        # Cabeceras y otras lineas
        for palabra in ignorar:
            if palabra in linea_upper:
                return True
        
        return False
    
    def _extraer_producto(self, linea: str) -> Optional[Dict]:
        """
        Extrae datos de producto de una linea.
        
        Retorna None si no es una linea de producto valida.
        """
        # Patron 1: Lote con espacio (2L041 25)
        # Formato: CANTIDAD LOTE DESCRIPCION PRECIO [DTO] IVA [SUBTOTAL]
        match1 = re.match(
            r'^(\d+[.,]\d{2})\s+'                    # Cantidad
            r'(\d?[A-Z]\d+\s+\d+)\s+'                # Lote tipo "2L041 25"
            r'(.+?)\s+'                              # Descripcion
            r'(\d+[.,]\d{2})\s+'                     # Precio
            r'(\d+[.,]\d{2})\s*'                     # Campo5 (dto o iva)
            r'(\d+[.,]\d{2})?$',                     # Campo6 opcional
            linea
        )
        
        if match1:
            return self._procesar_match(match1)
        
        # Patron 2: Lote largo sin espacio (A240928952)
        match2 = re.match(
            r'^(\d+[.,]\d{2})\s+'                    # Cantidad
            r'([A-Z]\d{6,12})\s+'                    # Lote tipo "A240928952"
            r'(.+?)\s+'                              # Descripcion
            r'(\d+[.,]\d{2})\s+'                     # Precio
            r'(\d+[.,]\d{2})\s*'                     # Campo5
            r'(\d+[.,]\d{2})?$',                     # Campo6 opcional
            linea
        )
        
        if match2:
            return self._procesar_match(match2)
        
        return None
    
    def _procesar_match(self, match) -> Dict:
        """Procesa un match de regex y devuelve el diccionario de producto."""
        cantidad = self._convertir_europeo(match.group(1))
        lote = match.group(2)
        descripcion = match.group(3).strip()
        precio = self._convertir_europeo(match.group(4))
        campo5 = self._convertir_europeo(match.group(5))
        campo6 = self._convertir_europeo(match.group(6)) if match.group(6) else None
        
        # Determinar si hay descuento
        # Si campo5 > 20 → es descuento %, campo6 es IVA
        # Si campo5 <= 20 → campo5 es IVA, campo6 es subtotal
        if campo5 > 20:
            # Hay descuento (ej: 100,00 = 100% descuento)
            dto_pct = campo5
            iva = int(campo6) if campo6 and campo6 <= 21 else 10
            base = round(cantidad * precio * (1 - dto_pct / 100), 2)
        else:
            # No hay descuento
            iva = int(campo5) if campo5 <= 21 else 10
            base = campo6 if campo6 else round(cantidad * precio, 2)
        
        # Extraer codigo del lote
        codigo = lote.split()[0] if ' ' in lote else lote
        
        return {
            'codigo': codigo,
            'articulo': descripcion[:50],
            'cantidad': int(cantidad) if cantidad == int(cantidad) else cantidad,
            'precio_ud': round(precio, 2),
            'iva': iva if iva in [4, 10, 21] else 10,
            'base': round(base, 2)
        }
    
    def _convertir_europeo(self, texto) -> float:
        """Convierte formato europeo a float."""
        if texto is None:
            return 0.0
        if isinstance(texto, (int, float)):
            return float(texto)
        texto = str(texto).strip()
        if not texto:
            return 0.0
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
        # Formato: "TOTAL FACTURA 527,67 €"
        m = re.search(r'TOTAL\s*FACTURA\s*(\d+[.,]\d{2})\s*€?', texto, re.IGNORECASE)
        if m:
            return self._convertir_europeo(m.group(1))
        
        return None
    
    def extraer_fecha(self, texto: str) -> Optional[str]:
        """Extrae fecha de la factura."""
        # Formato: "Fecha 07/10/2025"
        m = re.search(r'Fecha\s+(\d{2})/(\d{2})/(\d{4})', texto)
        if m:
            return f"{m.group(1)}/{m.group(2)}/{m.group(3)}"
        
        return None
    
    def extraer_numero_factura(self, texto: str) -> Optional[str]:
        """Extrae numero de factura."""
        # Buscar patron de referencia
        m = re.search(r'(?:Ref|Referencia|Nº|Numero)[:\s]*([A-Z0-9/-]+)', texto, re.IGNORECASE)
        return m.group(1) if m else None
    
    extraer_referencia = extraer_numero_factura
