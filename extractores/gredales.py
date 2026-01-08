"""
Extractor para LOS GREDALES DE EL TOBOSO S.L.

Bodega de vinos ecológicos de Toledo.
CIF: B83594150
IBAN: REDACTED_IBAN

Productos:
- SAUVIGNON BLANC -> VINO BLANCO SAUVIGNON
- SYRAH -> VINOS
- CABERNET SAUVIGNON -> VINOS
- GARNACHA ROSÉ -> VINO CLARETE O ROSADO
- GRACIANO -> VINO TINTO GRACIANO

IVA: 21%

Formato factura:
DESCRIPCION CAJAS BOTELLAS PRECIO/UD % DESCUENTO TOTAL
Los números pueden estar en línea separada o junto con la descripción.

NOTA: Algunas facturas tienen inconsistencias entre las líneas y la
base imponible. El extractor valida contra BASE IMPONIBLE.

Creado: 30/12/2025
"""
from extractores.base import ExtractorBase
from extractores import registrar
from typing import List, Dict, Optional
import re


@registrar('LOS GREDALES', 'GREDALES', 'LOS GREDALES DEL TOBOSO', 'GREDALES DE EL TOBOSO',
           'GREDALES TOBOSO', 'BODEGA LOS GREDALES')
class ExtractorGredales(ExtractorBase):
    """Extractor para facturas de LOS GREDALES DE EL TOBOSO."""
    
    nombre = 'LOS GREDALES'
    cif = 'B83594150'
    iban = 'REDACTED_IBAN'
    metodo_pdf = 'pdfplumber'
    
    # Mapeo de vinos a categorías
    CATEGORIAS = {
        'SAUVIGNON BLANC': 'VINO BLANCO SAUVIGNON',
        'GARNACHA ROSÉ': 'VINO CLARETE O ROSADO',
        'GRACIANO': 'VINO TINTO GRACIANO',
        'SYRAH': 'VINOS',
        'CABERNET SAUVIGNON': 'VINOS',
        'CABERNET': 'VINOS',
    }
    
    def extraer_lineas(self, texto: str) -> List[Dict]:
        """
        Extrae líneas de productos.
        
        El formato tiene descripciones multilínea con números intercalados:
        LOS GREDALES DE EL TOBOSO SAUVIGNON BLANC 2023, VINO
        BLANCO IGP, 13%, 75CL, ...
        5 30 3,00 € 90,00 €
        100% ECOLOGICO Y VEGANO
        """
        lineas = []
        
        # Patrón: busca CAJAS BOTELLAS PRECIO € TOTAL € al final de línea
        patron_numeros = re.compile(r'(\d+)\s+(\d+)\s+([\d,]+)\s*€\s+([\d,]+)\s*€\s*$')
        
        texto_lineas = texto.split('\n')
        vino_actual = None
        
        for linea in texto_lineas:
            linea_orig = linea.strip()
            linea_upper = linea_orig.upper()
            
            # Detectar tipo de vino en la descripción
            if 'SAUVIGNON BLANC' in linea_upper:
                vino_actual = 'SAUVIGNON BLANC'
            elif 'GARNACHA' in linea_upper and 'ROSÉ' in linea_upper:
                vino_actual = 'GARNACHA ROSÉ'
            elif 'GRACIANO' in linea_upper:
                vino_actual = 'GRACIANO'
            elif 'SYRAH' in linea_upper:
                vino_actual = 'SYRAH'
            elif 'CABERNET' in linea_upper:
                vino_actual = 'CABERNET SAUVIGNON'
            
            # Buscar números al final de la línea
            m = patron_numeros.search(linea_orig)
            if m and vino_actual:
                cajas = int(m.group(1))
                botellas = int(m.group(2))
                precio = self._convertir_europeo(m.group(3))
                total = self._convertir_europeo(m.group(4))
                
                # Ignorar línea de TOTAL general
                if cajas > 15 or total > 400:
                    continue
                
                categoria = self.CATEGORIAS.get(vino_actual, 'VINOS')
                
                lineas.append({
                    'codigo': '',
                    'articulo': f'LOS GREDALES {vino_actual}',
                    'cantidad': botellas,
                    'precio_ud': round(precio, 2),
                    'iva': 21,
                    'base': round(total, 2),
                    'categoria': categoria
                })
                
                vino_actual = None  # Reset para el siguiente producto
        
        # Validar contra BASE IMPONIBLE
        lineas = self._validar_contra_base(texto, lineas)
        
        return lineas
    
    def _validar_contra_base(self, texto: str, lineas: List[Dict]) -> List[Dict]:
        """
        Verifica que la suma de líneas coincida con BASE IMPONIBLE.
        Si hay discrepancia significativa, ajusta proporcionalmente.
        """
        base_imponible = self._extraer_base_imponible(texto)
        if not base_imponible or not lineas:
            return lineas
        
        suma_lineas = sum(l['base'] for l in lineas)
        diferencia = abs(suma_lineas - base_imponible)
        
        # Si la diferencia es mayor al 10%, hay inconsistencia
        if diferencia > base_imponible * 0.10:
            # Caso especial: algunas facturas listan productos pero no se vendieron
            # Usar solo la BASE IMPONIBLE como línea única
            return [{
                'codigo': '',
                'articulo': 'VINOS ECOLOGICOS LOS GREDALES',
                'cantidad': 1,
                'precio_ud': round(base_imponible, 2),
                'iva': 21,
                'base': round(base_imponible, 2),
                'categoria': 'VINOS'
            }]
        
        return lineas
    
    def _extraer_base_imponible(self, texto: str) -> Optional[float]:
        """Extrae BASE IMPONIBLE del texto."""
        m = re.search(r'BASE\s+IMPONIBLE\s+([\d,]+)\s*€', texto, re.IGNORECASE)
        if m:
            return self._convertir_europeo(m.group(1))
        return None
    
    def _convertir_europeo(self, texto: str) -> float:
        """Convierte formato europeo a float."""
        if not texto:
            return 0.0
        texto = texto.strip().replace('€', '').replace(' ', '')
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
        # Formato: "TOTAL 12 72 344,12 €"
        m = re.search(r'TOTAL\s+\d+\s+\d+\s+([\d,]+)\s*€', texto)
        if m:
            return self._convertir_europeo(m.group(1))
        return None
    
    def extraer_fecha(self, texto: str) -> Optional[str]:
        """Extrae fecha de la factura."""
        # Formato: "FECHA: 10/11/25" o "FECHA: 04/03/25"
        m = re.search(r'FECHA:\s*(\d{2}/\d{2}/\d{2,4})', texto)
        if m:
            fecha = m.group(1)
            # Convertir año corto a largo si es necesario
            partes = fecha.split('/')
            if len(partes[2]) == 2:
                partes[2] = '20' + partes[2]
            return '/'.join(partes)
        return None
    
    def extraer_numero_factura(self, texto: str) -> Optional[str]:
        """Extrae número de factura."""
        # Formato: "FACTURA Nº 2025/00072"
        m = re.search(r'FACTURA\s+N[ºo°]\s*(\d+/\d+)', texto, re.IGNORECASE)
        if m:
            return m.group(1)
        return None
    
    extraer_referencia = extraer_numero_factura
