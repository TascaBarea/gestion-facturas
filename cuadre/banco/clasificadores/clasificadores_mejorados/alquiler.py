"""
Clasificador: ALQUILER (BENJAMIN ORTEGA Y JAIME FERNANDEZ)
Versión: 2.0
Fecha: 26/01/2026

LÓGICA:
1. Detecta movimiento "TRANSFERENCIA A BENJAMIN ORTEGA Y JAIME FDEZ M"
2. Categoría: ALQUILER
3. Busca las facturas del mes de:
   - ORTEGA ALONSO BENJAMIN (510€)
   - FERNANDEZ MORENO JAIME (510€)
4. Detalle: "#xxxx, #yyyy"

EJEMPLO:
- Movimiento: "TRANSFERENCIA A BENJAMIN ORTEGA Y JAIME FDEZ M" (30/10/2025, -1.020€)
- Busca facturas octubre 2025:
   - #4185 ORTEGA ALONSO BENJAMIN
   - #4186 FERNANDEZ MORENO JAIME
- Resultado: Categoría ALQUILER, Detalle "#4185, #4186"
"""

import pandas as pd

# Control de facturas usadas
facturas_usadas = set()

# Propietarios del alquiler
PROPIETARIOS = [
    {
        "patron_concepto": "BENJAMIN ORTEGA Y JAIME",
        "titulos_factura": [
            "ORTEGA ALONSO BENJAMIN",
            "BENJAMIN ORTEGA",
        ],
    },
    {
        "patron_concepto": "BENJAMIN ORTEGA Y JAIME",
        "titulos_factura": [
            "FERNANDEZ MORENO JAIME",
            "JAIME FERNANDEZ",
        ],
    },
]


def buscar_factura_propietario(fecha_valor, df_fact, titulos_factura):
    """
    Busca factura de un propietario para el mes del movimiento.
    
    Args:
        fecha_valor: Fecha del movimiento
        df_fact: DataFrame de facturas
        titulos_factura: Lista de posibles títulos del propietario
    
    Returns:
        cod de la factura o None
    """
    global facturas_usadas
    
    fecha_mov = pd.to_datetime(fecha_valor, dayfirst=True)
    
    # Crear patrón de búsqueda
    patron = "|".join([t.upper() for t in titulos_factura])
    
    # Filtrar facturas del propietario
    df_prop = df_fact[
        df_fact["Título"].str.upper().str.contains(patron, na=False, regex=True)
    ].copy()
    
    if df_prop.empty:
        return None
    
    # Convertir fechas
    df_prop["Fec.Fac."] = pd.to_datetime(df_prop["Fec.Fac."], errors="coerce", dayfirst=True)
    
    # Filtrar facturas del mismo mes que no estén usadas
    mismo_mes = df_prop[
        (df_prop["Fec.Fac."].dt.month == fecha_mov.month) &
        (df_prop["Fec.Fac."].dt.year == fecha_mov.year) &
        (~df_prop["Cód."].isin(facturas_usadas))
    ]
    
    if not mismo_mes.empty:
        # Tomar la primera (normalmente solo hay una por mes por propietario)
        fila = mismo_mes.iloc[0]
        cod = fila["Cód."]
        facturas_usadas.add(cod)
        return cod
    
    return None


def clasificar_alquiler(concepto, importe, fecha_valor, df_fact):
    """
    Clasifica transferencias de alquiler a los propietarios.
    
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
    
    # Solo procesar si es transferencia a los propietarios del alquiler
    if "BENJAMIN ORTEGA Y JAIME" not in concepto_upper:
        return None, None, None
    
    # Buscar facturas de ambos propietarios
    facturas_encontradas = []
    
    # ORTEGA ALONSO BENJAMIN
    cod_benjamin = buscar_factura_propietario(
        fecha_valor, df_fact, 
        ["ORTEGA ALONSO BENJAMIN", "BENJAMIN ORTEGA"]
    )
    if cod_benjamin:
        facturas_encontradas.append(f"#{cod_benjamin}")
    
    # FERNANDEZ MORENO JAIME
    cod_jaime = buscar_factura_propietario(
        fecha_valor, df_fact,
        ["FERNANDEZ MORENO JAIME", "JAIME FERNANDEZ"]
    )
    if cod_jaime:
        facturas_encontradas.append(f"#{cod_jaime}")
    
    # Generar detalle
    if len(facturas_encontradas) == 2:
        detalle = ", ".join(facturas_encontradas)
        return "ALQUILER", detalle, "ALQUILER"
    elif len(facturas_encontradas) == 1:
        fecha_mov = pd.to_datetime(fecha_valor, dayfirst=True)
        mes_str = fecha_mov.strftime("%m/%Y")
        detalle = f"{facturas_encontradas[0]} (falta 1 factura {mes_str})"
        return "ALQUILER", detalle, "ALQUILER"
    else:
        fecha_mov = pd.to_datetime(fecha_valor, dayfirst=True)
        mes_str = fecha_mov.strftime("%m/%Y")
        return "ALQUILER", f"Sin facturas para {mes_str}", "ALQUILER"


def reset_facturas_usadas():
    """Reinicia el control de facturas usadas."""
    global facturas_usadas
    facturas_usadas = set()
