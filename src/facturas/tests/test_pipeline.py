# tests/test_pipeline.py (actualizado)
"""
Pruebas E2E (extremo a extremo) sobre PDFs reales.

Cómo usar:
  1) Crea carpeta `samples/` en la raíz del repo.
  2) Copia ahí tus PDFs de prueba, por ejemplo:
       samples/3014 3T25 0708 LA MOLIENDA VERDE. TF.pdf
       samples/3047 3T25 0731 LICORES MADRUEÑO TF.pdf
       samples/3049 3T25 0731 PANRUJE TF.pdf
  3) (Opcional recomendado) crea ficheros sidecar `.total` con el total con IVA esperado:
       samples/3014 3T25 0708 LA MOLIENDA VERDE. TF.total
       samples/3047 3T25 0731 LICORES MADRUEÑO TF.total
       samples/3049 3T25 0731 PANRUJE TF.total
     Dentro, escribe el total con formato europeo, p.ej.:  "250,07"  (sin comillas)
  4) Ejecuta:
       pytest -q

Notas:
- El test llama al CLI como función, inyectando `sys.argv` y
  simulando `input()` para el total con IVA cuando el parser lo pide.
- Comprueba que se genera un TSV con el esquema oficial y algunas
  invariantes básicas (sin línea PORTES, columnas presentes, etc.).
"""
from __future__ import annotations

import os
import sys
import importlib
import builtins
from pathlib import Path
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
SAMPLES = ROOT / "samples"
OUT = ROOT / "out_tests"

EXPECTED_COLS = [
    "NumeroArchivo",
    "Fecha",
    "NºFactura",
    "Proveedor",
    "Descripcion",
    "Categoria",
    "BaseImponible",
    "TipoIVA",
    "Observaciones",
]


def _load_total_sidecar(pdf_path: Path) -> str | None:
    sidecar = pdf_path.with_suffix(".total")
    return sidecar.read_text(encoding="utf-8").strip() if sidecar.exists() else None


def _run_cli_on(pdf_path: Path, tsv_out: Path):
    """Importa el módulo CLI y ejecuta main() con argv inyectado.
    Simula input() con el contenido del sidecar .total si hace falta.
    """
    sys.path.insert(0, str(ROOT))
    cli_mod = importlib.import_module("src.facturas.cli")

    argv = [
        str(pdf_path),
        "--lines",
        "--tsv", str(tsv_out),
        "--pretty",
    ]

    total = _load_total_sidecar(pdf_path)

    old_argv = sys.argv[:]
    sys.argv = ["prog"] + argv

    if total is not None:
        old_input = builtins.input
        builtins.input = lambda prompt=None: total
    else:
        old_input = None

    try:
        cli_mod.main()
    finally:
        sys.argv = old_argv
        if old_input is not None:
            builtins.input = old_input


@pytest.mark.parametrize(
    "pdf_name",
    [
        "3014 3T25 0708 LA MOLIENDA VERDE. TF.pdf",
        "3047 3T25 0731 LICORES MADRUEÑO TF.pdf",
        "3049 3T25 0731 PANRUJE TF.pdf",
    ],
)
def test_pipeline_tsv_generado(pdf_name: str):
    pdf_path = SAMPLES / pdf_name
    assert pdf_path.exists(), f"Falta sample: {pdf_path}"

    OUT.mkdir(exist_ok=True)
    tsv_out = OUT / (Path(pdf_name).stem + ".tsv")
    if tsv_out.exists():
        tsv_out.unlink()

    _run_cli_on(pdf_path, tsv_out)

    assert tsv_out.exists(), "No se generó el TSV de salida"

    df = pd.read_csv(tsv_out, sep="\t", dtype=str).fillna("")

    # 1) Columnas oficiales
    assert list(df.columns) == EXPECTED_COLS, f"Columnas inesperadas: {df.columns}"

    # 2) No debe haber líneas PORTES (se prorratean)
    assert not any(df["Descripcion"].str.upper().str.contains("PORTE")), "Aún aparece línea PORTES"

    # 3) Tipos IVA válidos
    valid_iva = {"21", "10", "4", "5", "2", "0", "REVISAR"}
    assert set(df["TipoIVA"].unique()) <= valid_iva, f"TipoIVA fuera de rango: {df['TipoIVA'].unique()}"

    # 4) Formato europeo en BaseImponible
    assert df["BaseImponible"].str.contains(
        r"^\d{1,3}(\.\d{3})*,\d{2}$|^\d+,\d{2}$",
        regex=True,
    ).all(), "BaseImponible no está en formato europeo (p.ej. 1.234,56)"


@pytest.mark.parametrize(
    "pdf_name",
    [
        "3014 3T25 0708 LA MOLIENDA VERDE. TF.pdf",
        "3047 3T25 0731 LICORES MADRUEÑO TF.pdf",
        "3049 3T25 0731 PANRUJE TF.pdf",
    ],
)
def test_total_con_iva_cuadrado(pdf_name: str):
    """Verifica que el total con IVA coincida con el sidecar .total (si se proporciona)."""
    pdf_path = SAMPLES / pdf_name
    total = _load_total_sidecar(pdf_path)
    if total is None:
        pytest.skip("Sin sidecar .total: se omite el test de cuadre")

    OUT.mkdir(exist_ok=True)
    tsv_out = OUT / (Path(pdf_name).stem + ".tsv")
    if tsv_out.exists():
        tsv_out.unlink()

    _run_cli_on(pdf_path, tsv_out)

    df = pd.read_csv(tsv_out, sep="\t", dtype=str).fillna("")

    def _eu_to_float(s: str) -> float:
        return float(s.replace(".", "").replace(",", ".")) if s else 0.0

    tot = 0.0
    for _, row in df.iterrows():
        base = _eu_to_float(row["BaseImponible"])
        iva = row["TipoIVA"].strip()
        iva_f = 0.0 if not iva or iva == "REVISAR" else float(iva) / 100.0
        tot += base * (1.0 + iva_f)

    tot = round(tot + 1e-9, 2)
    exp = _eu_to_float(total)

    assert abs(tot - exp) < 0.01, f"Total con IVA {tot} != esperado {exp}"

