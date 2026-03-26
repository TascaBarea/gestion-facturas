"""
pages/ejecutar.py — Panel de ejecución de scripts (solo admin).
Permite lanzar gmail, ventas, dashboard y cuadre desde la app.
"""

import json
import time
import urllib.request
import ssl

import streamlit as st
from utils.auth import require_role
from utils.data_client import _get_backend_url, _get_api_key, _ssl_context

require_role(["admin"])

st.title("Ejecutar scripts")

# ── Comprobar backend ─────────────────────────────────────────────────────────

BACKEND = _get_backend_url()
API_KEY = _get_api_key()

if not BACKEND:
    st.error("BACKEND_URL no configurado en secrets. No se pueden ejecutar scripts.")
    st.stop()


def _api_call(method: str, path: str, timeout: int = 10, data: bytes | None = None,
              content_type: str | None = None) -> dict | None:
    """Llama al backend API. Devuelve dict o None si falla."""
    url = f"{BACKEND}{path}"
    headers = {"User-Agent": "TascaBarea/1.0"}
    if API_KEY:
        headers["Authorization"] = f"Bearer {API_KEY}"
    if content_type:
        headers["Content-Type"] = content_type
    try:
        req = urllib.request.Request(url, headers=headers, method=method, data=data)
        with urllib.request.urlopen(req, timeout=timeout, context=_ssl_context()) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        st.error(f"Error API: {e}")
        return None


def _check_backend() -> bool:
    """Verifica que el backend responde."""
    result = _api_call("GET", "/health", timeout=3)
    return result is not None and result.get("status") == "ok"


if not _check_backend():
    st.warning("El backend no responde. El PC puede estar apagado.")
    st.stop()

st.success("Backend conectado", icon="\U0001f7e2")

# ── Scripts disponibles ───────────────────────────────────────────────────────

SCRIPTS_UI = {
    "gmail": {
        "nombre": "Gmail (produccion)",
        "descripcion": "Procesar emails y facturas pendientes",
        "icono": "\U0001f4e7",
        "color": "#1a73e8",
    },
    "gmail_test": {
        "nombre": "Gmail (test)",
        "descripcion": "Modo test: procesa sin modificar archivos",
        "icono": "\U0001f9ea",
        "color": "#7b1fa2",
    },
    "ventas": {
        "nombre": "Ventas semanales",
        "descripcion": "Descargar ventas Loyverse + WooCommerce",
        "icono": "\U0001f4ca",
        "color": "#2e7d32",
    },
    "dashboard": {
        "nombre": "Dashboard",
        "descripcion": "Generar HTML + PDF (meses cerrados)",
        "icono": "\U0001f4c8",
        "color": "#e65100",
    },
    "dashboard_email": {
        "nombre": "Dashboard + Email",
        "descripcion": "Generar dashboards y enviar por email",
        "icono": "\U0001f4e8",
        "color": "#c62828",
    },
    "cuadre": {
        "nombre": "Cuadre bancario",
        "descripcion": "Clasificar movimientos (requiere archivo Excel)",
        "icono": "\U0001f3e6",
        "color": "#0d47a1",
        "requires_file": True,
    },
}

# ── Estado de la sesion ───────────────────────────────────────────────────────

if "active_job_id" not in st.session_state:
    st.session_state.active_job_id = None

# ── UI: tarjetas de scripts ──────────────────────────────────────────────────

# Comprobar si hay un job en curso
scripts_info = _api_call("GET", "/api/scripts")
running = scripts_info.get("running") if scripts_info else None

if running:
    st.session_state.active_job_id = running["job_id"]

