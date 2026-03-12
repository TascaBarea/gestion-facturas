#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
================================================================================
CUADRE.PY - Clasificador de Movimientos Bancarios
================================================================================

Versión: 1.5
Fecha: Marzo 2026
Autor: TASCA BAREA S.L.L.

DESCRIPCIÓN:
------------
Clasifica movimientos bancarios de un archivo Excel (con hojas Tasca, Comestibles
y Facturas) rellenando las columnas Categoria_Tipo y Categoria_Detalle.

CAMBIOS v1.5:
-------------
- Yoigo mejorado: regex Y?C\d{9,} + filtro XFERA/YOIGO/MASMOVIL + fuzzy fallback ≥90%
- Alquiler mejorado: busca las 2 facturas (Ortega + Fernández) del mes del movimiento
- Suscripciones ampliadas: SPOTIFY/NETFLIX/AMAZON (sin factura), MAKE.COM/OPENAI (con factura)
- Comunidad mejorada: asigna las 2 facturas ISTA METERING más cercanas en fecha

CAMBIOS v1.4:
-------------
- Fix: No registrar vínculo factura-movimiento si Categoria_Tipo = REVISAR
- Eliminadas columnas "Unnamed" del archivo de salida
- Formato de fecha DD-MM-YY en todas las hojas
- Mejora clasificador: usa fecha más cercana (≤60 días) para desempatar facturas

CAMBIOS v1.3:
-------------
- Bug fix: Columna Origen ahora busca "Cód." (antes buscaba "#" que no existía)
- Pagos parciales: GARCIA VIVAS y PANIFIESTO muestran "Pagos parciales (N)"
- Facturas con múltiples pagos ahora se vinculan correctamente

CAMBIOS v1.2:
-------------
- Bug fix: Verificar fuzzy ≥70% incluso cuando hay 1 sola factura
- Umbral fuzzy subido de 50% a 70%
- Nuevo tratamiento: COMUNIDAD DE VECINOS (detecta "COM PROP")
- Nuevo tratamiento: LOYVERSE (suscripción sin factura)
- Mejorado mensaje de duplicados: "Posible duplicado con #XXXX"
- Nuevo: Archivo de LOG con decisiones tomadas
- Indicar fuzzy% en detalle cuando es <85%

CAMBIOS v1.1:
-------------
- Nueva columna "Origen" en hoja Facturas (indica movimiento asociado: T 11, C 21...)
- Corregido bug: facturas_usadas ahora es global entre hojas (evita duplicados)
- Corregido bug: Som Energia y Yoigo ahora añaden a facturas_usadas

FLUJO:
------
1. Seleccionar archivo Excel de entrada (GUI Windows)
2. Cargar MAESTRO_PROVEEDORES.xlsx para matching de nombres
3. Clasificar cada movimiento usando los clasificadores específicos
4. Generar archivo de salida: Cuadre_DDMMYY-DDMMYY.xlsx
   - Hojas Tasca/Comestibles con Categoria_Tipo y Categoria_Detalle
   - Hoja Facturas con nueva columna Origen
5. Generar archivo de LOG: Cuadre_DDMMYY-DDMMYY_log.txt

CLASIFICADORES:
---------------
- TPV: ABONO TPV, COMISIONES TPV
- Transferencia: TRANSFERENCIA A ...
- Compra Tarjeta: COMPRA TARJ. ...
- Adeudo/Recibo: ADEUDO RECIBO ...
- Som Energia: ... SOM ENERGIA ...
- Yoigo: ... YOIGO ...
- Comunidad de Vecinos: ADEUDO RECIBO COM PROP ...
- Suscripciones: LOYVERSE
- Casos Simples: TRASPASO, IMPUESTOS, NÓMINA, INGRESO

REQUISITOS:
-----------
    pip install pandas openpyxl rapidfuzz

USO:
----
    python cuadre.py

