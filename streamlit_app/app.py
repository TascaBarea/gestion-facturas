"""
Tasca Barea — Panel de gestión
Streamlit multi-page app con roles de acceso.
"""

import time

import streamlit as st
from utils.auth import check_login, page_ids_for_role, get_role, get_user_name
from utils.data_client import backend_disponible, fetch_backend_json

# ── Rate limiting login ──────────────────────────────────────────────────────
_MAX_LOGIN_ATTEMPTS = 5
_LOCKOUT_SECONDS = 60

st.set_page_config(
    page_title="Tasca Barea",
    page_icon="🫒",
    layout="centered",
)

# ── CSS corporativo ──────────────────────────────────────────────────────────

_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:ital,wght@0,400;0,500;0,700;1,400&family=Syne:wght@600;700;800&display=swap');

/* ── Tipografía global ────────────────────── */
html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
}
h1, h2, h3, .stMarkdown h1, .stMarkdown h2, .stMarkdown h3 {
    font-family: 'Syne', sans-serif;
    letter-spacing: -0.02em;
}

/* ── Sidebar ──────────────────────────────── */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #1A1A1A 0%, #2A1A1A 100%);
}
section[data-testid="stSidebar"] * {
    color: #FFF8F0 !important;
}
section[data-testid="stSidebar"] hr {
    border-color: rgba(255,248,240,0.15);
}
section[data-testid="stSidebar"] .stButton > button {
    background: transparent;
    border: 1px solid rgba(255,248,240,0.25);
    color: #FFF8F0 !important;
    transition: all 0.2s ease-out;
}
section[data-testid="stSidebar"] .stButton > button:hover {
    background: rgba(139,0,0,0.4);
    border-color: #8B0000;
}

/* ── Botones primary ──────────────────────── */
.stButton > button[kind="primary"],
button[data-testid="stFormSubmitButton"] > button {
    background: #8B0000;
    border: none;
    font-family: 'Syne', sans-serif;
    font-weight: 600;
    letter-spacing: 0.02em;
    transition: all 0.2s ease-out;
}
.stButton > button[kind="primary"]:hover {
    background: #6B0000;
    transform: translateY(-1px);
}

/* ── Métricas ─────────────────────────────── */
[data-testid="stMetric"] {
    background: #FFF8F0;
    border: 1px solid rgba(139,0,0,0.12);
    border-radius: 8px;
    padding: 0.75rem 1rem;
}
[data-testid="stMetricValue"] {
    font-family: 'Syne', sans-serif;
    color: #8B0000;
}

/* ── Tabs ─────────────────────────────────── */
.stTabs [data-baseweb="tab"] {
    font-family: 'DM Sans', sans-serif;
    font-weight: 500;
}
.stTabs [aria-selected="true"] {
    border-bottom-color: #8B0000;
}

/* ── Login ─────────────────────────────────── */
.login-container {
    max-width: 360px;
    margin: 4rem auto 0;
    text-align: center;
}
.login-marca {
    font-family: 'Syne', sans-serif;
    font-weight: 800;
    font-size: 2.4rem;
    color: #8B0000;
    letter-spacing: -0.03em;
    margin-bottom: 0.15rem;
}
.login-sub {
    font-family: 'DM Sans', sans-serif;
    color: #888;
    font-size: 0.95rem;
    margin-bottom: 2rem;
}
.login-linea {
    width: 48px;
    height: 3px;
    background: #8B0000;
    margin: 0.8rem auto 1.5rem;
    border-radius: 2px;
}

/* ── Sidebar branding ─────────────────────── */
.sidebar-marca {
    font-family: 'Syne', sans-serif;
    font-weight: 800;
    font-size: 1.35rem;
    color: #FFF8F0 !important;
    letter-spacing: -0.02em;
    margin: 0;
}
.sidebar-user {
    font-family: 'DM Sans', sans-serif;
    color: rgba(255,248,240,0.6) !important;
    font-size: 0.8rem;
    margin-top: 0.2rem;
}
.sidebar-divider {
    width: 32px;
    height: 2px;
    background: #8B0000;
    margin: 0.6rem auto 0;
    border-radius: 1px;
}

