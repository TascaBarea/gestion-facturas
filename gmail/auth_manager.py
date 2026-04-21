"""
gmail/auth_manager.py — Gestión centralizada de credenciales OAuth2.

Todos los scripts del proyecto que necesitan autenticación Google
deben usar este módulo en vez de cargar token.json manualmente.

Uso:
    from gmail.auth_manager import get_credentials, get_gmail_service

    creds = get_credentials()  # credenciales OAuth2 con auto-refresh
    service = get_gmail_service()  # servicio Gmail listo para usar
    drive = get_drive_service()  # servicio Drive listo para usar
"""

import logging
import os

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

log = logging.getLogger("auth_manager")

# ── Rutas ────────────────────────────────────────────────────────────────────

_GMAIL_DIR = os.path.dirname(os.path.abspath(__file__))
TOKEN_PATH = os.path.join(_GMAIL_DIR, "token.json")
CREDENTIALS_PATH = os.path.join(_GMAIL_DIR, "credentials.json")


def get_credentials():
    """Carga credenciales OAuth2, refresca si han expirado.

    NO se filtran scopes: el token.json dicta qué scopes están autorizados.
    Filtrar aquí provocaba que `creds.to_json()` tras refresh sobrescribiese
    el token con un subconjunto de scopes, perdiendo (p. ej.) `drive`.

    Returns:
        google.oauth2.credentials.Credentials válidas

    Raises:
        FileNotFoundError: si token.json no existe
        RuntimeError: si el token no es válido y no se puede refrescar
    """
    if not os.path.exists(TOKEN_PATH):
        raise FileNotFoundError(
            f"Token no encontrado: {TOKEN_PATH}\n"
            "Ejecutar: python gmail/renovar_token_business.py"
        )

    creds = Credentials.from_authorized_user_file(TOKEN_PATH)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            log.info("Refrescando token OAuth2...")
            creds.refresh(Request())
            with open(TOKEN_PATH, "w") as f:
                f.write(creds.to_json())
            log.info("Token refrescado y guardado")
        else:
            raise RuntimeError(
                "Token OAuth2 no válido y sin refresh_token.\n"
                "Ejecutar: python gmail/renovar_token_business.py"
            )

    return creds


def get_gmail_service():
    """Devuelve servicio Gmail autenticado."""
    return build("gmail", "v1", credentials=get_credentials())


def get_drive_service():
    """Devuelve servicio Drive autenticado."""
    return build("drive", "v3", credentials=get_credentials())
