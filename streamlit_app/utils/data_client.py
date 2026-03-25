"""
data_client.py — Cliente de datos para Streamlit.
Descarga JSON agregados desde Netlify CDN con cache de 1 hora.
"""

import json
import urllib.request
import streamlit as st


_BASE = st.secrets.get("NETLIFY_DATA_URL", "")


@st.cache_data(ttl=3600)
def _fetch_json(filename: str) -> dict | None:
    """Descarga un fichero JSON desde Netlify. Devuelve None si falla."""
    if not _BASE:
        return None
    url = f"{_BASE}/data/{filename}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "TascaBarea/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception:
        return None


def get_meta() -> dict | None:
    """Metadatos de la última exportación (timestamp, ficheros disponibles)."""
    return _fetch_json("meta.json")


def get_ventas_comes() -> dict | None:
    """Datos de ventas Comestibles (mensual, categorías, top productos, márgenes)."""
    return _fetch_json("ventas_comes.json")


def get_ventas_tasca() -> dict | None:
    """Datos de ventas Tasca (mensual, categorías, top productos, días semana)."""
    return _fetch_json("ventas_tasca.json")


def get_cuadre() -> dict | None:
    """Resumen del cuadre bancario (clasificados, REVISAR, detalle)."""
    return _fetch_json("cuadre.json")


def get_gmail() -> dict | None:
    """Resumen de la última ejecución Gmail (procesados, errores)."""
    return _fetch_json("gmail.json")


def get_monitor() -> dict | None:
    """Estado de los procesos automáticos (última ejecución, estado)."""
    return _fetch_json("monitor.json")


def ultima_actualizacion() -> str:
    """Devuelve timestamp legible de la última exportación, o 'Desconocido'."""
    meta = get_meta()
    if meta and "exportado" in meta:
        return meta["exportado"].replace("T", " ")[:16]
    return "Desconocido"
