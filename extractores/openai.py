"""
Extractor para OPENAI, LLC

Suscripción ChatGPT Plus.
EU OSS VAT: EU372041333
IVA: 0% (reverse charge - extranjero)
Categoría fija: GASTOS VARIOS
Moneda: USD - se convierte a EUR con tipo de cambio del día

Creado: 26/12/2025
"""
from extractores.base import ExtractorBase
from extractores import registrar
from typing import List, Dict, Optional
import re
import urllib.request
import json


@registrar('OPENAI', 'OPENAI LLC', 'CHATGPT')
class ExtractorOpenAI(ExtractorBase):
    """Extractor para facturas de OPENAI."""
    
    nombre = 'OPENAI'
    cif = 'EU372041333'
    metodo_pdf = 'pdfplumber'
    categoria_fija = 'GASTOS VARIOS'
    
    def extraer_lineas(self, texto: str) -> List[Dict]:
        """Extrae líneas de servicio de OPENAI."""
        lineas = []
        
        # Buscar Amount due en USD
        m = re.search(r'Amount\s+due\s+\$?([\d,.]+)\s*USD', texto, re.IGNORECASE)
        if m:
            importe_usd = self._convertir_europeo(m.group(1))
            
            # Convertir a EUR
            tipo_cambio = self._obtener_tipo_cambio()
            base_eur = round(importe_usd / tipo_cambio, 2)
            
            # Buscar descripción
            desc_match = re.search(r'(ChatGPT\s+Plus\s+Subscription)', texto, re.IGNORECASE)
            descripcion = desc_match.group(1) if desc_match else 'SUSCRIPCION CHATGPT PLUS'
            
            lineas.append({
                'codigo': '',
                'articulo': descripcion,
                'cantidad': 1,
                'precio_ud': base_eur,
                'iva': 0,
                'base': base_eur,
                'categoria': self.categoria_fija,
                'notas': f'Original: ${importe_usd} USD (TC: {tipo_cambio})'
            })
        
        return lineas
    
    def _obtener_tipo_cambio(self) -> float:
        """Obtiene tipo de cambio EUR/USD del BCE."""
        try:
            url = "https://api.frankfurter.app/latest?from=USD&to=EUR"
            with urllib.request.urlopen(url, timeout=5) as response:
                data = json.loads(response.read().decode())
                return 1 / data['rates']['EUR']  # USD por EUR
        except:
            return 1.10  # Tipo de cambio por defecto
    
    def _convertir_europeo(self, texto: str) -> float:
        """Convierte formato a float."""
        if not texto:
            return 0.0
        texto = texto.strip().replace(',', '')
        try:
            return float(texto)
        except:
            return 0.0
    
    def extraer_total(self, texto: str) -> Optional[float]:
        """Extrae total de la factura (en USD, se convierte a EUR)."""
        m = re.search(r'Amount\s+due\s+\$?([\d,.]+)\s*USD', texto, re.IGNORECASE)
        if m:
            importe_usd = self._convertir_europeo(m.group(1))
            tipo_cambio = self._obtener_tipo_cambio()
            return round(importe_usd / tipo_cambio, 2)
        return None
    
    def extraer_fecha(self, texto: str) -> Optional[str]:
        """Extrae fecha de la factura."""
        # "Date of issue June 18, 2025"
        m = re.search(r'Date\s+of\s+issue\s+(\w+)\s+(\d+),?\s+(\d{4})', texto)
        if m:
            meses = {'January': '01', 'February': '02', 'March': '03', 'April': '04',
                     'May': '05', 'June': '06', 'July': '07', 'August': '08',
                     'September': '09', 'October': '10', 'November': '11', 'December': '12'}
            mes = meses.get(m.group(1), '01')
            return f"{m.group(2).zfill(2)}/{mes}/{m.group(3)}"
        return None
    
    def extraer_referencia(self, texto: str) -> Optional[str]:
        """Extrae número de factura."""
        m = re.search(r'Invoice\s+number\s+([\w\-]+)', texto)
        if m:
            return m.group(1)
        return None
