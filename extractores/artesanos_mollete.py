# -*- coding: utf-8 -*-
"""
Extractor para MOLLETES ARTESANOS DE ANTEQUERA, S.L.

Fabricante de molletes y picos de Antequera (Malaga)
CIF: B93662708

Formato factura (PDF digital):
- Lineas producto: CODIGO DESCRIPCION CAJAS UNIDADES PRECIO DTO1 DTO2 IMPORTE
- Ejemplo: 10108 MOLLETE AT.80GR C-26 U*2M - CAD.: 27/01/2026 8 208,000 1,11 30,00 161,54
- El importe ya viene con el descuento del 30% aplicado

IVA: 4% (pan y derivados)

Creado: 20/12/2025
"""
from extractores.base import ExtractorBase
from extractores import registrar
from typing import List, Dict, Optional
import re
import pdfplumber


@registrar('ARTESANOS DEL MOLLETE', 'MOLLETES ARTESANOS', 'MOLLETES ARTESANOS DE ANTEQUERA',
           'ARTESANOS MOLLETE', 'MOLLETE ANTEQUERA')
class ExtractorArtesanosMollete(ExtractorBase):
    """Extractor para facturas de MOLLETES ARTESANOS DE ANTEQUERA."""
    
    nombre = 'ARTESANOS DEL MOLLETE'
    cif = 'B93662708'
    metodo_pdf = 'pdfplumber'
    categoria_fija = 'PAN Y BOLLERIA'
    
    def extraer_texto_pdfplumber(self, pdf_path: str) -> str:
        """Extrae texto del PDF."""
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
        CODIGO DESCRIPCION CAJAS UNIDADES PRECIO DTO1 DTO2 IMPORTE
        10108 MOLLETE AT.80GR C-26 U*2M - CAD.: 27/01/2026 8 208,000 1,11 30,00 161,54
        
        Nota: El importe ya tiene el descuento aplicado
        Algunos productos no tienen CAJAS (solo UNIDADES)
        """
        lineas = []
        
        # Patron para lineas de producto con cajas
        # CODIGO + DESCRIPCION + CAJAS + UNIDADES + PRECIO + DTO + IMPORTE
        patron_con_cajas = re.compile(
            r'^(\d{5})\s+'                     # Codigo (5 digitos)
            r'(.+?)\s+'                        # Descripcion
            r'(\d+)\s+'                        # Cajas
            r'(\d+,\d{3})\s+'                  # Unidades (con 3 decimales)
            r'(\d+,\d{2})\s+'                  # Precio
            r'(\d+,\d{2})\s+'                  # Descuento
            r'(\d+,\d{2})\s*$'                 # Importe
        , re.MULTILINE)
        
        # Patron para lineas sin cajas (solo unidades)
        patron_sin_cajas = re.compile(
            r'^(\d{5})\s+'                     # Codigo (5 digitos)
            r'(.+?)\s+'                        # Descripcion
            r'(\d+,\d{3})\s+'                  # Unidades (con 3 decimales)
            r'(\d+,\d{2})\s+'                  # Precio
            r'(\d+,\d{2})\s+'                  # Descuento
            r'(\d+,\d{2})\s*$'                 # Importe
        , re.MULTILINE)
        
        # Buscar lineas con cajas
        for match in patron_con_cajas.finditer(texto):
            codigo = match.group(1)
            descripcion = match.group(2).strip()
            unidades = self._convertir_europeo(match.group(4))
            precio = self._convertir_europeo(match.group(5))
            importe = self._convertir_europeo(match.group(7))
            
            # Limpiar descripcion (quitar CAD.: fecha)
            descripcion = re.sub(r'\s*-\s*CAD\.?:?\s*\d{2}/\d{2}/\d{4}', '', descripcion)
            descripcion = descripcion.strip()
            
            lineas.append({
                'codigo': codigo,
                'articulo': descripcion[:50],
                'cantidad': round(unidades, 3),
                'precio_ud': round(precio, 2),
                'iva': 4,
                'base': round(importe, 2)
            })
        
        # Buscar lineas sin cajas
        for match in patron_sin_cajas.finditer(texto):
            codigo = match.group(1)
            descripcion = match.group(2).strip()
            unidades = self._convertir_europeo(match.group(3))
            precio = self._convertir_europeo(match.group(4))
            importe = self._convertir_europeo(match.group(6))
            
            # Verificar que no sea una linea ya capturada
            if any(l['codigo'] == codigo and abs(l['base'] - importe) < 0.01 for l in lineas):
                continue
            
            descripcion = re.sub(r'\s*-\s*CAD\.?:?\s*\d{2}/\d{2}/\d{4}', '', descripcion)
            descripcion = descripcion.strip()
            
            lineas.append({
                'codigo': codigo,
                'articulo': descripcion[:50],
                'cantidad': round(unidades, 3),
                'precio_ud': round(precio, 2),
                'iva': 4,
                'base': round(importe, 2)
            })
        
        return lineas
    
    def _convertir_europeo(self, texto: str) -> float:
        """Convierte formato europeo (1.234,56) a float."""
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
        # Buscar TOTAL FRA seguido de importe o el ultimo importe con euro
        patron = re.search(r'TOTAL\s+FRA\s*\n\s*[\d,.\s]+\n\s*(\d+,\d{2})', texto)
        if patron:
            return self._convertir_europeo(patron.group(1))
        
        # Alternativa: buscar importe con simbolo euro
        patron2 = re.search(r'(\d+,\d{2})\s*€', texto)
        if patron2:
            return self._convertir_europeo(patron2.group(1))
        
        return None
    
    def extraer_fecha(self, texto: str) -> Optional[str]:
        """Extrae fecha de la factura."""
        # Formato: DD/MM/YYYY al inicio
        patron = re.search(r'^(\d{2}/\d{2}/\d{4})', texto, re.MULTILINE)
        if patron:
            return patron.group(1)
        return None
    
    def extraer_numero_factura(self, texto: str) -> Optional[str]:
        """Extrae numero de factura."""
        # Formato: G NNNN (ej: G 3311)
        patron = re.search(r'(G\s*\d{4})', texto)
        if patron:
            return patron.group(1).replace(' ', '')
        return None
