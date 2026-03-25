"""
Generador de Dashboards Barea (Comestibles + Tasca).

Lee datos de ventas (Loyverse + WooCommerce) desde los Excel,
calcula las estructuras de datos, genera dashboards HTML interactivos,
PDF de resumen mensual, y envia todo por email.

Uso:
    python ventas_semana/generar_dashboard.py                    # genera y abre
    python ventas_semana/generar_dashboard.py --no-open          # genera sin abrir
    python ventas_semana/generar_dashboard.py --solo-cerrados    # excluye mes en curso
    python ventas_semana/generar_dashboard.py --email --no-open  # genera y envia email
"""

import base64
import json
import os
import re
import ast
import shutil
import subprocess
import sys
import tempfile
import webbrowser
from collections import defaultdict
from datetime import datetime
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email import encoders

import numpy as np
import pandas as pd

# ── Rutas ─────────────────────────────────────────────────────────────────────
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_SCRIPT_DIR)

# Asegurar que config/ es importable desde cualquier directorio de ejecución
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

PATH_VENTAS = os.path.join(_ROOT, "datos", "Ventas Barea 2026.xlsx")
PATH_HISTORICO = os.path.join(_ROOT, "datos", "Ventas Barea Historico.xlsx")

# Comestibles
PATH_TEMPLATE = os.path.join(_SCRIPT_DIR, "dashboards", "dashboard_comes_template.html")
PATH_OUTPUT = os.path.join(_SCRIPT_DIR, "dashboards", "dashboard_comes.html")

# Tasca
PATH_TASCA_TEMPLATE = os.path.join(_SCRIPT_DIR, "dashboards", "dashboard_tasca_template.html")
PATH_TASCA_OUTPUT = os.path.join(_SCRIPT_DIR, "dashboards", "dashboard_tasca.html")

# Logos
PATH_LOGO_TASCA = os.path.join(_SCRIPT_DIR, "LOGO Tasca.jpg")
PATH_LOGO_COMES = os.path.join(_SCRIPT_DIR, "LOGO Comestibles .jpg")

# Años a incluir
YEAR_LIST = ["2025", "2026"]
TASCA_YEAR_LIST = ["2023", "2024", "2025", "2026"]

# Colores por categoría Comestibles
CAT_COLORS = {
    "ACEITES Y VINAGRES": "#c8a060",
    "DESPENSA": "#e8734a",
    "BAZAR": "#9a8070",
    "BOCADILLOS": "#c89060",
    "BODEGA": "#7a5a9a",
    "CHACINAS": "#e87e7e",
    "CONSERVAS": "#4a90d9",
    "CUPÓN REGALO": "#d4a0d0",
    "DULCES": "#d470a0",
    "EXPERIENCIAS": "#70d0c8",
    "OTROS": "#8a8a8a",
    "QUESOS": "#e8c97a",
    "VINOS": "#9b4f8a",
}

# Mapeo de categorías Loyverse → categorías simplificadas
CAT_MAP = {
    "APERITIVOS": "DESPENSA",
    "SALAZONES": "DESPENSA",
    "SALSAS": "DESPENSA",
    "CACHARRERIA": "BAZAR",
    "BODEGA Y CERVEZAS": "BODEGA",
    "LICORES Y VERMÚS": "BODEGA",
    "CONSERVAS MAR": "CONSERVAS",
    "CONSERVAS MONTAÑA": "CONSERVAS",
    "CONSERVAS VEGETALES": "CONSERVAS",
    "OTROS COMESTIBLES": "OTROS",
}

def _remapear_categorias(df):
    """Aplica CAT_MAP a la columna Categoria del DataFrame."""
    if "Categoria" in df.columns:
        df["Categoria"] = df["Categoria"].replace(CAT_MAP)
    return df

MESES_FULL = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
              "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
