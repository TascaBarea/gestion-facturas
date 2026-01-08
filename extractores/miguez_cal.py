"""
Extractor para MIGUEZ CAL S.L. (ForPlan - Productos de limpieza)

Productos de limpieza profesional, detergentes, papel.

Formato factura:
FECHA FACTURA CLIENTE N.I.F TELÉFONO PÁG.
31/01/25 A 400 430005044 B87760575 600214481 1
...
CODIGO DESCRIPCION UNID. PRECIO DTO1 DTO2 IMPORTE
FP2-06 FP-2 DETERGENTE MAQ. LAVAVAJILLAS GARRAFA 6 KG 2,00 13,01 26,02
...
TOTAL IMP. % IMPORTE BASE % IVA % REC. TOTAL FRA
181,25 181,25 21,00 38,06
219,31€

NOTAS:
- Facturas multipagina con SUMA Y SIGUE / SUMA ANTERIOR
- Lineas SCRAP son aportaciones medioambientales (ignorar, no tienen importe)
- Algunas lineas no tienen importe (producto sin coste adicional)
- Total en ultima pagina con formato XXX,XX€

Número factura: Formato "A XXXX" (letra + espacio + 3-5 dígitos)

CIF: B79868006
IVA: 21%

Creado: 19/12/2025
Actualizado: 07/01/2026 - Añadido extraer_numero_factura()
"""
from extractores.base import ExtractorBase
from extractores import registrar
from typing import List, Dict, Optional
import re


@registrar('MIGUEZ CAL', 'FORPLAN', 'FOR-PLAN', 'FOR PLAN')
class ExtractorMiguezCal(ExtractorBase):
    """Extractor para facturas de Miguez Cal (ForPlan)."""
    
    nombre = 'MIGUEZ CAL'
    cif = 'B79868006'
    iban = ''
    metodo_pdf = 'pdfplumber'
    categoria_fija = 'LIMPIEZA'
    
    def extraer_lineas(self, texto: str) -> List[Dict]:
        """
        Extrae lineas de la factura.
        
        Formato:
        FP2-06 FP-2 DETERGENTE MAQ. LAVAVAJILLAS GARRAFA 6 KG 2,00 13,01 26,02
        CODIGO DESCRIPCION                                   UNID PRECIO IMPORTE
        
        Ignorar:
        - Lineas SCRAP (aportaciones medioambientales)
        - Lineas sin importe final
        """
        lineas = []
        
        # Patron para lineas de producto con importe
        # CODIGO DESCRIPCION UNID PRECIO [DTO1] [DTO2] IMPORTE
        # Descripcion puede contener numeros, puntos, parentesis, etc.
        patron = re.compile(
            r'^([A-Z0-9][A-Z0-9.-]*)\s+'           # Codigo (ej: FP2-06, BOB.ECO1000)
            r'(.+?)\s+'                             # Descripcion (todo hasta los numeros)
            r'(\d+,\d{2})\s+'                       # Unidades (ej: 2,00 o 1,00)
            r'(\d+,\d{2})\s+'                       # Precio
            r'(\d+,\d{2})$'                         # Importe (ultimo valor)
        , re.MULTILINE)
        
        for match in patron.finditer(texto):
            codigo = match.group(1).strip()
            descripcion = match.group(2).strip()
            unidades = self._convertir_europeo(match.group(3))
            precio = self._convertir_europeo(match.group(4))
            importe = self._convertir_europeo(match.group(5))
            
            # Ignorar lineas SCRAP (aportaciones medioambientales)
            if codigo.startswith('SCRAP'):
                continue
            
            # Ignorar si importe es muy pequeno (posible SCRAP mal parseado)
            if importe < 1.0:
                continue
            
            lineas.append({
                'codigo': codigo,
                'articulo': descripcion,
                'cantidad': unidades,
                'precio_ud': precio,
                'iva': 21,
                'base': round(importe, 2),
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
        
        Formato: Línea después de cabecera FECHA FACTURA CLIENTE
        DD/MM/YY A XXXX 430005044 B87760575 600214481 1
        
        El número es "A XXXX" (letra + espacio + dígitos)
        """
        # Buscar línea con formato: DD/MM/YY A XXXX seguido de número cliente
        patron = re.search(
            r'^\d{2}/\d{2}/\d{2}\s+([A-Z]\s*\d{3,5})\s+\d{9}',
            texto,
            re.MULTILINE
        )
        if patron:
            return patron.group(1).strip()
        
        # Alternativa: buscar después de "FACTURA" en cabecera
        patron2 = re.search(
            r'FACTURA\s+([A-Z]\s*\d{3,5})\s+CLIENTE',
            texto,
            re.IGNORECASE
        )
        if patron2:
            return patron2.group(1).strip()
        
        return None
    
    def extraer_total(self, texto: str) -> Optional[float]:
        """
        Total en formato: 219,31€ o 219,31 €
        Esta en la ultima pagina despues de TOTAL FRA
        """
        # Buscar total con euro
        patron = re.search(r'(\d+,\d{2})€', texto)
        if patron:
            return self._convertir_europeo(patron.group(1))
        
        # Alternativo: buscar en vencimientos
        patron2 = re.search(r'Vencimientos:\s*\n\d{2}/\d{2}/\d{2}\s*\n(\d+,\d{2})', texto)
        if patron2:
            return self._convertir_europeo(patron2.group(1))
        
        # Buscar TOTAL FRA seguido de valor
        patron3 = re.search(r'TOTAL\s+FRA\s*\n?\s*(\d+,\d{2})', texto, re.IGNORECASE)
        if patron3:
            return self._convertir_europeo(patron3.group(1))
        
        return None
    
    def extraer_fecha(self, texto: str) -> Optional[str]:
        """
        Fecha en formato: 31/01/25 A 400
        """
        patron = re.search(r'^(\d{2})/(\d{2})/(\d{2})\s+A\s+\d+', texto, re.MULTILINE)
        if patron:
            dia = patron.group(1)
            mes = patron.group(2)
            anio = patron.group(3)
            # Convertir ano de 2 digitos a 4
            anio_completo = f"20{anio}" if int(anio) < 50 else f"19{anio}"
            return f"{dia}/{mes}/{anio_completo}"
        
        return None
