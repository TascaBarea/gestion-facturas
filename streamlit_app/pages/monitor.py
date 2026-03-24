"""
Monitor Sistema — Estado de los scripts automáticos.
"""

import streamlit as st
from utils.auth import require_role

require_role(["admin"])

st.title("Monitor Sistema")
st.markdown("Estado de los procesos automáticos (Task Scheduler).")
st.info("Esta página se activará en la Fase 2 cuando el puente de datos esté configurado.")
