"""
Clase base para todos los extractores de facturas.

Todos los extractores deben heredar de ExtractorBase e implementar
el método extraer_lineas().

Actualizado: 07/01/2026 - Mejora extracción número factura (extraer_referencia)

Ejemplo:
    from extractores.base import ExtractorBase
    from extractores import registrar
    
    @registrar('MI PROVEEDOR')
    class ExtractorMiProveedor(ExtractorBase):
        nombre = 'MI PROVEEDOR'
        cif = 'B12345678'
        iban = 'ES00 0000 0000 00'
        
        def extraer_lineas(self, texto: str) -> List[Dict]:
            lineas = []
            # ... lógica de extracción
            return lineas
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Optional
import re


class ExtractorBase(ABC):
    """
    Clase base abstracta para extractores de facturas.
    
    Atributos de clase (sobrescribir en subclases):
        nombre: Nombre del proveedor
        cif: CIF del proveedor
        iban: IBAN del proveedor (vacío si pago tarjeta/efectivo)
        metodo_pdf: Método de extracción ('pypdf', 'pdfplumber', 'ocr')
    """
    
    # === ATRIBUTOS DE CLASE (sobrescribir en subclases) ===
    nombre: str = ''
    cif: str = ''
    iban: str = ''
    metodo_pdf: str = 'pypdf'  # 'pypdf', 'pdfplumber', 'ocr'
    
    # === MÉTODO ABSTRACTO (obligatorio implementar) ===
    
    @abstractmethod
    def extraer_lineas(self, texto: str) -> List[Dict]:
        """
        Extrae las líneas de producto de la factura.
        
        Args:
            texto: Texto extraído del PDF
            
        Returns:
            Lista de diccionarios con las líneas:
            [
                {
                    'articulo': str,      # Nombre del producto (obligatorio)
                    'base': float,        # Importe SIN IVA (obligatorio)
                    'iva': int,           # Porcentaje IVA: 4, 10 o 21 (obligatorio)
                    'codigo': str,        # Código producto (opcional)
                    'cantidad': float,    # Cantidad (opcional)
                    'precio_ud': float,   # Precio unitario (opcional)
                },
                ...
            ]
        """
        pass
    
    # === MÉTODOS OPCIONALES (pueden sobrescribirse) ===
    
    def extraer_total(self, texto: str) -> Optional[float]:
        """
        Extrae el total de la factura.
        
        Por defecto usa patrones genéricos. Sobrescribir si el formato
        del proveedor es especial.
        
        Args:
            texto: Texto extraído del PDF
            
        Returns:
            Total de la factura o None si no se encuentra
        """
        # Patrones ordenados de más específico a más genérico
        patrones = [
            # TOTAL €: 890,08
            r'TOTAL\s*€[:\s]*(\d{1,3}(?:[.,]\d{3})*[.,]\d{2})',
            # TOTAL FACTURA: 123,45
            r'TOTAL\s*FACTURA[:\s]*(\d{1,3}(?:[.,]\d{3})*[.,]\d{2})',
            # TOTAL A PAGAR: 123,45
            r'TOTAL\s*A\s*PAGAR[:\s]*(\d{1,3}(?:[.,]\d{3})*[.,]\d{2})',
            # TOTAL: 123,45 €
            r'\bTOTAL[:\s]+(\d{1,3}(?:[.,]\d{3})*[.,]\d{2})\s*€',
            # TOTAL 123,45
            r'\bTOTAL[:\s]+(\d{1,3}(?:[.,]\d{3})*[.,]\d{2})',
        ]
        
        for patron in patrones:
            match = re.search(patron, texto, re.IGNORECASE | re.MULTILINE)
            if match:
                total_str = match.group(1)
                return self._convertir_importe(total_str)
        
        return None
    
    def extraer_fecha(self, texto: str) -> Optional[str]:
        """
        Extrae la fecha de la factura.
        
        Por defecto busca formato DD/MM/YYYY. Sobrescribir si el formato
        del proveedor es diferente.
        
        Args:
            texto: Texto extraído del PDF
            
        Returns:
            Fecha en formato DD/MM/YYYY o None si no se encuentra
        """
        # Patrón estándar DD/MM/YYYY
        patron = r'(\d{1,2})[/\-](\d{1,2})[/\-](\d{4})'
        match = re.search(patron, texto)
        
        if match:
            dia = match.group(1).zfill(2)
            mes = match.group(2).zfill(2)
            año = match.group(3)
            return f"{dia}/{mes}/{año}"
        
        return None
    
    def extraer_referencia(self, texto: str) -> Optional[str]:
        """
        Extrae el número de referencia/factura.
        
        IMPORTANTE: Si la subclase define extraer_numero_factura(), 
        se usa automáticamente ese método. Esto permite compatibilidad
        con extractores que usen cualquiera de los dos nombres.
        
        Actualizado 07/01/2026: Patrones mejorados + filtros anti-falsos positivos
        
        Args:
            texto: Texto extraído del PDF
            
        Returns:
            Número de referencia o None si no se encuentra
        """
        # =========================================================
        # COMPATIBILIDAD: Si la subclase define extraer_numero_factura,
        # usarlo automáticamente
        # =========================================================
        if hasattr(self, 'extraer_numero_factura') and callable(getattr(self, 'extraer_numero_factura')):
            # Verificar que no es el método heredado (evitar recursión)
            metodo = getattr(self, 'extraer_numero_factura')
            if metodo.__func__ is not ExtractorBase.extraer_numero_factura:
                resultado = metodo(texto)
                if resultado and self._es_referencia_valida(resultado):
                    return resultado
        
        # =========================================================
        # PATRONES GENÉRICOS MEJORADOS (07/01/2026)
        # Ordenados de más específico a más genérico
        # =========================================================
        patrones = [
            # Formato F00-00-00000 (CVNE y similares)
            r'\b(F\d{2}-\d{2}-\d{4,6})\b',
            
            # "Factura Nº: XXX" o "Fra. Nº: XXX" (con número después)
            r'(?:Factura|Fra\.?)\s*[Nn]º[:\s]*([A-Z]?\d{5,12}(?:\s*[A-Z])?)',
            
            # "Nº Factura: XXX" o "Nº Fra.: XXX"
            r'[Nn]º\s*(?:Factura|Fra\.?)[:\s]*([A-Z]?\d{5,12}(?:\s*[A-Z])?)',
            
            # "NºA XXXXXX" (SABORES PATERNA y similares)
            r'[Nn]º[A-Z]\s*(\d{5,8})',
            
            # Cabecera tabla: FECHA FACTURA CLIENTE → línea con A XXXX
            r'^\d{2}/\d{2}/\d{2}\s+([A-Z]\s*\d{3,6})\s+\d',
            
            # "Factura: XXXX" simple
            r'(?:Factura|FACTURA)[:\s]+([A-Z]?\s*\d{3,10})',
            
            # "Invoice: XXXX" o "Invoice #XXXX"
            r'[Ii]nvoice[:\s#]+([A-Z0-9][-/]?[A-Z0-9]{3,12})',
            
            # "Ref: XXXX" o "Ref.: XXXX"
            r'[Rr]ef\.?[:\s]+([A-Z0-9][-/]?[A-Z0-9]{3,12})',
            
            # "Nº XXXXXX" (genérico, al menos 5 dígitos)
            r'[Nn]º[:\s]*(\d{5,10})',
        ]
        
        for patron in patrones:
            match = re.search(patron, texto, re.MULTILINE)
            if match:
                resultado = match.group(1).strip()
                if self._es_referencia_valida(resultado):
                    return resultado
        
        return None
    
    def extraer_numero_factura(self, texto: str) -> Optional[str]:
        """
        Método base para extraer número de factura.
        Las subclases pueden sobrescribir este método con lógica específica.
        
        Por defecto, devuelve None para que extraer_referencia() use
        sus patrones genéricos.
        """
        return None
    
    def _es_referencia_valida(self, ref: str) -> bool:
        """
        Valida que una referencia extraída no sea un falso positivo.
        
        Filtra:
        - Teléfonos (9 dígitos exactos empezando por 6 o 9)
        - CIFs (letra + 8 dígitos)
        - Fechas (DD/MM/YYYY o similares)
        - Números de cliente (empiezan por 4 y tienen 9 dígitos)
        - Palabras sueltas sin dígitos suficientes
        
        Args:
            ref: Referencia a validar
            
        Returns:
            True si parece una referencia válida, False si es falso positivo
        """
        if not ref:
            return False
        
        # Limpiar espacios para validación
        ref_limpia = ref.replace(' ', '').replace('-', '').replace('/', '')
        
        # Mínimo 3 caracteres
        if len(ref_limpia) < 3:
            return False
        
        # Debe tener al menos 2 dígitos
        digitos = len(re.findall(r'\d', ref_limpia))
        if digitos < 2:
            return False
        
        # === FILTROS DE EXCLUSIÓN ===
        
        # Teléfonos móviles españoles: 6XXXXXXXX o 7XXXXXXXX (9 dígitos)
        if re.match(r'^[67]\d{8}$', ref_limpia):
            return False
        
        # Teléfonos fijos españoles: 9XXXXXXXX (9 dígitos)
        if re.match(r'^9\d{8}$', ref_limpia):
            return False
        
        # CIF/NIF: Letra + 8 dígitos
        if re.match(r'^[A-Z]\d{8}$', ref_limpia, re.IGNORECASE):
            return False
        
        # Números de cliente típicos: empiezan por 4 y tienen 9 dígitos
        if re.match(r'^4\d{8}$', ref_limpia):
            return False
        
        # Fechas: DD/MM/YYYY, DD-MM-YYYY, DDMMYYYY
        if re.match(r'^\d{2}[/\-]?\d{2}[/\-]?\d{2,4}$', ref_limpia):
            return False
        
        # Palabras comunes que NO son referencias
        palabras_excluir = [
            'FECHA', 'CLIENTE', 'FACTURA', 'SIMPLIFICADA', 'DATOS',
            'TOTAL', 'BASE', 'IVA', 'IMPORTE', 'PEDIDO', 'ALBARAN',
            'PROVEEDOR', 'NIF', 'CIF', 'TELEFONO', 'FAX', 'EMAIL',
            'DIRECCION', 'CODIGO', 'POSTAL', 'PROVINCIA', 'POBLACION'
        ]
        if ref.upper() in palabras_excluir:
            return False
        
        # Solo letras (sin números) → probablemente palabra suelta
        if ref_limpia.isalpha():
            return False
        
        return True
    
    # === MÉTODOS DE UTILIDAD ===
    
    def _convertir_importe(self, importe_str: str) -> float:
        """
        Convierte un string de importe a float.
        
        Maneja formatos:
        - 1.234,56 (español)
        - 1,234.56 (americano)
        - 1234.56 (sin separador miles)
        
        Args:
            importe_str: String con el importe
            
        Returns:
            Importe como float
        """
        # Limpiar espacios
        importe_str = importe_str.strip()
        
        # Formato español: 1.234,56
        if ',' in importe_str and '.' in importe_str:
            # Determinar cuál es el decimal
            pos_coma = importe_str.rfind(',')
            pos_punto = importe_str.rfind('.')
            
            if pos_coma > pos_punto:
                # Formato español: punto = miles, coma = decimal
                importe_str = importe_str.replace('.', '').replace(',', '.')
            else:
                # Formato americano: coma = miles, punto = decimal
                importe_str = importe_str.replace(',', '')
        elif ',' in importe_str:
            # Solo coma: es decimal
            importe_str = importe_str.replace(',', '.')
        
        return float(importe_str)
    
    def _limpiar_texto(self, texto: str) -> str:
        """
        Limpia el texto extraído del PDF.
        
        Args:
            texto: Texto a limpiar
            
        Returns:
            Texto limpio
        """
        # Eliminar múltiples espacios
        texto = re.sub(r' +', ' ', texto)
        # Eliminar múltiples saltos de línea
        texto = re.sub(r'\n+', '\n', texto)
        return texto.strip()
    
    def _calcular_base_desde_total(self, total: float, iva: int) -> float:
        """
        Calcula la base imponible a partir del total con IVA.
        
        Args:
            total: Total con IVA incluido
            iva: Porcentaje de IVA (4, 10, 21)
            
        Returns:
            Base imponible (sin IVA)
        """
        return round(total / (1 + iva / 100), 2)
    
    def _calcular_total_desde_base(self, base: float, iva: int) -> float:
        """
        Calcula el total con IVA a partir de la base.
        
        Args:
            base: Base imponible (sin IVA)
            iva: Porcentaje de IVA (4, 10, 21)
            
        Returns:
            Total con IVA incluido
        """
        return round(base * (1 + iva / 100), 2)


# Función auxiliar para el decorador registrar (importada desde __init__)
def registrar(*nombres_proveedor):
    """
    Decorador para registrar extractores.
    
    Este es un placeholder - la función real está en extractores/__init__.py
    Se reimporta aquí para conveniencia.
    """
    from extractores import registrar as _registrar
    return _registrar(*nombres_proveedor)
