"""
Log Gmail — Resumen de la última ejecución del procesador de facturas.
"""

import streamlit as st
from utils.auth import require_role
from utils.data_client import get_gmail, ultima_actualizacion

require_role(["admin"])

st.title("Log Gmail")
st.sidebar.caption(f"Datos: {ultima_actualizacion()}")

datos = get_gmail()

if not datos:
    st.info("Datos de Gmail no disponibles. Se generarán tras la próxima ejecución de gmail.py.")
    st.stop()

# ── KPIs ──
fecha = datos.get("fecha_ejecucion", "?")[:16].replace("T", " ")
st.caption(f"Última ejecución: {fecha}")

col1, col2, col3, col4 = st.columns(4)
col1.metric("Procesados", datos.get("total_procesados", 0))
col2.metric("Exitosos", datos.get("exitosos", 0))
col3.metric("Revisión", datos.get("requieren_revision", 0))
col4.metric("Errores", datos.get("errores", 0))

# ── Proveedores procesados ──
proveedores_ok = datos.get("proveedores_ok", [])
if proveedores_ok:
    with st.expander(f"Proveedores OK ({len(proveedores_ok)})"):
        for p in proveedores_ok:
            st.write(f"- {p}")

# ── Requieren revisión ──
revision = datos.get("revision", [])
if revision:
    with st.expander(f"Requieren revisión ({len(revision)})", expanded=True):
        for r in revision:
            st.write(f"- {r}")

# ── Errores ──
errores = datos.get("errores_detalle", [])
if errores:
    st.subheader("Errores")
    for e in errores:
        st.error(e)
