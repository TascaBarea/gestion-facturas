# -*- coding: utf-8 -*-
"""
Extractor para LA BARRA DULCE S.L.

Pastelería y bollería artesanal.

CIF: B19981141
IBAN: REDACTED_IBAN
IVA: 10% (pastelería)

Productos típicos:
- Palmeritas / Mini palmeritas / Minipalmeritas
- Buñuelos
- Fresas con chocolate
- Rosquillas San Isidro
- Desayunos (con fecha: "Desayuno 21/11", "Desayuno 12 de septiembre")

Formato líneas:
DESCRIPCION UNIDADES PRECIO IMPORTE
Minipalmeritas 1 29,28 29,28
Desayuno 21/11 1 11,23 11,23

Creado: 19/12/2025
Actualizado: 06/01/2026 - Categoría cambiada a DULCES
Validado: 8/8 facturas (1T25-4T25)
"""
from extractores.base import ExtractorBase
from extractores import registrar
from typing import List, Dict, Optional
import re


@registrar('LA BARRA DULCE', 'BARRA DULCE', 'LA BARRA DULCE S.L.')
class ExtractorBarraDulce(ExtractorBase):
    """Extractor para facturas de LA BARRA DULCE."""
    
    nombre = 'LA BARRA DULCE'
    cif = 'B19981141'
    iban = 'REDACTED_IBAN'
    metodo_pdf = 'pdfplumber'
    categoria_fija = 'DULCES'  # Cambiado de PASTELERIA a DULCES
    
    def _convertir_europeo(self, texto: str) -> float:
        """Convierte formato europeo (1.234,56) a float."""
        if not texto:
            return 0.0
        texto = texto.strip().replace('.', '').replace(',', '.')
        try:
            return float(texto)
        except:
            return 0.0
    
    def extraer_lineas(self, texto: str) -> List[Dict]:
        """
        Extrae líneas de productos.
        
        Formato:
        DESCRIPCION UNIDADES PRECIO IMPORTE
        Minipalmeritas 1 29,28 29,28
        Desayuno 21/11 1 11,23 11,23
        """
        lineas = []
        
        for linea_texto in texto.split('\n'):
            linea_texto = linea_texto.strip()
            if not linea_texto or len(linea_texto) < 5:
                continue
            
            # Ignorar cabeceras y líneas no deseadas
            upper = linea_texto.upper()
            if any(x in upper for x in [
                'DESCRIPCION', 'UNIDADES', 'PRECIO UNITARIO', 'BASE', 'IVA',
                'TOTAL', 'FACTURA', 'CLIENTE', 'CIF:', 'CALLE', 'TELEFONO',
                'OBSERVACIONES', 'PROTECCION', 'DATOS', 'CAIXA', 'TRANSFERENCIA',
                'BARRA DULCE', 'MESON', 'MADRID', 'FORMA DE PAGO', 'INFORMACION',
                'TASCA BAREA', 'RODAS', 'TARJETA', 'BANCARIA', 'IMPUESTOS',
                'COMERCIAL', 'RELACION', 'DERECHOS', 'DIRECCION'
            ]):
                continue
            
            # Patrón: acepta números y / en descripción
            # Ej: "Desayuno 21/11 1 11,23 11,23"
            match = re.match(
                r'^([A-Za-zñáéíóúÑÁÉÍÓÚ][A-Za-zñáéíóúÑÁÉÍÓÚ\s\d/]+?)\s+'
                r'(\d{1,3})\s+'
                r'(\d+,\d{2})\s+'
                r'(\d+,\d{2})$',
                linea_texto
            )
            
            if match:
                descripcion = match.group(1).strip()
                cantidad = int(match.group(2))
                precio = self._convertir_europeo(match.group(3))
                importe = self._convertir_europeo(match.group(4))
                
                # Validaciones
                if importe < 0.50 or len(descripcion) < 3:
                    continue
                
                # Evitar capturar líneas solo numéricas
                if descripcion.replace(' ', '').replace('/', '').isdigit():
                    continue
                
                lineas.append({
                    'codigo': '',
                    'articulo': descripcion[:50],
                    'cantidad': cantidad,
                    'precio_ud': round(precio, 2),
                    'iva': 10,  # Pastelería siempre 10%
                    'base': round(importe, 2),
                    'categoria': self.categoria_fija
                })
        
        return lineas
    
    def extraer_total(self, texto: str) -> Optional[float]:
        """Extrae total de la factura."""
        # Formato: TOTAL FACTURA 32,20€
        patron = re.search(r'TOTAL\s+FACTURA\s+(\d+,\d{2})\s*€', texto, re.IGNORECASE)
        if patron:
            return self._convertir_europeo(patron.group(1))
        return None
    
    def extraer_cuadro_fiscal(self, texto: str) -> List[Dict]:
        """Extrae cuadro fiscal (IVA 10%)."""
        cuadros = []
        
        # Buscar Base Imponible y Total impuestos
        base = re.search(r'Base\s+Imponible\s+(\d+,\d{2})', texto, re.IGNORECASE)
        cuota = re.search(r'Total\s+impuestos\s+(\d+,\d{2})', texto, re.IGNORECASE)
        
        if base and cuota:
            cuadros.append({
                'iva': 10,
                'base': self._convertir_europeo(base.group(1)),
                'cuota': self._convertir_europeo(cuota.group(1))
            })
        
        return cuadros
    
    def extraer_fecha(self, texto: str) -> Optional[str]:
        """Extrae fecha de la factura."""
        # Formato: CIF: B19981141 31.01.2025
        patron = re.search(r'CIF:\s*B\d+\s+(\d{2})\.(\d{2})\.(\d{4})', texto)
        if patron:
            return f"{patron.group(1)}/{patron.group(2)}/{patron.group(3)}"
        
        # Alternativo: DD.MM.YYYY
        patron2 = re.search(r'(\d{2})\.(\d{2})\.(\d{4})', texto)
        if patron2:
            return f"{patron2.group(1)}/{patron2.group(2)}/{patron2.group(3)}"
        
        return None
    
    def extraer_numero_factura(self, texto: str) -> Optional[str]:
        """Extrae número de factura."""
        # Buscar "Nº de factura" seguido de número
        patron = re.search(r'Nº\s+de\s+factura\s*\n?\s*(\d+)', texto, re.IGNORECASE)
        if patron:
            return patron.group(1)
        return None
