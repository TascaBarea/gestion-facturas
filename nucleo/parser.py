"""
Módulo de parseo de datos de facturas.

Contiene funciones para extraer:
- Fecha
- CIF
- IBAN
- Total
- Referencia/número de factura
- Datos del nombre de archivo

CAMBIOS v5.16 (07/01/2026):
- NUEVO: Asignación automática de TEMP001, TEMP002... para archivos sin número de gestoría
- Los archivos tipo "4T25 1020 PROVEEDOR TF.pdf" reciben TEMP001_4T25, TEMP002_4T25, etc.
- Contador TEMP reinicia por trimestre dentro de cada ejecución

Uso:
    from nucleo.parser import extraer_fecha, extraer_cif, extraer_total
    
    fecha = extraer_fecha(texto)
    cif = extraer_cif(texto)
    total = extraer_total(texto)
"""
import re
from typing import Optional, Dict, List, Tuple
from pathlib import Path


# =============================================================================
# CONTADOR GLOBAL TEMP POR TRIMESTRE (v5.16)
# =============================================================================

# Diccionario que guarda el contador TEMP por trimestre
# Ejemplo: {'4T25': 3, '1T26': 1} significa que ya se asignaron TEMP001-003 en 4T25
_CONTADOR_TEMP_POR_TRIMESTRE: Dict[str, int] = {}


def resetear_contadores_temp():
    """
    Resetea los contadores TEMP. Llamar al inicio de cada ejecución.
    """
    global _CONTADOR_TEMP_POR_TRIMESTRE
    _CONTADOR_TEMP_POR_TRIMESTRE = {}


def _obtener_siguiente_temp(trimestre: str) -> str:
    """
    Obtiene el siguiente número TEMP para un trimestre.
    
    Args:
        trimestre: Código de trimestre (ej: '4T25', '1T26')
        
    Returns:
        Número TEMP formateado (ej: 'TEMP001_4T25')
    """
    global _CONTADOR_TEMP_POR_TRIMESTRE
    
    if trimestre not in _CONTADOR_TEMP_POR_TRIMESTRE:
        _CONTADOR_TEMP_POR_TRIMESTRE[trimestre] = 0
    
    _CONTADOR_TEMP_POR_TRIMESTRE[trimestre] += 1
    contador = _CONTADOR_TEMP_POR_TRIMESTRE[trimestre]
    
    return f"TEMP{contador:03d}_{trimestre}"


# =============================================================================
# PARSEO DEL NOMBRE DE ARCHIVO
# =============================================================================

