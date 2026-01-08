import sys, os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
from router import clasificar_movimiento

archivo_default = "PROVEEDOR 2025.xlsx"
archivo = input("¿Cómo se llama el archivo de movimientos (Debe incluir la hoja Facturas de Kinema y los movimientos en las hojas Tasca y Comestibles)?\n[{}]: ".format(archivo_default)).strip()
if not archivo:
    archivo = archivo_default

if not os.path.exists(archivo):
    print(f"❌ No se encuentra el archivo '{archivo}'")
    exit(1)

excel_file = pd.ExcelFile(archivo)
hojas_disponibles = excel_file.sheet_names

if "Tasca" in hojas_disponibles and "Comestibles" in hojas_disponibles:
    hoja = input("¿Qué hoja quieres procesar: Tasca o Comestibles? [Tasca]: ").strip().capitalize()
    if hoja not in ["Tasca", "Comestibles"]:
        hoja = "Tasca"
else:
    print("❌ No se encuentran las hojas 'Tasca' y 'Comestibles' en el archivo.")
    exit(1)

df_mov = pd.read_excel(archivo, sheet_name=hoja)
df_fact = pd.read_excel(archivo, sheet_name="Facturas")
df_fuzzy = pd.read_excel("DiccionarioEmisorTitulo.xlsx")
df_aux = None

resultados = []
for _, row in df_mov.iterrows():
    concepto = row["Concepto"]
    importe = row["Importe"]
    f_valor = pd.to_datetime(row["F. Valor"], errors="coerce")
    f_oper = pd.to_datetime(row.get("F. Operativa", f_valor), errors="coerce")
    cod, detalle, protocolo = clasificar_movimiento(concepto, importe, f_valor, f_oper,
                                                    df_fact, df_fuzzy, df_aux, df_mov, set())
    resultados.append({
        "#": row["#"],
        "F. Valor": row["F. Valor"],
        "Concepto": concepto,
        "Importe": importe,
        "CLASIFICACION_TIPO": cod,
        "CLASIFICACION_DETALLE": detalle,
        "PROTOCOLO_APLICADO": protocolo
    })

df_out = pd.DataFrame(resultados)
salida = "clasificados.xlsx"

if os.path.exists(salida):
    overwrite = input(f"⚠️ El archivo '{salida}' ya existe. ¿Quieres sobrescribirlo? [s/N]: ").strip().lower()
    if overwrite != "s":
        print("❌ Operación cancelada.")
        exit(0)

df_out.to_excel(salida, index=False)
print(f"✅ Archivo generado correctamente: {salida}")