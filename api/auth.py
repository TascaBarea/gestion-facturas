"""
api/auth.py — Dependencia de autenticación por API key con roles.

Dos niveles:
- API_KEY (admin): lectura + escritura (ejecutar scripts, modificar MAESTRO, uploads)
- API_KEY_READONLY: solo lectura (consultar status, datos, listas)
"""

import logging

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from api.config import API_KEY, API_KEY_READONLY, DEV_MODE

logger = logging.getLogger(__name__)

_security = HTTPBearer(auto_error=False)


def _check_dev_mode():
    """Si no hay keys configuradas, verifica DEV_MODE."""
    if DEV_MODE:
        return
    logger.error("API_KEY no configurada y DEV_MODE no activo")
    raise HTTPException(
        status_code=500,
        detail="API_KEY no configurada. Añadir a api/.env o activar DEV_MODE=true",
    )


def _get_token(credentials: HTTPAuthorizationCredentials | None) -> str | None:
    """Extrae el token del header Authorization."""
    if credentials is None:
        return None
    return credentials.credentials


async def require_api_key(
    credentials: HTTPAuthorizationCredentials | None = Depends(_security),
):
    """Valida Bearer token (admin o readonly). Endpoints de lectura."""
    if not API_KEY and not API_KEY_READONLY:
        _check_dev_mode()
        return

    token = _get_token(credentials)
    valid_keys = {k for k in [API_KEY, API_KEY_READONLY] if k}
    if token not in valid_keys:
        raise HTTPException(status_code=401, detail="API key inválida")


async def require_admin_key(
    credentials: HTTPAuthorizationCredentials | None = Depends(_security),
):
    """Valida Bearer token — solo admin. Endpoints de escritura/ejecución."""
    if not API_KEY:
        _check_dev_mode()
        return

    token = _get_token(credentials)
    if token != API_KEY:
        raise HTTPException(status_code=403, detail="Se requiere API key de admin")
