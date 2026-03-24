"""
Log Gmail — Estado de la última ejecución del procesador de facturas.
"""

import streamlit as st
from utils.auth import require_role

require_role(["admin"])

st.title("Log Gmail")
st.markdown("Última ejecución del procesador de facturas por email.")
st.info("Esta página se activará en la Fase 2 cuando el puente de datos esté configurado.")
