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

import json
import os
import re
import sys
import webbrowser
from collections import defaultdict
from datetime import datetime

import numpy as np
import pandas as pd

from nucleo.utils import (
    to_float, round_safe, fmt_eur, clean_html,
    NumpyEncoder, json_dumps,
    MESES as _MESES_SHARED, MESES_FULL as _MESES_FULL_SHARED,
)
from ventas_semana.email_sender import enviar_email_dashboard
from ventas_semana.netlify_publisher import exportar_json_streamlit, publicar_github_pages
from ventas_semana.pdf_generator import generar_pdf_resumen, generar_pdf_comestibles

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

MESES_FULL = _MESES_FULL_SHARED
MESES_CORTO = _MESES_SHARED

# Meses con apertura parcial (no comparables) — 8 = Agosto
MESES_PARCIALES = [8]

# ── Configuracion email y Netlify ─────────────────────────────────────────────
try:
    from config.datos_sensibles import EMAILS_COMES_ONLY
except ImportError:
    EMAILS_COMES_ONLY = []



# Aliases locales para brevedad en templates HTML
_to_float = to_float
_clean_html = clean_html
_round = round_safe
_fmt_eur = fmt_eur
_json_dumps = json_dumps


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


def _preparar_df(df):
    """Filtra DataFrame de ventas: parsea fechas, excluye cancelados, solo ventas."""
    df = df.copy()
    df["Fecha"] = pd.to_datetime(df["Fecha"], errors="coerce")
    if "Estado" in df.columns:
        df = df[df["Estado"] != "Cancelado"]
    if "Tipo de recibo" in df.columns:
        df = df[df["Tipo de recibo"] == "Venta"]
    df["mes"] = df["Fecha"].dt.month
    return df


def _calcular_mensual_base(df_items, df_recibos):
    """Calcula métricas mensuales base: euros, unidades, tickets, prom_ticket, cats_pct.

    Devuelve dict {str(mes): {euros, unidades, tickets, prom_ticket, cats}}.
    Compartido entre Comestibles (calcular_D) y Tasca (calcular_RAW).
    """
    mensual = {}
    for m in range(1, 13):
        mensual[str(m)] = {"euros": 0, "unidades": 0, "tickets": 0,
                           "prom_ticket": 0, "cats": {}}

    if df_items is None or df_items.empty:
        return mensual

    df = _preparar_df(df_items)
    dr = _preparar_df(df_recibos) if df_recibos is not None and not df_recibos.empty else None

    for m in range(1, 13):
        dm = df[df["mes"] == m]
        if dm.empty:
            continue

        euros = _round(dm["Ventas netas"].sum())
        unidades = _round(dm["Cantidad"].sum())

        if dr is not None:
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

    return mensual


def _calcular_pbm(df_items):
    """Calcula productos por mes/categoría: pbm[month][cat] = [{art, euros, cant}].

    Compartido entre Comestibles (calcular_D) y Tasca (calcular_PBM_tasca).
    """
    pbm = {str(m): {} for m in range(1, 13)}

    if df_items is None or df_items.empty:
        return pbm

    df = _preparar_df(df_items)

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
            ).reset_index().sort_values("euros", ascending=False)
            pbm[str(m)][cat] = [
                {"art": row["Artículo"], "euros": _round(row["euros"]),
                 "cant": _round(row["cant"], 2)}
                for _, row in art_agg.iterrows()
                if row["euros"] > 0
            ]

    return pbm


