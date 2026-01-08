# -*- coding: utf-8 -*-
"""
Extractor para ANGEL BORJA VEGA
Productor Fabricante y Exportador de Pimentón de La Vera

NIF: 415928-L
Dirección: C/. Ignacio Cruz, 13 - 10450 Jarandilla de la Vera (Cáceres)
Teléfono: 927 56 00 66

Productos: Pimentón en latas 1/8 KG (Dulce, Agridulce, Picante)
IVA: 10% (alimentación)
Categoría: DESPENSA
Método pago: Recibo domiciliado (30 días)

Formato factura (escaneada - requiere OCR):
- Serie: A
- Nº Factura: 37, 140, etc.
- REF = Serie + Nº (ej: "A-37", "A-140")
- Fecha: DD-Mmm-YY (12-Feb-25)
- Líneas: Artículo | Lote | Kgs | Precio | %Iva | %Dto | Imp.Dto | Importe | Importe+Iva
- Desglose: Base | %Iva | Total Iva | Total Factura

Creado: 08/01/2026
Actualizado: 08/01/2026 - extraer_referencia para compatibilidad main.py
"""
from extractores.base import ExtractorBase
from extractores import registrar
from typing import List, Dict, Optional
import re
import pdfplumber

# Dependencias OCR
try:
    import pytesseract
    from pdf2image import convert_from_path
    OCR_DISPONIBLE = True
except ImportError:
    OCR_DISPONIBLE = False


@registrar('ANGEL BORJA', 'ANGEL BORJA VEGA', 'PIMENTON', 'PIMENTON LA VERA',
           'PIMENTON DE LA VERA', 'BORJA VEGA')
