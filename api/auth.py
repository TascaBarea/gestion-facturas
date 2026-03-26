"""
api/auth.py — Dependencia de autenticación por API key.
"""

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from api.config import API_KEY

_security = HTTPBearer(auto_error=False)


async def require_api_key(
    credentials: HTTPAuthorizationCredentials | None = Depends(_security),
):
    """Valida Bearer token. Si API_KEY está vacía, permite todo (dev local)."""
    if not API_KEY:
        return  # Sin key configurada → modo desarrollo
    if credentials is None or credentials.credentials != API_KEY:
        raise HTTPException(status_code=401, detail="API key inválida")