def parsear_nombre_archivo(nombre: str, es_carpeta_atrasadas: bool = False) -> Dict:
    """
    Extrae información del nombre del archivo.
    
    Formato esperado: NNNN TRIMESTRE FECHA PROVEEDOR TIPO.pdf
    Ejemplo: 2001 1T25 0115 CERES TF.pdf
    
    NUEVO v5.16: 
    - Si el archivo empieza con TRIMESTRE (ej: "4T25 1020 PROVEEDOR...")
      se asigna automáticamente un número TEMP001_4T25, TEMP002_4T25, etc.
    - Si el archivo empieza con 3 dígitos → es ATRASADA
      Formato: XXX [ATRASADA] [TRIMESTRE_ORIGEN] MMDD PROVEEDOR TIPO.pdf
      El # se devuelve como "XXX ATRASADA"
    
    Args:
        nombre: Nombre del archivo (con o sin extensión)
        es_carpeta_atrasadas: True si el archivo está en subcarpeta ATRASADAS
        
    Returns:
        Diccionario con:
        - numero: Número de factura (int, str "XXX ATRASADA", o str "TEMPXXX_XTxx")
        - trimestre: Trimestre (ej: '1T25')
        - fecha_archivo: Fecha del nombre (MMDD)
        - proveedor: Nombre del proveedor
        - tipo: Tipo de factura (TF, RC, EF, TJ, TR)
        - es_atrasada: bool indicando si es factura atrasada
    """
    # Eliminar extensión
    nombre_original = nombre
    nombre = Path(nombre).stem
    
    resultado = {
        'numero': 0,
        'trimestre': '',
        'fecha_archivo': '',
        'proveedor': '',
        'tipo': '',
        'es_atrasada': False
    }
    
    # =========================================================================
    # CASO 0: ATRASADA - Archivo con 3 dígitos al inicio (rango típico 900-999, 400-499)
    # Patrón: XXX [ATRASADA] [TRIMESTRE_ORIGEN] MMDD PROVEEDOR TIPO
    # Ejemplos: 
    #   - 460 ATRASADA 1T25 0326 SWITCHBOT TJ.pdf
    #   - 946 T25 0619 DE LUIS SABORES UNICOS TF.pdf (sin palabra ATRASADA)
    #   - 401 ATRASADAS 0710 BM TJ.pdf (sin trimestre origen)
    # 
    # REGLA: Si 3 dígitos + tiene palabra ATRASADA → siempre es atrasada
    #        Si 3 dígitos + NO tiene ATRASADA + está en carpeta ATRASADAS → es atrasada
    #        Si 3 dígitos + NO tiene ATRASADA + NO está en carpeta ATRASADAS → ERROR
    # =========================================================================
    
    # Detectar si empieza con 3 dígitos
    match_3dig = re.match(r'^(\d{3})\s+(.+)$', nombre)
    if match_3dig:
        num_3_digitos = match_3dig.group(1)
        resto = match_3dig.group(2)
        tiene_palabra_atrasada = bool(re.search(r'\bATRASADAS?\b', resto, re.IGNORECASE))
        
        # Determinar si tratar como atrasada o error
        if tiene_palabra_atrasada or es_carpeta_atrasadas:
            # Es una atrasada válida
            # Limpiar "ATRASADA" del resto para parsear mejor
            resto_limpio = re.sub(r'\bATRASADAS?\s*', '', resto, flags=re.IGNORECASE)
            
            # Intentar extraer trimestre origen, fecha, proveedor, tipo
            patron_resto = r'^(?:(\d[TQ]\d{2})\s+)?(?:(\d{4})\s+)?(.+?)\s*(TF|RC|EF|TJ|TR|REC)?\s*$'
            match_resto = re.match(patron_resto, resto_limpio, re.IGNORECASE)
            
            if match_resto:
                resultado['numero'] = f"{num_3_digitos} ATRASADA"
                resultado['trimestre'] = match_resto.group(1) or ''
                resultado['fecha_archivo'] = match_resto.group(2) or ''
                resultado['proveedor'] = match_resto.group(3).strip() if match_resto.group(3) else ''
                resultado['tipo'] = match_resto.group(4).upper() if match_resto.group(4) else ''
            else:
                resultado['numero'] = f"{num_3_digitos} ATRASADA"
                resultado['proveedor'] = resto_limpio.strip()
            
            resultado['es_atrasada'] = True
            return resultado
        else:
            # 3 dígitos sin palabra ATRASADA y fuera de carpeta ATRASADAS → ERROR
            resultado['numero'] = f"ERROR_3DIG_{num_3_digitos}"
            resultado['proveedor'] = resto
            return resultado
    
    # =========================================================================
    # CASO 1: Archivo con número de gestoría (formato estándar) - 4 dígitos
    # Patrón: NNNN [TRIMESTRE] [FECHA] PROVEEDOR TIPO
    # Ejemplo: 2001 1T25 0115 CERES TF
    # =========================================================================
    patron = r'^(\d{4})\s+(?:(\d[TQ]\d{2})\s+)?(?:(\d{4})\s+)?(.+?)\s+(TF|RC|EF|TJ|TR|REC)?\s*$'
    
    match = re.match(patron, nombre, re.IGNORECASE)
    if match:
        resultado['numero'] = int(match.group(1))
        resultado['trimestre'] = match.group(2) or ''
        resultado['fecha_archivo'] = match.group(3) or ''
        resultado['proveedor'] = match.group(4).strip() if match.group(4) else ''
        resultado['tipo'] = match.group(5).upper() if match.group(5) else ''
        return resultado
    
    # =========================================================================
    # CASO 2: Archivo sin número de gestoría (empieza con TRIMESTRE)
    # Patrón: TRIMESTRE FECHA PROVEEDOR TIPO
    # Ejemplo: 4T25 1020 EMBUTIDOS FERRIOL TF
    # =========================================================================
    patron_sin_numero = r'^(\d[TQ]\d{2})\s+(\d{4})\s+(.+?)\s+(TF|RC|EF|TJ|TR|REC)?\s*$'
    
    match_sin_num = re.match(patron_sin_numero, nombre, re.IGNORECASE)
    if match_sin_num:
        trimestre = match_sin_num.group(1).upper()
        # Asignar número TEMP
        numero_temp = _obtener_siguiente_temp(trimestre)
        
        resultado['numero'] = numero_temp  # String tipo "TEMP001_4T25"
        resultado['trimestre'] = trimestre
        resultado['fecha_archivo'] = match_sin_num.group(2) or ''
        resultado['proveedor'] = match_sin_num.group(3).strip() if match_sin_num.group(3) else ''
        resultado['tipo'] = match_sin_num.group(4).upper() if match_sin_num.group(4) else ''
        return resultado
    
    # =========================================================================
    # CASO 3: Intento simplificado (solo número al inicio) - 4 dígitos
    # =========================================================================
    match_simple = re.match(r'^(\d{4})\s+(.+)$', nombre)
    if match_simple:
        resultado['numero'] = int(match_simple.group(1))
        resto = match_simple.group(2)
        # Extraer tipo al final
        match_tipo = re.search(r'\s+(TF|RC|EF|TJ|TR|REC)\s*$', resto, re.IGNORECASE)
        if match_tipo:
            resultado['tipo'] = match_tipo.group(1).upper()
            resto = resto[:match_tipo.start()]
        resultado['proveedor'] = resto.strip()
        return resultado
    
    # =========================================================================
    # CASO 4: No se pudo parsear - devolver valores por defecto
    # =========================================================================
    return resultado


