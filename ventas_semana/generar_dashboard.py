"""
Generador de Dashboard Comestibles Barea.

Lee datos de ventas (Loyverse + WooCommerce) desde los Excel,
calcula las estructuras D y MD, e inyecta los JSON en el template HTML.

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
import webbrowser
from collections import defaultdict
from datetime import datetime
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email import encoders

import pandas as pd

# ── Rutas ─────────────────────────────────────────────────────────────────────
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_SCRIPT_DIR)

PATH_VENTAS = os.path.join(_ROOT, "datos", "Ventas Barea 2026.xlsx")
PATH_HISTORICO = os.path.join(_ROOT, "datos", "Ventas Barea Historico.xlsx")
PATH_TEMPLATE = os.path.join(_SCRIPT_DIR, "dashboards", "dashboard_comes_template.html")
PATH_OUTPUT = os.path.join(_SCRIPT_DIR, "dashboards", "dashboard_comes.html")

# Años a incluir
YEAR_LIST = ["2024", "2025", "2026"]

# Colores por categoría (fijo, igual que en el dashboard original)
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

# ── Configuracion email y GitHub Pages ────────────────────────────────────────
# Destinatarios del email (anadir socios cuando se quiera)
EMAILS_DASHBOARD = [
    "REDACTED_EMAIL",
    "REDACTED_EMAIL",
    "jaimefermo@gmail.com",
    "REDACTED_EMAIL",
]

# URL publica del dashboard en GitHub Pages
GITHUB_PAGES_URL = "https://tascabarea.github.io/barea-dashboard/"

# Ruta local del repo de GitHub Pages
GITHUB_PAGES_REPO = os.path.expanduser("~/barea-dashboard")

# Rutas Gmail (relativas al proyecto)
_GMAIL_DIR = os.path.join(_ROOT, "gmail")
_GMAIL_CREDENTIALS = os.path.join(_GMAIL_DIR, "credentials.json")
_GMAIL_TOKEN = os.path.join(_GMAIL_DIR, "token.json")


# ── Utilidades ────────────────────────────────────────────────────────────────
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


# ── Carga de datos ────────────────────────────────────────────────────────────
def cargar_datos():
    """Lee los Excel y devuelve (items_por_año, recibos_por_año, df_woo)."""
    items = {}
    recibos = {}

    # ── Histórico: 2024 y 2025 ──
    for year, sheet_items, sheet_recibos in [
        ("2024", "ComestiblesItem24", "ComestiblesRecibos24"),
        ("2025", "ComestiblesItems25", "ComestiblesRecibos25"),
    ]:
        try:
            df_i = pd.read_excel(PATH_HISTORICO, sheet_name=sheet_items)
            df_r = pd.read_excel(PATH_HISTORICO, sheet_name=sheet_recibos)
        except Exception as e:
            print(f"  Aviso: no se pudo leer {sheet_items}/{sheet_recibos}: {e}")
            continue

        # Normalizar columnas (Historico puede tener "Numero de recibo")
        df_i.rename(columns={
            "Numero de recibo": "Número de recibo",
            "Articulo": "Artículo",
        }, inplace=True)
        df_r.rename(columns={
            "Numero de recibo": "Número de recibo",
        }, inplace=True)

        # Convertir numerics
        for col in ["Cantidad", "Ventas brutas", "Descuentos", "Ventas netas",
                     "Costo de los bienes", "Beneficio bruto", "Impuestos"]:
            if col in df_i.columns:
                df_i[col] = df_i[col].apply(_to_float)
        for col in ["Ventas brutas", "Descuentos", "Ventas netas",
                     "Costo de los bienes", "Beneficio bruto"]:
            if col in df_r.columns:
                df_r[col] = df_r[col].apply(_to_float)

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


# ── Cálculo de D ──────────────────────────────────────────────────────────────
def calcular_D(items_por_año, recibos_por_año, df_woo):
    """
    Genera la estructura D:
    D[year].mensual[month] = {euros, unidades, tickets, prom_ticket, cats:{cat: %}}
    D[year].pbm[month][cat] = [{art, euros, cant}]
    D[year].cats_total = {cat: pct_total}
    D[year].cats_euros = {cat: total_euros}
    D[year].cats = [sorted cat names]
    D[year].rotation = [{art, cat, euros, cant, meses, avail, rot}]
    D.woo[month] = {euros, pedidos, products:{name: euros}}
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
            # Filtrar solo ventas (no reembolsos cancelados)
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

                # Tickets: contar recibos únicos de este mes
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

                # Categorías: % de ventas
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
                    "tickets": tickets,
                    "prom_ticket": _round(prom_ticket, 2),
                    "cats": cats_pct,
                }

                # PBM: productos por mes y categoría
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

        # cats_total: % de cada categoría sobre el total del año
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

        # rotation: productos con su rotación
        rotation = _calcular_rotation(df_items, year)

        D[year] = {
            "mensual": mensual,
            "pbm": pbm,
            "rotation": rotation,
            "cats_total": cats_total,
            "cats_euros": cats_euros_dict,
            "cats": sorted(cats_total.keys()),
        }

    # WooCommerce
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

    # Meses disponibles (con datos)
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

    # Filtrar solo pedidos válidos (no cancelados, no reembolsados)
    if "status" in df.columns:
        df = df[df["status"].isin(["completed", "processing", "on-hold"])]

    # Parsear fecha y filtrar solo año actual (2026)
    df["fecha"] = pd.to_datetime(df["date_created"], errors="coerce")
    df = df[df["fecha"].dt.year == int(YEAR_LIST[-1])]
    df["mes"] = df["fecha"].dt.month

    for m in range(1, 13):
        dm = df[df["mes"] == m]
        if dm.empty:
            continue

        euros = _round(float(dm["total"].sum()))
        pedidos = len(dm)

        # Productos: parsear line_items
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