MESES_CORTO = ["Ene", "Feb", "Mar", "Abr", "May", "Jun",
               "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]

# Meses con apertura parcial (no comparables) — 8 = Agosto
MESES_PARCIALES = [8]

# ── Configuracion email y Netlify ─────────────────────────────────────────────
try:
    from config.datos_sensibles import (EMAILS_FULL, EMAILS_COMES_ONLY,
                                        NETLIFY_TOKEN, NETLIFY_SITE_ID,
                                        NETLIFY_URL)
except ImportError:
    EMAILS_FULL = []
    EMAILS_COMES_ONLY = []
    NETLIFY_TOKEN = ""
    NETLIFY_SITE_ID = ""
    NETLIFY_URL = ""

# Alias para compatibilidad con código que usa GITHUB_PAGES_URL
GITHUB_PAGES_URL = NETLIFY_URL

_GMAIL_DIR = os.path.join(_ROOT, "gmail")
_GMAIL_CREDENTIALS = os.path.join(_GMAIL_DIR, "credentials.json")
_GMAIL_TOKEN = os.path.join(_GMAIL_DIR, "token.json")


# ── Utilidades ────────────────────────────────────────────────────────────────
class _NumpyEncoder(json.JSONEncoder):
    """Convierte tipos numpy a tipos nativos Python para JSON."""
    def default(self, obj):
        if isinstance(obj, (np.integer,)):
            return int(obj)
        if isinstance(obj, (np.floating,)):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return super().default(obj)


def _json_dumps(obj):
    """json.dumps con soporte para tipos numpy."""
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"), cls=_NumpyEncoder)


def _to_float(val):
    """Convierte a float, soportando formato español ('3,51') y NaN."""
    if pd.isna(val):
        return 0.0
    if isinstance(val, (int, float)):
        return float(val)
    s = str(val).strip()
    if not s:
        return 0.0
    return float(s.replace(",", "."))


def _clean_html(text):
    """Elimina tags HTML de un string."""
    if not text or pd.isna(text):
        return ""
    return re.sub(r"<[^>]+>", "", str(text)).strip()


def _round(n, d=2):
    return round(n, d)


def _fmt_eur(n, decimals=2):
    """Formatea número como moneda española: x.xxx,xx €"""
    if decimals == 0:
        s = f"{abs(n):,.0f}"
    else:
        s = f"{abs(n):,.{decimals}f}"
    s = s.replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{'-' if n < 0 else ''}{s} €"


def _normalizar_df(df_i, df_r):
    """Normaliza columnas y convierte numerics en items y recibos."""
    df_i.rename(columns={
        "Numero de recibo": "Número de recibo",
        "Articulo": "Artículo",
    }, inplace=True)
    df_r.rename(columns={
        "Numero de recibo": "Número de recibo",
    }, inplace=True)

    for col in ["Cantidad", "Ventas brutas", "Descuentos", "Ventas netas",
                 "Costo de los bienes", "Beneficio bruto", "Impuestos"]:
        if col in df_i.columns:
            df_i[col] = df_i[col].apply(_to_float)
    for col in ["Ventas brutas", "Descuentos", "Ventas netas",
                 "Costo de los bienes", "Beneficio bruto"]:
        if col in df_r.columns:
            df_r[col] = df_r[col].apply(_to_float)

    return df_i, df_r


COMES_OTROS_UMBRAL = 1.0  # Categorías con <1% del total anual → "OTROS"


def _agrupar_otros(d_year, umbral=COMES_OTROS_UMBRAL):
    """Agrupa categorias con <umbral% del total anual en 'OTROS'."""
    cats_total = d_year["cats_total"]
    if not cats_total:
        return

    # Identificar categorias pequenas (excluir "OTROS" si ya existe)
    pequenas = {c for c, pct in cats_total.items()
                if pct < umbral and c != "OTROS"}
    if not pequenas:
        return

    # -- cats_total: sumar en OTROS
    otros_pct = sum(cats_total[c] for c in pequenas)
    cats_total["OTROS"] = _round(cats_total.get("OTROS", 0) + otros_pct, 1)
    for c in pequenas:
        del cats_total[c]

    # -- cats_euros: sumar en OTROS
    cats_euros = d_year["cats_euros"]
    otros_euros = sum(cats_euros.get(c, 0) for c in pequenas)
    cats_euros["OTROS"] = _round(cats_euros.get("OTROS", 0) + otros_euros)
    for c in pequenas:
        cats_euros.pop(c, None)

    # -- cats: recalcular lista ordenada
    d_year["cats"] = sorted(cats_total.keys())

    # -- mensual[m]["cats"]: agrupar en cada mes
    for m in range(1, 13):
        mc = d_year["mensual"][str(m)]["cats"]
        otros_m = sum(mc.get(c, 0) for c in pequenas)
        if otros_m > 0:
            mc["OTROS"] = _round(mc.get("OTROS", 0) + otros_m, 1)
        for c in pequenas:
            mc.pop(c, None)

    # -- pbm: fusionar productos de categorias pequenas bajo "OTROS"
    for m in range(1, 13):
        pm = d_year["pbm"][str(m)]
        otros_prods = []
        for c in pequenas:
            if c in pm:
                otros_prods.extend(pm.pop(c))
        if otros_prods:
            existing = pm.get("OTROS", [])
            existing.extend(otros_prods)
            existing.sort(key=lambda x: x["euros"], reverse=True)
            pm["OTROS"] = existing


# ══════════════════════════════════════════════════════════════════════════════
# COMESTIBLES
# ══════════════════════════════════════════════════════════════════════════════

def cargar_datos():
    """Lee los Excel y devuelve (items_por_año, recibos_por_año, df_woo)."""
    items = {}
    recibos = {}

    # ── Histórico: 2025 ──
    for year, sheet_items, sheet_recibos in [
        ("2025", "ComestiblesItems25", "ComestiblesRecibos25"),
    ]:
        try:
            df_i = pd.read_excel(PATH_HISTORICO, sheet_name=sheet_items)
            df_r = pd.read_excel(PATH_HISTORICO, sheet_name=sheet_recibos)
        except Exception as e:
            print(f"  Aviso: no se pudo leer {sheet_items}/{sheet_recibos}: {e}")
            continue

        df_i, df_r = _normalizar_df(df_i, df_r)
        df_i = _remapear_categorias(df_i)
        items[year] = df_i
        recibos[year] = df_r

    # ── Actual: 2026 ──
    try:
        df_i_26 = pd.read_excel(PATH_VENTAS, sheet_name="ComesItems")
        df_r_26 = pd.read_excel(PATH_VENTAS, sheet_name="ComesRecibos")
        df_i_26 = _remapear_categorias(df_i_26)
        items["2026"] = df_i_26
        recibos["2026"] = df_r_26
    except Exception as e:
        print(f"  Aviso: no se pudo leer ComesItems/ComesRecibos: {e}")

    # ── WooCommerce ──
    df_woo = None
    try:
        df_woo = pd.read_excel(PATH_VENTAS, sheet_name="WOOCOMMERCE")
    except Exception as e:
        print(f"  Aviso: no se pudo leer WOOCOMMERCE: {e}")

    return items, recibos, df_woo


def calcular_D(items_por_año, recibos_por_año, df_woo):
    """
    Genera la estructura D para Comestibles:
    D[year].mensual[month] = {euros, unidades, tickets, prom_ticket, cats:{cat: %}}
    D[year].pbm[month][cat] = [{art, euros, cant}]
    D[year].cats_total, cats_euros, cats, rotation
    D.woo[month] = {euros, pedidos, products}
    """
    D = {}

    for year in YEAR_LIST:
        df_items = items_por_año.get(year)
        df_recibos = recibos_por_año.get(year)

        mensual = {}
        pbm = {}

        for m in range(1, 13):
            mensual[str(m)] = {"euros": 0, "unidades": 0, "tickets": 0,
                               "prom_ticket": 0, "cats": {}}
            pbm[str(m)] = {}

        if df_items is not None and not df_items.empty:
            df = df_items.copy()
            df["Fecha"] = pd.to_datetime(df["Fecha"], errors="coerce")
            if "Estado" in df.columns:
                df = df[df["Estado"] != "Cancelado"]
            if "Tipo de recibo" in df.columns:
                df = df[df["Tipo de recibo"] == "Venta"]
            df["mes"] = df["Fecha"].dt.month

            for m in range(1, 13):
                dm = df[df["mes"] == m]
                if dm.empty:
                    continue

                euros = _round(dm["Ventas netas"].sum())
                unidades = _round(dm["Cantidad"].sum())

                if df_recibos is not None and not df_recibos.empty:
                    dr = df_recibos.copy()
                    dr["Fecha"] = pd.to_datetime(dr["Fecha"], errors="coerce")
                    if "Estado" in dr.columns:
                        dr = dr[dr["Estado"] != "Cancelado"]
                    if "Tipo de recibo" in dr.columns:
                        dr = dr[dr["Tipo de recibo"] == "Venta"]
                    dr_m = dr[dr["Fecha"].dt.month == m]
                    tickets = dr_m["Número de recibo"].nunique()
                else:
                    tickets = dm["Número de recibo"].nunique()

                prom_ticket = _round(euros / tickets) if tickets > 0 else 0

                cats_euros = dm.groupby("Categoria")["Ventas netas"].sum()
                total_cat = cats_euros.sum()
                cats_pct = {}
                if total_cat > 0:
                    for cat, val in cats_euros.items():
                        if pd.notna(cat) and str(cat).strip():
                            cats_pct[str(cat)] = _round(val / total_cat * 100, 1)

                mensual[str(m)] = {
                    "euros": euros,
                    "unidades": _round(unidades, 2),
                    "tickets": int(tickets),
                    "prom_ticket": _round(prom_ticket, 2),
                    "cats": cats_pct,
                }

                for cat, grp in dm.groupby("Categoria"):
                    if pd.isna(cat) or not str(cat).strip():
                        continue
                    cat = str(cat)
                    art_agg = grp.groupby("Artículo").agg(
                        euros=("Ventas netas", "sum"),
                        cant=("Cantidad", "sum"),
                    ).reset_index()
                    art_agg = art_agg.sort_values("euros", ascending=False)
                    pbm[str(m)][cat] = [
                        {"art": row["Artículo"], "euros": _round(row["euros"]),
                         "cant": _round(row["cant"], 2)}
                        for _, row in art_agg.iterrows()
                        if row["euros"] > 0
                    ]

        total_year = sum(mensual[str(m)]["euros"] for m in range(1, 13))
        cats_euros_year = defaultdict(float)
        for m in range(1, 13):
            cats = mensual[str(m)]["cats"]
            m_euros = mensual[str(m)]["euros"]
            for cat, pct in cats.items():
                cats_euros_year[cat] += pct / 100 * m_euros

        cats_total = {}
        if total_year > 0:
            for cat, val in cats_euros_year.items():
                cats_total[cat] = _round(val / total_year * 100, 1)

        cats_euros_dict = {cat: _round(val) for cat, val in cats_euros_year.items()}
        rotation = _calcular_rotation(df_items, year)

        D[year] = {
            "mensual": mensual,
            "pbm": pbm,
            "rotation": rotation,
            "cats_total": cats_total,
            "cats_euros": cats_euros_dict,
            "cats": sorted(cats_total.keys()),
        }

    # Agrupar categorias pequenas en "OTROS"
    for year in YEAR_LIST:
        if year in D:
            _agrupar_otros(D[year])

    D["woo"] = _calcular_woo(df_woo)
    return D


def _calcular_rotation(df_items, year):
    """Calcula rotación de productos para un año."""
    if df_items is None or df_items.empty:
        return []

    df = df_items.copy()
    df["Fecha"] = pd.to_datetime(df["Fecha"], errors="coerce")
    if "Estado" in df.columns:
        df = df[df["Estado"] != "Cancelado"]
    if "Tipo de recibo" in df.columns:
        df = df[df["Tipo de recibo"] == "Venta"]
    df["mes"] = df["Fecha"].dt.month

    avail_months = sorted(df["mes"].dropna().unique())
    n_avail = len(avail_months)
    if n_avail == 0:
        return []

    agg = df.groupby(["Artículo", "Categoria"]).agg(
        euros=("Ventas netas", "sum"),
        cant=("Cantidad", "sum"),
        meses=("mes", "nunique"),
    ).reset_index()

    agg = agg[agg["euros"] > 0]
    agg["avail"] = n_avail
    agg["rot"] = agg.apply(
        lambda r: _round(r["euros"] / r["meses"]) if r["meses"] > 0 else 0, axis=1
    )
    agg = agg.sort_values("rot", ascending=False)

    return [
        {
            "art": row["Artículo"],
            "cat": str(row["Categoria"]) if pd.notna(row["Categoria"]) else "",
            "euros": _round(row["euros"]),
            "cant": _round(row["cant"], 2),
            "meses": int(row["meses"]),
            "avail": int(row["avail"]),
            "rot": _round(row["rot"]),
        }
        for _, row in agg.iterrows()
    ]


def _calcular_woo(df_woo):
    """Calcula datos WooCommerce: woo[month] = {euros, pedidos, products}."""
    woo = {}
    for m in range(1, 13):
        woo[str(m)] = {"euros": 0, "pedidos": 0, "products": {}}

    if df_woo is None or df_woo.empty:
        return woo

    df = df_woo.copy()

    # Compatibilidad: columna puede ser "status" (API) o "estado" (Excel limpio)
    col_status = "status" if "status" in df.columns else "estado"
    if col_status in df.columns:
        estados_validos = {"completed", "processing", "on-hold", "Completado", "En proceso"}
        df = df[df[col_status].isin(estados_validos)]

    # Compatibilidad: columna puede ser "date_created" (API) o "fecha" (Excel limpio)
    col_fecha = "date_created" if "date_created" in df.columns else "fecha"
    df["_fecha"] = pd.to_datetime(df[col_fecha], format="mixed", dayfirst=True, errors="coerce")
    df = df[df["_fecha"].dt.year == int(YEAR_LIST[-1])]
    df["mes"] = df["_fecha"].dt.month

    # Compatibilidad: total puede ser float (API) o string con coma (Excel limpio)
    if df["total"].dtype == object:
        df["_total"] = pd.to_numeric(
            df["total"].astype(str).str.replace("€", "").str.replace(" ", "").str.replace(",", "."),
            errors="coerce"
        ).fillna(0)
    else:
        df["_total"] = df["total"].fillna(0)

    for m in range(1, 13):
        dm = df[df["mes"] == m]
        if dm.empty:
            continue

        euros = _round(float(dm["_total"].sum()))
        pedidos = len(dm)

        products = defaultdict(float)
        # Formato API: line_items con lista de dicts
        if "line_items" in dm.columns:
            for _, row in dm.iterrows():
                line_items_raw = row.get("line_items", "")
                if not line_items_raw or pd.isna(line_items_raw):
                    continue
                try:
                    if isinstance(line_items_raw, str):
                        items_list = ast.literal_eval(line_items_raw)
                    else:
                        items_list = line_items_raw
                    if isinstance(items_list, list):
                        for item in items_list:
                            name = _clean_html(item.get("name", ""))
                            total_item = float(item.get("total", 0) or 0)
                            if name and total_item > 0:
                                products[name] += total_item
                except (ValueError, SyntaxError):
                    pass
        # Formato Excel limpio: items_resumen con texto descriptivo
        elif "items_resumen" in dm.columns:
            for _, row in dm.iterrows():
                resumen = str(row.get("items_resumen", ""))
                if resumen and resumen != "nan":
                    # Usar el resumen como nombre de producto, asignar el total del pedido
                    nombre = resumen[:80].strip()
                    if nombre:
                        products[nombre] += float(row.get("_total", 0))

        woo[str(m)] = {
            "euros": euros,
            "pedidos": pedidos,
            "products": {k: _round(v) for k, v in products.items()},
        }

    return woo


def calcular_MD(items_por_año):
    """Genera la estructura MD para Comestibles (margenes)."""
    MD = {}

    for year in YEAR_LIST:
        df_items = items_por_año.get(year)
        MD[year] = {}

        for m in range(1, 13):
            MD[year][str(m)] = {"cats": {}, "products": []}

        if df_items is None or df_items.empty:
            continue

        df = df_items.copy()
        df["Fecha"] = pd.to_datetime(df["Fecha"], errors="coerce")
        if "Estado" in df.columns:
            df = df[df["Estado"] != "Cancelado"]
        if "Tipo de recibo" in df.columns:
            df = df[df["Tipo de recibo"] == "Venta"]
        df["mes"] = df["Fecha"].dt.month

        for col in ["Ventas netas", "Costo de los bienes", "Descuentos", "Cantidad"]:
            if col in df.columns:
                df[col] = df[col].apply(_to_float)

        for m in range(1, 13):
            dm = df[df["mes"] == m]
            if dm.empty:
                continue

            cats = {}
            for cat, grp in dm.groupby("Categoria"):
                if pd.isna(cat) or not str(cat).strip():
                    continue
                cat = str(cat)
                euros = _round(grp["Ventas netas"].sum())
                coste = _round(grp["Costo de los bienes"].sum())
                desc = _round(grp["Descuentos"].sum()) if "Descuentos" in grp.columns else 0
                margen = _round(euros - coste)
                margen_pct = _round(margen / euros * 100, 1) if euros > 0 else 0
                cats[cat] = {
                    "euros": euros, "coste": coste, "margen": margen,
                    "margen_pct": margen_pct, "desc": desc,
                }

            products = []
            for art, grp in dm.groupby("Artículo"):
                if pd.isna(art) or not str(art).strip():
                    continue
                cat = str(grp["Categoria"].iloc[0]) if pd.notna(grp["Categoria"].iloc[0]) else ""
                euros = _round(grp["Ventas netas"].sum())
                coste = _round(grp["Costo de los bienes"].sum())
                desc = _round(grp["Descuentos"].sum()) if "Descuentos" in grp.columns else 0
                cant = _round(grp["Cantidad"].sum(), 2)
                margen = _round(euros - coste)
                margen_pct = _round(margen / euros * 100, 1) if euros > 0 else 0
                products.append({
                    "art": str(art), "cat": cat, "euros": euros, "coste": coste,
                    "margen": margen, "margen_pct": margen_pct, "desc": desc,
                    "cant": cant,
                })

            products.sort(key=lambda x: x["euros"], reverse=True)
            MD[year][str(m)] = {"cats": cats, "products": products}

    return MD


def calcular_DIAS(items_por_año, recibos_por_año):
    """
    Genera estructura DIAS para análisis por día de la semana.
    DIAS[year][dia_idx] = {euros, tickets, ticket_medio}  (0=Lunes..6=Domingo)
    DIAS[year]["heatmap"][dia_idx][mes] = euros
    DIAS["dias_nombres"] = ["Lunes", ..., "Domingo"]
    """
    DIAS = {}
    dias_nombres = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes",
                    "Sábado", "Domingo"]
    DIAS["dias_nombres"] = dias_nombres

    for year in YEAR_LIST:
        df_items = items_por_año.get(year)
        df_recibos = recibos_por_año.get(year)

        year_data = {}
        heatmap = {}
        for d in range(7):
            year_data[str(d)] = {"euros": 0, "tickets": 0, "ticket_medio": 0}
            heatmap[str(d)] = {}
            for m in range(1, 13):
                heatmap[str(d)][str(m)] = 0

        if df_items is not None and not df_items.empty:
            df = df_items.copy()
            df["Fecha"] = pd.to_datetime(df["Fecha"], errors="coerce")
            if "Estado" in df.columns:
                df = df[df["Estado"] != "Cancelado"]
            if "Tipo de recibo" in df.columns:
                df = df[df["Tipo de recibo"] == "Venta"]
            df["dia"] = df["Fecha"].dt.dayofweek
            df["mes"] = df["Fecha"].dt.month

            # Totales por día de la semana
            for d in range(7):
                dd = df[df["dia"] == d]
                if dd.empty:
                    continue
                euros = _round(dd["Ventas netas"].sum())

                # Tickets desde recibos
                if df_recibos is not None and not df_recibos.empty:
                    dr = df_recibos.copy()
                    dr["Fecha"] = pd.to_datetime(dr["Fecha"], errors="coerce")
                    if "Estado" in dr.columns:
                        dr = dr[dr["Estado"] != "Cancelado"]
                    if "Tipo de recibo" in dr.columns:
                        dr = dr[dr["Tipo de recibo"] == "Venta"]
                    dr["dia"] = dr["Fecha"].dt.dayofweek
                    dr_d = dr[dr["dia"] == d]
                    tickets = int(dr_d["Número de recibo"].nunique())
                else:
                    tickets = int(dd["Número de recibo"].nunique())

                ticket_medio = _round(euros / tickets) if tickets > 0 else 0
                year_data[str(d)] = {
                    "euros": euros,
                    "tickets": tickets,
                    "ticket_medio": ticket_medio,
                }

            # Heatmap: día × mes
            for d in range(7):
                for m in range(1, 13):
                    dm = df[(df["dia"] == d) & (df["mes"] == m)]
                    if not dm.empty:
                        heatmap[str(d)][str(m)] = _round(dm["Ventas netas"].sum())

        year_data["heatmap"] = heatmap
        DIAS[year] = year_data

    return DIAS


def generar_html(D, MD, DIAS=None):
    """Lee el template Comestibles y sustituye los placeholders."""
    with open(PATH_TEMPLATE, "r", encoding="utf-8") as f:
        template = f.read()

    years_with_data = [y for y in YEAR_LIST if any(
        D[y]["mensual"][str(m)]["tickets"] > 0 for m in range(1, 13)
    )]

    first_year = years_with_data[0] if years_with_data else YEAR_LIST[0]
    last_year = years_with_data[-1] if years_with_data else YEAR_LIST[-1]
    subtitle = f"{first_year}\u2013{last_year}"
    fecha_act = datetime.now().strftime("%d/%m/%Y")

    md_json = _json_dumps(MD)
    d_json = _json_dumps(D)
    years_json = _json_dumps(years_with_data)

    all_cats = set()
    for year in YEAR_LIST:
        all_cats.update(D[year].get("cats", []))
    cat_colors_filtered = {k: v for k, v in CAT_COLORS.items() if k in all_cats}
    _extra_colors = [
        "#7a9a6a", "#9a6a7a", "#6a7a9a", "#b0906a", "#6ab09a",
        "#9a6ab0", "#b06a6a", "#6a9ab0", "#b0b06a", "#6ab0b0",
    ]
    idx = 0
    for cat in sorted(all_cats):
        if cat not in cat_colors_filtered:
            cat_colors_filtered[cat] = _extra_colors[idx % len(_extra_colors)]
            idx += 1

    cc_json = _json_dumps(cat_colors_filtered)

    dias_json = _json_dumps(DIAS) if DIAS else "{}"

    html = template
    html = html.replace("{{MD_DATA}}", md_json)
    html = html.replace("{{D_DATA}}", d_json)
    html = html.replace("{{DIAS_DATA}}", dias_json)
    html = html.replace("{{YEARS_DATA}}", years_json)
    html = html.replace("{{CAT_COLORS_DATA}}", cc_json)
    html = html.replace("{{SUBTITLE_YEARS}}", subtitle)
    html = html.replace("{{FECHA_ACT}}", fecha_act)

    with open(PATH_OUTPUT, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"  Dashboard Comestibles: {PATH_OUTPUT}")
    return PATH_OUTPUT


def _filtrar_meses_cerrados(items, recibos, df_woo):
    """Excluye datos del mes en curso del ano actual (Comestibles)."""
    mes_actual = datetime.now().month
    year_actual = YEAR_LIST[-1]

    if year_actual in items and items[year_actual] is not None:
        df = items[year_actual]
        df["Fecha"] = pd.to_datetime(df["Fecha"], errors="coerce")
        items[year_actual] = df[df["Fecha"].dt.month < mes_actual]
        print(f"  Filtro meses cerrados Comes: {year_actual} hasta mes {mes_actual - 1} "
              f"({len(items[year_actual]):,} items)")

    if year_actual in recibos and recibos[year_actual] is not None:
        df = recibos[year_actual]
        df["Fecha"] = pd.to_datetime(df["Fecha"], errors="coerce")
        recibos[year_actual] = df[df["Fecha"].dt.month < mes_actual]

    if df_woo is not None and not df_woo.empty:
        df_woo = df_woo.copy()
        df_woo["_fecha"] = pd.to_datetime(df_woo["date_created"], errors="coerce")
        mask = ~((df_woo["_fecha"].dt.year == int(year_actual)) &
                 (df_woo["_fecha"].dt.month >= mes_actual))
        df_woo = df_woo[mask].drop(columns=["_fecha"])

    return items, recibos, df_woo


