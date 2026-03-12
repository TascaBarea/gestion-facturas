
from rapidfuzz import fuzz
import pandas as pd
import unicodedata
from datetime import datetime

facturas_usadas = set()

# ---------------------- CASOS ESPECIALES ----------------------
REGLAS_ESPECIALES = [
    {"clave": "PANIFIESTO LAVAPIES", "titulo": "PANIFIESTO LAVAPIES SL"},
    {"clave": "AY MADRE LA FRUTA", "titulo": "GARCIA VIVAS JULIO"},
]

# ---------------------- FUNCIONES AUXILIARES ----------------------
def normalizar_nombre(nombre):
    if not isinstance(nombre, str):
        return ""
    nombre = unicodedata.normalize("NFKD", nombre)
    nombre = "".join(c for c in nombre if not unicodedata.combining(c))
    nombre = nombre.upper().strip()
    for suf in ["S.L.", "SL", "S.A.", "SA"]:
        nombre = nombre.replace(suf, "")
    return " ".join(nombre.split())

def calcular_similitud(a, b):
    return fuzz.token_sort_ratio(normalizar_nombre(a), normalizar_nombre(b)) / 100

def extraer_nombre_emisor(concepto, df_fuzzy):
    try:
        nombre = concepto[30:].split("-")[0].strip().upper()
        fila = df_fuzzy[df_fuzzy["NOMBRE_EN_CONCEPTO"].str.upper() == nombre]
        if not fila.empty:
            return fila.iloc[0]["TITULO_FACTURA"].strip().upper()
        return nombre
    except (IndexError, KeyError, TypeError):
        return ""

def buscar_facturas_por_importe(df_fact, importe):
    importe_abs = round(abs(float(importe)), 2)
    return df_fact[abs(df_fact["Total"] - importe_abs) <= 0.01].copy()

def filtrar_por_similitud_y_uso(df, nombre_emisor):
    return df[
        df["Título"].apply(lambda t: calcular_similitud(nombre_emisor, t) >= 0.4) &
        (~df["Cód."].isin(facturas_usadas))
    ].copy()

def todos_mismo_emisor(df):
    titulos = df["Título"].dropna().astype(str).unique()
    if len(titulos) < 2:
        return True
    base = titulos[0]
    return all(calcular_similitud(base, otro) >= 0.5 for otro in titulos[1:])

def elegir_mas_cercana_en_fecha(df, fecha_valor):
    df = df.copy()
    df["Fec.Fac."] = pd.to_datetime(df["Fec.Fac."], errors="coerce")
    df["dist"] = (fecha_valor - df["Fec.Fac."]).abs().dt.days
    return df.sort_values("dist").iloc[0]

def es_caso_especial(concepto):
    concepto_upper = concepto.upper()
    for regla in REGLAS_ESPECIALES:
        if regla["clave"] in concepto_upper:
            return regla
    return None

def buscar_factura_mes(fecha_valor, df_fact, titulo_emisor):
    facturas = df_fact[df_fact["Título"].apply(lambda t: normalizar_nombre(t) == normalizar_nombre(titulo_emisor))]
    facturas = facturas.assign(**{"Fec.Fac.": pd.to_datetime(facturas["Fec.Fac."], errors="coerce", dayfirst=True)})
    mismas = facturas[(facturas["Fec.Fac."].dt.month == fecha_valor.month) &
                      (facturas["Fec.Fac."].dt.year == fecha_valor.year)]
    if len(mismas) == 1:
        return mismas.iloc[0]["Cód."], "Pago Parcial"
    elif len(mismas) > 1:
        return "REVISAR", "Error puto Jaime"
    else:
        return "REVISAR", f"Sin factura ese Mes de {titulo_emisor}"  

# ---------------------- CLASIFICADOR PRINCIPAL ----------------------
def clasificar_compra_tarjeta(concepto, importe, fecha_valor, fecha_operativa,
                              df_fact, df_fuzzy, df_aux, df_mov):
    try:
        concepto = str(concepto).strip().upper()
        protocolo = "COMPRA TARJ."

        if not concepto.startswith(protocolo):
            return None, None, None

        # --- CASO ESPECIAL ---
        especial = es_caso_especial(concepto)
        if especial:
            cod, detalle = buscar_factura_mes(fecha_valor, df_fact, especial["titulo"])
            return cod, detalle, protocolo

        # --- GENERAL ---
        nombre_emisor = extraer_nombre_emisor(concepto, df_fuzzy)
        facturas_candidatas = buscar_facturas_por_importe(df_fact, importe)

        if facturas_candidatas.empty:
            return "REVISAR", "Importe no encontrado", protocolo

        if len(facturas_candidatas) == 1:
            cod = facturas_candidatas.iloc[0]["Cód."]
            facturas_usadas.add(cod)
            return cod, nombre_emisor, protocolo

        candidatas = filtrar_por_similitud_y_uso(facturas_candidatas, nombre_emisor)

        if candidatas.empty:
            return "REVISAR", "Nombre no encontrado", protocolo

        candidatas = candidatas.sort_values(by=candidatas["Título"].apply(lambda t: calcular_similitud(nombre_emisor, t)), ascending=False).head(2)

        if len(candidatas) == 1:
            cod = candidatas.iloc[0]["Cód."]
            facturas_usadas.add(cod)
            return cod, nombre_emisor, protocolo

        if todos_mismo_emisor(candidatas):
            mejor = elegir_mas_cercana_en_fecha(candidatas, fecha_valor)
            cod = mejor["Cód."]
            facturas_usadas.add(cod)
            return cod, nombre_emisor, protocolo

        codigos = ", ".join(candidatas["Cód."].astype(str).tolist())
        return "REVISAR", codigos, protocolo

    except Exception as e:
        return "REVISAR", "Fallo Desconocido", "COMPRA TARJ."
