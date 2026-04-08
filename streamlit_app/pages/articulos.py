import streamlit as st
from utils.auth import require_role

require_role(["admin"])

st.header("📦 Artículos")
st.info("Página en construcción. Próximamente: catálogo de artículos Loyverse.")