def _calcular_cats_year(mensual):
    """Calcula cats_total y cats_euros a nivel año desde datos mensuales."""
    total_year = sum(mensual[str(m)]["euros"] for m in range(1, 13))
    cats_euros_year = defaultdict(float)
    for m in range(1, 13):
        cats = mensual[str(m)].get("cats", {})
        m_euros = mensual[str(m)]["euros"]
        for cat, pct in cats.items():
            cats_euros_year[cat] += pct / 100 * m_euros

    cats_total = {}
    if total_year > 0:
        for cat, val in cats_euros_year.items():
            cats_total[cat] = _round(val / total_year * 100, 1)

    cats_euros_dict = {cat: _round(val) for cat, val in cats_euros_year.items()}
    return cats_total, cats_euros_dict


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

        mensual = _calcular_mensual_base(df_items, df_recibos)
        pbm = _calcular_pbm(df_items)
        cats_total, cats_euros_dict = _calcular_cats_year(mensual)
        rotation = _calcular_rotation(df_items, year)

        D[year] = {
            "mensual": mensual,
            "pbm": pbm,
            "rotation": rotation,
            "cats_total": cats_total,
            "cats_euros": cats_euros_dict,
            "cats": sorted(cats_total.keys()),
        }

    # Agrupar categorias pequeñas en "OTROS"
    for year in YEAR_LIST:
        if year in D:
            _agrupar_otros(D[year])

    D["woo"] = _calcular_woo(df_woo)

    # WooCommerce reclasificado por fecha de celebración (devengo)
    woo_devengo = _calcular_woo_devengo(df_woo)
    for year in YEAR_LIST:
        D[year]["woo_devengo"] = woo_devengo.get(year, {
            str(m): {"euros": 0, "pedidos": 0, "products": {}} for m in range(1, 13)
        })

    return D


def _calcular_rotation(df_items, year):
    """Calcula rotación de productos para un año."""
    if df_items is None or df_items.empty:
        return []

    df = _preparar_df(df_items)

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

    # Compatibilidad: total puede ser float (API) o string con coma (Excel limpio).
    # Nota: usar is_numeric_dtype — pandas 3.x reporta strings como dtype 'str', no 'object'.
    if pd.api.types.is_numeric_dtype(df["total"]):
        df["_total"] = df["total"].fillna(0)
    else:
        df["_total"] = pd.to_numeric(
            df["total"].astype(str)
                       .str.replace("€", "", regex=False)
                       .str.replace(" ", "", regex=False)
                       .str.replace("\u00a0", "", regex=False)
                       .str.replace(".", "", regex=False)
                       .str.replace(",", ".", regex=False),
            errors="coerce"
        ).fillna(0)

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
                        items_list = json.loads(line_items_raw)
                    else:
                        items_list = line_items_raw
                    if isinstance(items_list, list):
                        for item in items_list:
                            name = _clean_html(item.get("name", ""))
                            total_item = float(item.get("total", 0) or 0)
                            if name and total_item > 0:
                                products[name] += total_item
                except (ValueError, json.JSONDecodeError, TypeError):
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


# ── WooCommerce devengo (por fecha de celebración) ──────────────────────────

_MESES_ES = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
    "julio": 7, "agosto": 8, "septiembre": 9, "octubre": 10, "noviembre": 11,
    "diciembre": 12,
}

_RE_REGALA = re.compile(r"regala\s+talleres", re.IGNORECASE)


def _extraer_fecha_celebracion(nombre_producto, fecha_compra):
    """Extrae (year_4dig, month) de celebración del nombre del producto WooCommerce.

    Busca patrones DD/MM/YY, DD-MM-YY, DD-mes-YYYY en el texto.
    Si hay varias fechas (productos concatenados con coma), usa la primera.
    Valida que el año tenga sentido respecto a la fecha de compra.
    Devuelve None si no encuentra fecha o si es un vale regalo sin fecha.
    """
    if not nombre_producto or pd.isna(nombre_producto):
        return None

    texto = str(nombre_producto)

    # Patrón 1: DD/MM/YY
    m = re.search(r"(\d{1,2})/(\d{2})/(\d{2})", texto)
    if m:
        day, month, yy = int(m.group(1)), int(m.group(2)), int(m.group(3))
        year = 2000 + yy
        if 1 <= month <= 12:
            # Sanidad: si el año es claramente incorrecto (ej: 25 cuando compra es 2026)
            if fecha_compra and year < fecha_compra.year:
                year = fecha_compra.year
            return (year, month)

    # Patrón 2: DD-MM-YY (numérico con guiones)
    m = re.search(r"(\d{1,2})-(\d{2})-(\d{2})(?!\d)", texto)
    if m:
        day, month, yy = int(m.group(1)), int(m.group(2)), int(m.group(3))
        year = 2000 + yy
        if 1 <= month <= 12:
            if fecha_compra and year < fecha_compra.year:
                year = fecha_compra.year
            return (year, month)

    # Patrón 3: DD-mes-YYYY o DD-mes-YY (texto)
    m = re.search(
        r"(\d{1,2})[-\s]+(enero|febrero|marzo|abril|mayo|junio|julio|agosto|"
        r"septiembre|octubre|noviembre|diciembre)[-\s]+(\d{4}|\d{2})",
        texto, re.IGNORECASE,
    )
    if m:
        month = _MESES_ES.get(m.group(2).lower())
        yy = int(m.group(3))
        year = yy if yy >= 2000 else 2000 + yy
        if month and fecha_compra and year < fecha_compra.year:
            year = fecha_compra.year
        return (year, month) if month else None

    return None


