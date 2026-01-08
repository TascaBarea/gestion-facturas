# -*- coding: utf-8 -*-
"""
Extractor para DIA / ECOMS SUPERMARKET S.L.
Franquiciado DIA en C/ Embajadores 29, Madrid

CIF: B72738602

IMPORTANTE: Soporta DOS formatos diferentes:

FORMATO 1 - Tickets digitales (pdfplumber):
  - Archivos con texto extraíble
  - Patrón: "DESCRIPCIÓN 2 ud 0,99 € 1,98 € B"
  - Letra A/B/C indica tipo IVA

FORMATO 2 - Tickets fotografiados (OCR):
  - PDFs sin texto (imágenes escaneadas)
  - Patrón: "LIMONES MALLA 2,29808 4,00%"
  - IVA como porcentaje explícito
  - N.FACTURA: FT 139080300130

REGLA FUNDAMENTAL:
  - Siempre extraer líneas INDIVIDUALES por artículo
  - Categoría se asigna via diccionario, NO agrupando por IVA

Creado: 28/12/2025
Actualizado: 04/01/2026 - Soporte OCR + líneas individuales
Actualizado: 07/01/2026 - Añadido extraer_numero_factura()
Actualizado: 07/01/2026 - Fix cuadro fiscal OCR con espacios (10, 00% → 10,00%)
"""
from extractores.base import ExtractorBase
from extractores import registrar
from typing import List, Dict, Optional
import re
import os

# Intentar importar dependencias OCR
try:
    import pytesseract
    from PIL import Image
    from pdf2image import convert_from_path
    OCR_DISPONIBLE = True
except ImportError:
    OCR_DISPONIBLE = False


