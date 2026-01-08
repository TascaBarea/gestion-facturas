"""
Extractor para DEBORA GARCIA TOLEDANO

Suministro de CO2 alimentario para cerveza.
NIF: 47524622K
IBAN: ES84 0049 0821 9627 1013 3112 (Banco Santander)

Formato factura (pdfplumber):
- Base imponible + IVA 21% - IRPF 1% = Total
- El IRPF se añade como línea negativa con IVA 0% para cuadrar

IVA: 21%
IRPF: 1% (retención) - SE RESTA DEL TOTAL
Categoría fija: Co2 GAS PARA LA CERVEZA

Creado: 26/12/2025
Corregido: 29/12/2025 - IRPF como línea negativa para cuadre
"""
from extractores.base import ExtractorBase
from extractores import registrar
from typing import List, Dict, Optional
import re


@registrar('DEBORA GARCIA TOLEDANO', 'DEBORAH GARCIA', 'DEBORA GARCIA', 
           'BEDORAH GARCIA TOLEDANO', 'DG CO2')
class ExtractorDeboraGarcia(ExtractorBase):
    """Extractor para facturas de DEBORA GARCIA TOLEDANO (CO2)."""
    
    nombre = 'DEBORA GARCIA'
    cif = '47524622K'
    iban = 'ES84 0049 0821 9627 1013 3112'
    metodo_pdf = 'pdfplumber'
    categoria_fija = 'Co2 GAS PARA LA CERVEZA'
    
    def extraer_lineas(self, texto: str) -> List[Dict]:
        """
        Extrae líneas de CO2 + IRPF negativo.
        
        Para que cuadre con el sistema de validación:
        - Línea CO2: base × 1.21 = X
        - Línea IRPF: -irpf × 1.00 = -Y
        - Total = X - Y = Total factura
        """
        lineas = []
        
        # Buscar "Base imponible" para obtener la base
        match_base = re.search(
            r'Base\s+imponible\s+(\d+[.,]\d{2})\s*€',
            texto,
            re.IGNORECASE
        )
        
        if match_base:
            base = self._convertir_europeo(match_base.group(1))
            
            # Buscar cantidad (formato con Q)
            cantidad = 1
            match_con_cantidad = re.search(
                r'(\d+[.,]\d{2})\s*€\s+(\d+)\s+(\d+[.,]\d{2})\s*€\s+\d+[.,]\d{2}\s*€\s*\(21%\)',
                texto
            )
            
            if match_con_cantidad:
                precio_ud = self._convertir_europeo(match_con_cantidad.group(1))
                cantidad = int(match_con_cantidad.group(2))
                base_linea = self._convertir_europeo(match_con_cantidad.group(3))
                if abs(precio_ud * cantidad - base_linea) < 0.01:
                    base = base_linea
            
            if base > 0:
                # Línea principal: CO2
                lineas.append({
                    'codigo': 'CO2',
                    'articulo': 'BOTELLA 10KG CO2 ALIMENTARIO',
                    'cantidad': cantidad,
                    'precio_ud': round(base / cantidad, 2) if cantidad else base,
                    'iva': 21,
                    'base': round(base, 2),
                    'categoria': self.categoria_fija
                })
                
                # Línea IRPF: negativa con IVA 0% para que cuadre
                # IRPF = 1% de la base
                irpf = round(base * 0.01, 2)
                lineas.append({
                    'codigo': 'IRPF',
                    'articulo': 'RETENCION IRPF 1%',
                    'cantidad': 1,
                    'precio_ud': -irpf,
                    'iva': 0,
                    'base': -irpf,
                    'categoria': self.categoria_fija
                })
        
        return lineas
    
    def _convertir_europeo(self, texto: str) -> float:
        """Convierte formato europeo a float."""
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
        m = re.search(r'^Total\s+(\d+[.,]\d{2})\s*€', texto, re.MULTILINE | re.IGNORECASE)
        if m:
            return self._convertir_europeo(m.group(1))
        return None
    
    def extraer_fecha(self, texto: str) -> Optional[str]:
        """Extrae fecha de la factura."""
        m = re.search(r'Emitida\s+(\d{2})/(\d{2})/(\d{4})', texto)
        if m:
            return f"{m.group(1)}/{m.group(2)}/{m.group(3)}"
        return None
    
    def extraer_numero_factura(self, texto: str) -> Optional[str]:
        """Extrae número de factura."""
        # Formato: "Factura nº F2025-241"
        m = re.search(r'Factura\s+n[ºo°]\s*(F\d+-\d+)', texto, re.IGNORECASE)
        if m:
            return m.group(1)
        return None
    
    # Alias para main.py
    extraer_referencia = extraer_numero_factura
