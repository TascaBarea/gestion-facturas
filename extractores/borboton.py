"""
Extractor para BODEGAS BORBOTÓN

Bodega de Toledo - Vinos A Ras de Suelo.
CIF: B45851755
IBAN: REDACTED_IBAN

Formato factura (pdfplumber):
Cod.    Vino                                    Uds.  Precio   Dto%   Ud.Precio  TOTAL
ARS0184 A RAS DE SUELO COUPAGE 2021 75cl        72    7,85 €   0,00%  7,85 €     565,20 €
L.01.COU.2021
Vintage 2021
Alc.% 14,0
Promocion especial                              24   -7,85 €   0,00% -7,85 €    -188,40 €
ARS0283 A RAS DE SUELO "EL TORREJÓN" 75 cl      12    9,92 €   0,00%  9,92 €     119,04 €

IMPORTANTE: Las promociones (descuentos) vienen en línea separada y SIEMPRE
se refieren al artículo de la línea inmediatamente superior.
Se consolidan: cantidad = compradas + regaladas, importe = precio - descuento

IVA: 21%
Sin categoría fija - busca en diccionario (5 artículos)

Actualizado: 26/12/2025
"""
from extractores.base import ExtractorBase
from extractores import registrar
from typing import List, Dict, Optional
import re


