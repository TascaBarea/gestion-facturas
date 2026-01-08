# -*- coding: utf-8 -*-
"""
Extractor para PABLO RUIZ HERRERA - LA DOLOROSA CASA DE FERMENTOS

Productos fermentados artesanales:
- Talleres/degustaciones de vermut
- Encurtidos fermentados (pepinillos, kimchi, escabeche)
- Fermentos varios

DNI: 32081620R (autónomo)
IBAN: ES27 0049 4680 8124 1609 2645

IVA: 21% (productos gourmet/servicios)

CATEGORÍAS:
- COSTE EXPERIENCIA: Talleres, degustaciones
- FERMENTOS: Productos fermentados (encurtidos, kimchi, etc.)

FORMATOS DE FACTURA:
1. TB-2025-01: Total línea INCLUYE IVA (detectar por "TOTAL BRUTO")
2. TB-2025-02+: Total línea es BASE (sin IVA)

Creado: 04/01/2026
Validado: 5/5 facturas (3T25-4T25)
"""
from extractores.base import ExtractorBase
from extractores import registrar
from typing import List, Dict, Optional
import re


@registrar('PABLO RUIZ', 'LA DOLOROSA', 'PABLO RUIZ LA DOLOROSA', 
           'PABLO RUIZ HERRERA', 'LA DOLOROSA CASA DE FERMENTOS')
