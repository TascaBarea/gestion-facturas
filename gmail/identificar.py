# -*- coding: utf-8 -*-
"""
IDENTIFICAR.PY - Módulo de identificación de proveedores
Gestión de facturas - TASCA BAREA S.L.L.

Sistema de puntos (2 de 3):
- Busca proveedor en: PDF, Asunto, Remitente
- Si 2+ coinciden → Confianza ALTA (automático)
- Si 0-1 coinciden → Confianza BAJA (preguntar)
"""

import os
import re
import pandas as pd
from typing import Optional
from thefuzz import fuzz, process

from gmail_config import (
    MAESTRO_PROVEEDORES,
    UMBRAL_FUZZY_PROVEEDOR,
    UMBRAL_FUZZY_INDICAR
)


# =============================================================================
# CARGA DEL MAESTRO DE PROVEEDORES
# =============================================================================

_maestro_cache = None

def cargar_maestro(verbose: bool = True) -> pd.DataFrame:
    """
    Carga el MAESTRO_PROVEEDORES (con cache).

    Returns:
        DataFrame con proveedores
    """
    global _maestro_cache

    if _maestro_cache is not None:
        return _maestro_cache

    if not os.path.exists(MAESTRO_PROVEEDORES):
        raise FileNotFoundError(f"No existe MAESTRO_PROVEEDORES: {MAESTRO_PROVEEDORES}")

    df = pd.read_excel(MAESTRO_PROVEEDORES)

    # Normalizar nombres de columnas
    df.columns = df.columns.str.strip().str.upper()

    _maestro_cache = df

    if verbose:
        _imprimir_estadisticas_maestro(df)

    return df


def _imprimir_estadisticas_maestro(df: pd.DataFrame):
    """Imprime resumen estadistico del MAESTRO_PROVEEDORES."""
    total = len(df)
    activos = (df["ACTIVO"].astype(str).str.upper() == "SI").sum() if "ACTIVO" in df.columns else total
    con_extractor = (df["TIENE_EXTRACTOR"].astype(str).str.upper() == "SI").sum() if "TIENE_EXTRACTOR" in df.columns else 0
    con_email = df["EMAIL"].notna().sum() if "EMAIL" in df.columns else 0
    con_cif = df["CIF"].notna().sum() if "CIF" in df.columns else 0
    con_iban = df["IBAN"].notna().sum() if "IBAN" in df.columns else 0

    n_alias = 0
    if "ALIAS" in df.columns:
        for val in df["ALIAS"].dropna():
            n_alias += len([a.strip() for a in str(val).split(",") if a.strip()])

    print(f"   MAESTRO: {total} proveedores ({activos} activos)")
    print(f"   Extractores: {con_extractor} | Emails: {con_email} | CIF: {con_cif} | IBAN: {con_iban} | Alias: {n_alias}")


def obtener_lista_proveedores() -> list[str]:
    """
    Obtiene lista de nombres de proveedores del MAESTRO.
    
    Returns:
        Lista de nombres de proveedores
    """
    df = cargar_maestro()
    
    # Buscar columna de proveedor
    columnas_posibles = ['PROVEEDOR', 'NOMBRE', 'TITULO', 'RAZÓN SOCIAL', 'RAZON SOCIAL']
    
    for col in columnas_posibles:
        if col in df.columns:
            proveedores = df[col].dropna().astype(str).tolist()
            return [p.strip() for p in proveedores if p.strip()]
    
    raise ValueError(f"No se encontró columna de proveedor en MAESTRO. Columnas: {list(df.columns)}")


def obtener_proveedores_con_alias() -> dict[str, str]:
    """
    Obtiene diccionario de alias → proveedor oficial.
    Incluye nombre oficial y todos los alias.
    
    Returns:
        Dict {alias_lowercase: nombre_proveedor_oficial}
    """
    df = cargar_maestro()
    
    alias_dict = {}
    
    for _, row in df.iterrows():
        proveedor = str(row.get('PROVEEDOR', '')).strip()
        if not proveedor or proveedor == 'nan':
            continue
        
        # Añadir nombre oficial
        alias_dict[proveedor.lower()] = proveedor
        
        # Añadir alias (separados por coma)
        alias_str = str(row.get('ALIAS', ''))
        if alias_str and alias_str != 'nan':
            for alias in alias_str.split(','):
                alias_limpio = alias.strip().lower()
                if alias_limpio:
                    alias_dict[alias_limpio] = proveedor
    
    return alias_dict


# Emails hardcoded (proveedores cuyo dominio no coincide con su razón social)
_EMAILS_HARDCODED = {
    'manuel@castrolaborda.com': 'PAGOS ALTOS DE ACERED, SL',
    'manuel@lajas.es': 'PAGOS ALTOS DE ACERED, SL',
}


