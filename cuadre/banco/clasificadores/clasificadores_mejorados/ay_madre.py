"""
Clasificador: AY MADRE LA FRUTA → GARCIA VIVAS JULIO
Versión: 1.0
Fecha: 26/01/2026

LÓGICA:
1. Detecta movimientos "COMPRA TARJ. ... AY MADRE LA FRUTA-MADRID"
2. Busca factura de GARCIA VIVAS JULIO del mismo mes
3. Todos los movimientos del mes → misma factura mensual

EJEMPLO:
- Movimiento: "COMPRA TARJ. 5540XXXXXXXX1019 AY MADRE LA FRUTA-MADRID" (14/10/2025)
- Busca factura GARCIA VIVAS JULIO con fecha en octubre 2025 (31/10/2025)
- Resultado: #4077
"""

import pandas as pd
from rapidfuzz import fuzz

# Control de facturas usadas por mes (para no duplicar)
# Estructura: {(año, mes): cod_factura}
facturas_mes_usadas = {}

# Control global de facturas usadas
facturas_usadas = set()


def normalizar_nombre(nombre):
    """Normaliza nombre para comparación."""
    if not isinstance(nombre, str):
        return ""
    import unicodedata
    nombre = unicodedata.normalize("NFKD", nombre)
    nombre = "".join(c for c in nombre if not unicodedata.combining(c))
    nombre = nombre.upper().strip()
    return " ".join(nombre.split())


def clasificar_ay_madre(concepto, importe, fecha_valor, df_fact):
    """
    Clasifica compras de AY MADRE LA FRUTA asignando factura GARCIA VIVAS JULIO.
    
    Args:
        concepto: Texto del concepto bancario
        importe: Importe del movimiento
        fecha_valor: Fecha valor del movimiento
        df_fact: DataFrame de facturas
    
    Returns:
        (Categoria_Tipo, Categoria_Detalle, Protocolo) o (None, None, None)
    """
    global facturas_mes_usadas, facturas_usadas
    
    concepto_upper = str(concepto).upper().strip()
    
    # Solo procesar si es AY MADRE LA FRUTA
    if "AY MADRE LA FRUTA" not in concepto_upper:
        return None, None, None
    
    # Convertir fecha
    fecha_mov = pd.to_datetime(fecha_valor, dayfirst=True)
    mes_key = (fecha_mov.year, fecha_mov.month)
    
    # --- Si ya tenemos factura asignada para este mes, reutilizarla ---
    if mes_key in facturas_mes_usadas:
        cod = facturas_mes_usadas[mes_key]
        return cod, "GARCIA VIVAS JULIO (pago parcial)", "AY MADRE"
    
    # --- Buscar factura de GARCIA VIVAS JULIO del mismo mes ---
    # Patrones de búsqueda
    patrones = ["GARCIA VIVAS", "JULIO GARCIA"]
    
    df_gv = df_fact[
        df_fact["Título"].str.upper().str.contains("|".join(patrones), na=False, regex=True)
    ].copy()
    
    if df_gv.empty:
        return "REVISAR", "AY MADRE: No hay facturas de GARCIA VIVAS JULIO", "AY MADRE"
    
    # Convertir fechas
    df_gv["Fec.Fac."] = pd.to_datetime(df_gv["Fec.Fac."], errors="coerce", dayfirst=True)
    
    # Filtrar facturas del mismo mes
    mismo_mes = df_gv[
        (df_gv["Fec.Fac."].dt.month == fecha_mov.month) &
        (df_gv["Fec.Fac."].dt.year == fecha_mov.year)
    ]
    
    if len(mismo_mes) == 1:
        fila = mismo_mes.iloc[0]
        cod = fila["Cód."]
        facturas_mes_usadas[mes_key] = cod
        facturas_usadas.add(cod)
        return cod, "GARCIA VIVAS JULIO", "AY MADRE"
    
    elif len(mismo_mes) > 1:
        # Varias facturas del mismo mes → tomar la de fin de mes (mayor fecha)
        fila = mismo_mes.sort_values("Fec.Fac.", ascending=False).iloc[0]
        cod = fila["Cód."]
        facturas_mes_usadas[mes_key] = cod
        facturas_usadas.add(cod)
        return cod, "GARCIA VIVAS JULIO", "AY MADRE"
    
    else:
        # No hay factura del mismo mes
        mes_str = fecha_mov.strftime("%m/%Y")
        return "REVISAR", f"AY MADRE: Sin factura GARCIA VIVAS para {mes_str}", "AY MADRE"


def reset_facturas_usadas():
    """Reinicia el control de facturas usadas."""
    global facturas_mes_usadas, facturas_usadas
    facturas_mes_usadas = {}
    facturas_usadas = set()