/* ── Reduced motion ───────────────────────── */
@media (prefers-reduced-motion: reduce) {
    *, *::before, *::after {
        animation-duration: 0.01ms !important;
        transition-duration: 0.01ms !important;
    }
}
</style>
"""

st.markdown(_CSS, unsafe_allow_html=True)

# ── Inicializar sesión ────────────────────────────────────────────────────────

if "autenticado" not in st.session_state:
    st.session_state.autenticado = False
    st.session_state.user_role = ""
    st.session_state.user_name = ""


# ── Definición de páginas ─────────────────────────────────────────────────────

ALL_PAGES = {
    "": {
        "inicio": st.Page("pages/inicio.py", title="Inicio", icon="🏠", default=True),
    },
    "Compras": {
        "parseo": st.Page("pages/parseo.py", title="Parseo", icon="🔍"),
        "facturas": st.Page("pages/facturas.py", title="Facturas", icon="📋"),
        "maestro": st.Page("pages/maestro.py", title="Proveedores", icon="📋"),
        "diccionario": st.Page("pages/diccionario.py", title="Diccionario", icon="📖"),
        "log_gmail": st.Page("pages/log_gmail.py", title="Log Gmail", icon="📧"),
    },
    "Ventas": {
        "ventas": st.Page("pages/ventas.py", title="Dashboard Ventas", icon="📊"),
        "articulos": st.Page("pages/articulos.py", title="Artículos", icon="📦"),
    },
    "Eventos": {
        "calendario_eventos": st.Page("pages/calendario_eventos.py", title="Calendario de Eventos", icon="📅"),
        "alta_evento": st.Page("pages/alta_evento.py", title="Alta de Evento", icon="🎪"),
    },
    "Operaciones": {
        "cuadre": st.Page("pages/cuadre.py", title="Cuadre Bancario", icon="🏦"),
        "mov_banco": st.Page("pages/mov_banco.py", title="Mov. Banco", icon="🏦"),
        "ejecutar": st.Page("pages/ejecutar.py", title="Ejecutar Scripts", icon="▶️"),
        "monitor": st.Page("pages/monitor.py", title="Monitor Sistema", icon="🖥️"),
        "documentos": st.Page("pages/documentos.py", title="Documentos", icon="📁"),
    },
}


# ── Login ─────────────────────────────────────────────────────────────────────

def _show_login():
    """Muestra formulario de login con estilo corporativo."""
    st.markdown(
        """
        <div class="login-container">
            <div class="login-marca">Tasca Barea</div>
            <div class="login-linea"></div>
            <div class="login-sub">Panel de gestión</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    username = st.text_input("Usuario", key="login_user")
    password = st.text_input("Contraseña", type="password", key="login_pwd")

    # Rate limiting: comprobar lockout
    attempts = st.session_state.get("login_attempts", 0)
    locked_until = st.session_state.get("login_locked_until", 0)
    now = time.time()

    if now < locked_until:
        remaining = int(locked_until - now)
        st.error(f"Demasiados intentos. Espera {remaining}s.")
        return

    if st.button("Entrar", type="primary", use_container_width=True):
        if not username or not password:
            st.error("Introduce usuario y contraseña.")
            return
        user_data = check_login(username.strip().lower(), password)
        if user_data:
            st.session_state.autenticado = True
            st.session_state.user_role = user_data["role"]
            st.session_state.user_name = user_data["name"]
            st.session_state.login_attempts = 0
            st.session_state.login_locked_until = 0
            st.rerun()
        else:
            attempts += 1
            st.session_state.login_attempts = attempts
            if attempts >= _MAX_LOGIN_ATTEMPTS:
                st.session_state.login_locked_until = now + _LOCKOUT_SECONDS
                st.error(f"Demasiados intentos ({attempts}). Bloqueado {_LOCKOUT_SECONDS}s.")
            else:
                st.error(f"Usuario o contraseña incorrectos ({attempts}/{_MAX_LOGIN_ATTEMPTS}).")


# ── Main ──────────────────────────────────────────────────────────────────────

if not st.session_state.autenticado:
    _show_login()
    st.stop()

# Construir navegación filtrada por rol
allowed = page_ids_for_role(get_role())
filtered_pages = {}
for section, section_pages in ALL_PAGES.items():
    visible = [page for pid, page in section_pages.items()
               if pid in allowed or section == ""]
    if visible:
        filtered_pages[section] = visible

if not any(filtered_pages.values()):
    st.error("Tu rol no tiene páginas asignadas.")
    st.stop()

# Sidebar
st.sidebar.markdown(
    f"""
    <div style="text-align:center; padding:1.2rem 0 0.5rem">
        <div class="sidebar-marca">Tasca Barea</div>
        <div class="sidebar-divider"></div>
        <div class="sidebar-user">{get_user_name()} · {get_role()}</div>
    </div>
    """,
    unsafe_allow_html=True,
)

if st.sidebar.button("Cerrar sesión", use_container_width=True):
    st.session_state.autenticado = False
    st.session_state.user_role = ""
    st.session_state.user_name = ""
    st.rerun()

# Indicador de estado del backend
_backend_ok = backend_disponible()
if _backend_ok:
    st.sidebar.success("Backend conectado", icon="\U0001f7e2")
else:
    st.sidebar.info("Solo lectura (PC apagado)", icon="\U0001f534")

# Alertas de procesos atrasados (solo admin, solo si backend disponible)
if _backend_ok and get_role() == "admin":
    _alertas = fetch_backend_json("/api/alerts")
    if _alertas and _alertas.get("alerts"):
        for _a in _alertas["alerts"]:
            _msg = f"{_a['module'].capitalize()}: {_a['message']}"
            if _a["level"] == "error":
                st.sidebar.error(_msg, icon="\u274c")
            else:
                st.sidebar.warning(_msg, icon="\u26a0\ufe0f")

# Navegación
nav = st.navigation(filtered_pages)
nav.run()