def obtener_emails_proveedores() -> dict[str, str]:
    """
    Obtiene diccionario de email → proveedor del MAESTRO + hardcoded.

    Returns:
        Dict {email: nombre_proveedor}
    """
    # Empezar con hardcoded
    emails = dict(_EMAILS_HARDCODED)

    df = cargar_maestro()

    # Buscar columna de email (columna G según diseño)
    columnas_email = ['EMAIL', 'E-MAIL', 'CORREO', 'MAIL']
    columnas_proveedor = ['PROVEEDOR', 'NOMBRE', 'TITULO']

    col_email = None
    col_proveedor = None

    for col in columnas_email:
        if col in df.columns:
            col_email = col
            break

    for col in columnas_proveedor:
        if col in df.columns:
            col_proveedor = col
            break

    if col_email is None or col_proveedor is None:
        return emails

    for _, row in df.iterrows():
        email = str(row.get(col_email, '')).strip().lower()
        proveedor = str(row.get(col_proveedor, '')).strip()

        if email and proveedor and email != 'nan':
            emails[email] = proveedor

    return emails


def obtener_info_proveedor(nombre_proveedor: str) -> dict:
    """
    Obtiene información completa de un proveedor del MAESTRO.
    
    Args:
        nombre_proveedor: Nombre del proveedor
    
    Returns:
        Dict con toda la info del proveedor
    """
    df = cargar_maestro()
    
    # Buscar columna de proveedor
    col_proveedor = None
    for col in ['PROVEEDOR', 'NOMBRE', 'TITULO']:
        if col in df.columns:
            col_proveedor = col
            break
    
    if col_proveedor is None:
        return {}
    
    # Buscar proveedor (exacto o fuzzy)
    mask = df[col_proveedor].str.upper() == nombre_proveedor.upper()
    
    if mask.any():
        row = df[mask].iloc[0]
        return row.to_dict()
    
    # Intentar fuzzy match
    proveedores = obtener_lista_proveedores()
    match = process.extractOne(nombre_proveedor, proveedores, scorer=fuzz.token_sort_ratio)
    
    if match and match[1] >= UMBRAL_FUZZY_PROVEEDOR:
        nombre_encontrado = match[0]
        mask = df[col_proveedor].str.upper() == nombre_encontrado.upper()
        if mask.any():
            row = df[mask].iloc[0]
            return row.to_dict()
    
    return {}


# =============================================================================
# FUZZY MATCHING
# =============================================================================

def buscar_proveedor_en_texto(texto: str, umbral: int = None) -> tuple[Optional[str], int]:
    """
    Busca un proveedor en un texto usando fuzzy matching.
    Busca tanto en nombres oficiales como en alias.
    
    Args:
        texto: Texto donde buscar
        umbral: Umbral mínimo de similitud (default: 70)
    
    Returns:
        Tuple (nombre_proveedor_oficial, score) o (None, 0)
    """
    if not texto or not texto.strip():
        return None, 0
    
    if umbral is None:
        umbral = 70  # Umbral más bajo para capturar más coincidencias
    
    # Obtener alias y proveedores
    alias_dict = obtener_proveedores_con_alias()
    
    if not alias_dict:
        return None, 0
    
    # Limpiar texto
    texto_limpio = texto.lower().strip()
    
    # 1. Buscar coincidencia exacta primero
    if texto_limpio in alias_dict:
        return alias_dict[texto_limpio], 100
    
    # 2. Buscar si algún alias está contenido en el texto
    for alias, proveedor in alias_dict.items():
        if len(alias) >= 4 and alias in texto_limpio:
            return proveedor, 95
    
    # 3. Fuzzy matching contra todos los alias
    lista_alias = list(alias_dict.keys())
    resultado = process.extractOne(
        texto_limpio, 
        lista_alias, 
        scorer=fuzz.token_sort_ratio
    )
    
    if resultado and resultado[1] >= umbral:
        alias_encontrado = resultado[0]
        return alias_dict[alias_encontrado], resultado[1]
    
    # 4. Intentar con token_set_ratio (más flexible)
    resultado = process.extractOne(
        texto_limpio, 
        lista_alias, 
        scorer=fuzz.token_set_ratio
    )
    
    if resultado and resultado[1] >= umbral:
        alias_encontrado = resultado[0]
        return alias_dict[alias_encontrado], resultado[1]
    
    return None, 0


