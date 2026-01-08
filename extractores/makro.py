# -*- coding: utf-8 -*-
"""
Extractor para MAKRO DISTRIBUCION MAYORISTA S.A.

Mayorista de alimentacion y menaje.
CIF: A-28647451 (no necesario - pago con tarjeta)

Estructura de factura:
- Lineas de producto: EAN DESCRIPCION CONT PREC.UD CONT_P PRECIO CANT IMPORTE IMP
- Codigo IVA: 1=10%, 2=21%, 5=4%
- Descuentos: "COMPRA MAS PAGA MENOS" con importe negativo
- Total: "Total a pagar XX,XX EUR"

Usa diccionario para categorias. Si no encuentra, categoria PENDIENTE.

Creado: 04/01/2026
"""
from extractores.base import ExtractorBase
from extractores import registrar
from typing import List, Dict, Optional
import re
from pathlib import Path
import pdfplumber

# Pandas para diccionario
try:
    import pandas as pd
    PANDAS_DISPONIBLE = True
except ImportError:
    PANDAS_DISPONIBLE = False


@registrar('MAKRO', 'MAKRO DISTRIBUCION', 'MAKRO DISTRIBUCION MAYORISTA',
           'MAKRO DISTRIBUCION MAYORISTA S.A.', 'MAKRO DISTRIBUCION MAYORISTA, S.A.')
