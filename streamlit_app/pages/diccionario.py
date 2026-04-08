import streamlit as st
from utils.auth import require_role

require_role(["admin"])

st.header("📖 Diccionario de Artículos")
st.info("Página en construcción. Próximamente: visualización del DiccionarioProveedoresCategoria.")
