"""
Extractor para PIFEMA S.L.

Distribuidor de vinos (Pedregosa, Quinta de Aves, etc.)
CIF: B79048914
IBAN: ES49 2100 3784 39 2200009823

Formato factura (pdfplumber):
- Cabecera con datos cliente y albaran
- Lineas: CODIGO DESCRIPCION UDS/KG PRECIO [DESC] P.NETO IMPORTE
- Productos con descuento 100% tienen importe 0,00 (muestras)
- PORTES con descuento 100% (importe 0,00)
- Total en linea separada: "XXX,XX EUR"

IVA: 21% (vinos)

Creado: 21/12/2025
"""
from extractores.base import ExtractorBase
from extractores import registrar
from typing import List, Dict, Optional
import re
import pdfplumber


@registrar('PIFEMA', 'PIFEMA S.L.', 'PIFEMA WINES')
class ExtractorPifema(ExtractorBase):
    """Extractor para facturas de PIFEMA (vinos)."""
    
    nombre = 'PIFEMA'
    cif = 'B79048914'
    iban = 'ES49 2100 3784 39 2200009823'
    metodo_pdf = 'pdfplumber'
    categoria_fija = 'VINOS'
    
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
    
    def extraer_lineas(self, texto: str) -> List[Dict]:
        """
        Extrae lineas INDIVIDUALES de productos.
        
        Formato: CODIGO DESCRIPCION UDS/KG PRECIO [DESC] P.NETO IMPORTE
        Ejemplo: 12102 CAVA BLANC DE MILLESSIME PEDREGOSA B.N. RESERVA 6.00 7,700 7,700 46,20
        Con dto:  12104 PEDREGOSA CLOS DE BLANCS... 1.00 6,350 100,00 0,000 0,00
        """
        lineas = []
        
        # Patron para lineas de producto con codigo (5-8 digitos)
        patron = re.compile(
            r'^(\d{5,8})\s+'           # Codigo (5-8 digitos)
            r'(.+?)\s+'                 # Descripcion
            r'(\d+[.,]\d{2})\s+'        # Cantidad (ej: 6.00)
            r'(\d+[.,]\d{2,3})\s+'      # Precio (ej: 7,700)
            r'(?:100,00\s+)?'           # Descuento opcional (100,00 = 100%)
            r'(\d+[.,]\d{2,3})\s+'      # P.Neto
            r'(\d+[.,]\d{2})$'          # Importe
        , re.MULTILINE)
        
        for match in patron.finditer(texto):
            codigo = match.group(1)
            descripcion = match.group(2).strip()
            cantidad = self._convertir_europeo(match.group(3))
            precio = self._convertir_europeo(match.group(4))
            importe = self._convertir_europeo(match.group(6))
            
            # Ignorar lineas con importe 0 (muestras, descuentos 100%)
            if importe < 0.01:
                continue
            
            # Ignorar PORTES (normalmente tienen importe 0, pero por si acaso)
            if 'PORTES' in descripcion.upper():
                continue
            
            # Ignorar cabeceras
            if any(x in descripcion.upper() for x in ['DESCRIPCION', 'CODIGO', 'IMPORTE']):
                continue
            
            lineas.append({
                'codigo': codigo,
                'articulo': descripcion[:50],
                'cantidad': cantidad,
                'precio_ud': round(precio, 3),
                'iva': 21,  # Vinos siempre 21%
                'base': round(importe, 2)
            })
        
        return lineas
    
    def _convertir_europeo(self, texto: str) -> float:
        """Convierte formato europeo (1.234,56) a float."""
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
    
    def extraer_total(self, texto: str) -> Optional[float]:
        """Extrae total de la factura.
        
        Busca linea con formato "XXX,XX EUR" o "X.XXX,XX EUR"
        """
        for linea in texto.split('\n'):
            linea = linea.strip()
            # Buscar linea con formato "123,45 EUR" o "1.234,56 EUR"
            match = re.match(r'^(\d{1,3}(?:\.\d{3})*,\d{2})\s*(?:EUR|€)$', linea, re.IGNORECASE)
            if match:
                return self._convertir_europeo(match.group(1))
        return None
    
    def extraer_fecha(self, texto: str) -> Optional[str]:
        """Extrae fecha de la factura (formato DD/MM/YY)."""
        patron = re.search(r'^(\d{2}/\d{2}/\d{2})\s', texto, re.MULTILINE)
        if patron:
            fecha = patron.group(1)
            # Convertir a DD/MM/YYYY
            partes = fecha.split('/')
            if len(partes) == 3 and len(partes[2]) == 2:
                return f"{partes[0]}/{partes[1]}/20{partes[2]}"
            return fecha
        return None
    
    def extraer_referencia(self, texto: str) -> Optional[str]:
        """Extrae numero de factura (formato M25 / XXXX)."""
        patron = re.search(r'M\d+\s*/\s*(\d+)', texto)
        if patron:
            return patron.group(1)
        return None
