# src/facturas/export/master.py
import os
import time
import pandas as pd

COLUMNS = [
    "NumeroArchivo","Fecha","NºFactura","Proveedor",
    "Descripcion","Categoria","TipoIVA","BaseImponible",
    "Observaciones","TotalConIVA"
]

def _safe_write(path: str, write_fn):
    try:
        write_fn(path)
        return path
    except PermissionError:
        base, ext = os.path.splitext(path)
        alt = f"{base}_{time.strftime('%Y%m%d_%H%M%S')}{ext}"
        write_fn(alt)
        print(f"[AVISO] '{path}' estaba en uso. Guardado como: {alt}")
        return alt

def _load_master(path: str) -> pd.DataFrame:
    if os.path.exists(path):
        try:
            df = pd.read_excel(path, sheet_name="Lineas")
        except Exception:
            df = pd.read_excel(path)  # por si no existe la hoja
    else:
        df = pd.DataFrame(columns=COLUMNS)
    # asegurar columnas
    for c in COLUMNS:
        if c not in df.columns:
            df[c] = "" if c != "BaseImponible" else 0
    return df.loc[:, COLUMNS]

def upsert_maestro(df_lineas: pd.DataFrame, header: dict, maestro_path: str) -> str:
    # asegurar columnas en las líneas nuevas
    df_lineas = df_lineas.copy()
    if "TotalConIVA" not in df_lineas.columns:
        df_lineas["TotalConIVA"] = header.get("TotalConIVA", "")
    for c in COLUMNS:
        if c not in df_lineas.columns:
            df_lineas[c] = "" if c != "BaseImponible" else 0
    df_lineas = df_lineas.loc[:, COLUMNS]

    master = _load_master(maestro_path)

    # clave de reemplazo: Proveedor + NºFactura + Fecha (conservar TotalConIVA en Observaciones para trazabilidad)
    mask = (
        (master["Proveedor"] == header.get("Proveedor","")) &
        (master["NºFactura"] == header.get("NºFactura","")) &
        (master["Fecha"] == header.get("Fecha",""))
    )
    master = master.loc[~mask].copy()
    master = pd.concat([master, df_lineas], ignore_index=True)

    def _write(target_path: str):
        with pd.ExcelWriter(target_path, engine="xlsxwriter") as w:
            master.to_excel(w, sheet_name="Lineas", index=False)
            # formato básico
            ws = w.sheets["Lineas"]
            if "BaseImponible" in master.columns:
                money_fmt = w.book.add_format({"num_format": "#,##0.00"})
                idx = master.columns.get_loc("BaseImponible")
                ws.set_column(idx, idx, 12, money_fmt)
            for i, col in enumerate(master.columns):
                width = 12
                if col in ("Descripcion", "Observaciones"): width = 60 if col == "Descripcion" else 30
                elif col in ("Proveedor","Categoria"): width = 18
                ws.set_column(i, i, width)
            ws.autofilter(0, 0, max(0, len(master)), max(0, len(master.columns)-1))
    return _safe_write(maestro_path, _write)
