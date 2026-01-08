#!/usr/bin/env python3
"""
IDENTIFICADOR DE PROVEEDORES v1.0
=================================
Módulo inteligente para identificar y normalizar nombres de proveedores.

Características:
- Parseo robusto de nombres de archivo (todos los formatos)
- Identificación por CIF (prioridad 1)
- Fuzzy matching contra lista maestra (prioridad 2)
- Generación automática de alias
- Compatible con ALIAS_DICCIONARIO existente

Autor: Claude (Anthropic)
Fecha: 04/01/2026
"""

import re
from difflib import SequenceMatcher
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import unicodedata

# ============================================================================
# CONFIGURACIÓN
# ============================================================================

# Umbral de similitud para fuzzy matching (0.0 - 1.0)
# 0.70 = moderado-agresivo (recomendado para typos)
UMBRAL_SIMILITUD = 0.70

# Umbral alto para match automático sin revisión
UMBRAL_SIMILITUD_ALTO = 0.85

# Prefijos comunes a eliminar del nombre del proveedor
PREFIJOS_ELIMINAR = [
    'BODEGA', 'BODEGAS', 'COOPERATIVA', 'COOP', 'SOCIEDAD',
    'DISTRIBUCIONES', 'DISTRIBUIDORA', 'COMERCIAL',
    'INDUSTRIAS', 'PRODUCTOS', 'CONSERVAS', 'EMBUTIDOS',
    'QUESERIA', 'QUESOS', 'CARNICAS', 'PANADERIA',
    'EMPRESA', 'GRUPO', 'COMPAÑIA', 'CIA'
]

# Sufijos comunes a eliminar
SUFIJOS_ELIMINAR = [
    'SL', 'SLU', 'SA', 'SAU', 'SLL', 'SCOOP', 'SC', 'CB',
    'COOP', 'SOCIEDAD COOPERATIVA', 'LIMITADA', 'ANONIMA',
    'AND', 'ANDALUCIA', 'MADRID', 'ESPAÑA'
]

# Formas de pago válidas (para detectar fin del nombre proveedor)
FORMAS_PAGO = ['TF', 'RC', 'REC', 'TJ', 'EF', 'TR', 'EG']

# Palabras a ignorar en comparaciones
STOPWORDS = ['DE', 'DEL', 'LA', 'LAS', 'LOS', 'EL', 'Y', 'E', 'EN', 'CON', 'SIN', 'POR', 'PARA']


# ============================================================================
# CLASE: ListaMaestraProveedores
# ============================================================================

