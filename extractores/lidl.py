"""
Extractor para LIDL SUPERMERCADOS S.A.U.

Supermercado - compras con tarjeta
CIF: A60195278

Formato factura (pdfplumber):
- Líneas por unidad: DESCRIPCION CANTIDAD Cant. PRECIO IMPORTE_NETO IVA VALOR_IVA IMPORTE
- Líneas por peso: DESCRIPCION CANTIDAD Kg PRECIO IMPORTE_NETO IVA VALOR_IVA IMPORTE
- Desglose fiscal por tipo de IVA al final

IVA mixto:
- 4%: Alimentación básica (frutas, verduras, pan, quesos)
- 10%: Alimentación general (aceites, conservas, vinagre)
- 21%: No alimentación (bolsas, limpieza)

Pago: Tarjeta (no requiere IBAN)

Creado: 20/12/2025
Validado: 5/5 facturas (1T25, 2T25, 3T25)
"""
from extractores.base import ExtractorBase
from extractores import registrar
from typing import List, Dict, Optional
import re
import pdfplumber


@registrar('LIDL', 'LIDL SUPERMERCADOS', 'LIDL SUPERMERCADOS S.A.U.')
class ExtractorLidl(ExtractorBase):
    """Extractor para facturas de LIDL."""
    
    nombre = 'LIDL'
    cif = 'A60195278'
    iban = ''  # Pago con tarjeta
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
    
    def extraer_lineas(self, texto: str) -> List[Dict]:
        """
        Extrae líneas de productos.
        
        Formatos:
        - Por unidad: DESCRIPCION 1 Cant. 0,5400 0,54 21,00 0,11 0,65
        - Por peso: DESCRIPCION 1,698 Kg 2,8740 4,88 4,00 0,20 5,08
        
        La descripción puede contener números (ej: "LIMÓN 1 KG", "BOLSAS GRANDES 50L")
        """
        lineas = []
        
        # Patrón para productos por unidad
        # BOLSAS GRANDES 50L 1 Cant. 1,2800 1,28 21,00 0,27 1,55
        patron_unidad = re.compile(
            r'^(.+?)\s+'                             # Descripción (cualquier cosa)
            r'(\d+)\s+Cant\.\s+'                     # Cantidad + "Cant."
            r'(\d+,\d{4})\s+'                        # Precio unitario (4 dec)
            r'(\d+,\d{2})\s+'                        # Importe neto
            r'(\d+,\d{2})\s+'                        # % IVA
            r'(\d+,\d{2})\s+'                        # Valor IVA
            r'(\d+,\d{2})$'                          # Importe final
        , re.MULTILINE)
        
        # Patrón para productos por peso (Kg)
        # LIMÓN 1,698 Kg 2,8740 4,88 4,00 0,20 5,08
        patron_kg = re.compile(
            r'^(.+?)\s+'                             # Descripción
            r'(\d+,\d{3})\s+Kg\s+'                   # Cantidad Kg (3 dec)
            r'(\d+,\d{4})\s+'                        # Precio/Kg
            r'(\d+,\d{2})\s+'                        # Importe neto
            r'(\d+,\d{2})\s+'                        # % IVA
            r'(\d+,\d{2})\s+'                        # Valor IVA
            r'(\d+,\d{2})$'                          # Importe final
        , re.MULTILINE)
        
        # Buscar productos por unidad
        for match in patron_unidad.finditer(texto):
            descripcion = match.group(1).strip()
            cantidad = int(match.group(2))
            precio = self._convertir_europeo(match.group(3))
            base = self._convertir_europeo(match.group(4))  # Importe neto = base
            iva = int(self._convertir_europeo(match.group(5)))
            
            # Filtrar líneas de cabecera
            if 'DESCRIPCIÓN' in descripcion.upper() or 'unitario' in descripcion.lower():
                continue
            if descripcion.upper() == 'TOTAL':
                continue
            
            lineas.append({
                'codigo': '',
                'articulo': descripcion[:50],
                'cantidad': cantidad,
                'precio_ud': round(precio, 4),
                'iva': iva,
                'base': round(base, 2)
            })
        
        # Buscar productos por Kg
        for match in patron_kg.finditer(texto):
            descripcion = match.group(1).strip()
            cantidad = self._convertir_europeo(match.group(2))
            precio = self._convertir_europeo(match.group(3))
            base = self._convertir_europeo(match.group(4))
            iva = int(self._convertir_europeo(match.group(5)))
            
            if 'DESCRIPCIÓN' in descripcion.upper():
                continue
            
            lineas.append({
                'codigo': '',
                'articulo': descripcion[:50],
                'cantidad': round(cantidad, 3),
                'precio_ud': round(precio, 4),
                'iva': iva,
                'base': round(base, 2)
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
        # Buscar "Total X,XX X,XX X,XX" (última columna es bruto)
        patron = re.search(r'Total\s+(\d+,\d{2})\s+(\d+,\d{2})\s+(\d+,\d{2})', texto)
        if patron:
            return self._convertir_europeo(patron.group(3))
        # Total simple
        patron = re.search(r'Total\s+(\d+[,.]?\d*)\s*\n', texto)
        if patron:
            return self._convertir_europeo(patron.group(1))
        return None
    
    def extraer_fecha(self, texto: str) -> Optional[str]:
        """Extrae fecha de la factura (formato DD-Mmm-YYYY → DD/MM/YYYY)."""
        patron = re.search(r'Fecha Factura:\s*(\d{2})-([A-Za-z]+)-(\d{4})', texto)
        if patron:
            dia = patron.group(1)
            mes_texto = patron.group(2).lower()
            anio = patron.group(3)
            
            meses = {
                'ene': '01', 'jan': '01',
                'feb': '02',
                'mar': '03',
                'abr': '04', 'apr': '04',
                'may': '05',
                'jun': '06',
                'jul': '07',
                'ago': '08', 'aug': '08',
                'sep': '09',
                'oct': '10',
                'nov': '11',
                'dic': '12', 'dec': '12'
            }
            mes = meses.get(mes_texto[:3], '01')
            return f"{dia}/{mes}/{anio}"
        return None
    
    def extraer_numero_factura(self, texto: str) -> Optional[str]:
        """Extrae número de factura."""
        patron = re.search(r'Nº Factura:\s*(\d+)', texto)
        if patron:
            return patron.group(1)
        return None
