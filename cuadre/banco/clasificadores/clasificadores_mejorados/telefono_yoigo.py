"""
Clasificador: TELEFONOS YOIGO
Versión: 2.0
Fecha: 26/01/2026

LÓGICA:
1. Detecta movimientos "TELEFONOS YOIGO YCxxxxxxxxxx"
2. Busca REF exacto en facturas (XFERA MOVILES SAU)
3. Si no encuentra → quita la Y inicial y busca "Cxxxxxxxxxx"
4. Si no encuentra → fuzzy >90% con el número de factura

EJEMPLO:
- Movimiento: "TELEFONOS YOIGO YC250014247872"
- Factura: XFERA MOVILES SAU con REF "C250014247872"
"""

import re
from rapidfuzz import fuzz

# Control de facturas usadas (se importa desde el módulo principal)
facturas_usadas = set()


def clasificar_yoigo(concepto, df_fact):
    """
    Clasifica movimientos de YOIGO/XFERA MOVILES.
    
    Args:
        concepto: Texto del concepto bancario
        df_fact: DataFrame de facturas con columnas Cód., Título, Factura
    
    Returns:
        (Categoria_Tipo, Categoria_Detalle, Protocolo) o (None, None, None)
    """
    global facturas_usadas
    
    concepto = str(concepto).upper().strip()
    
    # Solo procesar si contiene YOIGO
    if "YOIGO" not in concepto:
        return None, None, None
    
    # Extraer número de referencia (YCxxxxxxxxxx o Cxxxxxxxxxx)
    # Patrón: Y seguido de C y dígitos, o solo C y dígitos
    match = re.search(r"Y?(C\d{9,})", concepto)
    
    if not match:
        return "REVISAR", "YOIGO: No se encontró número de factura", "YOIGO"
    
    numero_original = match.group(0)  # Con o sin Y
    numero_sin_y = match.group(1)     # Sin Y (solo Cxxxxxxx)
    
    # Filtrar facturas de XFERA/YOIGO/MASMOVIL
    df_yoigo = df_fact[
        df_fact["Título"].str.upper().str.contains("XFERA|YOIGO|MASMOVIL", na=False, regex=True)
    ].copy()
    
    if df_yoigo.empty:
        return "REVISAR", f"YOIGO: No hay facturas de XFERA/YOIGO ({numero_original})", "YOIGO"
    
    # Normalizar columna Factura para comparación
    df_yoigo["Factura_norm"] = df_yoigo["Factura"].astype(str).str.upper().str.strip()
    
    # --- PASO 1: Buscar REF exacto (con Y) ---
    exacto_con_y = df_yoigo[df_yoigo["Factura_norm"] == numero_original]
    if not exacto_con_y.empty:
        fila = exacto_con_y.iloc[0]
        cod = fila["Cód."]
        if cod not in facturas_usadas:
            facturas_usadas.add(cod)
            return cod, numero_original, "YOIGO"
    
    # --- PASO 2: Buscar REF sin la Y ---
    exacto_sin_y = df_yoigo[df_yoigo["Factura_norm"] == numero_sin_y]
    if not exacto_sin_y.empty:
        fila = exacto_sin_y.iloc[0]
        cod = fila["Cód."]
        if cod not in facturas_usadas:
            facturas_usadas.add(cod)
            return cod, numero_sin_y, "YOIGO"
    
    # --- PASO 3: Buscar REF con fuzzy >90% ---
    mejor_score = 0
    mejor_fila = None
    
    for _, fila in df_yoigo.iterrows():
        ref_factura = fila["Factura_norm"]
        
        # Comparar con número original y sin Y
        score1 = fuzz.ratio(numero_original, ref_factura)
        score2 = fuzz.ratio(numero_sin_y, ref_factura)
        score = max(score1, score2)
        
        if score > mejor_score and fila["Cód."] not in facturas_usadas:
            mejor_score = score
            mejor_fila = fila
    
    if mejor_score >= 90 and mejor_fila is not None:
        cod = mejor_fila["Cód."]
        ref_encontrada = mejor_fila["Factura_norm"]
        facturas_usadas.add(cod)
        return cod, f"{ref_encontrada} (fuzzy {mejor_score}%)", "YOIGO"
    
    # --- No encontrado ---
    return "REVISAR", f"YOIGO: Factura no encontrada ({numero_original})", "YOIGO"


def reset_facturas_usadas():
    """Reinicia el control de facturas usadas."""
    global facturas_usadas
    facturas_usadas = set()
