"""
Extractor para DISTRIBUCIONES LAVAPIES S.COOP.MAD.

Distribuidor de bebidas en Madrid.
CIF: F88424072
IBAN: ES39 3035 0376 14 3760011213

Productos (IVA según diccionario - PUEDE VARIAR EN FACTURA):
- AGUVIC: AGUA VICHY CATALAN → AGUA CON GAS (10%)
- ZULINMA/ZULINPE/ZULINTO: ZUMOS LINDA → ZUMOS (10%)
- REFSIFG/REFSIFT: SIFONES → SIFON (10%)
- ZUMMOG1: MOSTO GREIP → MOSTO (21%)
- REFCAS1: GASEOSA CASERA → GASEOSA (21%)
- REFREV2: REVOLTOSA LIMON → REFRESCO DE LIMON (21%)
- REFFRIX: FRIXEN COLA → REFRESCO DE COLA (21%)
- PALESZE/PALESCO: PALESTINA → REFRESCO DE COLA (21%)
- REFCOZ2: COCA-COLA ZERO → REFRESCO DE COLA (21%)
- SCHT15: SCHWEPPES TÓNICA → TONICA (21%)
- REFSEV: SEVEN UP → REFRESCO DE LIMON (21%)

⚠️ IMPORTANTE: Este proveedor tiene errores frecuentes en la asignación de IVA.
El extractor deduce el IVA de cada producto según las bases de la factura,
NO según el diccionario. Se genera un aviso cuando hay discrepancia.

Creado: 30/12/2025
"""
from extractores.base import ExtractorBase
from extractores import registrar
from typing import List, Dict, Optional, Set, Tuple
import re
from itertools import combinations


