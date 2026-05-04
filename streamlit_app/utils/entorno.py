"""Detección del entorno de ejecución (local vs Streamlit Cloud)."""
from __future__ import annotations

import os
import socket
from pathlib import Path


def es_streamlit_cloud() -> bool:
    """True si la app está corriendo en Streamlit Community Cloud.

    Streamlit Cloud monta el repo en /mount/src/<repo>/ y expone
    HOSTNAME tipo 'streamlit-...'. Detectamos por ambos signos para
    ser robustos ante cambios futuros.
    """
    try:
        if Path("/mount/src").exists():
            return True
    except (PermissionError, OSError):
        pass
    hostname = socket.gethostname().lower()
    if hostname.startswith("streamlit"):
        return True
    if os.getenv("STREAMLIT_SHARING_MODE") or os.getenv("STREAMLIT_RUNTIME_ENV"):
        return True
    return False


def ruta_existe_seguro(ruta: str | Path) -> bool:
    """Path.exists() que NO lanza PermissionError ni OSError.

    En Streamlit Cloud rutas locales del PC (G:\\..., Dropbox local)
    pueden lanzar PermissionError en lugar de devolver False.
    """
    try:
        return Path(ruta).exists()
    except (PermissionError, OSError, ValueError):
        return False


def scripts_solo_local() -> set[str]:
    """Scripts cuya ejecución solo tiene sentido en el PC local de Jaime
    o en el VPS Contabo (no en Streamlit Cloud).

    Mantén esta lista sincronizada con SPEC_GESTION_FACTURAS_v4.x.
    """
    return {
        "gmail.py",
        "script_barea.py",
        "main.py",          # PARSEO
        "cuadre.py",
        "generar_dashboard.py",
        "actualizar_movimientos.py",
        "validacion.py",
    }
