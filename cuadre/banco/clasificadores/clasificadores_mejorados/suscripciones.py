"""
Clasificador: SUSCRIPCIONES EXTRANJERAS
Versión: 1.0
Fecha: 26/01/2026

LÓGICA:
Detecta compras con tarjeta de suscripciones extranjeras y busca
la factura del mismo mes.

MAPEO:
- WWW.MAKE.COM → CELONIS INC.
- OPENAI *CHATGPT → OPENAI LLC
- LOYVERSE.COM → FIVE GALAXIES COMMERCE LTD
- Spotify → GASTOS VARIOS (sin factura)

EJEMPLO:
- Movimiento: "COMPRA TARJ. 5540XXXXXXXX1019 WWW.MAKE.COM-NEW YORK" (15/10/2025)
- Busca factura CELONIS INC. con fecha en octubre 2025
"""

import pandas as pd
from rapidfuzz import fuzz

# Control de facturas usadas
facturas_usadas = set()

# Mapeo de texto en concepto → título en facturas
SUSCRIPCIONES_CON_FACTURA = [
    {
        "clave": "MAKE.COM",
        "titulo": "CELONIS INC.",
        "aliases": ["CELONIS", "MAKE"],
    },
    {
        "clave": "OPENAI",
        "titulo": "OPENAI LLC",
        "aliases": ["OPENAI", "CHATGPT", "CHAT GPT"],
    },
    {
        "clave": "LOYVERSE",
        "titulo": "FIVE GALAXIES COMMERCE LTD",
        "aliases": ["FIVE GALAXIES", "LOYVERSE"],
    },
]

SUSCRIPCIONES_SIN_FACTURA = [
    {
        "clave": "SPOTIFY",
        "categoria": "GASTOS VARIOS",
        "detalle": "Sin factura",
    },
    {
        "clave": "NETFLIX",
        "categoria": "GASTOS VARIOS", 
        "detalle": "Sin factura",
    },
    {
        "clave": "AMAZON PRIME",
        "categoria": "GASTOS VARIOS",
        "detalle": "Sin factura",
    },
]


def buscar_factura_mes(fecha_valor, df_fact, titulo_proveedor, aliases):
    """
    Busca factura del proveedor en el mismo mes que la fecha del movimiento.
    
    Args:
        fecha_valor: Fecha del movimiento
        df_fact: DataFrame de facturas
        titulo_proveedor: Nombre del proveedor a buscar
        aliases: Lista de alias del proveedor
    
    Returns:
        (cod, detalle) o ("REVISAR", mensaje)
    """
    global facturas_usadas
    
    # Crear patrón de búsqueda con todos los aliases
    patron = "|".join([titulo_proveedor.upper()] + [a.upper() for a in aliases])
    
    # Filtrar facturas del proveedor
    df_prov = df_fact[
        df_fact["Título"].str.upper().str.contains(patron, na=False, regex=True)
    ].copy()
    
    if df_prov.empty:
        return "REVISAR", f"No hay facturas de {titulo_proveedor}"
    
    # Convertir fechas
    df_prov["Fec.Fac."] = pd.to_datetime(df_prov["Fec.Fac."], errors="coerce", dayfirst=True)
    fecha_mov = pd.to_datetime(fecha_valor, dayfirst=True)
    
    # Filtrar facturas del mismo mes
    mismo_mes = df_prov[
        (df_prov["Fec.Fac."].dt.month == fecha_mov.month) &
        (df_prov["Fec.Fac."].dt.year == fecha_mov.year) &
        (~df_prov["Cód."].isin(facturas_usadas))
    ]
    
    if len(mismo_mes) == 1:
        fila = mismo_mes.iloc[0]
        cod = fila["Cód."]
        facturas_usadas.add(cod)
        return cod, titulo_proveedor
    
    elif len(mismo_mes) > 1:
        # Varias facturas del mismo mes → elegir la más cercana en fecha
        mismo_mes = mismo_mes.copy()
        mismo_mes["dist"] = abs((mismo_mes["Fec.Fac."] - fecha_mov).dt.days)
        mejor = mismo_mes.sort_values("dist").iloc[0]
        cod = mejor["Cód."]
        facturas_usadas.add(cod)
        return cod, titulo_proveedor
    
    else:
        # No hay factura del mismo mes → buscar la más cercana anterior
        anteriores = df_prov[
            (df_prov["Fec.Fac."] <= fecha_mov) &
            (~df_prov["Cód."].isin(facturas_usadas))
        ]
        
        if not anteriores.empty:
            anteriores = anteriores.copy()
            anteriores["dist"] = abs((anteriores["Fec.Fac."] - fecha_mov).dt.days)
            mejor = anteriores.sort_values("dist").iloc[0]
            cod = mejor["Cód."]
            mes_fac = mejor["Fec.Fac."].strftime("%m/%Y")
            facturas_usadas.add(cod)
            return cod, f"{titulo_proveedor} (fac. {mes_fac})"
        
        return "REVISAR", f"Sin factura de {titulo_proveedor} para {fecha_mov.strftime('%m/%Y')}"


def clasificar_suscripcion(concepto, importe, fecha_valor, df_fact):
    """
    Clasifica compras con tarjeta de suscripciones extranjeras.
    
    Args:
        concepto: Texto del concepto bancario
        importe: Importe del movimiento
        fecha_valor: Fecha valor del movimiento
        df_fact: DataFrame de facturas
    
    Returns:
        (Categoria_Tipo, Categoria_Detalle, Protocolo) o (None, None, None)
    """
    concepto_upper = str(concepto).upper().strip()
    
    # Solo procesar compras con tarjeta
    if not ("COMPRA TARJ" in concepto_upper or "ANUL COMPRA TARJ" in concepto_upper):
        return None, None, None
    
    # --- Suscripciones SIN factura ---
    for suscripcion in SUSCRIPCIONES_SIN_FACTURA:
        if suscripcion["clave"] in concepto_upper:
            return suscripcion["categoria"], suscripcion["detalle"], "SUSCRIPCION"
    
    # --- Suscripciones CON factura ---
    for suscripcion in SUSCRIPCIONES_CON_FACTURA:
        if suscripcion["clave"] in concepto_upper:
            cod, detalle = buscar_factura_mes(
                fecha_valor, 
                df_fact, 
                suscripcion["titulo"],
                suscripcion["aliases"]
            )
            
            # Si es anulación, indicarlo
            if "ANUL" in concepto_upper:
                detalle = f"ANULACIÓN - {detalle}"
            
            return cod, detalle, "SUSCRIPCION"
    
    # No es una suscripción conocida
    return None, None, None


def reset_facturas_usadas():
    """Reinicia el control de facturas usadas."""
    global facturas_usadas
    facturas_usadas = set()
