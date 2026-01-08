# -*- coding: utf-8 -*-
"""
Extractor para MARITA COSTA VILELA

Distribuidora de productos gourmet
NIF: REDACTED_DNI (autónoma)
Ubicación: Valdemoro, Madrid
Tel: 665 14 06 10

IBAN: ES78 2100 6398 7002 0001 9653

Productos típicos:
- AOVE Nobleza del Sur (4% IVA)
- Lucía Picos de Jamón (4% IVA desde ~junio 2025, antes 10%)
- Patés Lucas (10% IVA)
- Cookies Milola (10% IVA)
- Torreznos La Rústica (10% IVA)
- Patatas Quillo (10% IVA)

IMPORTANTE v5.12:
- Los importes en factura son BASE (sin IVA)
- El IVA se determina del DESGLOSE de la propia factura
- La categoría se obtiene del diccionario
- Maneja líneas multilínea (producto partido en dos líneas)

Número factura: Formato "1-XXXXXX" (prefijo-número 6 dígitos)
Ejemplo: 1-250563

Creado: 20/12/2025
Actualizado: 06/01/2026 - IVA del desglose, categoría del diccionario
Actualizado: 07/01/2026 - Corregido extraer_numero_factura() formato 1-XXXXXX
"""
from extractores.base import ExtractorBase
from extractores import registrar
from typing import List, Dict, Optional
import re
import pdfplumber