# =============================================================================
# EXTRACCIÓN DE FECHA
# =============================================================================

def extraer_fecha(texto: str, proveedor: str = '') -> Optional[str]:
    """
    Extrae la fecha de la factura del texto.
    
    Args:
        texto: Texto del PDF
        proveedor: Nombre del proveedor (para patrones específicos)
        
    Returns:
        Fecha en formato DD/MM/YYYY o None si no se encuentra
    """
    # Patrones ordenados de más específico a más genérico
    patrones = [
        # Fecha factura: 15/12/2025
        r'(?:Fecha|Fª|F\.)\s*(?:factura|fra|fact)?[:\s]*(\d{1,2})[/\-](\d{1,2})[/\-](\d{4})',
        # 15/12/2025
        r'(\d{1,2})[/\-](\d{1,2})[/\-](\d{4})',
        # 15-12-25 (año corto)
        r'(\d{1,2})[/\-](\d{1,2})[/\-](\d{2})\b',
        # 15 de diciembre de 2025
        r'(\d{1,2})\s+de\s+(\w+)\s+de\s+(\d{4})',
    ]
    
    for patron in patrones:
        match = re.search(patron, texto, re.IGNORECASE)
        if match:
            grupos = match.groups()
            
            # Caso: día de mes de año
            if len(grupos) == 3 and not grupos[1].isdigit():
                dia = grupos[0].zfill(2)
                mes = _mes_a_numero(grupos[1])
                año = grupos[2]
                if mes:
                    return f"{dia}/{mes}/{año}"
                continue
            
            # Caso: DD/MM/YYYY o DD/MM/YY
            dia = grupos[0].zfill(2)
            mes = grupos[1].zfill(2)
            año = grupos[2]
            
            # Año corto a largo
            if len(año) == 2:
                año = '20' + año
            
            # Validar fecha
            if _es_fecha_valida(dia, mes, año):
                return f"{dia}/{mes}/{año}"
    
    return None


