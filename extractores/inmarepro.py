"""
Extractor para INMAREPRO, S.L.

Empresa de mantenimiento de extintores.
CIF: B80183429

Formato factura:
- Siempre una unica linea: "Mantenimiento de extintores..."
- IVA: 21%
- Categoria fija: GASTOS VARIOS

Cuadro fiscal:
€ 57,57 57,57 12,09 69,66
  ^importe ^base ^iva ^total

Creado: 30/12/2025
"""
from extractores.base import ExtractorBase
from extractores import registrar
from typing import List, Dict, Optional
import re


@registrar('INMAREPRO', 'INMAREPRO SL', 'INMAREPRO S.L.')
class ExtractorInmarepro(ExtractorBase):
    """Extractor para facturas de INMAREPRO (extintores)."""
    
    nombre = 'INMAREPRO'
    cif = 'B80183429'
    iban = None  # Pago por domiciliacion
    metodo_pdf = 'pdfplumber'
    categoria_fija = 'GASTOS VARIOS'
    
    def extraer_lineas(self, texto: str) -> List[Dict]:
        """
        Extrae una unica linea con el importe total del mantenimiento.
        
        INMAREPRO siempre factura "Mantenimiento de extintores" como
        concepto unico, independientemente de si hay detalle de materiales.
        """
        lineas = []
        
        # Extraer base imponible del cuadro fiscal
        # Formato: "€ 57,57 57,57 12,09 69,66"
        #           importe base  iva   total
        m = re.search(r'€\s+([\d.,]+)\s+([\d.,]+)\s+([\d.,]+)\s+([\d.,]+)', texto)
        if m:
            base = self._convertir_europeo(m.group(2))
            
            if base > 0:
                lineas.append({
                    'codigo': '',
                    'articulo': 'MANTENIMIENTO EXTINTORES',
                    'cantidad': 1,
                    'precio_ud': round(base, 2),
                    'iva': 21,
                    'base': round(base, 2),
                    'categoria': self.categoria_fija
                })
        
        return lineas
    
    def _convertir_europeo(self, texto: str) -> float:
        """Convierte formato europeo a float."""
        if not texto:
            return 0.0
        texto = texto.strip().replace('.', '').replace(',', '.')
        try:
            return float(texto)
        except:
            return 0.0
    
    def extraer_total(self, texto: str) -> Optional[float]:
        """Extrae total de la factura."""
        # Formato cuadro: "€ 57,57 57,57 12,09 69,66"
        m = re.search(r'€\s+[\d.,]+\s+[\d.,]+\s+[\d.,]+\s+([\d.,]+)', texto)
        if m:
            return self._convertir_europeo(m.group(1))
        
        # Alternativa: "TOTAL 69,66"
        m = re.search(r'TOTAL\s+([\d.,]+)', texto)
        if m:
            return self._convertir_europeo(m.group(1))
        
        return None
    
    def extraer_fecha(self, texto: str) -> Optional[str]:
        """Extrae fecha de la factura."""
        # Formato: "31/10/2025" en la cabecera
        m = re.search(r'(\d{2}/\d{2}/\d{4})', texto)
        if m:
            return m.group(1)
        return None
    
    def extraer_numero_factura(self, texto: str) -> Optional[str]:
        """Extrae numero de factura."""
        # Formato: "FV25-3976" o "FV24-3899"
        m = re.search(r'(FV\d{2}-\d+)', texto)
        if m:
            return m.group(1)
        return None
    
    extraer_referencia = extraer_numero_factura
