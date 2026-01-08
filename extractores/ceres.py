# -*- coding: utf-8 -*-
"""
Extractor para CERES (Cervezas artesanas).

Proveedor de cervezas y bebidas.
CIF: B83478669
IBAN: (adeudo - no necesita)

Formato factura:
- Tabla con CODIGO, DESCRIPCION, UDS, PRECIO, DTO, IVA, IMPORTE
- Productos con descuento y sin descuento
- Envases retornables (CE99xxxx)
- Codigos especiales: URG (servicio urgente 3 chars), CLA (caja)
- IVA 21% o 10%

Actualizado: 21/12/2025
- FIX: Patrones flexibles (3-8 chars) para capturar URG (SERVICIO URGENTE)
- FIX: Fallback a OCR para PDFs escaneados (facturas enero 2025)
- FIX: Tolera punto despues del codigo (OCR: CE1393. -> CE1393)
- FIX: Acepta precios enteros o decimales (5 o 5,00)
- FIX: DESCUADRE_6.05 en facturas con SERVICIO URGENTE
"""
from extractores.base import ExtractorBase
from extractores import registrar
from typing import List, Dict, Optional
import re
import pdfplumber


@registrar('CERES', 'CERES CERVEZA', 'CERES CERVEZAS')
class ExtractorCeres(ExtractorBase):
    """Extractor para facturas de CERES."""
    
    nombre = 'CERES'
    cif = 'B83478669'
    iban = ''  # Adeudo
    metodo_pdf = 'pdfplumber'
    
    def extraer(self, pdf_path: str) -> Dict:
        """
        Extrae datos de factura CERES.
        Override para manejar OCR en PDFs escaneados.
        """
        # Guardar path para OCR
        self._pdf_path = pdf_path
        
        # Intentar extraccion normal con pdfplumber
        with pdfplumber.open(pdf_path) as pdf:
            texto = ''
            for page in pdf.pages:
                t = page.extract_text()
                if t:
                    texto += t + '\n'
        
        # Si no hay texto, intentar OCR
        if not texto or len(texto.strip()) < 100:
            texto_ocr = self._extraer_con_ocr()
            if texto_ocr:
                texto = texto_ocr
        
        # Extraer datos
        lineas = self.extraer_lineas(texto)
        total = self.extraer_total(texto)
        fecha = self.extraer_fecha(texto)
        
        return {
            'proveedor': self.nombre,
            'cif': self.cif,
            'fecha': fecha,
            'total': total,
            'lineas': lineas
        }
    
    def _extraer_con_ocr(self) -> Optional[str]:
        """
        Extrae texto usando OCR para PDFs escaneados.
        """
        try:
            from pdf2image import convert_from_path
            import pytesseract
            
            if not hasattr(self, '_pdf_path') or not self._pdf_path:
                return None
            
            # Convertir PDF a imagenes (300 DPI para buena calidad)
            images = convert_from_path(self._pdf_path, dpi=300)
            
            # OCR en cada pagina
            textos = []
            for img in images:
                # Usar 'eng' que funciona bien con numeros
                texto = pytesseract.image_to_string(img, lang='eng')
                if texto:
                    textos.append(texto)
            
            return '\n'.join(textos)
            
        except ImportError:
            # pdf2image o pytesseract no disponible
            return None
        except Exception:
            return None
    
    def extraer_lineas(self, texto: str) -> List[Dict]:
        """
        Extrae lineas de facturas CERES.
        
        Formato columnas: CODIGO DESC UDS PRECIO DTO IVA IMPORTE
        """
        if not texto:
            return []
            
        lineas = []
        codigos_procesados = set()
        
        # Palabras a ignorar en descripciones
        ignorar = ['Albaran', 'Descripcion', 'Producto', 'Codigo']
        
        # =====================================================
        # PATRON CON DESCUENTO: Codigo + Desc + Uds + Precio + Dto + IVA + Importe
        # - Codigos de 3-8 caracteres (URG=3, 001124=6, CE990002=8)
        # - Tolera punto despues del codigo (OCR: CE1393.)
        # - Acepta precios enteros o decimales
        # =====================================================
        patron_con_dto = re.compile(
            r'^([A-Z0-9]{3,8})\.?\s+'       # Codigo (3-8 chars) + punto opcional
            r'(.+?)\s+'                      # Descripcion
            r'(-?\d+)\s+'                    # Unidades
            r'(\d+[,\.]?\d*)\s+'             # Precio/Ud (entero o decimal)
            r'(\d+[,\.]?\d*)\s+'             # Descuento %
            r'(21|10)\s+'                    # IVA
            r'(-?\d+[,\.]\d+)',              # Importe
            re.MULTILINE
        )
        
        for m in patron_con_dto.finditer(texto):
            codigo, desc, uds, precio, dto, iva, importe = m.groups()
            desc_limpia = desc.strip()
            
            if any(x.lower() in desc_limpia.lower() for x in ignorar):
                continue
            
            importe_val = self._convertir_importe(importe)
            if importe_val == 0:
                continue
                
            key = (codigo, importe_val)
            if key in codigos_procesados:
                continue
            codigos_procesados.add(key)
            
            lineas.append({
                'codigo': codigo,
                'articulo': desc_limpia[:50],
                'cantidad': abs(int(uds)),
                'precio_ud': self._convertir_importe(precio),
                'iva': int(iva),
                'base': importe_val
            })
        
        # =====================================================
        # PATRON SIN DESCUENTO: Codigo + Desc + Uds + Precio + IVA + Importe
        # Para productos como SOUSAS y URG SERVICIO URGENTE
        # =====================================================
        patron_sin_dto = re.compile(
            r'^([A-Z0-9]{3,8})\.?\s+'       # Codigo (3-8 chars) + punto opcional
            r'(.+?)\s+'                      # Descripcion
            r'(-?\d+)\s+'                    # Unidades
            r'(\d+[,\.]?\d*)\s+'             # Precio/Ud (entero o decimal)
            r'(21|10)\s+'                    # IVA (sin dto antes)
            r'(-?\d+[,\.]\d+)',              # Importe
            re.MULTILINE
        )
        
        for m in patron_sin_dto.finditer(texto):
            codigo, desc, uds, precio, iva, importe = m.groups()
            desc_limpia = desc.strip()
            
            if any(x.lower() in desc_limpia.lower() for x in ignorar):
                continue
            if 'ENVASE' in desc_limpia.upper():
                continue  # Procesado por patron especifico
            
            importe_val = self._convertir_importe(importe)
            if importe_val == 0:
                continue
                
            key = (codigo, importe_val)
            if key in codigos_procesados:
                continue
            codigos_procesados.add(key)
            
            precio_val = self._convertir_importe(precio) if precio else 0
            
            lineas.append({
                'codigo': codigo,
                'articulo': desc_limpia[:50],
                'cantidad': abs(int(uds)),
                'precio_ud': precio_val,
                'iva': int(iva),
                'base': importe_val
            })
        
        # =====================================================
        # PATRON ENVASES LITROS: CE99xxxx ENVASE X lit.
        # =====================================================
        patron_envase = re.compile(
            r'^(CE99\d{4})\.?\s+'            # Codigo CE99xxxx + punto opcional
            r'(ENVASE\s+\d+\s*lit\.?)\s+'    # Descripcion
            r'(-?\d+)\s+'                    # Unidades
            r'(\d+[,\.]?\d*)\s+'             # Precio (entero o decimal)
            r'(21|10)\s+'                    # IVA
            r'(-?\d+[,\.]\d+)',              # Importe
            re.MULTILINE
        )
        
        for m in patron_envase.finditer(texto):
            codigo, desc, uds, precio, iva, importe = m.groups()
            importe_val = self._convertir_importe(importe)
            
            key = (codigo, importe_val)
            if key in codigos_procesados:
                continue
            codigos_procesados.add(key)
            
            lineas.append({
                'codigo': codigo,
                'articulo': desc.strip(),
                'cantidad': abs(int(uds)),
                'precio_ud': self._convertir_importe(precio),
                'iva': int(iva),
                'base': importe_val
            })
        
        # =====================================================
        # PATRON ENVASES ALH: CE99xxxx ENVASE 1/5 ALH
        # =====================================================
        patron_envase_alh = re.compile(
            r'^(CE99\d{4})\.?\s+'            # Codigo CE99xxxx + punto opcional
            r'(ENVASE\s+\d/\d\s+ALH)\s+'     # ENVASE 1/5 ALH
            r'(-?\d+)\s+'                    # Unidades
            r'(\d+[,\.]?\d*)\s+'             # Precio (entero o decimal)
            r'(21|10)\s+'                    # IVA
            r'(-?\d+[,\.]\d+)',              # Importe
            re.MULTILINE
        )
        
        for m in patron_envase_alh.finditer(texto):
            codigo, desc, uds, precio, iva, importe = m.groups()
            importe_val = self._convertir_importe(importe)
            
            key = (codigo, importe_val)
            if key in codigos_procesados:
                continue
            codigos_procesados.add(key)
            
            lineas.append({
                'codigo': codigo,
                'articulo': desc.strip(),
                'cantidad': abs(int(uds)),
                'precio_ud': self._convertir_importe(precio),
                'iva': int(iva),
                'base': importe_val
            })
        
        # =====================================================
        # PATRON CE99 GENERICO
        # =====================================================
        patron_ce99_generico = re.compile(
            r'^(CE99\d{4})\.?\s+'            # Codigo CE99xxxx + punto opcional
            r'(.+?)\s+'                      # Descripcion
            r'(-?\d+)\s+'                    # Unidades
            r'(\d+[,\.]?\d*)\s+'             # Precio (entero o decimal)
            r'(21|10)\s+'                    # IVA
            r'(-?\d+[,\.]\d+)',              # Importe
            re.MULTILINE
        )
        
        for m in patron_ce99_generico.finditer(texto):
            codigo, desc, uds, precio, iva, importe = m.groups()
            desc_limpia = desc.strip()
            
            if 'ENVASE' in desc_limpia.upper():
                continue  # Ya procesado
                
            importe_val = self._convertir_importe(importe)
            key = (codigo, importe_val)
            if key in codigos_procesados:
                continue
            codigos_procesados.add(key)
            
            lineas.append({
                'codigo': codigo,
                'articulo': desc_limpia[:50],
                'cantidad': abs(int(uds)),
                'precio_ud': self._convertir_importe(precio),
                'iva': int(iva),
                'base': importe_val
            })
        
        # =====================================================
        # CLA (caja retornable): CLA: X €
        # =====================================================
        cla_match = re.search(r'CLA:\s*(\d+)', texto)
        if cla_match:
            cla_cantidad = int(cla_match.group(1))
            if cla_cantidad > 0:
                key = ('CLA', float(cla_cantidad))
                if key not in codigos_procesados:
                    codigos_procesados.add(key)
                    lineas.append({
                        'codigo': 'CLA',
                        'articulo': 'CAJA RETORNABLE',
                        'cantidad': cla_cantidad,
                        'precio_ud': 1.0,
                        'iva': 21,
                        'base': float(cla_cantidad)
                    })
        
        return lineas
    
    def extraer_total(self, texto: str) -> Optional[float]:
        """Extrae el total de la factura."""
        if not texto:
            return None
            
        # Patron principal: Importe TOTAL ........ XXX,XX
        m = re.search(r'Importe\s+TOTAL\s*\.+\s*([\d.,]+)', texto)
        if m:
            return self._convertir_importe(m.group(1))
        
        # Patron alternativo (OCR): Vencimientos: XXX,XX
        m = re.search(r'Vencimientos:\s*([\d.,]+)', texto)
        if m:
            return self._convertir_importe(m.group(1))
        
        return None
    
    def extraer_fecha(self, texto: str) -> Optional[str]:
        """Extrae la fecha de la factura."""
        if not texto:
            return None
            
        # Formato: DD/MM/YYYY
        m = re.search(r'(\d{2}/\d{2}/\d{4})', texto)
        if m:
            return m.group(1)
        return None
    
    def extraer_numero_factura(self, texto: str) -> Optional[str]:
        """
        Extrae número de factura (REF).
        Formato en PDF: "2539610 03/10/2025 B87760575 B2B DIARIO"
        El número es el primero de 7 dígitos después de "Numero Fecha CIF/DNI".
        """
        if not texto:
            return None
        
        # Buscar línea con formato: NUMERO FECHA CIF FORMA_PAGO
        patron = re.search(
            r'Numero\s+Fecha\s+CIF/DNI.*?\n'
            r'(\d{7})\s+\d{2}/\d{2}/\d{4}',
            texto, re.IGNORECASE
        )
        if patron:
            return patron.group(1)
        
        # Alternativa: buscar directamente el patrón
        patron2 = re.search(r'\n(\d{7})\s+\d{2}/\d{2}/\d{4}\s+B\d+', texto)
        if patron2:
            return patron2.group(1)
        
        return None
