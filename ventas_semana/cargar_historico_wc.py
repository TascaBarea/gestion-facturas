"""
cargar_historico_wc.py — Carga histórica de pedidos WooCommerce
================================================================
Uso (ejecutar UNA SOLA VEZ):
    python ventas_semana/cargar_historico_wc.py

Descarga todos los pedidos WooCommerce desde el 01/01/2025 hasta el
15/03/2026 (inclusive) y los guarda en la pestaña WOOCOMMERCE del Excel
de ventas, en el mismo formato limpio de 9 columnas que usa script_barea.py.

Los pedidos ya existentes en el Excel no se duplican (dedup por id).
Script puntual: no se integra en el ciclo automático semanal.
"""

import os
import sys
import time
from datetime import datetime
from pathlib import Path

# ── Cargar .env ────────────────────────────────────────────────────────────────
_SCRIPT_DIR = Path(__file__).parent
_ENV_PATH = _SCRIPT_DIR / ".env"
if _ENV_PATH.exists():
    try:
        from dotenv import load_dotenv
        load_dotenv(_ENV_PATH)
    except ImportError:
        with open(_ENV_PATH, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

try:
    import pandas as pd
    from woocommerce import API as WC_API
    import openpyxl
except ImportError as e:
    print(f"[ERROR] Dependencia no instalada: {e}")
    sys.exit(1)

# ── Configuración ──────────────────────────────────────────────────────────────
DESDE = "2025-01-01T00:00:00.000Z"
HASTA = "2026-03-15T23:59:59.999Z"
TODOS_ESTADOS = True   # True = todos; False = solo completed/processing

PATH_VENTAS = os.getenv("PATH_VENTAS")
if not PATH_VENTAS or not os.path.exists(PATH_VENTAS):
    print(f"[ERROR] PATH_VENTAS no encontrado o no existe: {PATH_VENTAS!r}")
    print("  Comprueba el .env en ventas_semana/")
    sys.exit(1)


def _get_wc():
    url = os.getenv("WC_URL")
    key = os.getenv("WC_KEY")
    secret = os.getenv("WC_SECRET")
    if not url or not key or not secret:
        print("[ERROR] Faltan WC_URL, WC_KEY o WC_SECRET en el .env")
        sys.exit(1)
    return WC_API(url=url, consumer_key=key, consumer_secret=secret,
                  version="wc/v3", timeout=60)


def _normalizar_pedidos_wc(orders):
    """Mismo formato que script_barea.py: 7 columnas, 1 fila por pedido."""
    import re as _re

    def _limpiar_nombre_item(text):
        if not text:
            return ''
        text = _re.sub(r'<[^>]+>', ' ', str(text))
        text = _re.sub(r'\s{2,}', ' ', text)
        return text.strip()

    filas = []
    for o in orders:
        line_items = o.get("line_items", [])
        partes = []
        total_uds = 0
        for item in line_items:
            qty = item.get("quantity", 1)
            name = _limpiar_nombre_item(item.get("name", ""))
            total_uds += qty
            partes.append(name)
        try:
            total_eur = f"{float(o.get('total', 0)):.2f}".replace(".", ",") + " €"
        except (ValueError, TypeError):
            total_eur = o.get("total", "")
        fecha_raw = o.get("date_created", "")[:10]
        try:
            from datetime import datetime as _dt
            fecha_fmt = _dt.strptime(fecha_raw, "%Y-%m-%d").strftime("%d-%m-%y")
        except ValueError:
            fecha_fmt = fecha_raw
        filas.append({
            "id":            o.get("id"),
            "fecha":         fecha_fmt,
            "estado":        o.get("status"),
            "estado_pago":   o.get("payment_method_title"),
            "total":         total_eur,
            "items_resumen": ", ".join(partes) if partes else "",
            "num_items":     total_uds,
        })
    return pd.DataFrame(filas)


def _descargar_todos(wc):
    """Descarga todos los pedidos en el rango con paginación."""
    params = {
        "per_page": 100,
        "after": DESDE,
        "before": HASTA,
    }
    all_orders = []
    page = 1

    while True:
        params["page"] = page
        print(f"  Descargando página {page}...", end=" ", flush=True)
        try:
            resp = wc.get("orders", params=params)
            orders = resp.json()
        except Exception as e:
            print(f"\n[ERROR] Fallo en página {page}: {e}")
            break

        if not isinstance(orders, list):
            print(f"\n[ERROR] Respuesta inesperada: {orders}")
            break

        print(f"{len(orders)} pedidos")
        if not orders:
            break

        all_orders.extend(orders)
        page += 1

        if len(orders) < 100:
            break

        time.sleep(0.3)  # pausa para no saturar la API

    return all_orders


def _guardar_en_excel(df_nuevo):
    """Guarda en la pestaña WOOCOMMERCE, sin duplicar por id."""
    # Leer existentes (si los hay)
    existing_df = None
    try:
        existing_df = pd.read_excel(PATH_VENTAS, sheet_name="WOOCOMMERCE")
    except (ValueError, Exception):
        pass  # hoja vacía o no existe → se crea nueva

    if existing_df is not None and not existing_df.empty and "id" in existing_df.columns:
        df_nuevo["id"] = df_nuevo["id"].astype(str)
        existing_df["id"] = existing_df["id"].astype(str)
        antes = len(df_nuevo)
        df_nuevo = df_nuevo[~df_nuevo["id"].isin(existing_df["id"])]
        print(f"  Ya existían: {antes - len(df_nuevo)} pedidos (se omiten duplicados)")
        combined = pd.concat([existing_df, df_nuevo], ignore_index=True)
    else:
        combined = df_nuevo

    # Ordenar por fecha descendente
    if "fecha" in combined.columns:
        combined = combined.sort_values("fecha", ascending=False)

    # Escribir en Excel
    with pd.ExcelWriter(PATH_VENTAS, engine="openpyxl", mode="a",
                        if_sheet_exists="replace") as writer:
        combined.to_excel(writer, sheet_name="WOOCOMMERCE", index=False)

    return len(df_nuevo), len(combined)


def main():
    print("=" * 55)
    print("  CARGA HISTÓRICA WooCommerce")
    print(f"  Desde: 01/01/2025  →  Hasta: 15/03/2026")
    print("=" * 55)

    print("\n  Conectando con WooCommerce...")
    wc = _get_wc()

    print(f"\n  Descargando pedidos (todos los estados)...")
    all_orders = _descargar_todos(wc)

    if not all_orders:
        print("\n  No se encontraron pedidos en ese rango. Fin.")
        return

    print(f"\n  Total descargados: {len(all_orders)} pedidos")

    df = _normalizar_pedidos_wc(all_orders)

    # Estadísticas rápidas
    if "estado" in df.columns:
        print("\n  Distribución por estado:")
        for estado, n in df["estado"].value_counts().items():
            print(f"    {estado}: {n}")

    print(f"\n  Guardando en Excel: {PATH_VENTAS}")
    nuevos, total = _guardar_en_excel(df)

    print(f"\n  ✓ Listo.")
    print(f"    Pedidos nuevos guardados : {nuevos}")
    print(f"    Total en pestaña WOOCOMMERCE : {total}")
    print(f"\n  Cierra y vuelve a abrir el Excel para ver los cambios.")


if __name__ == "__main__":
    main()
