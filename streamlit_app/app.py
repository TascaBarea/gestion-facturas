"""
Comestibles Barea — Panel de gestión
Streamlit multi-page app para procesos WooCommerce.
"""

import streamlit as st

st.set_page_config(
    page_title="Comestibles Barea",
    page_icon="🫒",
    layout="centered",
)


# ── Autenticación simple por contraseña ──────────────────────────────────────

def _check_password():
    """Verifica contraseña almacenada en st.secrets['APP_PASSWORD']."""
    if "autenticado" not in st.session_state:
        st.session_state.autenticado = False

    if st.session_state.autenticado:
        return True

    st.markdown(
        """
        <div style="text-align:center; padding:2rem 0 1rem">
            <h1 style="color:#2E7D32">Comestibles Barea</h1>
            <p style="color:#888">Panel de gestión</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    password = st.text_input("Contraseña", type="password", key="login_pwd")

    if st.button("Entrar", type="primary"):
        if password == st.secrets.get("APP_PASSWORD", ""):
            st.session_state.autenticado = True
            st.rerun()
        else:
            st.error("Contraseña incorrecta")

    return False


# ── Main ─────────────────────────────────────────────────────────────────────

if not _check_password():
    st.stop()

# Sidebar con identidad visual
st.sidebar.markdown(
    """
    <div style="text-align:center; padding:1rem 0">
        <h2 style="color:#2E7D32; margin:0">Comestibles Barea</h2>
        <p style="color:#888; font-size:0.85rem">Panel de gestión</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# Página de inicio
st.title("Panel de gestión")
st.markdown("Selecciona una opción en el menú lateral para empezar.")

st.markdown("---")
st.markdown(
    """
    **Módulos disponibles:**
    - **Alta de Evento** — Crear talleres, catas y eventos en la tienda online
    """
)
