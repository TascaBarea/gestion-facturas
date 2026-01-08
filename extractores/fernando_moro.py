# -*- coding: utf-8 -*-
"""
Extractor para FERNANDO JOAQUÍN MORO HEREDIA (Chocolates artesanales)

Chocolatero artesanal de Llerena (Badajoz)
NIF: 08881383W (persona física)
IBAN: ES51 0182 0892 2502 0158 8601

Formato factura:
ARTÍCULO DESCRIPCIÓN CANTIDAD PRECIO UNIDAD SUBTOTAL DTO. TOTAL
1 Chocolate Valle Kilombero 10,00 3,60 36,00 36,00
envio 1,00 9,00 9,00 9,00

IVA: 10% (chocolates), 21% (envío)
Categoria fija: DULCES

NOTA: El coste de envío (IVA 21%) se reparte proporcionalmente
entre los chocolates, sumándolo a su base.

Creado: 04/01/2026
"""
from extractores.base import ExtractorBase
from extractores import registrar
from typing import List, Dict, Optional
import re
import pdfplumber


@registrar('FERNANDO MORO', 'FERNANDO JOAQUIN MORO', 'FERNANDO JOAQUÍN MORO',
           'MORO HEREDIA', 'CHOCOLATES MORO')
class ExtractorFernandoMoro(ExtractorBase):
    """Extractor para facturas de FERNANDO MORO (Chocolates)."""
    
    nombre = 'FERNANDO MORO'
    cif = '08881383W'
    iban = 'ES51 0182 0892 2502 0158 8601'
    metodo_pdf = 'pdfplumber'
    categoria_fija = 'DULCES'
    
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
        Extrae lineas de productos (chocolates).
        
        Formato:
        1 Chocolate Valle Kilombero 10,00 3,60 36,00 36,00
        envio 1,00 9,00 9,00 9,00
        
        El envío se reparte proporcionalmente entre los productos.
        """
        lineas = []
        coste_envio = 0.0
        productos_temp = []
        
        # Buscar línea de envío
        patron_envio = re.search(
            r'envio\s+[\d,]+\s+(\d+[,\.]\d+)\s+(\d+[,\.]\d+)\s+(\d+[,\.]\d+)',
            texto, re.IGNORECASE
        )
        if patron_envio:
            coste_envio = self._convertir_numero(patron_envio.group(3))
        
        # Patron para líneas de producto
        # Código + Descripción + Cantidad + Precio + Subtotal + Total
        # Ej: 1 Chocolate Valle Kilombero 10,00 3,60 36,00 36,00
        # Ej: 02 Xhocolate DArio 10,00 3,60 36,00 36,00
        patron_producto = re.compile(
            r'^(\d{1,2})\s+'                           # Código (1-2 dígitos)
            r'([A-Za-zñÑáéíóúÁÉÍÓÚ][A-Za-zñÑáéíóúÁÉÍÓÚ\s]+?)\s+'  # Descripción
            r'(\d+[,\.]\d{2})\s+'                      # Cantidad
            r'(\d+[,\.]\d{2})\s+'                      # Precio unitario
            r'(\d+[,\.]\d{2})\s+'                      # Subtotal
            r'(\d+[,\.]\d{2})\s*$'                     # Total
        , re.MULTILINE)
        
        for match in patron_producto.finditer(texto):
            codigo = match.group(1)
            descripcion = match.group(2).strip()
            cantidad = self._convertir_numero(match.group(3))
            precio = self._convertir_numero(match.group(4))
            total = self._convertir_numero(match.group(6))
            
            # Filtrar cabeceras y líneas no válidas
            if any(x in descripcion.upper() for x in ['ARTÍCULO', 'ARTICULO', 'DESCRIPCIÓN', 'DESCRIPCION']):
                continue
            
            if total > 0:
                productos_temp.append({
                    'codigo': codigo,
                    'descripcion': descripcion,
                    'cantidad': cantidad,
                    'precio': precio,
                    'total': total
                })
        
        # Calcular suma total para proporcionalidad
        suma_totales = sum(p['total'] for p in productos_temp)
        
        # Repartir coste de envío proporcionalmente
        for prod in productos_temp:
            base = prod['total']
            
            if coste_envio > 0 and suma_totales > 0:
                proporcion = prod['total'] / suma_totales
                # Envío ya viene como base (sin IVA), repartir directamente
                base += coste_envio * proporcion
            
            lineas.append({
                'codigo': prod['codigo'],
                'articulo': prod['descripcion'][:50],
                'cantidad': int(prod['cantidad']),
                'precio_ud': round(prod['precio'], 2),
                'iva': 10,
                'base': round(base, 2),
                'categoria': self.categoria_fija
            })
        
        return lineas
    
    def _convertir_numero(self, texto: str) -> float:
        """Convierte texto a float."""
        if not texto:
            return 0.0
        texto = str(texto).strip()
        texto = texto.replace(',', '.')
        try:
            return float(texto)
        except:
            return 0.0
    
    def extraer_total(self, texto: str) -> Optional[float]:
        """Extrae total de la factura."""
        # Formato: TOTAL: seguido de importe al final
        patron = re.search(r'TOTAL:\s*\n?\s*(\d+[,\.]\d{2})', texto, re.IGNORECASE)
        if patron:
            return self._convertir_numero(patron.group(1))
        
        # Alternativa: último número grande en el texto
        patron2 = re.search(r'(\d{2,3}[,\.]\d{2})\s*$', texto)
        if patron2:
            return self._convertir_numero(patron2.group(1))
        
        return None
    
    def extraer_fecha(self, texto: str) -> Optional[str]:
        """Extrae fecha de la factura."""
        # Formato en cabecera: DD/MM/YYYY al final de línea con número factura
        patron = re.search(r'(\d{2}/\d{2}/\d{4})', texto)
        if patron:
            return patron.group(1)
        
        return None
    
    def extraer_numero_factura(self, texto: str) -> Optional[str]:
        """Extrae numero de factura."""
        # Formato: 000067 (6 dígitos después del "1" de página)
        patron = re.search(r'\b1\s+(\d{6})\s+1\s+\d{2}/\d{2}/\d{4}', texto)
        if patron:
            return patron.group(1)
        
        # Alternativa
        patron2 = re.search(r'(\d{6})\s+\d+\s+\d{2}/\d{2}/\d{4}', texto)
        if patron2:
            return patron2.group(1)
        
        return None