def _mes_a_numero(mes: str) -> Optional[str]:
    """Convierte nombre de mes a número."""
    meses = {
        'enero': '01', 'febrero': '02', 'marzo': '03', 'abril': '04',
        'mayo': '05', 'junio': '06', 'julio': '07', 'agosto': '08',
        'septiembre': '09', 'octubre': '10', 'noviembre': '11', 'diciembre': '12',
        'ene': '01', 'feb': '02', 'mar': '03', 'abr': '04',
        'may': '05', 'jun': '06', 'jul': '07', 'ago': '08',
        'sep': '09', 'oct': '10', 'nov': '11', 'dic': '12',
    }
    return meses.get(mes.lower())


def _es_fecha_valida(dia: str, mes: str, año: str) -> bool:
    """Valida que la fecha sea razonable."""
    try:
        d, m, a = int(dia), int(mes), int(año)
        return 1 <= d <= 31 and 1 <= m <= 12 and 2020 <= a <= 2030
    except:
        return False


# =============================================================================
# EXTRACCIÓN DE CIF
# =============================================================================

def extraer_cif(texto: str) -> Optional[str]:
    """
    Extrae el CIF del proveedor del texto.
    
    Args:
        texto: Texto del PDF
        
    Returns:
        CIF normalizado o None si no se encuentra
    """
    # CIF propio a excluir
    CIF_PROPIO = 'B87760575'
    
    # Patrones de CIF
    patrones = [
        # CIF: B12345678
        r'(?:CIF|NIF|C\.I\.F|N\.I\.F)[:\s]*([A-Z]\d{8})',
        # B-12345678
        r'\b([A-Z])[- ]?(\d{8})\b',
        # DNI: 12345678X
        r'(?:DNI|NIF)[:\s]*(\d{8}[A-Z])',
        # CIF italiano (BIELLEBI): 06089700725
        r'(?:P\.IVA|IVA)[:\s]*(\d{11})',
    ]
    
    cifs_encontrados = []
    
    for patron in patrones:
        for match in re.finditer(patron, texto, re.IGNORECASE):
            grupos = match.groups()
            
            # Normalizar CIF
            if len(grupos) == 2:
                cif = grupos[0].upper() + grupos[1]
            else:
                cif = grupos[0].upper()
            
            # Limpiar guiones y espacios
            cif = cif.replace('-', '').replace(' ', '')
            
            # Excluir CIF propio
            if cif != CIF_PROPIO and cif not in cifs_encontrados:
                cifs_encontrados.append(cif)
    
    # Devolver el primero que no sea el propio
    return cifs_encontrados[0] if cifs_encontrados else None


# =============================================================================
# EXTRACCIÓN DE IBAN
# =============================================================================

def extraer_iban(texto: str) -> Optional[str]:
    """
    Extrae el IBAN del proveedor del texto.
    
    Args:
        texto: Texto del PDF
        
    Returns:
        IBAN formateado o None si no se encuentra
    """
    # Bancos a evitar (cuando hay varios IBANs)
    BANCOS_EVITAR = ['0049']  # Santander (suele ser del cliente)
    
    # Patrón IBAN español
    patron_iban = r'(?:IBAN[:\s]*)?([A-Z]{2}\d{2})\s*(\d{4})\s*(\d{4})\s*(\d{4})\s*(\d{4})\s*(\d{4})'
    
    # Patrón IBAN italiano
    patron_iban_it = r'([A-Z]{2}\d{2})\s*([A-Z])(\d{5})\s*(\d{5})\s*(\d{12})'
    
    ibans = []
    
    # Buscar IBANs españoles
    for match in re.finditer(patron_iban, texto, re.IGNORECASE):
        iban = ' '.join(match.groups())
        codigo_banco = match.group(2)
        
        # Priorizar IBANs de bancos no evitados
        if codigo_banco not in BANCOS_EVITAR:
            ibans.insert(0, iban)
        else:
            ibans.append(iban)
    
    # Buscar IBANs italianos
    for match in re.finditer(patron_iban_it, texto, re.IGNORECASE):
        iban = ''.join(match.groups())
        ibans.append(iban)
    
    return ibans[0] if ibans else None


