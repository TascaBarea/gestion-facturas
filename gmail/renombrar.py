# -*- coding: utf-8 -*-
"""
RENOMBRAR.PY - Módulo de nomenclatura de archivos
Gestión de facturas - TASCA BAREA S.L.L.

Formato: [PREFIJO] XTYY MMDD PROVEEDOR [N] TIPO.ext
Ejemplos:
  - 1T26 0115 CERES RC.pdf
  - 1T26 0115 CERES 2 RC.pdf
  - ATRASADA 4T25 1002 CERES RC.pdf
  - PROFORMA 1T26 0120 KINEMA TF.pdf
"""

import os
import re
from datetime import datetime
from typing import Optional
import pdfplumber

from config import (
    calcular_trimestre,
    PREFIJO_ATRASADA,
    PREFIJO_PROFORMA,
    TIPOS_PAGO
)
from identificar import cargar_maestro, obtener_info_proveedor


# =============================================================================
# SANITIZACIÓN DE NOMBRES
# =============================================================================

def sanitizar_nombre(nombre: str) -> str:
    """
    Limpia nombre de archivo para Windows/Dropbox.
    
    Args:
        nombre: Nombre a limpiar
    
    Returns:
        Nombre sanitizado
    """
    if not nombre:
        return "DESCONOCIDO"
    
    # Reemplazar tildes
    reemplazos = {
        'á': 'a', 'é': 'e', 'í': 'i', 'ó': 'o', 'ú': 'u',
        'Á': 'A', 'É': 'E', 'Í': 'I', 'Ó': 'O', 'Ú': 'U',
        'ñ': 'n', 'Ñ': 'N', 'ü': 'u', 'Ü': 'U',
        'ç': 'c', 'Ç': 'C', 'ª': 'a', 'º': 'o'
    }
    for viejo, nuevo in reemplazos.items():
        nombre = nombre.replace(viejo, nuevo)
    
    # Eliminar caracteres inválidos en Windows
    nombre = re.sub(r'[<>:"/\\|?*]', '', nombre)
    
    # Reemplazar puntos intermedios por espacios (excepto extensión)
    nombre = re.sub(r'\.(?=.*\.)', ' ', nombre)
    
    # Espacios dobles → espacio simple
    nombre = re.sub(r'\s+', ' ', nombre)
    
    # Eliminar puntos al final (Windows no los permite)
    nombre = nombre.rstrip('.')
    
    # Limitar longitud
    if len(nombre) > 60:
        nombre = nombre[:60]
    
    return nombre.strip()


def abreviar_proveedor(nombre: str, max_len: int = 25) -> str:
    """
    Abrevia nombre de proveedor para el nombre de archivo.
    
    Args:
        nombre: Nombre completo del proveedor
        max_len: Longitud máxima
    
    Returns:
        Nombre abreviado
    """
    if not nombre:
        return "DESCONOCIDO"
    
    # Sanitizar primero
    nombre = sanitizar_nombre(nombre)
    
    # Eliminar sufijos comunes
    sufijos = [' SL', ' SLL', ' SLU', ' SA', ' SAU', ' SCA', ' CB', ' SCCL', 
               ' S.L.', ' S.L', ' S.A.', ' S.COOP.MAD.', ' S. COOP.', ' COOP. V',
               ' INC.', ' INC', ' SARL', ' SRL', ' SOCIEDAD COOPERATIVA']
    
    nombre_upper = nombre.upper()
    for sufijo in sufijos:
        if nombre_upper.endswith(sufijo.upper()):
            nombre = nombre[:-len(sufijo)]
            break
    
    # Si sigue siendo largo, tomar primeras palabras
    if len(nombre) > max_len:
        palabras = nombre.split()
        nombre_corto = ""
        for palabra in palabras:
            if len(nombre_corto) + len(palabra) + 1 <= max_len:
                nombre_corto += (" " if nombre_corto else "") + palabra
            else:
                break
        nombre = nombre_corto if nombre_corto else nombre[:max_len]
    
    return nombre.strip().upper()


# =============================================================================
# EXTRACCIÓN DE FECHA DEL PDF
# =============================================================================

def extraer_fecha_pdf(ruta_pdf: str) -> Optional[datetime]:
    """
    Extrae la fecha de factura de un PDF.
    
    Args:
        ruta_pdf: Ruta al archivo PDF
    
    Returns:
        datetime o None si no se encuentra
    """
    try:
        with pdfplumber.open(ruta_pdf) as pdf:
            texto = ""
            for page in pdf.pages[:2]:  # Solo primeras 2 páginas
                texto += page.extract_text() or ""
        
        return extraer_fecha_de_texto(texto)
    
    except Exception as e:
        print(f"      ⚠️ Error leyendo PDF: {e}")
        return None