# ══════════════════════════════════════════════════════════════════════════════
# TASCA
# ══════════════════════════════════════════════════════════════════════════════

def cargar_datos_tasca():
    """Lee los Excel de Tasca y devuelve (items_por_año, recibos_por_año)."""
    items = {}
    recibos = {}

    # ── Histórico: 2023, 2024, 2025 ──
    for year, sheet_items, sheet_recibos in [
        ("2023", "TascaItems23", "TascaRecibos23"),
        ("2024", "TascaItems24", "TascaRecibos24"),
        ("2025", "TascaItems25", "TascaRecibos25"),
    ]:
        try:
            df_i = pd.read_excel(PATH_HISTORICO, sheet_name=sheet_items)
            df_r = pd.read_excel(PATH_HISTORICO, sheet_name=sheet_recibos)
        except Exception as e:
            print(f"  Aviso: no se pudo leer {sheet_items}/{sheet_recibos}: {e}")
            continue

        df_i, df_r = _normalizar_df(df_i, df_r)
        items[year] = df_i
        recibos[year] = df_r

    # ── Actual: 2026 ──
    try:
        df_i_26 = pd.read_excel(PATH_VENTAS, sheet_name="TascaItems")
        df_r_26 = pd.read_excel(PATH_VENTAS, sheet_name="TascaRecibos")
        items["2026"] = df_i_26
        recibos["2026"] = df_r_26
    except Exception as e:
        print(f"  Aviso: no se pudo leer TascaItems/TascaRecibos: {e}")

    return items, recibos


def calcular_RAW(items_por_año, recibos_por_año):
    """
    Genera la estructura RAW para Tasca:
    RAW[year].mensual[month] = {euros, unidades, tickets, prom_ticket}
    RAW[year].categorias_mes[month] = {cat: pct}
    RAW[year].cats_total, cats_euros, cats
    """
    RAW = {}

    for year in TASCA_YEAR_LIST:
        df_items = items_por_año.get(year)
        df_recibos = recibos_por_año.get(year)

        mensual = {}
        categorias_mes = {}

        for m in range(1, 13):
            mensual[str(m)] = {"euros": 0, "unidades": 0, "tickets": 0, "prom_ticket": 0}
            categorias_mes[str(m)] = {}

        if df_items is not None and not df_items.empty:
            df = df_items.copy()
            df["Fecha"] = pd.to_datetime(df["Fecha"], errors="coerce")
            if "Estado" in df.columns:
                df = df[df["Estado"] != "Cancelado"]
            if "Tipo de recibo" in df.columns:
                df = df[df["Tipo de recibo"] == "Venta"]
            df["mes"] = df["Fecha"].dt.month

            for m in range(1, 13):
                dm = df[df["mes"] == m]
                if dm.empty:
                    continue

                euros = _round(dm["Ventas netas"].sum())
                unidades = _round(dm["Cantidad"].sum())

                if df_recibos is not None and not df_recibos.empty:
                    dr = df_recibos.copy()
                    dr["Fecha"] = pd.to_datetime(dr["Fecha"], errors="coerce")
                    if "Estado" in dr.columns:
                        dr = dr[dr["Estado"] != "Cancelado"]
                    if "Tipo de recibo" in dr.columns:
                        dr = dr[dr["Tipo de recibo"] == "Venta"]
                    dr_m = dr[dr["Fecha"].dt.month == m]
                    tickets = dr_m["Número de recibo"].nunique()
                else:
                    tickets = dm["Número de recibo"].nunique()

                prom_ticket = _round(euros / tickets) if tickets > 0 else 0

                mensual[str(m)] = {
                    "euros": euros,
                    "unidades": _round(unidades, 2),
                    "tickets": int(tickets),
                    "prom_ticket": _round(prom_ticket, 2),
                }

                # Categorias: % de ventas por mes (para chart evolucion categorias)
                cats_euros = dm.groupby("Categoria")["Ventas netas"].sum()
                total_cat = cats_euros.sum()
                if total_cat > 0:
                    for cat, val in cats_euros.items():
                        if pd.notna(cat) and str(cat).strip():
                            categorias_mes[str(m)][str(cat)] = _round(val / total_cat * 100, 1)

        # cats_total y cats_euros para el año
        total_year = sum(mensual[str(m)]["euros"] for m in range(1, 13))
        cats_euros_year = defaultdict(float)
        for m in range(1, 13):
            cm = categorias_mes[str(m)]
            m_euros = mensual[str(m)]["euros"]
            for cat, pct in cm.items():
                cats_euros_year[cat] += pct / 100 * m_euros

        cats_total = {}
        if total_year > 0:
            for cat, val in cats_euros_year.items():
                cats_total[cat] = _round(val / total_year * 100, 1)

        cats_euros_dict = {cat: _round(val) for cat, val in cats_euros_year.items()}

        RAW[year] = {
            "mensual": mensual,
            "categorias_mes": categorias_mes,
            "cats_total": cats_total,
            "cats_euros": cats_euros_dict,
            "cats": sorted(cats_total.keys()),
        }

    return RAW


def calcular_PBM_tasca(items_por_año):
    """Genera PBM[year][month][cat] = [{art, euros, cant}] para Tasca."""
    PBM = {}

    for year in TASCA_YEAR_LIST:
        df_items = items_por_año.get(year)
        PBM[year] = {}

        for m in range(1, 13):
            PBM[year][str(m)] = {}

        if df_items is None or df_items.empty:
            continue

        df = df_items.copy()
        df["Fecha"] = pd.to_datetime(df["Fecha"], errors="coerce")
        if "Estado" in df.columns:
            df = df[df["Estado"] != "Cancelado"]
        if "Tipo de recibo" in df.columns:
            df = df[df["Tipo de recibo"] == "Venta"]
        df["mes"] = df["Fecha"].dt.month

        for m in range(1, 13):
            dm = df[df["mes"] == m]
            if dm.empty:
                continue

            for cat, grp in dm.groupby("Categoria"):
                if pd.isna(cat) or not str(cat).strip():
                    continue
                cat = str(cat)
                art_agg = grp.groupby("Artículo").agg(
                    euros=("Ventas netas", "sum"),
                    cant=("Cantidad", "sum"),
                ).reset_index()
                art_agg = art_agg.sort_values("euros", ascending=False)
                PBM[year][str(m)][cat] = [
                    {"art": row["Artículo"], "euros": _round(row["euros"]),
                     "cant": _round(row["cant"], 2)}
                    for _, row in art_agg.iterrows()
                    if row["euros"] > 0
                ]

    return PBM


def generar_html_tasca(RAW, PBM):
    """Lee el template Tasca y sustituye los placeholders."""
    with open(PATH_TASCA_TEMPLATE, "r", encoding="utf-8") as f:
        template = f.read()

    years_with_data = [y for y in TASCA_YEAR_LIST if any(
        RAW[y]["mensual"][str(m)]["tickets"] > 0 for m in range(1, 13)
    )]

    first_year = years_with_data[0] if years_with_data else TASCA_YEAR_LIST[0]
    last_year = years_with_data[-1] if years_with_data else TASCA_YEAR_LIST[-1]
    subtitle = f"{first_year}\u2013{last_year}"
    fecha_act = datetime.now().strftime("%d/%m/%Y")

    raw_json = _json_dumps(RAW)
    pbm_json = _json_dumps(PBM)
    years_json = _json_dumps(years_with_data)

    html = template
    html = html.replace("{{RAW_DATA}}", raw_json)
    html = html.replace("{{PBM_DATA}}", pbm_json)
    html = html.replace("{{YEARS_DATA}}", years_json)
    html = html.replace("{{SUBTITLE_YEARS}}", subtitle)
    html = html.replace("{{FECHA_ACT}}", fecha_act)

    with open(PATH_TASCA_OUTPUT, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"  Dashboard Tasca: {PATH_TASCA_OUTPUT}")
    return PATH_TASCA_OUTPUT


def _filtrar_meses_cerrados_tasca(items, recibos):
    """Excluye datos del mes en curso del ano actual (Tasca)."""
    mes_actual = datetime.now().month
    year_actual = TASCA_YEAR_LIST[-1]

    if year_actual in items and items[year_actual] is not None:
        df = items[year_actual]
        df["Fecha"] = pd.to_datetime(df["Fecha"], errors="coerce")
        items[year_actual] = df[df["Fecha"].dt.month < mes_actual]
        print(f"  Filtro meses cerrados Tasca: {year_actual} hasta mes {mes_actual - 1} "
              f"({len(items[year_actual]):,} items)")

    if year_actual in recibos and recibos[year_actual] is not None:
        df = recibos[year_actual]
        df["Fecha"] = pd.to_datetime(df["Fecha"], errors="coerce")
        recibos[year_actual] = df[df["Fecha"].dt.month < mes_actual]

    return items, recibos


# ══════════════════════════════════════════════════════════════════════════════
# PDF RESUMEN MENSUAL
# ══════════════════════════════════════════════════════════════════════════════

def _setup_pdf_fonts():
    """Registra Calibri y devuelve (font_normal, font_bold)."""
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    paths = {
        "Calibri": "C:/Windows/Fonts/calibri.ttf",
        "CalibriBold": "C:/Windows/Fonts/calibrib.ttf",
    }
    for name, path in paths.items():
        if os.path.exists(path):
            try:
                pdfmetrics.registerFont(TTFont(name, path))
            except Exception:
                pass
    fn = "Calibri" if os.path.exists(paths["Calibri"]) else "Helvetica"
    fb = "CalibriBold" if os.path.exists(paths["CalibriBold"]) else "Helvetica-Bold"
    return fn, fb


