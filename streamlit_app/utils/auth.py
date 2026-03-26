"""
Sistema de autenticación y roles para Streamlit app.
"""

import hmac
import streamlit as st

# Definición de roles y páginas permitidas
ROLE_PAGES = {
    "admin":   ["ventas", "cuadre", "log_gmail", "monitor", "ejecutar", "alta_evento", "calendario_eventos"],
    "socio":   ["ventas"],
    "comes":   ["ventas"],
    "eventos": ["alta_evento", "calendario_eventos"],
}


def get_user(username: str) -> dict | None:
    """Busca un usuario en st.secrets['users']. Devuelve dict o None."""
    users = st.secrets.get("users", {})
    return users.get(username)


def check_login(username: str, password: str) -> dict | None:
    """Verifica credenciales. Devuelve datos del usuario o None."""
    user = get_user(username)
    if not user:
        return None
    stored_pw = user.get("password", "")
    if not stored_pw or not hmac.compare_digest(password, stored_pw):
        return None
    return {"name": user.get("name", username), "role": user.get("role", "")}


def get_role() -> str:
    """Devuelve el rol del usuario autenticado, o cadena vacía."""
    return st.session_state.get("user_role", "")


def get_user_name() -> str:
    """Devuelve el nombre del usuario autenticado."""
    return st.session_state.get("user_name", "")


def require_role(allowed_roles: list[str]):
    """Verifica que el usuario tenga uno de los roles permitidos.
    Si no, muestra error y detiene la página.
    """
    if not st.session_state.get("autenticado", False):
        st.warning("Inicia sesión desde la página principal.")
        st.stop()
    role = get_role()
    if role not in allowed_roles:
        st.error("No tienes acceso a esta página.")
        st.stop()


def page_ids_for_role(role: str) -> list[str]:
    """Devuelve la lista de page_ids permitidos para un rol."""
    return ROLE_PAGES.get(role, [])