def extraer_todos_ibans(texto: str) -> List[str]:
    """
    Extrae todos los IBANs encontrados en el texto.
    
    Args:
        texto: Texto del PDF
        
    Returns:
        Lista de IBANs encontrados
    """
    patron = r'([A-Z]{2}\d{2})\s*(\d{4})\s*(\d{4})\s*(\d{4})\s*(\d{4})\s*(\d{4})'
    
    ibans = []
    for match in re.finditer(patron, texto, re.IGNORECASE):
        iban = ' '.join(match.groups())
        if iban not in ibans:
            ibans.append(iban)
    
    return ibans


# =============================================================================
# EXTRACCIÓN DE TOTAL
# =============================================================================

def extraer_total(texto: str, proveedor: str = '') -> Optional[float]:
    """
    Extrae el total de la factura del texto.
    
    Args:
        texto: Texto del PDF
        proveedor: Nombre del proveedor (para patrones específicos)
        
    Returns:
        Total de la factura o None si no se encuentra
    """
    proveedor_upper = proveedor.upper() if proveedor else ''
    
    # Patrones ordenados de más específico a más genérico
    patrones = [
        # v3.56 - LOS GREDALES: IVA 21% XX,XX € N N TOTAL €
        (r'IVA\s*21%\s*[\d,]+\s*€\s*\d+\s+\d+\s+(\d{1,3}(?:[.,]\d{3})*[,.]\d{2})\s*€', 'GREDALES'),
        
        # v3.56 - SERRÍN NO CHAN: XX,XX€TOTAL€TOTALES
        (r'[\d,]+\s*€(\d{1,3}(?:[.,]\d{3})*[.,]\d{2})\s*€TOTALES', 'SERRIN'),
        
        # v3.56 - BORBOTON: BASE € IVA% CUOTA € TOTAL €
        (r'(?:\d{1,3}(?:[.,]\d{3})*[.,]\d{2})\s*€\s+(?:21|10|4)[.,]00\s*%\s+(?:\d+[.,]\d{2})\s*€\s+(\d{1,3}(?:[.,]\d{3})*[.,]\d{2})\s*€', 'BORBOTON'),
        
        # v3.56 - MARITA COSTA: TOTAL: XXX,XX€
        (r'TOTAL:\s*([\d,]+)€', 'MARITA'),
        
        # v3.55 - IBARRAKO: XX,XX€ TOTAL€ al final de línea
        (r'[\d,]+\s*€[ \t]+(\d{1,3}[,.]\d{2})\s*€\s*$', 'IBARRAKO'),
        
        # v3.52 - EMJAMESA: después de 21,000 %
        (r'21,000\s*%\s*[\d,]+\s*€\n(\d{1,3}[,.]\d{2})\s*€', 'EMJAMESA'),
        
        # v3.54 - CERES: Importe TOTAL ...... XXX,XX
        (r'Importe\s+TOTAL\s*[.]+\s*(-?\d{1,3}(?:[.,]\d{3})*[.,]\d{2})', 'CERES'),
        
        # v3.57 - LICORES MADRUEÑO: TOTAL €: 890,08
        (r'TOTAL\s*€[:\s]*(\d{1,3}(?:[.,]\d{3})*[.,]\d{2})', 'MADRUEÑO'),
        
        # Genérico: TOTAL FACTURA: XXX,XX
        (r'(?:TOTAL\s*FACTURA|TOTAL\s*IMPORTE|Total\s*Factura)[:\s]*(\d{1,3}(?:[.,]\d{3})*[.,]\d{2})(?!\s*%)\s*€?', None),
        
        # Genérico: TOTAL A PAGAR XXX.XX€
        (r'TOTAL\s*A\s*PAGAR\s+(\d+\.\d{2})\s*€', None),
        
        # Genérico: XX,XX Euros
        (r'(\d{1,3}(?:[.,]\d{3})*[.,]\d{2})\s*Euros', None),
    ]
    
    for patron_str, proveedor_patron in patrones:
        # Si el patrón es específico, verificar que sea el proveedor correcto
        if proveedor_patron and proveedor_patron not in proveedor_upper:
            continue
        
        patron = re.compile(patron_str, re.IGNORECASE | re.MULTILINE)
        match = patron.search(texto)
        
        if match:
            total_str = match.group(1)
            valor = _convertir_importe(total_str)
            
            # Validar que sea razonable
            if valor and (valor > 1.0 or valor < -1.0):
                return valor
    
    return None


