"""
Alta de Evento / Taller / Cata en WooCommerce.
Formulario Streamlit con detección de conflictos de fecha,
selector en cascada tipo → subtipo, y soporte CERRADO.
"""

import re
import urllib.parse
import streamlit as st
from datetime import datetime, date
from utils.auth import require_role

require_role(["admin", "eventos"])

from utils.wc_client import get_wc_api, crear_producto

st.title("Alta de Evento")
st.markdown("Crea talleres, catas y eventos en la tienda online de Comestibles Barea.")

# ── Conexión WooCommerce ─────────────────────────────────────────────────────

try:
    wc = get_wc_api()
except Exception as e:
    st.error(f"Error conectando con WooCommerce: {e}")
    st.stop()

# ── Categorías WooCommerce → mapeo automático ────────────────────────────────

TIPO_CATEGORIA = {
    "TALLER": 39,
    "CATA": 40,
    "EVENTO": 44,
}

SUBTIPOS = {
    "TALLER": ["Aperitivos", "Encurtidos", "Kombucha", "Vermut", "Queso", "Otros (escribir)"],
    "CATA": ["Normal", "Especial", "Vinos", "Quesos", "Vermut", "Otros (escribir)"],
    "EVENTO": ["Degustación", "Otros (escribir)"],
}

# ── Cache de eventos existentes (para detección de conflictos) ───────────────

_FECHA_RE = re.compile(r"\b(\d{1,2}/\d{2}/\d{2})\s*$")


@st.cache_data(ttl=300)
def _cargar_eventos_existentes():
    """Carga eventos publicados con fecha futura. Devuelve {date_iso: [nombre, ...]}."""
    _wc = get_wc_api()
    eventos = {}
    hoy = date.today()
    page = 1
    while True:
        resp = _wc.get("products", params={
            "per_page": 100, "page": page, "status": "publish",
        }).json()
        if not isinstance(resp, list) or not resp:
            break
        for prod in resp:
            nombre = re.sub(r"<[^>]+>", "", prod.get("name", "")).strip()
            m = _FECHA_RE.search(nombre)
            if m:
                try:
                    dt = datetime.strptime(m.group(1), "%d/%m/%y").date()
                    if dt >= hoy:
                        eventos.setdefault(dt.isoformat(), []).append(nombre)
                except ValueError:
                    pass
        page += 1
        if len(resp) < 100:
            break
    return eventos


# ── FECHA (fuera del form para reacción en tiempo real) ──────────────────────

st.subheader("Datos del evento")

fecha = st.date_input(
    "Fecha del evento",
    value=None,
    min_value=date.today(),
    format="DD/MM/YYYY",
)

# Detección de conflicto de fecha
conflicto_confirmado = True
if fecha:
    eventos_existentes = _cargar_eventos_existentes()
    eventos_en_fecha = eventos_existentes.get(fecha.isoformat(), [])
    if eventos_en_fecha:
        for ev in eventos_en_fecha:
            st.warning(f"Ya hay un evento en esta fecha: **{ev}**")
        conflicto_confirmado = st.checkbox(
            "Confirmo que quiero crear otro evento en esta misma fecha"
        )

# ── FORMULARIO ───────────────────────────────────────────────────────────────

with st.form("form_evento"):

    # Selector cascada: tipo principal → subtipo
    tipo_principal = st.selectbox("Tipo principal", list(SUBTIPOS.keys()))
    subtipo = st.selectbox("Subtipo", SUBTIPOS[tipo_principal])

    nombre_libre = ""
    if subtipo == "Otros (escribir)":
        nombre_libre = st.text_input(
            "Nombre del subtipo (sin fecha)",
            placeholder="Ej: Jabones artesanales",
        )

    # ── CERRADO ──────────────────────────────────────────────────────────────
    st.markdown("---")
    es_cerrado = st.checkbox("CERRADO (evento reservado por un grupo)")

    plazas_totales = 10
    plazas_pagadas = 3
    if es_cerrado:
        st.caption("El evento aparece en el calendario pero solo es accesible por enlace privado.")
        col_ct, col_cp = st.columns(2)
        with col_ct:
            plazas_totales = st.number_input(
                "Plazas totales del grupo",
                min_value=1, max_value=30, value=10, step=1,
            )
        with col_cp:
            plazas_pagadas = st.number_input(
                "Plazas pagadas en reserva (min. 3)",
                min_value=3, max_value=30, value=3, step=1,
            )

    # ── Precio y horario ─────────────────────────────────────────────────────
    st.markdown("---")
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

    plazas_normales = 10
    if not es_cerrado:
        plazas_normales = st.number_input(
            "Número de plazas",
            min_value=1, max_value=30, value=10, step=1,
        )

    desc_extra = st.text_area(
        "Descripción adicional (opcional)",
        placeholder="Incluye degustación de 6 vinos y maridaje",
    )

    submitted = st.form_submit_button("Publicar evento", type="primary")

# ── Procesamiento ────────────────────────────────────────────────────────────