@registrar(
    'DIA',
    'ECOMS', 
    'ECOMS SUPERMARKET SL', 
    'ECOMS SUPERMARKET S.L.', 
    'ECOMS S', 
    'ECOMS SUPERMARKET',
    'DIA ECOMS',
    'GRUPO DIA',
    'DIA RETAIL',
    'DIA RETAIL ESPAÑA'
)
class ExtractorDiaEcoms(ExtractorBase):
    """Extractor para tickets de DIA / ECOMS SUPERMARKET."""
    
    nombre = 'ECOMS'
    cif = 'B72738602'
    iban = ''
    metodo_pdf = 'pdfplumber'  # Por defecto, cambia a OCR si necesario
    
    # Mapeo letra → tipo IVA (Formato 1)
    LETRA_IVA = {'A': 4, 'B': 10, 'C': 21}
    
    # Diccionario de nombres truncados → nombres completos
    # Los tickets DIA truncan nombres largos con "…"
    NOMBRES_COMPLETOS = {
        'BARRA PEREGRINA 2': 'BARRA PEREGRINA 250G',
        'CUBO OVALADO SP': 'CUBO OVALADO SP 12L',
        'BOLSA BASURA FUC': 'BOLSA BASURA FUCHSIA 30L',
        'PAPEL ALUMINIO 30': 'PAPEL ALUMINIO 30M',
        'FILM TRANSPAREN': 'FILM TRANSPARENTE 30M',
        'RABAS EMPANADAS': 'RABAS EMPANADAS 400G',
        'PIZZA CAMPESTRE': 'PIZZA CAMPESTRE 400G',
        'PIZZA 4 QUESOS ALP': 'PIZZA 4 QUESOS ALPINO',
        'EMPANA D.ATUN COCI': 'EMPANADA ATUN COCIDO',
        'TORT.ARROZ CHOCO': 'TORTITAS ARROZ CHOCOLATE',
        'NUGGETS POLLO AL': 'NUGGETS POLLO ALPINO',
        'NUGGETS POLLO AL PUN': 'NUGGETS POLLO ALPUNTO',
    }
    
    def __init__(self):
        super().__init__()
        self._texto_ocr = None
        self._usa_ocr = False
    
    def _limpiar_nombre(self, nombre: str) -> str:
        """
        Limpia y normaliza el nombre del producto.
        - Elimina caracteres de truncamiento (…)
        - Busca en diccionario de nombres completos
        - Normaliza espacios
        """
        if not nombre:
            return "PRODUCTO DIA"
        
        # Limpiar caracteres de truncamiento
        nombre = nombre.replace('…', '').replace('...', '').strip()
        nombre = re.sub(r'\s+', ' ', nombre).strip()
        
        # Buscar en diccionario de nombres completos
        nombre_upper = nombre.upper()
        if nombre_upper in self.NOMBRES_COMPLETOS:
            return self.NOMBRES_COMPLETOS[nombre_upper]
        
        # Buscar coincidencia parcial (por si el truncamiento es diferente)
        for truncado, completo in self.NOMBRES_COMPLETOS.items():
            if nombre_upper.startswith(truncado) or truncado.startswith(nombre_upper):
                return completo
        
        return nombre_upper
    
    def extraer_numero_factura(self, texto: str) -> Optional[str]:
        """
        Extrae número de factura.
        
        Formato ECOMS OCR: N.FACTURA: FT 139080300130
        El número es FT + 12 dígitos (sin espacio)
        """
        # Buscar N.FACTURA: FT XXXXXXXXXXXX
        patron = re.search(
            r'N\.?FACTURA[:\s]*(FT\s*\d{10,14})',
            texto,
            re.IGNORECASE
        )
        if patron:
            # Devolver sin espacios internos
            return patron.group(1).replace(' ', '')
        
        # Alternativa: buscar solo FT + dígitos
        patron2 = re.search(r'\b(FT\d{10,14})\b', texto)
        if patron2:
            return patron2.group(1)
        
        return None
    
    def extraer_lineas(self, texto: str) -> List[Dict]:
        """
        Extrae líneas INDIVIDUALES de productos.
        Detecta automáticamente el formato y usa el método apropiado.
        """
        if not texto or len(texto.strip()) < 50:
            # Texto vacío o muy corto = necesita OCR
            return []
        
        # Detectar formato por contenido
        if 'VENTA DE ARTICULOS' in texto.upper() or 'VENTA DF ARTICULOS' in texto.upper():
            # Formato 2: Factura formal (puede venir de OCR)
            return self._extraer_formato2(texto)
        elif 'Productos vendidos por Dia' in texto or 'CANTIDADPRECIO' in texto:
            # Formato 1: Ticket digital
            return self._extraer_formato1(texto)
        else:
            # Intentar ambos
            lineas = self._extraer_formato1(texto)
            if not lineas:
                lineas = self._extraer_formato2(texto)
            return lineas
    
    def _extraer_formato1(self, texto: str) -> List[Dict]:
        """
        Extrae productos del Formato 1 (tickets digitales).
        
        MANEJA:
        - Descripciones en línea separada o misma línea
        - Devoluciones (importes negativos): 1 ud 2,49 € -2,49 € A
        - Descuentos/cupones: BOQUERÓN MSC M.MARIN -1,00 €
        - Productos por peso: 0,525kg 1,69 €/kg 0,89 € A
        """
        lineas_raw = []
        
        # Patrón A: Solo precio (puede ser negativo)
        # Ejemplo: "1 ud 2,49 € -2,49 € A" o "2 ud 0,99 € 1,98 € B"
        patron_solo_precio = re.compile(
            r'^(\d+)\s+ud\s+(\d+[,\.]\d+)\s*€?\s+(-?\d+[,\.]\d+)\s*€?\s+([ABC])$',
            re.IGNORECASE
        )
        
        # Patrón B: Descripción + precio en misma línea (puede ser negativo)
        patron_con_desc = re.compile(
            r'^([A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ\s0-9\.\-]+?)\s+(\d+)\s+ud\s+(\d+[,\.]\d+)\s*€?\s+(-?\d+[,\.]\d+)\s*€?\s+([ABC])$',
            re.IGNORECASE
        )
        
        # Patrón C: Productos por peso (puede ser negativo)
        patron_peso = re.compile(
            r'^(\d+[,\.]\d+)\s*kg\s*(\d+[,\.]\d+)\s*€/kg\s+(-?\d+[,\.]\d+)\s*€?\s+([ABC])$',
            re.IGNORECASE
        )
        
        lineas_texto = [l.strip() for l in texto.split('\n')]
        
        IGNORAR = [
            'productos vendidos', 'descripción', 'cantidadprecio', 
            'forma de pago', 'resumen', 'desglose', 'tipo iva', 'iva incluido',
            'ecoms', 'supermarket', 'documento', 'compra en', 'tienda',
            'total', 'efectivo', 'cambio', 'tarjeta', 'nº de', 'fecha',
            'factura', 'empleado', 'caja', 'canjeado', 'nº', 'venta dia',
            'ofertas y cupones', 'validez', 'precio kg'
        ]
        
        i = 0
        while i < len(lineas_texto):
            linea = lineas_texto[i]
            
            # Ignorar líneas de sistema
            if any(ign in linea.lower() for ign in IGNORAR):
                i += 1
                continue
            
            # Patrón B: Descripción + datos en misma línea
            match = patron_con_desc.match(linea)
            if match:
                desc = match.group(1).strip()
                cantidad = int(match.group(2))
                precio = self._convertir_europeo(match.group(3))
                importe = self._convertir_europeo(match.group(4))
                letra = match.group(5).upper()
                
                if importe != 0:  # Permitir negativos
                    lineas_raw.append({
                        'codigo': 'ECOMS',
                        'articulo': self._limpiar_nombre(desc),
                        'cantidad': cantidad,
                        'precio_ud': precio,
                        'iva': self.LETRA_IVA.get(letra, 10),
                        'base': round(abs(importe), 2) if importe > 0 else round(importe, 2)
                    })
                i += 1
                continue
            
            # Patrón A: Solo datos, descripción en línea anterior
            match = patron_solo_precio.match(linea)
            if match and i > 0:
                cantidad = int(match.group(1))
                precio = self._convertir_europeo(match.group(2))
                importe = self._convertir_europeo(match.group(3))
                letra = match.group(4).upper()
                
                # Buscar descripción en línea anterior
                desc = lineas_texto[i-1].strip()
                
                if importe != 0 and desc:
                    lineas_raw.append({
                        'codigo': 'ECOMS',
                        'articulo': self._limpiar_nombre(desc),
                        'cantidad': cantidad,
                        'precio_ud': precio,
                        'iva': self.LETRA_IVA.get(letra, 10),
                        'base': round(abs(importe), 2) if importe > 0 else round(importe, 2)
                    })
                i += 1
                continue
            
            # Patrón C: Productos por peso
            match = patron_peso.match(linea)
            if match and i > 0:
                peso = self._convertir_europeo(match.group(1))
                precio_kg = self._convertir_europeo(match.group(2))
                importe = self._convertir_europeo(match.group(3))
                letra = match.group(4).upper()
                
                desc = lineas_texto[i-1].strip()
                
                if importe != 0 and desc:
                    lineas_raw.append({
                        'codigo': 'ECOMS',
                        'articulo': self._limpiar_nombre(desc),
                        'cantidad': round(peso, 3),
                        'precio_ud': precio_kg,
                        'iva': self.LETRA_IVA.get(letra, 10),
                        'base': round(abs(importe), 2)
                    })
                i += 1
                continue
            
            i += 1
        
        return lineas_raw
    
    def _extraer_formato2(self, texto: str) -> List[Dict]:
        """
        Extrae productos del Formato 2 (facturas OCR).
        
        Formato línea:
        DESCRIPCION IMPORTE IVA%
        Ej: "LIMONES MALLA 2,29808 4,00%"
        O:  "LIMONES MALLA 2,20192 4,00%"
        """
        lineas = []
        
        for linea in texto.split('\n'):
            linea = linea.strip()
            if not linea or len(linea) < 10:
                continue
            
            # Patrón: DESCRIPCION IMPORTE IVA
            # El IVA puede ser "4,00%" o solo "4" al final
            match = re.match(
                r'^([A-ZÁÉÍÓÚÑ][A-Za-záéíóúñÁÉÍÓÚÑ\s\.\-0-9]+?)\s+'  # Descripción
                r'(\d+[,\.]\d{2,5})\s+'                               # Importe
                r'(\d{1,2})',                                          # IVA (solo dígitos)
                linea, re.IGNORECASE
            )
            
            if not match:
                continue
            
            descripcion = match.group(1).strip()
            importe = self._convertir_europeo(match.group(2))
            
            try:
                iva = int(match.group(3))
            except:
                continue
            
            # Validar IVA
            if iva not in [4, 10, 21]:
                continue
            
            # Validar importe
            if importe <= 0 or importe > 500:
                continue
            
            # Limpiar descripción
            descripcion = descripcion.replace('|', 'L')
            descripcion = re.sub(r'\s+', ' ', descripcion).strip()
            
            # Ignorar líneas del cuadro fiscal
            if any(x in descripcion.lower() for x in ['tipo', 'base', 'cuota', 'total', 'desglose']):
                continue
            
            if len(descripcion) < 3:
                continue
            
            base = round(importe, 2)
            
            lineas.append({
                'codigo': 'ECOMS',
                'articulo': self._limpiar_nombre(descripcion),
                'cantidad': 1,
                'precio_ud': base,
                'iva': iva,
                'base': base
            })
        
        # Si no encontramos líneas, usar cuadro fiscal como fallback
        if not lineas:
            lineas = self._fallback_cuadro_fiscal(texto)
        
        return lineas
    
    def _fallback_cuadro_fiscal(self, texto: str) -> List[Dict]:
        """
        Fallback: crear líneas genéricas desde el cuadro fiscal.
        Se usa cuando el OCR no permite extraer líneas individuales.
        """
        lineas = []
        cuadro = self._extraer_cuadro_fiscal(texto)
        
        for item in cuadro:
            lineas.append({
                'codigo': 'ECOMS',
                'articulo': f'COMPRA DIA IVA {item["tipo"]}%',
                'cantidad': 1,
                'precio_ud': item['base'],
                'iva': item['tipo'],
                'base': item['base']
            })
        
        return lineas
    
    def procesar(self, ruta_archivo: str) -> Dict:
        """
        Procesa factura ECOMS, detectando si necesita OCR.
        Este método se llama desde main.py cuando metodo_pdf='ocr'.
        """
        # Primero intentar con pdfplumber
        try:
            import pdfplumber
            with pdfplumber.open(ruta_archivo) as pdf:
                texto = pdf.pages[0].extract_text() or ''
        except:
            texto = ''
        
        # Si no hay texto suficiente, usar OCR
        if len(texto.strip()) < 50:
            texto = self._extraer_texto_ocr(ruta_archivo)
            self._usa_ocr = True
        
        self._texto_ocr = texto
        
        return {
            'proveedor': self.nombre,
            'cif': self.cif,
            'fecha': self.extraer_fecha(texto),
            'referencia': self.extraer_numero_factura(texto),
            'total': self.extraer_total(texto),
            'lineas': self.extraer_lineas(texto)
        }
    
    def _extraer_texto_ocr(self, ruta_archivo: str) -> str:
        """Extrae texto usando OCR (Tesseract)."""
        if not OCR_DISPONIBLE:
            return ""
        
        extension = os.path.splitext(ruta_archivo)[1].lower()
        
        try:
            if extension in ['.jpg', '.jpeg', '.png', '.bmp', '.tiff']:
                img = Image.open(ruta_archivo)
            elif extension == '.pdf':
                images = convert_from_path(ruta_archivo, dpi=300)
                img = images[0]
            else:
                return ""
            
            # Intentar con español primero
            try:
                texto = pytesseract.image_to_string(img, lang='spa')
            except:
                texto = pytesseract.image_to_string(img)
            
            return texto
        except Exception as e:
            print(f"Error OCR ECOMS: {e}")
            return ""
    
    def extraer_total(self, texto: str) -> Optional[float]:
        """Extrae el total del ticket."""
        if not texto:
            return None
        
        patrones = [
            r'Total a pagar[\.]+\s*(\d+[,\.]\d+)\s*€',
            r'Total a pagar\s*(\d+[,\.]\d+)\s*€',
            r'Total venta Dia[\.]+\s*(\d+[,\.]\d+)\s*€',
            r'TOTAL\s+FACTURA\s+(\d+[,\.]\d+)',
            r'TOTAL\s+FACTURA\s+(\d+[,\.]\d+)',
        ]
        
        for patron in patrones:
            match = re.search(patron, texto, re.IGNORECASE)
            if match:
                return self._convertir_europeo(match.group(1))
        
        # Fallback: calcular desde cuadro fiscal
        cuadro = self._extraer_cuadro_fiscal(texto)
        if cuadro:
            return round(sum(d['base'] * (1 + d['tipo']/100) for d in cuadro), 2)
        
        return None
    
    def _extraer_cuadro_fiscal(self, texto: str) -> List[Dict]:
        """Extrae cuadro de IVA del ticket para validación."""
        desglose = []
        
        # Formato 1: "A 4% 2,66 € 0,11 €"
        patron1 = re.compile(
            r'([ABC])\s+(\d+)%\s+(\d+[,\.]\d+)\s*€?\s+(\d+[,\.]\d+)',
            re.MULTILINE
        )
        
        for match in patron1.finditer(texto):
            tipo = int(match.group(2))
            base = self._convertir_europeo(match.group(3))
            if tipo in [4, 10, 21] and base > 0:
                desglose.append({'tipo': tipo, 'base': base})
        
        if desglose:
            return desglose
        
        # Formato 2: "4,00% 3,26 0,13" o "10, 00% 4,71 0,47" (con espacio por OCR)
        patron2 = re.compile(
            r'(\d+)[,\.]\s*00%\s+(\d+[,\.]\d+)\s+(\d+[,\.]\d+)',
            re.MULTILINE
        )
        
        for match in patron2.finditer(texto):
            tipo = int(match.group(1))
            base = self._convertir_europeo(match.group(2))
            if tipo in [4, 10, 21] and base > 0:
                desglose.append({'tipo': tipo, 'base': base})
        
        return desglose
    
    def extraer_fecha(self, texto: str) -> Optional[str]:
        """Extrae la fecha del ticket."""
        if not texto:
            return None
        
        # Formato 1: "11/10/2025 12:52"
        patron = re.search(r'(\d{2}/\d{2}/\d{4})\s+\d{2}:\d{2}', texto)
        if patron:
            return patron.group(1)
        
        # Formato 2: "EMITIDA: 04-07-2025 20:21"
        patron2 = re.search(r'EMITIDA[:\s]+(\d{2})-(\d{2})-(\d{4})', texto, re.IGNORECASE)
        if patron2:
            return f"{patron2.group(1)}/{patron2.group(2)}/{patron2.group(3)}"
        
        # Formato genérico
        patron3 = re.search(r'(\d{2}/\d{2}/\d{4})', texto)
        if patron3:
            return patron3.group(1)
        
        return None
    
    def _convertir_europeo(self, texto: str) -> float:
        """Convierte formato europeo a float."""
        if not texto:
            return 0.0
        texto = str(texto).strip().replace('€', '').strip()
        if ',' in texto and '.' in texto:
            texto = texto.replace('.', '').replace(',', '.')
        elif ',' in texto:
            texto = texto.replace(',', '.')
        try:
            return float(texto)
        except:
            return 0.0