class ListaMaestraProveedores:
    """
    Gestiona la lista maestra de proveedores con CIF y alias.
    """
    
    def __init__(self):
        self.proveedores: Dict[str, dict] = {}  # nombre_canonico -> {cif, iban, ...}
        self.indice_cif: Dict[str, str] = {}    # cif -> nombre_canonico
        self.alias: Dict[str, str] = {}          # alias -> nombre_canonico
        self.alias_generados: Dict[str, str] = {} # nuevos alias detectados
    
    def cargar_desde_excel(self, ruta: str):
        """Carga proveedores desde EXTRACTORES_COMPLETO.xlsx"""
        import pandas as pd
        
        df = pd.read_excel(ruta)
        
        for _, row in df.iterrows():
            nombre = str(row.get('PROVEEDOR', '')).strip().upper()
            if not nombre:
                continue
            
            cif = str(row.get('CIF', '')).strip().upper()
            cif = cif if cif and cif != 'NAN' else None
            
            iban = str(row.get('IBAN', '')).strip()
            iban = iban if iban and iban != 'NAN' else None
            
            self.proveedores[nombre] = {
                'cif': cif,
                'iban': iban,
                'forma_pago': row.get('FORMA_PAGO'),
                'tiene_extractor': row.get('TIENE_EXTRACTOR') == 'SI',
            }
            
            # Indexar por CIF
            if cif:
                self.indice_cif[cif] = nombre
                # También sin guiones/espacios
                cif_limpio = re.sub(r'[\s\-]', '', cif)
                self.indice_cif[cif_limpio] = nombre
        
        print(f"[ListaMaestra] Cargados {len(self.proveedores)} proveedores, {len(self.indice_cif)} CIFs indexados")
    
    def cargar_alias_existentes(self, alias_dict: dict):
        """Carga alias del ALIAS_DICCIONARIO existente"""
        for alias, canonico in alias_dict.items():
            self.alias[alias.upper()] = canonico.upper()
        print(f"[ListaMaestra] Cargados {len(self.alias)} alias existentes")
    
    def agregar_alias(self, alias: str, canonico: str, auto_generado: bool = False):
        """Agrega un nuevo alias"""
        alias = alias.upper().strip()
        canonico = canonico.upper().strip()
        
        if auto_generado:
            self.alias_generados[alias] = canonico
        else:
            self.alias[alias] = canonico
    
    def buscar_por_cif(self, cif: str) -> Optional[str]:
        """Busca proveedor por CIF"""
        if not cif:
            return None
        
        cif = cif.upper().strip()
        cif_limpio = re.sub(r'[\s\-]', '', cif)
        
        return self.indice_cif.get(cif) or self.indice_cif.get(cif_limpio)
    
    def buscar_por_nombre(self, nombre: str) -> Tuple[Optional[str], float, str]:
        """
        Busca proveedor por nombre con fuzzy matching.
        
        Returns:
            (nombre_canonico, similitud, metodo)
            metodo: 'EXACTO', 'ALIAS', 'FUZZY_XX%', 'NO_MATCH'
        """
        if not nombre:
            return None, 0.0, 'NO_MATCH'
        
        nombre = nombre.upper().strip()
        
        # 1. Match exacto en proveedores
        if nombre in self.proveedores:
            return nombre, 1.0, 'EXACTO'
        
        # 2. Match en alias existentes
        if nombre in self.alias:
            return self.alias[nombre], 1.0, 'ALIAS'
        
        # 3. Match en alias generados
        if nombre in self.alias_generados:
            return self.alias_generados[nombre], 0.95, 'ALIAS_AUTO'
        
        # 4. Fuzzy matching contra proveedores
        mejor_match = None
        mejor_similitud = 0.0
        
        nombre_normalizado = normalizar_para_comparacion(nombre)
        
        for prov in self.proveedores.keys():
            prov_normalizado = normalizar_para_comparacion(prov)
            
            # Similitud directa
            sim = SequenceMatcher(None, nombre_normalizado, prov_normalizado).ratio()
            
            # Bonus si contiene el nombre del proveedor
            if prov_normalizado in nombre_normalizado or nombre_normalizado in prov_normalizado:
                sim = max(sim, 0.85)
            
            if sim > mejor_similitud:
                mejor_similitud = sim
                mejor_match = prov
        
        # 5. Fuzzy matching contra alias
        for alias, canonico in {**self.alias, **self.alias_generados}.items():
            alias_normalizado = normalizar_para_comparacion(alias)
            sim = SequenceMatcher(None, nombre_normalizado, alias_normalizado).ratio()
            
            if sim > mejor_similitud:
                mejor_similitud = sim
                mejor_match = canonico
        
        if mejor_similitud >= UMBRAL_SIMILITUD:
            metodo = f'FUZZY_{int(mejor_similitud * 100)}%'
            
            # Auto-generar alias si es match alto
            if mejor_similitud >= UMBRAL_SIMILITUD_ALTO and nombre != mejor_match:
                self.agregar_alias(nombre, mejor_match, auto_generado=True)
            
            return mejor_match, mejor_similitud, metodo
        
        return None, mejor_similitud, 'NO_MATCH'
    
    def exportar_alias_generados(self) -> str:
        """Exporta los alias generados en formato Python para añadir a ALIAS_DICCIONARIO"""
        if not self.alias_generados:
            return "# No se generaron nuevos alias"
        
        lines = ["# ========== ALIAS AUTO-GENERADOS =========="]
        
        # Agrupar por proveedor canónico
        por_canonico = {}
        for alias, canonico in sorted(self.alias_generados.items()):
            if canonico not in por_canonico:
                por_canonico[canonico] = []
            por_canonico[canonico].append(alias)
        
        for canonico, aliases in sorted(por_canonico.items()):
            lines.append(f"    # {canonico}")
            for alias in aliases:
                lines.append(f"    '{alias}': '{canonico}',")
        
        return '\n'.join(lines)


