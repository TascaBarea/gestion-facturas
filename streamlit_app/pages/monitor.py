"""
Monitor Sistema — Estado de los procesos automáticos.
Usa datos en vivo del backend cuando está disponible, fallback a JSON cacheado.
"""

from datetime import datetime

import streamlit as st
from utils.auth import require_role
from utils.data_client import (
    backend_disponible, fetch_backend_json, get_monitor, ultima_actualizacion,
)

require_role(["admin"])

st.title("Monitor Sistema")

# ── Obtener datos: en vivo o cacheados ───────────────────────────────────────

en_vivo = False
datos = None

if backend_disponible():
    datos = fetch_backend_json("/api/status")
    if datos:
        en_vivo = True

if not datos:
    datos = get_monitor()

if en_vivo:
    st.sidebar.success("Datos en vivo", icon="\U0001f4e1")
else:
    st.sidebar.caption(f"Datos: {ultima_actualizacion()}")

if not datos or "procesos" not in datos:
    st.info("Datos de monitor no disponibles. Se generarán tras la próxima ejecución semanal.")
    st.stop()

# ── Alertas activas ──────────────────────────────────────────────────────────

if en_vivo:
    alertas = fetch_backend_json("/api/alerts")
    if alertas and alertas.get("alerts"):
        for alerta in alertas["alerts"]:
            icono = "\u26a0\ufe0f" if alerta["level"] == "warning" else "\u274c"
            nombre = alerta["module"].capitalize()
            if alerta["level"] == "error":
                st.error(f"{icono} {nombre}: {alerta['message']}")
            else:
                st.warning(f"{icono} {nombre}: {alerta['message']}")

# ── Tarjetas de procesos ─────────────────────────────────────────────────────

PROCESOS_CONFIG = {
    "ventas": {"nombre": "Ventas (script_barea.py)", "frecuencia": "Lunes 03:00", "max_dias": 9},
    "gmail": {"nombre": "Gmail (gmail.py)", "frecuencia": "Viernes 03:00", "max_dias": 9},
    "cuadre": {"nombre": "Cuadre (cuadre.py)", "frecuencia": "Manual (mensual)", "max_dias": 45},
}

ahora = datetime.now()

for clave, config in PROCESOS_CONFIG.items():
    proc = datos["procesos"].get(clave, {})
    ultima = proc.get("ultima_ejecucion", "")

    # Parsear fecha
    fecha_dt = None
    if ultima:
        for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
            try:
                fecha_dt = datetime.strptime(ultima[:19], fmt)
                break
            except ValueError:
                continue

    # Calcular estado
    if fecha_dt:
        dias = (ahora - fecha_dt).days
        if dias <= config["max_dias"]:
            estado = "\U0001f7e2"
            estado_texto = "OK"
        elif dias <= config["max_dias"] * 2:
            estado = "\U0001f7e1"
            estado_texto = "Atención"
        else:
            estado = "\U0001f534"
            estado_texto = "Sin ejecutar"
        fecha_str = fecha_dt.strftime("%d/%m/%Y %H:%M")
        dias_str = f"hace {dias} día{'s' if dias != 1 else ''}"
    else:
        estado = "\u26aa"
        estado_texto = "Sin datos"
        fecha_str = "—"
        dias_str = ""

    with st.container(border=True):
        col1, col2, col3 = st.columns([3, 2, 1])
        col1.markdown(f"**{config['nombre']}**")
        col1.caption(f"Frecuencia: {config['frecuencia']}")
        col2.markdown(f"{fecha_str}")
        if dias_str:
            col2.caption(dias_str)
        col3.markdown(f"### {estado}")
        col3.caption(estado_texto)

    # Mostrar últimas líneas del log si hay datos en vivo
    if en_vivo and proc.get("ultimas_lineas"):
        with st.expander(f"Últimas líneas del log — {config['nombre']}"):
            st.code("\n".join(proc["ultimas_lineas"]), language="text")