def extraer_fecha_de_texto(texto: str) -> Optional[datetime]:
    """
    Extrae fecha de factura de un texto.
    
    Args:
        texto: Texto donde buscar
    
    Returns:
        datetime o None
    """
    if not texto:
        return None
    
    # Patrones de fecha (ordenados por especificidad)
    patrones = [
        # Fecha factura explícita: "Fecha factura: 15/01/2026"
        (r'fecha\s*(?:de\s*)?(?:factura|fra\.?|emisi[oó]n)[:\s]*(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{2,4})', 'dmy'),
        
        # Formato DD/MM/YYYY o DD-MM-YYYY
        (r'(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{4})', 'dmy'),
        
        # Formato DD/MM/YY
        (r'(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{2})(?!\d)', 'dmy_short'),
        
        # Formato "15 de enero de 2026"
        (r'(\d{1,2})\s+de\s+(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)\s+de\s+(\d{4})', 'texto'),
        
        # Formato "15-ene-2026" o "15-jan-2026"
        (r'(\d{1,2})[/\-.](ene|feb|mar|abr|may|jun|jul|ago|sep|oct|nov|dic|jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[/\-.](\d{2,4})', 'mes_corto'),
    ]
    
    meses_texto = {
        'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4, 'mayo': 5, 'junio': 6,
        'julio': 7, 'agosto': 8, 'septiembre': 9, 'octubre': 10, 'noviembre': 11, 'diciembre': 12
    }
    
    meses_corto = {
        'ene': 1, 'feb': 2, 'mar': 3, 'abr': 4, 'may': 5, 'jun': 6,
        'jul': 7, 'ago': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dic': 12,
        'jan': 1, 'apr': 4, 'aug': 8, 'dec': 12
    }
    
    texto_lower = texto.lower()
    
    for patron, tipo in patrones:
        matches = re.findall(patron, texto_lower)
        
        for match in matches:
            try:
                if tipo == 'dmy':
                    dia, mes, año = int(match[0]), int(match[1]), int(match[2])
                elif tipo == 'dmy_short':
                    dia, mes, año = int(match[0]), int(match[1]), int(match[2])
                    año = 2000 + año if año < 100 else año
                elif tipo == 'texto':
                    dia = int(match[0])
                    mes = meses_texto.get(match[1], 0)
                    año = int(match[2])
                elif tipo == 'mes_corto':
                    dia = int(match[0])
                    mes = meses_corto.get(match[1], 0)
                    año = int(match[2])
                    año = 2000 + año if año < 100 else año
                else:
                    continue
                
                # Validar fecha
                if 1 <= dia <= 31 and 1 <= mes <= 12 and 2020 <= año <= 2030:
                    return datetime(año, mes, dia)
            
            except (ValueError, IndexError):
                continue
    
    return None


# =============================================================================
# OBTENER TIPO DE PAGO
# =============================================================================

def obtener_tipo_pago(proveedor: str) -> str:
    """
    Obtiene el tipo de pago del proveedor desde el MAESTRO.
    
    Args:
        proveedor: Nombre del proveedor
    
    Returns:
        Tipo de pago (TF, RC, TJ, EF) o TF por defecto
    """
    if not proveedor:
        return "TF"
    
    info = obtener_info_proveedor(proveedor)
    
    # Buscar en columna FORMA_PAGO
    tipo = str(info.get('FORMA_PAGO', '')).strip().upper()
    
    if tipo in TIPOS_PAGO:
        return tipo
    
    # Fallback: TF (transferencia)
    return "TF"


# =============================================================================
# GENERAR NOMBRE DE ARCHIVO
# =============================================================================

