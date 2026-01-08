"""
Extractor para ALFARERIA ANGEL Y LOLI

Alfareria artesanal de Nijar (Almeria).
NIF: REDACTED_DNI (autonomo Lorenzo Lores Garcia)

Productos: Platos, cuencos, vasos, chupitos (ceramica artesanal)
IVA: 21%
Categoria: MENAJE / VAJILLA

Formato factura:
ARTICULO CANTIDAD PRECIO TOTAL
PLATO LLANO 20 5,70 114,00
CUENCO 10 CM 15 2,07 31,05   <- Cuidado: "10 CM" en el nombre

Cuadro fiscal:
TIPO IMPORTE DESCUENTO PORTES BASE I.V.A. R.E.
21,00 549,50 45,00 594,50 124,85

NOTA: Detecta automaticamente si el segundo numero es DESCUENTO o PORTES:
- Si IMPORTE + segundo = BASE → es PORTES
- Si IMPORTE - segundo = BASE → es DESCUENTO (se aplica proporcional)

Creado: 30/12/2025
"""
from extractores.base import ExtractorBase
from extractores import registrar
from typing import List, Dict, Optional
import re


@registrar('ALFARERIA ANGEL Y LOLI', 'ANGEL Y LOLI', 'ANGEL Y LOLI ALFARERIA',
           'ALFARERIA ANGEL', 'LORENZO LORES')
class ExtractorAlfareria(ExtractorBase):
    """Extractor para facturas de ALFARERIA ANGEL Y LOLI."""
    
    nombre = 'ALFARERIA ANGEL Y LOLI'
    cif = 'REDACTED_DNI'
    iban = None  # Autonomo, pago por transferencia directa
    metodo_pdf = 'pdfplumber'
    categoria_fija = 'MENAJE'
    
    def extraer_lineas(self, texto: str) -> List[Dict]:
        """
        Extrae lineas de productos.
        
        Formato:
        ARTICULO CANTIDAD PRECIO TOTAL
        PLATO LLANO 20 5,70 114,00
        CUENCO 10 CM 15 2,07 31,05
        
        El patron captura los 3 ultimos numeros, el resto es articulo.
        Esto permite capturar correctamente "CUENCO 10 CM".
        """
        lineas = []
        
        # Patron: ARTICULO (todo hasta los ultimos 3 numeros) CANTIDAD PRECIO TOTAL
        patron = re.compile(r'^(.+?)\s+(\d+)\s+([\d,]+)\s+([\d,]+)$')
        
        en_productos = False
        
        for linea in texto.split('\n'):
            linea = linea.strip()
            if not linea:
                continue
            
            # Detectar inicio de productos
            if 'ARTÍCULO' in linea and 'CANTIDAD' in linea:
                en_productos = True
                continue
            
            # Detectar fin de productos (cuadro fiscal)
            if 'TIPO' in linea and 'IMPORTE' in linea:
                en_productos = False
                continue
            
            if not en_productos:
                continue
            
            m = patron.match(linea)
            if m:
                articulo = m.group(1).strip()
                cantidad = int(m.group(2))
                precio = self._convertir_europeo(m.group(3))
                total = self._convertir_europeo(m.group(4))
                
                if total > 0:
                    lineas.append({
                        'codigo': '',
                        'articulo': articulo[:50],
                        'cantidad': cantidad,
                        'precio_ud': round(precio, 2),
                        'base': round(total, 2),
                        'iva': 21,
                        'categoria': self.categoria_fija
                    })
        
        # Extraer del cuadro fiscal: TIPO IMPORTE DESCUENTO PORTES BASE IVA
        # Formato: "21,00 549,50 45,00 594,50 124,85"
        m_fiscal = re.search(r'21[,.]00\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)', texto)
        if m_fiscal:
            importe = self._convertir_europeo(m_fiscal.group(1))
            segundo = self._convertir_europeo(m_fiscal.group(2))
            base = self._convertir_europeo(m_fiscal.group(3))
            
            # Detectar si es DESCUENTO o PORTES
            # Si importe + segundo ≈ base → es PORTES
            # Si importe - segundo ≈ base → es DESCUENTO
            
            if abs((importe + segundo) - base) < 0.10:
                # Es PORTES - añadir linea de porte (main.py lo prorrateara)
                if segundo > 0:
                    lineas.append({
                        'codigo': 'PORTE',
                        'articulo': 'PORTES',
                        'cantidad': 1,
                        'precio_ud': round(segundo, 2),
                        'base': round(segundo, 2),
                        'iva': 21,
                        'categoria': 'TRANSPORTE'
                    })
            elif abs((importe - segundo) - base) < 0.10:
                # Es DESCUENTO - aplicar descuento proporcional a las lineas
                if segundo > 0 and importe > 0:
                    factor_descuento = 1 - (segundo / importe)
                    for linea in lineas:
                        linea['base'] = round(linea['base'] * factor_descuento, 2)
                        if linea.get('precio_ud') and linea.get('cantidad'):
                            linea['precio_ud'] = round(linea['base'] / linea['cantidad'], 4)
        
        return lineas
    
    def _convertir_europeo(self, texto: str) -> float:
        """Convierte formato europeo a float."""
        if not texto:
            return 0.0
        texto = texto.strip().replace(',', '.')
        try:
            return float(texto)
        except:
            return 0.0
    
    def extraer_total(self, texto: str) -> Optional[float]:
        """Extrae total de la factura."""
        # Formato: "TOTAL: 719,35"
        m = re.search(r'TOTAL:\s*([\d.,]+)', texto)
        if m:
            return self._convertir_europeo(m.group(1))
        return None
    
    def extraer_fecha(self, texto: str) -> Optional[str]:
        """Extrae fecha de la factura."""
        # Formato en cuadro: "Factura 000064 1 03/07/2025"
        m = re.search(r'Factura\s+\d+\s+\d+\s+(\d{2}/\d{2}/\d{4})', texto)
        if m:
            return m.group(1)
        return None
    
    def extraer_numero_factura(self, texto: str) -> Optional[str]:
        """Extrae numero de factura."""
        # Formato: "Factura 000064 1 03/07/2025"
        m = re.search(r'Factura\s+(\d+)', texto)
        if m:
            return m.group(1)
        return None
    
    extraer_referencia = extraer_numero_factura
