"""
Tasca Barea — Panel de gestión
Streamlit multi-page app con roles de acceso.
"""

import streamlit as st
from utils.auth import check_login, page_ids_for_role, get_role, get_user_name
from utils.data_client import backend_disponible

st.set_page_config(
    page_title="Tasca Barea",
    page_icon="🫒",
    layout="centered",
)

# ── Inicializar sesión ────────────────────────────────────────────────────────

if "autenticado" not in st.session_state:
    st.session_state.autenticado = False
    st.session_state.user_role = ""
    st.session_state.user_name = ""


# ── Definición de páginas ─────────────────────────────────────────────────────

ALL_PAGES = {
    "alta_evento": st.Page("pages/alta_evento.py", title="Alta de Evento", icon="🎪"),
    "calendario_eventos": st.Page("pages/calendario_eventos.py", title="Calendario de Eventos", icon="📅"),
    "ventas": st.Page("pages/ventas.py", title="Dashboard Ventas", icon="📊"),
    "cuadre": st.Page("pages/cuadre.py", title="Cuadre Bancario", icon="🏦"),
    "log_gmail": st.Page("pages/log_gmail.py", title="Log Gmail", icon="📧"),
    "monitor": st.Page("pages/monitor.py", title="Monitor Sistema", icon="🖥️"),
    "ejecutar": st.Page("pages/ejecutar.py", title="Ejecutar Scripts", icon="▶️"),
}


# ── Login ─────────────────────────────────────────────────────────────────────

def _show_login():
    """Muestra formulario de login con usuario y contraseña."""
    st.markdown(
        """
        <div style="text-align:center; padding:2rem 0 1rem">
            <h1 style="color:#2E7D32">Tasca Barea</h1>
            <p style="color:#888">Panel de gestión</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    username = st.text_input("Usuario", key="login_user")
    password = st.text_input("Contraseña", type="password", key="login_pwd")

    if st.button("Entrar", type="primary"):
        if not username or not password:
            st.error("Introduce usuario y contraseña.")
            return
        user_data = check_login(username.strip().lower(), password)
        if user_data:
            st.session_state.autenticado = True
            st.session_state.user_role = user_data["role"]
            st.session_state.user_name = user_data["name"]
            st.rerun()
        else:
            st.error("Usuario o contraseña incorrectos.")


# ── Main ──────────────────────────────────────────────────────────────────────

if not st.session_state.autenticado:
    _show_login()
    st.stop()

# Construir navegación filtrada por rol
allowed = page_ids_for_role(get_role())
pages = [ALL_PAGES[pid] for pid in allowed if pid in ALL_PAGES]

if not pages:
    st.error("Tu rol no tiene páginas asignadas.")
    st.stop()

# Sidebar
st.sidebar.markdown(
    f"""
    <div style="text-align:center; padding:1rem 0">
        <h2 style="color:#2E7D32; margin:0">Tasca Barea</h2>
        <p style="color:#888; font-size:0.85rem">{get_user_name()} ({get_role()})</p>
    </div>
    """,
    unsafe_allow_html=True,
)

if st.sidebar.button("Cerrar sesión"):
    st.session_state.autenticado = False
    st.session_state.user_role = ""
    st.session_state.user_name = ""
    st.rerun()

# Indicador de estado del backend
if backend_disponible():
    st.sidebar.success("Backend conectado", icon="\U0001f7e2")
else:
    st.sidebar.info("Solo lectura (PC apagado)", icon="\U0001f534")

# Navegación
nav = st.navigation(pages)
nav.run()
