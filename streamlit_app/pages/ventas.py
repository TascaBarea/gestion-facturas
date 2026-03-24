"""
Dashboard de Ventas — Tasca Barea y Comestibles Barea.
Muestra datos agregados desde JSON exportado a Netlify.
"""

import streamlit as st
from utils.auth import require_role, get_role

require_role(["admin", "socio", "comes"])

st.title("Dashboard Ventas")

role = get_role()
if role == "comes":
    st.markdown("Datos de ventas de **Comestibles Barea**.")
else:
    st.markdown("Datos de ventas de **Tasca Barea** y **Comestibles Barea**.")

st.info("Esta página se activará en la Fase 2 cuando el puente de datos esté configurado.")
