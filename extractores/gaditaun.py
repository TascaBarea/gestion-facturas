# -*- coding: utf-8 -*-
"""
Extractor para GADITAUN (María Linarejos Martínez Rodríguez)
Conservas, vinos y aceites de Cádiz.

Autor: Claude (ParsearFacturas v5.0)
Fecha: 27/12/2025
Corregido: 28/12/2025 - Integración con sistema

PECULIARIDAD: Los PDFs requieren OCR (Print to PDF desde Zoho CRM).
             El IVA se calcula desde Impuestos/Total (puede ser 4%, 10% o 21%).
             La base se calcula como: Base = Total / (1 + IVA/100)
"""
from extractores.base import ExtractorBase
from extractores import registrar
import re
from typing import List, Dict, Optional


@registrar('GADITAUN', 'MARILINA', 'MARIA LINAREJOS', 'MARÍA LINAREJOS', 
           'GADITAUN MARILINA', 'MARILINA GADITAUN', 'GARDITAUN')
class ExtractorGaditaun(ExtractorBase):
    """
    Extractor para facturas de GADITAUN.
    
    Formato: Print to PDF desde Zoho CRM (requiere OCR).
    IVA variable: 4% (aceite), 10% (conservas), 21% (vinos).
    """
    
    nombre = 'GADITAUN'
    nombre_fiscal = 'María Linarejos Martínez Rodríguez'
    cif = 'REDACTED_DNI'
    iban = 'REDACTED_IBAN'
    metodo_pdf = 'ocr'  # Requiere OCR
    
    # Mapeo de productos a categorías (basado en Excel del usuario)
    CATEGORIAS = {
        'picarninas': ('CONSERVAS VEGETALES', 10),
        'berenjenas': ('CONSERVAS VEGETALES', 10),
        'picarragos': ('CONSERVAS VEGETALES', 10),
        'pate de tagarninas': ('CONSERVAS VEGETALES', 10),
        'tagarninas': ('CONSERVAS VEGETALES', 10),
        'duo vites': ('VINOS', 21),
        'relicta': ('VINOS', 21),
        'junus': ('VINOS', 21),
        'edalo': ('VINO BLANCO ZALEMA', 21),
        'aceite': ('ACEITES Y VINAGRES', 4),
        'aove': ('ACEITES Y VINAGRES', 4),
    }
    
    def extraer_texto_ocr(self, pdf_path: str) -> str:
        """Extrae texto del PDF usando OCR (Tesseract)."""
        try:
            from pdf2image import convert_from_path
            import pytesseract
            
            images = convert_from_path(pdf_path, dpi=300)
            textos = []
            for img in images:
                texto = pytesseract.image_to_string(img, lang='spa')
                textos.append(texto)
            return '\n'.join(textos)
        except Exception as e:
            print(f"Error OCR: {e}")
            return ""
    
    def extraer_texto(self, pdf_path: str) -> str:
        """Método principal de extracción - usa OCR."""
        return self.extraer_texto_ocr(pdf_path)
    
    def extraer_lineas(self, texto: str) -> List[Dict]:
        """
        Extrae líneas de productos de la factura.
        
        Maneja DOS formatos de OCR:
        
        FORMATO 1 (todo en una línea):
        '1 duo vites regantío viejo dv2rv 8,50 € 6 51,00€ 8,50€ 8,93€ 51,43€'
        
        FORMATO 2 (nombre y valores separados):
        '1 junus blanco regantío viejo jbrv'
        ...
        '8,85 € 6 53,10€ 8,85€ 9,290€ 53,54 €'
        """
        # Intentar primero con formato 1 (todo en una línea)
        lineas = self._extraer_formato_compacto(texto)
        
        # Si no encontramos nada, intentar formato 2 (separado)
        if not lineas:
            lineas = self._extraer_formato_separado(texto)
        
        return lineas
    
    def _extraer_formato_compacto(self, texto: str) -> List[Dict]:
        """Extrae líneas cuando todo está en una sola línea."""
        lineas = []
        
        # Patrón para inicio de línea
        patron_inicio = re.compile(
            r'^(\d)\s+'                                   # Nº de serie
            r'([a-záéíóúñ][\w\sáéíóúñ]+?)\s+'            # Nombre
            r'(\d+[.,]\d{2})\s*€?\s+'                     # Precio unidad
            r'(\d+)\s+',                                  # Cantidad
            re.IGNORECASE
        )
        
        patron_valores = re.compile(r'([\d.,/]+)\s*€')
        
        for line in texto.split('\n'):
            if not re.match(r'^\d\s+[a-záéíóúñ]', line, re.IGNORECASE):
                continue
            
            match_inicio = patron_inicio.match(line)
            if not match_inicio:
                continue
            
            # Verificar que tiene valores € (distingue de formato separado)
            valores = patron_valores.findall(line)
            if len(valores) < 4:  # Mínimo: precio, subtotal, impuestos, total
                continue
            
            num_serie, nombre, precio_str, cantidad_str = match_inicio.groups()
            cantidad = int(cantidad_str)
            
            impuestos_raw = valores[-2]
            total_raw = valores[-1]
            
            impuestos_raw = re.sub(r'[/]', '', impuestos_raw)
            impuestos = self._convertir_europeo(impuestos_raw)
            total = self._convertir_europeo(total_raw)
            
            if total < 0.01 or cantidad < 1:
                continue
            
            tipo_iva = self._detectar_iva(impuestos, total)
            base = round(total / (1 + tipo_iva / 100), 2)
            precio_ud = round(base / cantidad, 2) if cantidad > 0 else 0
            categoria = self._detectar_categoria(nombre)
            nombre_limpio = self._limpiar_nombre(nombre)
            
            lineas.append({
                'codigo': num_serie,
                'articulo': nombre_limpio[:60],
                'cantidad': cantidad,
                'precio_ud': precio_ud,
                'iva': tipo_iva,
                'base': base,
                'categoria': categoria
            })
        
        return lineas
    
    def _extraer_formato_separado(self, texto: str) -> List[Dict]:
        """
        Extrae líneas cuando nombre y valores están en líneas separadas.
        """
        lineas = []
        texto_lineas = texto.split('\n')
        
        # Buscar nombre del producto
        patron_nombre = re.compile(r'^(\d)\s+([a-záéíóúñ][\w\sáéíóúñ]+)$', re.IGNORECASE)
        
        # Formato A: valores con total
        patron_valores_completo = re.compile(
            r'^(\d+[.,]\d{2})\s*€\s+'    # Precio
            r'(\d+)\s+'                   # Cantidad
            r'[\d.,]+€?\s+'               # Subtotal
            r'[\d.,]+€?\s+'               # Descuento
            r'([\d.,]+)€?\s+'             # Impuestos
            r'(\d+[.,]\d{2})\s*€',        # Total
            re.IGNORECASE
        )
        
        # Formato B: valores sin total (total en línea separada)
        patron_valores_parcial = re.compile(
            r'^(\d+[.,]\d{2})\s*€\s+'    # Precio
            r'(\d+)\s+'                   # Cantidad
            r'[\d.,]+€?\s+'               # Subtotal
            r'[\d.,]+\s*€?\s+'            # Descuento
            r'([\d.,]+)\s*€?\s*$',        # Impuestos (final de línea)
            re.IGNORECASE
        )
        
        producto_actual = None
        
        for i, line in enumerate(texto_lineas):
            line = line.strip()
            
            # Buscar nombre de producto
            match_nombre = patron_nombre.match(line)
            if match_nombre:
                producto_actual = {
                    'num_serie': match_nombre.group(1),
                    'nombre': match_nombre.group(2).strip()
                }
                continue
            
            # Formato A: línea con todos los valores
            match_completo = patron_valores_completo.match(line)
            if match_completo and producto_actual:
                precio_str = match_completo.group(1)
                cantidad = int(match_completo.group(2))
                impuestos = self._convertir_europeo(match_completo.group(3))
                total = self._convertir_europeo(match_completo.group(4))
                
                if total > 0 and cantidad > 0:
                    tipo_iva = self._detectar_iva(impuestos, total)
                    base = round(total / (1 + tipo_iva / 100), 2)
                    precio_ud = round(base / cantidad, 2)
                    categoria = self._detectar_categoria(producto_actual['nombre'])
                    nombre_limpio = self._limpiar_nombre(producto_actual['nombre'])
                    
                    lineas.append({
                        'codigo': producto_actual['num_serie'],
                        'articulo': nombre_limpio[:60],
                        'cantidad': cantidad,
                        'precio_ud': precio_ud,
                        'iva': tipo_iva,
                        'base': base,
                        'categoria': categoria
                    })
                
                producto_actual = None
                continue
            
            # Formato B: valores parciales
            match_parcial = patron_valores_parcial.match(line)
            if match_parcial and producto_actual:
                precio_str = match_parcial.group(1)
                cantidad = int(match_parcial.group(2))
                impuestos = self._convertir_europeo(match_parcial.group(3))
                
                # Buscar total en siguientes líneas
                for j in range(i+1, min(i+5, len(texto_lineas))):
                    next_line = texto_lineas[j].strip()
                    match_total = re.search(r'(\d+[.,]\d{2})\s*€', next_line)
                    if match_total:
                        total = self._convertir_europeo(match_total.group(1))
                        if total > 0 and cantidad > 0:
                            tipo_iva = self._detectar_iva(impuestos, total)
                            base = round(total / (1 + tipo_iva / 100), 2)
                            precio_ud = round(base / cantidad, 2)
                            categoria = self._detectar_categoria(producto_actual['nombre'])
                            nombre_limpio = self._limpiar_nombre(producto_actual['nombre'])
                            
                            lineas.append({
                                'codigo': producto_actual['num_serie'],
                                'articulo': nombre_limpio[:60],
                                'cantidad': cantidad,
                                'precio_ud': precio_ud,
                                'iva': tipo_iva,
                                'base': base,
                                'categoria': categoria
                            })
                        break
                
                producto_actual = None
        
        return lineas
    
    def _detectar_iva(self, impuestos: float, total: float) -> int:
        """
        Detecta el tipo de IVA basándose en impuestos y total.
        IVA% = (impuestos / (total - impuestos)) * 100
        """
        if total <= 0 or impuestos <= 0:
            return 10  # Default
        
        base_estimada = total - impuestos
        if base_estimada <= 0:
            return 10
        
        iva_calculado = (impuestos / base_estimada) * 100
        
        # Aproximar al tipo más cercano
        tipos = [4, 10, 21]
        tipo_cercano = min(tipos, key=lambda x: abs(x - iva_calculado))
        
        return tipo_cercano
    
    def _detectar_categoria(self, nombre: str) -> str:
        """Detecta la categoría según el nombre del producto."""
        nombre_lower = nombre.lower()
        
        for clave, (categoria, _) in self.CATEGORIAS.items():
            if clave in nombre_lower:
                return categoria
        
        # Default según patrones
        if any(x in nombre_lower for x in ['vino', 'tinto', 'blanco', 'crianza', 'roble']):
            return 'VINOS'
        if any(x in nombre_lower for x in ['aceite', 'oliva', 'aove']):
            return 'ACEITES Y VINAGRES'
        
        return 'CONSERVAS VEGETALES'  # Default para GADITAUN
    
    def _limpiar_nombre(self, nombre: str) -> str:
        """Limpia el nombre del producto."""
        # Eliminar caracteres extraños de OCR
        nombre = re.sub(r'[^\w\sáéíóúñÁÉÍÓÚÑ.,/-]', '', nombre)
        nombre = ' '.join(nombre.split())
        return nombre
    
    def extraer_numero_factura(self, texto: str) -> Optional[str]:
        """Extrae número de factura (formato: 2025-321)."""
        patron = re.search(r'Número de Factura\s*:?\s*(\d{4}-\d+)', texto, re.IGNORECASE)
        if patron:
            return patron.group(1)
        
        # Alternativa
        patron2 = re.search(r'Factura\s*:?\s*(\d{4}-\d+)', texto, re.IGNORECASE)
        if patron2:
            return patron2.group(1)
        
        return None
    
    def extraer_fecha(self, texto: str) -> Optional[str]:
        """Extrae fecha de factura (formato: DD/MM/YYYY)."""
        patron = re.search(r'Fecha de Factura:?\s*(\d{2}/\d{2}/\d{4})', texto, re.IGNORECASE)
        if patron:
            return patron.group(1)
        
        # Alternativa con año corto
        patron2 = re.search(r'Fecha de Factura:?\s*(\d{2}/\d{2}/\d{2})', texto, re.IGNORECASE)
        if patron2:
            fecha = patron2.group(1)
            partes = fecha.split('/')
            if len(partes) == 3:
                return f"{partes[0]}/{partes[1]}/20{partes[2]}"
        
        return None
    
    def extraer_total(self, texto: str) -> Optional[float]:
        """Extrae el total de la factura."""
        # Formato 1: "Total general 258,60 €"
        patron = re.search(r'Total\s+general\s+(\d+[.,]\d{2})\s*€?', texto, re.IGNORECASE)
        if patron:
            return self._convertir_europeo(patron.group(1))
        
        # Formato 2: Buscar en desglose "Total general" seguido de valor en línea siguiente
        patron2 = re.search(r'Total\s+general\s*\n\s*(\d+[.,]\d{2})\s*€?', texto, re.IGNORECASE)
        if patron2:
            return self._convertir_europeo(patron2.group(1))
        
        # Formato 3: "TOTAL FACTURA" o similar
        patron3 = re.search(r'TOTAL\s+FACTURA\s*:?\s*(\d+[.,]\d{2})\s*€?', texto, re.IGNORECASE)
        if patron3:
            return self._convertir_europeo(patron3.group(1))
        
        # Formato 4: Buscar último valor € grande en el documento
        todos_valores = re.findall(r'(\d+[.,]\d{2})\s*€', texto)
        if todos_valores:
            # Tomar el valor más grande como total (heurística)
            valores_float = [self._convertir_europeo(v) for v in todos_valores]
            return max(valores_float)
        
        return None
    
    def _convertir_europeo(self, texto: str) -> float:
        """Convierte formato europeo (1.234,56) a float. Maneja errores OCR."""
        if not texto:
            return 0.0
        texto = texto.strip()
        
        # Eliminar caracteres no numéricos excepto . y ,
        texto = re.sub(r'[^\d.,]', '', texto)
        
        if not texto:
            return 0.0
        
        if '.' in texto and ',' in texto:
            texto = texto.replace('.', '').replace(',', '.')
        elif ',' in texto:
            texto = texto.replace(',', '.')
        elif len(texto) >= 3 and '.' not in texto:
            # Número sin decimales con 3+ dígitos (ej: "929" -> "9.29")
            texto = texto[:-2] + '.' + texto[-2:]
        
        try:
            return float(texto)
        except:
            return 0.0
