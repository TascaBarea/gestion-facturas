"""
Sistema de autenticación y roles para Streamlit app.
"""

import hashlib
import hmac
import os

import streamlit as st

# Definición de roles y páginas permitidas
ROLE_PAGES = {
    "admin":   ["ventas", "cuadre", "log_gmail", "monitor", "ejecutar", "alta_evento", "calendario_eventos", "maestro"],
    "socio":   ["ventas"],
    "comes":   ["ventas"],
    "eventos": ["alta_evento", "calendario_eventos"],
}


def get_user(username: str) -> dict | None:
    """Busca un usuario en st.secrets['users']. Devuelve dict o None."""
    users = st.secrets.get("users", {})
    return users.get(username)


def _hash_password(password: str, salt: bytes) -> str:
    """Genera hash scrypt de un password con salt dado."""
    h = hashlib.scrypt(password.encode(), salt=salt, n=16384, r=8, p=1, dklen=32)
    return salt.hex() + ":" + h.hex()


def _verify_password(password: str, stored_hash: str) -> bool:
    """Verifica un password contra su hash scrypt (salt:hash)."""
    if ":" not in stored_hash:
        return False
    salt_hex, hash_hex = stored_hash.split(":", 1)
    try:
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(hash_hex)
    except ValueError:
        return False
    h = hashlib.scrypt(password.encode(), salt=salt, n=16384, r=8, p=1, dklen=32)
    return hmac.compare_digest(h, expected)


def hash_password_for_storage(password: str) -> str:
    """Genera un hash scrypt listo para guardar en secrets.toml.

    Uso: python -c "from streamlit_app.utils.auth import hash_password_for_storage; print(hash_password_for_storage('mi_password'))"
    """
    salt = os.urandom(16)
    return _hash_password(password, salt)


def check_login(username: str, password: str) -> dict | None:
    """Verifica credenciales. Soporta password_hash (scrypt) y password (legacy plaintext)."""
    user = get_user(username)
    if not user:
        # Timing constante: hashear igualmente para no revelar si el usuario existe
        _hash_password(password, os.urandom(16))
        return None

    # Preferir password_hash (scrypt); fallback a password (plaintext legacy)
    stored_hash = user.get("password_hash", "")
    if stored_hash:
        if not _verify_password(password, stored_hash):
            return None
    else:
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