def _generar_graficos_pdf(D, RAW, mes_cerrado, year_actual):
    """Genera 4 PNGs con graficos de linea mejorados."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.ticker import FuncFormatter

    tmp_dir = tempfile.mkdtemp(prefix="barea_pdf_")
    fmt_euros = FuncFormatter(lambda x, _: _fmt_eur(x, 0))

    plt.rcParams.update({
        'figure.facecolor': 'white',
        'axes.facecolor': '#F8F9FA',
        'axes.spines.top': False,
        'axes.spines.right': False,
        'grid.alpha': 0.25,
        'grid.color': '#CCCCCC',
        'font.size': 9,
    })

    tasca_colors = {"2023": "#B4D4E8", "2024": "#7BAFD4",
                    "2025": "#4A8DB8", "2026": "#1F4E79"}
    comes_colors = {"2025": "#82B878", "2026": "#375623"}

    def _plot_segments(ax, xs, vals, color, lw, alpha, zorder, label=None):
        """Dibuja línea por segmentos: sólida normal, discontinua en parciales."""
        labeled = False
        for i in range(1, len(xs)):
            parcial = (xs[i] in MESES_PARCIALES or xs[i-1] in MESES_PARCIALES)
            kw = dict(color=color, linewidth=lw, zorder=zorder)
            if parcial:
                kw.update(linestyle='--', alpha=alpha * 0.4)
            else:
                kw['alpha'] = alpha
            if not labeled and label:
                kw['label'] = label
                labeled = True
            ax.plot([xs[i-1], xs[i]], [vals[i-1], vals[i]], **kw)
        if not labeled and label:
            ax.plot([], [], color=color, linewidth=lw, alpha=alpha, label=label)

    def _plot_markers(ax, xs, vals, color, ms, alpha, zorder):
        """Dibuja marcadores: pequeños y transparentes en meses parciales."""
        for x, v in zip(xs, vals):
            parcial = x in MESES_PARCIALES
            ax.plot(x, v, 'o', color=color,
                    markersize=3 if parcial else ms,
                    alpha=0.3 if parcial else alpha,
                    zorder=zorder + 1)

    def _plot_annotations(ax, xs, vals, color):
        """Anotaciones de valor + 'parcial' en meses parciales."""
        for x, v in zip(xs, vals):
            parcial = x in MESES_PARCIALES
            txt = _fmt_eur(v, 0) + ('*' if parcial else '')
            ax.annotate(txt, (x, v),
                        textcoords="offset points", xytext=(0, 10),
                        ha="center", fontsize=7, color=color,
                        fontweight="bold")
            if parcial:
                ax.annotate('parcial', (x, v),
                            textcoords="offset points", xytext=(0, -12),
                            ha="center", fontsize=6, color="#999",
                            fontstyle="italic")

    def _ax_base(ax, title, fmt):
        ax.set_title(title, fontsize=12, fontweight="bold", pad=12,
                     color="#1a1a1a")
        ax.set_xticks(range(1, 13))
        ax.set_xticklabels(MESES_CORTO, fontsize=8)
        ax.yaxis.set_major_formatter(fmt)
        ax.tick_params(axis="y", labelsize=8)
        ax.legend(fontsize=8, loc="upper right", framealpha=0.9,
                  edgecolor="#DDD")
        ax.set_xlim(0.5, 12.5)
        ax.grid(True, axis="y", alpha=0.25)
        for spine in ("bottom", "left"):
            ax.spines[spine].set_color("#CCCCCC")

    def _plot_modern(ax, data_dict, year_list, yr_colors, title, current_yr):
        for yr in year_list:
            if yr not in data_dict:
                continue
            mensual = data_dict[yr]["mensual"]
            xs, vals = [], []
            for m in range(1, 13):
                e = mensual.get(str(m), {}).get("euros", 0)
                if e and e > 0:
                    xs.append(m)
                    vals.append(e)
            if not vals:
                continue
            color = yr_colors.get(yr, "#999")
            is_cur = (yr == current_yr)
            lw = 2.5 if is_cur else 1.5
            ms = 6 if is_cur else 3
            a = 1.0 if is_cur else 0.45
            z = 3 if is_cur else 2

            _plot_segments(ax, xs, vals, color, lw, a, z, label=yr)
            _plot_markers(ax, xs, vals, color, ms, a, z)
            if is_cur:
                ax.fill_between(xs, vals, alpha=0.07, color=color)
                _plot_annotations(ax, xs, vals, color)
        _ax_base(ax, title, fmt_euros)

    # Grafico 1: Tasca
    fig1, ax1 = plt.subplots(figsize=(9, 3.8))
    _plot_modern(ax1, RAW, TASCA_YEAR_LIST, tasca_colors,
                 "Tasca Barea — Facturación mensual", year_actual)
    fig1.tight_layout(pad=1.5)
    path1 = os.path.join(tmp_dir, "chart_tasca.png")
    fig1.savefig(path1, dpi=180, bbox_inches="tight")
    plt.close(fig1)

    # Grafico 2: Comestibles
    fig2, ax2 = plt.subplots(figsize=(9, 3.8))
    _plot_modern(ax2, D, YEAR_LIST, comes_colors,
                 "Comestibles Barea — Facturación mensual", year_actual)
    fig2.tight_layout(pad=1.5)
    path2 = os.path.join(tmp_dir, "chart_comes.png")
    fig2.savefig(path2, dpi=180, bbox_inches="tight")
    plt.close(fig2)

    # Grafico 3: Comparativa
    fig3, ax3 = plt.subplots(figsize=(9, 3.8))
    yr = year_actual
    for lbl, data, color, mkr, off_y in [
        (f"Tasca {yr}", RAW, "#1F4E79", "o", 10),
        (f"Comestibles {yr}", D, "#375623", "s", -14),
    ]:
        mensual = data.get(yr, {}).get("mensual", {})
        xs, vs = [], []
        for m in range(1, 13):
            e = mensual.get(str(m), {}).get("euros", 0)
            if e and e > 0:
                xs.append(m)
                vs.append(e)
        if vs:
            _plot_segments(ax3, xs, vs, color, 2.5, 1.0, 3, label=lbl)
            _plot_markers(ax3, xs, vs, color, 6, 1.0, 3)
            ax3.fill_between(xs, vs, alpha=0.07, color=color)
            for x, v in zip(xs, vs):
                parcial = x in MESES_PARCIALES
                txt = _fmt_eur(v, 0) + ('*' if parcial else '')
                ax3.annotate(txt, (x, v),
                             textcoords="offset points", xytext=(0, off_y),
                             ha="center", fontsize=7, color=color,
                             fontweight="bold")
    _ax_base(ax3, f"Comparativa Tasca vs Comestibles — {yr}", fmt_euros)
    fig3.tight_layout(pad=1.5)
    path3 = os.path.join(tmp_dir, "chart_conjunto.png")
    fig3.savefig(path3, dpi=180, bbox_inches="tight")
    plt.close(fig3)

    # Grafico 4: Evolución conjunta continua (Tasca+Comes)
    # Excluir meses parciales (agosto) — conectar Jul→Sep con discontinua
    timeline_raw = []
    for y in sorted(set(YEAR_LIST) | set(TASCA_YEAR_LIST)):
        for m in range(1, 13):
            t_e = (RAW.get(y, {}).get("mensual", {})
                   .get(str(m), {}).get("euros", 0) or 0)
            c_e = (D.get(y, {}).get("mensual", {})
                   .get(str(m), {}).get("euros", 0) or 0)
            total = t_e + c_e
            if total > 0:
                timeline_raw.append((y, m, total))

    # Separar puntos normales y parciales (para trazar saltos)
    timeline = [(y, m, v) for y, m, v in timeline_raw
                if m not in MESES_PARCIALES]
    parciales_set = {(y, m) for y, m, _ in timeline_raw
                     if m in MESES_PARCIALES}

    fig4, ax4 = plt.subplots(figsize=(9, 3.5))
    if timeline:
        xs4 = list(range(len(timeline)))
        vals4 = [t[2] for t in timeline]
        months4 = [t[1] for t in timeline]
        years4 = [t[0] for t in timeline]

        color4 = "#CC0000"

        # Detectar saltos por mes parcial entre puntos consecutivos
        def _hay_parcial_entre(i):
            """True si entre punto i-1 e i se saltó un mes parcial."""
            y0, m0 = years4[i-1], months4[i-1]
            y1, m1 = years4[i], months4[i]
            # Comprobar si algún mes intermedio era parcial
            ym0 = int(y0) * 12 + m0
            ym1 = int(y1) * 12 + m1
            for ym in range(ym0 + 1, ym1):
                yy, mm = divmod(ym - 1, 12)
                mm += 1
                if (str(yy), mm) in parciales_set:
                    return True
            return False

        # Segmentos: sólido normal, discontinuo donde se saltó parcial
        for i in range(1, len(xs4)):
            salto = _hay_parcial_entre(i)
            kw = dict(color=color4, linewidth=2.5, zorder=3)
            if salto:
                kw.update(linestyle='--', alpha=0.3, linewidth=1.5)
            ax4.plot([xs4[i-1], xs4[i]], [vals4[i-1], vals4[i]], **kw)

        # Marcadores
        ax4.plot(xs4, vals4, 'o', color=color4, markersize=3.5,
                 zorder=4, alpha=0.85)

        # Media móvil 3 meses (línea de tendencia suave)
        if len(vals4) >= 3:
            ma = []
            for i in range(len(vals4)):
                if i < 2:
                    ma.append(None)
                else:
                    ma.append(sum(vals4[i-2:i+1]) / 3)
            xs_ma = [x for x, v in zip(xs4, ma) if v is not None]
            vs_ma = [v for v in ma if v is not None]
            ax4.plot(xs_ma, vs_ma, color=color4, linewidth=1.2,
                     alpha=0.25, zorder=2, linestyle='-')

        # Anotaciones: max, min, primero, último — con anti-solapamiento
        idx_max = max(range(len(vals4)), key=lambda i: vals4[i])
        idx_min = min(range(len(vals4)), key=lambda i: vals4[i])
        idx_first = 0
        idx_last = len(vals4) - 1
        anotar = {}
        for idx in [idx_first, idx_last, idx_min, idx_max]:
            anotar[idx] = vals4[idx]

        # Anti-solapamiento: si dos puntos están a ≤2 posiciones, alternar arriba/abajo
        anotar_sorted = sorted(anotar.keys())
        offsets = {}
        for j, idx in enumerate(anotar_sorted):
            arriba = True
            for prev_idx in anotar_sorted[:j]:
                if abs(idx - prev_idx) <= 2:
                    arriba = offsets.get(prev_idx, True) is False
            offsets[idx] = arriba

        for idx in anotar:
            v = vals4[idx]
            oy = 11 if offsets[idx] else -13
            ax4.annotate(_fmt_eur(v, 0), (xs4[idx], v),
                         textcoords="offset points",
                         xytext=(0, oy),
                         ha="center", fontsize=6.5, color="#333",
                         fontweight="bold")

        # Eje X: etiqueta cada trimestre (Ene, Abr, Jul, Oct)
        tick_pos = []
        tick_lbl = []
        for i, (y, m) in enumerate(zip(years4, months4)):
            if m in (1, 4, 7, 10):
                tick_pos.append(xs4[i])
                tick_lbl.append(f"{MESES_CORTO[m-1]} {y[2:]}")
        ax4.set_xticks(tick_pos)
        ax4.set_xticklabels(tick_lbl, fontsize=7.5, color="#555")

        # Bandas alternas de fondo por año (sutil)
        año_actual = None
        band_start = 0
        colores_band = ["#F8F8F8", "#FFFFFF"]
        band_idx = 0
        for i in range(len(years4)):
            if years4[i] != año_actual:
                if año_actual is not None:
                    ax4.axvspan(band_start - 0.5, xs4[i] - 0.5,
                                color=colores_band[band_idx % 2],
                                alpha=0.6, zorder=0)
                    band_idx += 1
                año_actual = years4[i]
                band_start = xs4[i]
        # Última banda
        ax4.axvspan(band_start - 0.5, xs4[-1] + 0.5,
                    color=colores_band[band_idx % 2],
                    alpha=0.6, zorder=0)

        # Eje Y: rango 15K–50K
        ax4.set_ylim(15000, 50000)
        ax4.yaxis.set_major_formatter(fmt_euros)
        ax4.yaxis.set_major_locator(plt.MultipleLocator(5000))
        ax4.tick_params(axis="y", labelsize=7.5, colors="#555")

    ax4.set_title("Evolución facturación total — Tasca + Comestibles",
                  fontsize=11, fontweight="bold", pad=10, color="#1a1a1a")
    ax4.grid(True, axis="y", alpha=0.2, linewidth=0.5)
    for spine in ax4.spines.values():
        spine.set_visible(False)
    ax4.tick_params(axis="both", length=0)
    fig4.tight_layout(pad=1.2)
    path4 = os.path.join(tmp_dir, "chart_total.png")
    fig4.savefig(path4, dpi=180, bbox_inches="tight")
    plt.close(fig4)

    plt.rcParams.update(plt.rcParamsDefault)
    return path1, path2, path3, path4, tmp_dir


def _calcular_dia_fuerte(items_por_año, year, mes):
    """Devuelve (dia_nombre, media_diaria) del dia con mas ventas."""
    df_items = items_por_año.get(year)
    if df_items is None or df_items.empty:
        return "-", 0

    df = df_items.copy()
    df["Fecha"] = pd.to_datetime(df["Fecha"], errors="coerce")
    if "Estado" in df.columns:
        df = df[df["Estado"] != "Cancelado"]
    if "Tipo de recibo" in df.columns:
        df = df[df["Tipo de recibo"] == "Venta"]
    df = df[df["Fecha"].dt.month == mes]
    if df.empty:
        return "-", 0

    df["dia_semana"] = df["Fecha"].dt.dayofweek
    ventas_dia = df.groupby("dia_semana")["Ventas netas"].sum()
    if ventas_dia.empty:
        return "-", 0

    dias = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes",
            "Sábado", "Domingo"]
    mejor = ventas_dia.idxmax()
    n_dias = df[df["dia_semana"] == mejor]["Fecha"].dt.date.nunique()
    media = ventas_dia[mejor] / n_dias if n_dias > 0 else 0
    return dias[int(mejor)], round(media, 2)


def _top3_productos(pbm_data, mes, pbm_data_prev_year=None):
    """Devuelve top 3 productos con euros, cant y variación vs mes anterior."""
    mes_data = pbm_data.get(str(mes), {})
    all_prods = []
    for cat_prods in mes_data.values():
        all_prods.extend(cat_prods)
    all_prods.sort(key=lambda x: x.get("euros", 0), reverse=True)
    top3 = all_prods[:3]

    # Datos del mes anterior para comparar
    if mes > 1:
        ant_data = pbm_data.get(str(mes - 1), {})
    elif pbm_data_prev_year:
        ant_data = pbm_data_prev_year.get("12", {})
    else:
        ant_data = {}
    ant_prods = {}
    for cat_prods in ant_data.values():
        for p in cat_prods:
            ant_prods[p["art"]] = p

    result = []
    for p in top3:
        euros_ant = ant_prods.get(p["art"], {}).get("euros", 0)
        var_pct = ((p["euros"] - euros_ant) / euros_ant * 100
                   if euros_ant > 0 else None)
        result.append({
            "art": p["art"], "euros": p["euros"],
            "cant": p["cant"], "var_pct": var_pct,
        })
    return result


def _var_html(euros, euros_ref):
    """Genera HTML de variación porcentual con flecha y color."""
    if euros_ref > 0:
        pct = (euros - euros_ref) / euros_ref * 100
        color = "#2E7D32" if pct >= 0 else "#C62828"
        arrow = "▲" if pct >= 0 else "▼"
        return f'<font color="{color}"><b>{arrow} {pct:+.1f}%</b></font>'
    return '<font color="#999">—</font>'


def _kpi_card(nombre, data_dict, year, mes, pbm_data, items_dict,
              color_accent, color_bg, font_name, font_bold,
              pbm_data_prev_year=None):
    """Genera tabla-card de KPIs para un negocio."""
    from reportlab.lib.units import mm
    from reportlab.lib.colors import HexColor, white
    from reportlab.platypus import Table, TableStyle, Paragraph
    from reportlab.lib.styles import ParagraphStyle

    d_mes = data_dict.get(year, {}).get("mensual", {}).get(str(mes), {})
    euros = d_mes.get("euros", 0)
    tickets = d_mes.get("tickets", 0)
    prom = d_mes.get("prom_ticket", 0)

    # vs año anterior
    year_ant = str(int(year) - 1)
    euros_ant_year = (data_dict.get(year_ant, {}).get("mensual", {})
                      .get(str(mes), {}).get("euros", 0))

    # vs mes anterior
    if mes > 1:
        euros_ant_mes = (data_dict.get(year, {}).get("mensual", {})
                         .get(str(mes - 1), {}).get("euros", 0))
    else:
        euros_ant_mes = (data_dict.get(year_ant, {}).get("mensual", {})
                         .get("12", {}).get("euros", 0))

    top3 = _top3_productos(pbm_data, mes, pbm_data_prev_year)
    dia, dia_media = _calcular_dia_fuerte(items_dict, year, mes)

    uid = nombre.replace(" ", "_")
    s_hdr = ParagraphStyle(f"kc_h_{uid}", fontName=font_bold, fontSize=11,
                           textColor=white, leading=14)
    s_big = ParagraphStyle(f"kc_b_{uid}", fontName=font_bold, fontSize=24,
                           textColor=HexColor("#1a1a1a"), leading=28)
    s_var = ParagraphStyle(f"kc_v_{uid}", fontName=font_name, fontSize=9,
                           textColor=HexColor("#555"), leading=12)
    s_det = ParagraphStyle(f"kc_d_{uid}", fontName=font_name, fontSize=9,
                           textColor=HexColor("#444"), leading=13)

    card_w = 82 * mm
    rows = [
        [Paragraph(nombre, s_hdr)],
        [Paragraph(_fmt_eur(euros, 0), s_big)],
        [Paragraph(f"vs año ant.: {_var_html(euros, euros_ant_year)}", s_var)],
        [Paragraph(f"vs mes ant.: {_var_html(euros, euros_ant_mes)}", s_var)],
        [Paragraph(f"<b>{tickets}</b> tickets &nbsp;·&nbsp; "
                   f"<b>{_fmt_eur(prom)}</b> ticket medio", s_det)],
        [Paragraph(f"Día fuerte: <b>{dia}</b> &nbsp;·&nbsp; "
                   f"media {_fmt_eur(dia_media)}", s_det)],
    ]
    if top3:
        lines = []
        for p in top3:
            if p["var_pct"] is not None:
                vc = "#2E7D32" if p["var_pct"] >= 0 else "#C62828"
                va = "▲" if p["var_pct"] >= 0 else "▼"
                vs = f' <font color="{vc}"><b>{va}{abs(p["var_pct"]):.0f}%</b></font>'
            else:
                vs = ' <font color="#999">nuevo</font>'
            lines.append(
                f'&nbsp;&nbsp;· {p["art"]}<br/>'
                f'&nbsp;&nbsp;&nbsp;&nbsp;{p["cant"]:.0f} uds · '
                f'{_fmt_eur(p["euros"])}{vs}')
        rows.append([Paragraph(
            f"Top productos:<br/>{'<br/>'.join(lines)}", s_det)])

    t = Table(rows, colWidths=[card_w])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, 0), HexColor(color_accent)),
        ("BACKGROUND", (0, 1), (0, -1), HexColor(color_bg)),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 1), (0, 1), 8),
        ("BOTTOMPADDING", (0, 2), (0, 3), 1),
        ("BOX", (0, 0), (-1, -1), 1, HexColor(color_accent)),
        ("LINEBELOW", (0, 0), (0, 0), 1, HexColor(color_accent)),
    ]))
    return t


def _tabla_categorias_pdf(data_dict, year, mes, mes_nombre, color_header,
                          font_name, font_bold, color_odd_row="#F7F8FA"):
    """Genera tabla de categorias con filas alternadas."""
    from reportlab.lib.units import mm
    from reportlab.lib.colors import HexColor, white
    from reportlab.platypus import Table, TableStyle

    if "categorias_mes" in data_dict.get(year, {}):
        cats_mes = data_dict[year]["categorias_mes"].get(str(mes), {})
    else:
        cats_mes = data_dict.get(year, {}).get("mensual", {}).get(
            str(mes), {}).get("cats", {})
    euros_mes = data_dict.get(year, {}).get("mensual", {}).get(
        str(mes), {}).get("euros", 0)

    cats_ytd = defaultdict(float)
    total_ytd = 0
    for m in range(1, mes + 1):
        m_euros = data_dict.get(year, {}).get("mensual", {}).get(
            str(m), {}).get("euros", 0)
        total_ytd += m_euros
        if "categorias_mes" in data_dict.get(year, {}):
            cm = data_dict[year]["categorias_mes"].get(str(m), {})
        else:
            cm = data_dict.get(year, {}).get("mensual", {}).get(
                str(m), {}).get("cats", {})
        for cat, pct in cm.items():
            cats_ytd[cat] += pct / 100 * m_euros

    all_cats = sorted(set(list(cats_mes.keys()) + list(cats_ytd.keys())))
    rows = [["Categoría", mes_nombre, "% mes", "Acum. YTD", "% YTD"]]
    for cat in all_cats:
        pct_m = cats_mes.get(cat, 0)
        e_m = pct_m / 100 * euros_mes if euros_mes > 0 else 0
        e_ytd = cats_ytd.get(cat, 0)
        p_ytd = (e_ytd / total_ytd * 100) if total_ytd > 0 else 0
        rows.append([cat, _fmt_eur(e_m), f"{pct_m:.1f}%",
                     _fmt_eur(e_ytd), f"{p_ytd:.1f}%"])
    rows.append(["TOTAL", _fmt_eur(euros_mes), "100%",
                 _fmt_eur(total_ytd), "100%"])

    t = Table(rows, colWidths=[38*mm, 22*mm, 14*mm, 24*mm, 14*mm])
    cmds = [
        ("FONTNAME", (0, 0), (-1, 0), font_bold),
        ("FONTNAME", (0, 1), (-1, -1), font_name),
        ("FONTNAME", (0, -1), (-1, -1), font_bold),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("BACKGROUND", (0, 0), (-1, 0), HexColor(color_header)),
        ("TEXTCOLOR", (0, 0), (-1, 0), white),
        ("BACKGROUND", (0, -1), (-1, -1), HexColor("#EEEEEE")),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("GRID", (0, 0), (-1, -1), 0.4, HexColor("#DDDDDD")),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
    ]
    for i in range(1, len(rows) - 1):
        if i % 2 == 1:
            cmds.append(("BACKGROUND", (0, i), (-1, i), HexColor(color_odd_row)))
    t.setStyle(TableStyle(cmds))
    return t


def generar_pdf_resumen(D, RAW, PBM_tasca, comes_items, tasca_items):
    """Genera PDF A4 con resumen mensual de ambos negocios."""
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import mm
        from reportlab.lib.colors import HexColor, white
        from reportlab.lib.styles import ParagraphStyle
        from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                        Image, Table, TableStyle, PageBreak)
    except ImportError:
        print("  Aviso: reportlab no instalado, no se genera PDF")
        return None

    font_name, font_bold = _setup_pdf_fonts()
    W, H = A4

    mes_cerrado = datetime.now().month - 1
    year_actual = YEAR_LIST[-1]
    if mes_cerrado < 1:
        mes_cerrado = 12
        year_actual = str(int(year_actual) - 1)
    mes_nombre = MESES_FULL[mes_cerrado - 1]

    chart_tasca, chart_comes, chart_conjunto, chart_total, tmp_dir = \
        _generar_graficos_pdf(D, RAW, mes_cerrado, year_actual)

    pdf_name = f"informe_barea_{mes_nombre.lower()}_{year_actual}.pdf"
    pdf_path = os.path.join(_SCRIPT_DIR, "dashboards", pdf_name)

    # ── Canvas callbacks ──
    def _on_first_page(canvas, doc):
        canvas.saveState()
        # Banda cabecera roja (ambos establecimientos)
        canvas.setFillColor(HexColor("#FF0000"))
        canvas.rect(0, H - 30*mm, W, 30*mm, fill=1, stroke=0)
        # Linea inferior
        canvas.setStrokeColor(HexColor("#CC0000"))
        canvas.setLineWidth(2)
        canvas.line(0, H - 30*mm, W, H - 30*mm)
        # Titulo
        canvas.setFillColor(white)
        canvas.setFont(font_bold, 18)
        canvas.drawCentredString(W / 2, H - 15*mm, "Informe Mensual")
        canvas.setFont(font_name, 13)
        canvas.setFillColor(HexColor("#B0BEC5"))
        canvas.drawCentredString(W / 2, H - 23*mm,
                                 f"{mes_nombre} {year_actual}")
        # Logos
        try:
            if os.path.exists(PATH_LOGO_TASCA):
                canvas.drawImage(PATH_LOGO_TASCA, 12*mm, H - 28*mm,
                                 22*mm, 22*mm, preserveAspectRatio=True)
        except Exception:
            pass
        try:
            if os.path.exists(PATH_LOGO_COMES):
                canvas.drawImage(PATH_LOGO_COMES, W - 34*mm, H - 28*mm,
                                 22*mm, 22*mm, preserveAspectRatio=True)
        except Exception:
            pass
        _draw_footer(canvas, doc)
        canvas.restoreState()

    def _on_later_pages(canvas, doc):
        canvas.saveState()
        canvas.setStrokeColor(HexColor("#FF0000"))
        canvas.setLineWidth(1.5)
        canvas.line(15*mm, H - 10*mm, W - 15*mm, H - 10*mm)
        canvas.setFont(font_bold, 8)
        canvas.setFillColor(HexColor("#FF0000"))
        canvas.drawString(15*mm, H - 8*mm,
                          f"Informe Mensual — {mes_nombre} {year_actual}")
        _draw_footer(canvas, doc)
        canvas.restoreState()

    def _draw_footer(canvas, doc):
        canvas.setStrokeColor(HexColor("#CCCCCC"))
        canvas.setLineWidth(0.5)
        canvas.line(15*mm, 13*mm, W - 15*mm, 13*mm)
        canvas.setFillColor(HexColor("#999999"))
        canvas.setFont(font_name, 7)
        canvas.drawString(
            15*mm, 8*mm,
            f"Generado el {datetime.now().strftime('%d/%m/%Y %H:%M')}")
        canvas.drawRightString(W - 15*mm, 8*mm,
                               f"Página {doc.page}")

    doc = SimpleDocTemplate(pdf_path, pagesize=A4,
                            leftMargin=15*mm, rightMargin=15*mm,
                            topMargin=15*mm, bottomMargin=18*mm)
    elements = []

    # Estilos
    s_heading = ParagraphStyle(
        "pr_h", fontName=font_bold, fontSize=14,
        textColor=HexColor("#FF0000"), spaceBefore=4*mm, spaceAfter=3*mm)
    s_body = ParagraphStyle(
        "pr_b", fontName=font_name, fontSize=10,
        textColor=HexColor("#333"), leading=14)
    s_section = ParagraphStyle(
        "pr_s", fontName=font_bold, fontSize=11,
        textColor=HexColor("#FF0000"), spaceBefore=2*mm, spaceAfter=2*mm)

    # ── PAGINA 1: KPIs + Comparativa ──
    elements.append(Spacer(1, 20*mm))
    elements.append(Paragraph("Resumen del mes", s_heading))

    year_ant = str(int(year_actual) - 1)
    comes_pbm = D.get(year_actual, {}).get("pbm", {})
    comes_pbm_prev = D.get(year_ant, {}).get("pbm", {})
    card_t = _kpi_card("TASCA BAREA", RAW, year_actual, mes_cerrado,
                       PBM_tasca.get(year_actual, {}), tasca_items,
                       "#1F4E79", "#DEEAF1", font_name, font_bold,
                       PBM_tasca.get(year_ant, {}))
    card_c = _kpi_card("COMESTIBLES BAREA", D, year_actual, mes_cerrado,
                       comes_pbm, comes_items,
                       "#375623", "#C6EFCE", font_name, font_bold,
                       comes_pbm_prev)
    cards = Table([[card_t, "", card_c]], colWidths=[84*mm, 6*mm, 84*mm])
    cards.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    elements.append(cards)
    elements.append(Spacer(1, 6*mm))

    # ── Tabla YTD ──
    def _ytd_kpis(data_dict, year, hasta_mes):
        ventas, tickets = 0, 0
        for m in range(1, hasta_mes + 1):
            d = data_dict.get(year, {}).get("mensual", {}).get(str(m), {})
            ventas += d.get("euros", 0)
            tickets += d.get("tickets", 0)
        ticket_medio = ventas / tickets if tickets > 0 else 0
        return ventas, tickets, ticket_medio

    from reportlab.platypus import Table, TableStyle
    from reportlab.lib.colors import HexColor

    def _tabla_ytd_pdf(titulo, color_accent, color_bg, data_actual, data_ant):
        v_act, t_act, tm_act = data_actual
        v_ant, t_ant, tm_ant = data_ant

        def pct(a, b):
            if b == 0:
                return "—"
            p = (a - b) / b * 100
            signo = "▲" if p >= 0 else "▼"
            return f"{signo}{abs(p):.1f}%"

        s_hdr = ParagraphStyle(f"ytd_h_{titulo}", fontName=font_bold,
                               fontSize=9, textColor=HexColor("#FFFFFF"))
        s_lbl = ParagraphStyle(f"ytd_l_{titulo}", fontName=font_bold,
                               fontSize=9, textColor=HexColor("#333"))
        s_val = ParagraphStyle(f"ytd_v_{titulo}", fontName=font_name,
                               fontSize=9, textColor=HexColor("#333"))

        rows = [
            [Paragraph(f"YTD {year_actual}", s_hdr),
             Paragraph("Acumulado", s_hdr),
             Paragraph(year_ant, s_hdr),
             Paragraph(f"vs YTD {year_ant}", s_hdr)],
            [Paragraph("Ventas netas", s_lbl),
             Paragraph(_fmt_eur(v_act), s_val),
             Paragraph(_fmt_eur(v_ant), s_val),
             Paragraph(pct(v_act, v_ant), s_val)],
            [Paragraph("Tickets", s_lbl),
             Paragraph(f"{t_act:,}".replace(",", "."), s_val),
             Paragraph(f"{t_ant:,}".replace(",", "."), s_val),
             Paragraph(pct(t_act, t_ant), s_val)],
            [Paragraph("Ticket medio", s_lbl),
             Paragraph(_fmt_eur(tm_act), s_val),
             Paragraph(_fmt_eur(tm_ant), s_val),
             Paragraph(pct(tm_act, tm_ant), s_val)],
        ]
        t = Table(rows, colWidths=[40*mm, 37*mm, 37*mm, 37*mm])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), HexColor(color_accent)),
            ("BACKGROUND", (0, 1), (-1, -1), HexColor(color_bg)),
            ("BACKGROUND", (0, 2), (-1, 2), HexColor("#FFFFFF")),
            ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#CCCCCC")),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
            ("ALIGN", (3, 0), (3, -1), "CENTER"),
        ]))
        return t

    elements.append(Paragraph("Acumulado año (YTD)", s_heading))
    ytd_t_act = _ytd_kpis(RAW, year_actual, mes_cerrado)
    ytd_t_ant = _ytd_kpis(RAW, year_ant, mes_cerrado)
    ytd_c_act = _ytd_kpis(D, year_actual, mes_cerrado)
    ytd_c_ant = _ytd_kpis(D, year_ant, mes_cerrado)

    elements.append(Paragraph("Tasca Barea", ParagraphStyle(
        "ytd_st", fontName=font_bold, fontSize=10,
        textColor=HexColor("#1F4E79"), spaceAfter=2*mm)))
    elements.append(_tabla_ytd_pdf(
        "tasca", "#1F4E79", "#DEEAF1", ytd_t_act, ytd_t_ant))
    elements.append(Spacer(1, 4*mm))
    elements.append(Paragraph("Comestibles Barea", ParagraphStyle(
        "ytd_sc", fontName=font_bold, fontSize=10,
        textColor=HexColor("#375623"), spaceAfter=2*mm)))
    elements.append(_tabla_ytd_pdf(
        "comes", "#375623", "#C6EFCE", ytd_c_act, ytd_c_ant))
    elements.append(Spacer(1, 6*mm))

    elements.append(Paragraph("Comparativa", s_heading))
    elements.append(Image(chart_conjunto, width=170*mm, height=62*mm))

    # ── PAGINA 2: Evolucion por negocio ──
    elements.append(PageBreak())
    elements.append(Paragraph(
        "Evolución de facturación", s_heading))
    elements.append(Spacer(1, 2*mm))
    elements.append(Image(chart_total, width=170*mm, height=65*mm))
    elements.append(Spacer(1, 6*mm))
    elements.append(Image(chart_tasca, width=170*mm, height=55*mm))
    elements.append(Spacer(1, 6*mm))
    elements.append(Image(chart_comes, width=170*mm, height=55*mm))

    # ── PAGINA 3: Categorias ──
    elements.append(PageBreak())
    elements.append(Paragraph(
        f"Ventas por categoría — {mes_nombre} {year_actual}",
        s_heading))

    elements.append(Paragraph("Tasca Barea", ParagraphStyle(
        "pr_ct", parent=s_section, textColor=HexColor("#1F4E79"))))
    elements.append(Spacer(1, 1*mm))
    elements.append(_tabla_categorias_pdf(
        RAW, year_actual, mes_cerrado, mes_nombre,
        "#1F4E79", font_name, font_bold, "#DEEAF1"))
    elements.append(Spacer(1, 6*mm))

    elements.append(Paragraph("Comestibles Barea", ParagraphStyle(
        "pr_cc", parent=s_section, textColor=HexColor("#375623"))))
    elements.append(Spacer(1, 1*mm))
    elements.append(_tabla_categorias_pdf(
        D, year_actual, mes_cerrado, mes_nombre,
        "#375623", font_name, font_bold, "#C6EFCE"))
    elements.append(Spacer(1, 8*mm))

    if GITHUB_PAGES_URL:
        url_c = GITHUB_PAGES_URL + "comestibles.html"
        url_t = GITHUB_PAGES_URL + "tasca.html"
        elements.append(Paragraph(
            f'<b>Dashboards interactivos:</b><br/>'
            f'<a href="{url_c}" color="#1565C0">{url_c}</a><br/>'
            f'<a href="{url_t}" color="#1565C0">{url_t}</a>',
            s_body))

    doc.build(elements, onFirstPage=_on_first_page,
              onLaterPages=_on_later_pages)

    try:
        shutil.rmtree(tmp_dir)
    except Exception:
        pass

    print(f"  PDF generado: {pdf_path}")
    return pdf_path


def generar_pdf_comestibles(D, comes_items):
    """Genera PDF A4 solo Comestibles - diseño profesional."""
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import mm
        from reportlab.lib.colors import HexColor, white
        from reportlab.lib.styles import ParagraphStyle
        from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                        Image, Table, TableStyle)
    except ImportError:
        print("  Aviso: reportlab no instalado, no se genera PDF Comestibles")
        return None

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.ticker import FuncFormatter

    font_name, font_bold = _setup_pdf_fonts()
    W, H = A4

    mes_cerrado = datetime.now().month - 1
    year_actual = YEAR_LIST[-1]
    if mes_cerrado < 1:
        mes_cerrado = 12
        year_actual = str(int(year_actual) - 1)
    mes_nombre = MESES_FULL[mes_cerrado - 1]

    # Grafico con estilo mejorado
    tmp_dir = tempfile.mkdtemp(prefix="barea_pdf_comes_")
    fmt_euros = FuncFormatter(lambda x, _: _fmt_eur(x, 0))
    comes_colors = {"2025": "#82B878", "2026": "#375623"}

    plt.rcParams.update({
        'figure.facecolor': 'white',
        'axes.facecolor': '#F8F9FA',
        'axes.spines.top': False,
        'axes.spines.right': False,
        'grid.alpha': 0.25,
        'font.size': 9,
    })

    fig, ax = plt.subplots(figsize=(9, 4))
    for yr in YEAR_LIST:
        if yr not in D:
            continue
        mensual = D[yr]["mensual"]
        xs, vals = [], []
        for m in range(1, 13):
            e = mensual.get(str(m), {}).get("euros", 0)
            if e and e > 0:
                xs.append(m)
                vals.append(e)
        if not vals:
            continue
        color = comes_colors.get(yr, "#999")
        is_cur = (yr == year_actual)
        lw = 2.5 if is_cur else 1.5
        ms = 6 if is_cur else 3
        a = 1.0 if is_cur else 0.45
        z = 3 if is_cur else 2
        # Segmentos con parcial
        labeled = False
        for i in range(1, len(xs)):
            parcial = (xs[i] in MESES_PARCIALES or xs[i-1] in MESES_PARCIALES)
            kw = dict(color=color, linewidth=lw, zorder=z)
            if parcial:
                kw.update(linestyle='--', alpha=a * 0.4)
            else:
                kw['alpha'] = a
            if not labeled:
                kw['label'] = yr
                labeled = True
            ax.plot([xs[i-1], xs[i]], [vals[i-1], vals[i]], **kw)
        if not labeled:
            ax.plot([], [], color=color, linewidth=lw, alpha=a, label=yr)
        for x, v in zip(xs, vals):
            p = x in MESES_PARCIALES
            ax.plot(x, v, 'o', color=color,
                    markersize=3 if p else ms,
                    alpha=0.3 if p else a, zorder=z + 1)
        if is_cur:
            ax.fill_between(xs, vals, alpha=0.07, color=color)
            for x, v in zip(xs, vals):
                p = x in MESES_PARCIALES
                txt = _fmt_eur(v, 0) + ('*' if p else '')
                ax.annotate(txt, (x, v),
                            textcoords="offset points", xytext=(0, 10),
                            ha="center", fontsize=7, color=color,
                            fontweight="bold")
                if p:
                    ax.annotate('parcial', (x, v),
                                textcoords="offset points", xytext=(0, -12),
                                ha="center", fontsize=6, color="#999",
                                fontstyle="italic")
    ax.set_title("Comestibles Barea — Facturación mensual",
                 fontsize=12, fontweight="bold", pad=12, color="#1a1a1a")
    ax.set_xticks(range(1, 13))
    ax.set_xticklabels(MESES_CORTO, fontsize=8)
    ax.yaxis.set_major_formatter(fmt_euros)
    ax.tick_params(axis="y", labelsize=8)
    ax.legend(fontsize=8, loc="upper right", framealpha=0.9, edgecolor="#DDD")
    ax.grid(True, axis="y", alpha=0.25)
    ax.set_xlim(0.5, 12.5)
    for spine in ("bottom", "left"):
        ax.spines[spine].set_color("#CCCCCC")
    fig.tight_layout(pad=1.5)
    chart_path = os.path.join(tmp_dir, "chart_comes.png")
    fig.savefig(chart_path, dpi=180, bbox_inches="tight")
    plt.close(fig)
    plt.rcParams.update(plt.rcParamsDefault)

    # ── PDF ──
    pdf_name = f"informe_comestibles_{mes_nombre.lower()}_{year_actual}.pdf"
    pdf_path = os.path.join(_SCRIPT_DIR, "dashboards", pdf_name)

    def _on_first_page(canvas, doc):
        canvas.saveState()
        canvas.setFillColor(HexColor("#375623"))
        canvas.rect(0, H - 30*mm, W, 30*mm, fill=1, stroke=0)
        canvas.setStrokeColor(HexColor("#C6EFCE"))
        canvas.setLineWidth(2)
        canvas.line(0, H - 30*mm, W, H - 30*mm)
        canvas.setFillColor(white)
        canvas.setFont(font_bold, 18)
        canvas.drawCentredString(W / 2, H - 15*mm, "Comestibles Barea")
        canvas.setFont(font_name, 13)
        canvas.setFillColor(HexColor("#C6EFCE"))
        canvas.drawCentredString(W / 2, H - 23*mm,
                                 f"Informe {mes_nombre} {year_actual}")
        try:
            if os.path.exists(PATH_LOGO_COMES):
                canvas.drawImage(PATH_LOGO_COMES, 12*mm, H - 28*mm,
                                 22*mm, 22*mm, preserveAspectRatio=True)
        except Exception:
            pass
        _draw_footer_c(canvas, doc)
        canvas.restoreState()

    def _on_later_pages(canvas, doc):
        canvas.saveState()
        canvas.setStrokeColor(HexColor("#375623"))
        canvas.setLineWidth(1.5)
        canvas.line(15*mm, H - 10*mm, W - 15*mm, H - 10*mm)
        canvas.setFont(font_bold, 8)
        canvas.setFillColor(HexColor("#375623"))
        canvas.drawString(15*mm, H - 8*mm,
                          f"Comestibles Barea — {mes_nombre} {year_actual}")
        _draw_footer_c(canvas, doc)
        canvas.restoreState()

    def _draw_footer_c(canvas, doc):
        canvas.setStrokeColor(HexColor("#CCCCCC"))
        canvas.setLineWidth(0.5)
        canvas.line(15*mm, 13*mm, W - 15*mm, 13*mm)
        canvas.setFillColor(HexColor("#999"))
        canvas.setFont(font_name, 7)
        canvas.drawString(
            15*mm, 8*mm,
            f"Generado el {datetime.now().strftime('%d/%m/%Y %H:%M')}")
        canvas.drawRightString(W - 15*mm, 8*mm,
                               f"Página {doc.page}")

    doc = SimpleDocTemplate(pdf_path, pagesize=A4,
                            leftMargin=15*mm, rightMargin=15*mm,
                            topMargin=15*mm, bottomMargin=18*mm)
    elements = []

    s_heading = ParagraphStyle(
        "pc_h", fontName=font_bold, fontSize=14,
        textColor=HexColor("#375623"), spaceBefore=4*mm, spaceAfter=3*mm)
    s_body = ParagraphStyle(
        "pc_b", fontName=font_name, fontSize=10,
        textColor=HexColor("#333"), leading=14)
    s_det = ParagraphStyle(
        "pc_det", fontName=font_name, fontSize=10,
        textColor=HexColor("#444"), leading=14)

    elements.append(Spacer(1, 20*mm))
    elements.append(Paragraph("Resumen del mes", s_heading))

    # KPIs como card unica
    d_mes = D.get(year_actual, {}).get("mensual", {}).get(
        str(mes_cerrado), {})
    euros = d_mes.get("euros", 0)
    tickets = d_mes.get("tickets", 0)
    prom = d_mes.get("prom_ticket", 0)

    year_ant = str(int(year_actual) - 1)
    euros_ant_year = (D.get(year_ant, {}).get("mensual", {})
                      .get(str(mes_cerrado), {}).get("euros", 0))
    if mes_cerrado > 1:
        euros_ant_mes = (D.get(year_actual, {}).get("mensual", {})
                         .get(str(mes_cerrado - 1), {}).get("euros", 0))
    else:
        euros_ant_mes = (D.get(year_ant, {}).get("mensual", {})
                         .get("12", {}).get("euros", 0))

    comes_pbm = D.get(year_actual, {}).get("pbm", {})
    comes_pbm_prev = D.get(year_ant, {}).get("pbm", {})
    top3 = _top3_productos(comes_pbm, mes_cerrado, comes_pbm_prev)
    dia, dia_media = _calcular_dia_fuerte(comes_items, year_actual,
                                          mes_cerrado)

    s_big = ParagraphStyle("pc_big", fontName=font_bold, fontSize=28,
                           textColor=HexColor("#1a1a1a"), leading=32)
    s_var = ParagraphStyle("pc_var", fontName=font_name, fontSize=10,
                           textColor=HexColor("#555"), leading=13)

    kpi_rows = [
        [Paragraph(_fmt_eur(euros, 0), s_big), ""],
        [Paragraph(
            f"vs año ant.: {_var_html(euros, euros_ant_year)} "
            f"&nbsp;·&nbsp; vs mes ant.: "
            f"{_var_html(euros, euros_ant_mes)}", s_var), ""],
        [Paragraph(
            f"<b>{tickets}</b> tickets &nbsp;·&nbsp; "
            f"<b>{_fmt_eur(prom)}</b> ticket medio &nbsp;·&nbsp; "
            f"Día fuerte: <b>{dia}</b> (media {_fmt_eur(dia_media)})",
            s_det), ""],
    ]
    if top3:
        lines = []
        for p in top3:
            if p["var_pct"] is not None:
                vc = "#2E7D32" if p["var_pct"] >= 0 else "#C62828"
                va = "▲" if p["var_pct"] >= 0 else "▼"
                vs = (f' <font color="{vc}"><b>'
                      f'{va}{abs(p["var_pct"]):.0f}%</b></font>')
            else:
                vs = ' <font color="#999">nuevo</font>'
            lines.append(
                f'{p["art"]} — {p["cant"]:.0f} uds · '
                f'{_fmt_eur(p["euros"])}{vs}')
        items_html = " &nbsp;·&nbsp; ".join(lines)
        kpi_rows.append([Paragraph(
            f"Top productos: {items_html}", s_det), ""])

    kpi_t = Table(kpi_rows, colWidths=[100*mm, 70*mm])
    kpi_t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BACKGROUND", (0, 0), (-1, -1), HexColor("#C6EFCE")),
        ("BOX", (0, 0), (-1, -1), 1, HexColor("#375623")),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
    ]))
    elements.append(kpi_t)
    elements.append(Spacer(1, 6*mm))

    # ── Tabla YTD Comestibles ──
    def _ytd_sum(data_dict, yr, hasta_mes):
        ventas, tickets = 0, 0
        for m in range(1, hasta_mes + 1):
            d = data_dict.get(yr, {}).get("mensual", {}).get(str(m), {})
            ventas += d.get("euros", 0)
            tickets += d.get("tickets", 0)
        tm = ventas / tickets if tickets > 0 else 0
        return ventas, tickets, tm

    def pct_str(a, b):
        if b == 0:
            return "—"
        p = (a - b) / b * 100
        return ("▲" if p >= 0 else "▼") + f"{abs(p):.1f}%"

    v_act, t_act, tm_act = _ytd_sum(D, year_actual, mes_cerrado)
    v_ant, t_ant, tm_ant = _ytd_sum(D, year_ant, mes_cerrado)

    s_ytd_h = ParagraphStyle("pc_yh", fontName=font_bold, fontSize=9,
                             textColor=HexColor("#FFFFFF"))
    s_ytd_l = ParagraphStyle("pc_yl", fontName=font_bold, fontSize=9,
                             textColor=HexColor("#333"))
    s_ytd_v = ParagraphStyle("pc_yv", fontName=font_name, fontSize=9,
                             textColor=HexColor("#333"))
    ytd_rows = [
        [Paragraph(f"YTD {year_actual}", s_ytd_h),
         Paragraph("Acumulado", s_ytd_h),
         Paragraph(year_ant, s_ytd_h),
         Paragraph(f"vs YTD {year_ant}", s_ytd_h)],
        [Paragraph("Ventas netas", s_ytd_l),
         Paragraph(_fmt_eur(v_act), s_ytd_v),
         Paragraph(_fmt_eur(v_ant), s_ytd_v),
         Paragraph(pct_str(v_act, v_ant), s_ytd_v)],
        [Paragraph("Tickets", s_ytd_l),
         Paragraph(f"{t_act:,}".replace(",", "."), s_ytd_v),
         Paragraph(f"{t_ant:,}".replace(",", "."), s_ytd_v),
         Paragraph(pct_str(t_act, t_ant), s_ytd_v)],
        [Paragraph("Ticket medio", s_ytd_l),
         Paragraph(_fmt_eur(tm_act), s_ytd_v),
         Paragraph(_fmt_eur(tm_ant), s_ytd_v),
         Paragraph(pct_str(tm_act, tm_ant), s_ytd_v)],
    ]
    ytd_t = Table(ytd_rows, colWidths=[40*mm, 37*mm, 37*mm, 37*mm])
    ytd_t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), HexColor("#375623")),
        ("BACKGROUND", (0, 1), (-1, -1), HexColor("#C6EFCE")),
        ("BACKGROUND", (0, 2), (-1, 2), HexColor("#FFFFFF")),
        ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#CCCCCC")),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("ALIGN", (3, 0), (3, -1), "CENTER"),
    ]))
    elements.append(Paragraph("Acumulado año (YTD)", s_heading))
    elements.append(ytd_t)
    elements.append(Spacer(1, 6*mm))

    # Grafico
    elements.append(Paragraph(
        "Evolución de facturación", s_heading))
    elements.append(Image(chart_path, width=170*mm, height=68*mm))
    elements.append(Spacer(1, 6*mm))

    # Categorias
    elements.append(Paragraph(
        f"Ventas por categoría — {mes_nombre} {year_actual}",
        s_heading))
    elements.append(_tabla_categorias_pdf(
        D, year_actual, mes_cerrado, mes_nombre,
        "#375623", font_name, font_bold, "#C6EFCE"))
    elements.append(Spacer(1, 8*mm))

    if GITHUB_PAGES_URL:
        url_c = GITHUB_PAGES_URL + "comestibles.html"
        elements.append(Paragraph(
            f'<b>Dashboard interactivo:</b> '
            f'<a href="{url_c}" color="#1565C0">{url_c}</a>', s_body))

    doc.build(elements, onFirstPage=_on_first_page,
              onLaterPages=_on_later_pages)

    try:
        shutil.rmtree(tmp_dir)
    except Exception:
        pass

    print(f"  PDF Comestibles generado: {pdf_path}")
    return pdf_path



# ══════════════════════════════════════════════════════════════════════════════
# EMAIL
# ══════════════════════════════════════════════════════════════════════════════

def _conectar_gmail():
    """Conecta con Gmail API y devuelve service, o None si falla."""
    try:
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
        from googleapiclient.discovery import build
    except ImportError:
        print("  Aviso: google-auth/google-api-python-client no instalados")
        return None

    if not os.path.exists(_GMAIL_TOKEN):
        print("  Aviso: no existe token.json de Gmail")
        return None

    scopes = [
        "https://www.googleapis.com/auth/gmail.readonly",
        "https://www.googleapis.com/auth/gmail.modify",
    ]
    creds = Credentials.from_authorized_user_file(_GMAIL_TOKEN, scopes)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            with open(_GMAIL_TOKEN, "w") as f:
                f.write(creds.to_json())
        else:
            print("  Aviso: credenciales Gmail expiradas")
            return None

    return build("gmail", "v1", credentials=creds)


def _adjuntar_archivo(message, path, filename, mime_type="application", mime_subtype="octet-stream"):
    """Adjunta un archivo a un MIMEMultipart."""
    if not path or not os.path.exists(path):
        return
    with open(path, "rb") as f:
        adj = MIMEBase(mime_type, mime_subtype)
        adj.set_payload(f.read())
        encoders.encode_base64(adj)
        adj.add_header("Content-Disposition", "attachment", filename=filename)
        message.attach(adj)


def _enviar_mensaje(service, email_dest, asunto, html_body, adjuntos):
    """Envia un email con adjuntos via Gmail API."""
    message = MIMEMultipart("mixed")
    message["To"] = email_dest
    message["Subject"] = asunto
    message.attach(MIMEText(html_body, "html"))
    for path, filename, mtype, msubtype in adjuntos:
        _adjuntar_archivo(message, path, filename, mtype, msubtype)
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    service.users().messages().send(userId="me", body={"raw": raw}).execute()


def _kpis_variacion_html(data_dict, year, mes, color):
    """Genera HTML de KPIs para un negocio."""
    d_mes = data_dict.get(year, {}).get("mensual", {}).get(str(mes), {})
    euros = d_mes.get("euros", 0)
    tickets = d_mes.get("tickets", 0)
    prom = d_mes.get("prom_ticket", 0)

    year_ant = str(int(year) - 1)
    d_ant = data_dict.get(year_ant, {}).get("mensual", {}).get(str(mes), {})
    euros_ant = d_ant.get("euros", 0)
    var_html = ""
    if euros_ant > 0:
        var = (euros - euros_ant) / euros_ant * 100
        sign = "+" if var >= 0 else ""
        vc = "#155724" if var >= 0 else "#721C24"
        var_html = f'<span style="color:{vc};font-weight:bold">{sign}{var:.1f}%</span> vs {year_ant}'

    kpi_html = f"""
        <table style="width:100%;border-collapse:collapse;margin-bottom:8px">
          <tr>
            <td style="padding:10px;background:white;border:1px solid #eee;text-align:center;width:33%">
              <div style="font-size:10px;color:#888;text-transform:uppercase">Ventas</div>
              <div style="font-size:20px;font-weight:bold;color:{color}">{_fmt_eur(euros, 0)}</div>
            </td>
            <td style="padding:10px;background:white;border:1px solid #eee;text-align:center;width:33%">
              <div style="font-size:10px;color:#888;text-transform:uppercase">Tickets</div>
              <div style="font-size:20px;font-weight:bold;color:{color}">{tickets:,}</div>
            </td>
            <td style="padding:10px;background:white;border:1px solid #eee;text-align:center;width:33%">
              <div style="font-size:10px;color:#888;text-transform:uppercase">Ticket medio</div>
              <div style="font-size:20px;font-weight:bold;color:{color}">{_fmt_eur(prom)}</div>
            </td>
          </tr>
        </table>
        {f'<div style="font-size:12px;margin-bottom:12px">{var_html}</div>' if var_html else ''}"""
    return kpi_html


def enviar_email_dashboard(D, RAW, path_comes, path_tasca,
                           path_pdf=None, path_pdf_comes=None):
    """Envia emails: completo a EMAILS_FULL, solo Comestibles a EMAILS_COMES_ONLY."""
    service = _conectar_gmail()
    if not service:
        return

    mes_cerrado = datetime.now().month - 1
    year_actual = YEAR_LIST[-1]
    if mes_cerrado < 1:
        mes_cerrado = 12
        year_actual = str(int(year_actual) - 1)
    mes_nombre = MESES_FULL[mes_cerrado - 1]
    fecha_gen = datetime.now().strftime('%d/%m/%Y %H:%M')

    url_comes = GITHUB_PAGES_URL + "comestibles.html" if GITHUB_PAGES_URL else ""
    url_tasca = GITHUB_PAGES_URL + "tasca.html" if GITHUB_PAGES_URL else ""

    # ── EMAIL COMPLETO (Tasca + Comestibles) → EMAILS_FULL ──
    tasca_kpis = _kpis_variacion_html(RAW, year_actual, mes_cerrado, "#8B6914")
    comes_kpis = _kpis_variacion_html(D, year_actual, mes_cerrado, "#2E7D32")

    links_full = ""
    if url_comes:
        links_full = (
            f'<div style="margin:16px 0;text-align:center">'
            f'<a href="{url_comes}" style="background:#2E7D32;color:white;'
            f'padding:10px 20px;border-radius:6px;text-decoration:none;'
            f'font-weight:bold;font-size:13px;display:inline-block;margin:4px">'
            f'Dashboard Comestibles</a>'
            f'<a href="{url_tasca}" style="background:#8B6914;color:white;'
            f'padding:10px 20px;border-radius:6px;text-decoration:none;'
            f'font-weight:bold;font-size:13px;display:inline-block;margin:4px">'
            f'Dashboard Tasca</a></div>'
        )

    html_full = f"""
    <html>
    <body style="font-family:Arial,sans-serif;font-size:14px;color:#333;max-width:600px;margin:0 auto">
      <div style="background:#1a1a1a;color:#f0ece4;padding:20px;border-radius:8px 8px 0 0;text-align:center">
        <h2 style="margin:0;font-size:20px;color:#e8c97a">Barea</h2>
        <p style="margin:4px 0 0;color:#9a9488;font-size:12px">
          Cómo nos ha ido en {mes_nombre.lower()} {year_actual}</p>
      </div>
      <div style="background:#f8f9fa;padding:20px;border:1px solid #ddd">
        <h3 style="margin:0 0 12px;color:#8B6914;font-size:16px">Tasca</h3>
        {tasca_kpis}
        <h3 style="margin:12px 0 12px;color:#2E7D32;font-size:16px">Comestibles</h3>
        {comes_kpis}
        {links_full}
        <div style="background:#e8f4fd;border:1px solid #bee5eb;border-radius:6px;
                    padding:10px 14px;margin:12px 0;font-size:12px;color:#0c5460">
          El informe detallado va adjunto en PDF. Los dashboards interactivos
          se pueden abrir en el navegador.
        </div>
      </div>
      <div style="padding:10px;font-size:10px;color:#999;text-align:center">
        Generado el {fecha_gen}
      </div>
    </body>
    </html>
    """

    asunto_full = f"Barea - Informe {mes_nombre} {year_actual}"
    adjuntos_full = [
        (path_pdf, os.path.basename(path_pdf) if path_pdf else "", "application", "pdf"),
        (path_comes, "dashboard_comestibles.html", "text", "html"),
        (path_tasca, "dashboard_tasca.html", "text", "html"),
    ]

    for email_dest in EMAILS_FULL:
        _enviar_mensaje(service, email_dest, asunto_full, html_full, adjuntos_full)

    if EMAILS_FULL:
        print(f"  Email completo enviado a: {', '.join(EMAILS_FULL)}")

    # ── EMAIL SOLO COMESTIBLES → EMAILS_COMES_ONLY ──
    if not EMAILS_COMES_ONLY:
        return

    link_comes = ""
    if url_comes:
        link_comes = (
            f'<div style="margin:16px 0;text-align:center">'
            f'<a href="{url_comes}" style="background:#2E7D32;color:white;'
            f'padding:10px 20px;border-radius:6px;text-decoration:none;'
            f'font-weight:bold;font-size:13px;display:inline-block">'
            f'Dashboard Comestibles</a></div>'
        )

    html_comes = f"""
    <html>
    <body style="font-family:Arial,sans-serif;font-size:14px;color:#333;max-width:600px;margin:0 auto">
      <div style="background:#0c0f0e;color:#a8e8c0;padding:20px;border-radius:8px 8px 0 0;text-align:center">
        <h2 style="margin:0;font-size:20px">Comestibles Barea</h2>
        <p style="margin:4px 0 0;color:#8aa898;font-size:12px">
          Cómo nos ha ido en {mes_nombre.lower()} {year_actual}</p>
      </div>
      <div style="background:#f8f9fa;padding:20px;border:1px solid #ddd">
        <h3 style="margin:0 0 12px;color:#2E7D32;font-size:16px">Resumen {mes_nombre}</h3>
        {comes_kpis}
        {link_comes}
        <div style="background:#e8f4fd;border:1px solid #bee5eb;border-radius:6px;
                    padding:10px 14px;margin:12px 0;font-size:12px;color:#0c5460">
          El informe detallado va adjunto en PDF. El dashboard interactivo
          se puede abrir en el navegador.
        </div>
      </div>
      <div style="padding:10px;font-size:10px;color:#999;text-align:center">
        Generado el {fecha_gen}
      </div>
    </body>
    </html>
    """

    asunto_comes = f"Comestibles Barea - Informe {mes_nombre} {year_actual}"
    adjuntos_comes = [
        (path_pdf_comes, os.path.basename(path_pdf_comes) if path_pdf_comes else "",
         "application", "pdf"),
        (path_comes, "dashboard_comestibles.html", "text", "html"),
    ]

    for email_dest in EMAILS_COMES_ONLY:
        _enviar_mensaje(service, email_dest, asunto_comes, html_comes, adjuntos_comes)

    print(f"  Email Comestibles enviado a: {', '.join(EMAILS_COMES_ONLY)}")


# ══════════════════════════════════════════════════════════════════════════════
# GITHUB PAGES (multi-file)
# ══════════════════════════════════════════════════════════════════════════════

def _generar_index_github_pages():
    """Genera el index.html landing page para GitHub Pages."""
    fecha = datetime.now().strftime("%d/%m/%Y %H:%M")
    return f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Barea · Dashboards</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box;}}
body{{background:#0f0e0c;color:#f0ece4;font-family:'Segoe UI',sans-serif;
      min-height:100vh;display:flex;flex-direction:column;align-items:center;
      justify-content:center;padding:40px 20px;}}
h1{{font-size:28px;color:#e8c97a;margin-bottom:8px;}}
.sub{{color:#9a9488;font-size:13px;margin-bottom:40px;}}
.cards{{display:flex;gap:24px;flex-wrap:wrap;justify-content:center;}}
.card{{background:#1a1916;border:1px solid #2e2c28;border-radius:12px;
       padding:32px 40px;text-align:center;text-decoration:none;
       transition:all .2s;min-width:240px;}}
.card:hover{{border-color:#c9a84c;transform:translateY(-2px);
             box-shadow:0 8px 24px rgba(0,0,0,.4);}}
.card h2{{font-size:18px;margin-bottom:6px;}}
.card p{{font-size:12px;color:#9a9488;}}
.card.tasca h2{{color:#e8c97a;}}
.card.comes h2{{color:#a8e8c0;}}
.footer{{margin-top:40px;font-size:11px;color:#5a5650;}}
</style>
</head>
<body>
  <h1>Barea</h1>
  <p class="sub">Dashboards de ventas</p>
  <div class="cards">
    <a href="tasca.html" class="card tasca">
      <h2>Tasca Barea</h2>
      <p>2023 – 2026</p>
    </a>
    <a href="comestibles.html" class="card comes">
      <h2>Comestibles Barea</h2>
      <p>2025 – 2026</p>
    </a>
  </div>
  <p class="footer">Actualizado: {fecha}</p>
</body>
</html>"""


