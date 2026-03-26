"""
Módulo de generación de Excel.

Genera archivos Excel con las facturas procesadas.

CAMBIOS v5.12 (18/01/2026):
- Nueva columna EXTRACTOR en hoja Lineas (nombre.py + método)
- Nueva función generar_nombre_salida_inteligente()
- Nombre archivo: carpeta_v1.xlsx o carpeta_v1_HHMM.xlsx si existe

CAMBIOS v5.11 (18/01/2026):
- Cabeceras Facturas: #, ARCHIVO, CUENTA, Fec.Fac., TITULO, REF, TOTAL FACTURA, Total Parseo, OBSERVACIONES
- CUENTA desde MAESTRO_PROVEEDORES.xlsx (matching 3 niveles: exacto → alias → similitud 70%)
- Nueva columna "Total Parseo" = suma de líneas parseadas
- Ruta MAESTRO: C:\\_ARCHIVOS\\TRABAJO\\Facturas\\gestion-facturas\\datos\\MAESTRO_PROVEEDORES.xlsx

CAMBIOS v5.9 (02/01/2026):
- FIX: Sanitización de caracteres ilegales para Excel (IllegalCharacterError)
- Función sanitizar_para_excel() elimina caracteres de control

CAMBIOS v5.8 (02/01/2026):
- Nueva hoja "Facturas" con cabeceras (una fila por factura)
- Hoja "Lineas" renombrada (antes "Facturas")
- Integración con DiccionarioEmisorTitulo.xlsx para CUENTA y TITULO
- Auto-numeración TMP001, TMP002... para facturas sin número de gestoría
"""
import pandas as pd
from pathlib import Path
from typing import List, Dict, Tuple, Optional, TYPE_CHECKING
from datetime import datetime
from difflib import SequenceMatcher
import re

if TYPE_CHECKING:
    from nucleo.factura import Factura


def _verificar_archivo_no_abierto(ruta) -> bool:
    """Comprueba que el archivo Excel no esté abierto. Devuelve True si está libre.

    Método: rename temporal (más fiable que open('a') en Windows con Excel).
    """
    ruta = Path(ruta)
    if not ruta.exists():
        return True
    try:
        tmp = ruta.with_suffix(ruta.suffix + ".check_lock")
        ruta.rename(tmp)
        tmp.rename(ruta)
        return True
    except (PermissionError, OSError):
        print(f"  ERROR: El archivo '{ruta.name}' está abierto en Excel. Ciérralo y reintenta.")
        return False


# ==============================================================================
# GENERACIÓN DE NOMBRE DE SALIDA INTELIGENTE (v5.12)
# ==============================================================================

def generar_nombre_salida_inteligente(carpeta_entrada: Path, outputs_dir: Path) -> Path:
    """
    Genera nombre de archivo de salida inteligente basado en la carpeta de entrada.
    
    Reglas:
    - Carpeta normal (ej: "4 TRI 2025") → "4_TRI_2025_v1.xlsx"
    - Carpeta ATRASADAS dentro de trimestre → "4_TRI_2025_ATRASADAS_v1.xlsx"
    - Carpeta ATRASADAS suelta → "ATRASADAS_v1.xlsx"
    - Si v1 existe → añadir timestamp: "4_TRI_2025_v1_1430.xlsx"
    
    Args:
        carpeta_entrada: Path de la carpeta con las facturas
        outputs_dir: Path del directorio de salida
        
    Returns:
        Path completo del archivo de salida
    """
    # Obtener nombre de la carpeta
    nombre_carpeta = carpeta_entrada.name
    
    # Verificar si es ATRASADAS dentro de un trimestre
    if nombre_carpeta.upper() == 'ATRASADAS':
        carpeta_padre = carpeta_entrada.parent.name
        # Verificar si el padre parece un trimestre
        if re.match(r'^\d\s*T', carpeta_padre, re.IGNORECASE) or 'TRI' in carpeta_padre.upper():
            nombre_base = f"{carpeta_padre}_ATRASADAS"
        else:
            nombre_base = "ATRASADAS"
    else:
        nombre_base = nombre_carpeta
    
    # Normalizar: espacios a guiones bajos
    nombre_base = nombre_base.replace(' ', '_')
    
    # Asegurar que outputs existe
    outputs_dir.mkdir(parents=True, exist_ok=True)
    
    # Buscar versión disponible
    nombre_v1 = f"{nombre_base}_v1.xlsx"
    ruta_v1 = outputs_dir / nombre_v1
    
    if not ruta_v1.exists():
        return ruta_v1
    
    # Si v1 existe, añadir timestamp
    timestamp = datetime.now().strftime('%H%M')
    nombre_con_timestamp = f"{nombre_base}_v1_{timestamp}.xlsx"
    return outputs_dir / nombre_con_timestamp


