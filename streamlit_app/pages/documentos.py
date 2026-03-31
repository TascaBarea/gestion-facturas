"""
pages/documentos.py — Archivos compartidos en Google Drive.
Muestra los archivos sincronizados organizados por carpeta.
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

# Añadir raíz del proyecto al path para importar nucleo/
_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

try:
    from nucleo.sync_drive import listar_carpeta, CARPETA_RAIZ
    _DRIVE_OK = True
except ImportError:
    _DRIVE_OK = False


# ── Funciones auxiliares ─────────────────────────────────────────────────────

def _fmt_size(size_str):
    """Convierte bytes (str) a formato legible."""
    try:
        size = int(size_str)
    except (ValueError, TypeError):
        return "—"
    if size < 1024:
        return f"{size} B"
    elif size < 1024 * 1024:
        return f"{size / 1024:.1f} KB"
    else:
        return f"{size / (1024 * 1024):.1f} MB"


def _fmt_date(iso_str):
    """Convierte fecha ISO a formato español."""
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        return dt.strftime("%d/%m/%Y %H:%M")
    except (ValueError, AttributeError):
        return "—"


def _mostrar_carpeta(nombre_carpeta, icono, descripcion):
    """Muestra una sección con los archivos de una subcarpeta de Drive."""
    st.markdown(f"### {icono} {nombre_carpeta}")
    st.caption(descripcion)

    try:
        archivos = listar_carpeta(nombre_carpeta)
    except Exception as e:
        st.error(f"Error conectando con Drive: {e}")
        return

    if not archivos:
        st.info("Sin archivos en esta carpeta.")
        return

    for archivo in archivos:
        nombre = archivo.get("name", "?")
        size = _fmt_size(archivo.get("size"))
        fecha = _fmt_date(archivo.get("modifiedTime"))
        link = archivo.get("webViewLink", "")
        mime = archivo.get("mimeType", "")

        # Icono según tipo
        if "spreadsheet" in mime or nombre.endswith((".xlsx", ".xls")):
            tipo_icono = "📊"
        elif "html" in mime or nombre.endswith(".html"):
            tipo_icono = "📄"
        elif "pdf" in mime or nombre.endswith(".pdf"):
            tipo_icono = "📕"
        else:
            tipo_icono = "📎"

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


# ── Contenido principal ──────────────────────────────────────────────────────

if not _DRIVE_OK:
    st.error(
        "No se pudo importar `nucleo.sync_drive`. "
        "Verifica que las dependencias de Google API estén instaladas."
    )
    st.stop()

st.markdown(
    f"Carpeta compartida: **{CARPETA_RAIZ}**  \n"
    "Los archivos se sincronizan automáticamente tras cada ejecución de Gmail y Ventas."
)

st.markdown("---")

_mostrar_carpeta("Ventas", "📈", "Dashboards y datos de ventas semanales")
st.markdown("")
_mostrar_carpeta("Facturas", "🧾", "Facturas procesadas y pagos registrados")

# También mostrar archivos sueltos en la raíz (si los hay)
try:
    raiz = listar_carpeta()
    # Filtrar: solo archivos, no carpetas
    archivos_raiz = [
        a for a in raiz
        if a.get("mimeType") != "application/vnd.google-apps.folder"
    ]
    if archivos_raiz:
        st.markdown("---")
        st.markdown("### 📁 Otros archivos")
        for archivo in archivos_raiz:
            nombre = archivo.get("name", "?")
            link = archivo.get("webViewLink", "")
            fecha = _fmt_date(archivo.get("modifiedTime"))
            if link:
                st.markdown(f"- [{nombre}]({link}) — {fecha}")
            else:
                st.markdown(f"- {nombre} — {fecha}")
except Exception:
    pass