# ── Cálculo de MD ─────────────────────────────────────────────────────────────
def calcular_MD(items_por_año):
    """
    Genera la estructura MD:
    MD[year][month].cats[cat] = {euros, coste, margen, margen_pct, desc}
    MD[year][month].products = [{art, cat, euros, coste, margen, margen_pct, desc, cant}]
    """
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

        # Asegurar columnas numéricas
        for col in ["Ventas netas", "Costo de los bienes", "Descuentos", "Cantidad"]:
            if col in df.columns:
                df[col] = df[col].apply(_to_float)

        for m in range(1, 13):
            dm = df[df["mes"] == m]
            if dm.empty:
                continue

            # Categorías
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

            # Productos
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


# ── Generación HTML ───────────────────────────────────────────────────────────
def generar_html(D, MD):
    """Lee el template y sustituye los placeholders con los datos calculados."""
    with open(PATH_TEMPLATE, "r", encoding="utf-8") as f:
        template = f.read()

    # Años con datos
    years_with_data = [y for y in YEAR_LIST if any(
        D[y]["mensual"][str(m)]["tickets"] > 0 for m in range(1, 13)
    )]

    first_year = years_with_data[0] if years_with_data else YEAR_LIST[0]
    last_year = years_with_data[-1] if years_with_data else YEAR_LIST[-1]
    subtitle = f"{first_year}\u2013{last_year}"

    fecha_act = datetime.now().strftime("%d/%m/%Y")

    # Serializar JSON (compacto, sin espacios innecesarios)
    md_json = json.dumps(MD, ensure_ascii=False, separators=(",", ":"))
    d_json = json.dumps(D, ensure_ascii=False, separators=(",", ":"))
    years_json = json.dumps(years_with_data)

    # CAT_COLORS: incluir solo categorías que existen en los datos
    all_cats = set()
    for year in YEAR_LIST:
        all_cats.update(D[year].get("cats", []))
    cat_colors_filtered = {k: v for k, v in CAT_COLORS.items() if k in all_cats}
    # Añadir colores genéricos para categorías nuevas no contempladas
    _extra_colors = [
        "#7a9a6a", "#9a6a7a", "#6a7a9a", "#b0906a", "#6ab09a",
        "#9a6ab0", "#b06a6a", "#6a9ab0", "#b0b06a", "#6ab0b0",
    ]
    idx = 0
    for cat in sorted(all_cats):
        if cat not in cat_colors_filtered:
            cat_colors_filtered[cat] = _extra_colors[idx % len(_extra_colors)]
            idx += 1

    cc_json = json.dumps(cat_colors_filtered, ensure_ascii=False, separators=(",", ":"))

    # Sustituir placeholders
    html = template
    html = html.replace("{{MD_DATA}}", md_json)
    html = html.replace("{{D_DATA}}", d_json)
    html = html.replace("{{YEARS_DATA}}", years_json)
    html = html.replace("{{CAT_COLORS_DATA}}", cc_json)
    html = html.replace("{{SUBTITLE_YEARS}}", subtitle)
    html = html.replace("{{FECHA_ACT}}", fecha_act)

    with open(PATH_OUTPUT, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"  Dashboard generado: {PATH_OUTPUT}")
    print(f"  {len(html):,} bytes, {len(html.splitlines())} líneas")

    return PATH_OUTPUT