================================================================================
"""

from __future__ import annotations

import os
import sys
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

import pandas as pd

# GUI Windows (opcional para entornos sin display)
try:
    import tkinter as tk
    from tkinter import filedialog, messagebox
    TKINTER_AVAILABLE = True
except ImportError:
    TKINTER_AVAILABLE = False
    tk = None
    filedialog = None
    messagebox = None

# Fuzzy matching
from rapidfuzz import fuzz


# ==============================================================================
# CONFIGURACIÓN
# ==============================================================================

# Ruta al MAESTRO_PROVEEDORES (relativa al script o absoluta)
MAESTRO_PATH = Path(r"C:\_ARCHIVOS\TRABAJO\Facturas\gestion-facturas\datos\MAESTRO_PROVEEDORES.xlsx")

# Directorio de salida
OUTPUT_DIR = Path(r"C:\_ARCHIVOS\TRABAJO\Facturas\gestion-facturas\outputs")

# Hojas esperadas en el archivo de entrada
HOJAS_MOVIMIENTOS = ["Tasca ", "Tasca", "TASCA", "Comestibles", "COMESTIBLES"]
HOJA_FACTURAS = "Facturas"

# Mapeo de columnas: Excel entrada → nombre interno clasificadores
MAPEO_FACTURAS = {
    "#": "Cód.",
    "TITULO": "Título", 
    "TOTAL FACTURA": "Total",
    "Fec.Fac.": "Fec.Fac.",
    "REF": "Factura",
}

# Comercios TPV conocidos
COMERCIOS_TPV = {
    "0337410674": "TASCA",
    "0354768939": "COMESTIBLES",
    "0354272759": "TALLERES",
}

# Casos especiales para compra tarjeta
REGLAS_ESPECIALES_TARJETA = [
    {"clave": "PANIFIESTO LAVAPIES", "titulo": "PANIFIESTO LAVAPIES SL"},
    {"clave": "AY MADRE LA FRUTA", "titulo": "GARCIA VIVAS JULIO"},
]

# Suscripciones sin factura (no generan factura fiscal)
SUSCRIPCIONES_SIN_FACTURA = [
    {"clave": "LOYVERSE", "tipo": "LOYVERSE", "detalle": "Sin factura"},
    {"clave": "SPOTIFY", "tipo": "GASTOS VARIOS", "detalle": "Sin factura"},
    {"clave": "NETFLIX", "tipo": "GASTOS VARIOS", "detalle": "Sin factura"},
    {"clave": "AMAZON PRIME", "tipo": "GASTOS VARIOS", "detalle": "Sin factura"},
]

# Suscripciones CON factura (texto en concepto → título en facturas)
SUSCRIPCIONES_CON_FACTURA = [
    {"clave": "MAKE.COM", "titulo": "CELONIS INC.", "aliases": ["CELONIS", "MAKE"]},
    {"clave": "OPENAI", "titulo": "OPENAI LLC", "aliases": ["OPENAI", "CHATGPT"]},
]

# NUEVO v1.2: Umbral de fuzzy para asignación automática
UMBRAL_FUZZY_MINIMO = 0.70  # 70%
UMBRAL_FUZZY_INDICAR = 0.85  # Por debajo de este, indicar % en detalle


# ==============================================================================
# ESTADO GLOBAL PARA EVITAR DUPLICADOS Y REGISTRAR VÍNCULOS
# ==============================================================================

facturas_usadas: set = set()
remesas_usadas: set = set()

# v1.1: Registro de vínculos factura → movimiento(s)
# Estructura: {factura_id: [("T", 11), ("C", 21), ...]}
vinculos_factura_movimiento: Dict[int, List[Tuple[str, int]]] = {}

# NUEVO v1.2: Log de decisiones
log_decisiones: List[str] = []


def reset_estado_global_inicio():
    """
    Reinicia el estado global al INICIO del proceso completo.
    Se llama UNA VEZ antes de procesar todas las hojas.
    """
    global facturas_usadas, remesas_usadas, vinculos_factura_movimiento, log_decisiones
    facturas_usadas = set()
    remesas_usadas = set()
    vinculos_factura_movimiento = {}
    log_decisiones = []


def reset_estado_por_hoja():
    """
    Reinicia solo el estado específico de cada hoja (remesas TPV).
    facturas_usadas NO se reinicia para evitar duplicados entre hojas.
    """
    global remesas_usadas
    remesas_usadas = set()


# ==============================================================================
# SISTEMA DE LOG (NUEVO v1.2)
# ==============================================================================

def log(mensaje: str):
    """Añade un mensaje al log de decisiones."""
    global log_decisiones
    log_decisiones.append(mensaje)


def guardar_log(ruta_salida: Path):
    """Guarda el log de decisiones en un archivo .txt"""
    global log_decisiones
    
    ruta_log = ruta_salida.with_suffix(".txt")
    ruta_log = Path(str(ruta_log).replace(".xlsx", "_log.txt"))
    
    try:
        with open(ruta_log, "w", encoding="utf-8") as f:
            f.write("=" * 80 + "\n")
            f.write("LOG DE DECISIONES - CUADRE v1.5\n")
            f.write(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 80 + "\n\n")
            
            for linea in log_decisiones:
                f.write(linea + "\n")
        
        print(f"   📝 Log guardado: {ruta_log.name}")
        return ruta_log
    except Exception as e:
        print(f"   ⚠️  Error guardando log: {e}")
        return None


# ==============================================================================
# REGISTRO DE VÍNCULOS FACTURA ↔ MOVIMIENTO (v1.1)
# ==============================================================================

def registrar_vinculo_factura(tipo: str, detalle: str, nombre_hoja: str, mov_num: int):
    """
    Extrae #XXXX del detalle y registra el vínculo factura → movimiento.
    
    MODIFICADO v1.4: No registra si tipo = "REVISAR"
    
    Args:
        tipo: Categoria_Tipo del movimiento
        detalle: Categoria_Detalle que puede contener "#XXXX"
        nombre_hoja: Nombre de la hoja (Tasca, Comestibles)
        mov_num: Número del movimiento (#)
    """
    global vinculos_factura_movimiento
    
    # NUEVO v1.4: No registrar vínculo si está marcado como REVISAR
    if tipo == "REVISAR":
        return
    
    if not detalle:
        return
    
    # Buscar todos los #XXXX en el detalle (puede haber varios en "ver también")
    matches = re.findall(r'#(\d+)', str(detalle))
    
    if not matches:
        return
    
    # Determinar prefijo: T para Tasca, C para Comestibles
    nombre_lower = nombre_hoja.lower().strip()
    if "tasca" in nombre_lower:
        prefijo = "T"
    elif "comestibles" in nombre_lower:
        prefijo = "C"
    else:
        prefijo = "?"
    
    # Solo registrar el PRIMER match (el principal, no los "ver también")
    fac_id = int(matches[0])
    
    if fac_id not in vinculos_factura_movimiento:
        vinculos_factura_movimiento[fac_id] = []
    
    # Evitar duplicados
    vinculo = (prefijo, mov_num)
    if vinculo not in vinculos_factura_movimiento[fac_id]:
        vinculos_factura_movimiento[fac_id].append(vinculo)


def generar_columna_origen(df_fact_original: pd.DataFrame) -> pd.Series:
    """
    Genera la columna Origen para la hoja Facturas.
    
    Formato:
    - Hasta 4 movimientos: "T 11, T 291, T 529, C 42"
    - Más de 4: "T 11, T 291, T 529, T 600 (+2)"
    - Pagos parciales (GARCIA VIVAS, PANIFIESTO): "Pagos parciales (17)"
    - Sin movimiento: ""
    
    Args:
        df_fact_original: DataFrame de Facturas con columna "Cód." o "#"
    
    Returns:
        Series con los valores de Origen
    """
    global vinculos_factura_movimiento
    
    # Proveedores con pagos parciales (muchas compras pequeñas → 1 factura mensual)
    PROVEEDORES_PAGOS_PARCIALES = ["GARCIA VIVAS", "PANIFIESTO"]
    
    origenes = []
    
    for _, row in df_fact_original.iterrows():
        # CORREGIDO v1.3: Buscar "Cód." primero, luego "#" como fallback
        fac_id = row.get("Cód.") or row.get("#")
        
        if fac_id is None or pd.isna(fac_id):
            origenes.append("")
            continue
        
        try:
            fac_id = int(fac_id)
        except (ValueError, TypeError):
            origenes.append("")
            continue
        
        if fac_id not in vinculos_factura_movimiento:
            origenes.append("")
            continue
        
        refs = vinculos_factura_movimiento[fac_id]
        
        # Ordenar por número de movimiento (mezclando T y C)
        refs_sorted = sorted(refs, key=lambda x: x[1])
        
        # NUEVO v1.3: Verificar si es proveedor de pagos parciales
        titulo = str(row.get("Título", "")).upper()
        es_pago_parcial = any(prov in titulo for prov in PROVEEDORES_PAGOS_PARCIALES)
        
        if es_pago_parcial and len(refs_sorted) > 1:
            # Formato especial para pagos parciales
            origen = f"Pagos parciales ({len(refs_sorted)})"
        elif len(refs_sorted) <= 4:
            origen = ", ".join([f"{h} {n}" for h, n in refs_sorted])
        else:
            primeros = ", ".join([f"{h} {n}" for h, n in refs_sorted[:4]])
            resto = len(refs_sorted) - 4
            origen = f"{primeros} (+{resto})"
        
        origenes.append(origen)
    
    return pd.Series(origenes)


# ==============================================================================
# UTILIDADES
# ==============================================================================

def formatear_fechas_df(df: pd.DataFrame) -> pd.DataFrame:
    """
    Formatea todas las columnas de fecha al formato DD-MM-YY.
    
    Args:
        df: DataFrame a procesar
    
    Returns:
        DataFrame con fechas formateadas
    """
    df = df.copy()
    
    # Columnas que contienen fechas
    columnas_fecha = ["F. Operativa", "F. Valor", "Fec.Fac."]
    
    for col in columnas_fecha:
        if col in df.columns:
            # Convertir a datetime y formatear
            df[col] = pd.to_datetime(df[col], errors="coerce", dayfirst=True)
            df[col] = df[col].dt.strftime("%d-%m-%y")
            # Reemplazar NaT (fechas inválidas) con vacío
            df[col] = df[col].fillna("")
    
    return df


def eliminar_columnas_unnamed(df: pd.DataFrame) -> pd.DataFrame:
    """
    Elimina columnas que empiezan con 'Unnamed'.
    
    Args:
        df: DataFrame a procesar
    
    Returns:
        DataFrame sin columnas Unnamed
    """
    cols_a_eliminar = [col for col in df.columns if str(col).startswith("Unnamed")]
    if cols_a_eliminar:
        df = df.drop(columns=cols_a_eliminar)
    return df


def normalizar_nombre(nombre: str) -> str:
    """Normaliza un nombre para comparación: mayúsculas, sin sufijos societarios."""
    if not isinstance(nombre, str):
        return ""
    import unicodedata
    nombre = unicodedata.normalize("NFKD", nombre)
    nombre = "".join(c for c in nombre if not unicodedata.combining(c))
    nombre = nombre.upper().strip()
    for suf in ["S.L.L.", "S.L.U.", "S.L.", "SL", "S.A.", "SA", "S.C.A.", "SCA", "S.COOP."]:
        nombre = nombre.replace(suf, "")
    return " ".join(nombre.split())


def calcular_similitud(a: str, b: str) -> float:
    """Calcula similitud entre dos strings usando fuzzy matching."""
    return fuzz.token_sort_ratio(normalizar_nombre(a), normalizar_nombre(b)) / 100


def calcular_similitud_con_aliases(nombre_emisor: str, titulo_factura: str, df_fuzzy: pd.DataFrame) -> float:
    """
    Calcula similitud entre nombre_emisor y titulo_factura,
    probando también todos los aliases del proveedor en df_fuzzy.

    Devuelve el mejor score entre:
    - Comparación directa nombre_emisor vs titulo_factura
    - Cada alias del proveedor (NOMBRE_EN_CONCEPTO) vs titulo_factura
    """
    mejor_score = calcular_similitud(nombre_emisor, titulo_factura)

    titulo_norm = normalizar_nombre(titulo_factura)
    aliases = df_fuzzy.loc[df_fuzzy["TITULO_FACTURA"] == nombre_emisor, "NOMBRE_EN_CONCEPTO"]

    for alias_norm in aliases:
        score = fuzz.token_sort_ratio(alias_norm, titulo_norm) / 100
        if score > mejor_score:
            mejor_score = score

    return mejor_score


def buscar_factura_candidata(
    nombre_emisor: str,
    importe: float,
    fecha_valor,
    fecha_operativa,
    df_fact: pd.DataFrame,
    df_fuzzy: pd.DataFrame,
    facturas_usadas: set,
    incluir_ref: bool = False,
    log_candidatas: bool = True,
) -> Tuple[str, str]:
    """
    Busca la mejor factura candidata para un movimiento bancario.

    Lógica común a transferencias, compras tarjeta y adeudos/recibos:
    1. Buscar facturas por importe
    2. Calcular fuzzy scores con aliases
    3. Filtrar por umbral 70%
    4. Filtrar ya usadas
    5. Desempatar por fecha (<=60 días, más cercana)
    6. Fallback por mejor fuzzy si no hay fecha

    Args:
        nombre_emisor: Nombre del emisor (ya resuelto por buscar_mejor_alias)
        importe: Importe del movimiento
        fecha_valor: Fecha valor del movimiento
        fecha_operativa: Fecha operativa (None para adeudo_recibo)
        df_fact: DataFrame de facturas
        df_fuzzy: DataFrame de aliases
        facturas_usadas: Set de códigos de factura ya asignados (se muta)
        incluir_ref: Si True, añade campo Factura al detalle (adeudo_recibo)
        log_candidatas: Si True, logea cada candidata individual

    Returns:
        (Categoria_Tipo, Categoria_Detalle)
    """
    # Buscar facturas por importe
    importe_abs = round(abs(float(importe)), 2)
    candidatas = df_fact[abs(df_fact["Total"] - importe_abs) <= 0.01].copy()

    if candidatas.empty:
        log(f"  → REVISAR: Importe {importe_abs} no encontrado")
        return "REVISAR", f"Importe {importe_abs} no encontrado"

    log(f"  Candidatas por importe {importe_abs}€: {len(candidatas)}")

    # Calcular score fuzzy para todas las candidatas (usando aliases del MAESTRO)
    candidatas["_score"] = candidatas["Título"].apply(
        lambda t: calcular_similitud_con_aliases(nombre_emisor, t, df_fuzzy)
    )

    if log_candidatas:
        for _, row in candidatas.iterrows():
            log(f"    - #{row['Cód.']} {row['Título']}: fuzzy {row['_score']*100:.1f}%")

    # Filtrar por umbral fuzzy (>=70%)
    candidatas_fuzzy = candidatas[candidatas["_score"] >= UMBRAL_FUZZY_MINIMO].copy()

    # CASO: Ninguna pasa el filtro fuzzy
    if candidatas_fuzzy.empty:
        mejor = candidatas.loc[candidatas["_score"].idxmax()]
        log(f"  → REVISAR: Ninguna supera fuzzy {UMBRAL_FUZZY_MINIMO*100:.0f}%")
        return "REVISAR", f"¿#{mejor['Cód.']} {mejor['Título']}? (fuzzy {mejor['_score']*100:.0f}%)"

    # Filtrar las ya usadas
    candidatas_disponibles = candidatas_fuzzy[~candidatas_fuzzy["Cód."].isin(facturas_usadas)].copy()

    # CASO: Todas las que pasan fuzzy ya están usadas
    if candidatas_disponibles.empty:
        mejor_usada = candidatas_fuzzy.loc[candidatas_fuzzy["_score"].idxmax()]
        log(f"  → REVISAR: Factura #{mejor_usada['Cód.']} ya usada")
        return "REVISAR", f"Posible duplicado con #{mejor_usada['Cód.']}"

    # Usar fecha para desempatar
    candidatas_disponibles["Fec.Fac."] = pd.to_datetime(
        candidatas_disponibles["Fec.Fac."], errors="coerce", dayfirst=True
    )
    fecha_mov = pd.to_datetime(fecha_valor, errors="coerce", dayfirst=True)
    if pd.isna(fecha_mov) and fecha_operativa is not None:
        fecha_mov = pd.to_datetime(fecha_operativa, errors="coerce", dayfirst=True)

    if pd.notna(fecha_mov):
        # Filtrar facturas anteriores o iguales al movimiento
        anteriores = candidatas_disponibles[candidatas_disponibles["Fec.Fac."] <= fecha_mov].copy()

        if not anteriores.empty:
            # Calcular días de diferencia
            anteriores["_dias"] = (fecha_mov - anteriores["Fec.Fac."]).dt.days

            # Filtrar por máximo 60 días de antigüedad
            dentro_plazo = anteriores[anteriores["_dias"] <= 60].copy()

            if not dentro_plazo.empty:
                # Elegir la más cercana en fecha
                dentro_plazo = dentro_plazo.sort_values("_dias")
                fila = dentro_plazo.iloc[0]
                cod = fila["Cód."]
                titulo = fila["Título"]
                score = fila["_score"]
                dias = fila["_dias"]

                facturas_usadas.add(cod)
                detalle = formatear_detalle_factura(cod, titulo, score, es_fuzzy=True)
                if incluir_ref:
                    ref = fila.get("Factura", "")
                    if pd.notna(ref) and str(ref).strip():
                        detalle += f" ({ref})"
                log(f"  → ASIGNADO: {titulo} {detalle} (fecha: {dias} días antes)")
                return titulo, detalle
            else:
                # Todas las anteriores están fuera del plazo de 60 días
                mejor = anteriores.sort_values("_dias").iloc[0]
                log(f"  → REVISAR: Factura #{mejor['Cód.']} muy antigua ({mejor['_dias']} días)")
                return "REVISAR", f"#{mejor['Cód.']} muy antigua ({mejor['_dias']} días)"
        else:
            # No hay facturas anteriores al movimiento
            log(f"  → REVISAR: No hay facturas anteriores al movimiento")
            return "REVISAR", f"No hay facturas anteriores a {fecha_mov.strftime('%d/%m/%Y')}"

    # Si no hay fecha válida, elegir por mejor fuzzy
    fila = candidatas_disponibles.loc[candidatas_disponibles["_score"].idxmax()]
    cod = fila["Cód."]
    titulo = fila["Título"]
    score = fila["_score"]

    facturas_usadas.add(cod)
    detalle = formatear_detalle_factura(cod, titulo, score, es_fuzzy=True)
    if incluir_ref:
        ref = fila.get("Factura", "")
        if pd.notna(ref) and str(ref).strip():
            detalle += f" ({ref})"

    log(f"  → ASIGNADO: {titulo} {detalle}")
    return titulo, detalle


def construir_df_fuzzy(df_maestro: pd.DataFrame) -> pd.DataFrame:
    """
    Construye el DataFrame de fuzzy matching desde MAESTRO_PROVEEDORES.
    
    Expande la columna ALIAS (separada por comas) en múltiples filas,
    cada una mapeando un alias al nombre del proveedor.
    
    Returns:
        DataFrame con columnas: NOMBRE_EN_CONCEPTO, TITULO_FACTURA
    """
    rows = []
    
    for _, row in df_maestro.iterrows():
        proveedor = str(row.get("PROVEEDOR", "")).strip()
        alias_str = str(row.get("ALIAS", "")).strip()
        
        if not proveedor:
            continue
            
        # Siempre incluir el nombre del proveedor como alias de sí mismo
        rows.append({
            "NOMBRE_EN_CONCEPTO": normalizar_nombre(proveedor),
            "TITULO_FACTURA": proveedor
        })
        
        # Expandir alias separados por coma
        if alias_str and alias_str.lower() != "nan":
            for alias in alias_str.split(","):
                alias_clean = alias.strip()
                if alias_clean:
                    rows.append({
                        "NOMBRE_EN_CONCEPTO": normalizar_nombre(alias_clean),
                        "TITULO_FACTURA": proveedor
                    })
    
    return pd.DataFrame(rows)


def construir_indice_aliases(df_fuzzy: pd.DataFrame) -> Dict[str, str]:
    """
    Construye un diccionario de búsqueda rápida desde df_fuzzy.

    Se llama 1 vez al cargar. Reemplaza iterrows() en buscar_mejor_alias().

    Returns:
        Dict {NOMBRE_EN_CONCEPTO: TITULO_FACTURA}
    """
    return dict(zip(df_fuzzy["NOMBRE_EN_CONCEPTO"], df_fuzzy["TITULO_FACTURA"]))


def buscar_mejor_alias(nombre_concepto: str, indice_aliases: Dict[str, str]) -> Tuple[str, bool]:
    """
    Busca el mejor match en indice_aliases para un nombre del concepto bancario.

    Args:
        nombre_concepto: Nombre extraído del concepto (ej: "CERES CERVEZA S L")
        indice_aliases: Dict {NOMBRE_EN_CONCEPTO: TITULO_FACTURA}

    Returns:
        Tuple (TITULO_FACTURA del mejor match, encontrado_en_alias)
        - encontrado_en_alias: True si se encontró en MAESTRO, False si no
    """
    nombre_norm = normalizar_nombre(nombre_concepto)

    if not indice_aliases:
        return nombre_concepto, False

    # Buscar match exacto primero — O(1)
    exact = indice_aliases.get(nombre_norm)
    if exact is not None:
        return exact, True

    # Buscar mejor match por similitud (≥85% para considerarse "encontrado")
    mejor_score = 0
    mejor_titulo = nombre_concepto

    for alias, titulo in indice_aliases.items():
        score = calcular_similitud(nombre_concepto, alias)
        if score > mejor_score:
            mejor_score = score
            mejor_titulo = titulo

    # Solo considerar "encontrado en alias" si score ≥ 85%
    encontrado = mejor_score >= 0.85

    if mejor_score >= 0.60:
        return mejor_titulo, encontrado
    else:
        return nombre_concepto, False


def formatear_detalle_factura(cod, titulo: str, score: float, es_fuzzy: bool = False) -> str:
    """
    Formatea el detalle de la factura asignada.
    
    NUEVO v1.2: Indica fuzzy% si es <85%
    """
    if es_fuzzy and score < UMBRAL_FUZZY_INDICAR:
        return f"#{cod} (fuzzy {score*100:.0f}%)"
    else:
        return f"#{cod}"


# ==============================================================================
# CLASIFICADORES ESPECIALES (NUEVO v1.2)
# ==============================================================================

def clasificar_comunidad_vecinos(concepto: str, fecha_valor=None, df_fact=None) -> Tuple[Optional[str], Optional[str]]:
    """
    Clasifica gastos de comunidad de vecinos y asigna facturas ISTA.

    v1.5: Busca las 2 facturas ISTA METERING más cercanas en fecha.
    El pago de comunidad incluye gastos de agua (ISTA).

    Returns:
        (Categoria_Tipo, Categoria_Detalle) o (None, None) si no aplica
    """
    global facturas_usadas
    concepto_upper = str(concepto).upper().strip()

    if "COM PROP" not in concepto_upper and "COMUNIDAD PROP" not in concepto_upper:
        return None, None

    # Buscar facturas ISTA METERING para vincular
    if df_fact is not None and fecha_valor is not None:
        df_ista = df_fact[
            df_fact["Título"].str.upper().str.contains("ISTA METERING", na=False)
        ].copy()

        if not df_ista.empty:
            df_ista["Fec.Fac."] = pd.to_datetime(df_ista["Fec.Fac."], errors="coerce", dayfirst=True)
            fecha_mov = pd.to_datetime(fecha_valor, errors="coerce", dayfirst=True)

            if pd.notna(fecha_mov):
                df_disponibles = df_ista[~df_ista["Cód."].isin(facturas_usadas)].copy()
                if not df_disponibles.empty:
                    df_disponibles["dist"] = abs((df_disponibles["Fec.Fac."] - fecha_mov).dt.days)
                    df_disponibles = df_disponibles.sort_values("dist")

                    facturas_asignadas = []
                    for _, fila in df_disponibles.head(2).iterrows():
                        cod = fila["Cód."]
                        facturas_usadas.add(cod)
                        facturas_asignadas.append(f"#{cod}")

                    if facturas_asignadas:
                        detalle = ", ".join(facturas_asignadas)
                        log(f"  → COMUNIDAD DE VECINOS: {detalle}")
                        return "COMUNIDAD DE VECINOS", detalle

    log(f"  → COMUNIDAD DE VECINOS detectada")
    return "COMUNIDAD DE VECINOS", ""


def clasificar_suscripciones(concepto: str, fecha_valor=None, df_fact=None) -> Tuple[Optional[str], Optional[str]]:
    """
    Clasifica suscripciones: sin factura (SPOTIFY, NETFLIX, LOYVERSE, AMAZON PRIME)
    y con factura (MAKE.COM→CELONIS, OPENAI→OPENAI LLC).

    Returns:
        (Categoria_Tipo, Categoria_Detalle) o (None, None) si no aplica
    """
    global facturas_usadas
    concepto_upper = str(concepto).upper()

    # --- Sin factura ---
    for suscripcion in SUSCRIPCIONES_SIN_FACTURA:
        if suscripcion["clave"] in concepto_upper:
            log(f"  → Suscripción detectada: {suscripcion['tipo']}")
            return suscripcion["tipo"], suscripcion["detalle"]

    # --- Con factura (buscar por mes) ---
    if df_fact is not None and fecha_valor is not None:
        for suscripcion in SUSCRIPCIONES_CON_FACTURA:
            if suscripcion["clave"] in concepto_upper:
                titulo = suscripcion["titulo"]
                patron = "|".join([titulo.upper()] + [a.upper() for a in suscripcion["aliases"]])
                df_prov = df_fact[
                    df_fact["Título"].str.upper().str.contains(patron, na=False, regex=True)
                ].copy()

                if df_prov.empty:
                    log(f"  → REVISAR: No hay facturas de {titulo}")
                    return "REVISAR", f"No hay facturas de {titulo}"

                fecha_v = pd.to_datetime(fecha_valor, errors="coerce", dayfirst=True)
                if pd.isna(fecha_v):
                    log(f"  → REVISAR: {titulo} - fecha inválida")
                    return "REVISAR", f"{titulo} - fecha inválida"

                df_prov["Fec.Fac."] = pd.to_datetime(df_prov["Fec.Fac."], errors="coerce", dayfirst=True)
                mismo_mes = df_prov[
                    (df_prov["Fec.Fac."].dt.month == fecha_v.month) &
                    (df_prov["Fec.Fac."].dt.year == fecha_v.year) &
                    (~df_prov["Cód."].isin(facturas_usadas))
                ]

                if not mismo_mes.empty:
                    cod = mismo_mes.iloc[0]["Cód."]
                    facturas_usadas.add(cod)
                    es_anul = "ANUL" in concepto_upper
                    detalle = f"#{cod} {titulo}"
                    if es_anul:
                        detalle = f"ANULACIÓN - {detalle}"
                    log(f"  → Suscripción {titulo}: {detalle}")
                    return titulo, detalle

                log(f"  → REVISAR: Sin factura de {titulo} para {fecha_v.strftime('%m/%Y')}")
                return "REVISAR", f"Sin factura de {titulo} para {fecha_v.strftime('%m/%Y')}"

    return None, None


# ==============================================================================
# CLASIFICADORES
# ==============================================================================

def clasificar_tpv(concepto: str, fecha_valor, importe: float, df_mov: pd.DataFrame) -> Tuple[Optional[str], Optional[str]]:
    """
    Clasifica movimientos TPV (ABONO TPV y COMISIONES).
    
    Returns:
        (Categoria_Tipo, Categoria_Detalle) o (None, None) si no aplica
    """
    global remesas_usadas
    
    concepto = concepto.upper().strip()
    
    if not (concepto.startswith("ABONO TPV") or concepto.startswith("COMISIONES")):
        return None, None
    
    # Detectar número de comercio
    comercio_match = re.search(r"\b(0337410674|0354768939|0354272759)\b", concepto)
    if not comercio_match:
        log(f"  → TPV: Número de Comercio desconocido")
        return "REVISAR", "Número de Comercio desconocido"
    
    numero_comercio = comercio_match.group()
    nombre_comercio = COMERCIOS_TPV.get(numero_comercio, "DESCONOCIDO")
    
    # Detectar número de remesa (último número de 10 dígitos)
    remesa_match = re.findall(r"\b\d{10}\b", concepto)
    numero_remesa = remesa_match[-1] if remesa_match else "SIN_REMESA"
    
    # Control de duplicados
    fecha_date = pd.to_datetime(fecha_valor, dayfirst=True).date() if fecha_valor else None
    clave_control = (fecha_date, numero_comercio, numero_remesa)
    
    # --- ABONO TPV ---
    if concepto.startswith("ABONO TPV"):
        if (clave_control, "ABONO") in remesas_usadas:
            log(f"  → TPV ABONO: Posible duplicado remesa {numero_remesa}")
            return "REVISAR", f"{numero_remesa} (posible duplicado)"
        remesas_usadas.add((clave_control, "ABONO"))
        
        tipo = f"TPV {nombre_comercio}"
        log(f"  → {tipo}: {numero_remesa}")
        return tipo, numero_remesa
    
    # --- COMISIONES TPV ---
    if concepto.startswith("COMISIONES"):
        if (clave_control, "COMISION") in remesas_usadas:
            log(f"  → TPV COMISION: Posible duplicado remesa {numero_remesa}")
            return "REVISAR", f"{numero_remesa} (posible duplicado)"
        remesas_usadas.add((clave_control, "COMISION"))
        
        # Buscar abono correspondiente para calcular porcentaje
        if df_mov is not None and not df_mov.empty:
            try:
                abonos = df_mov[
                    (df_mov["Concepto"].str.upper().str.startswith("ABONO TPV")) &
                    (df_mov["Concepto"].str.contains(numero_comercio, na=False)) &
                    (df_mov["Concepto"].str.contains(numero_remesa, na=False))
                ]
                
                if not abonos.empty:
                    abono_importe = abs(float(abonos.iloc[0]["Importe"]))
                    comision_importe = abs(float(importe))
                    if abono_importe > 0:
                        porcentaje = round((comision_importe / abono_importe) * 100, 3)
                        log(f"  → COMISION TPV {nombre_comercio}: {numero_remesa} ({porcentaje:.2f}%)")
                        return f"COMISION TPV {nombre_comercio}", f"{numero_remesa} ({porcentaje:.2f}%)"
            except Exception:
                pass
        
        log(f"  → COMISION TPV {nombre_comercio}: {numero_remesa}")
        return f"COMISION TPV {nombre_comercio}", numero_remesa
    
    return None, None


def clasificar_transferencia(concepto: str, importe: float, fecha_valor, fecha_operativa,
                             df_fact: pd.DataFrame, df_fuzzy: pd.DataFrame,
                             indice_aliases: Dict[str, str]) -> Tuple[Optional[str], Optional[str]]:
    """
    Clasifica transferencias salientes.
    
    MODIFICADO v1.4: 
    - Usar fecha más cercana (≤60 días) para desempatar cuando hay varias facturas
    - Ya no marca REVISAR por "fuzzy cercano" si las fechas son diferentes
    
    Returns:
        (Categoria_Tipo, Categoria_Detalle) o (None, None) si no aplica
    """
    global facturas_usadas
    
    concepto_orig = concepto
    concepto = concepto.upper().strip()
    
    # Caso especial: alquiler — buscar las 2 facturas de los propietarios
    if "BENJAMIN ORTEGA Y JAIME" in concepto:
        fecha_v = pd.to_datetime(fecha_valor, errors="coerce", dayfirst=True)
        facturas_encontradas = []
        for titulos in [["ORTEGA ALONSO BENJAMIN", "BENJAMIN ORTEGA"],
                        ["FERNANDEZ MORENO JAIME", "JAIME FERNANDEZ"]]:
            patron = "|".join([t.upper() for t in titulos])
            df_prop = df_fact[
                df_fact["Título"].str.upper().str.contains(patron, na=False, regex=True)
            ].copy()
            if not df_prop.empty and pd.notna(fecha_v):
                df_prop["Fec.Fac."] = pd.to_datetime(df_prop["Fec.Fac."], errors="coerce", dayfirst=True)
                mismo_mes = df_prop[
                    (df_prop["Fec.Fac."].dt.month == fecha_v.month) &
                    (df_prop["Fec.Fac."].dt.year == fecha_v.year) &
                    (~df_prop["Cód."].isin(facturas_usadas))
                ]
                if not mismo_mes.empty:
                    cod = mismo_mes.iloc[0]["Cód."]
                    facturas_usadas.add(cod)
                    facturas_encontradas.append(f"#{cod}")
        if facturas_encontradas:
            detalle = ", ".join(facturas_encontradas)
            if len(facturas_encontradas) < 2:
                mes_str = fecha_v.strftime("%m/%Y") if pd.notna(fecha_v) else "?"
                detalle += f" (falta 1 factura {mes_str})"
            log(f"  → ALQUILER: {detalle}")
            return "ALQUILER", detalle
        else:
            mes_str = fecha_v.strftime("%m/%Y") if pd.notna(fecha_v) else "?"
            log(f"  → ALQUILER: Sin facturas para {mes_str}")
            return "ALQUILER", f"Sin facturas para {mes_str}"
    
    if not concepto.startswith("TRANSFERENCIA A"):
        return None, None
    
    # Extraer nombre del beneficiario
    nombre_banco = concepto.replace("TRANSFERENCIA A", "").strip()
    nombre_emisor, encontrado_alias = buscar_mejor_alias(nombre_banco, indice_aliases)

    log(f"  Nombre banco: '{nombre_banco}' → Alias: '{nombre_emisor}' (encontrado={encontrado_alias})")

    return buscar_factura_candidata(
        nombre_emisor, importe, fecha_valor, fecha_operativa,
        df_fact, df_fuzzy, facturas_usadas,
    )


def clasificar_compra_tarjeta(concepto: str, importe: float, fecha_valor, fecha_operativa,
                              df_fact: pd.DataFrame, df_fuzzy: pd.DataFrame,
                              indice_aliases: Dict[str, str]) -> Tuple[Optional[str], Optional[str]]:
    """
    Clasifica compras con tarjeta.
    
    MODIFICADO v1.4:
    - Usar fecha más cercana (≤60 días) para desempatar cuando hay varias facturas
    - Ya no marca REVISAR por "fuzzy cercano" si las fechas son diferentes
    
    Returns:
        (Categoria_Tipo, Categoria_Detalle) o (None, None) si no aplica
    """
    global facturas_usadas
    
    concepto_upper = str(concepto).upper().strip()
    
    if not concepto_upper.startswith("COMPRA TARJ"):
        return None, None
    
    # Detectar suscripciones (sin factura: SPOTIFY, NETFLIX... / con factura: OPENAI, MAKE...)
    tipo_susc, detalle_susc = clasificar_suscripciones(concepto, fecha_valor, df_fact)
    if tipo_susc:
        return tipo_susc, detalle_susc
    
    # Casos especiales (PANIFIESTO, AY MADRE LA FRUTA)
    for regla in REGLAS_ESPECIALES_TARJETA:
        if regla["clave"] in concepto_upper:
            titulo_emisor = regla["titulo"]
            fecha_v = pd.to_datetime(fecha_valor, errors="coerce", dayfirst=True)
            if pd.notna(fecha_v):
                facturas = df_fact[df_fact["Título"].apply(lambda t: normalizar_nombre(t) == normalizar_nombre(titulo_emisor))]
                facturas = facturas.copy()
                facturas["Fec.Fac."] = pd.to_datetime(facturas["Fec.Fac."], errors="coerce", dayfirst=True)
                mismas = facturas[
                    (facturas["Fec.Fac."].dt.month == fecha_v.month) &
                    (facturas["Fec.Fac."].dt.year == fecha_v.year)
                ]
                if len(mismas) == 1:
                    cod = mismas.iloc[0]["Cód."]
                    # No verificar si ya usada para casos especiales (pagos parciales)
                    facturas_usadas.add(cod)
                    log(f"  → Caso especial {titulo_emisor}: #{cod} (pago parcial)")
                    return titulo_emisor, f"#{cod} (pago parcial)"
            log(f"  → REVISAR: Caso especial {titulo_emisor}")
            return "REVISAR", f"Caso especial: {titulo_emisor}"
    
    # Extraer nombre del comercio (posición 30 en adelante, antes del guión)
    try:
        nombre_comercio = concepto_upper[30:].split("-")[0].strip()
    except (IndexError, TypeError) as e:
        nombre_comercio = ""
    
    nombre_emisor, encontrado_alias = buscar_mejor_alias(nombre_comercio, indice_aliases)

    log(f"  Nombre comercio: '{nombre_comercio}' → Alias: '{nombre_emisor}'")

    return buscar_factura_candidata(
        nombre_emisor, importe, fecha_valor, fecha_operativa,
        df_fact, df_fuzzy, facturas_usadas,
        log_candidatas=False,
    )


def clasificar_adeudo_recibo(concepto: str, importe: float, fecha_valor,
                             df_fact: pd.DataFrame, df_fuzzy: pd.DataFrame,
                             indice_aliases: Dict[str, str]) -> Tuple[Optional[str], Optional[str]]:
    """
    Clasifica adeudos y recibos domiciliados.
    
    MODIFICADO v1.4:
    - Usar fecha más cercana (≤60 días) para desempatar cuando hay varias facturas
    - Ya no marca REVISAR por "fuzzy cercano" si las fechas son diferentes
    
    Returns:
        (Categoria_Tipo, Categoria_Detalle) o (None, None) si no aplica
    """
    global facturas_usadas
    
    concepto_upper = str(concepto).upper().strip()
    
    if not concepto_upper.startswith("ADEUDO RECIBO"):
        return None, None
    
    # Detectar comunidad de vecinos + facturas ISTA
    tipo_com, detalle_com = clasificar_comunidad_vecinos(concepto, fecha_valor, df_fact)
    if tipo_com:
        return tipo_com, detalle_com
    
    # Extraer nombre del emisor (después de "ADEUDO RECIBO")
    nombre_banco = concepto_upper.replace("ADEUDO RECIBO", "").strip()
    nombre_emisor, encontrado_alias = buscar_mejor_alias(nombre_banco, indice_aliases)

    log(f"  Nombre banco: '{nombre_banco}' → Alias: '{nombre_emisor}'")

    return buscar_factura_candidata(
        nombre_emisor, importe, fecha_valor, None,
        df_fact, df_fuzzy, facturas_usadas,
        incluir_ref=True,
    )


def clasificar_som_energia(concepto: str, importe: float, df_fact: pd.DataFrame) -> Tuple[Optional[str], Optional[str]]:
    """
    Clasifica facturas de Som Energia.
    
    Returns:
        (Categoria_Tipo, Categoria_Detalle) o (None, None) si no aplica
    """
    global facturas_usadas
    
    concepto_upper = str(concepto).upper()
    
    if "SOM ENERGIA" not in concepto_upper:
        return None, None
    
    # Buscar número de factura en el concepto
    match = re.search(r"(FE?\d{6,})", concepto_upper)
    if match:
        num_factura = match.group(1)
        # Buscar en columna Factura
        fila = df_fact[df_fact["Factura"].astype(str).str.upper().str.contains(num_factura, na=False)]
        if not fila.empty:
            cod = fila.iloc[0]["Cód."]
            if cod in facturas_usadas:
                log(f"  → REVISAR: Som Energia #{cod} ya usada")
                return "REVISAR", f"Posible duplicado con #{cod}"
            facturas_usadas.add(cod)
            log(f"  → SOM ENERGIA: #{cod} ({num_factura})")
            return "SOM ENERGIA SCCL", f"#{cod} ({num_factura})"
    
    # Buscar por importe
    importe_abs = round(abs(float(importe)), 2)
    candidatas = df_fact[abs(df_fact["Total"] - importe_abs) <= 0.01]
    som_matches = candidatas[candidatas["Título"].str.upper().str.contains("SOM ENERGIA", na=False)]
    
    if len(som_matches) == 1:
        fila = som_matches.iloc[0]
        cod = fila["Cód."]
        if cod in facturas_usadas:
            log(f"  → REVISAR: Som Energia #{cod} ya usada")
            return "REVISAR", f"Posible duplicado con #{cod}"
        ref = fila.get("Factura", "")
        facturas_usadas.add(cod)
        detalle = f"#{cod}"
        if pd.notna(ref) and str(ref).strip():
            detalle += f" ({ref})"
        log(f"  → SOM ENERGIA: {detalle}")
        return "SOM ENERGIA SCCL", detalle
    
    log(f"  → REVISAR: Som Energia - verificar manualmente")
    return "REVISAR", "Som Energia - verificar manualmente"


def clasificar_yoigo(concepto: str, df_fact: pd.DataFrame) -> Tuple[Optional[str], Optional[str]]:
    """
    Clasifica facturas de Yoigo.

    v1.5: Regex flexible Y?C + filtro XFERA/YOIGO/MASMOVIL + fuzzy fallback 90%

    Returns:
        (Categoria_Tipo, Categoria_Detalle) o (None, None) si no aplica
    """
    global facturas_usadas

    concepto_upper = str(concepto).upper()

    if "YOIGO" not in concepto_upper:
        return None, None

    # Regex flexible: captura YCxxxxxxxxxx o Cxxxxxxxxxx
    match = re.search(r"Y?(C\d{9,})", concepto_upper)
    if not match:
        log(f"  → REVISAR: YOIGO sin número de factura en concepto")
        return "REVISAR", "YOIGO: No se encontró número de factura"

    numero_original = match.group(0)  # Con o sin Y
    numero_sin_y = match.group(1)     # Solo Cxxxxxxxxxx

    # Filtrar facturas de XFERA/YOIGO/MASMOVIL
    df_yoigo = df_fact[
        df_fact["Título"].str.upper().str.contains("XFERA|YOIGO|MASMOVIL", na=False, regex=True)
    ].copy()

    if df_yoigo.empty:
        log(f"  → REVISAR: No hay facturas de XFERA/YOIGO ({numero_original})")
        return "REVISAR", f"YOIGO: No hay facturas XFERA ({numero_original})"

    df_yoigo["Factura_norm"] = df_yoigo["Factura"].astype(str).str.upper().str.strip()

    # PASO 1: Buscar REF exacto (con Y)
    exacto = df_yoigo[df_yoigo["Factura_norm"] == numero_original]
    if exacto.empty:
        # PASO 2: Buscar REF sin la Y
        exacto = df_yoigo[df_yoigo["Factura_norm"] == numero_sin_y]

    if not exacto.empty:
        cod = exacto.iloc[0]["Cód."]
        if cod in facturas_usadas:
            log(f"  → REVISAR: Yoigo #{cod} ya usada")
            return "REVISAR", f"Posible duplicado con #{cod}"
        facturas_usadas.add(cod)
        ref_encontrada = exacto.iloc[0]["Factura_norm"]
        log(f"  → YOIGO: #{cod} ({ref_encontrada})")
        return "XFERA MOVILES SAU", f"#{cod} ({ref_encontrada})"

    # PASO 3: Fuzzy fallback ≥90%
    mejor_score = 0
    mejor_fila = None
    for _, fila in df_yoigo.iterrows():
        ref_factura = fila["Factura_norm"]
        score = max(
            fuzz.ratio(numero_original, ref_factura),
            fuzz.ratio(numero_sin_y, ref_factura),
        )
        if score > mejor_score and fila["Cód."] not in facturas_usadas:
            mejor_score = score
            mejor_fila = fila

    if mejor_score >= 90 and mejor_fila is not None:
        cod = mejor_fila["Cód."]
        ref_encontrada = mejor_fila["Factura_norm"]
        facturas_usadas.add(cod)
        log(f"  → YOIGO: #{cod} ({ref_encontrada}) [fuzzy {mejor_score}%]")
        return "XFERA MOVILES SAU", f"#{cod} ({ref_encontrada}) [fuzzy {mejor_score}%]"

    log(f"  → REVISAR: Factura YOIGO no encontrada ({numero_original})")
    return "REVISAR", f"Factura YOIGO no encontrada ({numero_original})"


def clasificar_casos_simples(concepto: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Clasifica casos simples por palabras clave.
    
    Returns:
        (Categoria_Tipo, Categoria_Detalle) o (None, None) si no aplica
    """
    concepto_upper = str(concepto).upper()
    
    if "TRASPASO" in concepto_upper:
        log(f"  → TRASPASO")
        return "TRASPASO", ""
    
    if "COMISIÓN DIVISA" in concepto_upper or "COMISION DIVISA" in concepto_upper:
        log(f"  → COMISION DIVISA")
        return "COMISION DIVISA", "Pago en moneda no euro"
    
    if "IMPUESTO" in concepto_upper or "TGSS" in concepto_upper or "AEAT" in concepto_upper:
        log(f"  → IMPUESTOS")
        return "IMPUESTOS", ""
    
    if "NÓMINA" in concepto_upper or "NOMINA" in concepto_upper:
        log(f"  → NOMINAS")
        return "NOMINAS", ""
    
    if "TRANSFERENCIA A ELENA DE MIGUEL" in concepto_upper:
        log(f"  → NOMINAS: Elena de Miguel")
        return "NOMINAS", "Elena de Miguel"
    
    if concepto_upper.startswith("INGRESO"):
        log(f"  → INGRESO")
        return "INGRESO", ""

    if "SERVICIO DE TPV" in concepto_upper:
        log(f"  → SERVICIO DE TPV")
        return "SERVICIO DE TPV", ""

    return None, None


# ==============================================================================
# CLASIFICADOR PRINCIPAL (ROUTER)
# ==============================================================================

def clasificar_movimiento(concepto: str, importe: float, fecha_valor, fecha_operativa,
                          df_fact: pd.DataFrame, df_fuzzy: pd.DataFrame,
                          df_mov: pd.DataFrame,
                          indice_aliases: Dict[str, str]) -> Tuple[str, str]:
    """
    Router principal que dirige cada movimiento al clasificador apropiado.
    
    Returns:
        (Categoria_Tipo, Categoria_Detalle)
    """
    concepto = str(concepto).strip()
    concepto_upper = concepto.upper()
    
    # 1. TPV (prioridad alta - muy específico)
    if concepto_upper.startswith("ABONO TPV") or concepto_upper.startswith("COMISIONES"):
        tipo, detalle = clasificar_tpv(concepto, fecha_valor, importe, df_mov)
        if tipo is not None:
            return tipo, detalle or ""
    
    # 2. Compra con tarjeta (incluye LOYVERSE)
    if concepto_upper.startswith("COMPRA TARJ"):
        tipo, detalle = clasificar_compra_tarjeta(concepto, importe, fecha_valor, fecha_operativa, df_fact, df_fuzzy, indice_aliases)
        if tipo is not None:
            return tipo, detalle or ""
    
    # 3. Transferencia
    if concepto_upper.startswith("TRANSFERENCIA A"):
        tipo, detalle = clasificar_transferencia(concepto, importe, fecha_valor, fecha_operativa, df_fact, df_fuzzy, indice_aliases)
        if tipo is not None:
            return tipo, detalle or ""
    
    # 4. Som Energia (antes de adeudo genérico)
    if "SOM ENERGIA" in concepto_upper:
        tipo, detalle = clasificar_som_energia(concepto, importe, df_fact)
        if tipo is not None:
            return tipo, detalle or ""
    
    # 5. Yoigo (antes de adeudo genérico)
    if "YOIGO" in concepto_upper:
        tipo, detalle = clasificar_yoigo(concepto, df_fact)
        if tipo is not None:
            return tipo, detalle or ""
    
    # 6. Adeudo/Recibo genérico (incluye COMUNIDAD DE VECINOS)
    if concepto_upper.startswith("ADEUDO RECIBO"):
        tipo, detalle = clasificar_adeudo_recibo(concepto, importe, fecha_valor, df_fact, df_fuzzy, indice_aliases)
        if tipo is not None:
            return tipo, detalle or ""
    
    # 7. Casos simples
    tipo, detalle = clasificar_casos_simples(concepto)
    if tipo is not None:
        return tipo, detalle or ""
    
    # 8. No clasificado
    log(f"  → REVISAR: Sin clasificador")
    return "REVISAR", "Sin clasificador"


# ==============================================================================
# PROCESAMIENTO PRINCIPAL
# ==============================================================================

def procesar_hoja_movimientos(df_mov: pd.DataFrame, df_fact: pd.DataFrame,
                               df_fuzzy: pd.DataFrame, nombre_hoja: str,
                               indice_aliases: Dict[str, str]) -> pd.DataFrame:
    """
    Procesa una hoja de movimientos, clasificando cada fila.
    
    Args:
        df_mov: DataFrame de movimientos
        df_fact: DataFrame de facturas (con columnas mapeadas)
        df_fuzzy: DataFrame de aliases
        nombre_hoja: Nombre de la hoja para logging
        
    Returns:
        DataFrame con columnas Categoria_Tipo y Categoria_Detalle añadidas/actualizadas
    """
    df = df_mov.copy()
    
    # Asegurar que existen las columnas de salida
    if "Categoria_Tipo" not in df.columns:
        df["Categoria_Tipo"] = ""
    if "Categoria_Detalle" not in df.columns:
        df["Categoria_Detalle"] = ""
    
    # Solo reiniciar remesas, NO facturas_usadas
    reset_estado_por_hoja()
    
    total = len(df)
    clasificados = 0
    revisar = 0
    
    log(f"\n{'='*60}")
    log(f"PROCESANDO HOJA: {nombre_hoja} ({total} movimientos)")
    log(f"{'='*60}")
    
    print(f"\n📋 Procesando {nombre_hoja}: {total} movimientos")
    
    for idx, row in df.iterrows():
        concepto = row.get("Concepto", "")
        importe = row.get("Importe", 0)
        fecha_valor = row.get("F. Valor", row.get("F.Valor", None))
        fecha_operativa = row.get("F. Operativa", row.get("F.Operativa", None))
        mov_num = row.get("#", idx)
        
        log(f"\n[{nombre_hoja} #{mov_num}] {concepto[:50]}... ({importe}€)")
        
        # Clasificar
        tipo, detalle = clasificar_movimiento(
            concepto, importe, fecha_valor, fecha_operativa,
            df_fact, df_fuzzy, df, indice_aliases
        )
        
        df.at[idx, "Categoria_Tipo"] = tipo
        df.at[idx, "Categoria_Detalle"] = detalle
        
        # Registrar vínculo factura → movimiento (MODIFICADO v1.4: pasa tipo)
        registrar_vinculo_factura(tipo, detalle, nombre_hoja, mov_num)
        
        if tipo == "REVISAR":
            revisar += 1
        else:
            clasificados += 1
    
    print(f"   ✅ Clasificados: {clasificados}")
    print(f"   ⚠️  A revisar: {revisar}")
    
    log(f"\n--- RESUMEN {nombre_hoja} ---")
    log(f"Clasificados: {clasificados}")
    log(f"A revisar: {revisar}")
    
    return df


def cargar_y_mapear_facturas(xlsx: pd.ExcelFile) -> pd.DataFrame:
    """
    Carga la hoja Facturas y mapea las columnas al formato esperado por los clasificadores.
    """
    df = pd.read_excel(xlsx, sheet_name=HOJA_FACTURAS)
    
    # Mapear columnas
    df_mapped = df.rename(columns=MAPEO_FACTURAS)
    
    # Asegurar tipos correctos
    if "Total" in df_mapped.columns:
        df_mapped["Total"] = pd.to_numeric(df_mapped["Total"], errors="coerce").fillna(0)
    
    return df_mapped


def seleccionar_archivo_gui() -> Optional[Path]:
    """
    Abre un diálogo de Windows para seleccionar el archivo Excel de entrada.
    """
    if not TKINTER_AVAILABLE:
        print("   (tkinter no disponible - modo consola)")
        ruta = input("   Introduce la ruta al archivo Excel: ").strip()
        if ruta:
            return Path(ruta)
        return None
    
    downloads = Path(os.environ.get("USERPROFILE", str(Path.home()))) / "Downloads"
    if not downloads.exists():
        downloads = Path.cwd()
    
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    
    archivo = filedialog.askopenfilename(
        title="Selecciona el archivo Excel con movimientos a clasificar",
        initialdir=str(downloads),
        filetypes=[
            ("Excel files", "*.xlsx *.xls"),
            ("Todos los archivos", "*.*")
        ]
    )
    
    root.destroy()
    
    if archivo:
        return Path(archivo)
    return None


def generar_nombre_salida(df_movimientos: Dict[str, pd.DataFrame]) -> str:
    """
    Genera el nombre del archivo de salida basado en las fechas de los movimientos.
    
    Formato: Cuadre_DDMMYY-DDMMYY.xlsx
    """
    fecha_min = None
    fecha_max = None
    
    for nombre, df in df_movimientos.items():
        for col in ["F. Valor", "F.Valor", "F. Operativa", "F.Operativa"]:
            if col in df.columns:
                fechas = pd.to_datetime(df[col], errors="coerce", dayfirst=True)
                if fechas.notna().any():
                    f_min = fechas.min()
                    f_max = fechas.max()
                    if fecha_min is None or f_min < fecha_min:
                        fecha_min = f_min
                    if fecha_max is None or f_max > fecha_max:
                        fecha_max = f_max
    
    if fecha_min and fecha_max:
        str_min = fecha_min.strftime("%d%m%y")
        str_max = fecha_max.strftime("%d%m%y")
        return f"Cuadre_{str_min}-{str_max}.xlsx"
    else:
        hoy = datetime.now().strftime("%d%m%y")
        return f"Cuadre_{hoy}.xlsx"


# ==============================================================================
# FUNCIÓN PRINCIPAL
# ==============================================================================

def main():
    """Punto de entrada principal."""
    
    print("=" * 70)
    print("CUADRE.PY v1.5 - Clasificador de Movimientos Bancarios")
    print("=" * 70)
    print()
    
    # Inicializar estado global al inicio
    reset_estado_global_inicio()
    
    log("CUADRE.PY v1.5")
    log(f"Fecha ejecución: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 1. Seleccionar archivo de entrada
    print("📂 Selecciona el archivo Excel con los movimientos...")
    archivo_entrada = seleccionar_archivo_gui()
    
    if not archivo_entrada:
        print("❌ No se seleccionó ningún archivo. Saliendo.")
        return
    
    print(f"   Archivo: {archivo_entrada.name}")
    log(f"Archivo entrada: {archivo_entrada}")
    
    # 2. Cargar MAESTRO_PROVEEDORES
    print(f"\n📚 Cargando MAESTRO_PROVEEDORES...")
    if not MAESTRO_PATH.exists():
        maestro_alt = archivo_entrada.parent / "MAESTRO_PROVEEDORES.xlsx"
        if maestro_alt.exists():
            maestro_path = maestro_alt
        else:
            print(f"   ⚠️  No se encontró MAESTRO_PROVEEDORES en:")
            print(f"      - {MAESTRO_PATH}")
            print(f"      - {maestro_alt}")
            print("   Continuando sin matching de aliases...")
            df_maestro = pd.DataFrame()
            df_fuzzy = pd.DataFrame(columns=["NOMBRE_EN_CONCEPTO", "TITULO_FACTURA"])
            indice_aliases = {}
            log("MAESTRO_PROVEEDORES: NO ENCONTRADO")
    else:
        maestro_path = MAESTRO_PATH
    
    if 'maestro_path' in dir() and maestro_path:
        try:
            df_maestro = pd.read_excel(maestro_path)
            df_fuzzy = construir_df_fuzzy(df_maestro)
            indice_aliases = construir_indice_aliases(df_fuzzy)
            n_activos = (df_maestro.get("ACTIVO", pd.Series()).astype(str).str.upper() == "SI").sum()
            n_extractor = (df_maestro.get("TIENE_EXTRACTOR", pd.Series()).astype(str).str.upper() == "SI").sum()
            print(f"   ✅ {len(df_maestro)} proveedores ({n_activos} activos), {len(df_fuzzy)} aliases, {n_extractor} con extractor")
            log(f"MAESTRO_PROVEEDORES: {len(df_maestro)} proveedores, {len(df_fuzzy)} aliases")
        except Exception as e:
            print(f"   ❌ Error cargando MAESTRO: {e}")
            df_fuzzy = pd.DataFrame(columns=["NOMBRE_EN_CONCEPTO", "TITULO_FACTURA"])
            indice_aliases = {}
            log(f"MAESTRO_PROVEEDORES: ERROR - {e}")
    
    # 3. Cargar archivo de entrada
    print(f"\n📖 Leyendo archivo de entrada...")
    try:
        xlsx = pd.ExcelFile(archivo_entrada)
        print(f"   Hojas encontradas: {xlsx.sheet_names}")
        log(f"Hojas en archivo: {xlsx.sheet_names}")
    except Exception as e:
        print(f"   ❌ Error abriendo archivo: {e}")
        return
    
    # 4. Cargar hoja Facturas
    if HOJA_FACTURAS not in xlsx.sheet_names:
        print(f"   ❌ No se encontró la hoja '{HOJA_FACTURAS}'")
        return
    
    df_fact = cargar_y_mapear_facturas(xlsx)
    print(f"   ✅ Facturas: {len(df_fact)} registros")
    log(f"Facturas cargadas: {len(df_fact)}")
    
    # 5. Identificar hojas de movimientos
    hojas_encontradas = []
    for hoja in xlsx.sheet_names:
        for patron in HOJAS_MOVIMIENTOS:
            if hoja.strip().upper() == patron.strip().upper():
                hojas_encontradas.append(hoja)
                break
    
    if not hojas_encontradas:
        print(f"   ❌ No se encontraron hojas de movimientos (Tasca/Comestibles)")
        return
    
    print(f"   ✅ Hojas de movimientos: {hojas_encontradas}")
    
    # 6. Procesar cada hoja de movimientos
    resultados: Dict[str, pd.DataFrame] = {}
    
    for hoja in hojas_encontradas:
        df_mov = pd.read_excel(xlsx, sheet_name=hoja)
        df_procesado = procesar_hoja_movimientos(df_mov, df_fact, df_fuzzy, hoja, indice_aliases)
        resultados[hoja] = df_procesado
    
    # 7. Generar nombre de archivo de salida
    nombre_salida = generar_nombre_salida(resultados)
    
    if OUTPUT_DIR.exists():
        ruta_salida = OUTPUT_DIR / nombre_salida
    else:
        ruta_salida = archivo_entrada.parent / nombre_salida
    
    # 8. Guardar archivo de salida
    print(f"\n💾 Guardando resultado...")
    print(f"   Archivo: {ruta_salida}")
    
    try:
        with pd.ExcelWriter(ruta_salida, engine="openpyxl") as writer:
            # Guardar hojas de movimientos procesadas
            for hoja, df in resultados.items():
                # NUEVO v1.4: Formatear fechas DD-MM-YY
                df = formatear_fechas_df(df)
                df.to_excel(writer, sheet_name=hoja, index=False)
            
            # Añadir columna Origen a Facturas
            df_fact_original = pd.read_excel(xlsx, sheet_name=HOJA_FACTURAS)
            df_fact_original["Origen"] = generar_columna_origen(df_fact_original)
            
            # NUEVO v1.4: Eliminar columnas Unnamed
            df_fact_original = eliminar_columnas_unnamed(df_fact_original)
            
            # NUEVO v1.4: Formatear fechas DD-MM-YY
            df_fact_original = formatear_fechas_df(df_fact_original)
            
            # Reordenar columnas: Origen antes de OBSERVACIONES
            cols = list(df_fact_original.columns)
            if "OBSERVACIONES" in cols and "Origen" in cols:
                cols.remove("Origen")
                idx_obs = cols.index("OBSERVACIONES")
                cols.insert(idx_obs, "Origen")
                df_fact_original = df_fact_original[cols]
            
            df_fact_original.to_excel(writer, sheet_name=HOJA_FACTURAS, index=False)
            
            total_facturas = len(df_fact_original)
            facturas_con_origen = len([1 for o in df_fact_original["Origen"] if o and str(o).strip()])
            print(f"   📎 Facturas con Origen: {facturas_con_origen}/{total_facturas}")
            log(f"\nFacturas con Origen: {facturas_con_origen}/{total_facturas}")
        
        print(f"   ✅ Guardado correctamente")
    except PermissionError:
        print(f"   ❌ Error: El archivo está abierto en Excel. Ciérralo e intenta de nuevo.")
        return
    except Exception as e:
        print(f"   ❌ Error guardando: {e}")
        return
    
    # 9. Guardar LOG
    guardar_log(ruta_salida)
    
    # 10. Resumen final
    print()
    print("=" * 70)
    print("✅ PROCESO COMPLETADO")
    print("=" * 70)
    
    total_mov = sum(len(df) for df in resultados.values())
    total_revisar = sum(len(df[df["Categoria_Tipo"] == "REVISAR"]) for df in resultados.values())
    total_ok = total_mov - total_revisar
    
    print(f"   📊 Total movimientos: {total_mov}")
    print(f"   ✅ Clasificados: {total_ok} ({100*total_ok/total_mov:.1f}%)")
    print(f"   ⚠️  A revisar: {total_revisar} ({100*total_revisar/total_mov:.1f}%)")
    print(f"   📄 Archivo: {ruta_salida}")
    print()
    
    log(f"\n{'='*60}")
    log(f"RESUMEN FINAL")
    log(f"{'='*60}")
    log(f"Total movimientos: {total_mov}")
    log(f"Clasificados: {total_ok} ({100*total_ok/total_mov:.1f}%)")
    log(f"A revisar: {total_revisar} ({100*total_revisar/total_mov:.1f}%)")
    
    # Mostrar mensaje de éxito
    if TKINTER_AVAILABLE:
        root = tk.Tk()
        root.withdraw()
        messagebox.showinfo(
            "Cuadre completado",
            f"Proceso completado.\n\n"
            f"Movimientos: {total_mov}\n"
            f"Clasificados: {total_ok} ({100*total_ok/total_mov:.1f}%)\n"
            f"A revisar: {total_revisar}\n\n"
            f"Archivo: {ruta_salida.name}"
        )
        root.destroy()


# ==============================================================================
# PUNTO DE ENTRADA
# ==============================================================================

if __name__ == "__main__":
    main()
