"""
=============================================================================
PLANTILLA PARA NUEVO EXTRACTOR
=============================================================================

Instrucciones:
1. Copia este archivo: extractores/_plantilla.py → extractores/nuevo_proveedor.py
2. Cambia el nombre de la clase
3. Rellena los atributos: nombre, cif, iban, metodo_pdf
4. Implementa extraer_lineas()
5. Prueba: python tests/probar_extractor.py "NUEVO PROVEEDOR" factura.pdf

El extractor se registra automáticamente gracias al decorador @registrar()
"""
from extractores.base import ExtractorBase
from extractores import registrar
from typing import List, Dict, Optional
import re


@registrar('NOMBRE_PROVEEDOR')  # ← CAMBIAR: nombre como aparece en facturas
class ExtractorPlantilla(ExtractorBase):
    """
    Extractor para facturas de [NOMBRE PROVEEDOR].
    
    Formato de factura:
    - [Describir formato: tabla, líneas, etc.]
    - [IVA aplicable: 21%, 10%, 4%]
    - [Notas especiales]
    
    Creado: [FECHA]
    """
    
    # === CONFIGURACIÓN DEL PROVEEDOR ===
    nombre = 'NOMBRE_PROVEEDOR'  # ← CAMBIAR
    cif = 'B00000000'            # ← CAMBIAR: CIF real
    iban = 'ES00 0000 0000 00'   # ← CAMBIAR: IBAN real (vacío '' si pago tarjeta)
    metodo_pdf = 'pypdf'         # ← CAMBIAR si necesario: 'pypdf', 'pdfplumber', 'ocr'
    
    # === EXTRACCIÓN DE LÍNEAS (OBLIGATORIO) ===
    
    def extraer_lineas(self, texto: str) -> List[Dict]:
        """
        Extrae las líneas de producto de la factura.
        
        Args:
            texto: Texto extraído del PDF
            
        Returns:
            Lista de diccionarios con las líneas
        """
        lineas = []
        
        # =====================================================================
        # TU CÓDIGO AQUÍ
        # =====================================================================
        
        # Ejemplo 1: Patrón simple - DESCRIPCIÓN ... IMPORTE€
        # patron = r'^(.+?)\s+(\d+[.,]\d{2})\s*€?\s*$'
        # for match in re.finditer(patron, texto, re.MULTILINE):
        #     descripcion = match.group(1).strip()
        #     importe = self._convertir_importe(match.group(2))
        #     lineas.append({
        #         'articulo': descripcion,
        #         'base': self._calcular_base_desde_total(importe, 21),
        #         'iva': 21
        #     })
        
        # Ejemplo 2: Patrón con código - CÓDIGO | DESCRIPCIÓN | CANTIDAD | PRECIO | IMPORTE
        # patron = r'^(\d{4,6})\s+(.+?)\s+(\d+)\s+(\d+[.,]\d{2})\s+(\d+[.,]\d{2})$'
        # for match in re.finditer(patron, texto, re.MULTILINE):
        #     codigo = match.group(1)
        #     descripcion = match.group(2).strip()
        #     cantidad = int(match.group(3))
        #     precio_ud = self._convertir_importe(match.group(4))
        #     importe = self._convertir_importe(match.group(5))
        #     lineas.append({
        #         'codigo': codigo,
        #         'articulo': descripcion,
        #         'cantidad': cantidad,
        #         'precio_ud': precio_ud,
        #         'base': importe,  # Si ya es sin IVA
        #         'iva': 21
        #     })
        
        # Ejemplo 3: Tabla con IVA explícito - PRODUCTO | BASE | IVA% | TOTAL
        # patron = r'(.+?)\s+(\d+[.,]\d{2})\s+(\d+)%\s+(\d+[.,]\d{2})'
        # for match in re.finditer(patron, texto):
        #     descripcion = match.group(1).strip()
        #     base = self._convertir_importe(match.group(2))
        #     iva = int(match.group(3))
        #     lineas.append({
        #         'articulo': descripcion,
        #         'base': base,
        #         'iva': iva
        #     })
        
        # =====================================================================
        # FIN DE TU CÓDIGO
        # =====================================================================
        
        return lineas
    
    # === MÉTODOS OPCIONALES (descomentar si necesario) ===
    
    # def extraer_total(self, texto: str) -> Optional[float]:
    #     """
    #     Sobrescribe si el formato de total es especial.
    #     """
    #     # Ejemplo: buscar "TOTAL: 123,45€"
    #     match = re.search(r'TOTAL[:\s]+(\d+[.,]\d{2})\s*€', texto, re.IGNORECASE)
    #     if match:
    #         return self._convertir_importe(match.group(1))
    #     return None
    
    # def extraer_fecha(self, texto: str) -> Optional[str]:
    #     """
    #     Sobrescribe si el formato de fecha es especial.
    #     """
    #     # Ejemplo: buscar "Fecha: 31-12-2025"
    #     match = re.search(r'Fecha[:\s]+(\d{2})-(\d{2})-(\d{4})', texto)
    #     if match:
    #         return f"{match.group(1)}/{match.group(2)}/{match.group(3)}"
    #     return None