# ── Filtrado meses cerrados ───────────────────────────────────────────────────
def _filtrar_meses_cerrados(items, recibos, df_woo):
    """Excluye datos del mes en curso del ano actual."""
    mes_actual = datetime.now().month
    year_actual = YEAR_LIST[-1]  # "2026"

    if year_actual in items and items[year_actual] is not None:
        df = items[year_actual]
        df["Fecha"] = pd.to_datetime(df["Fecha"], errors="coerce")
        items[year_actual] = df[df["Fecha"].dt.month < mes_actual]
        print(f"  Filtro meses cerrados: {year_actual} hasta mes {mes_actual - 1} "
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


# ── Email con Gmail API ──────────────────────────────────────────────────────
def enviar_email_dashboard(D, path_html):
    """Envia email con resumen de KPIs del ultimo mes cerrado + dashboard adjunto."""
    try:
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
        from googleapiclient.discovery import build
    except ImportError:
        print("  Aviso: google-auth/google-api-python-client no instalados, "
              "no se puede enviar email")
        return

    if not os.path.exists(_GMAIL_TOKEN):
        print("  Aviso: no existe token.json de Gmail, no se puede enviar email")
        return

    # Conectar Gmail API
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
            print("  Aviso: credenciales Gmail expiradas, no se puede enviar email")
            return

    service = build("gmail", "v1", credentials=creds)

    # Determinar ultimo mes cerrado
    year_actual = YEAR_LIST[-1]
    mes_cerrado = datetime.now().month - 1
    if mes_cerrado < 1:
        mes_cerrado = 12
        year_actual = str(int(year_actual) - 1)

    mes_nombre = MESES_FULL[mes_cerrado - 1]

    # KPIs del mes cerrado
    d_mes = D[year_actual]["mensual"].get(str(mes_cerrado), {})
    euros = d_mes.get("euros", 0)
    tickets = d_mes.get("tickets", 0)
    prom = d_mes.get("prom_ticket", 0)

    # Top categoria
    cats = d_mes.get("cats", {})
    top_cat = max(cats, key=cats.get) if cats else "-"
    top_pct = cats.get(top_cat, 0) if cats else 0

    # Comparativa con ano anterior
    year_ant = str(int(year_actual) - 1)
    cmp_html = ""
    if year_ant in D:
        d_ant = D[year_ant]["mensual"].get(str(mes_cerrado), {})
        euros_ant = d_ant.get("euros", 0)
        if euros_ant > 0:
            var = (euros - euros_ant) / euros_ant * 100
            signo = "+" if var >= 0 else ""
            color = "#155724" if var >= 0 else "#721C24"
            bg = "#D4EDDA" if var >= 0 else "#F8D7DA"
            cmp_html = (
                f'<div style="background:{bg};color:{color};padding:10px 16px;'
                f'border-radius:6px;margin:12px 0;font-size:14px">'
                f'vs {mes_nombre} {year_ant}: {signo}{var:.1f}% '
                f'({euros_ant:,.0f}e)</div>'
            )

    # Acceso al dashboard
    if GITHUB_PAGES_URL:
        acceso_html = (
            f'<div style="margin:16px 0;text-align:center">'
            f'<a href="{GITHUB_PAGES_URL}" style="background:#1F4E79;color:white;'
            f'padding:12px 24px;border-radius:6px;text-decoration:none;'
            f'font-weight:bold;font-size:14px;display:inline-block">'
            f'Abrir Dashboard online</a></div>'
        )
    else:
        acceso_html = (
            '<div style="background:#e8f4fd;border:1px solid #bee5eb;'
            'border-radius:6px;padding:12px 16px;margin:16px 0;font-size:13px;'
            'color:#0c5460">'
            '<strong>Dashboard adjunto</strong> - '
            'Descarga el archivo <em>dashboard_comes.html</em> y abrelo en '
            'el navegador (Chrome, Safari, etc.) para ver el dashboard interactivo '
            'con todas las pestanas.'
            '</div>'
        )

    html = f"""
    <html>
    <body style="font-family:Arial,sans-serif;font-size:14px;color:#333;max-width:600px;margin:0 auto">
      <div style="background:#0c0f0e;color:#a8e8c0;padding:20px;border-radius:8px 8px 0 0">
        <h2 style="margin:0;font-size:20px">Comestibles Barea</h2>
        <p style="margin:4px 0 0;color:#8aa898;font-size:12px">
          Dashboard actualizado - {mes_nombre} {year_actual}</p>
      </div>
      <div style="background:#f8f9fa;padding:20px;border:1px solid #ddd">
        <h3 style="margin:0 0 16px;color:#1F4E79">Resumen {mes_nombre} {year_actual}</h3>
        <table style="width:100%;border-collapse:collapse">
          <tr>
            <td style="padding:12px;background:white;border:1px solid #eee;border-radius:4px;text-align:center;width:25%">
              <div style="font-size:11px;color:#888;text-transform:uppercase">Ventas</div>
              <div style="font-size:22px;font-weight:bold;color:#1F4E79">{euros:,.0f}e</div>
            </td>
            <td style="padding:12px;background:white;border:1px solid #eee;border-radius:4px;text-align:center;width:25%">
              <div style="font-size:11px;color:#888;text-transform:uppercase">Tickets</div>
              <div style="font-size:22px;font-weight:bold;color:#1F4E79">{tickets:,}</div>
            </td>
            <td style="padding:12px;background:white;border:1px solid #eee;border-radius:4px;text-align:center;width:25%">
              <div style="font-size:11px;color:#888;text-transform:uppercase">Ticket medio</div>
              <div style="font-size:22px;font-weight:bold;color:#1F4E79">{prom:.2f}e</div>
            </td>
            <td style="padding:12px;background:white;border:1px solid #eee;border-radius:4px;text-align:center;width:25%">
              <div style="font-size:11px;color:#888;text-transform:uppercase">Top cat.</div>
              <div style="font-size:16px;font-weight:bold;color:#1F4E79">{top_cat}</div>
              <div style="font-size:11px;color:#888">{top_pct}%</div>
            </td>
          </tr>
        </table>
        {cmp_html}
        {acceso_html}
      </div>
      <div style="padding:12px;font-size:11px;color:#999;text-align:center">
        Generado el {datetime.now().strftime('%d/%m/%Y %H:%M')}
      </div>
    </body>
    </html>
    """

    asunto = f"Comestibles Barea - Dashboard {mes_nombre} {year_actual}"

    for email_dest in EMAILS_DASHBOARD:
        message = MIMEMultipart("mixed")
        message["To"] = email_dest
        message["Subject"] = asunto
        message.attach(MIMEText(html, "html"))

        # Adjuntar el dashboard HTML
        with open(path_html, "rb") as f:
            adjunto = MIMEBase("text", "html")
            adjunto.set_payload(f.read())
            encoders.encode_base64(adjunto)
            adjunto.add_header(
                "Content-Disposition", "attachment",
                filename="dashboard_comes.html",
            )
            message.attach(adjunto)

        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
        service.users().messages().send(
            userId="me", body={"raw": raw}
        ).execute()

    print(f"  Email enviado a: {', '.join(EMAILS_DASHBOARD)}")


# ── GitHub Pages ──────────────────────────────────────────────────────────────
def publicar_github_pages(path_html):
    """Copia el dashboard al repo de GitHub Pages y hace push."""
    if not GITHUB_PAGES_REPO:
        return

    if not os.path.isdir(GITHUB_PAGES_REPO):
        print(f"  Aviso: repo GitHub Pages no encontrado: {GITHUB_PAGES_REPO}")
        return

    try:
        dest = os.path.join(GITHUB_PAGES_REPO, "index.html")
        shutil.copy2(path_html, dest)

        fecha = datetime.now().strftime("%Y-%m-%d %H:%M")
        subprocess.run(
            ["git", "add", "."],
            cwd=GITHUB_PAGES_REPO, check=True, capture_output=True,
        )
        subprocess.run(
            ["git", "commit", "-m", f"Dashboard {fecha}"],
            cwd=GITHUB_PAGES_REPO, check=True, capture_output=True,
        )
        subprocess.run(
            ["git", "push"],
            cwd=GITHUB_PAGES_REPO, check=True, capture_output=True,
        )
        print(f"  GitHub Pages actualizado: {GITHUB_PAGES_URL or GITHUB_PAGES_REPO}")
    except subprocess.CalledProcessError as e:
        stderr = e.stderr.decode(errors="replace") if e.stderr else ""
        if "nothing to commit" in stderr:
            print("  GitHub Pages: sin cambios")
        else:
            print(f"  Aviso GitHub Pages: {stderr[:200]}")
    except Exception as e:
        print(f"  Aviso GitHub Pages: {e}")


# ── Main ──────────────────────────────────────────────────────────────────────
def main(abrir_navegador=True, solo_meses_cerrados=False, enviar_email=False):
    """Orquesta la generacion completa del dashboard."""
    print("--- Generando Dashboard Comestibles ---")

    items, recibos, df_woo = cargar_datos()

    # Filtrar meses cerrados si se pide
    if solo_meses_cerrados:
        items, recibos, df_woo = _filtrar_meses_cerrados(items, recibos, df_woo)

    # Resumen de datos cargados
    for year in YEAR_LIST:
        if year in items:
            n = len(items[year])
            print(f"  {year}: {n:,} items")
        else:
            print(f"  {year}: sin datos")
    if df_woo is not None:
        print(f"  WooCommerce: {len(df_woo):,} pedidos")

    D = calcular_D(items, recibos, df_woo)
    MD = calcular_MD(items)
    path = generar_html(D, MD)

    # GitHub Pages
    publicar_github_pages(path)

    # Email
    if enviar_email:
        try:
            enviar_email_dashboard(D, path)
        except Exception as e:
            print(f"  Error enviando email: {e}")

    if abrir_navegador:
        webbrowser.open("file:///" + path.replace("\\", "/"))
        print("  Abierto en navegador")

    print("--- Dashboard listo ---")
    return path


if __name__ == "__main__":
    import sys
    abrir = "--no-open" not in sys.argv
    cerrados = "--solo-cerrados" in sys.argv
    email = "--email" in sys.argv
    main(abrir_navegador=abrir, solo_meses_cerrados=cerrados, enviar_email=email)