def extraer_dominio_email(email: str) -> str:
    """
    Extrae el dominio de un email.
    
    Args:
        email: Dirección de email
    
    Returns:
        Dominio (sin www, sin extensión común)
    """
    if not email:
        return ""
    
    # Extraer parte después de @
    match = re.search(r'@([\w.-]+)', email.lower())
    if not match:
        return ""
    
    dominio = match.group(1)
    
    # Quitar extensiones comunes
    dominio = re.sub(r'\.(com|es|org|net|eu|info)$', '', dominio)
    
    return dominio


def buscar_proveedor_por_email(email_remitente: str) -> tuple[Optional[str], int]:
    """
    Busca un proveedor por el email del remitente.
    
    Args:
        email_remitente: Email del remitente
    
    Returns:
        Tuple (nombre_proveedor, score) o (None, 0)
    """
    if not email_remitente:
        return None, 0
    
    # Extraer email limpio
    match = re.search(r'<([^>]+)>', email_remitente)
    if match:
        email = match.group(1).lower()
    else:
        email = email_remitente.lower().strip()
    
    # 1. Buscar coincidencia exacta en MAESTRO
    emails_maestro = obtener_emails_proveedores()
    
    if email in emails_maestro:
        return emails_maestro[email], 100
    
    # 2. Buscar por dominio
    dominio = extraer_dominio_email(email)
    
    if dominio:
        # Buscar dominio en lista de proveedores
        proveedor, score = buscar_proveedor_en_texto(dominio, umbral=UMBRAL_FUZZY_INDICAR)
        if proveedor:
            return proveedor, score
    
    # 3. Buscar nombre del remitente (antes del @)
    nombre_remitente = email.split('@')[0] if '@' in email else email
    nombre_remitente = re.sub(r'[._-]', ' ', nombre_remitente)
    
    if len(nombre_remitente) > 3:
        proveedor, score = buscar_proveedor_en_texto(nombre_remitente, umbral=UMBRAL_FUZZY_INDICAR)
        if proveedor:
            return proveedor, score
    
    return None, 0


# =============================================================================
# IDENTIFICACIÓN PRINCIPAL (SISTEMA 2 DE 3)
# =============================================================================

def identificar_proveedor(remitente: str, asunto: str, contenido_pdf: str = None) -> dict:
    """
    Identifica el proveedor usando sistema de puntos (2 de 3).
    
    Args:
        remitente: Email/nombre del remitente
        asunto: Asunto del email
        contenido_pdf: Texto extraído del PDF (opcional)
    
    Returns:
        Dict con resultado de identificación
    """
    resultado = {
        'proveedor': None,
        'confianza': 'BAJA',
        'score': 0,
        'fuentes': {
            'remitente': {'proveedor': None, 'score': 0},
            'asunto': {'proveedor': None, 'score': 0},
            'pdf': {'proveedor': None, 'score': 0}
        },
        'coincidencias': 0,
        'metodo': 'ninguno'
    }
    
    # 1. Buscar por remitente
    prov_remitente, score_remitente = buscar_proveedor_por_email(remitente)
    resultado['fuentes']['remitente'] = {
        'proveedor': prov_remitente,
        'score': score_remitente
    }
    
    # 2. Buscar en asunto
    prov_asunto, score_asunto = buscar_proveedor_en_texto(asunto)
    resultado['fuentes']['asunto'] = {
        'proveedor': prov_asunto,
        'score': score_asunto
    }
    
    # 3. Buscar en PDF (si disponible)
    if contenido_pdf:
        prov_pdf, score_pdf = buscar_proveedor_en_texto(contenido_pdf)
        resultado['fuentes']['pdf'] = {
            'proveedor': prov_pdf,
            'score': score_pdf
        }
    
    # Contar coincidencias
    proveedores_encontrados = {}
    
    for fuente, info in resultado['fuentes'].items():
        prov = info['proveedor']
        if prov:
            if prov not in proveedores_encontrados:
                proveedores_encontrados[prov] = {'count': 0, 'scores': [], 'fuentes': []}
            proveedores_encontrados[prov]['count'] += 1
            proveedores_encontrados[prov]['scores'].append(info['score'])
            proveedores_encontrados[prov]['fuentes'].append(fuente)
    
    if not proveedores_encontrados:
        resultado['metodo'] = 'no_encontrado'
        return resultado
    
    # Encontrar el proveedor con más coincidencias
    mejor_proveedor = None
    mejor_count = 0
    mejor_score = 0
    
    for prov, info in proveedores_encontrados.items():
        avg_score = sum(info['scores']) / len(info['scores'])
        if info['count'] > mejor_count or (info['count'] == mejor_count and avg_score > mejor_score):
            mejor_proveedor = prov
            mejor_count = info['count']
            mejor_score = avg_score
    
    resultado['proveedor'] = mejor_proveedor
    resultado['coincidencias'] = mejor_count
    resultado['score'] = int(mejor_score)
    
    # Determinar confianza
    if mejor_count >= 2:
        resultado['confianza'] = 'ALTA'
        resultado['metodo'] = f'{mejor_count}_de_3'
    elif mejor_count == 1 and mejor_score >= UMBRAL_FUZZY_PROVEEDOR:
        resultado['confianza'] = 'MEDIA'
        resultado['metodo'] = '1_de_3_score_alto'
    else:
        resultado['confianza'] = 'BAJA'
        resultado['metodo'] = '1_de_3_score_bajo'
    
    return resultado


