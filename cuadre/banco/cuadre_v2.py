#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
================================================================================
CUADRE.PY v2.0 — Clasificador de Movimientos Bancarios (CLI)
================================================================================

Wrapper CLI sobre cuadre_engine.py.
Cruza movimientos bancarios con facturas. Sistema de 3 capas:
  Capa 1: Reglas estructurales (TPV, comisiones, nóminas…)
  Capa 2: Memoria histórica + cruce de facturas
  Capa 3: REVISAR

USO:
    python -m cuadre.banco.cuadre \\
        --desde 02/01/2025 --hasta 31/12/2025 \\
        --movimientos "datos/Movimientos Cuenta 2025.xlsx" \\
        --facturas-historico "datos/Movimientos Cuenta 2025.xlsx" \\
        --output "outputs/CUADRE_020125-311225.xlsx" \\
        --verbose

    python -m cuadre.banco.cuadre --aprender "outputs/CUADRE_corregido.xlsx"

REQUISITOS:
    pip install pandas openpyxl rapidfuzz
================================================================================
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path

from cuadre.banco.cuadre_engine import CuadreEngine

# ── Rutas por defecto ─────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATOS_DIR = BASE_DIR / "datos"
OUTPUTS_DIR = BASE_DIR / "outputs"
MEMORIA_DEFAULT = DATOS_DIR / "clasificaciones_historicas.json"
MAESTRO_DEFAULT = DATOS_DIR / "MAESTRO_PROVEEDORES.xlsx"

# Si la memoria no está en datos/, buscar junto al script (retrocompatibilidad)
if not MEMORIA_DEFAULT.exists():
    _alt = Path(__file__).resolve().parent / "clasificaciones_historicas.json"
    if _alt.exists():
        MEMORIA_DEFAULT = _alt


def _parse_fecha(s: str) -> datetime:
    """Parsea fecha DD/MM/YYYY."""
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%d/%m/%y", "%d-%m-%y"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    raise argparse.ArgumentTypeError(f"Fecha inválida: '{s}'. Usar DD/MM/YYYY")


def _generar_nombre_salida(desde: datetime, hasta: datetime) -> str:
    return f"CUADRE_{desde.strftime('%d%m%y')}-{hasta.strftime('%d%m%y')}.xlsx"


