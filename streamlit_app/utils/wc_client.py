"""
Wrapper WooCommerce API para Streamlit app.
Extraido de ventas_semana/script_barea.py y alta_evento.py.
"""

import re
import streamlit as st
from woocommerce import API as WC_API


@st.cache_resource
def get_wc_api():
    """Devuelve cliente WooCommerce API usando secrets de Streamlit."""
    return WC_API(
        url=st.secrets["WC_URL"],
        consumer_key=st.secrets["WC_KEY"],
        consumer_secret=st.secrets["WC_SECRET"],
        version="wc/v3",
        timeout=30,
    )


def cargar_categorias(wc):
    """Carga todas las categorias de productos WooCommerce."""
    cats, page = [], 1
    while True:
        resp = wc.get("products/categories", params={"per_page": 100, "page": page}).json()
        if not isinstance(resp, list) or not resp:
            break
        cats.extend(resp)
        page += 1
        if len(resp) < 100:
            break
    return [(c["id"], c["name"]) for c in cats if c.get("name") != "Sin categoría"]


def cargar_tipos_evento(wc):
    """Carga nombres únicos de eventos/cursos desde productos WooCommerce.

    Filtra productos tipo ticket-event, excluye CERRADO,
    y extrae el nombre corto (antes del HTML <br><small>).
    Devuelve lista de nombres únicos ordenados.
    """
    productos = listar_productos(wc, status="publish")
    nombres = set()
    for p in productos:
        if p.get("type") != "ticket-event":
            continue
        nombre = p.get("name", "")
        # Excluir cerrados
        if nombre.upper().startswith("CERRADO"):
            continue
        # Extraer nombre corto: antes de <br>, <small>, o HTML tags
        nombre_corto = re.split(r"<br>|<small>|<br/>", nombre, maxsplit=1)[0]
        nombre_corto = re.sub(r"<[^>]+>", "", nombre_corto).strip()
        if nombre_corto:
            nombres.add(nombre_corto)
    return sorted(nombres)


def crear_producto(wc, payload: dict) -> dict:
    """Crea un producto en WooCommerce. Devuelve la respuesta JSON."""
    resp = wc.post("products", payload)
    return resp.json()


def listar_productos(wc, **params) -> list:
    """Lista productos con paginacion."""
    productos, page = [], 1
    while True:
        params["per_page"] = 100
        params["page"] = page
        resp = wc.get("products", params=params).json()
        if not isinstance(resp, list) or not resp:
            break
        productos.extend(resp)
        page += 1
        if len(resp) < 100:
            break
    return productos


def nombre_corto_evento(nombre_raw):
    """Extrae nombre corto de un producto WC (antes del HTML)."""
    nombre = re.split(r"<br>|<small>|<br/>", nombre_raw, maxsplit=1)[0]
    return re.sub(r"<[^>]+>", "", nombre).strip()


def cargar_eventos_futuros(wc):
    """Carga eventos ticket-event con stock_status instock o manage_stock.

    Devuelve lista de dicts con id, nombre, stock_quantity, total_sales, manage_stock.
    """
    productos = listar_productos(wc, status="publish")
    eventos = []
    for p in productos:
        if p.get("type") != "ticket-event":
            continue
        eventos.append({
            "id": p["id"],
            "nombre_raw": p.get("name", ""),
            "nombre": nombre_corto_evento(p.get("name", "")),
            "stock_quantity": p.get("stock_quantity"),
            "manage_stock": p.get("manage_stock", False),
            "total_sales": p.get("total_sales", 0),
        })
    return eventos


def cargar_pedidos_evento(wc, product_id):
    """Carga todos los pedidos (processing/completed) de un producto."""
    pedidos = []
    page = 1
    while True:
        resp = wc.get("orders", params={
            "product": product_id,
            "per_page": 100,
            "page": page,
            "status": "processing,completed",
        }).json()
        if not isinstance(resp, list) or not resp:
            break
        pedidos.extend(resp)
        page += 1
        if len(resp) < 100:
            break
    return pedidos
