# -*- coding: utf-8 -*-
"""
Extractor para CONSERVAS ARTESANAS CURRICÁN S.L. (CURRIMAR)

Conservas de mar artesanales de Galicia.
CIF: B27431162
IBAN: ES67 0238 8166 9706 0004 9215 (Banco Santander)
Dirección: P.I. Camba Parcela 29-30, 27877-XOVE (Lugo)

Productos: Pulpo AOVE, Fabas con pulpo, Marmitako, Calamares, Albóndigas bonito...
Categoría fija: CONSERVAS MAR
IVA: 10% (conservas alimenticias)

PORTES:
- A veces incluyen portes (21%)
- Los portes se prorratean entre los productos (coste CON IVA)

Formato factura:
Nº BULTO  EAN 13          PRODUCTO                    ML. GR.Neto UDS. LOTE  PRECIO UD.  TOTAL
1+2/2     8437013825320   Pulpo AOVE                  138 100     24   25226 7,45 €      178,80 €

BASE IMPONIBLE     178,80 €
I.V.A. 10%          17,88 €
PORTES               - €
I.V.A. 21% portes    - €
TOTAL FACTURA      196,68 €

Soporta facturas rectificativas (cantidades negativas).

Creado: 06/01/2026
Validado: 6/6 facturas
"""
from extractores.base import ExtractorBase
from extractores import registrar
from typing import List, Dict, Optional
import re


@registrar('CURRICAN', 'CURRICÁN', 'CURRIMAR', 'CONSERVAS CURRICAN', 
           'CONSERVAS ARTESANAS CURRICAN', 'CONSERVAS ARTESANAS CURRICÁN')
class ExtractorCurrican(ExtractorBase):
    """Extractor para facturas de CONSERVAS CURRICAN / CURRIMAR."""
    
    nombre = 'CONSERVAS CURRICAN'
    cif = 'B27431162'
    iban = 'ES67 0238 8166 9706 0004 9215'
    metodo_pdf = 'pdfplumber'
    categoria_fija = 'CONSERVAS MAR'
    
    def _convertir_europeo(self, texto: str) -> float:
        """Convierte formato europeo a float."""
        if not texto:
            return 0.0
        texto = str(texto).strip().replace('€', '').replace(' ', '')
        if texto == '-' or texto == '':
            return 0.0
        # Manejar negativos
        negativo = texto.startswith('-')
        texto = texto.replace('-', '')
        
        if '.' in texto and ',' in texto:
            texto = texto.replace('.', '').replace(',', '.')
        elif ',' in texto:
            texto = texto.replace(',', '.')
        try:
            valor = float(texto)
            return -valor if negativo else valor
        except:
            return 0.0
    
    def _extraer_portes(self, texto: str) -> float:
        """Extrae PORTES (base 21%) - devuelve coste CON IVA para prorratear."""
        match = re.search(r'PORTES\s+([\d,]+)\s*€', texto)
        if match:
            base_portes = self._convertir_europeo(match.group(1))
            return round(base_portes * 1.21, 2)  # Coste CON IVA
        return 0.0
    
    def extraer_lineas(self, texto: str) -> List[Dict]:
        """
        Extrae líneas de productos.
        
        Formato: NºBULTO EAN13 PRODUCTO ML GR.Neto UDS LOTE PRECIO TOTAL
        """
        lineas = []
        
        # Patrón para líneas de producto
        # Ejemplo: 1+2/2 8437013825320 Pulpo AOVE 138 100 24 25226 7,45 € 178,80 €
        patron = re.compile(
            r'[\d\+\-/]+\s+'              # Nº BULTO (1+2/2, 3-5/5, etc)
            r'\d{13}\s+'                   # EAN13
            r'(.+?)\s+'                    # PRODUCTO
            r'\d+\s+\d+\s+'                # ML GR.Neto
            r'(-?\d+)\s+'                  # UDS (puede ser negativo)
            r'\d+\s+'                      # LOTE
            r'([\d,]+)\s*€?\s*'            # PRECIO
            r'(-?[\d,]+)\s*€'              # TOTAL (puede ser negativo)
        )
        
        for match in patron.finditer(texto):
            producto = match.group(1).strip()
            uds = int(match.group(2))
            precio = self._convertir_europeo(match.group(3))
            total = self._convertir_europeo(match.group(4))
            
            lineas.append({
                'codigo': producto[:3].upper(),
                'articulo': producto[:50],
                'cantidad': abs(uds),
                'precio_ud': round(precio, 2),
                'base': round(total, 2),  # Puede ser negativo en rectificativas
                'iva': 10,
                'categoria': self.categoria_fija
            })
        
        # Extraer y prorratear portes
        portes_con_iva = self._extraer_portes(texto)
        if portes_con_iva > 0 and lineas:
            total_productos = sum(abs(l['base']) for l in lineas)
            if total_productos > 0:
                for linea in lineas:
                    proporcion = abs(linea['base']) / total_productos
                    extra = portes_con_iva * proporcion
                    # Si base es negativa (rectificativa), no añadir portes
                    if linea['base'] > 0:
                        linea['base'] = round(linea['base'] + extra, 2)
        
        return lineas
    
    def extraer_total(self, texto: str) -> Optional[float]:
        """Extrae total de la factura."""
        match = re.search(r'TOTAL\s+FACTURA\s+(-?[\d,.\s]+)\s*€', texto, re.IGNORECASE)
        if match:
            return self._convertir_europeo(match.group(1).replace(' ', ''))
        return None
    
    def extraer_fecha(self, texto: str) -> Optional[str]:
        """Extrae fecha de la factura."""
        # Formato: Xove, 22-oct.-2025
        meses = {
            'ene': '01', 'feb': '02', 'mar': '03', 'abr': '04',
            'may': '05', 'jun': '06', 'jul': '07', 'ago': '08',
            'sep': '09', 'oct': '10', 'nov': '11', 'dic': '12'
        }
        match = re.search(r'(\d{1,2})-([a-z]{3})\.?-(\d{4})', texto, re.IGNORECASE)
        if match:
            dia = match.group(1).zfill(2)
            mes = meses.get(match.group(2).lower(), '01')
            año = match.group(3)
            return f"{dia}/{mes}/{año}"
        return None
    
    def extraer_numero_factura(self, texto: str) -> Optional[str]:
        """Extrae número de factura."""
        # Factura normal: 0621/25
        match = re.search(r'Nº\s*FACTURA[^\d]*(\d+/\d+)', texto, re.IGNORECASE)
        if match:
            return match.group(1)
        # Factura rectificativa: R011/25
        match = re.search(r'FACTURA\s+RECTIFICATIVA\s+([R\d]+/\d+)', texto, re.IGNORECASE)
        if match:
            return match.group(1)
        return None
