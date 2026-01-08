"""
Extractor para BIELLEBI SRL (Italia)

Proveedor de taralli y dulces italianos.
P.IVA: 06089700725 (Italia)
IVA: 0% (intracomunitario Art. 41 DL 331/93)
Categoría: TARALLI (por defecto), DULCES (si empieza por TRECCE)
Portes: Se prorratean entre los productos

Creado: 26/12/2025
"""
from extractores.base import ExtractorBase
from extractores import registrar
from typing import List, Dict, Optional
import re


@registrar('BIELLEBI', 'BIELLEBI SRL', 'LA PURISIMA BIELLEBI')
class ExtractorBiellebi(ExtractorBase):
    """Extractor para facturas de BIELLEBI (Italia)."""
    
    nombre = 'BIELLEBI'
    cif = 'IT06089700725'
    metodo_pdf = 'pdfplumber'
    
    def extraer_lineas(self, texto: str) -> List[Dict]:
        """Extrae líneas de productos de BIELLEBI con prorrateo de portes."""
        lineas_raw = []
        portes = 0.0
        
        # Patrón para líneas de producto
        patron = re.compile(
            r'(\d{2}\w*/\d+/\d+)\s+'          # Código (02FRI/250/25 o 02FRICI/250/25)
            r'([A-Z][A-Za-z0-9\s]+?)'          # Descripción
            r'\s+g?\d+[Xx]?\d*\s+'             # Formato (g250X25)
            r'[\d/]+\s+'                        # Lote
            r'PZ\s+'                            # UM
            r'([\d,.]+)\s+'                    # Cantidad
            r'\d+\s+'                           # CT
            r'([\d,.]+)\s+'                    # Precio
            r'([\d,.]+)\s+'                    # Imponible
            r'\d+'                              # C.I.
        )
        
        for match in patron.finditer(texto):
            codigo = match.group(1)
            descripcion = match.group(2).strip()
            cantidad = self._convertir_europeo(match.group(3))
            precio = self._convertir_europeo(match.group(4))
            imponible = self._convertir_europeo(match.group(5))
            
            if imponible > 0:
                lineas_raw.append({
                    'codigo': codigo,
                    'articulo': descripcion,
                    'cantidad': cantidad,
                    'precio_ud': precio,
                    'base': imponible
                })
        
        # Buscar portes
        m = re.search(r'Spese\s+di\s+spedizione\s+N\s+[\d,.]+\s+([\d,.]+)\s+([\d,.]+)', texto)
        if m:
            portes = self._convertir_europeo(m.group(2))
        
        # Prorratear portes
        lineas = []
        suma_base = sum(l['base'] for l in lineas_raw)
        
        for l in lineas_raw:
            base_original = l['base']
            if suma_base > 0 and portes > 0:
                porcion_portes = (base_original / suma_base) * portes
                base_final = base_original + porcion_portes
            else:
                base_final = base_original
            
            # Determinar categoría
            if l['articulo'].upper().startswith('TRECCE'):
                categoria = 'DULCES'
            else:
                categoria = 'TARALLI'
            
            lineas.append({
                'codigo': l['codigo'],
                'articulo': l['articulo'],
                'cantidad': l['cantidad'],
                'precio_ud': round(base_final / l['cantidad'], 4) if l['cantidad'] > 0 else base_final,
                'iva': 0,
                'base': round(base_final, 2),
                'categoria': categoria
            })
        
        return lineas
    
    def _convertir_europeo(self, texto: str) -> float:
        """Convierte formato europeo a float."""
        if not texto:
            return 0.0
        texto = texto.strip()
        if ',' in texto and '.' in texto:
            texto = texto.replace('.', '').replace(',', '.')
        elif ',' in texto:
            texto = texto.replace(',', '.')
        try:
            return float(texto)
        except:
            return 0.0
    
    def extraer_total(self, texto: str) -> Optional[float]:
        """Extrae total de la factura."""
        m = re.search(r'TOTALE\s+FATTURA\s*€?\s*([\d.,]+)', texto, re.IGNORECASE)
        if m:
            return self._convertir_europeo(m.group(1))
        # Alternativa: Imponibile total
        m = re.search(r'Imponibile\s+([\d.,]+)', texto)
        if m:
            return self._convertir_europeo(m.group(1))
        return None
    
    def extraer_fecha(self, texto: str) -> Optional[str]:
        """Extrae fecha de la factura."""
        m = re.search(r'Data\s+(\d{2}/\d{2}/\d{4})', texto)
        if m:
            return m.group(1)
        return None
    
    def extraer_referencia(self, texto: str) -> Optional[str]:
        """Extrae número de factura."""
        m = re.search(r'FATTURA\s+(\d+\s*/\s*\w+\s*/\s*\d+)', texto)
        if m:
            return m.group(1).replace(' ', '')
        return None
