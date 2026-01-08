"""
Extractor para IBARRAKO PIPARRAK S. COOP.

Cooperativa de guindillas/piparras de Ibarra (Gipuzkoa)
CIF: F20532297
IBAN: REDACTED_IBAN (KUTXABANK)
Direccion: Otarreaga s/n, 20400 - IBARRA (Gipuzkoa)

METODO: pdfplumber (PDF texto)

Productos:
- 2008 GALON IBARLUR PET (garrafas piparras)
- 2004 BOTES GALON 1ª (botes guindillas)

IVA: 10% (conservas alimentarias)
Categoria: PIPARRAS

Tiene dos formatos de factura:
- Formato nuevo: bilingue vasco/español (FV24-XXXX)
- Formato antiguo: solo español (XX.XXX.XXX)

Creado: 21/12/2025
Validado: 3/3 facturas (1T25-2T25)
"""
from extractores.base import ExtractorBase
from extractores import registrar
from typing import List, Dict, Optional
import re


@registrar('IBARRAKO', 'IBARRAKO PIPARRAK', 'IBARRAKO PIPARRA', 'PIPARRAK')
class ExtractorIbarrako(ExtractorBase):
    """Extractor para facturas de IBARRAKO PIPARRAK S. COOP."""
    
    nombre = 'IBARRAKO PIPARRAK S. COOP.'
    cif = 'F20532297'
    iban = 'REDACTED_IBAN'
    metodo_pdf = 'pdfplumber'
    categoria_fija = 'PIPARRAS'
    
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
        Codigo (4 digitos) + Descripcion + Cantidad + Precio + %Dto + Importe
        Ejemplo: 2004 BOTES GALON 1ª 12,00 12,00 0,00 144,00
        """
        lineas = []
        
        # Patron para lineas de producto
        patron = re.compile(
            r'^(\d{4})\s+'           # Codigo 4 digitos
            r'(.+?)\s+'              # Descripcion
            r'(\d+,\d{2})\s+'        # Cantidad
            r'(\d+,\d{2})\s+'        # Precio
            r'(\d+,\d{2})\s+'        # % Dto
            r'(\d+,\d{2})\s*$'       # Importe
        , re.MULTILINE)
        
        for match in patron.finditer(texto):
            codigo = match.group(1)
            articulo = match.group(2).strip()
            cantidad = float(match.group(3).replace(',', '.'))
            precio = float(match.group(4).replace(',', '.'))
            importe = float(match.group(6).replace(',', '.'))
            
            lineas.append({
                'codigo': codigo,
                'articulo': articulo[:50],
                'cantidad': round(cantidad, 2),
                'precio_ud': round(precio, 2),
                'iva': 10,  # IVA 10% para conservas alimentarias
                'base': round(importe, 2)
            })
        
        return lineas
    
    def extraer_total(self, texto: str) -> Optional[float]:
        """
        Extrae total de la factura.
        
        Formato antiguo: 396,00 39,60 1,40 0,00 Euros 435,60
        Formato nuevo: 168,00 € 184,80 €
        """
        # Formato antiguo: buscar despues de "Euros"
        m_total = re.search(r'Euros\s+([\d.,]+)', texto)
        if m_total:
            return float(m_total.group(1).replace('.', '').replace(',', '.'))
        
        # Formato nuevo: buscar linea con dos importes €
        m_total2 = re.search(r'([\d.,]+)\s*€\s+([\d.,]+)\s*€', texto)
        if m_total2:
            return float(m_total2.group(2).replace('.', '').replace(',', '.'))
        
        return None
    
    def extraer_fecha(self, texto: str) -> Optional[str]:
        """
        Extrae fecha de la factura.
        
        Formato: d/m/yyyy o dd/mm/yyyy
        """
        m = re.search(r'(\d{1,2})/(\d{1,2})/(\d{4})', texto)
        if m:
            dia, mes, año = m.groups()
            return f"{dia.zfill(2)}/{mes.zfill(2)}/{año}"
        return None
    
    def extraer_numero_factura(self, texto: str) -> Optional[str]:
        """
        Extrae numero de factura.
        
        Formato nuevo: FV24-0235
        Formato antiguo: 11.942.488
        """
        # Formato nuevo
        m = re.search(r'(FV\d+-\d+)', texto)
        if m:
            return m.group(1)
        
        # Formato antiguo
        m = re.search(r'(\d{1,2}\.\d{3}\.\d{3})', texto)
        if m:
            return m.group(1)
        
        return None