if submitted:
    errores = []

    if fecha is None:
        errores.append("La fecha es obligatoria.")

    if fecha and not conflicto_confirmado:
        errores.append("Hay un evento en la misma fecha. Marca la confirmación o elige otra fecha.")

    if subtipo == "Otros (escribir)" and not nombre_libre.strip():
        errores.append("Escribe el nombre del subtipo.")

    # CERRADO: validar plazas
    if es_cerrado and plazas_pagadas > plazas_totales:
        errores.append(f"Las plazas pagadas ({plazas_pagadas}) no pueden superar las totales ({plazas_totales}).")

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

    # Aviso plazas inusuales (solo eventos normales)
    if not es_cerrado and (plazas_normales < 7 or plazas_normales > 11):
        if plazas_normales < 7:
            st.warning(f"Has puesto **{plazas_normales} plazas**. Es menos de lo habitual (7-11).")
        else:
            st.warning(f"Has puesto **{plazas_normales} plazas**. Es más de lo habitual (7-11).")
        confirmado = st.checkbox("Confirmo que el número de plazas es correcto")
        if not confirmado:
            st.stop()

    # ── Construir nombre ─────────────────────────────────────────────────────
    subtipo_final = nombre_libre.strip() if subtipo == "Otros (escribir)" else subtipo
    tipo_label = tipo_principal.capitalize()

    if tipo_principal == "EVENTO":
        nombre_base = f"{tipo_label} {subtipo_final}"
    else:
        nombre_base = f"{tipo_label} de {subtipo_final}"

    fecha_yy = fecha.strftime("%d/%m/%y")

    if es_cerrado:
        nombre_producto = f"CERRADO {nombre_base} {fecha_yy}"
    else:
        nombre_producto = f"{nombre_base} {fecha_yy}"

    # ── Descripción ──────────────────────────────────────────────────────────
    partes_desc = []
    if hora_inicio:
        horario = f"HORARIO: de {hora_inicio.strftime('%H:%M')}"
        if hora_fin:
            horario += f" a {hora_fin.strftime('%H:%M')}"
        partes_desc.append(horario)
    if es_cerrado:
        partes_desc.append(f"Evento reservado — {plazas_totales} plazas ({plazas_pagadas} pagadas en reserva)")
    if desc_extra and desc_extra.strip():
        partes_desc.append(desc_extra.strip())
    descripcion = "\n".join(partes_desc)

    # ── Resumen ──────────────────────────────────────────────────────────────
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
        if es_cerrado:
            st.markdown(f"**Plazas totales:** {plazas_totales}")
            st.markdown(f"**Pagadas en reserva:** {plazas_pagadas}")
            st.markdown(f"**Pendientes de pago:** {plazas_totales - plazas_pagadas}")
        else:
            st.markdown(f"**Plazas:** {plazas_normales}")
        st.markdown(f"**Categoría:** {tipo_principal.lower()}")

    # ── Payload WooCommerce ──────────────────────────────────────────────────
    cat_id = TIPO_CATEGORIA.get(tipo_principal)

    if es_cerrado:
        stock_qty = plazas_totales - plazas_pagadas
        payload = {
            "name": nombre_producto,
            "type": "simple",
            "status": "publish",
            "catalog_visibility": "hidden",
            "regular_price": str(precio),
            "description": descripcion,
            "manage_stock": True,
            "stock_quantity": stock_qty,
            "stock_status": "instock" if stock_qty > 0 else "outofstock",
            "categories": [{"id": cat_id}] if cat_id else [],
        }
    else:
        payload = {
            "name": nombre_producto,
            "type": "simple",
            "status": "publish",
            "regular_price": str(precio),
            "description": descripcion,
            "manage_stock": True,
            "stock_quantity": plazas_normales,
            "stock_status": "instock",
            "categories": [{"id": cat_id}] if cat_id else [],
        }

    with st.spinner("Publicando en WooCommerce..."):
        resultado = crear_producto(wc, payload)

    if "id" in resultado:
        st.success(f"Evento publicado correctamente (ID: {resultado['id']})")
        url = resultado.get("permalink", "")

        if es_cerrado and url:
            # Enlace privado para compartir con el grupo
            st.markdown("---")
            st.subheader("Enlace privado para el grupo")
            st.caption("Comparte este enlace con los asistentes para que paguen sus plazas.")
            st.code(url, language=None)

            # Botón WhatsApp
            texto_wa = f"Reserva tu plaza para {nombre_base} ({fecha.strftime('%d/%m/%Y')}): {url}"
            wa_url = f"https://wa.me/?text={urllib.parse.quote(texto_wa)}"
            st.link_button("Enviar por WhatsApp", wa_url, type="primary")

        elif url:
            st.markdown(f"[Ver en la tienda]({url})")

        st.info("Aparecerá en el email semanal del próximo lunes.")
        _cargar_eventos_existentes.clear()
    else:
        msg = resultado.get("message", str(resultado))
        st.error(f"Error de WooCommerce: {msg}")
