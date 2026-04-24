"""
config/loader.py — Wrapper unificado para acceso a configuración sensible.

Estrategia de lookup (en este orden):
  1) Streamlit secrets — `st.secrets` (tascabarea.streamlit.app).
  2) Variables de entorno del proceso.
  3) `config/datos_sensibles.py` (dev local + VPS; gitignored).
  4) `default` pasado a la llamada.

La última capa (datos_sensibles.py) solo existe en PC y en el VPS donde lo
copiamos manualmente; en Streamlit Cloud no está → `get()` cae a env o default
sin romper el import.

Motivo de existir: `config/settings.py` necesitaba `from config.datos_sensibles
import CIF_PROPIO` sin try/except. En Streamlit Cloud eso disparaba
`ModuleNotFoundError` al importar `nucleo/__init__.py` (vía
nucleo.validacion → config.settings). Con este loader, la ausencia del
archivo legacy es benigna.

Uso:
    from config.loader import get
    CIF_PROPIO = get("CIF_PROPIO", "")
"""
from __future__ import annotations

import os
from typing import Any

try:
    import streamlit as _st  # type: ignore
    _SECRETS_OBJ = getattr(_st, "secrets", None)
except Exception:
    _SECRETS_OBJ = None


def _from_secrets(key: str) -> Any:
    """Lee `key` de st.secrets si está disponible. None si no."""
    if _SECRETS_OBJ is None:
        return None
    try:
        # st.secrets tiene API dict-like con __contains__/__getitem__.
        # Si Streamlit no está en modo runtime (p.ej. pytest), puede lanzar.
        if key in _SECRETS_OBJ:
            return _SECRETS_OBJ[key]
    except Exception:
        return None
    return None


def _from_legacy(key: str, default: Any) -> Any:
    """Intenta leer `key` de config/datos_sensibles.py. Devuelve `default` si
    el módulo no existe o no tiene el atributo."""
    try:
        from config import datos_sensibles  # type: ignore
    except ModuleNotFoundError:
        return default
    return getattr(datos_sensibles, key, default)


def get(key: str, default: Any = None) -> Any:
    """Resuelve `key` según la cascada secrets → env → legacy → default."""
    val = _from_secrets(key)
    if val is not None:
        return val
    val = os.environ.get(key)
    if val is not None:
        return val
    return _from_legacy(key, default)