def _calcular_woo_devengo(df_woo):
    """Reclasifica pedidos WooCommerce por fecha de CELEBRACIÓN (devengo).

    Devuelve dict: {year_str: {month_str: {euros, pedidos, products}}}.
    Excluye productos 'Regala talleres y catas' sin fecha de celebración.
    Si no se encuentra fecha de celebración, usa la fecha de compra como fallback.
    """
    result = {}
    for yr in YEAR_LIST:
        result[yr] = {}
        for m in range(1, 13):
            result[yr][str(m)] = {"euros": 0, "pedidos": 0, "products": {}}

    if df_woo is None or df_woo.empty:
        return result

    df = df_woo.copy()

    # Filtrar por estado válido
    col_status = "status" if "status" in df.columns else "estado"
    if col_status in df.columns:
        estados_validos = {"completed", "processing", "on-hold", "Completado", "En proceso"}
        df = df[df[col_status].isin(estados_validos)]

    # Fecha de compra
    col_fecha = "date_created" if "date_created" in df.columns else "fecha"
    df["_fecha_compra"] = pd.to_datetime(df[col_fecha], format="mixed", dayfirst=True, errors="coerce")

    # Total numérico — usar is_numeric_dtype (pandas 3.x reporta strings como 'str', no 'object').
    if pd.api.types.is_numeric_dtype(df["total"]):
        df["_total"] = df["total"].fillna(0)
    else:
        df["_total"] = pd.to_numeric(
            df["total"].astype(str)
                       .str.replace("€", "", regex=False)
                       .str.replace(" ", "", regex=False)
                       .str.replace("\u00a0", "", regex=False)
                       .str.replace(".", "", regex=False)
                       .str.replace(",", ".", regex=False),
            errors="coerce",
        ).fillna(0)

    for _, row in df.iterrows():
        nombre = str(row.get("items_resumen", "") or "")
        total = float(row.get("_total", 0))
        fecha_compra = row.get("_fecha_compra")

        if total <= 0:
            continue

        # Excluir vales regalo sin fecha de celebración
        if _RE_REGALA.search(nombre):
            fecha_cel = _extraer_fecha_celebracion(nombre, fecha_compra)
            if fecha_cel is None:
                continue  # vale regalo puro → no contabilizar

        # Determinar mes de devengo
        fecha_cel = _extraer_fecha_celebracion(nombre, fecha_compra)
        if fecha_cel:
            year_dev, month_dev = fecha_cel
        elif pd.notna(fecha_compra):
            year_dev, month_dev = fecha_compra.year, fecha_compra.month
        else:
            continue

        yr_str = str(year_dev)
        m_str = str(month_dev)

        # Solo años que estamos procesando
        if yr_str not in result:
            continue

        result[yr_str][m_str]["euros"] = _round(result[yr_str][m_str]["euros"] + total)
        result[yr_str][m_str]["pedidos"] += 1

        # Nombre del producto (truncar para legibilidad)
        prod_name = nombre[:80].strip() if nombre else "Sin nombre"
        if prod_name:
            result[yr_str][m_str]["products"][prod_name] = _round(
                result[yr_str][m_str]["products"].get(prod_name, 0) + total
            )

    return result


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