def exportar_json_streamlit(D, MD, DIAS, RAW, PBM):
    """Exporta datos agregados como JSON para el puente Streamlit ↔ Netlify.

    Genera ficheros en un directorio temporal data/ que se incluirán en el
    ZIP de Netlify. Solo contiene datos agregados (sin CIFs, IBANs, etc.).
    """
    data_dir = os.path.join(tempfile.gettempdir(), "barea_streamlit_data", "data")
    os.makedirs(data_dir, exist_ok=True)

    # ── ventas_comes.json ──
    comes = {"años": {}, "woo": {}}
    for year in D:
        if year == "woo":
            # WooCommerce: euros y pedidos por mes
            for mes, val in D["woo"].items():
                comes["woo"][mes] = {
                    "euros": round(val.get("euros", 0), 2),
                    "pedidos": val.get("pedidos", 0)
                }
            continue
        y = D[year]
        comes["años"][year] = {"mensual": {}, "categorias": {}, "top_productos": {}, "margenes": {}}
        # Mensual
        for mes, val in y.get("mensual", {}).items():
            comes["años"][year]["mensual"][mes] = {
                "euros": round(val.get("euros", 0), 2),
                "unidades": round(val.get("unidades", 0), 1),
                "tickets": val.get("tickets", 0),
                "prom_ticket": round(val.get("prom_ticket", 0), 2)
            }
            # Categorías (% del mes)
            comes["años"][year]["categorias"][mes] = val.get("cats", {})
        # Top productos por mes (max 10 por categoría)
        for mes, cats in y.get("pbm", {}).items():
            top_mes = []
            for cat, productos in cats.items():
                for p in sorted(productos, key=lambda x: x.get("euros", 0), reverse=True)[:10]:
                    top_mes.append({"art": p["art"], "cat": cat,
                                    "euros": round(p.get("euros", 0), 2),
                                    "cant": round(p.get("cant", 0), 1)})
            comes["años"][year]["top_productos"][mes] = sorted(
                top_mes, key=lambda x: x["euros"], reverse=True)[:20]
        # Márgenes por categoría (de MD)
        if year in MD:
            for mes, val in MD[year].items():
                cats_margen = {}
                for cat, datos in val.get("cats", {}).items():
                    cats_margen[cat] = {
                        "euros": round(datos.get("euros", 0), 2),
                        "margen_pct": round(datos.get("margen_pct", 0), 1)
                    }
                comes["años"][year]["margenes"][mes] = cats_margen

    with open(os.path.join(data_dir, "ventas_comes.json"), "w", encoding="utf-8") as f:
        json.dump(comes, f, ensure_ascii=False, separators=(",", ":"), cls=_NumpyEncoder)
    print(f"  ventas_comes.json generado")

    # ── ventas_tasca.json ──
    tasca = {"años": {}, "dias_semana": {}}
    for year in RAW:
        r = RAW[year]
        tasca["años"][year] = {"mensual": {}, "categorias": {}, "top_productos": {}}
        for mes, val in r.get("mensual", {}).items():
            tasca["años"][year]["mensual"][mes] = {
                "euros": round(val.get("euros", 0), 2),
                "unidades": round(val.get("unidades", 0), 1),
                "tickets": val.get("tickets", 0),
                "prom_ticket": round(val.get("prom_ticket", 0), 2)
            }
        for mes, cats in r.get("categorias_mes", {}).items():
            tasca["años"][year]["categorias"][mes] = cats
        # Top productos de PBM
        if year in PBM:
            for mes, cats in PBM[year].items():
                top_mes = []
                for cat, productos in cats.items():
                    for p in sorted(productos, key=lambda x: x.get("euros", 0), reverse=True)[:10]:
                        top_mes.append({"art": p["art"], "cat": cat,
                                        "euros": round(p.get("euros", 0), 2),
                                        "cant": round(p.get("cant", 0), 1)})
                tasca["años"][year]["top_productos"][mes] = sorted(
                    top_mes, key=lambda x: x["euros"], reverse=True)[:20]
    # Días de la semana
    for year in DIAS:
        if year == "dias_nombres":
            continue
        tasca["dias_semana"][year] = {}
        for dia_idx, val in DIAS[year].items():
            if dia_idx == "heatmap":
                continue
            tasca["dias_semana"][year][str(dia_idx)] = {
                "euros": round(val.get("euros", 0), 2),
                "tickets": val.get("tickets", 0),
                "ticket_medio": round(val.get("ticket_medio", 0), 2)
            }

    with open(os.path.join(data_dir, "ventas_tasca.json"), "w", encoding="utf-8") as f:
        json.dump(tasca, f, ensure_ascii=False, separators=(",", ":"), cls=_NumpyEncoder)
    print(f"  ventas_tasca.json generado")

    # ── Copiar gmail_resumen.json y cuadre_resumen.json si existen ──
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    archivos_opcionales = [
        (os.path.join(base_dir, "outputs", "logs_gmail", "gmail_resumen.json"), "gmail.json"),
        (os.path.join(base_dir, "outputs", "cuadre_resumen.json"), "cuadre.json"),
    ]
    for src, dst in archivos_opcionales:
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(data_dir, dst))
            print(f"  {dst} copiado desde {os.path.basename(src)}")

    # ── monitor.json ──
    procesos = {}
    logs_gmail = os.path.join(base_dir, "outputs", "logs_gmail")
    logs_barea = os.path.join(base_dir, "outputs", "logs_barea")
    for nombre, directorio in [("gmail", logs_gmail), ("ventas", logs_barea)]:
        if os.path.isdir(directorio):
            auto_logs = sorted([f for f in os.listdir(directorio) if f.startswith("auto_") and f.endswith(".log")])
            if auto_logs:
                ultimo = auto_logs[-1]
                # Extraer fecha del nombre: auto_YYYY-MM-DD.log
                fecha_str = ultimo.replace("auto_", "").replace(".log", "")
                procesos[nombre] = {"ultima_ejecucion": fecha_str, "log": ultimo}
    # Cuadre: leer timestamp de cuadre_resumen.json si existe
    cuadre_json_path = os.path.join(base_dir, "outputs", "cuadre_resumen.json")
    if os.path.exists(cuadre_json_path):
        try:
            with open(cuadre_json_path, "r", encoding="utf-8") as f:
                cuadre_data = json.load(f)
            procesos["cuadre"] = {"ultima_ejecucion": cuadre_data.get("fecha_ejecucion", "")}
        except Exception:
            pass

    with open(os.path.join(data_dir, "monitor.json"), "w", encoding="utf-8") as f:
        json.dump({"procesos": procesos}, f, ensure_ascii=False, indent=2)
    print(f"  monitor.json generado")

    # ── meta.json ──
    from datetime import datetime as _dt
    archivos_presentes = [f for f in os.listdir(data_dir) if f.endswith(".json") and f != "meta.json"]
    meta = {
        "exportado": _dt.now().isoformat(timespec="seconds"),
        "version": "1.0",
        "archivos": sorted(archivos_presentes)
    }
    with open(os.path.join(data_dir, "meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    print(f"  meta.json generado ({len(archivos_presentes)} ficheros)")

    return os.path.dirname(data_dir)  # devuelve el dir padre que contiene data/


def publicar_github_pages(path_comes, path_tasca, data_dir=None):
    """Publica ambos dashboards en Netlify (reemplaza GitHub Pages)."""
    if not NETLIFY_TOKEN or not NETLIFY_SITE_ID:
        print("  Aviso: NETLIFY_TOKEN o NETLIFY_SITE_ID no configurados")
        return

    import zipfile
    import urllib.request

    try:
        # Crear zip con los 3 archivos
        tmp_zip = os.path.join(tempfile.gettempdir(), "barea_dashboards.zip")
        index_html = _generar_index_github_pages()

        with zipfile.ZipFile(tmp_zip, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.write(path_comes, "comestibles.html")
            zf.write(path_tasca, "tasca.html")
            zf.writestr("index.html", index_html)
            # Incluir JSON de datos para Streamlit
            if data_dir:
                json_dir = os.path.join(data_dir, "data")
                if os.path.isdir(json_dir):
                    for fname in os.listdir(json_dir):
                        if fname.endswith(".json"):
                            zf.write(os.path.join(json_dir, fname), f"data/{fname}")
                    print(f"  JSON incluidos en ZIP: {len(os.listdir(json_dir))} ficheros")

        # Subir a Netlify via API
        url = f"https://api.netlify.com/api/v1/sites/{NETLIFY_SITE_ID}/deploys"
        with open(tmp_zip, "rb") as f:
            data = f.read()

        req = urllib.request.Request(
            url, data=data, method="POST",
            headers={
                "Authorization": f"Bearer {NETLIFY_TOKEN}",
                "Content-Type": "application/zip",
            }
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            result = json.loads(resp.read())

        os.remove(tmp_zip)
        print(f"  Netlify actualizado: {NETLIFY_URL}")
        return result.get("deploy_ssl_url", NETLIFY_URL)

    except Exception as e:
        print(f"  Aviso Netlify: {e}")
    except Exception as e:
        print(f"  Aviso GitHub Pages: {e}")


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════

def main(abrir_navegador=True, solo_meses_cerrados=False, enviar_email=False):
    """Orquesta la generacion de ambos dashboards + PDF + email."""
    print("=" * 50)
    print("  GENERADOR DE DASHBOARDS BAREA")
    print("=" * 50)

    # ── 1. COMESTIBLES ──
    print("\n--- Comestibles ---")
    items, recibos, df_woo = cargar_datos()

    if solo_meses_cerrados:
        items, recibos, df_woo = _filtrar_meses_cerrados(items, recibos, df_woo)

    for year in YEAR_LIST:
        if year in items:
            print(f"  {year}: {len(items[year]):,} items")
        else:
            print(f"  {year}: sin datos")
    if df_woo is not None:
        print(f"  WooCommerce: {len(df_woo):,} pedidos")

    D = calcular_D(items, recibos, df_woo)
    MD = calcular_MD(items)
    DIAS = calcular_DIAS(items, recibos)
    path_comes = generar_html(D, MD, DIAS)

    # ── 2. TASCA ──
    print("\n--- Tasca ---")
    t_items, t_recibos = cargar_datos_tasca()

    if solo_meses_cerrados:
        t_items, t_recibos = _filtrar_meses_cerrados_tasca(t_items, t_recibos)

    for year in TASCA_YEAR_LIST:
        if year in t_items:
            print(f"  {year}: {len(t_items[year]):,} items")
        else:
            print(f"  {year}: sin datos")

    RAW = calcular_RAW(t_items, t_recibos)
    PBM = calcular_PBM_tasca(t_items)
    path_tasca = generar_html_tasca(RAW, PBM)

    # ── 3. JSON Streamlit + Netlify ──
    print("\n--- JSON Streamlit + Netlify ---")
    try:
        data_dir = exportar_json_streamlit(D, MD, DIAS, RAW, PBM)
    except Exception as e:
        print(f"  Error exportando JSON Streamlit: {e}")
        data_dir = None
    publicar_github_pages(path_comes, path_tasca, data_dir=data_dir)

    # ── 4. PDF + Email ──
    if enviar_email:
        print("\n--- PDF + Email ---")
        path_pdf = None
        path_pdf_comes = None

        try:
            path_pdf = generar_pdf_resumen(D, RAW, PBM, items, t_items)
        except Exception as e:
            print(f"  Error generando PDF completo: {e}")

        if EMAILS_COMES_ONLY:
            try:
                path_pdf_comes = generar_pdf_comestibles(D, items)
            except Exception as e:
                print(f"  Error generando PDF Comestibles: {e}")

        try:
            enviar_email_dashboard(D, RAW, path_comes, path_tasca,
                                   path_pdf, path_pdf_comes)
        except Exception as e:
            print(f"  Error enviando email: {e}")

    # ── 5. Abrir navegador ──
    if abrir_navegador:
        webbrowser.open("file:///" + path_comes.replace("\\", "/"))
        webbrowser.open("file:///" + path_tasca.replace("\\", "/"))
        print("\n  Abiertos en navegador")

    print("\n" + "=" * 50)
    print("  DASHBOARDS LISTOS")
    print("=" * 50)
    return path_comes, path_tasca


if __name__ == "__main__":
    import sys
    abrir = "--no-open" not in sys.argv
    cerrados = "--solo-cerrados" in sys.argv
    email = "--email" in sys.argv
    main(abrir_navegador=abrir, solo_meses_cerrados=cerrados, enviar_email=email)