class ExtractorMakro(ExtractorBase):
    """Extractor para facturas de MAKRO."""
    
    nombre = 'MAKRO DISTRIBUCION MAYORISTA S.A.'
    cif = 'A28647451'
    iban = ''
    metodo_pdf = 'pdfplumber'
    
    # Diccionario singleton
    _diccionario = None
    
    # Mapeo codigo IVA MAKRO
    CODIGO_IVA = {
        '1': 10,
        '2': 21,
        '5': 4,
    }
    
    # Tipos de contenedor validos en MAKRO
    TIPOS_CONTENEDOR = ['RT', 'BL', 'CJ', 'UD', 'PK', 'GF', 'BO', 'AE', 'TR', 'PZ', 'BT', '--']
    
    def __init__(self):
        """Inicializa el extractor y carga el diccionario."""
        super().__init__()
        self._cargar_diccionario()
    
    def _cargar_diccionario(self):
        """Carga el diccionario de productos MAKRO."""
        if ExtractorMakro._diccionario is not None:
            return
        
        if not PANDAS_DISPONIBLE:
            ExtractorMakro._diccionario = {}
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
                    makro_df = df[df['PROVEEDOR'].str.contains('MAKRO', case=False, na=False)]
                    ExtractorMakro._diccionario = {}
                    for _, row in makro_df.iterrows():
                        art = str(row['ARTICULO']).strip().upper()
                        # Normalizar quitando espacios multiples
                        art_norm = ' '.join(art.split())
                        ExtractorMakro._diccionario[art_norm] = {
                            'iva': int(row['TIPO_IVA']) if pd.notna(row['TIPO_IVA']) else None,
                            'categoria': str(row['CATEGORIA']) if pd.notna(row['CATEGORIA']) else None
                        }
                    return
                except Exception as e:
                    print(f"[MAKRO] Error cargando diccionario: {e}")
        
        ExtractorMakro._diccionario = {}
    
    def _convertir_importe(self, texto: str) -> float:
        """Convierte texto a float (formato europeo)."""
        if not texto:
            return 0.0
        texto = str(texto).strip().replace(' ', '')
        texto = re.sub(r'[^\d,.\-]', '', texto)
        negativo = '-' in texto
        texto = texto.replace('-', '')
        if '.' in texto and ',' in texto:
            texto = texto.replace('.', '').replace(',', '.')
        elif ',' in texto:
            texto = texto.replace(',', '.')
        try:
            valor = float(texto)
            return -valor if negativo else valor
        except:
            return 0.0
    
    def _buscar_en_diccionario(self, descripcion: str) -> Optional[Dict]:
        """Busca articulo en diccionario con fuzzy matching."""
        if not ExtractorMakro._diccionario:
            return None
        
        desc_norm = ' '.join(descripcion.upper().strip().split())
        
        # 1. Match exacto
        if desc_norm in ExtractorMakro._diccionario:
            return ExtractorMakro._diccionario[desc_norm]
        
        # 2. Match parcial - descripcion contiene articulo del diccionario
        for art, data in ExtractorMakro._diccionario.items():
            if art in desc_norm or desc_norm in art:
                return data
        
        # 3. Match por primeras palabras
        palabras_desc = desc_norm.split()[:3]
        for art, data in ExtractorMakro._diccionario.items():
            palabras_art = art.split()[:3]
            if palabras_desc and palabras_art:
                if palabras_desc[0] == palabras_art[0]:
                    if len(palabras_desc) > 1 and len(palabras_art) > 1:
                        if palabras_desc[1] == palabras_art[1]:
                            return data
                    elif len(palabras_desc) == 1 or len(palabras_art) == 1:
                        return data
        
        return None
    
    def extraer_texto(self, pdf_path: str) -> str:
        """Extrae texto del PDF con pdfplumber."""
        try:
            texto_completo = []
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    texto = page.extract_text()
                    if texto:
                        texto_completo.append(texto)
            return '\n'.join(texto_completo)
        except Exception as e:
            print(f"[MAKRO] Error extrayendo texto: {e}")
            return ''
    
    def _compactar_linea(self, linea: str) -> str:
        """Compacta lineas con espacios entre caracteres."""
        chars = linea.split(' ')
        if len(chars) > 10 and sum(1 for c in chars if len(c) == 1) > len(chars) * 0.5:
            return ''.join(chars)
        return linea
    
    def _parsear_linea_producto(self, linea: str) -> Optional[Dict]:
        """Parsea una linea de producto MAKRO."""
        linea_original = linea.strip()
        linea = self._compactar_linea(linea_original)
        
        # Intentar formato con espacios normales primero
        m_normal = re.match(
            r'^(\d{13,14})\s+'          # EAN
            r'(.+?)\s+'                  # DESC
            r'([A-Z]{2}|--)\s+'          # TIPO
            r'([\d,]+)\s+'               # PREC_UD
            r'(\d+)\s+'                  # CONT
            r'([\d,]+)\s+'               # PRECIO
            r'(\d+)\s+'                  # CANT
            r'([\d,]+)\s+'               # IMPORTE
            r'(\d)'                      # IVA
            , linea_original)
        
        if m_normal:
            try:
                ean = m_normal.group(1)
                desc = m_normal.group(2).strip()
                precio = float(m_normal.group(6).replace(',', '.'))
                cant = int(m_normal.group(7))
                importe = float(m_normal.group(8).replace(',', '.'))
                cod_iva = m_normal.group(9)
                
                # Validar matematicamente
                esperado = cant * precio
                if abs(importe - esperado) < esperado * 0.2:
                    return {
                        'ean': ean,
                        'descripcion': desc,
                        'cantidad': cant,
                        'importe': importe,
                        'iva': self.CODIGO_IVA.get(cod_iva, 21)
                    }
            except:
                pass
        
        # Intentar formato compactado (sin espacios)
        m_ean = re.match(r'^(0?\d{13})', linea)
        if not m_ean:
            return None
        
        ean = m_ean.group(1)
        resto = linea[len(ean):]
        
        # Buscar tipo de contenedor - el ULTIMO que aparece seguido de numero
        tipo_encontrado = None
        pos_tipo = -1
        
        for tipo in self.TIPOS_CONTENEDOR:
            # Buscar todas las ocurrencias del tipo
            idx = 0
            while True:
                idx = resto.find(tipo, idx)
                if idx == -1:
                    break
                if idx > 0 and idx < len(resto) - 2:
                    despues = resto[idx + len(tipo):]
                    if despues and despues[0].isdigit():
                        # Tomar el que esta mas a la derecha
                        if idx > pos_tipo:
                            tipo_encontrado = tipo
                            pos_tipo = idx
                idx += 1
        
        if not tipo_encontrado:
            return None
        
        desc_raw = resto[:pos_tipo]
        numeros_str = resto[pos_tipo + 2:]
        
        # Probar diferentes combinaciones y validar matematicamente
        mejor_match = None
        mejor_diff = float('inf')
        
        for prec_ud_decimales in [3, 2]:
            for cont_digitos in [1, 2, 3]:
                for precio_enteros in [1, 2, 3]:
                    for cant_digitos in [1, 2]:
                        try:
                            patron = (
                                r'^(\d+,\d{' + str(prec_ud_decimales) + r'})'
                                r'(\d{' + str(cont_digitos) + r'})'
                                r'(\d{' + str(precio_enteros) + r'},\d{2})'
                                r'(\d{' + str(cant_digitos) + r'})'
                                r'(\d+,\d{2})'
                                r'(\d)'
                            )
                            
                            m = re.match(patron, numeros_str)
                            if not m:
                                continue
                            
                            prec_ud = float(m.group(1).replace(',', '.'))
                            cont = int(m.group(2))
                            precio = float(m.group(3).replace(',', '.'))
                            cant = int(m.group(4))
                            importe = float(m.group(5).replace(',', '.'))
                            cod_iva = m.group(6)
                            
                            if cant <= 0 or cant > 200:
                                continue
                            if cont <= 0 or cont > 100:
                                continue
                            if importe <= 0 or importe > 5000:
                                continue
                            
                            # Validacion matematica: importe ≈ cant * precio
                            esperado = cant * precio
                            diff = abs(importe - esperado)
                            
                            if diff < esperado * 0.15 and diff < mejor_diff:
                                mejor_diff = diff
                                mejor_match = {
                                    'cant': cant,
                                    'importe': importe,
                                    'cod_iva': cod_iva
                                }
                        except:
                            continue
        
        if not mejor_match:
            return None
        
        iva = self.CODIGO_IVA.get(mejor_match['cod_iva'], 21)
        
        # Formatear descripcion
        desc = re.sub(r'(\d)([A-Z])', r'\1 \2', desc_raw)
        desc = re.sub(r'([A-Z])(\d)', r'\1 \2', desc)
        
        return {
            'ean': ean,
            'descripcion': desc,
            'cantidad': mejor_match['cant'],
            'importe': mejor_match['importe'],
            'iva': iva
        }
    
    def extraer_lineas(self, texto: str) -> List[Dict]:
        """Extrae lineas de productos de la factura MAKRO."""
        lineas = []
        ultima_categoria = 'PENDIENTE'
        
        for line in texto.split('\n'):
            line = line.strip()
            if not line:
                continue
            
            line_compact = self._compactar_linea(line)
            
            # Ignorar cabeceras y pies
            if any(x in line_compact.upper() for x in ['FACTURA', 'PAGINA', 'NCLIENTE',
                                                        'NIF', 'TASCABAREA', 'MADRID',
                                                        'MERCANCIA', 'TOTALAPAGAR',
                                                        'TARJETA', 'NUMERODEBULTOS',
                                                        'DEVOLUCIONES', 'FINDEFACTURA',
                                                        '----', 'PESOTOTAL']):
                continue
            
            # Buscar descuento
            if 'COMPRAMASPA' in line_compact.upper() or 'COMPRA MAS PAGA' in line.upper():
                m_desc = re.search(r'([\d,]+)-(\d)', line_compact)
                if m_desc:
                    # El importe del descuento es BASE (sin IVA)
                    base = -abs(float(m_desc.group(1).replace(',', '.')))
                    cod_iva = m_desc.group(2)
                    iva = self.CODIGO_IVA.get(cod_iva, 21)
                    
                    lineas.append({
                        'articulo': 'DESCUENTO COMPRA MAS PAGA MENOS',
                        'cantidad': 1,
                        'precio_ud': base,
                        'iva': iva,
                        'base': base,
                        'categoria': ultima_categoria
                    })
                continue
            
            # Buscar producto
            producto = self._parsear_linea_producto(line)
            if producto:
                # Buscar en diccionario
                dict_match = self._buscar_en_diccionario(producto['descripcion'])
                
                if dict_match and dict_match['categoria']:
                    categoria = dict_match['categoria']
                else:
                    categoria = 'PENDIENTE'
                
                ultima_categoria = categoria
                
                # En MAKRO el importe es la BASE (sin IVA)
                base = producto['importe']
                
                lineas.append({
                    'articulo': producto['descripcion'][:50],
                    'cantidad': producto['cantidad'],
                    'precio_ud': round(base / producto['cantidad'], 4),
                    'iva': producto['iva'],
                    'base': base,
                    'categoria': categoria
                })
        
        return lineas
    
    def extraer_total(self, texto: str) -> Optional[float]:
        """Extrae total de la factura."""
        for line in texto.split('\n'):
            line_compact = self._compactar_linea(line)
            
            # Patron: "Total a pagar XX,XX EUR" o "Totalapagar XX,XX EUR"
            if 'Totalapagar' in line_compact or 'Total a pagar' in line:
                m = re.search(r'([\d,]+)\s*EUR', line_compact)
                if m:
                    return self._convertir_importe(m.group(1))
            
            # Alternativo: "Tarjeta XX,XX EUR"
            if 'Tarjeta' in line_compact:
                m = re.search(r'Tarjeta\s*([\d,]+)\s*EUR', line_compact)
                if m:
                    return self._convertir_importe(m.group(1))
        
        return None
    
    def extraer_fecha(self, texto: str) -> Optional[str]:
        """Extrae fecha de la factura."""
        for line in texto.split('\n'):
            line_compact = self._compactar_linea(line)
            
            # Patron: "Fecha de venta: DD/MM/YYYY" o "Fechadeventa:DD/MM/YYYY"
            m = re.search(r'Fechadeventa:?(\d{2}/\d{2}/\d{4})', line_compact)
            if m:
                return m.group(1)
            
            m2 = re.search(r'Fecha de venta:\s*(\d{2}/\d{2}/\d{4})', line)
            if m2:
                return m2.group(1)
        
        return None
    
    def extraer_referencia(self, texto: str) -> Optional[str]:
        """Extrae numero de factura."""
        for line in texto.split('\n'):
            line_compact = self._compactar_linea(line)
            
            # Patron: "Factura 0/0(064)0004/(2025)026943"
            m = re.search(r'Factura:?\s*([\d/\(\)]+)', line_compact)
            if m:
                ref = m.group(1)
                if len(ref) > 10:  # Formato completo
                    return ref
        
        return None