@registrar('BODEGAS BORBOTON', 'BORBOTON', 'BORBOTÓN', 'BORBOTON FINCA Y BODEGA')
class ExtractorBorboton(ExtractorBase):
    """Extractor para facturas de BODEGAS BORBOTÓN."""
    
    nombre = 'BODEGAS BORBOTON'
    cif = 'B45851755'
    iban = 'REDACTED_IBAN'
    metodo_pdf = 'pdfplumber'
    
    def extraer_lineas(self, texto: str) -> List[Dict]:
        """
        Extrae líneas de productos y consolida promociones.
        
        La promoción siempre se aplica al artículo inmediatamente superior:
        - Cantidad final = cantidad comprada + cantidad promoción
        - Importe final = importe producto - importe promoción (que viene negativo)
        """
        lineas_raw = []
        
        # Patrón para productos: CODIGO DESCRIPCION UDS PRECIO € DTO% UD.PRECIO € TOTAL €
        # ARS0184 A RAS DE SUELO COUPAGE 2021 75cl 72 7,85 € 0,00 % 7,85 € 565,20 €
        patron_producto = re.compile(
            r'^([A-Z]{3}\d{4})\s+'                    # Código (ARS0184)
            r'(.+?)\s+'                               # Descripción
            r'(\d+)\s+'                               # Unidades
            r'([\d,]+)\s*€\s+'                        # Precio
            r'[\d,]+\s*%\s+'                          # Dto%
            r'[\d,]+\s*€\s+'                          # Ud. Precio
            r'([\d,]+)\s*€',                          # TOTAL
            re.MULTILINE
        )
        
        # Patrón para promociones: Promocion especial [6+3] UDS -PRECIO € DTO% -UD.PRECIO € -TOTAL €
        patron_promo = re.compile(
            r'^Promoci[oó]n\s+(?:especial\s*)?(?:\d+\+\d+)?\s*'  # "Promoción especial 6+3"
            r'(\d+)\s+'                                          # Unidades (regaladas)
            r'(-?[\d,]+)\s*€\s+'                                 # Precio (negativo)
            r'[\d,]+\s*%\s+'                                     # Dto%
            r'(-?[\d,]+)\s*€\s+'                                 # Ud. Precio
            r'(-?[\d,]+)\s*€',                                   # TOTAL (negativo)
            re.MULTILINE
        )
        
        # Primero extraemos todos los productos
        for match in patron_producto.finditer(texto):
            codigo, desc, uds, precio, total = match.groups()
            
            # Limpiar descripción (quitar lote, vintage, etc.)
            desc_limpia = desc.strip()
            desc_limpia = re.sub(r'\s+L\.\d+.*$', '', desc_limpia)
            desc_limpia = re.sub(r'\s+Vintage.*$', '', desc_limpia, flags=re.IGNORECASE)
            desc_limpia = desc_limpia.strip()
            
            lineas_raw.append({
                'tipo': 'producto',
                'codigo': codigo,
                'articulo': desc_limpia,
                'cantidad': int(uds),
                'precio_ud': self._convertir_importe(precio),
                'base': self._convertir_importe(total),
                'pos': match.start()  # Para ordenar
            })
        
        # Luego extraemos las promociones
        for match in patron_promo.finditer(texto):
            uds, precio, ud_precio, total = match.groups()
            
            lineas_raw.append({
                'tipo': 'promocion',
                'cantidad': int(uds),
                'descuento': abs(self._convertir_importe(total)),  # Valor absoluto
                'pos': match.start()
            })
        
        # Ordenar por posición en el texto
        lineas_raw.sort(key=lambda x: x['pos'])
        
        # Consolidar: cada promoción se aplica al producto inmediatamente anterior
        lineas_finales = []
        
        for i, item in enumerate(lineas_raw):
            if item['tipo'] == 'producto':
                # Buscar si la siguiente línea es una promoción
                promo_siguiente = None
                if i + 1 < len(lineas_raw) and lineas_raw[i + 1]['tipo'] == 'promocion':
                    promo_siguiente = lineas_raw[i + 1]
                
                cantidad_final = item['cantidad']
                base_final = item['base']
                
                if promo_siguiente:
                    # Sumar cantidad (botellas compradas + regaladas)
                    cantidad_final = item['cantidad'] + promo_siguiente['cantidad']
                    # Restar descuento del importe
                    base_final = round(item['base'] - promo_siguiente['descuento'], 2)
                
                lineas_finales.append({
                    'codigo': item['codigo'],
                    'articulo': item['articulo'],
                    'cantidad': cantidad_final,
                    'precio_ud': round(base_final / cantidad_final, 2) if cantidad_final > 0 else item['precio_ud'],
                    'iva': 21,
                    'base': base_final
                })
        
        return lineas_finales
    
    def _convertir_importe(self, texto: str) -> float:
        """Convierte formato europeo a float."""
        if not texto:
            return 0.0
        texto = texto.strip()
        # Manejar negativos
        negativo = texto.startswith('-')
        texto = texto.lstrip('-')
        # Formato europeo: 1.234,56 → 1234.56
        if '.' in texto and ',' in texto:
            texto = texto.replace('.', '').replace(',', '.')
        elif ',' in texto:
            texto = texto.replace(',', '.')
        try:
            valor = float(texto)
            return -valor if negativo else valor
        except:
            return 0.0
    
    def extraer_total(self, texto: str) -> Optional[float]:
        """Extrae total de la factura."""
        # Formato: "357,12 € 21,00 % 75,00 € 432,12 €" - último valor es TOTAL
        match = re.search(
            r'([\d.,]+)\s*€\s+21[,.]00\s*%\s+[\d.,]+\s*€\s+([\d.,]+)\s*€',
            texto
        )
        if match:
            return self._convertir_importe(match.group(2))
        
        # Alternativa: buscar TOTAL seguido de importe
        match = re.search(r'TOTAL\s+([\d.,]+)\s*€', texto, re.IGNORECASE)
        if match:
            return self._convertir_importe(match.group(1))
        
        return None
    
    def extraer_fecha(self, texto: str) -> Optional[str]:
        """Extrae fecha de la factura."""
        # Formato: "28/11/2025"
        match = re.search(r'(\d{2})/(\d{2})/(\d{4})', texto)
        if match:
            return f"{match.group(1)}/{match.group(2)}/{match.group(3)}"
        return None
    
    def extraer_referencia(self, texto: str) -> Optional[str]:
        """Extrae número de factura."""
        # Formato: "NUM. 20538/25"
        match = re.search(r'NUM\.\s*(\d+/\d+)', texto)
        if match:
            return match.group(1)
        return None
