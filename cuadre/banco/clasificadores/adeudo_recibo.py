
from difflib import SequenceMatcher

def fuzzy_match(a, b):
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()

def clasificar_adeudo(concepto, importe, f_valor, df_fact, df_fuzzy):
    importe_abs = round(abs(float(importe)), 2)
    facturas = df_fact[abs(df_fact["Total"] - importe_abs) <= 0.01]

    if len(facturas) == 0:
        return "REVISAR", "Importe no encontrado", "ADEUDO RECIBO"

    if len(facturas) == 1:
        f = facturas.iloc[0]
        return f["Cód."], f["Factura"], "ADEUDO RECIBO"

    return "REVISAR", "Varias facturas posibles", "ADEUDO RECIBO"
