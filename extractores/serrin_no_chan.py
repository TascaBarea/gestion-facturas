"""
Extractor para SERRÍN NO CHAN S.L.

Ultramarinos gallegos - Productos gourmet de Galicia
CIF: B-87.214.755
IBAN: REDACTED_IBAN
Dirección: Alonso Cano 10 L27A, 28010 Madrid
Email: serrinnegocio@gmail.com

Productos típicos:
- Mariñeiras (galletas gallegas): AOVE, chía, mantequilla, clásicas - 4% IVA
- Perusiñas (galletas): limón, canela, jengibre, mantequilla - 10% IVA
- Patatotas (patatas) - 10% IVA
- Chorizo lalinense 240g - 10% IVA
- Lacón porciones - 10% IVA
- Pulpo - 10% IVA
- Patés (carabinero, langostino, sardina) - 10% IVA
- Vermú Lodeiros rojo/blanco 75cl - 21% IVA
- Vermutito/Minivermú 6cl - 21% IVA

Tipos de IVA:
- 4%: Mariñeiras (galletas con AOVE)
- 10%: Alimentación general
- 21%: Bebidas alcohólicas (vermú)

Creado: 20/12/2025
Validado: 7/7 facturas (2T25, 3T25, 4T25)
"""
from extractores.base import ExtractorBase
from extractores import registrar
from typing import List, Dict, Optional
import re


@registrar('SERRIN NO CHAN', 'SERRIN', 'SERRIN NO CHAO', 'SERRIN NOCHAO', 
           'SERRÍN NO CHAN', 'SERRÍN')
class ExtractorSerrinNoChan(ExtractorBase):
    """Extractor para facturas de SERRÍN NO CHAN S.L."""
    
    nombre = 'SERRIN NO CHAN'
    cif = 'B87214755'
    iban = 'REDACTED_IBAN'
    metodo_pdf = 'pdfplumber'
    
    def _convertir_europeo(self, texto: str) -> float:
        """Convierte formato europeo (1.234,56) a float."""
        if not texto:
            return 0.0
        texto = str(texto).strip().replace('€', '').replace(' ', '').strip()
        if '.' in texto and ',' in texto:
            texto = texto.replace('.', '').replace(',', '.')
        elif ',' in texto:
            texto = texto.replace(',', '.')
        try:
            return float(texto)
        except:
            return 0.0
    
    def extraer_texto(self, pdf_path: str) -> str:
        """Extrae texto con pdfplumber."""
        import pdfplumber
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                if len(pdf.pages) > 0:
                    return pdf.pages[0].extract_text()
        except:
            pass
        return ""
    
    def extraer_lineas(self, texto: str) -> List[Dict]:
        """
        Extrae líneas de producto.
        
        Formato:
        Código Referencia/Artículo Cantidad Precio Unitario Tipo IVA Importe IVA Importe sin IVA Importe con IVA
        
        Ejemplo:
        PER Perusiñas limón 6 4,90 10,00% 2,94 € 29,40 € 32,34 €
        MAR Mariñeiras AOVE 20 1,89 4,00% 1,51 € 37,80 € 39,31 €
        """
        lineas = []
        
        # Patrón para líneas de producto
        # Código Artículo Cantidad Precio TipoIVA% ImporteIVA€ ImporteSinIVA€ ImporteConIVA€
        for m in re.finditer(
            r'^([A-Z]+)\s+'                              # Código (PER, MAR, LOD, etc.)
            r'(.+?)\s+'                                  # Descripción
            r'([\d,]+)\s+'                               # Cantidad
            r'([\d,]+)\s+'                               # Precio unitario
            r'(\d+)[,.](\d+)%\s+'                        # Tipo IVA
            r'([\d,]+)\s*€\s+'                           # Importe IVA
            r'([\d,]+)\s*€\s+'                           # Importe sin IVA
            r'([\d,]+)\s*€',                             # Importe con IVA
            texto,
            re.MULTILINE
        ):
            codigo = m.group(1)
            articulo = m.group(2).strip()
            cantidad = self._convertir_europeo(m.group(3))
            precio = self._convertir_europeo(m.group(4))
            iva = int(m.group(5))
            base = self._convertir_europeo(m.group(8))
            
            lineas.append({
                'codigo': codigo,
                'articulo': articulo,
                'cantidad': int(cantidad) if cantidad == int(cantidad) else cantidad,
                'precio_ud': precio,
                'iva': iva,
                'base': base
            })
        
        return lineas
    
    def extraer_desglose_iva(self, texto: str) -> List[Dict]:
        """
        Extrae desglose de IVA.
        
        Formato:
        I.V.A sobre 166,30 € 4,00% 6,65 €
        I.V.A sobre 248,00 € 10,00% 24,80 €
        I.V.A sobre 282,18 € 21,00% 59,26 €
        """
        desglose = []
        
        for m in re.finditer(
            r'I\.V\.A sobre\s+([\d,.]+)\s*€\s+(\d+)[,.](\d+)%\s+([\d,.]+)\s*€',
            texto
        ):
            base = self._convertir_europeo(m.group(1))
            tipo = int(m.group(2))
            cuota = self._convertir_europeo(m.group(4))
            if base > 0:
                desglose.append({
                    'tipo': tipo,
                    'base': base,
                    'iva': cuota
                })
        
        return desglose
    
    def extraer_total(self, texto: str) -> Optional[float]:
        """
        Extrae total de la factura.
        
        Busca: "Total Factura con I.V.A. XXX,XX €"
        """
        m = re.search(r'Total Factura con I\.V\.A\.\s*([\d,.]+)\s*€', texto)
        if m:
            return self._convertir_europeo(m.group(1))
        
        # Alternativa: calcular desde desglose
        desglose = self.extraer_desglose_iva(texto)
        if desglose:
            return round(sum(d['base'] + d['iva'] for d in desglose), 2)
        
        return None
    
    def extraer_fecha(self, texto: str) -> Optional[str]:
        """Extrae fecha de la factura."""
        m = re.search(r'Fecha\s+(\d{1,2}/\d{1,2}/\d{4})', texto)
        if m:
            # Normalizar fecha a DD/MM/YYYY
            fecha = m.group(1)
            partes = fecha.split('/')
            if len(partes) == 3:
                dia = partes[0].zfill(2)
                mes = partes[1].zfill(2)
                anio = partes[2]
                return f"{dia}/{mes}/{anio}"
            return fecha
        return None
    
    def extraer_numero_factura(self, texto: str) -> Optional[str]:
        """Extrae número de factura."""
        m = re.search(r'Número fac\.\s+(FV/\d+/\d+)', texto)
        if m:
            return m.group(1)
        return None