def calcular_DIAS(items_por_año, recibos_por_año, year_list=None):
    """
    Genera estructura DIAS para análisis por día de la semana.
    DIAS[year][dia_idx] = {euros, tickets, ticket_medio}  (0=Lunes..6=Domingo)
    DIAS[year]["heatmap"][dia_idx][mes] = euros
    DIAS["dias_nombres"] = ["Lunes", ..., "Domingo"]
    """
    if year_list is None:
        year_list = YEAR_LIST
    DIAS = {}
    dias_nombres = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes",
                    "Sábado", "Domingo"]
    DIAS["dias_nombres"] = dias_nombres

    for year in year_list:
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
            df = _preparar_df(df_items)
            df["dia"] = df["Fecha"].dt.dayofweek
            dr = _preparar_df(df_recibos) if df_recibos is not None and not df_recibos.empty else None

            # Totales por día de la semana
            for d in range(7):
                dd = df[df["dia"] == d]
                if dd.empty:
                    continue
                euros = _round(dd["Ventas netas"].sum())

                if dr is not None:
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
        # Incluir EXPERIENCIAS si hay datos WooCommerce devengo
        wd = D[year].get("woo_devengo", {})
        if any(wd.get(str(m), {}).get("euros", 0) > 0 for m in range(1, 13)):
            all_cats.add("EXPERIENCIAS")
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
        col_fecha = "date_created" if "date_created" in df_woo.columns else "fecha"
        df_woo["_fecha"] = pd.to_datetime(df_woo[col_fecha], errors="coerce")
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


def _calcular_dias_mes(df_items, df_recibos):
    """Calcula euros por día-de-semana por mes: {month: {dia_idx: euros}}.

    dia_idx: 0=Lunes..6=Domingo.  Se usa en el KPI 'Mejor día' de Tasca.
    """
    dias_mes = {str(m): {str(d): 0 for d in range(7)} for m in range(1, 13)}
    if df_items is None or df_items.empty:
        return dias_mes
    df = _preparar_df(df_items)
    df["dia"] = df["Fecha"].dt.dayofweek
    for m in range(1, 13):
        dm = df[df["mes"] == m]
        if dm.empty:
            continue
        for d in range(7):
            dd = dm[dm["dia"] == d]
            if not dd.empty:
                dias_mes[str(m)][str(d)] = _round(dd["Ventas netas"].sum())
    return dias_mes


def calcular_RAW(items_por_año, recibos_por_año):
    """
    Genera la estructura RAW para Tasca:
    RAW[year].mensual[month] = {euros, unidades, tickets, prom_ticket, cats}
    RAW[year].categorias_mes[month] = {cat: pct}
    RAW[year].cats_total, cats_euros, cats
    """
    RAW = {}

    for year in TASCA_YEAR_LIST:
        df_items = items_por_año.get(year)
        df_recibos = recibos_por_año.get(year)

        mensual = _calcular_mensual_base(df_items, df_recibos)
        # categorias_mes es lo mismo que cats en mensual
        categorias_mes = {m: mensual[m]["cats"] for m in mensual}
        cats_total, cats_euros_dict = _calcular_cats_year(mensual)

        RAW[year] = {
            "mensual": mensual,
            "categorias_mes": categorias_mes,
            "cats_total": cats_total,
            "cats_euros": cats_euros_dict,
            "cats": sorted(cats_total.keys()),
            "dias_mes": _calcular_dias_mes(df_items, df_recibos),
        }

    return RAW


def calcular_PBM_tasca(items_por_año):
    """Genera PBM[year][month][cat] = [{art, euros, cant}] para Tasca."""
    PBM = {}

    for year in TASCA_YEAR_LIST:
        PBM[year] = _calcular_pbm(items_por_año.get(year))

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
# MAIN
# ══════════════════════════════════════════════════════════════════════════════

def main(abrir_navegador=True, solo_meses_cerrados=True, enviar_email=False):
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
    DIAS_TASCA = calcular_DIAS(t_items, t_recibos, year_list=TASCA_YEAR_LIST)
    path_tasca = generar_html_tasca(RAW, PBM)

    # ── 3. JSON Streamlit + Netlify ──
    print("\n--- JSON Streamlit + Netlify ---")
    try:
        data_dir = exportar_json_streamlit(D, MD, DIAS, RAW, PBM, DIAS_TASCA)
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
    parcial = "--incluir-parcial" in sys.argv
    # --solo-cerrados se mantiene como alias compatible (ahora es el default)
    cerrados = not parcial
    email = "--email" in sys.argv
    main(abrir_navegador=abrir, solo_meses_cerrados=cerrados, enviar_email=email)