# ============================================================================
# FUNCIONES DE NORMALIZACIÓN
# ============================================================================

def quitar_tildes(texto: str) -> str:
    """Elimina tildes y diacríticos"""
    return ''.join(
        c for c in unicodedata.normalize('NFD', texto)
        if unicodedata.category(c) != 'Mn'
    )

def normalizar_para_comparacion(nombre: str) -> str:
    """
    Normaliza un nombre para comparación fuzzy.
    Elimina prefijos, sufijos, stopwords y caracteres especiales.
    """
    if not nombre:
        return ""
    
    nombre = nombre.upper().strip()
    nombre = quitar_tildes(nombre)
    
    # Eliminar caracteres especiales
    nombre = re.sub(r'[^\w\s]', ' ', nombre)
    
    palabras = nombre.split()
    
    # Eliminar prefijos
    while palabras and palabras[0] in PREFIJOS_ELIMINAR:
        palabras.pop(0)
    
    # Eliminar sufijos
    while palabras and palabras[-1] in SUFIJOS_ELIMINAR:
        palabras.pop()
    
    # Eliminar stopwords (excepto si es la única palabra)
    if len(palabras) > 1:
        palabras = [p for p in palabras if p not in STOPWORDS]
    
    return ' '.join(palabras)


def parsear_nombre_archivo(nombre_archivo: str) -> dict:
    """
    Parsea el nombre del archivo para extraer información.
    
    Formatos soportados:
    1. "2009 2T25 0512 PROVEEDOR TF.pdf" (numerado)
    2. "2T25 0512 PROVEEDOR TF.pdf" (sin numerar)
    3. "2T 0512 PROVEEDOR TF.pdf" (sin año en trimestre)
    4. "405 ATRASADA 2T25 0512 PROVEEDOR TF.pdf" (atrasada numerada)
    5. "ATRASADA 2T25 0512 PROVEEDOR TF.pdf" (atrasada sin numerar)
    6. "ATRASADA2T25 0512 PROVEEDOR TF.pdf" (atrasada pegada)
    
    Returns:
        {
            'num_gestoria': str or None,
            'trimestre': str or None,
            'fecha': str or None (MMDD),
            'proveedor_crudo': str,
            'forma_pago': str or None,
            'es_atrasada': bool
        }
    """
    resultado = {
        'num_gestoria': None,
        'trimestre': None,
        'fecha': None,
        'proveedor_crudo': '',
        'forma_pago': None,
        'es_atrasada': False
    }
    
    # Quitar extensión
    nombre = re.sub(r'\.(pdf|jpg|jpeg|png)$', '', nombre_archivo, flags=re.IGNORECASE)
    nombre = nombre.strip()
    original = nombre
    
    # Detectar y quitar forma de pago al final
    forma_pago_pattern = r'\s+(' + '|'.join(FORMAS_PAGO) + r')(\s*\d*)?$'
    match_pago = re.search(forma_pago_pattern, nombre, re.IGNORECASE)
    if match_pago:
        resultado['forma_pago'] = match_pago.group(1).upper()
        # Normalizar REC -> RC
        if resultado['forma_pago'] == 'REC':
            resultado['forma_pago'] = 'RC'
        nombre = nombre[:match_pago.start()].strip()
    
    # Detectar ATRASADA
    if 'ATRASADA' in nombre.upper():
        resultado['es_atrasada'] = True
        # Quitar ATRASADA (puede estar pegada al trimestre)
        nombre = re.sub(r'ATRASADA\s*', '', nombre, flags=re.IGNORECASE)
    
    # CASO 0: Formato especial con DOS números antes del trimestre
    # "2001 1251 1T25 0311 PROVEEDOR" (número interno + número gestoría + trimestre + fecha)
    match = re.match(r'^(\d{3,4})\s+(\d{3,4})\s+(\d[TQ]\d{0,2})\s+(\d{4})\s+(.+)$', nombre, re.IGNORECASE)
    if match:
        resultado['num_gestoria'] = match.group(1)  # Usar el primero como gestoría
        resultado['trimestre'] = match.group(3).upper()
        resultado['fecha'] = match.group(4)
        resultado['proveedor_crudo'] = match.group(5).strip()
        return resultado
    
    # CASO 1: Empieza con número de gestoría (3-4 dígitos) seguido de trimestre
    # "2009 2T25 0512 PROVEEDOR" o "405 2T25 0512 PROVEEDOR"
    match = re.match(r'^(\d{3,4})\s+(\d[TQ]\d{0,2})\s+(\d{4})\s+(.+)$', nombre, re.IGNORECASE)
    if match:
        resultado['num_gestoria'] = match.group(1)
        resultado['trimestre'] = match.group(2).upper()
        resultado['fecha'] = match.group(3)
        resultado['proveedor_crudo'] = match.group(4).strip()
        return resultado
    
    # CASO 2: Empieza con trimestre (sin número gestoría)
    # "2T25 0512 PROVEEDOR" o "2T 0512 PROVEEDOR"
    match = re.match(r'^(\d[TQ]\d{0,2})\s+(\d{4})\s+(.+)$', nombre, re.IGNORECASE)
    if match:
        resultado['trimestre'] = match.group(1).upper()
        resultado['fecha'] = match.group(2)
        resultado['proveedor_crudo'] = match.group(3).strip()
        return resultado
    
    # CASO 3: Solo número gestoría y fecha (sin trimestre explícito)
    # "2009 0512 PROVEEDOR"
    match = re.match(r'^(\d{3,4})\s+(\d{4})\s+(.+)$', nombre)
    if match:
        resultado['num_gestoria'] = match.group(1)
        resultado['fecha'] = match.group(2)
        resultado['proveedor_crudo'] = match.group(3).strip()
        return resultado
    
    # CASO 4: Solo fecha y proveedor
    # "0512 PROVEEDOR"
    match = re.match(r'^(\d{4})\s+(.+)$', nombre)
    if match:
        resultado['fecha'] = match.group(1)
        resultado['proveedor_crudo'] = match.group(2).strip()
        return resultado
    
    # CASO 5: No hay patrón reconocible, usar todo como proveedor
    resultado['proveedor_crudo'] = nombre
    
    return resultado


