"""
pages/documentos.py — Archivos compartidos en Google Drive.

v2 (24/04/2026): ampliado a 6 secciones alineadas con la estructura
post-R.5 de "Barea - Datos Compartidos": Ventas, Compras, Movimientos
Banco, Artículos, Maestro, Cuadres. Las 3 primeras tienen pestañas
"Año en curso" / "Histórico"; las 3 últimas son planas.
"""

import sys
import os
from datetime import datetime

import streamlit as st
from utils.auth import require_role

require_role(["admin", "socio", "comes"])

st.title("Documentos compartidos")
st.caption("Archivos sincronizados en Google Drive")

# ── Importar sync_drive ──────────────────────────────────────────────────────

_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

try:
    from nucleo.sync_drive import listar_carpeta, CARPETA_RAIZ
    _DRIVE_OK = True
except ImportError:
    _DRIVE_OK = False


# ── Configuración cerrada de secciones ───────────────────────────────────────

CARPETAS_DOCUMENTOS = [
    {
        "clave": "ventas",
        "titulo": "Ventas",
        "icono": "📊",
        "descripcion": "Dashboards y datos de ventas semanales",
        "ruta_drive": ["Ventas"],
        "subcarpetas": ["Año en curso", "Histórico"],
    },
    {
        "clave": "compras",
        "titulo": "Compras",
        "icono": "🧾",
        "descripcion": "Facturas procesadas y pagos registrados",
        "ruta_drive": ["Compras"],
        "subcarpetas": ["Año en curso", "Histórico"],
    },
    {
        "clave": "movimientos_banco",
        "titulo": "Movimientos Banco",
        "icono": "🏦",
        "descripcion": "Extractos y consolidados bancarios",
        "ruta_drive": ["Movimientos Banco"],
        "subcarpetas": ["Año en curso", "Histórico"],
    },
    {
        "clave": "articulos",
        "titulo": "Artículos",
        "icono": "📦",
        "descripcion": "Catálogo de productos",
        "ruta_drive": ["Articulos"],
        "subcarpetas": None,
    },
    {
        "clave": "maestro",
        "titulo": "Maestro",
        "icono": "📚",
        "descripcion": "MAESTRO_PROVEEDORES + Diccionario artículo→categoría",
        "ruta_drive": ["Maestro"],
        "subcarpetas": None,
    },
    {
        "clave": "cuadres",
        "titulo": "Cuadres",
        "icono": "⚖️",
        "descripcion": "Cuadres bancarios generados por cuadre.py",
        "ruta_drive": ["Cuadres"],
        "subcarpetas": None,
    },
]


# ── Formatters ───────────────────────────────────────────────────────────────

def _fmt_size(size_str):
    """Convierte bytes (str) a formato legible."""
    try:
        size = int(size_str)
    except (ValueError, TypeError):
        return "—"
    if size < 1024:
        return f"{size} B"
    if size < 1024 * 1024:
        return f"{size / 1024:.1f} KB"
    return f"{size / (1024 * 1024):.1f} MB"


def _fmt_date(iso_str):
    """Convierte fecha ISO a formato español."""
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        return dt.strftime("%d/%m/%Y %H:%M")
    except (ValueError, AttributeError):
        return "—"


def _icono_archivo(nombre, mime):
    if "spreadsheet" in mime or nombre.endswith((".xlsx", ".xls")):
        return "📊"
    if "html" in mime or nombre.endswith(".html"):
        return "📄"
    if "pdf" in mime or nombre.endswith(".pdf"):
        return "📕"
    return "📎"


# ── Render ───────────────────────────────────────────────────────────────────

def _listar_archivos(ruta_drive):
    """Pinta los archivos que hay dentro de `ruta_drive` (lista de segmentos)."""
    try:
        archivos = listar_carpeta(ruta_drive)
    except Exception as e:
        st.error(f"Error conectando con Drive: {e}")
        return

    # Filtrar subcarpetas: solo mostrar archivos reales
    archivos = [
        a for a in archivos
        if a.get("mimeType") != "application/vnd.google-apps.folder"
    ]

    if not archivos:
        st.info("Sin archivos en esta carpeta.")
        return

    for archivo in archivos:
        nombre = archivo.get("name", "?")
        size = _fmt_size(archivo.get("size"))
        fecha = _fmt_date(archivo.get("modifiedTime"))
        link = archivo.get("webViewLink", "")
        mime = archivo.get("mimeType", "")
        tipo_icono = _icono_archivo(nombre, mime)

        with st.container(border=True):
            col1, col2, col3 = st.columns([4, 2, 2])
            with col1:
                if link:
                    st.markdown(f"{tipo_icono} **[{nombre}]({link})**")
                else:
                    st.markdown(f"{tipo_icono} **{nombre}**")
            with col2:
                st.caption(f"Tamaño: {size}")
            with col3:
                st.caption(f"Actualizado: {fecha}")


def _render_seccion(cfg):
    """Render de una sección: encabezado + archivos (con o sin pestañas)."""
    st.markdown(f"### {cfg['icono']} {cfg['titulo']}")
    st.caption(cfg["descripcion"])

    if cfg["subcarpetas"]:
        tabs = st.tabs(cfg["subcarpetas"])
        for tab, sub in zip(tabs, cfg["subcarpetas"]):
            with tab:
                _listar_archivos(cfg["ruta_drive"] + [sub])
    else:
        _listar_archivos(cfg["ruta_drive"])

    st.markdown("")  # separador visual entre secciones


# ── Contenido principal ──────────────────────────────────────────────────────

if not _DRIVE_OK:
    st.error(
        "No se pudo importar `nucleo.sync_drive`. "
        "Verifica que las dependencias de Google API estén instaladas."
    )
    st.stop()

st.markdown(
    f"Carpeta compartida: **{CARPETA_RAIZ}**  \n"
    "Los archivos se sincronizan automáticamente tras cada ejecución de los scripts."
)
st.markdown("---")

for _cfg in CARPETAS_DOCUMENTOS:
    _render_seccion(_cfg)
