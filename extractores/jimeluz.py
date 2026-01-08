# -*- coding: utf-8 -*-
"""
Extractor para JIMELUZ EMPRENDEDORES S.L.

Supermercado en Calle Embajadores, 50 - 28005 Madrid.
Venta de frutas, verduras, limpieza, hielo, etc.

REQUIERE OCR - Las facturas son tickets escaneados.

Estrategia:
1. Extraer TOTAL del PDF
2. Extraer lineas con OCR
3. Buscar cada articulo en diccionario (fuzzy matching)
4. Si no encuentra, deducir IVA por palabras clave o del ticket
5. Si OCR falla, marcar como PENDIENTE

Creado: 04/01/2026
"""
from extractores.base import ExtractorBase
from extractores import registrar
from typing import List, Dict, Optional, Tuple
import re
from pathlib import Path

# OCR imports
try:
    from pdf2image import convert_from_path
    import pytesseract
    OCR_DISPONIBLE = True
except ImportError:
    OCR_DISPONIBLE = False

# Pandas para diccionario
try:
    import pandas as pd
    PANDAS_DISPONIBLE = True
except ImportError:
    PANDAS_DISPONIBLE = False


@registrar('JIMELUZ', 'JIMELUZ EMPRENDEDORES', 'JIMELUZ EMPRENDEDORES S.L.',
           'JIMELUZ EMPRENDEDORES SL', 'IMELUZ', 'JIME LUZ')
