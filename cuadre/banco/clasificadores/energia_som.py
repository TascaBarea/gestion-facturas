
import re

def clasificar_somenergia(concepto, importe, df_fact):
    concepto = str(concepto)
    if "SOM ENERGIA" not in concepto.upper():
        return None, None, None

    match = re.search(r"FAC\d{4,}", concepto.upper())
    if match:
        facnum = match.group()
        fila = df_fact[df_fact['Factura'].astype(str).str.upper() == facnum]
        if not fila.empty:
            fila = fila.iloc[0]
            return fila['Cód.'], facnum, "SOM ENERGIA"
        else:
            return "REVISAR", "Factura no encontrada", "SOM ENERGIA"

    importe_abs = round(abs(float(importe)), 2)
    candidatas = df_fact[abs(df_fact['Total'] - importe_abs) <= 0.01]
    som_matches = candidatas[candidatas['Título'].str.upper().str.contains("SOM ENERGIA")]

    if len(som_matches) == 1:
        fila = som_matches.iloc[0]
        return fila['Cód.'], fila['Factura'], "SOM ENERGIA"
    else:
        return "REVISAR", "Factura no encontrada o múltiples coincidencias", "SOM ENERGIA"
