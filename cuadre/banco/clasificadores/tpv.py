import re
import pandas as pd

# Estructura de control: {(fecha, comercio, remesa, tipo): True}
remesas_usadas = set()

def clasificar_tpv(concepto, fecha_valor, df_mov):
    concepto = concepto.upper().strip()

    if not (concepto.startswith("ABONO TPV") or concepto.startswith("COMISIONES")):
        return None, None, None

    # Comercios permitidos
    comercios_validos = {
        "0337410674": "TASCA",
        "0354768939": "COMESTIBLES",
        "0354272759": "TALLERES"
    }

    # Detectar Número de Comercio
    comercio_match = re.search(r"\b(0337410674|0354768939|0354272759)\b", concepto)
    if not comercio_match:
        return "REVISAR", "Número de Comercio desconocido", "TPV"
    numero_comercio = comercio_match.group()
    nombre_comercio = comercios_validos[numero_comercio]

    # Detectar Número de Remesa (último número de 10 dígitos al final)
    remesa_match = re.findall(r"\b\d{10}\b", concepto)
    numero_remesa = remesa_match[-1] if remesa_match else "REMESA NO DETECTADA"

    clave_control = (fecha_valor.date(), numero_comercio, numero_remesa)

    # --- ABONO TPV ---
    if concepto.startswith("ABONO TPV"):
        if (clave_control + ("ABONO",)) in remesas_usadas:
            return "REVISAR", numero_remesa, "TPV"
        remesas_usadas.add(clave_control + ("ABONO",))
        tipo = f"TPV {nombre_comercio} {numero_comercio}"
        return tipo, numero_remesa, "TPV"

    # --- COMISIONES TPV ---
    if concepto.startswith("COMISIONES"):
        abonos_mismo_dia = df_mov[
            (pd.to_datetime(df_mov["F. Valor"], errors="coerce").dt.date == fecha_valor.date()) &
            (df_mov["Concepto"].str.upper().str.startswith("ABONO TPV")) &
            (df_mov["Concepto"].str.contains(numero_comercio)) &
            (df_mov["Concepto"].str.contains(numero_remesa))
        ]

        if abonos_mismo_dia.empty:
            return "REVISAR", "Abono no encontrado", "TPV"
        if len(abonos_mismo_dia) > 1:
            return "REVISAR", "Varios abonos con misma F. Valor", "TPV"

        if (clave_control + ("COMISIONES",)) in remesas_usadas:
            return "REVISAR", numero_remesa, "TPV"
        remesas_usadas.add(clave_control + ("COMISIONES",))

        abono = abonos_mismo_dia.iloc[0]
        abono_importe = abs(float(abono["Importe"]))

        try:
            comision_importe = abs(float(df_mov[df_mov["Concepto"] == concepto]["Importe"].values[0]))
            porcentaje = round((comision_importe / abono_importe) * 100, 3)
            detalle = f"{numero_remesa} — {porcentaje:.3f}%"
            tipo = f"Comisiones TPV {nombre_comercio}"
            return tipo, detalle, "TPV"
        except Exception as e:
            return "REVISAR", f"Error en cálculo comisión: {str(e)}", "TPV"

    return None, None, None