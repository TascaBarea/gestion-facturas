# -*- coding: utf-8 -*-
"""
Extractor para ANA CABALLO VERMOUTH, S.L.

Vermut artesanal de Extremadura
CIF: B87925970
IBAN: REDACTED_IBAN

Formato factura:
DESCRIPCION CANT. PRECIO DTO. NETO
Botella 75 cl. Ana Caballo Vermouth Rojo. L011223 6 15,80 20,00% 75,84
Tubo Botella 75 cl. Promocional 6 0,00 0,00% 0,00

Incluye:
- Productos con descuento (20%, 15%, etc.)
- Productos promocionales (precio 0,00)
- Amenities, tubos, bolsas

IVA: 21%
Categoria fija: LICORES Y VERMUS

Creado: 04/01/2026
"""
from extractores.base import ExtractorBase
from extractores import registrar
from typing import List, Dict, Optional
import re
import pdfplumber


@registrar('ANA CABALLO', 'ANA CABALLO VERMOUTH', 'ANA CABALLO VERMOUTH S.L.',
           'ANA CABALLO VERMOUTH SL')
class ExtractorAnaCaballo(ExtractorBase):
    """Extractor para facturas de ANA CABALLO VERMOUTH."""
    
    nombre = 'ANA CABALLO VERMOUTH'
    cif = 'B87925970'
    iban = 'REDACTED_IBAN'
    metodo_pdf = 'pdfplumber'
    categoria_fija = 'LICORES Y VERMUS'
    
    def extraer_texto(self, pdf_path: str) -> str:
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
    
    def extraer_lineas(self, texto: str) -> List[Dict]:
        """
        Extrae lineas de productos.
        
        Formato:
        DESCRIPCION CANT. PRECIO DTO. NETO
        Botella 75 cl. Ana Caballo Vermouth Rojo. L011223 6 15,80 20,00% 75,84
        Amenity 30 ml. Ana Caballo Vermouth Rojo. L010922 Promocional 5 0,00 0,00% 0,00
        """
        lineas = []
        
        # Patron para lineas de producto
        # Descripcion + Cantidad + Precio + Descuento% + Neto
        patron = re.compile(
            r'^(.+?)\s+'                    # Descripcion
            r'(\d+)\s+'                     # Cantidad
            r'(\d+,\d{2})\s+'               # Precio unitario
            r'(\d+,\d{2})%\s+'              # Descuento %
            r'(\d+,\d{2})\s*$'              # Neto (base)
        , re.MULTILINE)
        
        for match in patron.finditer(texto):
            descripcion = match.group(1).strip()
            cantidad = int(match.group(2))
            precio = self._convertir_europeo(match.group(3))
            descuento = self._convertir_europeo(match.group(4))
            neto = self._convertir_europeo(match.group(5))
            
            # Filtrar cabeceras
            if any(x in descripcion.upper() for x in ['DESCRIPCIÓN', 'DESCRIPCION', 'CANT.', 'PRECIO']):
                continue
            
            # Limpiar descripcion - quitar lotes al final (ej: L011223, LB11021)
            descripcion_limpia = re.sub(r'\s+L[A-Z]?\d+\s*$', '', descripcion)
            descripcion_limpia = re.sub(r'\s+\d{6}\s*$', '', descripcion_limpia)
            descripcion_limpia = re.sub(r'\s+Promocional\s*$', '', descripcion_limpia, flags=re.IGNORECASE)
            
            # Calcular precio con descuento aplicado
            if cantidad > 0 and neto > 0:
                precio_con_dto = round(neto / cantidad, 2)
            else:
                precio_con_dto = 0.0
            
            lineas.append({
                'codigo': '',
                'articulo': descripcion_limpia[:50],
                'cantidad': cantidad,
                'precio_ud': precio_con_dto,
                'iva': 21,
                'base': round(neto, 2),
                'categoria': self.categoria_fija
            })
        
        return lineas
    
    def _convertir_europeo(self, texto: str) -> float:
        """Convierte formato europeo (1.234,56) a float."""
        if not texto:
            return 0.0
        texto = str(texto).strip()
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
        # Formato: Total: 373,80 €
        patron = re.search(r'Total:\s*(\d+,\d{2})\s*€', texto)
        if patron:
            return self._convertir_europeo(patron.group(1))
        
        return None
    
    def extraer_fecha(self, texto: str) -> Optional[str]:
        """Extrae fecha de la factura."""
        # Formato: Fecha: 26-12-2025
        patron = re.search(r'Fecha:\s*(\d{2})-(\d{2})-(\d{4})', texto)
        if patron:
            return f"{patron.group(1)}/{patron.group(2)}/{patron.group(3)}"
        
        return None
    
    def extraer_numero_factura(self, texto: str) -> Optional[str]:
        """Extrae numero de factura."""
        # Formato: Factura FAC2025A347
        patron = re.search(r'Factura\s+(FAC\d+[A-Z]?\d*)', texto)
        if patron:
            return patron.group(1)
        
        return None
