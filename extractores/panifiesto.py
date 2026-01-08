"""
Extractor para PANIFIESTO LAVAPIES SL

Panaderia artesanal de Lavapies (Madrid)
CIF: B87874327
Direccion: C/Encomienda 5 L10, 28012 Madrid
Telefono: 694449020
Email: panifiesto@gmail.com
Web: www.panifiesto.com

METODO: pdfplumber (PDF texto)

Productos: Pan artesanal (entregas diarias)
IVA: 4% (pan)
Categoria: PAN

Forma de pago: Tarjeta / Efectivo (no requiere SEPA)

NOTA: Las facturas son mensuales y agrupan multiples albaranes.
Se genera UNA SOLA LINEA por factura con el total del cuadro fiscal.

CAMBIOS v5.0 (26/12/2025):
- Simplificado: una sola línea por factura
- Usa base imponible del cuadro fiscal (más precisa)
- categoria_fija = 'PAN'

Creado: 21/12/2025
Actualizado: 26/12/2025
Validado: 10/10 facturas (1T25-4T25)
"""
from extractores.base import ExtractorBase
from extractores import registrar
from typing import List, Dict, Optional
import re


@registrar('PANIFIESTO', 'PANIFIESTO LAVAPIES')
class ExtractorPanifiesto(ExtractorBase):
    """Extractor para facturas de PANIFIESTO LAVAPIES SL."""
    
    nombre = 'PANIFIESTO LAVAPIES SL'
    cif = 'B87874327'
    iban = ''  # Pago por tarjeta/efectivo
    metodo_pdf = 'pdfplumber'
    categoria_fija = 'PAN'
    
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
        Extrae UNA SOLA LINEA con el total de la factura.
        
        Usa la base imponible del cuadro fiscal (más precisa que suma de albaranes).
        
        Cuadro fiscal ejemplo:
        Base imponible % Iva Total I.V.A.
         168,41 4 6,74 175,15
        """
        lineas = []
        
        # Extraer base imponible del cuadro fiscal
        # Formato: 168,41 4 6,74 175,15 (base, iva%, cuota, total)
        patron_fiscal = re.search(
            r'Base imponible.*?(\d+[.,]\d{2})\s+4\s+(\d+[.,]\d{2})\s+(\d+[.,]\d{2})',
            texto,
            re.DOTALL | re.IGNORECASE
        )
        
        if patron_fiscal:
            base = float(patron_fiscal.group(1).replace('.', '').replace(',', '.'))
            
            lineas.append({
                'codigo': '',
                'articulo': 'Pan',
                'cantidad': 1,
                'precio_ud': round(base, 2),
                'iva': 4,
                'base': round(base, 2),
                'categoria': 'PAN'  # categoria_fija
            })
        else:
            # Fallback: extraer total de albaranes
            patron_total = re.search(r'Total delegación\s+([\d.,]+)', texto)
            if patron_total:
                base = float(patron_total.group(1).replace('.', '').replace(',', '.'))
                
                lineas.append({
                    'codigo': '',
                    'articulo': 'Pan',
                    'cantidad': 1,
                    'precio_ud': round(base, 2),
                    'iva': 4,
                    'base': round(base, 2),
                    'categoria': 'PAN'
                })
        
        return lineas
    
    def extraer_total(self, texto: str) -> Optional[float]:
        """Extrae total de la factura."""
        # Primero buscar en formato "Total Neto XXX,XX €"
        m = re.search(r'Total Neto\s+([\d.,]+)\s*€', texto)
        if m:
            return float(m.group(1).replace('.', '').replace(',', '.'))
        
        # Alternativa: cuadro fiscal
        m = re.search(r'Base imponible.*?(\d+[.,]\d{2})\s+4\s+(\d+[.,]\d{2})\s+(\d+[.,]\d{2})', texto, re.DOTALL)
        if m:
            return float(m.group(3).replace('.', '').replace(',', '.'))
        
        return None
    
    def extraer_fecha(self, texto: str) -> Optional[str]:
        """
        Extrae fecha de la factura.
        Formato: 25-100101-57 28-feb.-2025 0023 B87760575
        """
        m = re.search(r'25-100101-\d+\s+(\d{2}-\w+\.-\d{4})', texto)
        if m:
            return self._convertir_fecha(m.group(1))
        return None
    
    def _convertir_fecha(self, fecha_raw: str) -> str:
        """Convierte fecha de formato '28-feb.-2025' a '28/02/2025'."""
        meses = {
            'ene': '01', 'feb': '02', 'mar': '03', 'abr': '04',
            'may': '05', 'jun': '06', 'jul': '07', 'ago': '08',
            'sep': '09', 'oct': '10', 'nov': '11', 'dic': '12'
        }
        
        match = re.match(r'(\d{2})-(\w+)\.-(\d{4})', fecha_raw)
        if match:
            dia = match.group(1)
            mes_txt = match.group(2).lower()[:3]
            anio = match.group(3)
            mes = meses.get(mes_txt, '01')
            return f"{dia}/{mes}/{anio}"
        return fecha_raw
    
    def extraer_numero_factura(self, texto: str) -> Optional[str]:
        """Extrae numero de factura (formato 25-100101-XXX)."""
        m = re.search(r'(25-100101-\d+)', texto)
        return m.group(1) if m else None
