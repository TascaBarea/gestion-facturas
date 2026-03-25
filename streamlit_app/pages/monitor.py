"""
Monitor Sistema — Estado de los procesos automáticos.
"""

from datetime import datetime, timedelta

import streamlit as st
from utils.auth import require_role
from utils.data_client import get_monitor, ultima_actualizacion

require_role(["admin"])

st.title("Monitor Sistema")
st.sidebar.caption(f"Datos: {ultima_actualizacion()}")

datos = get_monitor()

if not datos or "procesos" not in datos:
    st.info("Datos de monitor no disponibles. Se generarán tras la próxima ejecución semanal.")
    st.stop()

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
            estado = "🟢"
            estado_texto = "OK"
        elif dias <= config["max_dias"] * 2:
            estado = "🟡"
            estado_texto = "Atención"
        else:
            estado = "🔴"
            estado_texto = "Sin ejecutar"
        fecha_str = fecha_dt.strftime("%d/%m/%Y %H:%M")
        dias_str = f"hace {dias} día{'s' if dias != 1 else ''}"
    else:
        estado = "⚪"
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
