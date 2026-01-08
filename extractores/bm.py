"""
Extractor para BM SUPERMERCADOS (DISTRIBUCION SUPERMERCADOS, SL).
CIF: B20099586 | Método pago: Tarjeta (no SEPA)

Tickets de supermercado con IVA mixto (4%, 10%, 21%).

IMPORTANTE: Los importes de líneas INCLUYEN IVA.
Este extractor devuelve 'importe_iva_inc' y main.py:
1. Consulta el diccionario para obtener IVA y categoría
2. Calcula base = importe_iva_inc / (1 + iva/100)

v5.12: Simplificado - IVA y categoría vienen del diccionario
Creado: 01/01/2026
Actualizado: 04/01/2026 - Delega IVA/categoría al diccionario
"""
from extractores.base import ExtractorBase
from extractores import registrar
from typing import List, Dict, Optional
import re


@registrar('BM SUPERMERCADOS', 'BM', 'DISTRIBUCION SUPERMERCADOS', 'SUPERMERCADOS BM')
class ExtractorBM(ExtractorBase):
    """Extractor para tickets de BM SUPERMERCADOS."""
    
    nombre = 'BM SUPERMERCADOS'
    cif = 'B20099586'
    iban = None  # No aplica - pago con tarjeta
    metodo_pdf = 'pdfplumber'
    # Flag para indicar que los importes incluyen IVA
    importes_con_iva = True
    
    def _convertir_importe(self, texto: str) -> float:
        """Convierte texto a float (formato europeo)."""
        if not texto:
            return 0.0
        texto = str(texto).strip().replace('€', '').replace(' ', '')
        if ',' in texto and '.' in texto:
            texto = texto.replace('.', '').replace(',', '.')
        elif ',' in texto:
            texto = texto.replace(',', '.')
        try:
            return float(texto)
        except:
            return 0.0
    
    def extraer_lineas(self, texto: str) -> List[Dict]:
        """
        Extrae líneas de producto del ticket.
        
        Devuelve 'importe_iva_inc' (NO 'base') para que main.py
        calcule la base después de consultar el diccionario.
        """
        lineas = []
        texto_lineas = texto.split('\n')
        
        # Palabras a ignorar
        skip_words = ['TOTAL', 'TARJETA', 'EFECTIVO', 'CAMBIO', 'TICKET', 'AHORRO', 'PUNTO', 
                      'CUENTA BM', 'Tipo', 'Base', '---', '***', 'CIF:', 'FACTURA', 'atendió',
                      'devolución', 'Le atendió', 'COPIA PARA', 'APP ', 'ENTREGADO', 'POR COMPRAR', 
                      'ACUMULADO', 'conseguido', 'NUMERO DE', 'Cliente', 'NIF', 'Nombre', 
                      'Domicilio', 'Población', 'Teléfono', 'atención', 'GRACIAS', 'DUQUE DE ALBA', 
                      'JAIME', 'UD/KG', 'Vencimientos', 'SEC/', 'COMERCIO', 'TITULAR', 'ARC',
                      'AID', 'APLICACION', 'VALIDACION', 'OPER', 'IMPORTE', 'N.SEC', 'Promoción',
                      'Promocion']
        
        i = 0
        while i < len(texto_lineas):
            linea = texto_lineas[i].strip()
            
            # Cambio de sección (ignorar)
            if linea.startswith('- ') and linea.endswith(' -'):
                i += 1
                continue
            
            # Promoción/descuento → aplicar al artículo anterior
            if 'Promoción' in linea or 'Promocion' in linea:
                m_promo = re.search(r'(-?[\d.,]+)$', linea)
                if m_promo and lineas:
                    descuento = self._convertir_importe(m_promo.group(1))
                    lineas[-1]['importe_iva_inc'] = round(lineas[-1]['importe_iva_inc'] + descuento, 2)
                i += 1
                continue
            
            # Ignorar líneas no relevantes
            if any(x in linea for x in skip_words):
                i += 1
                continue
            
            # Patrón granel: CANT DESC PRECIO_UD IMPORTE
            m_granel = re.match(r'^([\d.,]+)\s+(.+?)\s+([\d.,]+)\s+([\d.,]+)$', linea)
            if m_granel:
                cant, desc, precio_ud, importe = m_granel.groups()
                cantidad = self._convertir_importe(cant)
                importe_con_iva = self._convertir_importe(importe)
                
                if importe_con_iva > 0 and len(desc) > 2 and '%' not in desc:
                    lineas.append({
                        'articulo': desc.strip()[:50],
                        'cantidad': cantidad,
                        'precio_ud': self._convertir_importe(precio_ud),
                        'importe_iva_inc': importe_con_iva
                        # Sin 'iva', 'base', 'categoria' - los asigna main.py
                    })
                i += 1
                continue
            
            # Patrón normal: CANT DESC IMPORTE
            m_normal = re.match(r'^(\d+)\s+(.+?)\s+([\d.,]+)$', linea)
            if m_normal:
                cant, desc, importe = m_normal.groups()
                cantidad = int(cant)
                importe_con_iva = self._convertir_importe(importe)
                
                if '%' not in desc and importe_con_iva > 0 and len(desc) > 2:
                    desc = re.sub(r'\s*\*\s*$', '', desc).strip()
                    lineas.append({
                        'articulo': desc[:50],
                        'cantidad': cantidad,
                        'precio_ud': round(importe_con_iva / cantidad, 2) if cantidad > 0 else importe_con_iva,
                        'importe_iva_inc': importe_con_iva
                    })
                i += 1
                continue
            
            # Patrón sin cantidad: DESC IMPORTE (una sola unidad)
            m_simple = re.match(r'^([A-Za-zÁÉÍÓÚÑáéíóúñ\s\-]+?)\s+(\d+[.,]\d{2})$', linea)
            if m_simple:
                desc, importe = m_simple.groups()
                importe_con_iva = self._convertir_importe(importe)
                
                if importe_con_iva > 0 and len(desc.strip()) > 2:
                    lineas.append({
                        'articulo': desc.strip()[:50],
                        'cantidad': 1,
                        'precio_ud': importe_con_iva,
                        'importe_iva_inc': importe_con_iva
                    })
                i += 1
                continue
            
            i += 1
        
        return lineas
    
    def extraer_total(self, texto: str) -> Optional[float]:
        """Extrae total del ticket."""
        m = re.search(r'TOTAL COMPRA[^\d]*(\d+[.,]\d{2})', texto)
        if m:
            return self._convertir_importe(m.group(1))
        
        m2 = re.search(r'TOTAL COMPRA \(iva incl\.\)\s*(\d+[.,]\d{2})', texto)
        if m2:
            return self._convertir_importe(m2.group(1))
        
        return None
    
    def extraer_fecha(self, texto: str) -> Optional[str]:
        """Extrae fecha del ticket en formato DD-MM-YY."""
        m = re.search(r'(\d{2})[/-](\d{2})[/-](\d{2})\s', texto)
        if m:
            dia, mes, ano = m.groups()
            return f"{dia}-{mes}-{ano}"
        return None
    
    def extraer_numero_factura(self, texto: str) -> Optional[str]:
        """Extrae número de factura."""
        m = re.search(r'Datos FACTURA:\s*(\S+)', texto)
        if m:
            return m.group(1)
        m2 = re.search(r'FACTURA SIMPLIFICADA:\s*(\S+)', texto)
        if m2:
            return m2.group(1)
        return None
    
    extraer_referencia = extraer_numero_factura
