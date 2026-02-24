# tests/test_excel_export.py
import os
import re
from pathlib import Path
import math
import pandas as pd
import pytest

# === Config ===
# 1) Si defines EXCEL_PATH, usará ese archivo
# 2) Si no, toma el último .xlsx en .\out\
EXCEL_ENV = os.getenv("EXCEL_PATH", "").strip()
OUT_DIR = Path("./out")


def _latest_excel_in_out() -> Path:
    candidates = sorted(OUT_DIR.glob("*.xlsx"), key=lambda p: p.stat().st_mtime, reverse=True)
    return candidates[0] if candidates else None


def _get_excel_path() -> Path:
    if EXCEL_ENV:
        p = Path(EXCEL_ENV)
        if not p.exists():
            pytest.skip(f"EXCEL_PATH '{p}' no existe; genera un Excel primero.")
        return p
    else:
        p = _latest_excel_in_out()
        if not p:
            pytest.skip("No se encontró ningún Excel en .\\out. Genera uno con el CLI antes de correr los tests.")
        return p


def _parse_eu_decimal(s):
    """
    Convierte '1.234,56' / '123,45' / '123' (texto) a float (en notación Python).
    Si no puede convertir, devuelve None.
    """
    if s is None:
        return None
    if isinstance(s, (int, float)):
        return float(s)
    t = str(s).strip()
    if t == "":
        return None
    # Si parece formato europeo, remover separador de miles y cambiar coma por punto
    t2 = t.replace(".", "").replace(",", ".")
    try:
        return float(t2)
    except Exception:
        return None


def test_excel_file_exists():
    p = _get_excel_path()
    assert p and p.exists(), "No se encontró el Excel para validar."


def test_required_sheets():
    p = _get_excel_path()
    xl = pd.ExcelFile(p)
    sheets = set(xl.sheet_names)
    assert "Líneas" in sheets or "Lineas" in sheets, f"Falta hoja 'Líneas' en {p.name}"
    assert "Metadata" in sheets, f"Falta hoja 'Metadata' en {p.name}"


def test_required_columns_present():
    p = _get_excel_path()
    try:
        df = pd.read_excel(p, sheet_name="Líneas")
    except ValueError:
        df = pd.read_excel(p, sheet_name="Lineas")

    cols = set(df.columns.astype(str))
    required = {"Descripcion", "BaseImponible", "TipoIVA"}  # Categoria opcional
    missing = required - cols
    assert not missing, f"Faltan columnas requeridas en 'Líneas': {missing}"


def test_base_imponible_eu_format_most_rows():
    """
    Verifica que la mayoría de BaseImponible venga con coma decimal (formato europeo).
    Acepta algunas celdas vacías o no numéricas.
    """
    p = _get_excel_path()
    try:
        df = pd.read_excel(p, sheet_name="Líneas", dtype=str)
    except ValueError:
        df = pd.read_excel(p, sheet_name="Lineas", dtype=str)

    bi = df["BaseImponible"].dropna().astype(str).str.strip()
    if len(bi) == 0:
        pytest.skip("No hay BaseImponible poblado para validar (todas vacías).")

    # patrón simple: termina con ,dd
    pat = re.compile(r".*,\d{2}$")
    matches = bi.apply(lambda x: bool(pat.search(x)))
    ratio = matches.mean()
    assert ratio >= 0.7, f"Menos del 70% de BaseImponible está en formato europeo (coma y 2 decimales). Ratio={ratio:.2f}"


def test_no_totales_rows_in_lineas():
    """
    Chequea que no se hayan colado filas de totales en la hoja de 'Líneas'
    (p. ej., 'TOTAL FACTURA', 'BASE IMPONIBLE').
    """
    p = _get_excel_path()
    try:
        df = pd.read_excel(p, sheet_name="Líneas", dtype=str)
    except ValueError:
        df = pd.read_excel(p, sheet_name="Lineas", dtype=str)

    descs = df["Descripcion"].fillna("").str.lower()
    bad = descs.str.startswith("total") | descs.str.contains(" base imponible")
    assert bad.sum() == 0, f"Se colaron {bad.sum()} filas de totales/pie en 'Líneas'."


def test_iva_and_totallinea_if_present():
    """
    Si las columnas ImporteIVA y TotalLinea existen: validar cálculos.
    Si no existen, el test hace skip (no bloquea tu pipeline).
    """
    p = _get_excel_path()
    try:
        df = pd.read_excel(p, sheet_name="Líneas", dtype=str)
    except ValueError:
        df = pd.read_excel(p, sheet_name="Lineas", dtype=str)

    cols = set(df.columns.astype(str))
    if not {"ImporteIVA", "TotalLinea"}.issubset(cols):
        pytest.skip("Aún no se exportan columnas ImporteIVA/TotalLinea; test saltado.")

    # Convierte columnas
    df["BI_f"] = df["BaseImponible"].apply(_parse_eu_decimal)
    df["IVA_num"] = df["TipoIVA"].apply(lambda x: _parse_eu_decimal(x) if str(x).strip().upper() != "REVISAR" else None)
    df["ImpIVA_f"] = df["ImporteIVA"].apply(_parse_eu_decimal)
    df["Total_f"] = df["TotalLinea"].apply(_parse_eu_decimal)

    # Filas calculables (TipoIVA numérico y BI válida)
    m = df["BI_f"].notna() & df["IVA_num"].notna()
    if m.sum() == 0:
        pytest.skip("No hay filas calculables (TipoIVA numérico + BaseImponible válida).")

    sub = df[m].copy()

    # Cálculo esperado
    sub["ImpIVA_exp"] = (sub["BI_f"] * sub["IVA_num"] / 100).round(2)
    sub["Total_exp"] = (sub["BI_f"] + sub["ImpIVA_exp"]).round(2)

    # Compara con tolerancia de 0,01
    def _close(a, b, tol=0.01):
        return (a is not None) and (b is not None) and (not math.isnan(a)) and (not math.isnan(b)) and abs(a - b) <= tol

    bad_iva = ~sub.apply(lambda r: _close(r["ImpIVA_f"], r["ImpIVA_exp"]), axis=1)
    bad_total = ~sub.apply(lambda r: _close(r["Total_f"], r["Total_exp"]), axis=1)

    assert bad_iva.sum() == 0, f"{bad_iva.sum()} filas con ImporteIVA distinto del esperado."
    assert bad_total.sum() == 0, f"{bad_total.sum()} filas con TotalLinea distinto del esperado."