def main():
    parser = argparse.ArgumentParser(
        description="Cuadre Bancario v2.0 — Clasificador de movimientos",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # Modo normal
    parser.add_argument("--desde", type=str, help="Fecha inicio DD/MM/YYYY")
    parser.add_argument("--hasta", type=str, help="Fecha fin DD/MM/YYYY")
    parser.add_argument("--movimientos", type=str, help="Ruta al Excel MOV_BANCO")
    parser.add_argument("--facturas-provisional", type=str, help="Ruta al Excel facturas provisional")
    parser.add_argument("--facturas-historico", type=str, help="Ruta al Excel facturas histórico")
    parser.add_argument("--memoria", type=str, default=str(MEMORIA_DEFAULT), help="Ruta al JSON de memoria")
    parser.add_argument("--maestro", type=str, default=str(MAESTRO_DEFAULT), help="Ruta al MAESTRO_PROVEEDORES")
    parser.add_argument("--output", "-o", type=str, help="Ruta de salida (auto si no se indica)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Mostrar detalle de clasificación")

    # Modo aprender
    parser.add_argument("--aprender", type=str, help="Ruta a un CUADRE corregido para actualizar memoria")

    # Retrocompatibilidad: modo GUI
    parser.add_argument("--archivo", type=str, help="(legacy) Ruta archivo - redirige a --movimientos")

    args = parser.parse_args()

    # ── Modo aprender ─────────────────────────────────────────────────────────
    if args.aprender:
        _modo_aprender(args)
        return

    # ── Modo cuadre ───────────────────────────────────────────────────────────
    _modo_cuadre(args)


def _modo_aprender(args):
    """Lee un CUADRE corregido y actualiza la memoria histórica."""
    cuadre_path = Path(args.aprender)
    if not cuadre_path.exists():
        print(f"❌ Archivo no encontrado: {cuadre_path}")
        sys.exit(1)

    memoria_path = Path(args.memoria)
    print(f"CUADRE v2.0 — Modo Aprender")
    print(f"  Cuadre: {cuadre_path.name}")
    print(f"  Memoria: {memoria_path}")

    engine = CuadreEngine()
    n = engine.aprender_de_cuadre(cuadre_path, memoria_path)
    print(f"  ✅ Memoria actualizada: {n} conceptos")


def _modo_cuadre(args):
    """Ejecuta el cuadre completo."""
    # ── Resolver archivo de movimientos ───────────────────────────────────────
    mov_path = args.movimientos or args.archivo
    if not mov_path:
        # Intentar GUI si tkinter disponible
        mov_path = _seleccionar_archivo_gui()
        if not mov_path:
            print("❌ No se indicó archivo de movimientos. Usar --movimientos <ruta>")
            sys.exit(1)

    mov_path = Path(mov_path)
    if not mov_path.exists():
        print(f"❌ Archivo no encontrado: {mov_path}")
        sys.exit(1)

    # ── Resolver fechas ───────────────────────────────────────────────────────
    if args.desde and args.hasta:
        desde = _parse_fecha(args.desde)
        hasta = _parse_fecha(args.hasta)
    else:
        # Auto-detectar rango del archivo
        desde, hasta = _auto_detectar_rango(mov_path)
        if desde is None:
            print("❌ No se pudieron detectar fechas. Usar --desde y --hasta")
            sys.exit(1)

    # ── Banner ────────────────────────────────────────────────────────────────
    print("=" * 70)
    print("CUADRE BANCARIO v2.0")
    print("=" * 70)
    print(f"Período: {desde.strftime('%d/%m/%Y')} – {hasta.strftime('%d/%m/%Y')}")
    print(f"MOV_BANCO: {mov_path.name}")

    # ── Crear engine ──────────────────────────────────────────────────────────
    memoria_path = Path(args.memoria)
    maestro_path = Path(args.maestro)

    engine = CuadreEngine(
        memoria_path=memoria_path if memoria_path.exists() else None,
        maestro_path=maestro_path if maestro_path.exists() else None,
        verbose=args.verbose,
    )

    if memoria_path.exists():
        print(f"Memoria: {len(engine.memoria)} conceptos cargados")
    else:
        print(f"Memoria: no encontrada ({memoria_path})")

    # ── Cargar movimientos ────────────────────────────────────────────────────
    movimientos = engine.cargar_movimientos(mov_path)
    for nombre, df in movimientos.items():
        # Mostrar total y filtrado
        n_total = len(df)
        df_filtrado = engine.filtrar_por_fechas(df, desde, hasta)
        print(f"  {nombre}: {len(df_filtrado)} movimientos en rango (de {n_total} total)")

    # ── Cargar facturas ───────────────────────────────────────────────────────
    df_fact_hist = None
    df_fact_prov = None

    if args.facturas_historico:
        p = Path(args.facturas_historico)
        if p.exists():
            df_fact_hist = engine.cargar_facturas_historico(p)
            print(f"Facturas histórico: {len(df_fact_hist)} registros")
        else:
            print(f"  ⚠️  Facturas histórico no encontrado: {p}")
    else:
        # Auto-buscar hoja Facturas dentro de MOV_BANCO
        import pandas as pd
        xlsx = pd.ExcelFile(mov_path)
        if "Facturas" in xlsx.sheet_names:
            df_fact_hist = engine.cargar_facturas_historico(mov_path)
            print(f"Facturas (desde MOV_BANCO): {len(df_fact_hist)} registros")

    if args.facturas_provisional:
        p = Path(args.facturas_provisional)
        if p.exists():
            df_fact_prov = engine.cargar_facturas_provisional(p)
            print(f"Facturas provisional: {len(df_fact_prov)} registros")
        else:
            print(f"  ⚠️  Facturas provisional no encontrado: {p}")

    df_facturas = engine.unificar_facturas(hist=df_fact_hist, prov=df_fact_prov)
    n_total_fact = len(df_facturas)
    n_hist = len(df_fact_hist) if df_fact_hist is not None else 0
    n_prov = len(df_fact_prov) if df_fact_prov is not None else 0
    if n_hist and n_prov:
        print(f"Facturas: {n_hist} histórico + {n_prov} provisional = {n_total_fact} total")
    elif n_total_fact:
        print(f"Facturas: {n_total_fact} total")

    # ── Ejecutar clasificación ────────────────────────────────────────────────
    print()
    resultado = engine.procesar(movimientos, df_facturas, desde=desde, hasta=hasta)

    # ── Estadísticas ──────────────────────────────────────────────────────────
    s = resultado.stats
    total = s["total"]

    print(f"\nCLASIFICACIÓN:")
    if total > 0:
        print(f"  Capa 1 (reglas):    {s['capa1']:>4} movimientos ({100*s['capa1']/total:.1f}%)")
        print(f"  Capa 2a (memoria):  {s['capa2a']:>4} movimientos ({100*s['capa2a']/total:.1f}%)")
        print(f"  Capa 2b (facturas): {s['capa2b']:>4} movimientos ({100*s['capa2b']/total:.1f}%)")
        print(f"  Capa 3 (REVISAR):   {s['capa3']:>4} movimientos ({100*s['capa3']/total:.1f}%)")

    # Vinculación facturas
    n_vinculadas = sum(1 for _, row in resultado.df_facturas.iterrows()
                       if row.get("Origen") and str(row["Origen"]).strip())
    print(f"\nVINCULACIÓN FACTURAS:")
    print(f"  Vinculadas a movimiento: {n_vinculadas} facturas")
    print(f"  Sin vincular: {n_total_fact - n_vinculadas} facturas")

    # ── Guardar ───────────────────────────────────────────────────────────────
    if args.output:
        ruta_salida = Path(args.output)
    else:
        nombre = _generar_nombre_salida(desde, hasta)
        ruta_salida = OUTPUTS_DIR / nombre if OUTPUTS_DIR.exists() else mov_path.parent / nombre

    print(f"\n💾 Guardando: {ruta_salida}")
    try:
        engine.guardar_excel(resultado, ruta_salida)
        print(f"  ✅ Excel guardado")
    except PermissionError:
        print(f"  ❌ Error: El archivo está abierto en Excel. Ciérralo e intenta de nuevo.")
        sys.exit(1)

    # Log
    ruta_log = engine.guardar_log(resultado, ruta_salida)
    print(f"  📝 Log: {ruta_log.name}")

    # JSON Streamlit
    ruta_json = OUTPUTS_DIR / "cuadre_resumen.json"
    engine.exportar_json_streamlit(resultado, ruta_json)
    print(f"  📋 JSON Streamlit: {ruta_json.name}")

    # ── Resumen final ─────────────────────────────────────────────────────────
    total_ok = total - s["capa3"]
    print()
    print("=" * 70)
    print("✅ PROCESO COMPLETADO")
    print("=" * 70)
    print(f"  📊 Total movimientos: {total}")
    print(f"  ✅ Clasificados: {total_ok} ({100*total_ok/total:.1f}%)" if total else "")
    print(f"  ⚠️  A revisar: {s['capa3']} ({100*s['capa3']/total:.1f}%)" if total else "")
    print(f"  📄 Archivo: {ruta_salida}")
    print()


def _auto_detectar_rango(mov_path: Path):
    """Auto-detecta rango de fechas del archivo de movimientos."""
    import pandas as pd
    try:
        xlsx = pd.ExcelFile(mov_path)
        fecha_min, fecha_max = None, None
        for sheet in xlsx.sheet_names:
            sn = sheet.strip().upper()
            if sn not in ("TASCA", "COMESTIBLES"):
                continue
            df = pd.read_excel(xlsx, sheet_name=sheet)
            for col in ["F. Operativa", "F. Valor"]:
                if col in df.columns:
                    fechas = pd.to_datetime(df[col], errors="coerce", dayfirst=True)
                    if fechas.notna().any():
                        fmin = fechas.min()
                        fmax = fechas.max()
                        if fecha_min is None or fmin < fecha_min:
                            fecha_min = fmin
                        if fecha_max is None or fmax > fecha_max:
                            fecha_max = fmax
        if fecha_min and fecha_max:
            return fecha_min.to_pydatetime(), fecha_max.to_pydatetime()
    except Exception:
        pass
    return None, None


def _seleccionar_archivo_gui():
    """Intenta abrir diálogo de selección de archivo."""
    try:
        import tkinter as tk
        from tkinter import filedialog
        import os
        downloads = Path(os.environ.get("USERPROFILE", str(Path.home()))) / "Downloads"
        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        archivo = filedialog.askopenfilename(
            title="Selecciona el archivo Excel con movimientos",
            initialdir=str(downloads if downloads.exists() else Path.cwd()),
            filetypes=[("Excel", "*.xlsx *.xls"), ("Todos", "*.*")],
        )
        root.destroy()
        return archivo if archivo else None
    except Exception:
        return None


if __name__ == "__main__":
    main()