# =============================================================================
# EXTRACCIÓN Y SUGERENCIA DE EMAILS
# =============================================================================

def extraer_email_limpio(remitente: str) -> str:
    """
    Extrae email limpio de un string de remitente.
    
    Args:
        remitente: String como "Nombre <email@dominio.com>"
    
    Returns:
        Email limpio en minúsculas
    """
    if not remitente:
        return ""
    
    # Buscar email entre < >
    match = re.search(r'<([^>]+)>', remitente)
    if match:
        return match.group(1).lower().strip()
    
    # Si no hay < >, asumir que todo es email
    if '@' in remitente:
        return remitente.lower().strip()
    
    return ""


def generar_sugerencias_email(emails_procesados: list[dict]) -> list[dict]:
    """
    Genera sugerencias de emails para añadir al MAESTRO.
    
    Args:
        emails_procesados: Lista de dicts con 'remitente', 'proveedor_identificado'
    
    Returns:
        Lista de sugerencias {proveedor, email_sugerido, confianza}
    """
    sugerencias = {}
    
    for item in emails_procesados:
        remitente = item.get('remitente', '')
        proveedor = item.get('proveedor_identificado')
        
        if not proveedor or not remitente:
            continue
        
        email = extraer_email_limpio(remitente)
        if not email:
            continue
        
        # Ignorar emails genéricos
        emails_genericos = ['noreply', 'no-reply', 'info@', 'envios@emailpdf']
        if any(gen in email for gen in emails_genericos):
            continue
        
        # Añadir sugerencia (priorizar el más frecuente)
        if proveedor not in sugerencias:
            sugerencias[proveedor] = {'email': email, 'count': 1}
        else:
            if sugerencias[proveedor]['email'] == email:
                sugerencias[proveedor]['count'] += 1
    
    # Convertir a lista
    resultado = []
    for proveedor, info in sugerencias.items():
        resultado.append({
            'proveedor': proveedor,
            'email_sugerido': info['email'],
            'frecuencia': info['count'],
            'confianza': 'ALTA' if info['count'] >= 2 else 'MEDIA'
        })
    
    return sorted(resultado, key=lambda x: x['frecuencia'], reverse=True)


def actualizar_emails_maestro(sugerencias: list[dict], ruta_maestro: str = None, 
                               solo_preview: bool = True) -> pd.DataFrame:
    """
    Actualiza el MAESTRO con los emails sugeridos.
    
    Args:
        sugerencias: Lista de sugerencias de generar_sugerencias_email()
        ruta_maestro: Ruta al archivo MAESTRO (default: MAESTRO_PROVEEDORES)
        solo_preview: Si True, solo muestra preview sin guardar
    
    Returns:
        DataFrame actualizado
    """
    if ruta_maestro is None:
        ruta_maestro = MAESTRO_PROVEEDORES
    
    df = pd.read_excel(ruta_maestro)
    
    actualizados = 0
    
    for sug in sugerencias:
        proveedor = sug['proveedor']
        email = sug['email_sugerido']
        
        # Buscar fila del proveedor
        mask = df['PROVEEDOR'].str.upper() == proveedor.upper()
        
        if mask.any():
            idx = df[mask].index[0]
            email_actual = df.loc[idx, 'EMAIL']
            
            # Solo actualizar si está vacío
            if pd.isna(email_actual) or str(email_actual).strip() == '':
                if solo_preview:
                    print(f"  [PREVIEW] {proveedor}: {email}")
                else:
                    df.loc[idx, 'EMAIL'] = email
                actualizados += 1
    
    if not solo_preview and actualizados > 0:
        df.to_excel(ruta_maestro, index=False)
        print(f"\n✅ Guardados {actualizados} emails en MAESTRO")
    
    return df


# =============================================================================
# INTERFAZ INTERACTIVA
# =============================================================================