class ExtractorJimeluz(ExtractorBase):
    """Extractor para tickets escaneados de JIMELUZ (requiere OCR)."""
    
    nombre = 'JIMELUZ EMPRENDEDORES S.L.'
    cif = ''
    iban = ''
    metodo_pdf = 'ocr'
    
    # Diccionario singleton
    _diccionario = None
    
    # Palabras clave para deducir IVA
    KEYWORDS_IVA_4 = ['BANANA', 'MANZANA', 'NARANJA', 'LIMON', 'LIMA', 'RUCULA', 
                      'FRUTA', 'VERDURA', 'TOMATE', 'LECHUGA', 'PATATA', 'CEBOLLA',
                      'PIMIENTO', 'PEPINO', 'ZANAHORIA', 'GRANEL', 'MESA CRF']
    KEYWORDS_IVA_10 = ['HIELO', 'AGUA', 'LECHE', 'YOGUR', 'QUESO', 'PAN', 'MOLLETE',
                       'CHOCOLATE', 'SALMON', 'PESCADO', 'CUBITO', 'KIT KAT']
    KEYWORDS_IVA_21 = ['PAPEL', 'BOLSA', 'ALUMINIO', 'LIMPIEZA', 'LEJIA', 'BAYETA',
                       'HIGIENICO', 'SERVILLETA', 'FREGONA']
    
    def __init__(self):
        """Inicializa el extractor y carga el diccionario."""
        super().__init__()
        self._cargar_diccionario()
    
    def _cargar_diccionario(self):
        """Carga el diccionario de productos JIMELUZ."""
        if ExtractorJimeluz._diccionario is not None:
            return
        
        if not PANDAS_DISPONIBLE:
            ExtractorJimeluz._diccionario = {}
            return
        
        posibles_rutas = [
            Path('datos/DiccionarioProveedoresCategoria.xlsx'),
            Path('DiccionarioProveedoresCategoria.xlsx'),
            Path('../datos/DiccionarioProveedoresCategoria.xlsx'),
        ]
        
        for ruta in posibles_rutas:
            if ruta.exists():
                try:
                    df = pd.read_excel(ruta, sheet_name='Articulos')
                    jimeluz_df = df[df['PROVEEDOR'].str.contains('JIMELUZ', case=False, na=False)]
                    ExtractorJimeluz._diccionario = {}
                    for _, row in jimeluz_df.iterrows():
                        art = str(row['ARTICULO']).strip().upper()
                        ExtractorJimeluz._diccionario[art] = {
                            'iva': int(row['TIPO_IVA']) if pd.notna(row['TIPO_IVA']) else None,
                            'categoria': str(row['CATEGORIA']) if pd.notna(row['CATEGORIA']) else None
                        }
                    return
                except Exception as e:
                    print(f"[JIMELUZ] Error cargando diccionario: {e}")
        
        ExtractorJimeluz._diccionario = {}
    
    def _convertir_importe(self, texto: str) -> float:
        """Convierte texto a float (formato europeo)."""
        if not texto:
            return 0.0
        texto = str(texto).strip().replace(' ', '')
        texto = re.sub(r'[^\d,.]', '', texto)
        if '.' in texto and ',' in texto:
            texto = texto.replace('.', '').replace(',', '.')
        elif ',' in texto:
            texto = texto.replace(',', '.')
        try:
            return float(texto)
        except:
            return 0.0
    
    def _buscar_en_diccionario(self, descripcion: str) -> Optional[Dict]:
        """
        Busca articulo en diccionario con fuzzy matching.
        Retorna {'iva': X, 'categoria': Y} o None.
        """
        if not ExtractorJimeluz._diccionario:
            return None
        
        desc_upper = descripcion.upper().strip()
        
        # 1. Match exacto
        if desc_upper in ExtractorJimeluz._diccionario:
            return ExtractorJimeluz._diccionario[desc_upper]
        
        # 2. Match parcial - descripcion contiene articulo del diccionario
        for art, data in ExtractorJimeluz._diccionario.items():
            # Si el articulo del diccionario esta contenido en la descripcion
            if art in desc_upper:
                return data
            # Si la descripcion esta contenida en el articulo del diccionario
            if desc_upper in art:
                return data
        
        # 3. Match por palabras clave principales (primeras 2-3 palabras)
        palabras_desc = desc_upper.split()[:3]
        for art, data in ExtractorJimeluz._diccionario.items():
            palabras_art = art.split()[:3]
            # Si coinciden las primeras palabras
            if palabras_desc and palabras_art:
                if palabras_desc[0] == palabras_art[0]:
                    if len(palabras_desc) > 1 and len(palabras_art) > 1:
                        if palabras_desc[1][:3] == palabras_art[1][:3]:
                            return data
                    else:
                        return data
        
        return None
    
    def _deducir_iva_por_keywords(self, descripcion: str) -> Optional[int]:
        """Deduce IVA por palabras clave cuando no esta en diccionario."""
        desc_upper = descripcion.upper()
        
        for kw in self.KEYWORDS_IVA_4:
            if kw in desc_upper:
                return 4
        
        for kw in self.KEYWORDS_IVA_10:
            if kw in desc_upper:
                return 10
        
        for kw in self.KEYWORDS_IVA_21:
            if kw in desc_upper:
                return 21
        
        return None
    
    def _determinar_categoria(self, descripcion: str, iva: int) -> str:
        """Determina categoria basada en descripcion e IVA."""
        desc_upper = descripcion.upper()
        
        # Por palabras clave
        if any(kw in desc_upper for kw in ['BANANA', 'MANZANA', 'NARANJA', 'LIMON', 'LIMA']):
            return 'FRUTAS Y VERDURAS'
        if any(kw in desc_upper for kw in ['RUCULA', 'LECHUGA', 'TOMATE', 'VERDURA']):
            return 'VERDE PARA MOLLETES'
        if 'HIELO' in desc_upper or 'CUBITO' in desc_upper:
            return 'HIELO'
        if any(kw in desc_upper for kw in ['PAPEL', 'ALUMINIO', 'HIGIENICO', 'LIMPIEZA']):
            return 'LIMPIEZA'
        if 'SALMON' in desc_upper:
            return 'PESCADO (SALMON BACALAO)'
        if 'MOLLETE' in desc_upper:
            return 'MOLLETES'
        
        # Por IVA
        if iva == 4:
            return 'FRUTAS Y VERDURAS'
        elif iva == 10:
            return 'ALIMENTACION'
        elif iva == 21:
            return 'LIMPIEZA'
        
        return 'PENDIENTE'
    
    def extraer_texto(self, pdf_path: str) -> str:
        """Extrae texto del PDF usando OCR."""
        if not OCR_DISPONIBLE:
            return ""
        
        try:
            images = convert_from_path(pdf_path, dpi=300)
            texto_completo = []
            for img in images:
                try:
                    texto = pytesseract.image_to_string(img, lang='spa')
                except:
                    texto = pytesseract.image_to_string(img, lang='eng')
                texto_completo.append(texto)
            return '\n'.join(texto_completo)
        except Exception as e:
            print(f"[JIMELUZ] Error OCR: {e}")
            return ""
    
    def extraer_lineas(self, texto: str) -> List[Dict]:
        """
        Extrae lineas de productos del ticket.
        Formato: CANT DESCRIPCION %IVA IMPORTE
        Multiples patrones para tolerar OCR malo.
        
        Si las lineas extraidas suman menos del 50% del total,
        retorna una linea PENDIENTE con el total.
        """
        lineas = []
        lineas_procesadas = set()
        
        # Patron 1: Formato limpio "1 BANANA GRANEL 4,00 0,19"
        patron1 = re.compile(
            r'^\s*(\d+)\s+'
            r'([A-Za-z][A-Za-z0-9\s/,\.\-]+?)\s+'
            r'(\d{1,2})[,.](\d{2})\s+'
            r'(\d+[,\.]\d{2})\s*$'
        )
        
        # Patron 2: Con espacios en IVA "1 LIMON 4, 00 1,49"
        patron2 = re.compile(
            r'^\s*(\d+)\s+'
            r'([A-Za-z][A-Za-z0-9\s/,\.\-]+?)\s+'
            r'(\d{1,2})[,.\s]+(\d{2})\s+'
            r'(\d+[,\.]\d{2})\s*$'
        )
        
        # Patron 3: Mas flexible, buscar IVA conocido y importe al final
        patron3 = re.compile(
            r'^\s*[\d\-\*]?\s*(\d+)\s+'
            r'(.+?)\s+'
            r'(4|10|21)[,.\s]*0{1,2}\s+'
            r'(\d+[,\.]\d{2})\s*$'
        )
        
        for line in texto.split('\n'):
            line_original = line.strip()
            if not line_original:
                continue
            
            # Normalizar caracteres OCR comunes
            line = line_original.replace('|', '1').replace('!', '1').replace('l', '1')
            line = re.sub(r'\s+', ' ', line)
            
            # Ignorar lineas de totales y cabeceras
            line_upper = line.upper()
            if any(x in line_upper for x in ['TOTAL', 'BASE', 'CUOTA', 'NUM.', 'OTROS', 
                                              'BONIFICACION', 'COPIA', 'TICKET', 'DATOS',
                                              'FACTURA', 'NOMBRE', 'FISCAL', 'DOMICIL',
                                              'POBLACION', 'PROVINCIA', 'POSTAL', 'CAJA',
                                              'ARTICULO', 'CANT.', 'DESCRIPCION', 'IMPORTE',
                                              'JIMELUZ', 'EMBAJADOR', 'MADRID', 'RODAS']):
                continue
            
            # Intentar patrones en orden
            m = patron1.match(line) or patron2.match(line) or patron3.match(line)
            
            if m:
                try:
                    cantidad = int(m.group(1))
                    descripcion = m.group(2).strip()
                    
                    # Extraer IVA
                    if len(m.groups()) == 5:
                        iva_entero = int(m.group(3))
                        importe = self._convertir_importe(m.group(5))
                    else:
                        iva_entero = int(m.group(3))
                        importe = self._convertir_importe(m.group(4))
                    
                    # Validar
                    if iva_entero not in [4, 10, 21]:
                        continue
                    if importe <= 0 or importe > 100:
                        continue
                    if cantidad <= 0 or cantidad > 50:
                        continue
                    if len(descripcion) < 3:
                        continue
                    
                    # Evitar duplicados
                    key = f"{cantidad}_{descripcion[:10]}_{importe}"
                    if key in lineas_procesadas:
                        continue
                    lineas_procesadas.add(key)
                    
                    # Buscar en diccionario
                    dict_match = self._buscar_en_diccionario(descripcion)
                    
                    if dict_match:
                        iva = dict_match['iva'] if dict_match['iva'] else iva_entero
                        categoria = dict_match['categoria'] if dict_match['categoria'] else 'PENDIENTE'
                    else:
                        iva_deducido = self._deducir_iva_por_keywords(descripcion)
                        iva = iva_deducido if iva_deducido else iva_entero
                        categoria = self._determinar_categoria(descripcion, iva)
                    
                    # Calcular base (importe incluye IVA)
                    base = round(importe / (1 + iva / 100), 2)
                    
                    lineas.append({
                        'articulo': descripcion[:50],
                        'cantidad': cantidad,
                        'precio_ud': round(importe / cantidad, 4) if cantidad > 0 else importe,
                        'iva': iva,
                        'base': base,
                        'categoria': categoria
                    })
                except (ValueError, IndexError):
                    continue
        
        # Verificar si OCR capturo suficientes lineas (>50% del total)
        total = self.extraer_total(texto)
        if total and total > 0:
            suma_lineas = sum(l['base'] * (1 + l['iva']/100) for l in lineas)
            cobertura = suma_lineas / total
            
            if cobertura < 0.5:
                # OCR insuficiente - retornar linea PENDIENTE
                return [{
                    'articulo': 'PENDIENTE REVISION OCR',
                    'cantidad': 1,
                    'precio_ud': 0,
                    'iva': 0,
                    'base': 0,
                    'categoria': 'PENDIENTE'
                }]
        elif not lineas:
            # Sin total y sin lineas - PENDIENTE
            return [{
                'articulo': 'PENDIENTE REVISION OCR',
                'cantidad': 1,
                'precio_ud': 0,
                'iva': 0,
                'base': 0,
                'categoria': 'PENDIENTE'
            }]
        
        return lineas
    
    def extraer_total(self, texto: str) -> Optional[float]:
        """Extrae TOTAL del ticket con tolerancia a OCR malo."""
        texto_norm = texto.upper().replace('|', '1').replace('!', '1')
        
        # 1. TOTAL FACTURA (varias formas de escribirlo)
        patrones_factura = [
            r'TOTAL\s*FACTURA[^\d]*([\d]+[,.][\d]{2})',
            r'TOTAL\s*FA[^\d]*([\d]+[,.][\d]{2})',
            r'TOTAL\s*FAC[^\d]*([\d]+[,.][\d]{2})',
        ]
        for p in patrones_factura:
            m = re.search(p, texto_norm)
            if m:
                val = self._convertir_importe(m.group(1))
                if 0.5 < val < 500:
                    return val
        
        # 2. TOTAL PAGADO
        m2 = re.search(r'TOTAL\s*PAGADO[^\d]*([\d]+[,.][\d]{2})', texto_norm)
        if m2:
            val = self._convertir_importe(m2.group(1))
            if 0.5 < val < 500:
                return val
        
        # 3. TOTAL COMPRA
        m3 = re.search(r'TOTAL\s*COMPRA[^\d]*([\d]+[,.][\d]{2})', texto_norm)
        if m3:
            val = self._convertir_importe(m3.group(1))
            if 0.5 < val < 500:
                return val
        
        # 4. Buscar numero que aparece 2+ veces (el total aparece varias veces)
        todos = re.findall(r'([\d]+[,.][\d]{2})', texto)
        if todos:
            from collections import Counter
            valores = [self._convertir_importe(v) for v in todos]
            valores_filtrados = [v for v in valores if v not in [21.0, 10.0, 4.0, 0.0] and 0.5 < v < 500]
            if valores_filtrados:
                contador = Counter(valores_filtrados)
                mas_comun = contador.most_common(1)
                if mas_comun and mas_comun[0][1] >= 2:
                    return mas_comun[0][0]
        
        return None
    
    def extraer_fecha(self, texto: str) -> Optional[str]:
        """Extrae fecha del ticket."""
        m = re.search(r'FECHA[:\s]*(\d{2}/\d{2}/\d{4})', texto, re.IGNORECASE)
        if m:
            return m.group(1)
        return None
    
    def extraer_referencia(self, texto: str) -> Optional[str]:
        """Extrae numero de factura."""
        m = re.search(r'FACTURA\s*N[.:\s]*([A-Z]?\d{6,12})', texto, re.IGNORECASE)
        if m:
            return m.group(1)
        return None
