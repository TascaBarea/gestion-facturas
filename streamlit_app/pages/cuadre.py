"""
Cuadre Bancario — Resumen de clasificación de movimientos.
"""

import streamlit as st
import pandas as pd
from utils.auth import require_role
from utils.data_client import get_cuadre, ultima_actualizacion

require_role(["admin"])

st.title("Cuadre Bancario")
st.sidebar.caption(f"Datos: {ultima_actualizacion()}")

datos = get_cuadre()

if not datos:
    st.info("Datos de cuadre no disponibles. Se generarán tras la próxima ejecución de cuadre.py.")
    st.stop()

# ── KPIs ──
st.caption(f"Archivo: {datos.get('archivo', '?')} · Ejecutado: {datos.get('fecha_ejecucion', '?')[:16]}")

total = datos.get("total", {})
col1, col2, col3 = st.columns(3)
col1.metric("Total movimientos", f"{total.get('total', 0):,}")
col2.metric("Clasificados", f"{total.get('ok', 0):,}",
            delta=f"{total.get('pct_ok', 0):.1f}%")
col3.metric("A revisar", f"{total.get('revisar', 0):,}",
            delta=f"-{100 - total.get('pct_ok', 0):.1f}%", delta_color="inverse")

# ── Detalle por hoja ──
st.subheader("Detalle por cuenta")

hojas = datos.get("hojas", {})
for nombre, stats in hojas.items():
    with st.expander(f"{nombre} — {stats.get('total', 0)} movimientos"):
        c1, c2, c3 = st.columns(3)
        c1.metric("Clasificados", stats.get("ok", 0))
        c2.metric("A revisar", stats.get("revisar", 0))
        c3.metric("% clasificado", f"{stats.get('pct_ok', 0):.1f}%")

# ── Tabla REVISAR ──
revisar = datos.get("revisar_detalle", [])
if revisar:
    st.subheader(f"Movimientos a revisar ({len(revisar)})")
    df = pd.DataFrame(revisar)
    if "importe" in df.columns:
        df["importe"] = df["importe"].apply(lambda x: f"{x:,.2f} €")
    st.dataframe(df, use_container_width=True, hide_index=True)
else:
    st.success("No hay movimientos pendientes de revisión.")