def generar_nombre_archivo(
    proveedor: str,
    fecha_factura: datetime,
    fecha_proceso: datetime = None,
    extension: str = ".pdf",
    es_proforma: bool = False,
    numero_secuencial: int = None
) -> tuple[str, bool]:
    """
    Genera el nombre de archivo según nomenclatura.
    
    Args:
        proveedor: Nombre del proveedor
        fecha_factura: Fecha de la factura
        fecha_proceso: Fecha de procesamiento (default: hoy)
        extension: Extensión del archivo
        es_proforma: Si es una proforma
        numero_secuencial: Número si hay varias del mismo día
    
    Returns:
        Tuple (nombre_archivo, es_atrasada)
    """
    if fecha_proceso is None:
        fecha_proceso = datetime.now()
    
    # Calcular trimestres
    trimestre_factura = calcular_trimestre(fecha_factura)
    trimestre_proceso = calcular_trimestre(fecha_proceso)
    
    # ¿Es atrasada?
    es_atrasada = trimestre_factura != trimestre_proceso
    
    # Componentes del nombre
    xtyy = trimestre_factura  # 1T26, 4T25, etc.
    mmdd = fecha_factura.strftime("%m%d")  # 0115, 1002, etc.
    
    # Nombre del proveedor (abreviado y sanitizado)
    nombre_prov = abreviar_proveedor(proveedor)
    
    # Tipo de pago
    tipo_pago = obtener_tipo_pago(proveedor)
    
    # Construir nombre
    partes = []
    
    # Prefijo (si aplica)
    if es_proforma:
        partes.append(PREFIJO_PROFORMA)
    elif es_atrasada:
        partes.append(PREFIJO_ATRASADA)
    
    # Trimestre y fecha
    partes.append(xtyy)
    partes.append(mmdd)
    
    # Proveedor
    partes.append(nombre_prov)
    
    # Número secuencial (si hay varias del mismo día)
    if numero_secuencial and numero_secuencial > 1:
        partes.append(str(numero_secuencial))
    
    # Tipo de pago
    partes.append(tipo_pago)
    
    # Unir con espacios
    nombre = " ".join(partes)
    
    # Añadir extensión
    if not extension.startswith('.'):
        extension = '.' + extension
    
    nombre_final = nombre + extension.lower()
    
    return nombre_final, es_atrasada


# =============================================================================
# DETECTAR PROFORMA
# =============================================================================

def es_proforma(texto: str = None, nombre_archivo: str = None, asunto: str = None) -> bool:
    """
    Detecta si un documento es una proforma.
    
    Args:
        texto: Texto del PDF
        nombre_archivo: Nombre del archivo original
        asunto: Asunto del email
    
    Returns:
        True si es proforma
    """
    palabras_proforma = ['proforma', 'pro-forma', 'pro forma', 'presupuesto', 'cotizacion', 'cotización']
    
    # Buscar en nombre de archivo
    if nombre_archivo:
        nombre_lower = nombre_archivo.lower()
        if any(p in nombre_lower for p in palabras_proforma):
            return True
    
    # Buscar en asunto
    if asunto:
        asunto_lower = asunto.lower()
        if any(p in asunto_lower for p in palabras_proforma):
            return True
    
    # Buscar en texto del PDF (primeras líneas)
    if texto:
        texto_inicio = texto[:500].lower()
        if any(p in texto_inicio for p in palabras_proforma):
            return True
    
    return False


# =============================================================================
# CONTROL DE SECUENCIALES
# =============================================================================

class ControlSecuencial:
    """Controla números secuenciales para archivos del mismo día/proveedor."""
    
    def __init__(self):
        self.contador = {}  # {(proveedor, fecha): último_número}
    
    def obtener_siguiente(self, proveedor: str, fecha: datetime) -> int:
        """
        Obtiene el siguiente número secuencial.
        
        Args:
            proveedor: Nombre del proveedor
            fecha: Fecha de la factura
        
        Returns:
            Número secuencial (1, 2, 3...)
        """
        clave = (proveedor.upper(), fecha.strftime("%Y%m%d"))
        
        if clave not in self.contador:
            self.contador[clave] = 1
        else:
            self.contador[clave] += 1
        
        return self.contador[clave]
    
    def reiniciar(self):
        """Reinicia todos los contadores."""
        self.contador = {}


# Instancia global
control_secuencial = ControlSecuencial()


# =============================================================================
# FUNCIÓN PRINCIPAL DE RENOMBRADO
# =============================================================================

