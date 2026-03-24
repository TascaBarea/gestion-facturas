"""
Alta de Evento / Taller / Cata en WooCommerce.
Conversión del CLI alta_evento.py a formulario Streamlit.
"""

import streamlit as st
from datetime import datetime, date
from utils.auth import require_role

require_role(["admin", "eventos"])

from utils.wc_client import get_wc_api, cargar_tipos_evento, crear_producto

st.title("Alta de Evento")
st.markdown("Crea talleres, catas y eventos en la tienda online de Comestibles Barea.")

# ── Conexión WooCommerce ─────────────────────────────────────────────────────

try:
    wc = get_wc_api()
except Exception as e:
    st.error(f"Error conectando con WooCommerce: {e}")
    st.stop()


# ── Cargar tipos de evento (cacheado por sesión) ─────────────────────────────

@st.cache_data(ttl=300)
def _tipos_evento():
    _wc = get_wc_api()
    return cargar_tipos_evento(_wc)


tipos = _tipos_evento()

# ── Formulario ───────────────────────────────────────────────────────────────

with st.form("form_evento"):
    st.subheader("Datos del evento")

    # Nombres basados en eventos existentes en WC + opción libre
    opciones_evento = tipos + ["Otro (escribir)"]
    seleccion_nombre = st.selectbox("Tipo de evento", opciones_evento)

    nombre_libre = ""
    if seleccion_nombre == "Otro (escribir)":
        nombre_libre = st.text_input(
            "Nombre del evento (sin fecha)",
            placeholder="Ej: Cata de vinos naturales",
        )

    nombre_base = nombre_libre if seleccion_nombre == "Otro (escribir)" else seleccion_nombre

    col1, col2 = st.columns(2)
    with col1:
        fecha = st.date_input(
            "Fecha del evento",
            value=None,
            min_value=date.today(),
            format="DD/MM/YYYY",
        )
    with col2:
        precio_str = st.text_input(
            "Precio por persona (€)",
            placeholder="35,50",
        )

    st.subheader("Horario")
    col3, col4 = st.columns(2)
    with col3:
        hora_inicio = st.time_input("Hora de inicio", value=None)
    with col4:
        hora_fin = st.time_input("Hora de fin", value=None)

    st.subheader("Detalles")

    plazas = st.number_input(
        "Número de plazas",
        min_value=1,
        max_value=30,
        value=10,
        step=1,
    )

    desc_extra = st.text_area(
        "Descripción adicional (opcional)",
        placeholder="Incluye degustación de 6 vinos y maridaje",
    )

    submitted = st.form_submit_button("Publicar evento", type="primary")

# ── Procesamiento ────────────────────────────────────────────────────────────

if submitted:
    # Validaciones
    errores = []
    if not nombre_base or not nombre_base.strip():
        errores.append("El nombre del evento es obligatorio.")
    if fecha is None:
        errores.append("La fecha es obligatoria.")

    # Precio
    precio = None
    if not precio_str or not precio_str.strip():
        errores.append("El precio es obligatorio.")
    else:
        try:
            precio = float(precio_str.strip().replace(",", "."))
            if precio <= 0:
                errores.append("El precio debe ser positivo.")
        except ValueError:
            errores.append(f"Precio inválido: '{precio_str}'.")

    if errores:
        for e in errores:
            st.error(e)
        st.stop()

    # Aviso si plazas fuera del rango habitual (7-11)
    plazas_inusuales = plazas < 7 or plazas > 11
    if plazas_inusuales:
        if plazas < 7:
            st.warning(f"Has puesto **{plazas} plazas**. Es menos de lo habitual (7-11).")
        else:
            st.warning(f"Has puesto **{plazas} plazas**. Es más de lo habitual (7-11).")
        confirmado = st.checkbox("Confirmo que el número de plazas es correcto")
        if not confirmado:
            st.stop()

    # Construir nombre: "Cata de vinos 28/03/26"
    fecha_yy = fecha.strftime("%d/%m/%y")
    nombre_producto = f"{nombre_base.strip()} {fecha_yy}"

    # Construir descripción
    partes_desc = []
    if hora_inicio:
        horario = f"HORARIO: de {hora_inicio.strftime('%H:%M')}"
        if hora_fin:
            horario += f" a {hora_fin.strftime('%H:%M')}"
        partes_desc.append(horario)
    if desc_extra and desc_extra.strip():
        partes_desc.append(desc_extra.strip())
    descripcion = "\n".join(partes_desc)

    # Resumen antes de publicar
    st.markdown("---")
    st.subheader("Resumen")
    col_r1, col_r2 = st.columns(2)
    with col_r1:
        st.markdown(f"**Nombre:** {nombre_producto}")
        st.markdown(f"**Fecha:** {fecha.strftime('%d/%m/%Y')}")
        if hora_inicio:
            horario_txt = hora_inicio.strftime("%H:%M")
            if hora_fin:
                horario_txt += f" a {hora_fin.strftime('%H:%M')}"
            st.markdown(f"**Horario:** {horario_txt}")
    with col_r2:
        st.markdown(f"**Precio:** {precio:.2f} €".replace(".", ","))
        st.markdown(f"**Plazas:** {plazas}")

    # Crear producto en WooCommerce
    payload = {
        "name": nombre_producto,
        "type": "simple",
        "status": "publish",
        "regular_price": str(precio),
        "description": descripcion,
        "manage_stock": True,
        "stock_quantity": plazas,
        "stock_status": "instock",
    }

    with st.spinner("Publicando en WooCommerce..."):
        resultado = crear_producto(wc, payload)

    if "id" in resultado:
        st.success(f"Evento publicado correctamente (ID: {resultado['id']})")
        url = resultado.get("permalink", "")
        if url:
            st.markdown(f"[Ver en la tienda]({url})")
        st.info("Aparecerá en el email semanal del próximo lunes.")
        # Limpiar cache de categorías por si se creó una nueva
        _tipos_evento.clear()
    else:
        msg = resultado.get("message", str(resultado))
        st.error(f"Error de WooCommerce: {msg}")
