# -*- coding: utf-8 -*-
"""
Extractor para PAGO DE LAS OLMAS (OLMEDO CASADO S.C.)

Quesos y lácteos de oveja artesanales.
NIF: J47556360
IBAN: ES66 3058 5010 0627 2000 7736
Dirección: C/Carretera Ventas, 12 - 47131 Geria, Valladolid

Productos:
- Quesos (semicurado, curado, viejo) → IVA 4%, categoría QUESOS
- Yogur natural de oveja → IVA 4%, categoría DESPENSA
- Yogur con mermelada, cuajada, arroz con leche, mantequilla → IVA 10%, categoría DESPENSA

IMPORTANTE - PORTES Y CAJAS:
- Los "Gastos de envío" y "caja cartón" van al 21% en la factura
- PERO se prorratean proporcionalmente entre los productos
- El coste CON IVA (base * 1.21) se reparte entre las bases de los productos
- Así el coste de transporte queda incluido en cada producto

Formato factura:
CANTIDAD CONCEPTO PRECIO IMPORTE
4,430 Kg de queso semicurado de oveja 12,60 € 55,82 €

Creado: 06/01/2026
"""
from extractores.base import ExtractorBase
from extractores import registrar
from typing import List, Dict, Optional
import re


@registrar('PAGO DE LAS OLMAS', 'OLMEDO CASADO', 'LAS OLMAS')
class ExtractorPagoLasOlmas(ExtractorBase):
    """Extractor para facturas de PAGO DE LAS OLMAS."""
    
    nombre = 'PAGO DE LAS OLMAS'
    cif = 'J47556360'
    iban = 'ES66 3058 5010 0627 2000 7736'
    metodo_pdf = 'pdfplumber'
    
    # Mapeo de productos a IVA y categoría
    PRODUCTOS_IVA = {
        'queso semicurado': (4, 'QUESOS'),
        'queso curado': (4, 'QUESOS'),
        'queso viejo': (4, 'QUESOS'),
        'yogur natural': (4, 'DESPENSA'),
        'yogur de oveja con mermelada': (10, 'DESPENSA'),
        'yogur con mermelada': (10, 'DESPENSA'),
        'cuajada': (10, 'DESPENSA'),
        'arroz con leche': (10, 'DESPENSA'),
        'mantequilla': (10, 'DESPENSA'),
    }
    
    def _convertir_europeo(self, texto: str) -> float:
        """Convierte formato europeo a float."""
        if not texto:
            return 0.0
        texto = str(texto).strip().replace('€', '').replace(' ', '')
        if texto == '-' or texto == '':
            return 0.0
        if '.' in texto and ',' in texto:
            texto = texto.replace('.', '').replace(',', '.')
        elif ',' in texto:
            texto = texto.replace(',', '.')
        try:
            return float(texto)
        except:
            return 0.0
    
    def _determinar_iva_categoria(self, descripcion: str) -> tuple:
        """Determina IVA y categoría según el producto."""
        desc_lower = descripcion.lower()
        for key, (iva, cat) in self.PRODUCTOS_IVA.items():
            if key in desc_lower:
                return iva, cat
        # Default para productos no mapeados
        return 10, 'DESPENSA'
    
    def _extraer_portes_cajas(self, texto: str) -> float:
        """
        Extrae gastos de envío y caja cartón.
        Devuelve el importe CON IVA (base * 1.21) para prorratear.
        """
        total_base_21 = 0.0
        
        # Buscar caja cartón
        match = re.search(r'[\d,]+\s+caja\s+cart[oó]n\s+[\d,]+\s*€\s+([\d,]+)\s*€', texto, re.IGNORECASE)
        if match:
            total_base_21 += self._convertir_europeo(match.group(1))
        
        # Buscar gastos de envío
        match = re.search(r'[\d,]+\s+Gastos\s+de\s+env[ií]o\s+[\d,]+\s*€\s+([\d,]+)\s*€', texto, re.IGNORECASE)
        if match:
            total_base_21 += self._convertir_europeo(match.group(1))
        
        # Devolver el coste CON IVA para prorratear
        return round(total_base_21 * 1.21, 2)
    
    def extraer_lineas(self, texto: str) -> List[Dict]:
        """
        Extrae líneas de productos.
        
        Los portes (gastos envío + caja cartón) se prorratean:
        - Se calcula el coste CON IVA de los portes (base * 1.21)
        - Se reparte proporcionalmente entre los productos
        - Se suma a la base de cada producto
        """
        lineas = []
        
        # Patrón para productos lácteos (contienen "de oveja" o "de leche")
        patron = re.compile(
            r'^([\d,]+)\s+'                    # Cantidad
            r'([A-Za-záéíóúñÑ\s]+(?:de oveja|de leche)[A-Za-záéíóúñÑ\s]*)\s+'  # Descripción
            r'([\d,]+)\s*€\s+'                 # Precio
            r'([\d,]+)\s*€'                    # Importe
        , re.MULTILINE | re.IGNORECASE)
        
        for match in patron.finditer(texto):
            cantidad = self._convertir_europeo(match.group(1))
            descripcion = match.group(2).strip()
            precio = self._convertir_europeo(match.group(3))
            importe = self._convertir_europeo(match.group(4))
            
            # Saltar líneas sin importe
            if importe <= 0:
                continue
                
            iva, categoria = self._determinar_iva_categoria(descripcion)
            
            lineas.append({
                'codigo': descripcion[:3].upper(),
                'articulo': descripcion[:50],
                'cantidad': round(cantidad, 2) if cantidad != int(cantidad) else int(cantidad),
                'precio_ud': round(precio, 2),
                'base': round(importe, 2),
                'iva': iva,
                'categoria': categoria
            })
        
        # Extraer portes y cajas CON IVA para prorratear
        portes_con_iva = self._extraer_portes_cajas(texto)
        
        # Prorratear portes entre los productos
        if portes_con_iva > 0 and lineas:
            total_productos = sum(l['base'] for l in lineas)
            if total_productos > 0:
                for linea in lineas:
                    proporcion = linea['base'] / total_productos
                    extra = portes_con_iva * proporcion
                    linea['base'] = round(linea['base'] + extra, 2)
        
        return lineas
    
    def extraer_total(self, texto: str) -> Optional[float]:
        """Extrae total de la factura."""
        # El OCR a veces introduce espacios extraños: "1 60,90" en lugar de "160,90"
        match = re.search(r'T\.\s*FACTURA\s+([\d,.\s]+)€', texto, re.IGNORECASE)
        if match:
            valor = match.group(1).replace(' ', '')  # Quitar espacios
            return self._convertir_europeo(valor)
        return None
    
    def extraer_fecha(self, texto: str) -> Optional[str]:
        """Extrae fecha de la factura."""
        match = re.search(r'FECHA\s+(\d{2}/\d{2}/\d{2,4})', texto, re.IGNORECASE)
        if match:
            fecha = match.group(1)
            # Convertir DD/MM/YY a DD/MM/20YY si es necesario
            partes = fecha.split('/')
            if len(partes) == 3 and len(partes[2]) == 2:
                partes[2] = '20' + partes[2]
                fecha = '/'.join(partes)
            return fecha
        return None
    
    def extraer_numero_factura(self, texto: str) -> Optional[str]:
        """Extrae número de factura."""
        match = re.search(r'FACTURA\s+(\d+/\d+)', texto, re.IGNORECASE)
        if match:
            return match.group(1)
        return None