def procesar_renombrado(
    ruta_archivo: str,
    proveedor: str,
    asunto: str = None,
    fecha_proceso: datetime = None
) -> dict:
    """
    Procesa un archivo y genera su nuevo nombre.
    
    Args:
        ruta_archivo: Ruta al archivo en backup temporal
        proveedor: Nombre del proveedor identificado
        asunto: Asunto del email (para detectar proforma)
        fecha_proceso: Fecha de procesamiento
    
    Returns:
        Dict con información del renombrado
    """
    resultado = {
        'archivo_original': os.path.basename(ruta_archivo),
        'nombre_nuevo': None,
        'es_atrasada': False,
        'es_proforma': False,
        'fecha_factura': None,
        'trimestre': None,
        'tipo_pago': None,
        'proveedor_abreviado': None,
        'error': None
    }
    
    if fecha_proceso is None:
        fecha_proceso = datetime.now()
    
    # Obtener extensión
    extension = os.path.splitext(ruta_archivo)[1].lower()
    
    # Extraer fecha del PDF
    fecha_factura = None
    texto_pdf = None
    
    if extension == '.pdf':
        try:
            with pdfplumber.open(ruta_archivo) as pdf:
                texto_pdf = ""
                for page in pdf.pages[:2]:
                    texto_pdf += page.extract_text() or ""
            
            fecha_factura = extraer_fecha_de_texto(texto_pdf)
        except Exception as e:
            resultado['error'] = f"Error leyendo PDF: {e}"
    
    # Si no se encontró fecha, usar fecha de proceso
    if fecha_factura is None:
        fecha_factura = fecha_proceso
        resultado['error'] = "Fecha no extraída, usando fecha de proceso"
    
    resultado['fecha_factura'] = fecha_factura
    resultado['trimestre'] = calcular_trimestre(fecha_factura)
    
    # Detectar proforma
    nombre_original = os.path.basename(ruta_archivo)
    proforma = es_proforma(texto_pdf, nombre_original, asunto)
    resultado['es_proforma'] = proforma
    
    # Obtener número secuencial
    num_sec = control_secuencial.obtener_siguiente(proveedor, fecha_factura)
    
    # Generar nombre
    nombre_nuevo, es_atrasada = generar_nombre_archivo(
        proveedor=proveedor,
        fecha_factura=fecha_factura,
        fecha_proceso=fecha_proceso,
        extension=extension,
        es_proforma=proforma,
        numero_secuencial=num_sec if num_sec > 1 else None
    )
    
    resultado['nombre_nuevo'] = nombre_nuevo
    resultado['es_atrasada'] = es_atrasada
    resultado['tipo_pago'] = obtener_tipo_pago(proveedor)
    resultado['proveedor_abreviado'] = abreviar_proveedor(proveedor)
    
    return resultado


# =============================================================================
# TEST
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("TEST MÓDULO RENOMBRAR")
    print("=" * 60)
    
    # Test sanitización
    print("\n1. Test sanitización:")
    tests_sanitizar = [
        "JOSÉ GARCÍA S.L.",
        "Café Español (Madrid)",
        "Proveedor/Distribuidor",
        "ACEITES GARCÍA DE LA CRUZ S.L."
    ]
    for t in tests_sanitizar:
        print(f"   '{t}' → '{sanitizar_nombre(t)}'")
    
    # Test abreviar
    print("\n2. Test abreviar proveedor:")
    tests_abreviar = [
        "CERES CERVEZA SL",
        "KINEMA S.COOP.MAD.",
        "JAMONES Y EMBUTIDOS BERNAL SLU",
        "AGRICOLA DE MONTBRIO DEL CAMP SCCL",
        "MOLLETES ARTESANOS DE ANTEQUERA SL"
    ]
    for t in tests_abreviar:
        print(f"   '{t}' → '{abreviar_proveedor(t)}'")
    
    # Test extracción de fecha
    print("\n3. Test extracción de fecha:")
    tests_fecha = [
        "Fecha factura: 15/01/2026",
        "Fecha: 28-01-2026",
        "Emitida el 15 de enero de 2026",
        "Invoice date: 15-jan-2026",
        "Fecha 28/1/26"
    ]
    for t in tests_fecha:
        fecha = extraer_fecha_de_texto(t)
        print(f"   '{t}' → {fecha.strftime('%d/%m/%Y') if fecha else 'No encontrada'}")
    
    # Test generar nombre
    print("\n4. Test generar nombre:")
    fecha_factura = datetime(2026, 1, 15)
    fecha_proceso = datetime(2026, 1, 28)
    
    nombre, atrasada = generar_nombre_archivo(
        proveedor="CERES CERVEZA SL",
        fecha_factura=fecha_factura,
        fecha_proceso=fecha_proceso
    )
    print(f"   Normal: {nombre} (atrasada: {atrasada})")
    
    # Test atrasada
    fecha_factura_vieja = datetime(2025, 10, 2)
    nombre, atrasada = generar_nombre_archivo(
        proveedor="CERES CERVEZA SL",
        fecha_factura=fecha_factura_vieja,
        fecha_proceso=fecha_proceso
    )
    print(f"   Atrasada: {nombre} (atrasada: {atrasada})")
    
    # Test proforma
    nombre, atrasada = generar_nombre_archivo(
        proveedor="KINEMA S.COOP.MAD.",
        fecha_factura=fecha_factura,
        fecha_proceso=fecha_proceso,
        es_proforma=True
    )
    print(f"   Proforma: {nombre}")
    
    # Test secuencial
    print("\n5. Test secuencial (mismo proveedor/día):")
    control = ControlSecuencial()
    for i in range(3):
        num = control.obtener_siguiente("CERES", fecha_factura)
        nombre, _ = generar_nombre_archivo(
            proveedor="CERES CERVEZA SL",
            fecha_factura=fecha_factura,
            numero_secuencial=num if num > 1 else None
        )
        print(f"   #{i+1}: {nombre}")
