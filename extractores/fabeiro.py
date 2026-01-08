# -*- coding: utf-8 -*-
"""
Extractor para FABEIRO S.L.

Proveedor de productos ibericos y conservas de Getafe (Madrid)
CIF: B79992079

Formato factura (PDF digital multipagina):
- Lineas producto: CODIGO CONCEPTO IVA% CANTIDAD P.UNIDAD DE. IMPORTE
- Ejemplo: CA0005 ANCHOA OLIVA GRAN SELECCION 60 10,00% 12,0000 24,0000 288,00
- Segunda linea descripcion: LOMOS - SIN28

IVA mixto:
- 10%: Embutidos, conservas, anchoas, cecina
- 4%: Quesos (cabra, oveja)

Categorias por codigo:
- CA0005, CA0024 (anchoas) -> ANCHOAS
- ZA0010, AL0007 (quesos) -> QUESO APERITIVO
- LE0003 (cecina) -> CHACINAS
- SA0011 (salchichon) -> EMBUTIDOS APERITIVO

Creado: 20/12/2025
Actualizado: 21/12/2025 - Mapeo de categorias por codigo
"""
from extractores.base import ExtractorBase
from extractores import registrar
from typing import List, Dict, Optional
import re
import pdfplumber


@registrar('FABEIRO', 'FABEIRO S.L.', 'FABEIRO SL', 'FABEIROIBERICO')
class ExtractorFabeiro(ExtractorBase):
    """Extractor para facturas de FABEIRO S.L."""
    
    nombre = 'FABEIRO'
    cif = 'B79992079'
    metodo_pdf = 'pdfplumber'
    
    # Mapeo de categorias por codigo de articulo
    CATEGORIAS = {
        'CA0005': 'ANCHOAS',           # ANCHOA OLIVA GRAN SELECCION 60
        'CA0024': 'ANCHOAS',           # ANCHOA CANT. OLIVA R.FAMILIA
        'ZA0010': 'QUESO APERITIVO',   # QUESO DE CABRA
        'AL0007': 'QUESO APERITIVO',   # QUESO OVEJA AHUMADO NAVARRA
        'LE0003': 'CHACINAS',          # CECINA DE LEON IGP BABILLA
        'SA0011': 'EMBUTIDOS APERITIVO', # SALCHICHON IBERICO PRIMERA
    }
    
    def extraer_texto_pdfplumber(self, pdf_path: str) -> str:
        """Extrae texto de todas las paginas del PDF."""
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
    
    def extraer_lineas(self, texto: str) -> List[Dict]:
        """
        Extrae lineas INDIVIDUALES de productos.
        
        Formato:
        CODIGO CONCEPTO IVA% CANTIDAD P.UNIDAD DE. IMPORTE
        CA0005 ANCHOA OLIVA GRAN SELECCION 60 10,00% 12,0000 24,0000 288,00
        LOMOS - SIN28  (segunda linea descripcion - ignorar)
        
        Nota: La cantidad puede tener 4 decimales (ej: 5,7850 kg)
        """
        lineas = []
        
        # Patron principal para lineas de producto
        # CODIGO + DESCRIPCION + IVA% + CANTIDAD + PRECIO + [DESC] + IMPORTE
        patron_linea = re.compile(
            r'^([A-Z]{2}\d{4})\s+'           # Codigo (CA0005, LE0003, SA0011, ZA0010, AL0007)
            r'(.+?)\s+'                       # Descripcion
            r'(\d+,\d{2})%\s+'                # IVA (10,00% o 4,00%)
            r'(\d+,\d{4})\s+'                 # Cantidad (con 4 decimales)
            r'(\d+,\d{4})\s+'                 # Precio unitario (con 4 decimales)
            r'(\d+,\d{2})\s*$'                # Importe final
        , re.MULTILINE)
        
        for match in patron_linea.finditer(texto):
            codigo = match.group(1)
            descripcion = match.group(2).strip()
            iva = self._convertir_europeo(match.group(3))
            cantidad = self._convertir_europeo(match.group(4))
            precio = self._convertir_europeo(match.group(5))
            importe = self._convertir_europeo(match.group(6))
            
            # Limpiar descripcion (quitar guiones finales, lotes, etc.)
            descripcion = re.sub(r'\s*-\s*$', '', descripcion)
            descripcion = descripcion.strip()
            
            # Obtener categoria del mapeo
            categoria = self.CATEGORIAS.get(codigo, 'PENDIENTE')
            
            lineas.append({
                'codigo': codigo,
                'articulo': descripcion[:50],
                'cantidad': round(cantidad, 4),
                'precio_ud': round(precio, 4),
                'iva': int(iva),
                'base': round(importe, 2),
                'categoria': categoria
            })
        
        return lineas
    
    def _convertir_europeo(self, texto: str) -> float:
        """Convierte formato europeo (1.234,56) a float."""
        if not texto:
            return 0.0
        texto = texto.strip()
        # Quitar puntos de miles y cambiar coma por punto
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
        # Buscar TOTAL seguido de importe
        # TOTAL 1.588,35 o TOTAL 1.588,35 EUR
        patron = re.search(r'TOTAL\s+(\d+\.?\d*,\d{2})\s*', texto)
        if patron:
            return self._convertir_europeo(patron.group(1))
        return None
    
    def extraer_fecha(self, texto: str) -> Optional[str]:
        """Extrae fecha de la factura."""
        # Formato: Fecha Factura seguido de DD-MM-YYYY
        patron = re.search(r'Fecha\s+Factura\s*\n.*?(\d{2}-\d{2}-\d{4})', texto, re.DOTALL)
        if patron:
            # Convertir de DD-MM-YYYY a DD/MM/YYYY
            fecha = patron.group(1).replace('-', '/')
            return fecha
        # Alternativa directa
        patron2 = re.search(r'(\d{2}-\d{2}-\d{4})', texto)
        if patron2:
            return patron2.group(1).replace('-', '/')
        return None
    
    def extraer_numero_factura(self, texto: str) -> Optional[str]:
        """Extrae numero de factura."""
        # Formato: 25 - 11.474
        patron = re.search(r'N[o0]\s*Factura\s*Fecha.*?\n.*?(\d+\s*-\s*\d+\.?\d+)', texto, re.DOTALL)
        if patron:
            return patron.group(1).replace(' ', '')
        # Alternativa
        patron2 = re.search(r'(\d{2}\s*-\s*\d+\.\d+)', texto)
        if patron2:
            return patron2.group(1).replace(' ', '')
        return None
