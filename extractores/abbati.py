"""
Extractor para ABBATI CAFFE S.L.

Tostadores de cafe de Las Rozas (Madrid)
CIF: B82567876
Direccion: Las Rozas, 28231 Madrid
Telefono: 916361770
Email: info@abbaticaffe.com

METODO: pdfplumber (PDF texto)

Productos: Cafe en dosis, azucar
IVA: 10% (alimentacion)
Categoria: CAFE

Forma de pago: Recibo Bancario (domiciliacion)

NOTA: El nombre correcto es "Abbati Caffe" (con doble 'f', sin acento)

Creado: 21/12/2025
Validado: 3/3 facturas (1T25-3T25)
"""
from extractores.base import ExtractorBase
from extractores import registrar
from typing import List, Dict, Optional
import re


@registrar('ABBATI', 'ABBATI CAFFE', 'ABBATI CAFE', 'CAFFE ABBATI')
class ExtractorAbbati(ExtractorBase):
    """Extractor para facturas de ABBATI CAFFE S.L."""
    
    nombre = 'ABBATI CAFFE S.L.'
    cif = 'B82567876'
    iban = ''  # Pago por domiciliacion (Recibo Bancario)
    metodo_pdf = 'pdfplumber'
    categoria_fija = 'CAFE'
    
    def extraer_texto(self, pdf_path: str) -> str:
        """Extrae texto con pdfplumber."""
        import pdfplumber
        
        texto = ""
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                t = page.extract_text()
                if t:
                    texto += t + "\n"
        return texto
    
    def extraer_lineas(self, texto: str) -> List[Dict]:
        """
        Extrae lineas de productos.
        
        Formato lineas:
        Ref. Descripcion Cantidad Precio % Dto. % IVA Total
        00616 DOSIS CAFE X 150 1,00 50,50 10,00 50,50
        
        Nota: %Dto siempre es vacio (no hay columna), el patron captura:
        Codigo + Descripcion + Cantidad + Precio + %IVA + Total
        """
        lineas = []
        
        # Patron para lineas de producto
        patron = re.compile(
            r'^(\d{5})\s+'                      # Codigo 5 digitos
            r'(.+?)\s+'                          # Descripcion
            r'(\d+,\d{2})\s+'                   # Cantidad
            r'(\d+,\d{2})\s+'                   # Precio
            r'(\d+,\d{2})\s+'                   # % IVA
            r'(\d+,\d{2})\s*$'                  # Total
        , re.MULTILINE)
        
        for match in patron.finditer(texto):
            codigo = match.group(1)
            articulo = match.group(2).strip()
            cantidad = float(match.group(3).replace(',', '.'))
            precio = float(match.group(4).replace(',', '.'))
            iva_pct = int(float(match.group(5).replace(',', '.')))
            importe = float(match.group(6).replace(',', '.'))
            
            lineas.append({
                'codigo': codigo,
                'articulo': articulo[:50],
                'cantidad': round(cantidad, 2),
                'precio_ud': round(precio, 2),
                'iva': iva_pct,
                'base': round(importe, 2)
            })
        
        return lineas
    
    def extraer_total(self, texto: str) -> Optional[float]:
        """Extrae total de la factura."""
        m = re.search(r'TOTAL\s+([\d.,]+)', texto)
        if m:
            return float(m.group(1).replace('.', '').replace(',', '.'))
        return None
    
    def extraer_fecha(self, texto: str) -> Optional[str]:
        """Extrae fecha de la factura."""
        m = re.search(r'Fecha:\s*(\d{2}/\d{2}/\d{4})', texto)
        return m.group(1) if m else None
    
    def extraer_numero_factura(self, texto: str) -> Optional[str]:
        """Extrae numero de factura (formato 1/013607)."""
        m = re.search(r'FACTURA\s+(\d+/\s*\d+)', texto)
        return m.group(1).replace(' ', '') if m else None
