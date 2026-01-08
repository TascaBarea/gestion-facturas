"""
Extractor para LA CONSERVERA DEL PREPIRINEO, S.COOP.P

Cooperativa de conservas vegetales artesanales de Uncastillo (Zaragoza).
Especialidad en patés vegetales.

CIF: F50765338
IBAN: ES78 2085 0871 6703 3009 9948

Productos (IVA 10% - conservas vegetales):
- Paté de pimientos verdes fritos
- Paté de setas con especias
- Paté de boletus
- Paté de tomates secos
- Paté de pisto
- Paté de calabacín con nueces
- Paté de berenjenas
- Paté de olivas de Aragón con cebolla
- Paté de olivas verdes (arbequina)
- Paté vegetal sabor chorizo
- Paté vegetal sabor foie
- Paté de pimientos asados

Formato líneas:
CÓDIGO DESCRIPCIÓN CANTIDAD PRECIO SUBTOTAL TOTAL
105PV121 PATÉ DE PIMIENTOS VERDES FRITOS 24,00 2,65 63,60 63,60

Creado: 01/01/2026
Validado: 2/2 facturas (3T25-4T25)
"""
from extractores.base import ExtractorBase
from extractores import registrar
from typing import List, Dict, Optional
import re


@registrar('CONSERVERA PREPIRINEO', 'LA CONSERVERA DEL PREPIRINEO', 
           'CONSERVERA DEL PREPIRINEO', 'PREPIRINEO',
           'LA CONSERVERA DEL PREPIRINEO S.COOP.P')
class ExtractorConserveraPrepirineo(ExtractorBase):
    """Extractor para facturas de La Conservera del Prepirineo."""
    
    nombre = 'LA CONSERVERA DEL PREPIRINEO'
    cif = 'F50765338'
    iban = 'ES78 2085 0871 6703 3009 9948'
    metodo_pdf = 'pdfplumber'
    categoria_fija = 'CONSERVAS VEGETALES'
    
    def _convertir_importe(self, texto: str) -> float:
        """Convierte texto a float (formato europeo)."""
        if not texto:
            return 0.0
        texto = str(texto).strip().replace(' ', '')
        if '.' in texto and ',' in texto:
            texto = texto.replace('.', '').replace(',', '.')
        elif ',' in texto:
            texto = texto.replace(',', '.')
        try:
            return float(texto)
        except:
            return 0.0
    
    def extraer_lineas(self, texto: str) -> List[Dict]:
        """
        Extrae líneas de productos.
        
        Formato:
        CÓDIGO DESCRIPCIÓN CANTIDAD PRECIO SUBTOTAL TOTAL
        105PV121 PATÉ DE PIMIENTOS VERDES FRITOS 24,00 2,65 63,60 63,60
        """
        lineas = []
        
        # Patrón para líneas de patés (acepta minúsculas en paréntesis)
        patron = re.compile(
            r'^(\d{3}[A-Z0-9]+)\s+'                      # Código (105PV121)
            r'(PAT[ÉE][A-ZÁÉÍÓÚÑa-záéíóúñ\s\(\)]+?)\s+'  # Descripción
            r'(\d+[,.]00)\s+'                             # Cantidad
            r'(\d+[,.]?\d*)\s+'                           # Precio unitario
            r'(\d+[,.]?\d+)\s+'                           # Subtotal
            r'(\d+[,.]?\d+)',                             # Total
            re.MULTILINE
        )
        
        for m in patron.finditer(texto):
            codigo, descripcion, cantidad, precio, subtotal, total = m.groups()
            
            lineas.append({
                'codigo': codigo,
                'articulo': descripcion.strip()[:50],
                'cantidad': self._convertir_importe(cantidad),
                'precio_ud': self._convertir_importe(precio),
                'iva': 10,  # Siempre IVA 10% (conservas)
                'base': self._convertir_importe(total),
                'categoria': self.categoria_fija
            })
        
        return lineas
    
    def extraer_total(self, texto: str) -> Optional[float]:
        """Extrae total de la factura."""
        # Buscar "TOTAL:" seguido de número
        m = re.search(r'TOTAL:\s*([\d,.]+)', texto)
        if m:
            return self._convertir_importe(m.group(1))
        
        # Alternativa: buscar en vencimientos
        m2 = re.search(r'Vencimientos.*?\n[\d/]+\s+([\d,.]+)', texto, re.DOTALL)
        if m2:
            return self._convertir_importe(m2.group(1))
        
        return None
    
    def extraer_cuadro_fiscal(self, texto: str) -> List[Dict]:
        """
        Extrae cuadro fiscal.
        
        Formato:
        TIPO IMPORTE DESCUENTO PRONTO PAGO PORTES FINANCIACIÓN BASE I.V.A. R.E.
        10,00 381,60                                          381,60 38,16
        """
        cuadros = []
        
        # IVA 10% (principal para conservas)
        m10 = re.search(r'10[,.]00\s+([\d,.]+)\s+([\d,.]+)\s+([\d,.]+)', texto)
        if m10:
            cuadros.append({
                'iva': 10,
                'importe': self._convertir_importe(m10.group(1)),
                'base': self._convertir_importe(m10.group(2)),
                'cuota': self._convertir_importe(m10.group(3))
            })
        
        # IVA 21% (por si hay otros productos)
        m21 = re.search(r'21[,.]00\s+([\d,.]+)\s+([\d,.]+)\s+([\d,.]+)', texto)
        if m21:
            cuadros.append({
                'iva': 21,
                'importe': self._convertir_importe(m21.group(1)),
                'base': self._convertir_importe(m21.group(2)),
                'cuota': self._convertir_importe(m21.group(3))
            })
        
        return cuadros
    
    def extraer_fecha(self, texto: str) -> Optional[str]:
        """Extrae fecha de la factura."""
        # Formato: "Factura 1 250200 1 25/09/2025"
        m = re.search(r'Factura\s+\d+\s+\d+\s+\d+\s+(\d{2}/\d{2}/\d{4})', texto)
        if m:
            return m.group(1)
        return None
    
    def extraer_referencia(self, texto: str) -> Optional[str]:
        """Extrae número de factura."""
        # Formato: "Factura 1 250200 1 25/09/2025" -> número es 250200
        m = re.search(r'Factura\s+\d+\s+(\d+)\s+\d+\s+\d{2}/\d{2}/\d{4}', texto)
        if m:
            return m.group(1)
        return None
