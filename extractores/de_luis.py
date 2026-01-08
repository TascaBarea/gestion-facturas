"""
Extractor para DE LUIS SABORES UNICOS S.L.
CIF: B86249711

Proveedor de quesos (Cañarejal). Todo al 4% IVA (quesos).

Estructura factura:
- Líneas de producto: el campo "Total" es la BASE (sin IVA)
- Cuadro fiscal: B. Imponible | I.V.A. | Cuota IVA | TOTAL Fra.
- Ejemplo: 334,14 | 4% | 13,37 | 347,51

ESTRATEGIA: Usar el cuadro fiscal para garantizar cuadre perfecto.

Creado: 01/01/2026
"""
from extractores.base import ExtractorBase
from extractores import registrar
from typing import List, Dict, Optional
import re


@registrar('DE LUIS SABORES UNICOS', 'DE LUIS', 'DE LUIS SABORES', 
           'JAMONES LIEBANA', 'JAMONESLIEBANA')
class ExtractorDeLuis(ExtractorBase):
    """Extractor para facturas de DE LUIS SABORES UNICOS."""
    
    nombre = 'DE LUIS SABORES UNICOS'
    cif = 'B86249711'
    iban = 'ES53 0049 1920 1021 1019 2545'  # Banco Santander
    metodo_pdf = 'pdfplumber'
    
    def _convertir_importe(self, texto: str) -> float:
        """Convierte texto a float (formato europeo)."""
        if not texto:
            return 0.0
        texto = str(texto).strip().replace('€', '').replace(' ', '')
        if ',' in texto and '.' in texto:
            texto = texto.replace('.', '').replace(',', '.')
        elif ',' in texto:
            texto = texto.replace(',', '.')
        try:
            return float(texto)
        except:
            return 0.0
    
    def extraer_cuadro_fiscal(self, texto: str) -> Dict:
        """
        Extrae el cuadro fiscal de la factura.
        Formato: "334,14 334,14 4% 13,37" seguido de "347,51" en línea aparte
        """
        # Buscar línea con patrón: BASE BASE IVA% CUOTA_IVA
        # Ej: "334,14 334,14 4% 13,37"
        m = re.search(r'([\d.,]+)\s+([\d.,]+)\s+(\d+)%\s+([\d.,]+)', texto)
        if m:
            importe_bruto = self._convertir_importe(m.group(1))
            base = self._convertir_importe(m.group(2))
            iva_tipo = int(m.group(3))
            cuota_iva = self._convertir_importe(m.group(4))
            
            return {
                'base': base,
                'iva_tipo': iva_tipo,
                'cuota_iva': cuota_iva,
                'total': round(base + cuota_iva, 2)
            }
        
        return None
    
    def extraer_lineas(self, texto: str) -> List[Dict]:
        """
        Genera líneas basadas en el cuadro fiscal.
        DE LUIS solo tiene IVA 4% (quesos), así que creamos una línea virtual.
        """
        lineas = []
        cuadro = self.extraer_cuadro_fiscal(texto)
        
        if cuadro:
            lineas.append({
                'articulo': 'QUESOS CAÑAREJAL (IVA 4%)',
                'base': cuadro['base'],
                'iva': cuadro['iva_tipo'],
                'categoria': 'QUESOS',
                'cantidad': 1,
                'precio_ud': cuadro['base']
            })
        else:
            # Fallback: extraer líneas individuales
            lineas = self._extraer_lineas_detalle(texto)
        
        return lineas
    
    def _extraer_lineas_detalle(self, texto: str) -> List[Dict]:
        """
        Extrae líneas de producto individuales (fallback).
        Formato: NUM CODIGO DESCRIPCION CANTIDAD KILOS PRECIO TOTAL IVA%
        """
        lineas = []
        
        # Patrón para líneas de producto
        # Ej: "1 O760 CREMA DE QUESO "CAÑAREJAL" 200 GR. 6 6 7,19 43,14 4%"
        patron = re.compile(
            r'^\d+\s+'                    # Número de línea
            r'([A-Z]\d+)\s+'              # Código (O760, O765, O711)
            r'(.+?)\s+'                   # Descripción
            r'(\d+)\s+'                   # Cantidad
            r'([\d.,]+)\s+'               # Kilos
            r'([\d.,]+)\s+'               # Precio
            r'([\d.,]+)\s+'               # Total (BASE)
            r'(\d+)%',                    # IVA%
            re.MULTILINE
        )
        
        for m in patron.finditer(texto):
            codigo, desc, cantidad, kilos, precio, total, iva = m.groups()
            
            lineas.append({
                'articulo': desc.strip()[:50],
                'codigo': codigo,
                'cantidad': int(cantidad),
                'precio_ud': self._convertir_importe(precio),
                'base': self._convertir_importe(total),  # Total = Base (sin IVA)
                'iva': int(iva),
                'categoria': 'QUESOS'
            })
        
        return lineas
    
    def extraer_total(self, texto: str) -> Optional[float]:
        """Extrae el total de la factura."""
        # Método 1: Buscar número suelto después del cuadro fiscal (el TOTAL Fra.)
        # El total suele estar en una línea aparte después de la cuota IVA
        cuadro = self.extraer_cuadro_fiscal(texto)
        if cuadro:
            return cuadro['total']
        
        # Método 2: Buscar "T O T A L Fra." o similar
        m = re.search(r'T\s*O\s*T\s*A\s*L\s*Fra\.?\s*([\d.,]+)', texto)
        if m:
            return self._convertir_importe(m.group(1))
        
        # Método 3: Buscar número grande después de "Cuota IVA"
        m2 = re.search(r'Cuota IVA.*?R\.Equivalencia.*?([\d.,]+)\s*$', texto, re.MULTILINE | re.DOTALL)
        if m2:
            return self._convertir_importe(m2.group(1))
        
        return None
    
    def extraer_fecha(self, texto: str) -> Optional[str]:
        """Extrae fecha de la factura."""
        # Buscar "Fecha DD/MM/YYYY" cerca de "Número"
        m = re.search(r'Fecha\s+(\d{2})/(\d{2})/(\d{4})', texto)
        if m:
            dia, mes, año = m.groups()
            return f"{dia}-{mes}-{año}"
        return None
    
    def extraer_referencia(self, texto: str) -> Optional[str]:
        """Extrae número de factura."""
        # Formato: "Número 25 - 5469"
        m = re.search(r'Número\s+(\d+)\s*-\s*(\d+)', texto)
        if m:
            return f"{m.group(1)}-{m.group(2)}"
        return None