@registrar('MARITA COSTA', 'MARITA', 'COSTA VILELA', 'MARITA COSTA VILELA')
class ExtractorMaritaCosta(ExtractorBase):
    """Extractor para facturas de MARITA COSTA VILELA."""
    
    nombre = 'MARITA'
    cif = 'REDACTED_DNI'
    iban = 'ES78 2100 6398 7002 0001 9653'
    metodo_pdf = 'pdfplumber'
    # NO usar categoria_fija - se obtiene del diccionario
    
    def _convertir_europeo(self, texto: str) -> float:
        """Convierte formato europeo (1.234,56) a float."""
        if not texto:
            return 0.0
        texto = str(texto).strip()
        texto = texto.replace('\u20ac', '').replace('€', '')
        texto = texto.replace('EUR', '').replace('eur', '')
        texto = texto.replace(' ', '').strip()
        
        if '.' in texto and ',' in texto:
            texto = texto.replace('.', '').replace(',', '.')
        elif ',' in texto:
            texto = texto.replace(',', '.')
        try:
            return float(texto)
        except:
            return 0.0
    
    def extraer_texto(self, pdf_path: str) -> str:
        """Extrae texto del PDF."""
        try:
            with pdfplumber.open(pdf_path) as pdf:
                texto = pdf.pages[0].extract_text()
                return texto or ''
        except:
            return ''
    
    def extraer_numero_factura(self, texto: str) -> Optional[str]:
        """
        Extrae número de factura.
        
        Formato en cabecera: MADRID Factura 1 250563 1 30/04/2025
        El número es "1-250563" (prefijo-número de 6 dígitos)
        """
        # Buscar patrón: Factura PREFIJO NUMERO PAGINA FECHA
        patron = re.search(
            r'Factura\s+(\d+)\s+(\d{6})\s+\d+\s+\d{2}/\d{2}/\d{4}',
            texto
        )
        if patron:
            prefijo = patron.group(1)
            numero = patron.group(2)
            return f"{prefijo}-{numero}"
        
        # Alternativa: buscar solo "Factura 1 XXXXXX"
        patron2 = re.search(r'Factura\s+(\d+)\s+(\d{6})', texto, re.IGNORECASE)
        if patron2:
            return f"{patron2.group(1)}-{patron2.group(2)}"
        
        return None
    
    def extraer_desglose_iva(self, texto: str) -> Dict[int, float]:
        """
        Extrae desglose de IVA del cuadro fiscal.
        
        Formato en factura:
        TIPO BASE I.V.A R.E. ...
        21,00
        10,00 79,90 7,99
        4,00 326,10 13,04
        2,00 238,38 4,77  (IVA reducido 2024)
        
        Returns:
            Dict con {tipo_iva: base} ej: {10: 79.90, 4: 326.10}
        """
        desglose = {}
        
        # Buscar líneas con formato: TIPO BASE IVA
        # Ej: "10,00 79,90 7,99" o "4,00 326,10 13,04" o "2,00 238,38 4,77"
        patron = re.compile(
            r'^(\d{1,2})[,.]00\s+'      # Tipo IVA (2, 4, 10, 21)
            r'([\d.,]+)\s+'              # Base
            r'([\d.,]+)\s*$',            # Cuota IVA
            re.MULTILINE
        )
        
        for match in patron.finditer(texto):
            tipo = int(match.group(1))
            base = self._convertir_europeo(match.group(2))
            if base > 0 and tipo in [2, 4, 10, 21]:  # Incluye IVA 2%
                desglose[tipo] = base
        
        return desglose
    
    def _es_candidato_iva_reducido(self, articulo: str) -> bool:
        """
        Identifica productos que podrían ir a IVA reducido (2% o 4%).
        """
        art = articulo.upper()
        return 'AOVE' in art or 'LUCÍA PICOS' in art or 'LUCIA PICOS' in art
    
    def _asignar_iva_por_desglose(self, lineas: List[Dict], desglose: Dict[int, float]) -> List[Dict]:
        """
        Asigna IVA a las líneas buscando la combinación que cuadre con el desglose.
        
        Usa combinatoria para encontrar qué productos van a IVA reducido (2% o 4%)
        y cuáles van al 10%.
        """
        from itertools import combinations
        
        # Determinar el tipo de IVA reducido (2% en 2024, 4% desde 2025)
        iva_reducido = None
        if 2 in desglose and desglose[2] > 0:
            iva_reducido = 2
        elif 4 in desglose and desglose[4] > 0:
            iva_reducido = 4
        
        if not iva_reducido:
            # Sin IVA reducido, todo al 10%
            for l in lineas:
                l['iva'] = 10
            return lineas
        
        base_reducido_objetivo = desglose.get(iva_reducido, 0)
        
        # Identificar candidatos a IVA reducido
        candidatos = [(i, l) for i, l in enumerate(lineas) if self._es_candidato_iva_reducido(l['articulo'])]
        
        # Probar todas las combinaciones de candidatos
        mejor_combo = None
        mejor_diff = float('inf')
        
        for r in range(len(candidatos) + 1):
            for combo in combinations(candidatos, r):
                suma = sum(l['base'] for i, l in combo)
                diff = abs(suma - base_reducido_objetivo)
                if diff < mejor_diff:
                    mejor_diff = diff
                    mejor_combo = set(i for i, l in combo)
        
        # Asignar IVA según la mejor combinación
        for i, l in enumerate(lineas):
            if mejor_combo and i in mejor_combo:
                l['iva'] = iva_reducido
            else:
                l['iva'] = 10
        
        return lineas
    
    def _unir_lineas_multilinea(self, lineas_texto: List[str]) -> List[str]:
        """
        Une líneas que están partidas en dos.
        
        Ejemplo:
        "PQVAN130 QUILLO PATATAS SABOR A VINAGRE Y AJO NEGRO"
        "130G - 251204 8,00 1,8500€ 14,80€ 14,80€"
        
        Se convierte en:
        "PQVAN130 QUILLO PATATAS SABOR A VINAGRE Y AJO NEGRO 130G - 251204 8,00 1,8500€ 14,80€ 14,80€"
        """
        resultado = []
        i = 0
        
        # Palabras que NO deben unirse con la siguiente línea
        palabras_no_unir = ['Albarán', 'ARTÍCULO', 'Vencimientos', 'TIPO', 'OBSERVACIONES', 'FORMA']
        
        while i < len(lineas_texto):
            linea_actual = lineas_texto[i].strip()
            
            # No unir si la línea contiene palabras de encabezado
            es_encabezado = any(palabra in linea_actual for palabra in palabras_no_unir)
            
            # Si la línea NO termina con € y la siguiente SÍ termina con €
            # y NO es un encabezado, entonces están partidas
            if (linea_actual and 
                not linea_actual.endswith('€') and 
                '€' not in linea_actual and
                not es_encabezado and
                i + 1 < len(lineas_texto)):
                
                linea_siguiente = lineas_texto[i + 1].strip()
                
                # Verificar que la siguiente tiene el patrón de datos (cantidad, precios, €)
                # y que empieza con algo que parece continuación (no código de producto)
                if (linea_siguiente.endswith('€') and 
                    re.search(r'\d+[,.]?\d*\s+[\d,]+€', linea_siguiente) and
                    not re.match(r'^[A-Z]{2,}[A-Z0-9]*\s+[A-Z]', linea_siguiente)):
                    # Unir las dos líneas
                    linea_unida = linea_actual + ' ' + linea_siguiente
                    resultado.append(linea_unida)
                    i += 2  # Saltar ambas líneas
                    continue
            
            resultado.append(linea_actual)
            i += 1
        
        return resultado
    
    def extraer_lineas(self, texto: str) -> List[Dict]:
        """
        Extrae líneas de producto.
        
        Formato:
        CODIGO DESCRIPCION CANTIDAD PRECIO€ SUBTOTAL€ TOTAL€
        
        Los importes son BASE (sin IVA).
        El IVA se asigna buscando la combinación que cuadre con el desglose.
        La categoría se obtiene del diccionario (en main.py).
        """
        lineas = []
        lineas_texto = texto.split('\n')
        
        # Unir líneas partidas
        lineas_texto = self._unir_lineas_multilinea(lineas_texto)
        
        # Extraer desglose IVA de la factura
        desglose = self.extraer_desglose_iva(texto)
        
        # Patrón para líneas de producto
        # CODIGO DESC CANTIDAD PRECIO€ SUBTOTAL€ TOTAL€
        patron = re.compile(
            r'^(.+?)\s+'                     # Código + Descripción
            r'(\d+[,.]?\d*)\s+'              # Cantidad
            r'([\d,]+)€\s+'                  # Precio unitario
            r'([\d,]+)€\s+'                  # Subtotal
            r'([\d,]+)€$'                    # Total (base)
        )
        
        for linea in lineas_texto:
            linea = linea.strip()
            
            # Ignorar líneas no relevantes
            if not linea or 'TOTAL:' in linea or 'Albarán:' in linea:
                continue
            if 'Vencimientos' in linea or 'ARTÍCULO' in linea:
                continue
            if '€' not in linea:
                continue
            if 'TIPO' in linea and 'BASE' in linea:
                continue
            
            match = patron.match(linea)
            if match:
                prefijo = match.group(1).strip()
                cantidad = self._convertir_europeo(match.group(2))
                precio = self._convertir_europeo(match.group(3))
                base = self._convertir_europeo(match.group(5))
                
                # Ignorar líneas con importe muy bajo
                if base < 1.0:
                    continue
                
                # Separar código de descripción
                codigo, articulo = self._separar_codigo_descripcion(prefijo)
                
                # Limpiar descripción
                articulo = self._limpiar_descripcion(articulo)
                
                lineas.append({
                    'codigo': codigo or '',
                    'articulo': articulo[:50],
                    'cantidad': int(cantidad) if cantidad == int(cantidad) else cantidad,
                    'precio_ud': precio,
                    'iva': 0,  # Se asigna después
                    'base': base
                    # Sin 'categoria' - la asigna main.py desde el diccionario
                })
        
        # Asignar IVA basándose en el desglose de la factura
        lineas = self._asignar_iva_por_desglose(lineas, desglose)
        
        return lineas
    
    def _separar_codigo_descripcion(self, prefijo: str) -> tuple:
        """Separa código de descripción."""
        # Caso 1: Código con espacio (ej: "LR 010 LA RUSTICA...")
        match_espacio = re.match(r'^([A-Z]{2,3}\s+\d{3,4})\s+(.+)$', prefijo)
        if match_espacio:
            return match_espacio.group(1), match_espacio.group(2)
        
        # Caso 2: Código alfanumérico (ej: "AOVENOV500 AOVE...")
        match_normal = re.match(r'^([A-Z][A-Z0-9]{3,14})\s+(.+)$', prefijo)
        if match_normal:
            codigo = match_normal.group(1)
            resto = match_normal.group(2)
            return codigo, resto
        
        # Caso 3: Sin código claro
        return None, prefijo
    
    def _limpiar_descripcion(self, desc: str) -> str:
        """Limpia la descripción de lotes y caracteres extra."""
        # Quitar códigos de lote al final (ej: "- 251204", "- L094M")
        desc = re.sub(r'\s*-\s*[A-Z0-9]+$', '', desc)
        desc = re.sub(r'\s*-\s*L\d+[A-Z]?$', '', desc)
        desc = re.sub(r'\s*-\s*\d{6}$', '', desc)
        # Quitar sufijos de gramaje redundantes que quedaron de líneas partidas
        desc = re.sub(r'\s+\d+G\s*-\s*\d+$', '', desc)
        desc = ' '.join(desc.split())
        return desc
    
    def extraer_total(self, texto: str) -> Optional[float]:
        """Extrae total de la factura."""
        # Buscar "TOTAL: XXX,XX€"
        m = re.search(r'TOTAL:\s*([\d.,]+)€?', texto)
        if m:
            total = self._convertir_europeo(m.group(1))
            if total > 10:
                return total
        
        # Fallback: calcular desde desglose
        desglose = self.extraer_desglose_iva(texto)
        if desglose:
            total = 0
            for tipo, base in desglose.items():
                total += base * (1 + tipo / 100)
            return round(total, 2)
        
        return None
    
    def extraer_fecha(self, texto: str) -> Optional[str]:
        """Extrae fecha de la factura."""
        # Buscar formato DD/MM/YYYY
        m = re.search(r'(\d{2}/\d{2}/\d{4})', texto)
        if m:
            return m.group(1)
        return None
