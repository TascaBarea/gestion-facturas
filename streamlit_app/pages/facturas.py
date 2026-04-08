import streamlit as st
from utils.auth import require_role

require_role(["admin"])

st.header("📋 Listado de Facturas")
st.info("Página en construcción. Próximamente: listado filtrable de facturas procesadas.")
