"""
data_client.py — Cliente de datos para Streamlit.
Descarga JSON agregados desde Netlify CDN con cache de 1 hora.
"""

import json
import logging
import urllib.request
import ssl
import streamlit as st

logger = logging.getLogger(__name__)

_BASE = st.secrets.get("NETLIFY_DATA_URL", "")


@st.cache_data(ttl=3600)
def _fetch_json(filename: str) -> dict | None:
    """Descarga un fichero JSON desde Netlify. Devuelve None si falla."""
    if not _BASE:
        logger.warning("NETLIFY_DATA_URL no configurado en secrets")
        return None
    url = f"{_BASE}/data/{filename}"
    try:
        # Crear contexto SSL que no verifique certificados (Streamlit Cloud compatible)
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        req = urllib.request.Request(url, headers={"User-Agent": "TascaBarea/1.0"})
        with urllib.request.urlopen(req, timeout=15, context=ctx) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data
    except Exception as e:
        logger.error(f"Error fetching {url}: {e}")
        # Mostrar error en la app para diagnóstico
        st.toast(f"Error cargando {filename}: {e}", icon="⚠️")
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
