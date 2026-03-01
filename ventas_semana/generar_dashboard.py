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
    "QUESOS": "#e8c97a", "CHACINAS": "#e87e7e", "VINOS": "#9b4f8a",
    "CONSERVAS MAR": "#4a90d9", "CONSERVAS MONTAÑA": "#7ab87a",
    "CONSERVAS VEGETALES": "#5aaa7a", "ACEITES Y VINAGRES": "#c8a060",
    "APERITIVOS": "#e8734a", "DULCES": "#d470a0", "DESPENSA": "#8a9a7a",
    "BODEGA Y CERVEZAS": "#7a5a9a", "LICORES Y VERMÚS": "#c06070",
    "SALAZONES": "#6aa0b8", "SALSAS": "#a8c060", "EXPERIENCIAS": "#70d0c8",
    "BAZAR": "#9a8070", "BOCADILLOS": "#c89060", "CACHARRERIA": "#7a8090",
    "CUPÓN REGALO": "#d4a0d0", "OTROS COMESTIBLES": "#8a8a8a",
    "CONSERVAS": "#6090a8", "OTROS": "#7a7a7a",
}

MESES_FULL = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
              "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
MESES_CORTO = ["Ene", "Feb", "Mar", "Abr", "May", "Jun",
               "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]

# ── Configuracion email y GitHub Pages ────────────────────────────────────────
# Destinatarios: informe completo (Tasca + Comestibles)
EMAILS_FULL = [
    "REDACTED_EMAIL",
    "REDACTED_EMAIL",
    "jaimefermo@gmail.com",
]
# Destinatarios: solo Comestibles
EMAILS_COMES_ONLY = [
    "REDACTED_EMAIL",
]

GITHUB_PAGES_URL = "https://tascabarea.github.io/barea-dashboard/"
GITHUB_PAGES_REPO = os.path.expanduser("~/barea-dashboard")

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
        items[year] = df_i
        recibos[year] = df_r

    # ── Actual: 2026 ──
    try:
        df_i_26 = pd.read_excel(PATH_VENTAS, sheet_name="ComesItems")
        df_r_26 = pd.read_excel(PATH_VENTAS, sheet_name="ComesRecibos")
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

    if "status" in df.columns:
        df = df[df["status"].isin(["completed", "processing", "on-hold"])]

    df["fecha"] = pd.to_datetime(df["date_created"], errors="coerce")
    df = df[df["fecha"].dt.year == int(YEAR_LIST[-1])]
    df["mes"] = df["fecha"].dt.month

    for m in range(1, 13):
        dm = df[df["mes"] == m]
        if dm.empty:
            continue

        euros = _round(float(dm["total"].sum()))
        pedidos = len(dm)

        products = defaultdict(float)
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


def generar_html(D, MD):
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

    html = template
    html = html.replace("{{MD_DATA}}", md_json)
    html = html.replace("{{D_DATA}}", d_json)
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
    """Genera 3 PNGs con graficos de linea mejorados."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.ticker import FuncFormatter

    tmp_dir = tempfile.mkdtemp(prefix="barea_pdf_")
    fmt_euros = FuncFormatter(lambda x, _: f"{x:,.0f}€")

    plt.rcParams.update({
        'figure.facecolor': 'white',
        'axes.facecolor': '#F8F9FA',
        'axes.spines.top': False,
        'axes.spines.right': False,
        'grid.alpha': 0.25,
        'grid.color': '#CCCCCC',
        'font.size': 9,
    })

    tasca_colors = {"2023": "#A8C5E2", "2024": "#E8A0A0",
                    "2025": "#82D9A2", "2026": "#E8C97A"}
    comes_colors = {"2025": "#7EB5E8", "2026": "#82D9A2"}

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
            ax.plot(xs, vals, marker="o",
                    markersize=6 if is_cur else 3,
                    linewidth=2.5 if is_cur else 1.5,
                    label=yr, color=color,
                    alpha=1.0 if is_cur else 0.45,
                    zorder=3 if is_cur else 2)
            if is_cur:
                ax.fill_between(xs, vals, alpha=0.07, color=color)
                for x, v in zip(xs, vals):
                    ax.annotate(f"{v:,.0f}€", (x, v),
                                textcoords="offset points", xytext=(0, 10),
                                ha="center", fontsize=7, color=color,
                                fontweight="bold")
        ax.set_title(title, fontsize=12, fontweight="bold", pad=12,
                     color="#1a1a1a")
        ax.set_xticks(range(1, 13))
        ax.set_xticklabels(MESES_CORTO, fontsize=8)
        ax.yaxis.set_major_formatter(fmt_euros)
        ax.tick_params(axis="y", labelsize=8)
        ax.legend(fontsize=8, loc="upper right", framealpha=0.9,
                  edgecolor="#DDD")
        ax.set_xlim(0.5, 12.5)
        ax.grid(True, axis="y", alpha=0.25)
        for spine in ("bottom", "left"):
            ax.spines[spine].set_color("#CCCCCC")

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
        (f"Tasca {yr}", RAW, "#C9A84C", "o", 10),
        (f"Comestibles {yr}", D, "#4A9B6F", "s", -14),
    ]:
        mensual = data.get(yr, {}).get("mensual", {})
        xs, vs = [], []
        for m in range(1, 13):
            e = mensual.get(str(m), {}).get("euros", 0)
            if e and e > 0:
                xs.append(m)
                vs.append(e)
        if vs:
            ax3.plot(xs, vs, marker=mkr, markersize=6, linewidth=2.5,
                     label=lbl, color=color, zorder=3)
            ax3.fill_between(xs, vs, alpha=0.07, color=color)
            for x, v in zip(xs, vs):
                ax3.annotate(f"{v:,.0f}€", (x, v),
                             textcoords="offset points", xytext=(0, off_y),
                             ha="center", fontsize=7, color=color,
                             fontweight="bold")
    ax3.set_title(f"Comparativa Tasca vs Comestibles — {yr}",
                  fontsize=12, fontweight="bold", pad=12, color="#1a1a1a")
    ax3.set_xticks(range(1, 13))
    ax3.set_xticklabels(MESES_CORTO, fontsize=8)
    ax3.yaxis.set_major_formatter(fmt_euros)
    ax3.tick_params(axis="y", labelsize=8)
    ax3.legend(fontsize=8, loc="upper right", framealpha=0.9, edgecolor="#DDD")
    ax3.grid(True, axis="y", alpha=0.25)
    ax3.set_xlim(0.5, 12.5)
    for spine in ("top", "right"):
        ax3.spines[spine].set_visible(False)
    for spine in ("bottom", "left"):
        ax3.spines[spine].set_color("#CCCCCC")
    fig3.tight_layout(pad=1.5)
    path3 = os.path.join(tmp_dir, "chart_conjunto.png")
    fig3.savefig(path3, dpi=180, bbox_inches="tight")
    plt.close(fig3)

    plt.rcParams.update(plt.rcParamsDefault)
    return path1, path2, path3, tmp_dir


def _calcular_dia_fuerte(items_por_año, year, mes):
    """Devuelve el dia de la semana con mas ventas para un mes/año."""
    df_items = items_por_año.get(year)
    if df_items is None or df_items.empty:
        return "-"

    df = df_items.copy()
    df["Fecha"] = pd.to_datetime(df["Fecha"], errors="coerce")
    if "Estado" in df.columns:
        df = df[df["Estado"] != "Cancelado"]
    if "Tipo de recibo" in df.columns:
        df = df[df["Tipo de recibo"] == "Venta"]
    df = df[df["Fecha"].dt.month == mes]
    if df.empty:
        return "-"

    df["dia_semana"] = df["Fecha"].dt.dayofweek
    ventas_dia = df.groupby("dia_semana")["Ventas netas"].sum()
    if ventas_dia.empty:
        return "-"

    dias = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes",
            "Sábado", "Domingo"]
    mejor = ventas_dia.idxmax()
    return dias[int(mejor)]


def _top3_productos(pbm_data, mes):
    """Devuelve los top 3 productos del mes desde PBM."""
    mes_data = pbm_data.get(str(mes), {})
    all_prods = []
    for cat_prods in mes_data.values():
        all_prods.extend(cat_prods)
    all_prods.sort(key=lambda x: x.get("euros", 0), reverse=True)
    return [p["art"] for p in all_prods[:3]]


def _kpi_card(nombre, data_dict, year, mes, pbm_data, items_dict,
              color_accent, color_bg, font_name, font_bold):
    """Genera tabla-card de KPIs para un negocio."""
    from reportlab.lib.units import mm
    from reportlab.lib.colors import HexColor, white
    from reportlab.platypus import Table, TableStyle, Paragraph
    from reportlab.lib.styles import ParagraphStyle

    d_mes = data_dict.get(year, {}).get("mensual", {}).get(str(mes), {})
    euros = d_mes.get("euros", 0)
    tickets = d_mes.get("tickets", 0)
    prom = d_mes.get("prom_ticket", 0)

    year_ant = str(int(year) - 1)
    d_ant = data_dict.get(year_ant, {}).get("mensual", {}).get(str(mes), {})
    euros_ant = d_ant.get("euros", 0)
    if euros_ant > 0:
        var_pct = (euros - euros_ant) / euros_ant * 100
        var_color = "#2E7D32" if var_pct >= 0 else "#C62828"
        var_arrow = "▲" if var_pct >= 0 else "▼"
        var_html = (f'<font color="{var_color}"><b>'
                    f'{var_arrow} {var_pct:+.1f}%</b></font>')
    else:
        var_html = '<font color="#999">—</font>'

    top3 = _top3_productos(pbm_data, mes)
    dia = _calcular_dia_fuerte(items_dict, year, mes)

    uid = nombre.replace(" ", "_")
    s_hdr = ParagraphStyle(f"kc_h_{uid}", fontName=font_bold, fontSize=11,
                           textColor=white, leading=14)
    s_big = ParagraphStyle(f"kc_b_{uid}", fontName=font_bold, fontSize=24,
                           textColor=HexColor("#1a1a1a"), leading=28)
    s_var = ParagraphStyle(f"kc_v_{uid}", fontName=font_name, fontSize=10,
                           textColor=HexColor("#555"), leading=13)
    s_det = ParagraphStyle(f"kc_d_{uid}", fontName=font_name, fontSize=9,
                           textColor=HexColor("#444"), leading=13)

    card_w = 82 * mm
    rows = [
        [Paragraph(nombre, s_hdr)],
        [Paragraph(f"{euros:,.0f}€", s_big)],
        [Paragraph(f"vs año anterior: {var_html}", s_var)],
        [Paragraph(f"<b>{tickets}</b> tickets &nbsp;·&nbsp; "
                   f"<b>{prom:.2f}€</b> ticket medio", s_det)],
        [Paragraph(f"Día fuerte: <b>{dia}</b>", s_det)],
    ]
    if top3:
        items_html = "<br/>".join(f"&nbsp;&nbsp;· {p}" for p in top3)
        rows.append([Paragraph(f"Top productos:<br/>{items_html}", s_det)])

    t = Table(rows, colWidths=[card_w])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, 0), HexColor(color_accent)),
        ("BACKGROUND", (0, 1), (0, -1), HexColor(color_bg)),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 1), (0, 1), 10),
        ("BOTTOMPADDING", (0, 2), (0, 2), 2),
        ("BOX", (0, 0), (-1, -1), 1, HexColor(color_accent)),
        ("LINEBELOW", (0, 0), (0, 0), 1, HexColor(color_accent)),
    ]))
    return t


def _tabla_categorias_pdf(data_dict, year, mes, mes_nombre, color_header,
                          font_name, font_bold):
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
        rows.append([cat, f"{e_m:,.0f}€", f"{pct_m:.1f}%",
                     f"{e_ytd:,.0f}€", f"{p_ytd:.1f}%"])
    rows.append(["TOTAL", f"{euros_mes:,.0f}€", "100%",
                 f"{total_ytd:,.0f}€", "100%"])

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
        if i % 2 == 0:
            cmds.append(("BACKGROUND", (0, i), (-1, i), HexColor("#F7F8FA")))
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

    chart_tasca, chart_comes, chart_conjunto, tmp_dir = \
        _generar_graficos_pdf(D, RAW, mes_cerrado, year_actual)

    pdf_name = f"informe_barea_{mes_nombre.lower()}_{year_actual}.pdf"
    pdf_path = os.path.join(_SCRIPT_DIR, "dashboards", pdf_name)

    # ── Canvas callbacks ──
    def _on_first_page(canvas, doc):
        canvas.saveState()
        # Banda cabecera azul oscuro
        canvas.setFillColor(HexColor("#1B2A4A"))
        canvas.rect(0, H - 30*mm, W, 30*mm, fill=1, stroke=0)
        # Linea dorada
        canvas.setStrokeColor(HexColor("#C9A84C"))
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
        canvas.setStrokeColor(HexColor("#1B2A4A"))
        canvas.setLineWidth(1.5)
        canvas.line(15*mm, H - 10*mm, W - 15*mm, H - 10*mm)
        canvas.setFont(font_bold, 8)
        canvas.setFillColor(HexColor("#1B2A4A"))
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
        textColor=HexColor("#1B2A4A"), spaceBefore=4*mm, spaceAfter=3*mm)
    s_body = ParagraphStyle(
        "pr_b", fontName=font_name, fontSize=10,
        textColor=HexColor("#333"), leading=14)
    s_section = ParagraphStyle(
        "pr_s", fontName=font_bold, fontSize=11,
        textColor=HexColor("#1B2A4A"), spaceBefore=2*mm, spaceAfter=2*mm)

    # ── PAGINA 1: KPIs + Comparativa ──
    elements.append(Spacer(1, 20*mm))
    elements.append(Paragraph("Resumen del mes", s_heading))

    comes_pbm = D.get(year_actual, {}).get("pbm", {})
    card_t = _kpi_card("TASCA BAREA", RAW, year_actual, mes_cerrado,
                       PBM_tasca.get(year_actual, {}), tasca_items,
                       "#8B6914", "#FFF8E7", font_name, font_bold)
    card_c = _kpi_card("COMESTIBLES BAREA", D, year_actual, mes_cerrado,
                       comes_pbm, comes_items,
                       "#2E7D32", "#E8F5E9", font_name, font_bold)
    cards = Table([[card_t, "", card_c]], colWidths=[84*mm, 6*mm, 84*mm])
    cards.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    elements.append(cards)
    elements.append(Spacer(1, 6*mm))

    elements.append(Paragraph("Comparativa", s_heading))
    elements.append(Image(chart_conjunto, width=170*mm, height=62*mm))

    # ── PAGINA 2: Evolucion por negocio ──
    elements.append(PageBreak())
    elements.append(Paragraph(
        "Evolución de facturación", s_heading))
    elements.append(Spacer(1, 2*mm))
    elements.append(Image(chart_tasca, width=170*mm, height=65*mm))
    elements.append(Spacer(1, 8*mm))
    elements.append(Image(chart_comes, width=170*mm, height=65*mm))

    # ── PAGINA 3: Categorias ──
    elements.append(PageBreak())
    elements.append(Paragraph(
        f"Ventas por categoría — {mes_nombre} {year_actual}",
        s_heading))

    elements.append(Paragraph("Tasca Barea", ParagraphStyle(
        "pr_ct", parent=s_section, textColor=HexColor("#8B6914"))))
    elements.append(Spacer(1, 1*mm))
    elements.append(_tabla_categorias_pdf(
        RAW, year_actual, mes_cerrado, mes_nombre,
        "#8B6914", font_name, font_bold))
    elements.append(Spacer(1, 6*mm))

    elements.append(Paragraph("Comestibles Barea", ParagraphStyle(
        "pr_cc", parent=s_section, textColor=HexColor("#2E7D32"))))
    elements.append(Spacer(1, 1*mm))
    elements.append(_tabla_categorias_pdf(
        D, year_actual, mes_cerrado, mes_nombre,
        "#1F4E79", font_name, font_bold))
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
    fmt_euros = FuncFormatter(lambda x, _: f"{x:,.0f}€")
    comes_colors = {"2025": "#7EB5E8", "2026": "#82D9A2"}

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
        ax.plot(xs, vals, marker="o",
                markersize=6 if is_cur else 3,
                linewidth=2.5 if is_cur else 1.5,
                label=yr, color=color,
                alpha=1.0 if is_cur else 0.45,
                zorder=3 if is_cur else 2)
        if is_cur:
            ax.fill_between(xs, vals, alpha=0.07, color=color)
            for x, v in zip(xs, vals):
                ax.annotate(f"{v:,.0f}€", (x, v),
                            textcoords="offset points", xytext=(0, 10),
                            ha="center", fontsize=7, color=color,
                            fontweight="bold")
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
        canvas.setFillColor(HexColor("#1B5E20"))
        canvas.rect(0, H - 30*mm, W, 30*mm, fill=1, stroke=0)
        canvas.setStrokeColor(HexColor("#81C784"))
        canvas.setLineWidth(2)
        canvas.line(0, H - 30*mm, W, H - 30*mm)
        canvas.setFillColor(white)
        canvas.setFont(font_bold, 18)
        canvas.drawCentredString(W / 2, H - 15*mm, "Comestibles Barea")
        canvas.setFont(font_name, 13)
        canvas.setFillColor(HexColor("#A5D6A7"))
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
        canvas.setStrokeColor(HexColor("#2E7D32"))
        canvas.setLineWidth(1.5)
        canvas.line(15*mm, H - 10*mm, W - 15*mm, H - 10*mm)
        canvas.setFont(font_bold, 8)
        canvas.setFillColor(HexColor("#2E7D32"))
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
        textColor=HexColor("#1B5E20"), spaceBefore=4*mm, spaceAfter=3*mm)
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
    d_ant = D.get(year_ant, {}).get("mensual", {}).get(
        str(mes_cerrado), {})
    euros_ant = d_ant.get("euros", 0)
    if euros_ant > 0:
        var_pct = (euros - euros_ant) / euros_ant * 100
        var_color = "#2E7D32" if var_pct >= 0 else "#C62828"
        var_arrow = "▲" if var_pct >= 0 else "▼"
        var_html = (f'<font color="{var_color}"><b>'
                    f'{var_arrow} {var_pct:+.1f}%</b></font>')
    else:
        var_html = '<font color="#999">—</font>'

    comes_pbm = D.get(year_actual, {}).get("pbm", {})
    top3 = _top3_productos(comes_pbm, mes_cerrado)
    dia = _calcular_dia_fuerte(comes_items, year_actual, mes_cerrado)

    s_big = ParagraphStyle("pc_big", fontName=font_bold, fontSize=28,
                           textColor=HexColor("#1a1a1a"), leading=32)
    s_var = ParagraphStyle("pc_var", fontName=font_name, fontSize=11,
                           textColor=HexColor("#555"), leading=14)

    kpi_rows = [
        [Paragraph(f"{euros:,.0f}€", s_big),
         Paragraph(f"vs año anterior: {var_html}", s_var)],
        [Paragraph(
            f"<b>{tickets}</b> tickets &nbsp;·&nbsp; "
            f"<b>{prom:.2f}€</b> ticket medio &nbsp;·&nbsp; "
            f"Día fuerte: <b>{dia}</b>", s_det), ""],
    ]
    if top3:
        items_str = " &nbsp;·&nbsp; ".join(top3)
        kpi_rows.append([Paragraph(
            f"Top productos: <b>{items_str}</b>", s_det), ""])

    kpi_t = Table(kpi_rows, colWidths=[100*mm, 70*mm])
    kpi_t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BACKGROUND", (0, 0), (-1, -1), HexColor("#E8F5E9")),
        ("BOX", (0, 0), (-1, -1), 1, HexColor("#2E7D32")),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
    ]))
    elements.append(kpi_t)
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
        "#1F4E79", font_name, font_bold))
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
              <div style="font-size:20px;font-weight:bold;color:{color}">{euros:,.0f}€</div>
            </td>
            <td style="padding:10px;background:white;border:1px solid #eee;text-align:center;width:33%">
              <div style="font-size:10px;color:#888;text-transform:uppercase">Tickets</div>
              <div style="font-size:20px;font-weight:bold;color:{color}">{tickets:,}</div>
            </td>
            <td style="padding:10px;background:white;border:1px solid #eee;text-align:center;width:33%">
              <div style="font-size:10px;color:#888;text-transform:uppercase">Ticket medio</div>
              <div style="font-size:20px;font-weight:bold;color:{color}">{prom:.2f}€</div>
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


def publicar_github_pages(path_comes, path_tasca):
    """Publica ambos dashboards + index en GitHub Pages."""
    if not GITHUB_PAGES_REPO:
        return

    if not os.path.isdir(GITHUB_PAGES_REPO):
        print(f"  Aviso: repo GitHub Pages no encontrado: {GITHUB_PAGES_REPO}")
        return

    try:
        # Copiar dashboards
        shutil.copy2(path_comes, os.path.join(GITHUB_PAGES_REPO, "comestibles.html"))
        shutil.copy2(path_tasca, os.path.join(GITHUB_PAGES_REPO, "tasca.html"))

        # Generar index
        index_html = _generar_index_github_pages()
        with open(os.path.join(GITHUB_PAGES_REPO, "index.html"), "w", encoding="utf-8") as f:
            f.write(index_html)

        fecha = datetime.now().strftime("%Y-%m-%d %H:%M")
        subprocess.run(
            ["git", "add", "."],
            cwd=GITHUB_PAGES_REPO, check=True, capture_output=True,
        )
        subprocess.run(
            ["git", "commit", "-m", f"Dashboards {fecha}"],
            cwd=GITHUB_PAGES_REPO, check=True, capture_output=True,
        )
        subprocess.run(
            ["git", "push"],
            cwd=GITHUB_PAGES_REPO, check=True, capture_output=True,
        )
        print(f"  GitHub Pages actualizado: {GITHUB_PAGES_URL}")
    except subprocess.CalledProcessError as e:
        stderr = e.stderr.decode(errors="replace") if e.stderr else ""
        if "nothing to commit" in stderr:
            print("  GitHub Pages: sin cambios")
        else:
            print(f"  Aviso GitHub Pages: {stderr[:200]}")
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
    path_comes = generar_html(D, MD)

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

    # ── 3. GitHub Pages ──
    print("\n--- GitHub Pages ---")
    publicar_github_pages(path_comes, path_tasca)

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