def _convertir_importe(importe_str: str) -> Optional[float]:
    """
    Convierte un string de importe a float.
    
    Args:
        importe_str: String con el importe
        
    Returns:
        Importe como float o None si falla
    """
    try:
        importe_str = importe_str.strip()
        
        # Formato español: 1.234,56
        if ',' in importe_str and '.' in importe_str:
            pos_coma = importe_str.rfind(',')
            pos_punto = importe_str.rfind('.')
            
            if pos_coma > pos_punto:
                importe_str = importe_str.replace('.', '').replace(',', '.')
            else:
                importe_str = importe_str.replace(',', '')
        elif ',' in importe_str:
            importe_str = importe_str.replace(',', '.')
        
        return float(importe_str)
    except:
        return None


# =============================================================================
# EXTRACCIÓN DE REFERENCIA
# =============================================================================

def extraer_referencia(texto: str, proveedor: str = '') -> Optional[str]:
    """
    Extrae el número de referencia/factura del texto.
    
    Args:
        texto: Texto del PDF
        proveedor: Nombre del proveedor (para patrones específicos)
        
    Returns:
        Número de referencia o None si no se encuentra
    """
    patrones = [
        # Nº Factura: 12345
        r'(?:Nº|N°|Núm|Numero)\s*(?:Factura|Fra|Fact)[:\s]*([A-Z0-9/-]+)',
        # Factura nº 12345
        r'(?:Factura|Fra)\s*(?:nº|n°|núm)?[:\s]*([A-Z0-9/-]+)',
        # Ref: ABC-12345
        r'(?:Ref|Referencia)[:\s]*([A-Z0-9/-]+)',
        # SERIE NÚMERO: A 12345
        r'SERIE\s+N[ÚU]MERO[:\s]*([A-Z]?\s*\d+)',
    ]
    
    for patron in patrones:
        match = re.search(patron, texto, re.IGNORECASE)
        if match:
            ref = match.group(1).strip()
            # Limpiar espacios extra
            ref = re.sub(r'\s+', ' ', ref)
            if len(ref) >= 2:  # Mínimo 2 caracteres
                return ref
    
    return None


# =============================================================================
# DETECCIÓN DE PROVEEDOR
# =============================================================================

def detectar_proveedor_por_cif(texto: str) -> Optional[str]:
    """
    Detecta el proveedor basándose en el CIF encontrado.
    
    Args:
        texto: Texto del PDF
        
    Returns:
        Nombre del proveedor o None si no se detecta
    """
    try:
        from config.proveedores import obtener_proveedor_por_cif
    except ImportError:
        return None
    
    cif = extraer_cif(texto)
    if cif:
        return obtener_proveedor_por_cif(cif)
    
    return None


def detectar_proveedor_por_contenido(texto: str) -> Optional[str]:
    """
    Detecta el proveedor analizando el contenido del PDF.
    
    Args:
        texto: Texto del PDF
        
    Returns:
        Nombre del proveedor o None si no se detecta
    """
    # Primero intentar por CIF
    proveedor = detectar_proveedor_por_cif(texto)
    if proveedor:
        return proveedor
    
    # Luego buscar palabras clave
    texto_upper = texto.upper()
    
    palabras_clave = {
        'CERES CERVEZAS': 'CERES',
        'B83478669': 'CERES',
        'BM SUPERMERCADOS': 'BM',
        'JIMELUZ EMPRENDEDORES': 'JIMELUZ',
        'LICORES MADRUEÑO': 'LICORES MADRUEÑO',
        'MARIANO MADRUEÑO': 'LICORES MADRUEÑO',
    }
    
    for clave, proveedor in palabras_clave.items():
        if clave in texto_upper:
            return proveedor
    
    return None