def limpiar_nombre_proveedor(nombre_crudo: str) -> str:
    """
    Limpia el nombre crudo del proveedor extraído del archivo.
    
    Elimina:
    - Prefijos tipo BODEGA, BODEGAS, COOP, etc.
    - Sufijos tipo SL, SA, COOP, etc.
    - Números residuales
    - Formas de pago residuales
    """
    if not nombre_crudo:
        return ""
    
    nombre = nombre_crudo.upper().strip()
    
    # Quitar formas de pago que pudieran quedar
    for fp in FORMAS_PAGO:
        nombre = re.sub(rf'\b{fp}\b', '', nombre)
    
    # Quitar números sueltos al final (ej: " 2", " 3")
    nombre = re.sub(r'\s+\d+$', '', nombre)
    
    # Quitar sufijos empresariales
    for sufijo in SUFIJOS_ELIMINAR:
        nombre = re.sub(rf'\b{sufijo}\b\.?', '', nombre, flags=re.IGNORECASE)
    
    # Limpiar espacios múltiples
    nombre = re.sub(r'\s+', ' ', nombre).strip()
    
    return nombre


# ============================================================================
# CLASE: IdentificadorProveedor
# ============================================================================

class IdentificadorProveedor:
    """
    Clase principal para identificar proveedores a partir de archivos.
    """
    
    def __init__(self, lista_maestra: ListaMaestraProveedores):
        self.lista_maestra = lista_maestra
        self.cache_identificaciones: Dict[str, dict] = {}
        self.pendientes: List[dict] = []  # Proveedores no identificados
    
    def identificar(self, nombre_archivo: str, cif_pdf: str = None) -> dict:
        """
        Identifica el proveedor de una factura.
        
        Args:
            nombre_archivo: Nombre del archivo PDF
            cif_pdf: CIF extraído del contenido del PDF (opcional)
        
        Returns:
            {
                'proveedor_canonico': str,
                'proveedor_crudo': str,
                'metodo': str,  # 'CIF', 'EXACTO', 'ALIAS', 'FUZZY_XX%', 'PENDIENTE'
                'similitud': float,
                'num_gestoria': str or None,
                'trimestre': str or None,
                'fecha': str or None,
                'forma_pago': str or None,
                'es_atrasada': bool
            }
        """
        # Cache
        cache_key = f"{nombre_archivo}|{cif_pdf or ''}"
        if cache_key in self.cache_identificaciones:
            return self.cache_identificaciones[cache_key]
        
        # Parsear nombre archivo
        info = parsear_nombre_archivo(nombre_archivo)
        
        resultado = {
            'proveedor_canonico': None,
            'proveedor_crudo': info['proveedor_crudo'],
            'metodo': 'PENDIENTE',
            'similitud': 0.0,
            'num_gestoria': info['num_gestoria'],
            'trimestre': info['trimestre'],
            'fecha': info['fecha'],
            'forma_pago': info['forma_pago'],
            'es_atrasada': info['es_atrasada']
        }
        
        # PASO 1: Buscar por CIF del PDF
        if cif_pdf:
            canonico = self.lista_maestra.buscar_por_cif(cif_pdf)
            if canonico:
                resultado['proveedor_canonico'] = canonico
                resultado['metodo'] = 'CIF'
                resultado['similitud'] = 1.0
                self.cache_identificaciones[cache_key] = resultado
                return resultado
        
        # PASO 2: Limpiar nombre crudo
        nombre_limpio = limpiar_nombre_proveedor(info['proveedor_crudo'])
        
        # PASO 3: Buscar en lista maestra
        canonico, similitud, metodo = self.lista_maestra.buscar_por_nombre(nombre_limpio)
        
        if canonico:
            resultado['proveedor_canonico'] = canonico
            resultado['metodo'] = metodo
            resultado['similitud'] = similitud
        else:
            # PASO 4: Intentar con el nombre crudo completo
            canonico, similitud, metodo = self.lista_maestra.buscar_por_nombre(info['proveedor_crudo'])
            
            if canonico:
                resultado['proveedor_canonico'] = canonico
                resultado['metodo'] = metodo
                resultado['similitud'] = similitud
            else:
                # No se pudo identificar
                resultado['proveedor_canonico'] = f"PENDIENTE: {nombre_limpio}"
                resultado['metodo'] = 'PENDIENTE'
                resultado['similitud'] = similitud
                
                self.pendientes.append({
                    'archivo': nombre_archivo,
                    'nombre_crudo': info['proveedor_crudo'],
                    'nombre_limpio': nombre_limpio,
                    'mejor_similitud': similitud
                })
        
        self.cache_identificaciones[cache_key] = resultado
        return resultado
    
    def generar_reporte(self) -> str:
        """Genera reporte de identificación"""
        lines = []
        lines.append("=" * 70)
        lines.append("REPORTE DE IDENTIFICACIÓN DE PROVEEDORES")
        lines.append("=" * 70)
        
        # Estadísticas
        total = len(self.cache_identificaciones)
        por_metodo = {}
        for r in self.cache_identificaciones.values():
            metodo = r['metodo'].split('_')[0]  # FUZZY_85% -> FUZZY
            por_metodo[metodo] = por_metodo.get(metodo, 0) + 1
        
        lines.append(f"\nTotal procesados: {total}")
        for metodo, count in sorted(por_metodo.items()):
            pct = 100 * count / total if total > 0 else 0
            lines.append(f"  {metodo}: {count} ({pct:.1f}%)")
        
        # Pendientes
        if self.pendientes:
            lines.append(f"\n{'=' * 70}")
            lines.append(f"PENDIENTES DE REVISIÓN ({len(self.pendientes)}):")
            lines.append("-" * 70)
            for p in self.pendientes:
                lines.append(f"  Archivo: {p['archivo'][:50]}")
                lines.append(f"    Crudo: {p['nombre_crudo']}")
                lines.append(f"    Limpio: {p['nombre_limpio']}")
                lines.append(f"    Mejor similitud: {p['mejor_similitud']:.0%}")
                lines.append("")
        
        # Alias generados
        alias_gen = self.lista_maestra.exportar_alias_generados()
        if 'No se generaron' not in alias_gen:
            lines.append(f"\n{'=' * 70}")
            lines.append("ALIAS AUTO-GENERADOS (añadir a ALIAS_DICCIONARIO):")
            lines.append("-" * 70)
            lines.append(alias_gen)
        
        return '\n'.join(lines)