class ExtractorPabloRuiz(ExtractorBase):
    """Extractor para facturas de PABLO RUIZ - LA DOLOROSA."""
    
    nombre = 'PABLO RUIZ LA DOLOROSA'
    cif = '32081620R'  # DNI (autónomo)
    iban = 'ES27 0049 4680 8124 1609 2645'
    metodo_pdf = 'pdfplumber'
    
    def _convertir_europeo(self, texto: str) -> float:
        """Convierte formato europeo a float."""
        if not texto:
            return 0.0
        texto = str(texto).strip().replace('€', '').strip()
        if '.' in texto and ',' in texto:
            texto = texto.replace('.', '').replace(',', '.')
        elif ',' in texto:
            texto = texto.replace(',', '.')
        try:
            return float(texto)
        except:
            return 0.0
    
    def _categorizar(self, descripcion: str) -> str:
        """
        Determina categoría según descripción.
        
        COSTE EXPERIENCIA: Talleres, degustaciones
        FERMENTOS: Todo lo demás
        """
        desc_lower = descripcion.lower()
        
        # Palabras clave para COSTE EXPERIENCIA
        # Incluye variantes con/sin tilde y typos comunes
        keywords_experiencia = [
            'taller', 
            'degustación', 'degustacion',
            'degustción',  # Typo común
        ]
        
        if any(kw in desc_lower for kw in keywords_experiencia):
            return 'COSTE EXPERIENCIA'
        
        return 'FERMENTOS'
    
    def extraer_lineas(self, texto: str) -> List[Dict]:
        """
        Extrae líneas de productos.
        
        Maneja dos formatos:
        1. DESC + UNIDADES + PRECIO € + TOTAL € (una línea)
        2. DESC + UNIDADES + TOTAL € (precio en otra línea)
        """
        lineas = []
        lineas_raw = texto.split('\n')
        
        # Detectar formato: si tiene 'TOTAL BRUTO', los totales de línea YA incluyen IVA
        formato_con_iva = 'TOTAL BRUTO' in texto
        
        i = 0
        while i < len(lineas_raw):
            line = lineas_raw[i].strip()
            i += 1
            
            if not line or '€' not in line:
                continue
            
            # Formato 1: DESC + UNIDADES + PRECIO € + TOTAL € (todo en una línea)
            m1 = re.match(
                r'^([A-Za-záéíóúñÁÉÍÓÚÑ][A-Za-záéíóúñÁÉÍÓÚÑ0-9\s/,\.\-]+?)\s+'
                r'(\d+)\s+'
                r'([\d,]+)\s*€\s+'
                r'([\d,]+)\s*€',
                line
            )
            
            if m1:
                descripcion = m1.group(1).strip()
                cantidad = int(m1.group(2))
                precio_ud = self._convertir_europeo(m1.group(3))
                total_linea = self._convertir_europeo(m1.group(4))
                
                # Filtrar cabeceras y líneas vacías
                if total_linea < 0.01:
                    continue
                if any(x in descripcion.upper() for x in ['DESCRIPCION', 'UNIDADES', 'PRECIO', 'UNITARIO', 'COMENTARIOS']):
                    continue
                
                # Si formato tiene IVA incluido, calcular base
                if formato_con_iva:
                    base = round(total_linea / 1.21, 2)
                else:
                    base = total_linea
                
                lineas.append({
                    'codigo': '',
                    'articulo': descripcion[:50],
                    'cantidad': cantidad,
                    'precio_ud': precio_ud,
                    'iva': 21,
                    'base': base,
                    'categoria': self._categorizar(descripcion)
                })
                continue
            
            # Formato 2: DESC + UNIDADES + TOTAL € (precio en otra línea)
            m2 = re.match(
                r'^([A-Za-záéíóúñÁÉÍÓÚÑ][A-Za-záéíóúñÁÉÍÓÚÑ0-9\s/,\.\-]+?)\s+'
                r'(\d+)\s+'
                r'([\d,]+)\s*€$',
                line
            )
            
            if m2:
                descripcion = m2.group(1).strip()
                cantidad = int(m2.group(2))
                total_linea = self._convertir_europeo(m2.group(3))
                
                # Buscar precio unitario en la siguiente línea
                precio_ud = 0.0
                if i < len(lineas_raw):
                    next_line = lineas_raw[i].strip()
                    m_precio = re.match(r'^([\d,]+)\s*€$', next_line)
                    if m_precio:
                        precio_ud = self._convertir_europeo(m_precio.group(1))
                        i += 1  # Saltar línea de precio
                
                # Filtrar cabeceras y líneas vacías
                if total_linea < 0.01:
                    continue
                if any(x in descripcion.upper() for x in ['DESCRIPCION', 'UNIDADES', 'PRECIO', 'UNITARIO', 'COMENTARIOS']):
                    continue
                
                lineas.append({
                    'codigo': '',
                    'articulo': descripcion[:50],
                    'cantidad': cantidad,
                    'precio_ud': precio_ud if precio_ud > 0 else round(total_linea / cantidad, 2),
                    'iva': 21,
                    'base': total_linea,  # En formato 2 siempre es base
                    'categoria': self._categorizar(descripcion)
                })
        
        return lineas
    
    def extraer_total(self, texto: str) -> Optional[float]:
        """
        Extrae total de la factura.
        
        El total es el mayor valor € en la factura.
        """
        matches = re.findall(r'([\d,.]+)\s*€', texto)
        if matches:
            valores = [self._convertir_europeo(v) for v in matches]
            return max(valores)
        return None
    
    def extraer_base_iva(self, texto: str) -> tuple:
        """Extrae base imponible e IVA."""
        total = self.extraer_total(texto)
        lineas = self.extraer_lineas(texto)
        
        if lineas:
            base = sum(l['base'] for l in lineas)
            iva = round(base * 0.21, 2)
            return base, iva
        
        # Fallback: calcular desde total
        if total:
            base = round(total / 1.21, 2)
            iva = round(total - base, 2)
            return base, iva
        
        return 0.0, 0.0
    
    def extraer_fecha(self, texto: str) -> Optional[str]:
        """Extrae fecha de factura."""
        patron = re.search(r'Fecha\s+de\s+factura:\s*(\d{2}/\d{2}/\d{4})', texto)
        if patron:
            return patron.group(1)
        return None
    
    def extraer_referencia(self, texto: str) -> Optional[str]:
        """
        Extrae número de factura.
        Formato: "Número de factura: TB-2025-03"
        """
        # Con acento
        patron = re.search(r'N[úu]mero\s+de\s+factura:\s*(TB-\d{4}-\d+)', texto, re.IGNORECASE)
        if patron:
            return patron.group(1)
        return None
    
    # Alias para compatibilidad
    extraer_numero_factura = extraer_referencia
