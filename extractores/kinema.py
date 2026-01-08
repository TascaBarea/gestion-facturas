# -*- coding: utf-8 -*-
"""
Extractor para KINEMA S.COOP.MAD.

Gestoria y asesoria contable/fiscal/laboral de Madrid
CIF: F84600022

Formato factura (PDF digital):
- Lineas servicio: CODIGO DESCRIPCION CANTIDAD PRECIO SUBTOTAL DTO TOTAL
- Ejemplo: 00001 ASESORIA CONTABLE Y FISCAL 1,00 120,00 120,00 120,00
- IVA: 21% (servicios profesionales)
- Puede incluir SUPLIDOS (gastos por cuenta del cliente, sin IVA)

Categoria fija: GESTORIA

Creado: 20/12/2025
"""
from extractores.base import ExtractorBase
from extractores import registrar
from typing import List, Dict, Optional
import re
import pdfplumber


@registrar('KINEMA', 'KINEMA S.COOP', 'KINEMA S.COOP.MAD', 'KINEMA SCOOP')
class ExtractorKinema(ExtractorBase):
    """Extractor para facturas de KINEMA S.COOP.MAD."""
    
    nombre = 'KINEMA'
    cif = 'F84600022'
    metodo_pdf = 'pdfplumber'
    categoria_fija = 'GESTORIA'  # Siempre es gestoria
    
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
        Extrae lineas INDIVIDUALES de servicios.
        
        Formato:
        CODIGO DESCRIPCION CANTIDAD PRECIO SUBTOTAL DTO TOTAL
        00001 ASESORIA CONTABLE Y FISCAL 1,00 120,00 120,00 120,00
        00015 ASESORIA/GESTORIA LABORAL. 8,00 15,00 120,00 120,00
        
        Nota: Los suplidos se manejan aparte (sin IVA)
        """
        lineas = []
        
        # Patron para lineas de servicio
        # CODIGO (5 digitos) + DESCRIPCION + CANTIDAD + PRECIO + SUBTOTAL + [DTO] + TOTAL
        patron_linea = re.compile(
            r'^(\d{5})\s+'                    # Codigo (00001, 00015)
            r'(.+?)\s+'                       # Descripcion
            r'(\d+,\d{2})\s+'                 # Cantidad
            r'(\d+,\d{2})\s+'                 # Precio unitario
            r'(\d+,\d{2})\s+'                 # Subtotal
            r'(\d+,\d{2})\s*$'                # Total (sin descuento)
        , re.MULTILINE)
        
        for match in patron_linea.finditer(texto):
            codigo = match.group(1)
            descripcion = match.group(2).strip()
            cantidad = self._convertir_europeo(match.group(3))
            precio = self._convertir_europeo(match.group(4))
            importe = self._convertir_europeo(match.group(6))  # Ultimo campo es el total
            
            # Limpiar descripcion
            descripcion = re.sub(r'\s+', ' ', descripcion)
            descripcion = descripcion.strip().rstrip('.')
            
            lineas.append({
                'codigo': codigo,
                'articulo': descripcion[:50],
                'cantidad': cantidad,
                'precio_ud': round(precio, 2),
                'iva': 21,
                'base': round(importe, 2),
                'categoria': 'GESTORIA'  # Categoria fija
            })
        
        # Buscar suplidos (gastos por cuenta del cliente, sin IVA)
        patron_suplidos = re.search(r'SUPLIDOS\s+(\d+,\d{2})', texto)
        if patron_suplidos:
            suplidos = self._convertir_europeo(patron_suplidos.group(1))
            if suplidos > 0:
                lineas.append({
                    'codigo': 'SUPL',
                    'articulo': 'SUPLIDOS (GASTOS REGISTRO/TRAMITES)',
                    'cantidad': 1,
                    'precio_ud': round(suplidos, 2),
                    'iva': 0,  # Suplidos sin IVA
                    'base': round(suplidos, 2),
                    'categoria': 'GESTORIA'
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
        # Buscar TOTAL: seguido de importe
        patron = re.search(r'TOTAL:\s*(\d+,\d{2})', texto)
        if patron:
            return self._convertir_europeo(patron.group(1))
        return None
    
    def extraer_fecha(self, texto: str) -> Optional[str]:
        """Extrae fecha de la factura."""
        # Formato: DD/MM/YYYY al final de linea de cabecera
        patron = re.search(r'(\d{2}/\d{2}/\d{4})', texto)
        if patron:
            return patron.group(1)
        return None
    
    def extraer_numero_factura(self, texto: str) -> Optional[str]:
        """Extrae numero de factura."""
        # Formato: Factura 1 NNNNNN (ej: 002235)
        patron = re.search(r'Factura\s+1\s+(\d{6})', texto)
        if patron:
            return patron.group(1)
        return None
