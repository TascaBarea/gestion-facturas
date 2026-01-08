# -*- coding: utf-8 -*-
"""
Extractor para CASA DEL DUQUE 2015 SL (HOME IDEAL)
Bazar/tienda de hogar en C/Duque de Alba 15, Madrid

CIF: B87309613
Tel: 914293959
Método: OCR (Tesseract) - tickets escaneados

Productos: artículos de hogar, limpieza, decoración, herramientas
IVA: 21% (todos los productos)
Categoría: GASTOS VARIOS (fija)
Método pago: Tarjeta

Formatos de líneas detectados:
- Formato A: DESCRIPCION  UNDS.  SUMA  IVA%  (SUMA = importe CON IVA)
- Formato B: CANx PRECIO DESCRIPCION  SUMA  (ticket simplificado)
- Formato C: CANx PRECIO 21%-DESCRIPCION  SUMA (IVA inline)

Creado: 28/12/2025
Actualizado: 08/01/2026 - extraer_referencia + mejora OCR
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


@registrar('CASA DEL DUQUE', 'CASA DEL DUQUE SL', 'CASA DEL DUQUE 2015 SL', 
           'HOME IDEAL', 'CASA DEL DUQUE 2015')
class ExtractorCasaDelDuque(ExtractorBase):
    """Extractor para tickets de CASA DEL DUQUE / HOME IDEAL."""
    
    nombre = 'CASA DEL DUQUE 2015 SL'
    cif = 'B87309613'
    iban = ''
    metodo_pdf = 'hibrido'  # pdfplumber + OCR fallback
    categoria_fija = 'GASTOS VARIOS'
    
    def extraer_texto(self, pdf_path: str) -> str:
        """Extrae texto usando método híbrido (pdfplumber + OCR fallback)."""
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
        """Extrae texto usando OCR (Tesseract)."""
        try:
            images = convert_from_path(pdf_path, dpi=300)
            if not images:
                return ''
            
            img = images[0]
            texto = pytesseract.image_to_string(img, config='--psm 6')
            return texto
        except Exception as e:
            print(f"Error OCR CASA DEL DUQUE: {e}")
            return ''
    
    def extraer_referencia(self, texto: str) -> Optional[str]:
        """
        Extrae el número de factura.
        
        Formato: Factura No.: 2025125295 → "2025125295"
        
        v5.14: Renombrado de extraer_numero_factura a extraer_referencia
        """
        patrones = [
            r'Factura\s+No\.?\s*:?\s*(\d{10})',
            r'Factura\s+No\.?\s*:?\s*(\d+)',
            r'No:\s*(\d{10})',
        ]
        
        for patron in patrones:
            match = re.search(patron, texto, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return None
    
    def extraer_fecha(self, texto: str) -> Optional[str]:
        """
        Extrae la fecha de la factura.
        
        Formatos:
        - Fecha:06-12-2025 → 06/12/2025
        - 07-08-2025 (en línea No:)
        """
        patrones = [
            r'Fecha\s*:?\s*(\d{2})-(\d{2})-(\d{4})',
            r'(\d{2})-(\d{2})-(202\d)\s+\d{2}:\d{2}',  # 07-08-2025 19:31:38
        ]
        
        for patron in patrones:
            match = re.search(patron, texto, re.IGNORECASE)
            if match:
                dia = match.group(1)
                mes = match.group(2)
                año = match.group(3)
                return f"{dia}/{mes}/{año}"
        
        return None
    
    def extraer_total(self, texto: str) -> Optional[float]:
        """Extrae el total de la factura."""
        patrones = [
            r'(\d+)\s*ARTIC\.?\s*,?\s*TOTAL:\s*([\d,\.]+)\s*Euro',
            r'ARTIC\.?\s*,?\s*TOTAL:\s*([\d,\.]+)\s*Euro',
            r'TOTAL:\s*([\d,\.]+)\s*Euro',
            r'Tarjeta:\s*([\d,\.]+)\s*Euro',
            r'EFECTIVO:\s*([\d,\.]+)',
            r'([\d,\.]+)\s*Euro\s*$',
        ]
        
        for patron in patrones:
            match = re.search(patron, texto, re.IGNORECASE | re.MULTILINE)
            if match:
                # El total está en el último grupo
                total_str = match.group(match.lastindex)
                total = self._convertir_europeo(total_str)
                if total > 0.5:
                    return total
        
        # Alternativa: calcular desde cuadro fiscal (Imponible + IVA)
        patrones_fiscal = [
            r'(\d+[,\.]\d{2})\s+21%+\s+(\d+[,\.]\d{2})',
            r'(\d+[,\.]\d{2})\s+21[%X]+\s+(\d+[,\.]\d{2})',
        ]
        
        for patron in patrones_fiscal:
            match = re.search(patron, texto, re.IGNORECASE)
            if match:
                base = self._convertir_europeo(match.group(1))
                iva = self._convertir_europeo(match.group(2))
                if base > 0:
                    return round(base + iva, 2)
        
        return None
    
    def extraer_lineas(self, texto: str) -> List[Dict]:
        """
        Extrae líneas de productos usando los 3 formatos detectados.
        Si las líneas no cuadran con el total, usa el cuadro fiscal.
        """
        # Obtener total esperado
        total_esperado = self.extraer_total(texto) or 0
        
        # Probar todos los formatos
        lineas_a = self._extraer_formato_a(texto)
        lineas_b = self._extraer_formato_b(texto)
        lineas_c = self._extraer_formato_c(texto)
        
        # Usar el formato que más líneas encuentre
        todas = [lineas_a, lineas_b, lineas_c]
        lineas = max(todas, key=len)
        
        # Verificar si las líneas cuadran con el total
        if lineas and total_esperado > 0:
            base_total = sum(l['base'] for l in lineas)
            total_calc = round(base_total * 1.21, 2)
            diff = abs(total_calc - total_esperado)
            
            # Si no cuadra (diferencia > 5%), usar cuadro fiscal
            if diff > total_esperado * 0.05:
                lineas_fiscal = self._extraer_desde_fiscal(texto)
                if lineas_fiscal:
                    # Verificar si fiscal cuadra mejor
                    base_fiscal = sum(l['base'] for l in lineas_fiscal)
                    total_fiscal = round(base_fiscal * 1.21, 2)
                    diff_fiscal = abs(total_fiscal - total_esperado)
                    
                    if diff_fiscal < diff:
                        return lineas_fiscal
        
        # Si no encontramos líneas, usar fiscal
        if not lineas:
            lineas = self._extraer_desde_fiscal(texto)
        
        return lineas
    
    def _extraer_formato_a(self, texto: str) -> List[Dict]:
        """
        Formato A: DESCRIPCION  UNDS.  SUMA  IVA%
        
        SUMA = importe CON IVA incluido
        base = suma / 1.21
        """
        lineas = []
        
        # Limpiar texto de caracteres OCR problemáticos
        texto_limpio = texto.replace('»', ' ').replace('«', ' ')
        
        # Patrón más flexible: DESCRIPCION  cantidad  importe  21%
        patron = re.compile(
            r'^([A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ0-9\s/\-\.]+?)\s+'  # Descripción
            r'(\d{1,3})\s+'                               # Cantidad
            r'(\d+[,\.]\d{2})\s+'                         # Suma (con IVA)
            r'21[%X]',                                    # IVA (puede ser % o X por OCR)
            re.MULTILINE | re.IGNORECASE
        )
        
        for match in patron.finditer(texto_limpio):
            descripcion = match.group(1).strip()
            cantidad = int(match.group(2))
            suma_iva_inc = self._convertir_europeo(match.group(3))
            
            # Filtrar líneas no válidas
            if len(descripcion) < 2 or suma_iva_inc < 0.10:
                continue
            if any(skip in descripcion.upper() for skip in 
                   ['DESCRIPCION', 'IMPONIBLE', 'ARTIC', 'TOTAL', 'UNDS', 'IVAX']):
                continue
            
            # Calcular base (suma incluye IVA)
            base = round(suma_iva_inc / 1.21, 2)
            precio_ud = round(base / cantidad, 2) if cantidad > 0 else base
            
            lineas.append({
                'codigo': '',
                'articulo': descripcion[:50],
                'cantidad': cantidad,
                'precio_ud': precio_ud,
                'iva': 21,
                'base': base,
                'categoria': self.categoria_fija
            })
        
        return lineas
    
    def _extraer_formato_b(self, texto: str) -> List[Dict]:
        """
        Formato B: CANx PRECIO DESCRIPCION  SUMA
        
        Ejemplo: 2x  6,95 JARRON  13,90
        SUMA = importe CON IVA incluido
        """
        lineas = []
        
        patron = re.compile(
            r'(\d+)x\s+'                    # Cantidad (2x)
            r'(\d+[,\.]\d{2})\s+'           # Precio unitario
            r'([A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ0-9\s]+?)\s+'  # Descripción
            r'(\d+[,\.]\d{2})',             # Suma (con IVA)
            re.MULTILINE
        )
        
        for match in patron.finditer(texto):
            cantidad = int(match.group(1))
            precio = self._convertir_europeo(match.group(2))
            descripcion = match.group(3).strip()
            suma_iva_inc = self._convertir_europeo(match.group(4))
            
            if suma_iva_inc < 0.10:
                continue
            
            # Calcular base (suma incluye IVA)
            base = round(suma_iva_inc / 1.21, 2)
            
            lineas.append({
                'codigo': '',
                'articulo': descripcion[:50],
                'cantidad': cantidad,
                'precio_ud': round(precio / 1.21, 2),  # precio también incluye IVA
                'iva': 21,
                'base': base,
                'categoria': self.categoria_fija
            })
        
        return lineas
    
    def _extraer_formato_c(self, texto: str) -> List[Dict]:
        """
        Formato C: CANx PRECIO 21%-DESCRIPCION  SUMA
        
        Ejemplo: 1x  2,95 21%-NIEVE NAVIDAD 150  2,95
        SUMA = importe CON IVA incluido
        
        Nota: OCR puede leer variaciones del marcador 21%
        """
        lineas = []
        
        # Patrón flexible para OCR
        patron = re.compile(
            r'(\d+)x\s+'                         # Cantidad (1x)
            r'(\d+[,\.]\d{2})\s+'                # Precio unitario
            r'2[1Il]?[%!]?-'                      # Marcador IVA (puede ser 21%-, 2!%-, etc.)
            r'([A-ZÁÉÍÓÚÑ0-9][^\n]+?)\s+'        # Descripción
            r'(\d+[,\.]\d{2})',                  # Suma (con IVA)
            re.MULTILINE | re.IGNORECASE
        )
        
        for match in patron.finditer(texto):
            cantidad = int(match.group(1))
            precio = self._convertir_europeo(match.group(2))
            descripcion = match.group(3).strip()
            suma_iva_inc = self._convertir_europeo(match.group(4))
            
            if suma_iva_inc < 0.10:
                continue
            
            # Calcular base (suma incluye IVA)
            base = round(suma_iva_inc / 1.21, 2)
            
            lineas.append({
                'codigo': '',
                'articulo': descripcion[:50],
                'cantidad': cantidad,
                'precio_ud': round(precio / 1.21, 2),
                'iva': 21,
                'base': base,
                'categoria': self.categoria_fija
            })
        
        return lineas
    
    def _extraer_desde_fiscal(self, texto: str) -> List[Dict]:
        """Extrae una línea genérica desde el cuadro fiscal."""
        lineas = []
        
        # Buscar: Imponible IVA%  IVA  REQ
        #         26,40     21%   5,55
        # Nota: OCR puede generar caracteres raros
        patrones = [
            r'(\d+[,\.]\d{2})\s+21%+\s+(\d+[,\.]\d{2})',  # Normal
            r'(\d+[,\.]\d{2})\s+21[%X]+\s+(\d+[,\.]\d{2})',  # Con X por OCR
            r'Imponible.*?(\d+[,\.]\d{2})\s+21',  # Buscando después de Imponible
        ]
        
        for patron in patrones:
            match = re.search(patron, texto, re.IGNORECASE)
            if match:
                base = self._convertir_europeo(match.group(1))
                if base > 0:
                    lineas.append({
                        'codigo': '',
                        'articulo': 'Artículos varios',
                        'cantidad': 1,
                        'precio_ud': base,
                        'iva': 21,
                        'base': base,
                        'categoria': self.categoria_fija
                    })
                    return lineas
        
        return lineas
    
    def _convertir_europeo(self, texto: str) -> float:
        """Convierte formato europeo (coma decimal) a float."""
        if not texto:
            return 0.0
        texto = str(texto).strip()
        # Formato europeo: 1.234,56 o 1234,56
        if ',' in texto and '.' in texto:
            texto = texto.replace('.', '').replace(',', '.')
        elif ',' in texto:
            texto = texto.replace(',', '.')
        try:
            return float(texto)
        except:
            return 0.0
