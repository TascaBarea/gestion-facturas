"""
Alta de Evento / Taller / Cata en WooCommerce.
Conversión del CLI alta_evento.py a formulario Streamlit.
"""

import streamlit as st
from datetime import datetime, date

# Proteger página con autenticación
if not st.session_state.get("autenticado", False):
    st.warning("Inicia sesión desde la página principal.")
    st.stop()

from utils.wc_client import get_wc_api, cargar_categorias, crear_producto

st.title("Alta de Evento")
st.markdown("Crea talleres, catas y eventos en la tienda online de Comestibles Barea.")

# ── Conexión WooCommerce ─────────────────────────────────────────────────────

try:
    wc = get_wc_api()
except Exception as e:
    st.error(f"Error conectando con WooCommerce: {e}")
    st.stop()


# ── Cargar categorías (cacheado por sesión) ──────────────────────────────────

@st.cache_data(ttl=300)
def _categorias():
    _wc = get_wc_api()
    return cargar_categorias(_wc)


cats = _categorias()
nombres_cats = ["(Sin categoría)"] + [nombre for _, nombre in cats]

# ── Formulario ───────────────────────────────────────────────────────────────

with st.form("form_evento"):
    st.subheader("Datos del evento")

    # Nombres basados en categorías WC + opción libre
    nombres_evento = [nombre for _, nombre in cats] + ["Otro (escribir)"]
    seleccion_nombre = st.selectbox("Tipo de evento", nombres_evento)

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

    plazas_str = st.text_input(
        "Número de plazas (vacío = sin límite)",
        placeholder="20",
    )

    cat_seleccion = st.selectbox("Categoría", nombres_cats)

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

    # Plazas
    plazas = None
    if plazas_str and plazas_str.strip():
        try:
            plazas = int(plazas_str.strip())
            if plazas <= 0:
                errores.append("Las plazas deben ser un número positivo.")
        except ValueError:
            errores.append(f"Plazas inválido: '{plazas_str}'.")

    if errores:
        for e in errores:
            st.error(e)
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

    # Categoría
    cat_id = None
    if cat_seleccion != "(Sin categoría)":
        for cid, cname in cats:
            if cname == cat_seleccion:
                cat_id = cid
                break

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
        st.markdown(f"**Plazas:** {plazas if plazas else 'Sin límite'}")
        st.markdown(f"**Categoría:** {cat_seleccion}")

    # Crear producto en WooCommerce
    payload = {
        "name": nombre_producto,
        "type": "simple",
        "status": "publish",
        "regular_price": str(precio),
        "description": descripcion,
        "manage_stock": plazas is not None,
    }
    if plazas is not None:
        payload["stock_quantity"] = plazas
        payload["stock_status"] = "instock"
    if cat_id:
        payload["categories"] = [{"id": cat_id}]

    with st.spinner("Publicando en WooCommerce..."):
        resultado = crear_producto(wc, payload)

    if "id" in resultado:
        st.success(f"Evento publicado correctamente (ID: {resultado['id']})")
        url = resultado.get("permalink", "")
        if url:
            st.markdown(f"[Ver en la tienda]({url})")
        st.info("Aparecerá en el email semanal del próximo lunes.")
        # Limpiar cache de categorías por si se creó una nueva
        _categorias.clear()
    else:
        msg = resultado.get("message", str(resultado))
        st.error(f"Error de WooCommerce: {msg}")
