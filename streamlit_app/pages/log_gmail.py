"""
Log Gmail — Resumen de la última ejecución del procesador de facturas.
Incluye mini-cola de facturas pendientes de ubicación (v1.18 ventana de gracia).
"""

import json
import os
import sys
import streamlit as st
from datetime import date
from pathlib import Path

from utils.auth import require_role
from utils.data_client import get_gmail, ultima_actualizacion

require_role(["admin"])

# Asegurar directorio raíz en sys.path
_ROOT = str(Path(__file__).resolve().parent.parent.parent)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

st.title("Log Gmail")
st.sidebar.caption(f"Datos: {ultima_actualizacion()}")

datos = get_gmail()

if not datos:
    st.info("Datos de Gmail no disponibles. Se generarán tras la próxima ejecución de gmail.py.")
    st.stop()

# ── KPIs ──
fecha = datos.get("fecha_ejecucion", "?")[:16].replace("T", " ")
st.caption(f"Última ejecución: {fecha}")

col1, col2, col3, col4 = st.columns(4)
col1.metric("Procesados", datos.get("total_procesados", 0))
col2.metric("Exitosos", datos.get("exitosos", 0))
col3.metric("Revisión", datos.get("requieren_revision", 0))
col4.metric("Errores", datos.get("errores", 0))

# v1.18: KPIs ventana de gracia
gracia = datos.get("facturas_gracia", 0)
pendientes_count = datos.get("facturas_pendientes", 0)
if gracia > 0 or pendientes_count > 0:
    col5, col6 = st.columns(2)
    if gracia > 0:
        col5.metric("Ventana gracia", gracia)
    if pendientes_count > 0:
        col6.metric("Pendientes ubicación", pendientes_count)

# ── Proveedores procesados ──
proveedores_ok = datos.get("proveedores_ok", [])
if proveedores_ok:
    with st.expander(f"Proveedores OK ({len(proveedores_ok)})"):
        for p in proveedores_ok:
            st.write(f"- {p}")

# ── Requieren revisión ──
revision = datos.get("revision", [])
if revision:
    with st.expander(f"Requieren revisión ({len(revision)})", expanded=True):
        for r in revision:
            st.write(f"- {r}")

# ── Errores ──
errores = datos.get("errores_detalle", [])
if errores:
    st.subheader("Errores")
    for e in errores:
        st.error(e)


# ============================================================================
# v1.18: FACTURAS PENDIENTES DE UBICACIÓN (ventana de gracia trimestral)
# ============================================================================

COLA_PATH = Path(os.environ.get(
    "GESTION_FACTURAS_DIR",
    str(Path(__file__).resolve().parent.parent.parent)
)) / "datos" / "facturas_pendientes.json"


def _cargar_pendientes():
    if not COLA_PATH.exists():
        return []
    with open(COLA_PATH, 'r', encoding='utf-8') as f:
        cola = json.load(f)
    return [f for f in cola if f.get('estado') == 'pendiente']


def _resolver_pendiente(factura: dict, destino: str):
    """Sube el PDF a Dropbox según la decisión del usuario y actualiza la cola."""
    pdf_path = Path(factura.get('ruta_pdf_temporal', ''))
    if not pdf_path.exists():
        st.error(f"PDF no encontrado: {pdf_path}")
        return

    pdf_bytes = pdf_path.read_bytes()

    if destino == 'GRACIA':
        carpeta = factura['opciones']['trimestre_anterior']['carpeta']
        nombre = factura['opciones']['trimestre_anterior']['nombre']
    else:  # ATRASADA
        carpeta = factura['opciones']['atrasada']['carpeta']
        nombre = factura['opciones']['atrasada']['nombre']

    # Subir a Dropbox
    try:
        from gmail.dropbox_selector import obtener_cliente_dropbox
        from gmail.gmail import CONFIG

        cliente = obtener_cliente_dropbox(CONFIG)
        if cliente:
            from datetime import datetime
            # Construir fecha_factura y fecha_ejecucion para la interfaz del cliente
            fecha_fac = datetime.strptime(factura['fecha_factura'], '%Y-%m-%d')
            fecha_proc = datetime.strptime(factura['fecha_proceso'], '%Y-%m-%d')
            ruta, _ = cliente.subir_archivo(pdf_bytes, nombre, fecha_fac, fecha_proc, destino=destino)
            st.success(f"{nombre} subido a {carpeta}")
        else:
            st.warning(f"Dropbox no disponible. PDF guardado en: {pdf_path}")
    except Exception as e:
        st.error(f"Error subiendo a Dropbox: {e}")
        return

    # Actualizar cola JSON
    cola = json.load(open(COLA_PATH, 'r', encoding='utf-8'))
    for f in cola:
        if f.get('id') == factura['id']:
            f['estado'] = 'resuelto'
            f['resuelto_por'] = 'streamlit'
            f['fecha_resolucion'] = date.today().isoformat()
            f['destino_final'] = destino
            break

    tmp = COLA_PATH.with_suffix('.tmp')
    with open(tmp, 'w', encoding='utf-8') as fout:
        json.dump(cola, fout, ensure_ascii=False, indent=2)
    tmp.replace(COLA_PATH)

    # Borrar PDF temporal
    pdf_path.unlink(missing_ok=True)


st.divider()
st.subheader("Facturas pendientes de ubicación")

pendientes = _cargar_pendientes()

if pendientes:
    st.warning(f"{len(pendientes)} factura(s) pendientes de ubicación")

    for factura in pendientes:
        with st.container(border=True):
            col_info, col_btn1, col_btn2 = st.columns([4, 2, 2])

            with col_info:
                st.markdown(f"**{factura.get('archivo_renombrado', '?')}**")
                st.caption(
                    f"Proveedor: {factura.get('proveedor', '?')} · "
                    f"Fecha: {factura.get('fecha_factura', '?')} · "
                    f"Total: {factura.get('total', '?')} · "
                    f"Día {factura.get('dia_proceso', '?')} del {factura.get('trimestre_actual', '?')}"
                )

            with col_btn1:
                carpeta_ant = factura.get('opciones', {}).get('trimestre_anterior', {}).get('carpeta', '?')
                if st.button(
                    f"Trim. anterior ({carpeta_ant})",
                    key=f"gracia_{factura['id']}",
                    type="primary",
                ):
                    _resolver_pendiente(factura, 'GRACIA')
                    st.rerun()

            with col_btn2:
                if st.button(
                    f"ATRASADA ({factura.get('trimestre_actual', '?')})",
                    key=f"atrasada_{factura['id']}",
                ):
                    _resolver_pendiente(factura, 'ATRASADA')
                    st.rerun()
else:
    st.success("No hay facturas pendientes de ubicación")
