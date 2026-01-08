"""
Extractor para PORVAZ VILAGARCIA S.L.

Conservas gallegas de Vilagarcia de Arousa (Pontevedra)
CIF: B36281087
IBAN: REDACTED_IBAN

Formato factura (pdfplumber):
- Lineas producto: DESCRIPCION CANTIDAD PRECIO IVA IMPORTE
- IVA: 10% (conservas alimenticias)

CATEGORIA FIJA: CONSERVAS PESCADO

Variantes nombre: PORVAZ, PORVAZ TITO, PORVAZ VILLAGARCIA, CONSERVAS TITO

Creado: 19/12/2025
Actualizado: 30/12/2025 - Corregido patron para incluir Ñ (ZAMBURIÑA)
"""
from extractores.base import ExtractorBase
from extractores import registrar
from typing import List, Dict, Optional
import re


@registrar('PORVAZ', 'PORVAZ TITO', 'PORVAZ VILLAGARCIA', 'PORVAZ VILAGARCIA', 
           'PORVAZ VILLAG', 'CONSERVAS TITO', 'TITO CONSERVAS', 'LA RIVIERE')
class ExtractorPorvaz(ExtractorBase):
    """Extractor para facturas de PORVAZ VILAGARCIA S.L."""
    
    nombre = 'PORVAZ'
    cif = 'B36281087'
    iban = 'REDACTED_IBAN'
    metodo_pdf = 'pdfplumber'
    categoria = 'CONSERVAS PESCADO'  # CATEGORIA FIJA
    
    def extraer_lineas(self, texto: str) -> List[Dict]:
        """
        Extrae lineas INDIVIDUALES de productos.
        
        Formato:
        DESCRIPCION CANTIDAD PRECIO IVA IMPORTE
        BERBERECHO ENLATADO 40/60 RR120 AL 10 4,500 10,0 45,00
        ZAMBURIÑA SALSA DE VIEIRA 10 3,050 10,0 30,50
        
        NOTA: El patron incluye Ñ y acentos para capturar productos como ZAMBURIÑA
        """
        lineas = []
        
        # Patron corregido: incluye Ñ y acentos en la descripcion
        patron_linea = re.compile(
            r'^([A-ZÁÉÍÓÚÑ0-9/\s]+?)\s+'       # Descripcion con acentos y Ñ
            r'(\d+)\s+'                         # Cantidad (entero)
            r'(\d+,\d{3})\s+'                   # Precio (X,XXX)
            r'(\d+,\d)\s+'                      # IVA (10,0)
            r'(\d+,\d{2})\s*$'                  # Importe
        , re.MULTILINE)
        
        for match in patron_linea.finditer(texto):
            descripcion = match.group(1).strip()
            cantidad = int(match.group(2))
            precio = self._convertir_europeo(match.group(3))
            iva = int(float(self._convertir_europeo(match.group(4))))
            importe = self._convertir_europeo(match.group(5))
            
            # Filtrar cabeceras y lineas no validas
            if any(x in descripcion.upper() for x in ['DESCRIPCION', 'CANTIDAD', 'PRECIO', 
                                                       'IMPORTE', 'CLIENTE', 'FACTURA']):
                continue
            
            # Validar que el importe sea razonable
            if importe < 1.0:
                continue
            
            lineas.append({
                'codigo': '',  # PORVAZ no usa codigos
                'articulo': descripcion[:50],
                'cantidad': cantidad,
                'precio_ud': round(precio, 3),
                'iva': iva,
                'base': round(importe, 2),
                'categoria': self.categoria  # Asignar categoria fija
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
        # Buscar "Total Factura:" seguido del importe
        patron = re.search(
            r'Total\s+Factura:\s*(\d+,\d{2})',
            texto, re.IGNORECASE
        )
        if patron:
            return self._convertir_europeo(patron.group(1))
        return None
    
    def extraer_fecha(self, texto: str) -> Optional[str]:
        """Extrae fecha de la factura."""
        # Formato: Fecha: 14-04-2025
        patron = re.search(r'Fecha:\s*(\d{2}-\d{2}-\d{4})', texto)
        if patron:
            # Convertir de DD-MM-YYYY a DD/MM/YYYY
            fecha = patron.group(1).replace('-', '/')
            return fecha
        return None
    
    def extraer_numero_factura(self, texto: str) -> Optional[str]:
        """Extrae numero de factura."""
        # Formato: Numero: 0132/25
        patron = re.search(r'N[uú]mero:\s*(\d+/\d+)', texto)
        if patron:
            return patron.group(1)
        return None
    
    extraer_referencia = extraer_numero_factura
