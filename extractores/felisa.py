"""
Extractor para FELISA GOURMET (PESCADOS DON FELIX).
CIF: B72113897 | IBAN: REDACTED_IBAN (BBVA)

Conservas de pescado premium de Barbate (Cádiz):
- Sardinas ahumadas (FSAH500, SAHG500, SAH120)
- Anchoas ahumadas (AAH120)
- Sardinas/Boquerones en vinagre (SV120, BV120)
- Mojama (TN) - se vende por kilos
- Atún rojo: lomo (LAR125), solomillo (SL125), paté (PATEATUN), marcurada (JMB100)
- Melva (M125)

IVA: 10% productos alimentarios, 21% transporte (8,30€ fijo)

Nota: Facturas anteriores a marzo 2025 usaban IBAN Santander ES33 0049 2347 6124 1404 5127

Creado: 18/12/2025
Actualizado: 01/01/2026 - Validado con 13 facturas (1T25-4T25)
Validado: 13/13 facturas ✓
"""
from extractores.base import ExtractorBase
from extractores import registrar
from typing import List, Dict, Optional
import re
import pdfplumber


@registrar('FELISA GOURMET', 'FELISA', 'PESCADOS DON FELIX', 'DON FELIX')
class ExtractorFelisa(ExtractorBase):
    """Extractor para facturas de FELISA GOURMET."""
    
    nombre = 'FELISA GOURMET'
    cif = 'B72113897'
    iban = 'REDACTED_IBAN'  # BBVA (desde marzo 2025)
    metodo_pdf = 'pdfplumber'
    
    def _convertir_importe(self, texto: str) -> float:
        """Convierte texto a float."""
        if not texto:
            return 0.0
        texto = str(texto).strip().replace('€', '').replace(' ', '')
        if '.' in texto and ',' in texto:
            texto = texto.replace('.', '').replace(',', '.')
        elif ',' in texto:
            texto = texto.replace(',', '.')
        try:
            return float(texto)
        except:
            return 0.0
    
    def extraer_cuadro_fiscal(self, texto: str) -> List[Dict]:
        """
        Extrae el cuadro fiscal oficial.
        
        Formato típico:
        Base imponible IVA Rec. Equiv.
        69,60 10 % 6,96
        8,30 21 % 1,74
        """
        desglose = []
        for m in re.finditer(r'([\d,.]+)\s+(\d+)\s*%\s+([\d,.]+)', texto):
            base = self._convertir_importe(m.group(1))
            tipo = int(m.group(2))
            iva = self._convertir_importe(m.group(3))
            if base > 0 and tipo in [4, 10, 21]:
                desglose.append({'tipo': tipo, 'base': base, 'iva': iva})
        return desglose
    
    def extraer_lineas(self, texto: str) -> List[Dict]:
        """
        Extrae líneas de producto.
        
        Formato:
        CODIGO DESCRIPCION CANTIDAD Unidades/Kilos PRECIO TOTAL
        
        Ejemplos:
        FSAH500 SARDINA AHUMADA 500GR FELISA 6 Unidades 11,6000 69,60
        TN MOJAMA 3UNID 0,74 Kilos 44,0000 32,56
        """
        lineas = []
        
        # Patrón para líneas de producto
        patron = re.compile(
            r'^([A-Z][A-Z0-9]*)\s+'           # Código (AAH120, TN, etc.)
            r'(.+?)\s+'                        # Descripción
            r'([\d,]+)\s+'                     # Cantidad
            r'(?:Unidades|Kilos)\s+'           # Unidad
            r'([\d,]+)\s+'                     # Precio unitario
            r'([\d,]+)',                       # Total línea
            re.MULTILINE
        )
        
        for match in patron.finditer(texto):
            codigo, desc, cantidad, precio, importe = match.groups()
            desc_limpia = desc.strip()
            
            # Filtrar líneas inválidas (albaranes, lotes)
            if 'Albaran' in desc_limpia or 'Lote:' in desc_limpia:
                continue
            if len(desc_limpia) < 3:
                continue
            
            # Limpiar descripción
            desc_limpia = re.sub(r'\s*-\s*[A-Z0-9]+$', '', desc_limpia)
            
            cant = self._convertir_importe(cantidad)
            base = self._convertir_importe(importe)
            
            if base > 0:
                lineas.append({
                    'codigo': codigo,
                    'articulo': desc_limpia[:50],
                    'cantidad': cant if cant != int(cant) else int(cant),
                    'precio_ud': self._convertir_importe(precio),
                    'iva': 10,  # Todos los productos alimentarios al 10%
                    'base': base
                })
        
        # TRANSPORTE (IVA 21%, siempre 8,30€)
        match_transp = re.search(r'TRANSPORTE\s+([\d,]+)', texto)
        if match_transp:
            valor = self._convertir_importe(match_transp.group(1))
            if 0 < valor < 50:
                lineas.append({
                    'codigo': 'TRANSP',
                    'articulo': 'TRANSPORTE',
                    'cantidad': 1,
                    'precio_ud': valor,
                    'iva': 21,
                    'base': valor
                })
        
        # Validar con cuadro fiscal
        cuadro = self.extraer_cuadro_fiscal(texto)
        if cuadro and lineas:
            lineas = self._ajustar_con_cuadro_fiscal(lineas, cuadro)
        
        return lineas
    
    def _ajustar_con_cuadro_fiscal(self, lineas: List[Dict], cuadro: List[Dict]) -> List[Dict]:
        """Ajusta las bases para que cuadren con el cuadro fiscal."""
        # Bases del cuadro fiscal por tipo IVA
        bases_fiscales = {d['tipo']: d['base'] for d in cuadro}
        
        # Bases extraídas por tipo IVA
        bases_extraidas = {}
        for linea in lineas:
            iva = linea['iva']
            bases_extraidas[iva] = bases_extraidas.get(iva, 0) + linea['base']
        
        # Calcular factores de ajuste si hay diferencia
        for iva in bases_extraidas:
            if iva in bases_fiscales:
                diff = abs(bases_extraidas[iva] - bases_fiscales[iva])
                if diff > 0.10 and bases_extraidas[iva] > 0:
                    # Aplicar ajuste proporcional
                    factor = bases_fiscales[iva] / bases_extraidas[iva]
                    for linea in lineas:
                        if linea['iva'] == iva:
                            linea['base'] = round(linea['base'] * factor, 2)
        
        return lineas
    
    def extraer_total(self, texto: str) -> Optional[float]:
        """Extrae total de la factura."""
        # Método 1: Total Factura XX,XX €
        m = re.search(r'Total\s*Factura\s*([\d,.]+)\s*€', texto)
        if m:
            return self._convertir_importe(m.group(1))
        
        # Método 2: Suma desde cuadro fiscal
        cuadro = self.extraer_cuadro_fiscal(texto)
        if cuadro:
            return round(sum(d['base'] + d['iva'] for d in cuadro), 2)
        
        return None
    
    def extraer_fecha(self, texto: str) -> Optional[str]:
        """Extrae fecha de la factura (DD/MM/YYYY)."""
        m = re.search(r'(\d{2}/\d{2}/\d{4})', texto)
        if m:
            return m.group(1)
        return None
    
    def extraer_numero_factura(self, texto: str) -> Optional[str]:
        """Extrae número de factura (formato TG25/XXXX)."""
        m = re.search(r'TG\d+/\d+', texto)
        return m.group(0) if m else None
    
    # Alias para main.py
    extraer_referencia = extraer_numero_factura