@registrar('DISTRIBUCIONES LAVAPIES', 'LAVAPIES', 'DIST LAVAPIES', 'DISTRIB LAVAPIES')
class ExtractorLavapies(ExtractorBase):
    """Extractor para facturas de DISTRIBUCIONES LAVAPIES."""
    
    nombre = 'DISTRIBUCIONES LAVAPIES'
    cif = 'F88424072'
    iban = 'ES39 3035 0376 14 3760011213'
    metodo_pdf = 'pdfplumber'
    
    # IVA esperado según diccionario (para avisos)
    IVA_ESPERADO = {
        'AGUVIC': 10, 'ZULINMA': 10, 'ZULINPE': 10, 'ZULINTO': 10,
        'REFSIFG': 10, 'REFSIFT': 10,
        'ZUMMOG1': 21, 'REFCAS1': 21, 'REFREV2': 21, 'REFFRIX': 21,
        'PALESZE': 21, 'PALESCO': 21, 'REFCOZ2': 21, 'SCHT15': 21, 'REFSEV': 21,
    }
    
    # Categorías por referencia
    CATEGORIAS = {
        'AGUVIC': 'AGUA CON GAS',
        'ZULINMA': 'ZUMOS',
        'ZULINPE': 'ZUMOS',
        'ZULINTO': 'ZUMOS',
        'REFSIFG': 'SIFON',
        'REFSIFT': 'SIFON',
        'ZUMMOG1': 'MOSTO',
        'REFCAS1': 'GASEOSA',
        'REFREV2': 'REFRESCO DE LIMON',
        'REFFRIX': 'REFRESCO DE COLA',
        'PALESZE': 'REFRESCO DE COLA',
        'PALESCO': 'REFRESCO DE COLA',
        'REFCOZ2': 'REFRESCO DE COLA',
        'SCHT15': 'TONICA',
        'REFSEV': 'REFRESCO DE LIMON',
    }
    
    def extraer_lineas(self, texto: str) -> List[Dict]:
        """
        Extrae líneas de productos.
        
        El IVA de cada producto se deduce de las bases de la factura,
        usando un algoritmo de subset-sum para determinar qué productos
        corresponden a cada base imponible.
        """
        # Extraer productos
        patron = re.compile(
            r'(\d+/\d+)\s+'      # Nº Albarán
            r'(\w+)\s+'           # Referencia
            r'(.+?)\s+'           # Descripción
            r'(\d+)\s+'           # Cantidad
            r'([\d,]+)\s+'        # Precio
            r'([\d,]+)\s*€'       # Importe
        )
        
        productos = []
        for m in patron.finditer(texto):
            productos.append({
                'albaran': m.group(1),
                'ref': m.group(2),
                'descripcion': m.group(3).strip(),
                'cantidad': int(m.group(4)),
                'precio_ud': self._convertir_europeo(m.group(5)),
                'base': self._convertir_europeo(m.group(6)),
            })
        
        # Extraer bases imponibles de la factura
        base21_fact = self._extraer_valor(texto, r'BASE IMP\. AL 21%\s+([\d,]+)')
        base10_fact = self._extraer_valor(texto, r'BASE IMP\. AL 10%\s+([\d,]+)')
        
        # Deducir IVA de cada producto según las bases
        importes = [p['base'] for p in productos]
        indices_21 = self._encontrar_subset_suma(importes, base21_fact)
        
        lineas = []
        avisos = []
        
        for i, p in enumerate(productos):
            # Asignar IVA según la factura
            if indices_21 and i in indices_21:
                iva_factura = 21
            else:
                iva_factura = 10
            
            # Obtener categoría
            categoria = self.CATEGORIAS.get(p['ref'], 'BEBIDAS')
            
            # Verificar discrepancia con IVA esperado
            iva_esperado = self.IVA_ESPERADO.get(p['ref'])
            if iva_esperado and iva_esperado != iva_factura:
                avisos.append(
                    f"IVA incorrecto: {p['ref']} ({p['descripcion'][:25]}) "
                    f"factura={iva_factura}% vs esperado={iva_esperado}%"
                )
            
            lineas.append({
                'codigo': p['ref'],
                'articulo': p['descripcion'][:50],
                'cantidad': p['cantidad'],
                'precio_ud': round(p['precio_ud'], 2),
                'iva': iva_factura,
                'base': round(p['base'], 2),
                'categoria': categoria,
                'albaran': p['albaran'],
            })
        
        # Guardar avisos para logging
        if avisos:
            self._avisos_iva = avisos
        
        return lineas
    
    def _encontrar_subset_suma(self, importes: List[float], objetivo: float, 
                                tolerancia: float = 0.02) -> Optional[Set[int]]:
        """
        Encuentra qué índices de productos suman aproximadamente el objetivo.
        Usa fuerza bruta (OK para <20 productos).
        """
        if not objetivo or objetivo <= 0:
            return set()
        
        n = len(importes)
        mejor_diff = float('inf')
        mejor_indices = None
        
        for r in range(n + 1):
            for combo in combinations(range(n), r):
                suma = sum(importes[i] for i in combo)
                diff = abs(suma - objetivo)
                if diff < mejor_diff:
                    mejor_diff = diff
                    mejor_indices = set(combo)
                    if diff < tolerancia:
                        return mejor_indices
        
        return mejor_indices if mejor_diff < 1.0 else None
    
    def _extraer_valor(self, texto: str, patron: str) -> float:
        """Extrae un valor numérico usando un patrón regex."""
        m = re.search(patron, texto)
        if m:
            return self._convertir_europeo(m.group(1))
        return 0.0
    
    def _convertir_europeo(self, texto: str) -> float:
        """Convierte formato europeo a float."""
        if not texto:
            return 0.0
        texto = texto.strip().replace('€', '').replace(' ', '')
        texto = texto.replace('.', '').replace(',', '.')
        try:
            return float(texto)
        except:
            return 0.0
    
    def extraer_total(self, texto: str) -> Optional[float]:
        """
        Extrae total de la factura.
        Usa los valores de IVA directamente de la factura (no calcula).
        """
        # Extraer bases e IVAs de la factura
        m_21 = re.search(r'BASE IMP\. AL 21%\s+([\d,]+)\s+IVA 21%\s+([\d,]+)', texto)
        m_10 = re.search(r'BASE IMP\. AL 10%\s+([\d,]+)\s+IVA 10%\s+([\d,]+)', texto)
        
        base21 = self._convertir_europeo(m_21.group(1)) if m_21 else 0
        iva21 = self._convertir_europeo(m_21.group(2)) if m_21 else 0
        base10 = self._convertir_europeo(m_10.group(1)) if m_10 else 0
        iva10 = self._convertir_europeo(m_10.group(2)) if m_10 else 0
        
        # Total = suma de bases + IVAs (usando valores de factura)
        return round(base21 + iva21 + base10 + iva10, 2)
    
    def extraer_fecha(self, texto: str) -> Optional[str]:
        """Extrae fecha de la factura."""
        # Formato: "30/12/25" después de FECHA
        m = re.search(r'(\d{2}/\d{2}/\d{2})\s+\d{6}', texto)
        if m:
            fecha = m.group(1)
            partes = fecha.split('/')
            if len(partes[2]) == 2:
                partes[2] = '20' + partes[2]
            return '/'.join(partes)
        return None
    
    def extraer_numero_factura(self, texto: str) -> Optional[str]:
        """Extrae número de factura."""
        # Formato: "Nº DOCUMENTO" seguido de fecha y número
        m = re.search(r'(\d{2}/\d{2}/\d{2})\s+(\d{6})', texto)
        if m:
            return m.group(2)
        return None
    
    extraer_referencia = extraer_numero_factura
    
    def get_avisos_iva(self) -> List[str]:
        """Devuelve avisos de discrepancia de IVA de la última extracción."""
        return getattr(self, '_avisos_iva', [])
