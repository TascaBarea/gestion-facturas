"""
Cuadre Bancario — Estado de la conciliación bancaria.
"""

import streamlit as st
from utils.auth import require_role

require_role(["admin"])

st.title("Cuadre Bancario")
st.markdown("Estado de la conciliación bancaria mensual.")
st.info("Esta página se activará en la Fase 2 cuando el puente de datos esté configurado.")
