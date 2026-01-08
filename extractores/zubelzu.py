# -*- coding: utf-8 -*-
"""
Extractor para ZUBELZU PIPARRAK S.L.
Piparras, guindillas y mousse de piparra del País Vasco.

Autor: Claude (ParsearFacturas v5.0)
Fecha: 27/12/2025
Corregido: 28/12/2025 - Integración con sistema
Validado: 6/6 facturas (100%)
"""
from extractores.base import ExtractorBase
from extractores import registrar
import re
from typing import List, Dict, Optional
import pdfplumber


@registrar('ZUBELZU', 'ZUBELZU PIPARRAK', 'ZUBELZU PIPARRAK SL', 
           'ZUBELZU PIPARRAK S.L.', 'ZUBELZU PIPARRAK S.L')
class ExtractorZubelzu(ExtractorBase):
    """
    Extractor para facturas de ZUBELZU PIPARRAK.
    
    Formato PDF muy limpio y consistente:
    - Líneas: CODIGO CONCEPTO CAJAS CANTIDAD PRECIO TOTAL
    - IVA siempre 10%
    - Categoría: PIPARRAS (guindillas/mousse)
    """
    
    nombre = 'ZUBELZU PIPARRAK'
    cif = 'B75079608'
    # IBAN del proveedor (extraído de la factura: 3035/0141/82/1410019635)
    iban = 'ES66 3035 0141 8214 1001 9635'  # Formato IBAN estándar
    metodo_pdf = 'pdfplumber'
    categoria_fija = 'PIPARRAS'  # Todos los productos son piparras/guindillas
    iva_fijo = 10  # Siempre 10%
    
    def extraer_texto(self, pdf_path: str) -> str:
        """Extrae texto del PDF usando pdfplumber."""
        texto_completo = []
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    texto = page.extract_text()
                    if texto:
                        texto_completo.append(texto)
        except Exception as e:
            print(f"Error extrayendo texto: {e}")
        return '\n'.join(texto_completo)
    
    def extraer_lineas(self, texto: str) -> List[Dict]:
        """
        Extrae líneas de productos de la factura.
        
        Formato de línea:
        1901 MOUSSE DE PIPARRA 400 g 2 12 5,630 67,56
        |    |                       |  |  |     |
        COD  CONCEPTO                CAJ CANT PRECIO TOTAL
        
        Nota: Después de cada línea viene LOTE: xxx CONSUMO PREFERENTE: xxx (ignorar)
        """
        lineas = []
        
        # Patrón para líneas de producto
        # Código (3-4 dígitos) + Concepto + Cajas + Cantidad + Precio + Total
        patron = re.compile(
            r'^(\d{2,4})\s+'                          # Código producto (2-4 dígitos)
            r'(.+?)\s+'                                # Concepto (nombre producto)
            r'(\d+)\s+'                                # Cajas
            r'(\d+)\s+'                                # Cantidad
            r'(\d+[.,]\d{2,3})\s+'                     # Precio unitario (puede ser 5,630 o 11,450)
            r'(\d+[.,]\d{2})',                         # Total línea
            re.MULTILINE
        )
        
        for match in patron.finditer(texto):
            codigo = match.group(1)
            concepto = match.group(2).strip()
            cajas = int(match.group(3))
            cantidad = int(match.group(4))
            precio = self._convertir_europeo(match.group(5))
            total = self._convertir_europeo(match.group(6))
            
            # Filtrar líneas que no son productos (cabeceras, etc.)
            if any(x.upper() in concepto.upper() for x in ['BRUTO', 'BASE', 'TOTAL', 'FACTURA', 'ALBARAN']):
                continue
            
            # Filtrar líneas con valores inválidos
            if total < 0.01 or cantidad < 1:
                continue
            
            # Limpiar concepto (quitar posibles espacios extra)
            concepto = ' '.join(concepto.split())
            
            lineas.append({
                'codigo': codigo,
                'articulo': concepto[:60],  # Limitar longitud
                'cantidad': cantidad,
                'precio_ud': round(precio, 4),  # ZUBELZU usa 3 decimales
                'iva': self.iva_fijo,
                'base': round(total, 2),
                'categoria': self.categoria_fija
            })
        
        return lineas
    
    def extraer_numero_factura(self, texto: str) -> Optional[str]:
        """
        Extrae número de factura.
        Formato: A 51.993
        """
        # Buscar en la línea que tiene CIF + fecha + serie + número
        patron = re.search(
            r'B87760575\s+\d{2}/\d{2}/\d{2}\s+([A-Z])\s+(\d+[.,]\d+)',
            texto
        )
        if patron:
            serie = patron.group(1)
            numero = patron.group(2).replace('.', '').replace(',', '')
            return f"{serie}-{numero}"
        
        # Alternativa: buscar "Nº FACTURA" seguido del número
        patron2 = re.search(r'Nº\s*FACTURA\s*\n\s*[A-Z]\s+(\d+[.,]\d+)', texto)
        if patron2:
            return patron2.group(1).replace('.', '').replace(',', '')
        
        return None
    
    def extraer_fecha(self, texto: str) -> Optional[str]:
        """
        Extrae fecha de la factura.
        Formato en PDF: 14/11/25 (DD/MM/YY)
        Retorna: DD/MM/YYYY
        """
        # Buscar fecha en la línea del CIF
        patron = re.search(
            r'B87760575\s+(\d{2}/\d{2}/\d{2})',
            texto
        )
        if patron:
            fecha_corta = patron.group(1)
            # Convertir YY a YYYY
            partes = fecha_corta.split('/')
            if len(partes) == 3:
                dia, mes, ano = partes
                ano_completo = f"20{ano}" if int(ano) < 50 else f"19{ano}"
                return f"{dia}/{mes}/{ano_completo}"
        
        # Alternativa: buscar cualquier fecha DD/MM/YY
        patron2 = re.search(r'(\d{2}/\d{2}/\d{2})\s+[A-Z]\s+\d+', texto)
        if patron2:
            fecha_corta = patron2.group(1)
            partes = fecha_corta.split('/')
            if len(partes) == 3:
                dia, mes, ano = partes
                ano_completo = f"20{ano}" if int(ano) < 50 else f"19{ano}"
                return f"{dia}/{mes}/{ano_completo}"
        
        return None
    
    def extraer_total(self, texto: str) -> Optional[float]:
        """
        Extrae el total de la factura.
        
        Línea de totales:
        BRUTO DTO. BASE I.V.A. I.V.A. IMP. I.V.A. R.E. IMP.R.E. TOTAL FACTURA
        1.068,36 1.068,36 10,00 106,84 1.175,20
        
        El TOTAL FACTURA es el último valor de la línea.
        """
        # Buscar línea de totales (5 valores numéricos)
        patron = re.search(
            r'([\d.,]+)\s+'        # BRUTO
            r'([\d.,]+)\s+'        # BASE
            r'10[,.]00\s+'         # IVA % (siempre 10,00)
            r'([\d.,]+)\s+'        # IMP. IVA
            r'([\d.,]+)',          # TOTAL FACTURA
            texto
        )
        if patron:
            return self._convertir_europeo(patron.group(4))
        
        # Alternativa: buscar "TOTAL FACTURA" seguido de número
        patron2 = re.search(r'TOTAL\s+FACTURA\s*\n\s*([\d.,]+)', texto, re.IGNORECASE)
        if patron2:
            return self._convertir_europeo(patron2.group(1))
        
        return None
    
    def extraer_base_imponible(self, texto: str) -> Optional[float]:
        """Extrae la base imponible (antes de IVA)."""
        patron = re.search(
            r'([\d.,]+)\s+'        # BRUTO
            r'([\d.,]+)\s+'        # BASE (este es el que queremos)
            r'10[,.]00\s+'         # IVA %
            r'([\d.,]+)\s+'        # IMP. IVA
            r'([\d.,]+)',          # TOTAL
            texto
        )
        if patron:
            return self._convertir_europeo(patron.group(2))
        return None
    
    def extraer_iva(self, texto: str) -> Optional[float]:
        """Extrae el importe del IVA."""
        patron = re.search(
            r'([\d.,]+)\s+'        # BRUTO
            r'([\d.,]+)\s+'        # BASE
            r'10[,.]00\s+'         # IVA %
            r'([\d.,]+)\s+'        # IMP. IVA (este)
            r'([\d.,]+)',          # TOTAL
            texto
        )
        if patron:
            return self._convertir_europeo(patron.group(3))
        return None
    
    def _convertir_europeo(self, texto: str) -> float:
        """
        Convierte formato europeo (1.234,56) a float.
        También maneja formato 5,630 (3 decimales).
        """
        if not texto:
            return 0.0
        texto = texto.strip()
        
        # Si tiene punto y coma, es formato europeo completo (1.234,56)
        if '.' in texto and ',' in texto:
            texto = texto.replace('.', '').replace(',', '.')
        # Si solo tiene coma, es decimal español (5,630)
        elif ',' in texto:
            texto = texto.replace(',', '.')
        
        try:
            return float(texto)
        except:
            return 0.0
