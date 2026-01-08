
def clasificar_yoigo(concepto, df_fact):
    concepto = str(concepto)
    if "YOIGO" not in concepto.upper():
        return None, None, None

    import re
    match = re.search(r"C\d{9,}", concepto.upper())
    if match:
        codigo = match.group()
        fila = df_fact[df_fact["Factura"].astype(str).str.upper() == codigo]
        if not fila.empty:
            return fila.iloc[0]["Cód."], codigo, "YOIGO"

    return "REVISAR", "Factura YOIGO no encontrada", "YOIGO"
