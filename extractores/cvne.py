"""
Extractor para CVNE (Compania Vinicola del Norte de Espana)

Vinos, cavas y vermuts Valsangiacomo.

Formato factura:
Nº factura Fecha Nº Pedido Cliente Cliente CIF/NIF Nº Proveedor
F26-40-08002 30/11/2025 4303025416 B87760575

Articulo Descripcion Anada Cantidad Precio % Dto. PV Importe
926673510ES00 VALSANGIACOMO CAVA VALLE SANJAIME B 00 6 5,55 0,13 33,43
...
Total lineas Dto. Lineas Dto. Factura PV Base imponible % IVA Importe IVA % RE Importe RE Total EUR
252,90 1,14 254,04 21 % 53,35 307,39

IMPORTANTE: El "Importe" de cada linea ya tiene el descuento aplicado (es el PV, precio venta).
Número factura: F26-40-08002 (formato FXX-XX-XXXXX)

CIF: A48002893
IVA: 21%

Creado: 19/12/2025
Actualizado: 07/01/2026 - Añadido extraer_numero_factura()
"""
from extractores.base import ExtractorBase
from extractores import registrar
from typing import List, Dict, Optional
import re


@registrar('CVNE', 'COMPAÑIA VINICOLA', 'VALSANGIACOMO')
class ExtractorCvne(ExtractorBase):
    """Extractor para facturas de CVNE."""
    
    nombre = 'CVNE'
    cif = 'A48002893'
    iban = 'ES0921009144310200025176'
    metodo_pdf = 'pdfplumber'
    categoria_fija = 'VINOS'
    
    def extraer_lineas(self, texto: str) -> List[Dict]:
        """
        Extrae lineas de la factura.
        
        Formato lineas:
        926673510ES00 VALSANGIACOMO CAVA VALLE SANJAIME B 00 6 5,55 0,13 33,43
        
        codigo descripcion anada cantidad precio %dto PV importe
        
        El importe ya tiene el descuento de linea aplicado.
        """
        lineas = []
        
        # Patron para lineas de producto
        # Codigo: 9 digitos + ES + 2 digitos = 14 chars
        # Formato: 926673510ES00 VALSANGIACOMO CAVA... 00 6 5,55 0,13 33,43
        patron = re.compile(
            r'^(\d{9}[A-Z]{2}\d{2})\s+'        # Codigo articulo (14 chars)
            r'(.+?)\s+'                         # Descripcion (flexible)
            r'(\d{2})\s+'                       # Anada (00)
            r'(\d+)\s+'                         # Cantidad
            r'(\d+,\d{2})\s+'                   # Precio unitario
            r'(\d+,\d{2})\s+'                   # % Dto o PV
            r'(\d+,\d{2})$'                     # Importe
        , re.MULTILINE)
        
        for match in patron.finditer(texto):
            codigo = match.group(1)
            descripcion = match.group(2).strip()
            cantidad = int(match.group(4))
            precio = self._convertir_europeo(match.group(5))
            importe = self._convertir_europeo(match.group(7))
            
            # Limpiar descripcion (puede tener B al final de otra linea)
            descripcion = re.sub(r'\s+B$', '', descripcion)
            descripcion = re.sub(r'\s+', ' ', descripcion).strip()
            
            lineas.append({
                'codigo': codigo,
                'articulo': descripcion,
                'cantidad': cantidad,
                'precio_ud': precio,
                'iva': 21,
                'base': round(importe, 2),
                'categoria': self.categoria_fija
            })
        
        # Si no hay lineas, intentar con patron mas flexible
        if not lineas:
            # Buscar base imponible directamente
            patron_base = re.search(r'Base\s+imponible.*?(\d+,\d{2})\s+21\s*%', texto, re.IGNORECASE)
            if patron_base:
                base = self._convertir_europeo(patron_base.group(1))
                lineas.append({
                    'codigo': '',
                    'articulo': 'VINOS Y VERMUTS CVNE',
                    'cantidad': 1,
                    'precio_ud': base,
                    'iva': 21,
                    'base': round(base, 2),
                    'categoria': self.categoria_fija
                })
        
        return lineas
    
    def _convertir_europeo(self, texto: str) -> float:
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
    
    def extraer_numero_factura(self, texto: str) -> Optional[str]:
        """
        Extrae número de factura.
        
        Formato: F26-40-08002 (FXX-XX-XXXXX)
        Aparece después de "Nº factura" en la cabecera.
        """
        # Buscar formato FXX-XX-XXXXX
        patron = re.search(r'\b(F\d{2}-\d{2}-\d{4,6})\b', texto)
        if patron:
            return patron.group(1)
        
        # Alternativa: buscar después de "Nº factura"
        patron2 = re.search(r'[Nn]º\s*factura[^\n]*?(F\d{2}-\d{2}-\d{4,6})', texto)
        if patron2:
            return patron2.group(1)
        
        return None
    
    def extraer_total(self, texto: str) -> Optional[float]:
        """
        Total esta en la linea de resumen como 'Total EUR' o al final.
        Formato: 252,90 1,14 254,04 21 % 53,35 307,39
        """
        # Buscar en linea de vencimiento: 30/12/2025 307,39
        patron_venc = re.search(r'\d{2}/\d{2}/\d{4}\s+(\d+,\d{2})\s*$', texto, re.MULTILINE)
        if patron_venc:
            return self._convertir_europeo(patron_venc.group(1))
        
        # Buscar Total EUR directamente
        patron_total = re.search(r'Total\s+EUR\s*\n?\s*(\d+,\d{2})', texto, re.IGNORECASE)
        if patron_total:
            return self._convertir_europeo(patron_total.group(1))
        
        # Buscar patron: % IVA Importe seguido de valores
        # 21 % 53,35 307,39 (el ultimo valor es el total)
        patron_resumen = re.search(r'21\s*%\s+(\d+,\d{2})\s+(\d+,\d{2})', texto)
        if patron_resumen:
            return self._convertir_europeo(patron_resumen.group(2))
        
        return None
    
    def extraer_fecha(self, texto: str) -> Optional[str]:
        """
        Fecha en formato: F26-40-08002 30/11/2025
        """
        patron = re.search(r'F\d{2}-\d{2}-\d{5}\s+(\d{2})/(\d{2})/(\d{4})', texto)
        if patron:
            return f"{patron.group(1)}/{patron.group(2)}/{patron.group(3)}"
        
        # Alternativo: buscar fecha despues de "Fecha"
        patron2 = re.search(r'Fecha[^\d]*(\d{2})/(\d{2})/(\d{4})', texto)
        if patron2:
            return f"{patron2.group(1)}/{patron2.group(2)}/{patron2.group(3)}"
        
        return None