# ============================================================================
# FUNCIÓN DE CONVENIENCIA
# ============================================================================

def crear_identificador(ruta_lista_maestra: str, alias_existentes: dict = None) -> IdentificadorProveedor:
    """
    Crea un identificador configurado.
    
    Args:
        ruta_lista_maestra: Ruta a EXTRACTORES_COMPLETO.xlsx
        alias_existentes: ALIAS_DICCIONARIO del main.py (opcional)
    
    Returns:
        IdentificadorProveedor configurado
    """
    lista = ListaMaestraProveedores()
    lista.cargar_desde_excel(ruta_lista_maestra)
    
    if alias_existentes:
        lista.cargar_alias_existentes(alias_existentes)
    
    return IdentificadorProveedor(lista)


# ============================================================================
# TEST
# ============================================================================

if __name__ == '__main__':
    # Test del parser de nombres
    test_archivos = [
        "2009 2T25 0512 BODEGA VIRGEN DE LA SIERRA COOP REC.pdf",
        "1033 1T25 0123 VIRGEN DE LA SIERRA TF.pdf",
        "2T25 0512 VIRGEN DE LA SIERA TF.pdf",  # typo
        "2T 0512 BODEGA VIRGEN DE LA SIERRA COOP RC.pdf",
        "405 ATRASADA 2T25 0512 BODEGAS VIRGEN SIERRA REC.pdf",
        "ATRASADA 2T25 0512 VIRGEN SIERRA TJ.pdf",
        "ATRASADA2T25 0512 COOPERATIVA VIRGEN DE LA SIERRA EF.pdf",
        "3090 3T25 0915 BODEGAS VIRGEN DE LA SIERRA RC.pdf",
    ]
    
    print("=" * 70)
    print("TEST: Parseo de nombres de archivo")
    print("=" * 70)
    
    for archivo in test_archivos:
        info = parsear_nombre_archivo(archivo)
        limpio = limpiar_nombre_proveedor(info['proveedor_crudo'])
        print(f"\nArchivo: {archivo}")
        print(f"  Num Gestoría: {info['num_gestoria']}")
        print(f"  Trimestre: {info['trimestre']}")
        print(f"  Fecha: {info['fecha']}")
        print(f"  Forma Pago: {info['forma_pago']}")
        print(f"  Atrasada: {info['es_atrasada']}")
        print(f"  Proveedor crudo: {info['proveedor_crudo']}")
        print(f"  Proveedor limpio: {limpio}")
