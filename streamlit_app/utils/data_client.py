"""
data_client.py — Cliente de datos para Streamlit.
Modo dual: intenta API backend primero, fallback a GitHub Pages CDN.
"""

import json
import logging
import urllib.request
import ssl
import streamlit as st

logger = logging.getLogger(__name__)


def _get_cdn_base() -> str:
    """URL base de GitHub Pages CDN (fallback cuando el backend no está disponible)."""
    return st.secrets.get("NETLIFY_DATA_URL", "")


def _get_backend_url() -> str:
    """URL del backend FastAPI (vacío = no configurado)."""
    return st.secrets.get("BACKEND_URL", "")


def _get_api_key() -> str:
    """API key para autenticar con el backend."""
    return st.secrets.get("API_KEY", "")


def _ssl_context():
    """Contexto SSL para Streamlit Cloud.

    Usa verificación estándar. Si hay problemas con certificados de Cloudflare
    tunnel, se puede configurar BACKEND_SSL_VERIFY=false en secrets (no recomendado).
    """
    if st.secrets.get("BACKEND_SSL_VERIFY", "true").lower() == "false":
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        return ctx
    return ssl.create_default_context()


def _fetch_from_backend(filename: str) -> dict | None:
    """Intenta obtener JSON del backend FastAPI."""
    base = _get_backend_url()
    if not base:
        return None
    url = f"{base}/api/data/{filename}"
    headers = {"User-Agent": "TascaBarea/1.0"}
    api_key = _get_api_key()
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=5, context=_ssl_context()) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        logger.debug(f"Backend no disponible ({url}): {e}")
        return None


def _fetch_from_cdn(filename: str) -> dict | None:
    """Descarga JSON desde GitHub Pages CDN (fallback)."""
    base = _get_cdn_base()
    if not base:
        logger.warning("NETLIFY_DATA_URL (CDN) no configurado en secrets")
        return None
    url = f"{base}/data/{filename}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "TascaBarea/1.0"})
        with urllib.request.urlopen(req, timeout=15, context=_ssl_context()) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        logger.error(f"Error fetching {url}: {e}")
        return None


@st.cache_data(ttl=3600)
def _fetch_json(filename: str) -> dict | None:
    """Obtiene JSON: API backend primero, Netlify como fallback."""
    data = _fetch_from_backend(filename)
    if data is not None:
        return data
    return _fetch_from_cdn(filename)


def backend_disponible() -> bool:
    """Comprueba si el backend FastAPI responde al health check."""
    base = _get_backend_url()
    if not base:
        return False
    try:
        req = urllib.request.Request(
            f"{base}/health",
            headers={"User-Agent": "TascaBarea/1.0"},
        )
        with urllib.request.urlopen(req, timeout=3, context=_ssl_context()) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data.get("status") == "ok"
    except Exception:
        return False


def fetch_backend_json(path: str, timeout: int = 5) -> dict | None:
    """Llama a un endpoint del backend directamente (sin cache, sin fallback)."""
    base = _get_backend_url()
    if not base:
        return None
    url = f"{base}{path}"
    headers = {"User-Agent": "TascaBarea/1.0"}
    api_key = _get_api_key()
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=timeout, context=_ssl_context()) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        logger.debug(f"Backend call failed ({url}): {e}")
        return None


def put_backend_json(path: str, body: dict, timeout: int = 10) -> dict | None:
    """PUT JSON al backend. Devuelve respuesta o None si falla."""
    base = _get_backend_url()
    if not base:
        return None
    url = f"{base}{path}"
    headers = {"User-Agent": "TascaBarea/1.0", "Content-Type": "application/json"}
    api_key = _get_api_key()
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    try:
        data = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers=headers, method="PUT")
        with urllib.request.urlopen(req, timeout=timeout, context=_ssl_context()) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8", errors="replace")
        logger.error(f"PUT {url} → {e.code}: {error_body}")
        try:
            return {"error": True, "status": e.code, "detail": json.loads(error_body).get("detail", error_body)}
        except Exception:
            return {"error": True, "status": e.code, "detail": error_body}
    except Exception as e:
        logger.error(f"PUT {url} failed: {e}")
        return None


def post_backend_json(path: str, body: dict, timeout: int = 10) -> dict | None:
    """POST JSON al backend. Devuelve respuesta o None si falla."""
    base = _get_backend_url()
    if not base:
        return None
    url = f"{base}{path}"
    headers = {"User-Agent": "TascaBarea/1.0", "Content-Type": "application/json"}
    api_key = _get_api_key()
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    try:
        data = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=timeout, context=_ssl_context()) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8", errors="replace")
        logger.error(f"POST {url} → {e.code}: {error_body}")
        try:
            return {"error": True, "status": e.code, "detail": json.loads(error_body).get("detail", error_body)}
        except Exception:
            return {"error": True, "status": e.code, "detail": error_body}
    except Exception as e:
        logger.error(f"POST {url} failed: {e}")
        return None


# ── API pública (misma interfaz que antes) ────────────────────────────────────

def get_meta() -> dict | None:
    return _fetch_json("meta.json")

def get_ventas_comes() -> dict | None:
    return _fetch_json("ventas_comes.json")

def get_ventas_tasca() -> dict | None:
    return _fetch_json("ventas_tasca.json")

def get_cuadre() -> dict | None:
    return _fetch_json("cuadre.json")

def get_gmail() -> dict | None:
    return _fetch_json("gmail.json")

def get_monitor() -> dict | None:
    return _fetch_json("monitor.json")

def ultima_actualizacion() -> str:
    meta = get_meta()
    if meta and "exportado" in meta:
        return meta["exportado"].replace("T", " ")[:16]
    return "Desconocido"