# ==============================================================================
# SANITIZACIÓN DE CARACTERES PARA EXCEL
# ==============================================================================

def sanitizar_para_excel(valor):
    """
    Elimina caracteres ilegales para Excel (caracteres de control).
    
    Excel no acepta caracteres de control (0x00-0x1F) excepto:
    - 0x09 (tab)
    - 0x0A (newline)
    - 0x0D (carriage return)
    
    Args:
        valor: Cualquier valor a sanitizar
        
    Returns:
        Valor sanitizado (string sin caracteres ilegales)
    """
    if valor is None:
        return valor
    if isinstance(valor, str):
        # Elimina caracteres de control excepto tab, newline, carriage return
        return re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', valor)
    return valor


def sanitizar_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Sanitiza todas las columnas de texto de un DataFrame.
    
    Args:
        df: DataFrame a sanitizar
        
    Returns:
        DataFrame con textos sanitizados
    """
    for col in df.select_dtypes(include=['object']).columns:
        df[col] = df[col].apply(sanitizar_para_excel)
    return df


# ==============================================================================
# CONFIGURACIÓN DEL DICCIONARIO DE CUENTAS
# ==============================================================================

# Ruta por defecto al MAESTRO_PROVEEDORES
MAESTRO_PROVEEDORES_DEFAULT = r"C:\_ARCHIVOS\TRABAJO\Facturas\gestion-facturas\datos\MAESTRO_PROVEEDORES.xlsx"

# Caché global para evitar recargar el diccionario en cada llamada
_CACHE_CUENTAS: Dict[str, str] = {}  # PROVEEDOR -> CUENTA
_CACHE_ALIAS: Dict[str, str] = {}     # ALIAS -> PROVEEDOR
_CACHE_CARGADO: bool = False


def cargar_diccionario_cuentas(ruta: Optional[Path] = None) -> Tuple[Dict[str, str], Dict[str, str]]:
    """
    Carga el MAESTRO_PROVEEDORES para obtener CUENTA por proveedor.
    
    Args:
        ruta: Ruta al archivo MAESTRO_PROVEEDORES.xlsx
        
    Returns:
        Tupla (dict_cuentas, dict_alias)
        - dict_cuentas: {PROVEEDOR_NORMALIZADO: CUENTA}
        - dict_alias: {ALIAS_NORMALIZADO: PROVEEDOR}
    """
    global _CACHE_CUENTAS, _CACHE_ALIAS, _CACHE_CARGADO
    
    if _CACHE_CARGADO:
        return _CACHE_CUENTAS, _CACHE_ALIAS
    
    if ruta is None:
        ruta = Path(MAESTRO_PROVEEDORES_DEFAULT)
    
    dict_cuentas = {}
    dict_alias = {}
    
    try:
        # Cargar MAESTRO_PROVEEDORES (Sheet1)
        df = pd.read_excel(ruta, sheet_name='Sheet1')
        
        for _, row in df.iterrows():
            # Obtener CUENTA (puede ser float, convertir a int string)
            cuenta_raw = row.get('CUENTA', '')
            if pd.notna(cuenta_raw):
                cuenta = str(int(float(cuenta_raw)))
            else:
                continue
            
            # Obtener PROVEEDOR
            proveedor = str(row.get('PROVEEDOR', '')).strip().upper()
            if proveedor and cuenta:
                dict_cuentas[proveedor] = cuenta
                # También sin puntuación
                proveedor_limpio = re.sub(r'[.,]', '', proveedor)
                if proveedor_limpio != proveedor:
                    dict_cuentas[proveedor_limpio] = cuenta
            
            # Procesar ALIAS (separados por coma)
            alias_raw = row.get('ALIAS', '')
            if pd.notna(alias_raw) and alias_raw:
                aliases = [a.strip().upper() for a in str(alias_raw).split(',')]
                for alias in aliases:
                    if alias:
                        dict_alias[alias] = proveedor
                        # También sin puntuación
                        alias_limpio = re.sub(r'[.,]', '', alias)
                        if alias_limpio != alias:
                            dict_alias[alias_limpio] = proveedor
        
        _CACHE_CUENTAS = dict_cuentas
        _CACHE_ALIAS = dict_alias
        _CACHE_CARGADO = True
        
        print(f"   MAESTRO_PROVEEDORES: {len(dict_cuentas)} proveedores, {len(dict_alias)} alias")
        
    except Exception as e:
        print(f"[AVISO] No se pudo cargar MAESTRO_PROVEEDORES.xlsx: {e}")
    
    return dict_cuentas, dict_alias


def normalizar_para_busqueda(texto) -> str:
    """
    Normaliza un texto para búsqueda flexible.
    """
    if texto is None or (isinstance(texto, float) and pd.isna(texto)):
        return ''
    texto = str(texto).upper().strip()
    if texto == 'NAN':
        return ''
    # Quitar prefijos comunes de archivos
    texto = re.sub(r'^\d+T\d*\s+\d+\s+', '', texto)  # Quitar "4T25 1001 "
    texto = re.sub(r'^ATRASADA\s+', '', texto)
    # Quitar sufijos de tipo de factura
    texto = re.sub(r'\s+(TF|TJ|RC)\.?PDF$', '', texto, flags=re.IGNORECASE)
    texto = re.sub(r'\s+(TF|TJ|RC)$', '', texto, flags=re.IGNORECASE)
    # Normalizar espacios
    texto = ' '.join(texto.split())
    return texto


def buscar_cuenta_titulo(proveedor: str, ruta_diccionario: Optional[Path] = None) -> Tuple[str, str]:
    """
    Busca la CUENTA y TITULO oficial de un proveedor.
    
    Matching de 3 niveles:
    1. Búsqueda exacta en PROVEEDOR
    2. Búsqueda en ALIAS (separados por coma en MAESTRO)
    3. Búsqueda por similitud (>70%)
    
    Args:
        proveedor: Nombre del proveedor (del extractor o archivo)
        ruta_diccionario: Ruta al MAESTRO_PROVEEDORES (opcional)
        
    Returns:
        Tupla (CUENTA, TITULO) o ('PENDIENTE', proveedor_original) si no encuentra
    """
    dict_cuentas, dict_alias = cargar_diccionario_cuentas(ruta_diccionario)
    
    if not proveedor or (isinstance(proveedor, float) and pd.isna(proveedor)):
        return ('PENDIENTE', '')
    
    proveedor = str(proveedor)
    proveedor_norm = normalizar_para_busqueda(proveedor)
    proveedor_upper = proveedor.upper().strip()
    
    # =========================================================================
    # NIVEL 1: Búsqueda exacta en PROVEEDOR
    # =========================================================================
    if proveedor_upper in dict_cuentas:
        return (dict_cuentas[proveedor_upper], proveedor_upper)
    
    if proveedor_norm in dict_cuentas:
        return (dict_cuentas[proveedor_norm], proveedor_norm)
    
    # =========================================================================
    # NIVEL 2: Búsqueda en ALIAS
    # =========================================================================
    # Búsqueda exacta en alias
    if proveedor_upper in dict_alias:
        titulo = dict_alias[proveedor_upper]
        if titulo in dict_cuentas:
            return (dict_cuentas[titulo], titulo)
    
    if proveedor_norm in dict_alias:
        titulo = dict_alias[proveedor_norm]
        if titulo in dict_cuentas:
            return (dict_cuentas[titulo], titulo)
    
    # Búsqueda parcial en alias (contiene)
    for alias, titulo in dict_alias.items():
        if alias in proveedor_upper or proveedor_upper in alias:
            if titulo in dict_cuentas:
                return (dict_cuentas[titulo], titulo)
    
    # Búsqueda parcial en cuentas (contiene)
    for cliente, cuenta in dict_cuentas.items():
        if cliente in proveedor_upper or proveedor_upper in cliente:
            return (cuenta, cliente)
    
    # =========================================================================
    # NIVEL 3: Búsqueda por similitud (>70%)
    # =========================================================================
    mejor_match = None
    mejor_ratio = 0.0
    
    # Primero en alias
    for alias, titulo in dict_alias.items():
        ratio = SequenceMatcher(None, proveedor_norm, alias).ratio()
        if ratio > mejor_ratio and ratio > 0.70:
            mejor_ratio = ratio
            mejor_match = ('alias', alias, titulo)
    
    # Luego en cuentas
    for cliente, cuenta in dict_cuentas.items():
        ratio = SequenceMatcher(None, proveedor_norm, cliente).ratio()
        if ratio > mejor_ratio and ratio > 0.70:
            mejor_ratio = ratio
            mejor_match = ('cuenta', cliente, cuenta)
    
    if mejor_match:
        if mejor_match[0] == 'alias':
            titulo = mejor_match[2]
            if titulo in dict_cuentas:
                return (dict_cuentas[titulo], titulo)
        else:
            return (mejor_match[2], mejor_match[1])
    
    # No encontrado
    return ('PENDIENTE', proveedor)


def extraer_numero_gestoria(archivo: str, numero_factura) -> Tuple[str, bool]:
    """
    Extrae el número de gestoría del nombre de archivo.
    
    Patrones válidos:
    - "3005 3T25 0704 CERES TF.pdf" → 3005
    - "946 T25 0619 DE LUIS..." → 946
    - "4001 4T 1108 ANTHROPIC..." → 4001
    
    Args:
        archivo: Nombre del archivo PDF
        numero_factura: Número asignado por el sistema (f.numero)
        
    Returns:
        Tupla (numero, es_temporal)
        - numero: El número de gestoría o TMPxxx si no tiene
        - es_temporal: True si es número temporal generado
    """
    if not archivo:
        return ('', True)
    
    # Patrón: número al inicio (3-4 dígitos) seguido de espacio
    match = re.match(r'^(\d{3,4})\s+', archivo)
    if match:
        return (match.group(1), False)
    
    # Si el número de factura del sistema es válido (no empieza por 9 y tiene 4 dígitos)
    if numero_factura:
        num_str = str(numero_factura)
        if re.match(r'^\d{3,4}$', num_str):
            # Verificar que el archivo empieza con este número
            if archivo.startswith(num_str):
                return (num_str, False)
    
    # No tiene número de gestoría
    return ('', True)


def formatear_fecha_factura(fecha) -> str:
    """
    Formatea la fecha al formato DD-MM-YY.
    
    Args:
        fecha: Fecha en varios formatos posibles
        
    Returns:
        Fecha formateada o cadena vacía
    """
    if not fecha:
        return ''
    
    fecha_str = str(fecha).strip()
    
    # Ya está en formato DD-MM-YY
    if re.match(r'^\d{2}-\d{2}-\d{2}$', fecha_str):
        return fecha_str
    
    # Formato DD/MM/YYYY
    match = re.match(r'^(\d{2})/(\d{2})/(\d{4})$', fecha_str)
    if match:
        dd, mm, yyyy = match.groups()
        return f"{dd}-{mm}-{yyyy[2:]}"
    
    # Formato DD/MM/YY
    match = re.match(r'^(\d{2})/(\d{2})/(\d{2})$', fecha_str)
    if match:
        dd, mm, yy = match.groups()
        return f"{dd}-{mm}-{yy}"
    
    # Formato YYYY-MM-DD
    match = re.match(r'^(\d{4})-(\d{2})-(\d{2})', fecha_str)
    if match:
        yyyy, mm, dd = match.groups()
        return f"{dd}-{mm}-{yyyy[2:]}"
    
    # Devolver tal cual si no reconoce el formato
    return fecha_str


def generar_excel(facturas: List['Factura'], ruta: Path, nombre_hoja: str = 'Lineas',
                  ruta_diccionario: Optional[Path] = None) -> int:
    """
    Genera el Excel con las facturas procesadas.
    
    Crea dos hojas:
    - "Lineas": Detalle de todas las líneas de factura (antes "Facturas")
    - "Facturas": Cabeceras con una fila por factura
    
    Args:
        facturas: Lista de facturas procesadas
        ruta: Ruta donde guardar el archivo
        nombre_hoja: Nombre de la hoja de líneas (por compatibilidad)
        ruta_diccionario: Ruta al DiccionarioEmisorTitulo.xlsx
        
    Returns:
        Número de filas de líneas generadas
    """
    # Asegurar que el directorio existe
    ruta.parent.mkdir(parents=True, exist_ok=True)
    
    # Contador para números temporales
    contador_tmp = 1
    
    # =========================================================================
    # HOJA 1: LINEAS (detalle de artículos)
    # v5.12: Nueva columna EXTRACTOR al final
    # =========================================================================
    filas_lineas = []
    
    for f in facturas:
        # v5.12: Obtener info del extractor
        extractor_nombre = getattr(f, 'extractor_nombre', '') or ''
        extractor_metodo = getattr(f, 'metodo_pdf', '') or ''
        if extractor_nombre:
            extractor_info = f"{extractor_nombre} ({extractor_metodo})" if extractor_metodo else extractor_nombre
        elif extractor_metodo:
            extractor_info = f"generico ({extractor_metodo})"
        else:
            extractor_info = ''
        
        if f.lineas:
            for linea in f.lineas:
                filas_lineas.append({
                    '#': f.numero,
                    'FECHA': f.fecha or '',
                    'REF': f.referencia or '',
                    'PROVEEDOR': f.proveedor,
                    'ARTICULO': linea.articulo,
                    'CATEGORIA': linea.categoria or 'PENDIENTE',
                    'ID_CAT': linea.id_categoria or '',
                    'CANTIDAD': linea.cantidad if linea.cantidad else '',
                    'PRECIO_UD': linea.precio_ud if linea.precio_ud else '',
                    'TIPO IVA': linea.iva,
                    'BASE (€)': linea.base,
                    'CUOTA IVA': linea.cuota_iva,
                    'TOTAL FAC': f.total or '',
                    'CUADRE': f.cuadre,
                    'ARCHIVO': f.archivo,
                    'EXTRACTOR': extractor_info,  # v5.12
                })
        else:
            # Factura sin líneas extraídas
            filas_lineas.append({
                '#': f.numero,
                'FECHA': f.fecha or '',
                'REF': f.referencia or '',
                'PROVEEDOR': f.proveedor,
                'ARTICULO': 'VER FACTURA',
                'CATEGORIA': 'PENDIENTE',
                'ID_CAT': '',
                'CANTIDAD': '',
                'PRECIO_UD': '',
                'TIPO IVA': '',
                'BASE (€)': f.total or '',
                'CUOTA IVA': '',
                'TOTAL FAC': f.total or '',
                'CUADRE': f.cuadre,
                'ARCHIVO': f.archivo,
                'EXTRACTOR': extractor_info,  # v5.12
            })
    
    # =========================================================================
    # HOJA 2: FACTURAS (cabeceras, una fila por factura)
    # Cabeceras: #, ARCHIVO, CUENTA, Fec.Fac., TITULO, REF, TOTAL FACTURA, Total Parseo, OBSERVACIONES
    # =========================================================================
    filas_facturas = []
    
    for f in facturas:
        # Extraer número de gestoría
        num_gestoria, es_temporal = extraer_numero_gestoria(f.archivo, f.numero)
        
        if es_temporal or not num_gestoria:
            num_gestoria = f"TMP{contador_tmp:03d}"
            contador_tmp += 1
        
        # Buscar CUENTA y TITULO desde MAESTRO_PROVEEDORES
        cuenta, titulo = buscar_cuenta_titulo(f.proveedor, ruta_diccionario)
        
        # Formatear fecha DD-MM-YY
        fecha_formateada = formatear_fecha_factura(f.fecha)
        
        # Calcular Total Parseo (suma de líneas)
        if f.lineas:
            total_parseo = sum(l.base * (1 + l.iva/100) for l in f.lineas)
            total_parseo = round(total_parseo, 2)
        else:
            total_parseo = ''
        
        # OBSERVACIONES = cuadre
        observaciones = f.cuadre or ''
        if es_temporal:
            if observaciones:
                observaciones += ', SIN_NUM_GESTORIA'
            else:
                observaciones = 'SIN_NUM_GESTORIA'
        
        filas_facturas.append({
            '#': num_gestoria,
            'ARCHIVO': f.archivo,
            'CUENTA': cuenta,
            'Fec.Fac.': fecha_formateada,
            'TITULO': titulo,
            'REF': f.referencia or '',
            'TOTAL FACTURA': f.total or '',
            'Total Parseo': total_parseo,
            'OBSERVACIONES': observaciones
        })
    
    # =========================================================================
    # GUARDAR EXCEL CON AMBAS HOJAS
    # =========================================================================
    df_lineas = pd.DataFrame(filas_lineas)
    df_facturas = pd.DataFrame(filas_facturas)
    
    # SANITIZAR antes de escribir (evita IllegalCharacterError)
    df_lineas = sanitizar_dataframe(df_lineas)
    df_facturas = sanitizar_dataframe(df_facturas)
    
    if not _verificar_archivo_no_abierto(ruta):
        print(f"  ABORTANDO escritura — archivo bloqueado.")
        return 0

    with pd.ExcelWriter(ruta, engine='openpyxl') as writer:
        # Orden: Lineas primero, Facturas después (según preferencia B)
        df_lineas.to_excel(writer, index=False, sheet_name='Lineas')
        df_facturas.to_excel(writer, index=False, sheet_name='Facturas')

    return len(filas_lineas)


def generar_excel_resumen(facturas: List['Factura'], ruta: Path) -> int:
    """
    Genera un Excel resumen con totales por proveedor.
    
    Args:
        facturas: Lista de facturas procesadas
        ruta: Ruta donde guardar el archivo
        
    Returns:
        Número de filas generadas
    """
    # Agrupar por proveedor
    resumen = {}
    for f in facturas:
        prov = f.proveedor or 'DESCONOCIDO'
        if prov not in resumen:
            resumen[prov] = {
                'facturas': 0,
                'total': 0.0,
                'lineas': 0,
                'ok': 0,
                'errores': 0
            }
        resumen[prov]['facturas'] += 1
        resumen[prov]['total'] += f.total or 0
        resumen[prov]['lineas'] += len(f.lineas)
        if f.cuadre == 'OK':
            resumen[prov]['ok'] += 1
        else:
            resumen[prov]['errores'] += 1
    
    # Convertir a filas
    filas = []
    for prov, datos in sorted(resumen.items()):
        filas.append({
            'PROVEEDOR': prov,
            'FACTURAS': datos['facturas'],
            'TOTAL €': round(datos['total'], 2),
            'LINEAS': datos['lineas'],
            'OK': datos['ok'],
            'ERRORES': datos['errores'],
            '% ÉXITO': f"{100 * datos['ok'] / datos['facturas']:.1f}%" if datos['facturas'] > 0 else '0%'
        })
    
    df = pd.DataFrame(filas)
    df = sanitizar_dataframe(df)  # SANITIZAR
    ruta.parent.mkdir(parents=True, exist_ok=True)
    df.to_excel(ruta, index=False, sheet_name='Resumen')
    
    return len(filas)


def generar_excel_errores(facturas: List['Factura'], ruta: Path) -> int:
    """
    Genera un Excel con las facturas que tienen errores.
    
    Args:
        facturas: Lista de facturas procesadas
        ruta: Ruta donde guardar el archivo
        
    Returns:
        Número de filas generadas
    """
    filas = []
    
    for f in facturas:
        if f.tiene_errores or f.cuadre != 'OK':
            filas.append({
                '#': f.numero,
                'ARCHIVO': f.archivo,
                'PROVEEDOR': f.proveedor,
                'FECHA': f.fecha or '',
                'TOTAL': f.total or '',
                'CUADRE': f.cuadre,
                'ERRORES': ', '.join(f.errores) if f.errores else '',
                'LINEAS': len(f.lineas),
                'RUTA': str(f.ruta) if f.ruta else ''
            })
    
    if filas:
        df = pd.DataFrame(filas)
        df = sanitizar_dataframe(df)  # SANITIZAR
        ruta.parent.mkdir(parents=True, exist_ok=True)
        df.to_excel(ruta, index=False, sheet_name='Errores')
    
    return len(filas)


def generar_excel_multihoja(facturas: List['Factura'], ruta: Path) -> dict:
    """
    Genera un Excel con múltiples hojas:
    - Lineas: todas las líneas (detalle)
    - Facturas: cabeceras (una por factura)
    - Resumen: totales por proveedor
    - Errores: facturas con problemas
    
    Args:
        facturas: Lista de facturas procesadas
        ruta: Ruta donde guardar el archivo
        
    Returns:
        Dict con conteo de filas por hoja
    """
    ruta.parent.mkdir(parents=True, exist_ok=True)

    if not _verificar_archivo_no_abierto(ruta):
        print(f"  ABORTANDO escritura — archivo bloqueado.")
        return {}

    contador_tmp = 1

    with pd.ExcelWriter(ruta, engine='openpyxl') as writer:
        # Hoja 1: Lineas (detalle)
        filas_lineas = []
        for f in facturas:
            if f.lineas:
                for linea in f.lineas:
                    filas_lineas.append({
                        '#': f.numero,
                        'FECHA': f.fecha or '',
                        'PROVEEDOR': f.proveedor,
                        'ARTICULO': linea.articulo,
                        'CATEGORIA': linea.categoria or 'PENDIENTE',
                        'CANTIDAD': linea.cantidad if linea.cantidad else '',
                        'PRECIO_UD': linea.precio_ud if linea.precio_ud else '',
                        'IVA': linea.iva,
                        'BASE': linea.base,
                        'TOTAL FAC': f.total or '',
                        'CUADRE': f.cuadre
                    })
            else:
                filas_lineas.append({
                    '#': f.numero,
                    'FECHA': f.fecha or '',
                    'PROVEEDOR': f.proveedor,
                    'ARTICULO': 'VER FACTURA',
                    'CATEGORIA': 'PENDIENTE',
                    'CANTIDAD': '',
                    'PRECIO_UD': '',
                    'IVA': '',
                    'BASE': f.total or '',
                    'TOTAL FAC': f.total or '',
                    'CUADRE': f.cuadre
                })
        
        df_lineas = pd.DataFrame(filas_lineas)
        df_lineas = sanitizar_dataframe(df_lineas)  # SANITIZAR
        df_lineas.to_excel(writer, index=False, sheet_name='Lineas')
        
        # Hoja 2: Facturas (cabeceras)
        filas_facturas = []
        for f in facturas:
            num_gestoria, es_temporal = extraer_numero_gestoria(f.archivo, f.numero)
            if es_temporal or not num_gestoria:
                num_gestoria = f"TMP{contador_tmp:03d}"
                contador_tmp += 1
            
            cuenta, titulo = buscar_cuenta_titulo(f.proveedor)
            fecha_formateada = formatear_fecha_factura(f.fecha)
            
            observaciones = f.cuadre or ''
            if es_temporal:
                observaciones += ', SIN_NUM_GESTORIA' if observaciones else 'SIN_NUM_GESTORIA'
            
            filas_facturas.append({
                '#': num_gestoria,
                'CUENTA': cuenta,
                'TITULO': titulo,
                'Fec.Fac.': fecha_formateada,
                'REF': f.referencia or '',
                'Total': f.total or '',
                'OBSERVACIONES': observaciones
            })
        
        df_facturas = pd.DataFrame(filas_facturas)
        df_facturas = sanitizar_dataframe(df_facturas)  # SANITIZAR
        df_facturas.to_excel(writer, index=False, sheet_name='Facturas')
        
        # Hoja 3: Resumen
        resumen = {}
        for f in facturas:
            prov = f.proveedor or 'DESCONOCIDO'
            if prov not in resumen:
                resumen[prov] = {'facturas': 0, 'total': 0.0, 'ok': 0}
            resumen[prov]['facturas'] += 1
            resumen[prov]['total'] += f.total or 0
            if f.cuadre == 'OK':
                resumen[prov]['ok'] += 1
        
        filas_resumen = [
            {'PROVEEDOR': p, 'FACTURAS': d['facturas'], 'TOTAL': round(d['total'], 2), 
             'OK': d['ok'], '%': f"{100*d['ok']/d['facturas']:.0f}%"}
            for p, d in sorted(resumen.items())
        ]
        df_resumen = pd.DataFrame(filas_resumen)
        df_resumen = sanitizar_dataframe(df_resumen)  # SANITIZAR
        df_resumen.to_excel(writer, index=False, sheet_name='Resumen')
        
        # Hoja 4: Errores
        filas_errores = [
            {'ARCHIVO': f.archivo, 'PROVEEDOR': f.proveedor, 'CUADRE': f.cuadre, 
             'ERRORES': ', '.join(f.errores)}
            for f in facturas if f.tiene_errores or f.cuadre != 'OK'
        ]
        df_errores = pd.DataFrame(filas_errores)
        df_errores = sanitizar_dataframe(df_errores)  # SANITIZAR
        df_errores.to_excel(writer, index=False, sheet_name='Errores')
    
    return {
        'Lineas': len(filas_lineas),
        'Facturas': len(filas_facturas),
        'Resumen': len(filas_resumen),
        'Errores': len(filas_errores)
    }
