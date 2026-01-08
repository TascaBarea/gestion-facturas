# -*- coding: utf-8 -*-
"""
Extractor para BERZAL HERMANOS S.A.

Quesos, mantequillas y productos lácteos.
CIF: A78490182

Formato factura (pdfplumber):
CODIGO CONCEPTO CAJAS UNID KILOS PRECIO DTO PR.NETO UN/KG IVA IMPORTE
206017 Mantequilla "Cañada Real" dulce 120 grs 0,13 2 0,240 2,740 2,740 U 10 5,48
111456 Mousse de Oca con Hongos Rollo 1,5 kg 0,50 1 1,50012,250 10,0 11,025 K 10 16,54

NOTA: Las líneas con descuento (DTO) tienen formato diferente con números pegados.
La estrategia es buscar el patrón U/K IVA IMPORTE al final de cada línea.

IVA: 10% (lácteos)

VERSIÓN: v5.16 - 07/01/2026
- FIX: Patrón simplificado que busca U/K IVA IMPORTE al final
- FIX: Captura correctamente líneas con y sin descuento
- FIX: Nombre siempre 'BERZAL HERMANOS'

Creado: 19/12/2025
Actualizado: 07/01/2026
"""
from extractores.base import ExtractorBase
from extractores import registrar
from typing import List, Dict, Optional
import re


@registrar('BERZAL', 'BERZAL HERMANOS', 'QUESOS BERZAL', 'BERZAL HNOS')
class ExtractorBerzal(ExtractorBase):
    """Extractor para facturas de BERZAL HERMANOS."""
    
    nombre = 'BERZAL HERMANOS'  # Siempre nombre completo
    cif = 'A78490182'
    iban = 'ES20 0128 0025 9105 0000 1422'
    metodo_pdf = 'pdfplumber'
    
    def extraer_lineas(self, texto: str) -> List[Dict]:
        """
        Extrae líneas individuales de productos.
        
        Estrategia: buscar líneas que empiecen con código 6 dígitos
        y terminen con el patrón U/K IVA IMPORTE.
        """
        lineas = []
        
        # Patrón robusto: CODIGO ... U/K IVA IMPORTE al final de línea
        # Captura líneas con y sin descuento
        patron_linea = re.compile(
            r'^(\d{6})\s+'                    # Código (6 dígitos)
            r'(.+?)\s+'                        # Descripción (non-greedy)
            r'([UK])\s+'                       # Unidad (U o K)
            r'(\d{1,2})\s+'                    # IVA (1-2 dígitos: 4, 10, 21)
            r'(\d+,\d{2})$'                    # IMPORTE al final de línea
        , re.MULTILINE)
        
        for match in patron_linea.finditer(texto):
            codigo = match.group(1)
            descripcion = match.group(2).strip()
            unidad = match.group(3)
            iva = int(match.group(4))
            importe = self._convertir_europeo(match.group(5))
            
            # Limpiar descripción de números intermedios (cajas, kilos, precios)
            # Buscar hasta el primer grupo de números decimales
            desc_limpia = re.sub(r'\s+\d+[,\.]\d+.*$', '', descripcion)
            desc_limpia = re.sub(r'\s+', ' ', desc_limpia).strip()
            
            # Validar importe mínimo
            if importe < 0.50:
                continue
            
            # Calcular cantidad aproximada (para referencia)
            # En BERZAL el PR.NETO está justo antes de U/K
            # Intentar extraer del texto original
            cantidad = self._extraer_cantidad(descripcion, importe)
            precio_ud = round(importe / cantidad, 2) if cantidad > 0 else importe
            
            lineas.append({
                'codigo': codigo,
                'articulo': desc_limpia[:50],
                'cantidad': cantidad,
                'precio_ud': precio_ud,
                'iva': iva,
                'base': round(importe, 2)
            })
        
        # Si no encontró líneas, usar fallback de desglose fiscal
        if not lineas:
            lineas = self._extraer_desglose(texto)
        
        return lineas
    
    def _extraer_cantidad(self, descripcion: str, importe: float) -> int:
        """
        Intenta extraer la cantidad de unidades de la descripción.
        Busca el patrón: ... CAJAS UNID KILOS ...
        """
        # Buscar números enteros en la descripción
        # El segundo número suele ser UNID
        numeros = re.findall(r'\b(\d+)\b', descripcion)
        
        if len(numeros) >= 2:
            try:
                # El segundo número suele ser unidades
                cantidad = int(numeros[1])
                if 1 <= cantidad <= 100:
                    return cantidad
            except:
                pass
        
        # Fallback: estimar desde precio típico
        # Mantequillas ~3€, Paté ~2.50€
        if importe > 20:
            return max(1, int(importe / 3))
        elif importe > 10:
            return max(1, int(importe / 2.5))
        else:
            return max(1, int(importe / 3))
    
    def _extraer_desglose(self, texto: str) -> List[Dict]:
        """Extrae usando desglose fiscal como fallback."""
        lineas = []
        
        # Buscar: BASE_IMPONIBLE IVA% en el cuadro fiscal
        # Formato: 73,49 10 73,49 10 7,35
        patron = re.compile(
            r'(\d+,\d{2})\s+(\d{1,2})\s+\d+,\d{2}\s+\d{1,2}\s+(\d+,\d{2})',
            re.MULTILINE
        )
        
        for match in patron.finditer(texto):
            base = self._convertir_europeo(match.group(1))
            iva = int(match.group(2))
            cuota = self._convertir_europeo(match.group(3))
            
            # Validar que es un IVA válido y la cuota cuadra
            if iva in [4, 10] and base > 5:
                cuota_esperada = round(base * iva / 100, 2)
                if abs(cuota - cuota_esperada) < 1.0:
                    lineas.append({
                        'codigo': '',
                        'articulo': f'LACTEOS BERZAL IVA {iva}%',
                        'cantidad': 1,
                        'precio_ud': round(base, 2),
                        'iva': iva,
                        'base': round(base, 2)
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
        """Extrae el total de la factura."""
        # Buscar TOTAL IMPORTE XX,XX (formato más común en BERZAL)
        patron = re.search(
            r'TOTAL\s+IMPORTE\s+(\d+,\d{2})',
            texto, re.IGNORECASE
        )
        if patron:
            return self._convertir_europeo(patron.group(1))
        
        # Alternativa: TOTAL FACTURA
        patron2 = re.search(
            r'TOTAL\s+FACTURA\s+(\d+,\d{2})',
            texto, re.IGNORECASE
        )
        if patron2:
            return self._convertir_europeo(patron2.group(1))
        
        return None
    
    def extraer_fecha(self, texto: str) -> Optional[str]:
        """Extrae la fecha de la factura."""
        # Formato: DD/MM/YY en cabecera
        patron = re.search(r'(\d{2}/\d{2}/\d{2})\s+\d+', texto)
        if patron:
            fecha = patron.group(1)
            # Convertir YY a YYYY
            partes = fecha.split('/')
            if len(partes) == 3 and len(partes[2]) == 2:
                año = '20' + partes[2]
                return f'{partes[0]}/{partes[1]}/{año}'
            return fecha
        return None
    
    def extraer_numero_factura(self, texto: str) -> Optional[str]:
        """Extrae el número de factura."""
        # Buscar FACTURA seguido de número
        patron = re.search(r'FACTURA[^\d]*(\d+)', texto, re.IGNORECASE)
        if patron:
            return patron.group(1)
        return None