def preguntar_proveedor(resultado_identificacion: dict, remitente: str, asunto: str) -> str:
    """
    Pregunta al usuario cuando la confianza es baja.
    
    Args:
        resultado_identificacion: Resultado de identificar_proveedor()
        remitente: Email del remitente
        asunto: Asunto del email
    
    Returns:
        Nombre del proveedor seleccionado
    """
    print("\n" + "=" * 50)
    print("⚠️  PROVEEDOR NO IDENTIFICADO CON CERTEZA")
    print("=" * 50)
    print(f"De: {remitente[:60]}")
    print(f"Asunto: {asunto[:60]}")
    
    # Mostrar opciones encontradas
    opciones = []
    fuentes = resultado_identificacion['fuentes']
    
    for fuente, info in fuentes.items():
        if info['proveedor']:
            if info['proveedor'] not in [o[0] for o in opciones]:
                opciones.append((info['proveedor'], info['score'], fuente))
    
    if opciones:
        print("\nOpciones encontradas:")
        for i, (prov, score, fuente) in enumerate(opciones, 1):
            print(f"  [{i}] {prov} (score: {score}%, fuente: {fuente})")
    
    print(f"  [M] Escribir nombre manualmente")
    print(f"  [S] Saltar este email")
    print(f"  [L] Listar todos los proveedores")
    
    while True:
        seleccion = input("\nSelecciona opción: ").strip().upper()
        
        if seleccion == 'S':
            return None
        
        if seleccion == 'L':
            proveedores = obtener_lista_proveedores()
            print("\nProveedores disponibles:")
            for i, p in enumerate(sorted(proveedores), 1):
                print(f"  {i:3}. {p}")
            continue
        
        if seleccion == 'M':
            nombre = input("Escribe el nombre del proveedor: ").strip()
            if nombre:
                # Verificar si existe
                proveedor, score = buscar_proveedor_en_texto(nombre, umbral=50)
                if proveedor:
                    confirmar = input(f"¿Te refieres a '{proveedor}'? (S/N): ").strip().upper()
                    if confirmar == 'S':
                        return proveedor
                    else:
                        print(f"Proveedor '{nombre}' no encontrado en MAESTRO")
                else:
                    print(f"Proveedor '{nombre}' no encontrado en MAESTRO")
            continue
        
        # Selección numérica
        try:
            idx = int(seleccion) - 1
            if 0 <= idx < len(opciones):
                return opciones[idx][0]
        except ValueError:
            pass
        
        print("Opción no válida. Intenta de nuevo.")


# =============================================================================
# TEST
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("TEST MÓDULO IDENTIFICAR")
    print("=" * 60)
    
    # Cargar maestro
    print("\n1. Cargando MAESTRO_PROVEEDORES...")
    try:
        df = cargar_maestro()
        print(f"   ✅ Cargado: {len(df)} proveedores")
        print(f"   Columnas: {list(df.columns)}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
        exit(1)
    
    # Listar algunos proveedores
    print("\n2. Primeros 10 proveedores:")
    proveedores = obtener_lista_proveedores()
    for p in proveedores[:10]:
        print(f"   - {p}")
    
    # Test fuzzy matching
    print("\n3. Test fuzzy matching (con ALIAS):")
    tests = [
        "CERES CERVEZA",
        "ceres",
        "KINEMA",
        "cooperativa kinema",
        "BERNAL",
        "jamones bernal",
        "QUESOS CATI",
        "BORBOTON",
        "molletes",
        "anthropic",
        "MONTBRIONE",
        "praizal",
    ]
    
    for texto in tests:
        prov, score = buscar_proveedor_en_texto(texto)
        if prov:
            print(f"   '{texto}' → {prov} ({score}%)")
        else:
            print(f"   '{texto}' → No encontrado")
    
    # Test identificación completa
    print("\n4. Test identificación completa:")
    casos = [
        {
            'remitente': 'envios@emailpdf.es',
            'asunto': 'Factura 06406_2613175_TASCA BAREA. CERES CERVEZA SL',
        },
        {
            'remitente': 'facturacion@cooperativakinema.es',
            'asunto': 'Su factura 000052',
        },
        {
            'remitente': 'pepejo@pepejolabrador.com',
            'asunto': 'FACTURA Nº 30',
        },
    ]
    
    for caso in casos:
        print(f"\n   De: {caso['remitente']}")
        print(f"   Asunto: {caso['asunto']}")
        
        resultado = identificar_proveedor(caso['remitente'], caso['asunto'])
        
        print(f"   → Proveedor: {resultado['proveedor']}")
        print(f"   → Confianza: {resultado['confianza']}")
        print(f"   → Coincidencias: {resultado['coincidencias']}/3")