class ExtractorAngelBorja(ExtractorBase):
    """Extractor para facturas de ANGEL BORJA VEGA (Pimentón)."""
    
    nombre = 'ANGEL BORJA VEGA'
    cif = '415928L'
    metodo_pdf = 'hibrido'  # pdfplumber + OCR fallback
    categoria_fija = 'DESPENSA'
    
    # Meses en español abreviados
    MESES = {
        'ene': '01', 'feb': '02', 'mar': '03', 'abr': '04',
        'may': '05', 'jun': '06', 'jul': '07', 'ago': '08',
        'sep': '09', 'oct': '10', 'nov': '11', 'dic': '12'
    }
    
    def extraer_texto(self, pdf_path: str) -> str:
        """Extrae texto del PDF (pdfplumber primero, OCR como fallback)."""
        # Intentar pdfplumber primero
        try:
            with pdfplumber.open(pdf_path) as pdf:
                textos = []
                for page in pdf.pages:
                    texto = page.extract_text()
                    if texto:
                        textos.append(texto)
                texto_pdf = '\n'.join(textos)
                
                # Si hay texto suficiente, usarlo
                if texto_pdf and len(texto_pdf.strip()) > 100:
                    return texto_pdf
        except:
            pass
        
        # Fallback a OCR
        if OCR_DISPONIBLE:
            return self._extraer_texto_ocr(pdf_path)
        
        return ''
    
    def _extraer_texto_ocr(self, pdf_path: str) -> str:
        """Extrae texto usando OCR."""
        try:
            images = convert_from_path(pdf_path, dpi=300)
            if not images:
                return ''
            
            img = images[0]
            texto = pytesseract.image_to_string(img, config='--psm 3')
            return texto
        except Exception as e:
            print(f"Error OCR ANGEL BORJA: {e}")
            return ''
    
    def extraer_referencia(self, texto: str) -> Optional[str]:
        """
        Extrae el número de factura con serie.
        
        Formato OCR: "N Factura: 140" o "Nº Factura: 140"
        Serie siempre es A para este proveedor → "A-140"
        
        v5.14: Renombrado de extraer_numero_factura a extraer_referencia
        """
        # Buscar Nº Factura (OCR puede tener variaciones)
        patrones = [
            r'N[ºº°o]?\s*Factura:\s*\|?\s*(\d+)',
            r'Factura:\s*\|?\s*(\d+)',
            r'N\s*Factura:\s*(\d+)',
        ]
        
        for patron in patrones:
            match = re.search(patron, texto, re.IGNORECASE)
            if match:
                numero = match.group(1)
                return f"A-{numero}"
        
        return None
    
    def extraer_fecha(self, texto: str) -> Optional[str]:
        """
        Extrae la fecha de factura.
        
        Formato OCR: "Fecha factura: 07-Jun-25" o "Fecha factura: | 12-Feb-25"
        """
        patron = re.search(
            r'Fecha\s+factura:\s*\|?\s*(\d{1,2})-([A-Za-z]{3})-(\d{2})',
            texto, re.IGNORECASE
        )
        if patron:
            dia = patron.group(1).zfill(2)
            mes_abrev = patron.group(2).lower()
            año_corto = patron.group(3)
            
            mes = self.MESES.get(mes_abrev, '01')
            año = f"20{año_corto}"
            
            return f"{dia}/{mes}/{año}"
        
        return None
    
    def extraer_total(self, texto: str) -> Optional[float]:
        """Extrae el total de la factura."""
        # Buscar TOTAL FACTURA: 105.60
        patrones = [
            r'TOTAL\s+FACTURA:\s*([\d.,]+)',
            r'TOTAL\s*FACTURA\s*[:\|]?\s*([\d.,]+)',
        ]
        
        for patron in patrones:
            match = re.search(patron, texto, re.IGNORECASE)
            if match:
                return self._convertir_numero(match.group(1))
        
        return None
    
    def extraer_lineas(self, texto: str) -> List[Dict]:
        """
        Extrae líneas de productos.
        
        Formato OCR: LATA DE 1/8 KG DULCE(24 botes) 10 24 2.00 10.00% 0.00% 0.00 48.00 52.80
        Nota: OCR puede introducir caracteres extraños (puntos, comillas)
        """
        lineas = []
        
        # Patrón más flexible para manejar variaciones OCR
        patron = re.compile(
            r'LATA\s+DE\s+(\d+/\d+)\s*KG?\s*(\w+)\s*\((\d+)\s*botes?\)\s+'  # LATA DE 1/8 KG DULCE(24 botes)
            r'(\d+)\s+'                                                      # Lote
            r'(\d+)\s+'                                                      # Kgs
            r'(\d+[.,]\d+)\s+'                                               # Precio
            r'(\d+[.,]\d+)%'                                                 # %Iva
            r'[^0-9]*'                                                       # cualquier cosa entre % e Iva (puntos, espacios)
            r'(\d+[.,]\d+)%'                                                 # %Dto
            r'[^0-9]*'                                                       # cualquier cosa
            r'(\d+[.,]\d+)\s+'                                               # Imp.Dto
            r'(\d+[.,]\d+)',                                                 # BASE
            re.IGNORECASE
        )
        
        for match in patron.finditer(texto):
            tamaño = match.group(1)  # 1/8
            tipo = match.group(2).upper()  # DULCE, AGRIDULCE, PICANTE
            cantidad = int(match.group(5))  # Kgs
            precio = self._convertir_numero(match.group(6))
            iva = int(float(match.group(7).replace(',', '.')))
            base = self._convertir_numero(match.group(10))
            
            # Nombre artículo
            articulo = f"Pimentón {tipo.capitalize()} {tamaño} KG"
            
            if base > 0:
                lineas.append({
                    'codigo': 'PIMENTON',
                    'articulo': articulo[:50],
                    'cantidad': cantidad,
                    'precio_ud': round(precio, 2),
                    'iva': iva,
                    'base': round(base, 2),
                    'categoria': self.categoria_fija
                })
        
        # Si no encontramos líneas, intentar desde desglose fiscal
        if not lineas:
            lineas = self._extraer_lineas_desglose(texto)
        
        return lineas
    
    def _extraer_lineas_desglose(self, texto: str) -> List[Dict]:
        """Extrae desde el desglose de IVA si no se encuentran líneas detalladas."""
        lineas = []
        
        # Buscar Base en el desglose: "Base 96.00 10.00%"
        patron_base = re.search(r'Base\s+Imponible:\s*([\d.,]+)', texto, re.IGNORECASE)
        if not patron_base:
            patron_base = re.search(r'Base\s+([\d.,]+)\s+[\d.,]+%', texto)
        
        if patron_base:
            base = self._convertir_numero(patron_base.group(1))
            if base > 0:
                lineas.append({
                    'codigo': 'PIMENTON',
                    'articulo': 'Pimentón de La Vera',
                    'cantidad': 1,
                    'precio_ud': round(base, 2),
                    'iva': 10,
                    'base': round(base, 2),
                    'categoria': self.categoria_fija
                })
        
        return lineas
    
    def _convertir_numero(self, texto: str) -> float:
        """Convierte texto a número (formato americano: 48.00)."""
        if not texto:
            return 0.0
        texto = str(texto).strip()
        # Este proveedor usa formato americano (punto decimal, sin separador de miles)
        # Ejemplo: 48.00, 22.00, 2.00
        texto = texto.replace(',', '.')  # por si acaso hay coma
        try:
            return float(texto)
        except:
            return 0.0
