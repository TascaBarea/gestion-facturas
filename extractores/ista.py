"""
Extractor para ISTA (Liquidacion de Consumos de Agua)

Servicio de medicion y reparto de costes de agua.
No tiene CIF en la factura (es una liquidacion, no factura fiscal).

Formato factura (pdfplumber):
Fecha de recibo: 20/03/2025
...
LIQUIDACION
ID CONCEPTO CONSUMO IMPORTE IVA
470239 Consumo (A.Fria) 40 34,04 10%
470239 Cuotas de Servicio del Canal de Isabel II (A.Fria) 15,60 10%
BASE IMP. % IMP. IVA
49,64 10% 4,96
Importe total 54,60 E

Categoria: CONSUMO AGUA FRIA (siempre)
IVA: 10%

Creado: 19/12/2025
"""
from extractores.base import ExtractorBase
from extractores import registrar
from typing import List, Dict, Optional
import re


@registrar('ISTA', 'ISTA 2')
class ExtractorIsta(ExtractorBase):
    """Extractor para liquidaciones de ISTA."""
    
    nombre = 'ISTA'
    cif = ''  # No tiene CIF, es liquidacion de consumos
    iban = ''
    metodo_pdf = 'pdfplumber'
    
    def extraer_lineas(self, texto: str) -> List[Dict]:
        """
        Extrae lineas de la liquidacion.
        
        Formatos:
        470239 Consumo (A.Fria) 40 34,04 10%
        470239 Cuotas de Servicio del Canal de Isabel II (A.Fria) 15,60 10%
        """
        lineas = []
        
        # Patron para lineas con consumo: ID CONCEPTO CONSUMO IMPORTE IVA%
        # 470239 Consumo (A.Fria) 40 34,04 10%
        patron_con_consumo = re.compile(
            r'(\d{6})\s+'                              # ID (6 digitos)
            r'(Consumo\s*\([^)]+\))\s+'                # Concepto con consumo
            r'(\d+)\s+'                                # Consumo (unidades)
            r'(\d+,\d{2})\s+'                          # Importe
            r'(\d+)%'                                  # IVA
        )
        
        for match in patron_con_consumo.finditer(texto):
            concepto = match.group(2).strip()
            consumo = int(match.group(3))
            importe = self._convertir_europeo(match.group(4))
            iva = int(match.group(5))
            
            if importe > 0:
                lineas.append({
                    'codigo': match.group(1),
                    'articulo': 'CONSUMO AGUA FRIA',
                    'cantidad': consumo,
                    'precio_ud': round(importe / consumo, 4) if consumo > 0 else importe,
                    'iva': iva,
                    'base': round(importe, 2),
                    'categoria': 'CONSUMO AGUA FRIA'
                })
        
        # Patron para cuotas de servicio (sin consumo): ID CONCEPTO IMPORTE IVA%
        # 470239 Cuotas de Servicio del Canal de Isabel II (A.Fria) 15,60 10%
        patron_cuotas = re.compile(
            r'(\d{6})\s+'                              # ID
            r'(Cuotas\s+de\s+Servicio[^)]+\))\s+'      # Concepto cuotas
            r'(\d+,\d{2})\s+'                          # Importe
            r'(\d+)%'                                  # IVA
        )
        
        for match in patron_cuotas.finditer(texto):
            importe = self._convertir_europeo(match.group(3))
            iva = int(match.group(4))
            
            if importe > 0:
                lineas.append({
                    'codigo': match.group(1),
                    'articulo': 'CONSUMO AGUA FRIA',
                    'cantidad': 1,
                    'precio_ud': round(importe, 2),
                    'iva': iva,
                    'base': round(importe, 2),
                    'categoria': 'CONSUMO AGUA FRIA'
                })
        
        # Si no encontramos lineas detalladas, usar la base imponible total
        if not lineas:
            # Buscar: BASE IMP. % IMP. IVA\n49,64 10% 4,96
            patron_base = re.search(r'BASE\s+IMP\.\s+%\s+IMP\.\s+IVA\s*\n\s*(\d+,\d{2})\s+(\d+)%', texto)
            if patron_base:
                base = self._convertir_europeo(patron_base.group(1))
                iva = int(patron_base.group(2))
                if base > 0:
                    lineas.append({
                        'codigo': '',
                        'articulo': 'CONSUMO AGUA FRIA',
                        'cantidad': 1,
                        'precio_ud': round(base, 2),
                        'iva': iva,
                        'base': round(base, 2),
                        'categoria': 'CONSUMO AGUA FRIA'
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
    
    def extraer_total(self, texto: str) -> Optional[float]:
        # Formato ISTA: el total esta ANTES de "Importe total"
        # 56,11 €
        # Importe total
        patron = re.search(r'(\d+,\d{2})\s*€?\s*\n\s*Importe\s+total', texto, re.IGNORECASE)
        if patron:
            return self._convertir_europeo(patron.group(1))
        
        # Alternativo: buscar XX,XX € seguido de Importe total en misma linea
        patron2 = re.search(r'(\d+,\d{2})\s*€\s*Importe\s+total', texto, re.IGNORECASE)
        if patron2:
            return self._convertir_europeo(patron2.group(1))
        
        return None
    
    def extraer_fecha(self, texto: str) -> Optional[str]:
        # Formato: Fecha de recibo: 20/03/2025
        patron = re.search(r'Fecha\s+de\s+recibo:\s*(\d{2})/(\d{2})/(\d{4})', texto)
        if patron:
            return f"{patron.group(1)}/{patron.group(2)}/{patron.group(3)}"
        
        # Alternativo: Fecha de recibo: DD/MM/YYYY en otra linea
        patron2 = re.search(r'Fecha\s+de\s+recibo:\s*\n?\s*(\d{2})/(\d{2})/(\d{4})', texto)
        if patron2:
            return f"{patron2.group(1)}/{patron2.group(2)}/{patron2.group(3)}"
        
        return None
