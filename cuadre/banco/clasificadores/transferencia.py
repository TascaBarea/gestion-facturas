from rapidfuzz import fuzz
import pandas as pd
import re

facturas_usadas = set()

def normalizar_nombre(nombre):
    nombre = nombre.upper().strip()
    nombre = re.sub(r"\b(SL|S\.L\.|S\.A\.|SA)\b", "", nombre)
    return re.sub(r"\s+", " ", nombre)

def extraer_nombre_emisor(concepto, df_fuzzy):
    nombre_emisor = concepto.replace("TRANSFERENCIA A", "").strip()
    if "NOMBRE_EN_CONCEPTO" in df_fuzzy.columns:
        fila = df_fuzzy[df_fuzzy["NOMBRE_EN_CONCEPTO"].str.upper() == nombre_emisor]
        if not fila.empty:
            return fila.iloc[0]["TITULO_FACTURA"].strip().upper()
    return nombre_emisor

def buscar_por_importe(df_fact, importe_abs):
    return df_fact[abs(df_fact["Total"] - importe_abs) <= 0.01].copy()

def calcular_similitud(a, b):
    return fuzz.token_sort_ratio(normalizar_nombre(a), normalizar_nombre(b)) / 100

def evaluar_factura_directa(fila, nombre_emisor, fecha_valor):
    cod = fila["Cód."]
    titulo = fila["Título"]
    score = calcular_similitud(nombre_emisor, titulo)
    detalle = "Similitud baja de nombre" if score < 0.6 else titulo

    if (fecha_valor - pd.to_datetime(fila["Fec.Fac."])).days < -21:
        detalle += " — Fecha muy anterior"
    if cod in facturas_usadas:
        detalle += " — Posible duplicado con movimiento anterior"

    facturas_usadas.add(cod)
    return cod, detalle, "TRANSFERENCIA"

def filtrar_por_similitud_y_uso(df, nombre_emisor):
    return df[
        df["Título"].apply(lambda t: calcular_similitud(nombre_emisor, t) >= 0.5) &
        (~df["Cód."].isin(facturas_usadas))
    ].copy()

def todos_mismo_emisor(df, nombre_emisor):
    return all(calcular_similitud(nombre_emisor, t) >= 0.5 for t in df["Título"])

def elegir_mas_cercana_en_fecha(df, fecha_operativa):
    df["Fec.Fac."] = pd.to_datetime(df["Fec.Fac."], errors="coerce")
    df["distancia_dias"] = (fecha_operativa - df["Fec.Fac."]).abs().dt.days
    df = df[~df["Cód."].isin(facturas_usadas)]
    if df.empty:
        return None
    return df.sort_values("distancia_dias").iloc[0]

def clasificar_transferencia(concepto, importe, fecha_valor, fecha_operativa,
                             df_fact, df_fuzzy, df_aux, df_mov, duplicados_control):
    concepto = concepto.upper().strip()

    if concepto == "TRANSFERENCIA A BENJAMIN ORTEGA Y JAIME FDEZ M":
        return "ALQUILER", "", "TRANSFERENCIA"

    if not concepto.startswith("TRANSFERENCIA A"):
        return None, None, None

    nombre_emisor = extraer_nombre_emisor(concepto, df_fuzzy)
    importe_abs = round(abs(float(importe)), 2)
    facturas_candidatas = buscar_por_importe(df_fact, importe_abs)

    if len(facturas_candidatas) == 0:
        return "REVISAR", "Importe de factura no encontrado", "TRANSFERENCIA"
    if len(facturas_candidatas) == 1:
        return evaluar_factura_directa(facturas_candidatas.iloc[0], nombre_emisor, fecha_valor)

    filtradas = filtrar_por_similitud_y_uso(facturas_candidatas, nombre_emisor)

    if len(filtradas) == 1:
        return evaluar_factura_directa(filtradas.iloc[0], nombre_emisor, fecha_valor)

    if todos_mismo_emisor(filtradas, nombre_emisor):
        mejor = elegir_mas_cercana_en_fecha(filtradas, fecha_operativa)
        if mejor is not None:
            return evaluar_factura_directa(mejor, nombre_emisor, fecha_valor)

    codigos = ", ".join(filtradas["Cód."].astype(str).tolist())
    return "REVISAR", f"Elegir entre: {codigos}", "TRANSFERENCIA"