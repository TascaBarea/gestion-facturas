# -*- coding: utf-8 -*-
"""
Extractor para ALCAMPO S.A.

Supermercado - compras menores pagadas con tarjeta
CIF: A28581882
Sin IBAN (pago tarjeta)
Sin portes

Dos formatos de factura:
1. DIGITAL (PDF texto): Factura completa con tabla de productos
2. TICKET ESCANEADO (imagen): Factura simplificada, necesita OCR

IVA variable: 4% (alimentos basicos), 10% (alimentos), 21% (otros)
Categoria: Por diccionario (productos variados)

Creado: 04/01/2026
"""
from extractores.base import ExtractorBase
from extractores import registrar
from typing import List, Dict, Optional
import re
import pdfplumber


@registrar('ALCAMPO', 'ALCAMPO S.A.', 'ALCAMPO SA', 'ALCAMPO RIBERA', 
           'ALCAMPO RIBERA DE CURTIDORES')
class ExtractorAlcampo(ExtractorBase):
    """Extractor para facturas de ALCAMPO S.A."""
    
    nombre = 'ALCAMPO S.A.'
    cif = 'A28581882'
    iban = ''  # Pago con tarjeta
    metodo_pdf = 'pdfplumber'
    
    # Mapeo letras IVA en tickets
    IVA_LETRAS = {
        'A': 21,
        'B': 10,
        'C': 4
    }
    
    def extraer_texto(self, pdf_path: str) -> str:
        """
        Extrae texto del PDF.
        Intenta pdfplumber primero, si falla usa OCR.
        """
        texto = self._extraer_pdfplumber(pdf_path)
        
        # Si no hay texto suficiente, intentar OCR
        if len(texto.strip()) < 50:
            texto_ocr = self._extraer_ocr(pdf_path)
            if len(texto_ocr) > len(texto):
                return texto_ocr
        
        return texto
    
    def _extraer_pdfplumber(self, pdf_path: str) -> str:
        """Extrae texto con pdfplumber."""
        texto_completo = []
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    texto = page.extract_text()
                    if texto:
                        texto_completo.append(texto)
        except Exception as e:
            pass
        return '\n'.join(texto_completo)
    
    def _extraer_ocr(self, pdf_path: str) -> str:
        """Extrae texto con OCR (pytesseract)."""
        try:
            from pdf2image import convert_from_path
            import pytesseract
            
            # Convertir PDF a imagenes
            images = convert_from_path(pdf_path, dpi=300)
            
            texto_completo = []
            for img in images:
                # OCR con configuracion para tickets
                texto = pytesseract.image_to_string(
                    img, 
                    lang='spa',
                    config='--psm 6'  # Assume uniform block of text
                )
                if texto:
                    texto_completo.append(texto)
            
            return '\n'.join(texto_completo)
        except ImportError:
            # Si no hay pytesseract/pdf2image, devolver vacio
            return ''
        except Exception as e:
            return ''
    
    def extraer_lineas(self, texto: str) -> List[Dict]:
        """
        Extrae lineas de productos.
        Detecta automaticamente si es factura digital o ticket.
        """
        # Detectar tipo de factura
        if 'Nº Factura' in texto or 'Total Factura' in texto:
            return self._extraer_lineas_digital(texto)
        elif 'FACTURA SIMPLIFICADA' in texto.upper() or 'TOT' in texto:
            return self._extraer_lineas_ticket(texto)
        else:
            # Intentar ambos metodos
            lineas = self._extraer_lineas_digital(texto)
            if not lineas:
                lineas = self._extraer_lineas_ticket(texto)
            return lineas
    
    def _extraer_lineas_digital(self, texto: str) -> List[Dict]:
        """
        Extrae lineas de facturas digitales.
        
        Formato:
        Codigo Concepto Cantidad Base Imponible Impuesto Importe Impuesto Importe Liquido
        8433634000443 BOLSA RAFIA REUT 2 1,14€ 21 0,24€ 1,38€
        802 LIMON APC GRANEL 2265 4,99€ 4 0,2€ 5,19€
        """
        lineas = []
        
        # Patron para lineas de producto
        # Codigo (numeros) + Concepto + Cantidad + Base€ + IVA% + ImpIVA€ + Total€
        patron = re.compile(
            r'^(\d+)\s+'                      # Codigo (EAN o corto)
            r'([A-Z][A-Z0-9\s\._]+?)\s+'      # Concepto
            r'(\d+)\s+'                       # Cantidad
            r'(\d+,\d+)€\s+'                  # Base Imponible
            r'(\d+)\s+'                       # % IVA
            r'(\d+,\d+)€\s+'                  # Importe IVA
            r'(\d+(?:,\d+)?)€'                # Importe Liquido (con o sin decimales)
        , re.MULTILINE)
        
        for match in patron.finditer(texto):
            codigo = match.group(1)
            concepto = match.group(2).strip()
            cantidad = int(match.group(3))
            base = self._convertir_europeo(match.group(4))
            iva = int(match.group(5))
            total = self._convertir_europeo(match.group(7))
            
            # Filtrar cabeceras y lineas invalidas (usar palabras completas)
            palabras_concepto = concepto.upper().split()
            if any(x in palabras_concepto for x in ['CODIGO', 'CONCEPTO', 'CANTIDAD']):
                continue
            
            if base > 0:
                lineas.append({
                    'codigo': codigo,
                    'articulo': concepto[:50],
                    'cantidad': cantidad,
                    'precio_ud': round(base / cantidad if cantidad > 0 else base, 4),
                    'iva': iva,
                    'base': round(base, 2)
                })
        
        return lineas
    
    def _extraer_lineas_ticket(self, texto: str) -> List[Dict]:
        """
        Extrae lineas de tickets escaneados (OCR).
        
        Formato:
        CEBOLLETA BLANCA 1,45 C
        LONG.SERRANO 350 2,90 B
        PAPEL COCINA 3,49 A
        
        Donde: A=21%, B=10%, C=4%
        """
        lineas = []
        
        # Patron para lineas de ticket
        # Producto + Precio + Letra IVA
        patron = re.compile(
            r'^([A-Z][A-Z0-9\s\.\-]+?)\s+'    # Producto
            r'(\d+[,\.]\d{2})\s+'              # Precio
            r'([ABC])\s*$'                     # Letra IVA
        , re.MULTILINE)
        
        for match in patron.finditer(texto):
            producto = match.group(1).strip()
            precio = self._convertir_europeo(match.group(2))
            letra_iva = match.group(3).upper()
            iva = self.IVA_LETRAS.get(letra_iva, 21)
            
            # Calcular base desde precio con IVA
            base = round(precio / (1 + iva / 100), 2)
            
            # Filtrar lineas invalidas (usar palabras completas)
            palabras_producto = producto.upper().split()
            if any(x in palabras_producto for x in ['TOT', 'TARJETA', 'CAMBIO', 'IVA', 'EFECTIVO']):
                continue
            
            if precio > 0 and len(producto) >= 3:
                lineas.append({
                    'codigo': '',
                    'articulo': producto[:50],
                    'cantidad': 1,
                    'precio_ud': round(base, 2),
                    'iva': iva,
                    'base': round(base, 2)
                })
        
        return lineas
    
    def _convertir_europeo(self, texto: str) -> float:
        """Convierte formato europeo (1.234,56) a float."""
        if not texto:
            return 0.0
        texto = str(texto).strip()
        # Quitar simbolo euro
        texto = texto.replace('€', '').strip()
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
        # Formato digital: Total Factura 13,65€
        patron1 = re.search(r'Total\s+Factura\s+(\d+,\d+)€', texto, re.IGNORECASE)
        if patron1:
            return self._convertir_europeo(patron1.group(1))
        
        # Formato ticket: TOT 4,35
        patron2 = re.search(r'TOT\s+(\d+[,\.]\d{2})', texto)
        if patron2:
            return self._convertir_europeo(patron2.group(1))
        
        # Alternativa: € TARJETA seguido de importe
        patron3 = re.search(r'€?\s*TARJETA\s+(\d+[,\.]\d{2})', texto)
        if patron3:
            return self._convertir_europeo(patron3.group(1))
        
        return None
    
    def extraer_fecha(self, texto: str) -> Optional[str]:
        """Extrae fecha de la factura."""
        # Formato digital: Madrid, a 5 de Agosto de 2025
        meses = {
            'enero': '01', 'febrero': '02', 'marzo': '03', 'abril': '04',
            'mayo': '05', 'junio': '06', 'julio': '07', 'agosto': '08',
            'septiembre': '09', 'octubre': '10', 'noviembre': '11', 'diciembre': '12'
        }
        patron1 = re.search(r'(\d{1,2})\s+de\s+(\w+)\s+de\s+(\d{4})', texto, re.IGNORECASE)
        if patron1:
            dia = patron1.group(1).zfill(2)
            mes = meses.get(patron1.group(2).lower(), '01')
            anio = patron1.group(3)
            return f"{dia}/{mes}/{anio}"
        
        # Formato ticket: 07/09/25 o 7/09/25
        patron2 = re.search(r'(\d{1,2})/(\d{2})/(\d{2})\s', texto)
        if patron2:
            dia = patron2.group(1).zfill(2)
            mes = patron2.group(2)
            anio = '20' + patron2.group(3)
            return f"{dia}/{mes}/{anio}"
        
        return None
    
    def extraer_numero_factura(self, texto: str) -> Optional[str]:
        """Extrae numero de factura."""
        # Formato digital: Nº Factura 250889300009
        patron1 = re.search(r'Nº\s*Factura\s+(\d+)', texto)
        if patron1:
            return patron1.group(1)
        
        # Formato ticket: N. REFERENCIA 00533_250907_143523
        patron2 = re.search(r'N\.\s*REFERENCIA[:\s]+(\S+)', texto)
        if patron2:
            return patron2.group(1)
        
        return None