# Si hay un job activo, mostrar su progreso
if st.session_state.active_job_id:
    job = _api_call("GET", f"/api/jobs/{st.session_state.active_job_id}?full_log=true")
    if job:
        status = job["status"]
        script_name = job.get("script", "")
        ui = SCRIPTS_UI.get(script_name, {})

        if status == "running":
            st.subheader(f"{ui.get('icono', '')} {ui.get('nombre', script_name)} en curso...")
            with st.spinner("Ejecutando..."):
                # Mostrar log en vivo
                log_container = st.empty()
                while True:
                    job = _api_call("GET", f"/api/jobs/{st.session_state.active_job_id}?full_log=true")
                    if not job:
                        break
                    log_text = "\n".join(job.get("log", []))
                    log_container.code(log_text, language="text")
                    if job["status"] != "running":
                        break
                    time.sleep(3)

            # Job terminado
            if job and job["status"] == "completed":
                st.success(f"Completado (exit code: {job.get('exit_code', '?')})")
            elif job and job["status"] == "failed":
                st.error(f"Error: {job.get('error', 'desconocido')}")

            st.session_state.active_job_id = None
            st.rerun()

        elif status in ("completed", "failed"):
            # Mostrar resultado del último job
            if status == "completed":
                st.success(f"{ui.get('icono', '')} {ui.get('nombre', script_name)} completado")
            else:
                st.error(f"{ui.get('icono', '')} {ui.get('nombre', script_name)} falló: {job.get('error', '')}")

            with st.expander("Ver log completo"):
                st.code("\n".join(job.get("log", [])), language="text")

            if st.button("Cerrar"):
                st.session_state.active_job_id = None
                st.rerun()
            st.stop()

# ── Tarjetas de scripts ──────────────────────────────────────────────────────

st.markdown("---")

# Upload de archivo para cuadre
uploaded_file = None

cols = st.columns(2)
for i, (script_id, ui) in enumerate(SCRIPTS_UI.items()):
    with cols[i % 2]:
        with st.container(border=True):
            st.markdown(
                f"### {ui['icono']} {ui['nombre']}\n"
                f"<p style='color:#888;font-size:0.85rem'>{ui['descripcion']}</p>",
                unsafe_allow_html=True,
            )

            if ui.get("requires_file"):
                uploaded_file = st.file_uploader(
                    "Archivo Excel de movimientos",
                    type=["xlsx", "xls"],
                    key=f"upload_{script_id}",
                )
                can_run = uploaded_file is not None
            else:
                can_run = True

            if st.button(
                f"Ejecutar",
                key=f"btn_{script_id}",
                disabled=not can_run or running is not None,
                type="primary",
                use_container_width=True,
            ):
                # Si es cuadre, primero subir archivo
                extra_path = ""
                if ui.get("requires_file") and uploaded_file:
                    # Subir archivo al backend
                    boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
                    body = (
                        f"--{boundary}\r\n"
                        f'Content-Disposition: form-data; name="file"; filename="{uploaded_file.name}"\r\n'
                        f"Content-Type: application/octet-stream\r\n\r\n"
                    ).encode("utf-8")
                    body += uploaded_file.getvalue()
                    body += f"\r\n--{boundary}--\r\n".encode("utf-8")

                    upload_result = _api_call(
                        "POST", "/api/upload/n43",
                        data=body,
                        content_type=f"multipart/form-data; boundary={boundary}",
                        timeout=30,
                    )
                    if upload_result and "path" in upload_result:
                        extra_path = f"?archivo={upload_result['path']}"
                    else:
                        st.error("Error subiendo archivo")
                        st.stop()

                result = _api_call("POST", f"/api/scripts/{script_id}{extra_path}")
                if result and "job_id" in result:
                    st.session_state.active_job_id = result["job_id"]
                    st.rerun()

# ── Historial de jobs ─────────────────────────────────────────────────────────

st.markdown("---")
with st.expander("Historial de ejecuciones"):
    jobs = _api_call("GET", "/api/jobs?limit=10")
    if jobs and jobs.get("jobs"):
        for j in jobs["jobs"]:
            status_icon = {
                "completed": "\u2705",
                "failed": "\u274c",
                "running": "\u23f3",
                "pending": "\u23f3",
            }.get(j["status"], "\u2753")
            ui = SCRIPTS_UI.get(j.get("script", ""), {})
            nombre = ui.get("nombre", j.get("script", "?"))
            st.text(
                f"{status_icon} {nombre} | "
                f"{j.get('created_at', '?')} | "
                f"exit: {j.get('exit_code', '-')}"
            )
    else:
        st.info("Sin ejecuciones recientes")
