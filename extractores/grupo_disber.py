"""
Extractor para GRUPO DISBER SL

Distribuidor de vinos y conservas gourmet en Lliria (Valencia)
Productos: Vinos VEGAMAR, Conservas HERENCIA DEL MAR
CIF: B46144424

Formato factura (pdfplumber):
- Líneas: [CODIGO] Descripción CANTIDAD BASE P.UNIT IMPORTE €
- Desglose fiscal al final

IVA:
- 21%: Vinos
- 10%: Conservas

Creado: 20/12/2025
Validado: 4/4 facturas (1T25, 2T25)
"""
from extractores.base import ExtractorBase
from extractores import registrar
from typing import List, Dict, Optional
import re
import pdfplumber


@registrar('GRUPO DISBER', 'DISBER', 'DISBER SL', 'GRUPODISBER')
class ExtractorGrupoDisber(ExtractorBase):
    """Extractor para facturas de GRUPO DISBER."""
    
    nombre = 'GRUPO DISBER'
    cif = 'B46144424'
    iban = 'ES3921008617150200024610'
    metodo_pdf = 'pdfplumber'
    
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
    
    def extraer_tipo_iva(self, texto: str) -> int:
        """Detecta el tipo de IVA de la factura (10% o 21%)."""
        if 'IVA 21%' in texto:
            return 21
        elif 'IVA 10%' in texto:
            return 10
        return 21  # Default para vinos
    
    def extraer_lineas(self, texto: str) -> List[Dict]:
        """
        Extrae líneas de productos.
        
        Formato: [CODIGO] Descripción CANTIDAD BASE P.UNIT IMPORTE €
        Ejemplo: [2VSME] Botella Vino Blanco HUELLA de Merseguera VEGAMAR 24,00 5,10 5,1000 122,40 €
        """
        lineas = []
        iva = self.extraer_tipo_iva(texto)
        
        # Patrón para líneas de producto
        patron_linea = re.compile(
            r'\[([A-Z0-9]+)\]\s+'                    # Código entre corchetes
            r'(.+?)\s+'                              # Descripción
            r'(\d+[,.]\d{2})\s+'                     # Cantidad
            r'(\d+[,.]\d{2})\s+'                     # Base IVA (precio con dto)
            r'(\d+[,.]\d{4})\s+'                     # P.Unit (4 decimales)
            r'(\d+[,.]\d{2})\s*€'                    # Importe
        )
        
        for match in patron_linea.finditer(texto):
            codigo = match.group(1).strip()
            descripcion = match.group(2).strip()
            cantidad = self._convertir_europeo(match.group(3))
            precio = self._convertir_europeo(match.group(5))  # P.Unit
            importe = self._convertir_europeo(match.group(6))
            
            # Limpiar descripción (quitar saltos de línea)
            descripcion = re.sub(r'\s+', ' ', descripcion)
            
            lineas.append({
                'codigo': codigo,
                'articulo': descripcion[:50],
                'cantidad': cantidad,
                'precio_ud': round(precio, 4),
                'iva': iva,
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
        """Extrae total de la factura."""
        # Buscar "Total XXX,XX €"
        patron = re.search(r'Total\s+(\d+[,.]\d{2})\s*€', texto)
        if patron:
            return self._convertir_europeo(patron.group(1))
        return None
    
    def extraer_fecha(self, texto: str) -> Optional[str]:
        """Extrae fecha de la factura."""
        # La fecha está en la línea después del encabezado "Fecha de factura:"
        # Formato: 055372 20/05/2025 055372 AR25004604 ...
        # Buscamos la primera fecha DD/MM/YYYY en el texto
        fechas = re.findall(r'(\d{2}/\d{2}/\d{4})', texto)
        if fechas:
            return fechas[0]  # Primera fecha es la de factura
        return None
    
    def extraer_numero_factura(self, texto: str) -> Optional[str]:
        """Extrae número de factura."""
        # Formato: Factura FCVD250500043
        patron = re.search(r'Factura\s+(FCVD\d+)', texto)
        if patron:
            return patron.group(1)
        return None
