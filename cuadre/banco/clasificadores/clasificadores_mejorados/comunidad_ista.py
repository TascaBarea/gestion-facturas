"""
Clasificador: COMUNIDAD DE VECINOS + ISTA
Versión: 1.0
Fecha: 26/01/2026

LÓGICA:
1. Detecta movimientos "ADEUDO RECIBO COM PROP RODAS 2"
2. Categoría: COMUNIDAD DE VECINOS
3. Busca las 2 facturas ISTA más cercanas en fecha que no hayan sido usadas
4. El pago de comunidad incluye gastos de agua (ISTA)

EJEMPLO:
- Movimiento: "ADEUDO RECIBO COM PROP RODAS 2" (07/10/2025, -127.23€)
- Busca 2 facturas de ISTA METERING SERVICES más cercanas
- Detalle: "#4260, #4261"
"""

import pandas as pd

# Control de facturas usadas
facturas_usadas = set()


def clasificar_comunidad_ista(concepto, importe, fecha_valor, df_fact):
    """
    Clasifica pagos de comunidad de vecinos y asigna facturas ISTA.
    
    Args:
        concepto: Texto del concepto bancario
        importe: Importe del movimiento
        fecha_valor: Fecha valor del movimiento
        df_fact: DataFrame de facturas
    
    Returns:
        (Categoria_Tipo, Categoria_Detalle, Protocolo) o (None, None, None)
    """
    global facturas_usadas
    
    concepto_upper = str(concepto).upper().strip()
    
    # Solo procesar si es COM PROP o COMUNIDAD PROP
    if "COM PROP" not in concepto_upper and "COMUNIDAD PROP" not in concepto_upper:
        return None, None, None
    
    # Filtrar facturas de ISTA METERING (excluir MAKRO que también tiene "ISTA" en REF)
    df_ista = df_fact[
        df_fact["Título"].str.upper().str.contains("ISTA METERING", na=False)
    ].copy()
    
    if df_ista.empty:
        return "COMUNIDAD DE VECINOS", "Sin facturas ISTA disponibles", "COMUNIDAD"
    
    # Convertir fechas
    df_ista["Fec.Fac."] = pd.to_datetime(df_ista["Fec.Fac."], errors="coerce", dayfirst=True)
    fecha_mov = pd.to_datetime(fecha_valor, dayfirst=True)
    
    # Filtrar facturas no usadas
    df_disponibles = df_ista[~df_ista["Cód."].isin(facturas_usadas)].copy()
    
    if df_disponibles.empty:
        return "COMUNIDAD DE VECINOS", "Todas las facturas ISTA ya usadas", "COMUNIDAD"
    
    # Calcular distancia en días a la fecha del movimiento
    df_disponibles["dist"] = abs((df_disponibles["Fec.Fac."] - fecha_mov).dt.days)
    
    # Ordenar por distancia (más cercanas primero)
    df_disponibles = df_disponibles.sort_values("dist")
    
    # Tomar las 2 más cercanas
    facturas_asignadas = []
    for _, fila in df_disponibles.head(2).iterrows():
        cod = fila["Cód."]
        facturas_usadas.add(cod)
        facturas_asignadas.append(f"#{cod}")
    
    if facturas_asignadas:
        detalle = ", ".join(facturas_asignadas)
        return "COMUNIDAD DE VECINOS", detalle, "COMUNIDAD"
    else:
        return "COMUNIDAD DE VECINOS", "Sin facturas ISTA", "COMUNIDAD"


def reset_facturas_usadas():
    """Reinicia el control de facturas usadas."""
    global facturas_usadas
    facturas_usadas = set()
