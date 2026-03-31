"""
Alta de Evento / Taller / Cata en WooCommerce.
Formulario Streamlit con detección de conflictos de fecha,
selector en cascada tipo → subtipo, soporte CERRADO y modo test.
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


# ── Detección de tests pendientes ────────────────────────────────────────────

@st.cache_data(ttl=300)
def _contar_tests():
    """Cuenta productos [TEST] privados en WooCommerce."""
    _wc = get_wc_api()
    count = 0
    page = 1
    while True:
        resp = _wc.get("products", params={
            "per_page": 100, "page": page,
            "status": "private",
            "search": "[TEST]",
        }).json()
        if not isinstance(resp, list) or not resp:
            break
        count += sum(1 for p in resp if p.get("name", "").startswith("[TEST]"))
        page += 1
        if len(resp) < 100:
            break
    return count


@st.cache_data(ttl=300)
def _listar_tests():
    """Lista productos [TEST] privados. Devuelve lista de dicts."""
    _wc = get_wc_api()
    tests = []
    page = 1
    while True:
        resp = _wc.get("products", params={
            "per_page": 100, "page": page,
            "status": "private",
            "search": "[TEST]",
        }).json()
        if not isinstance(resp, list) or not resp:
            break
        for p in resp:
            if p.get("name", "").startswith("[TEST]"):
                tests.append({
                    "id": p["id"],
                    "name": p["name"],
                    "date_created": p.get("date_created", "")[:10],
                    "price": p.get("regular_price", "0"),
                    "status": p.get("status", ""),
                })
        page += 1
        if len(resp) < 100:
            break
    return tests


# ── Banner de tests pendientes ───────────────────────────────────────────────

n_tests = _contar_tests()
if n_tests > 0:
    st.warning(f"Hay **{n_tests}** evento(s) de prueba pendientes de eliminar. Ver abajo.")

# ── Fechas ocupadas (ayuda visual) ───────────────────────────────────────────

st.subheader("Datos del evento")

_eventos_existentes = _cargar_eventos_existentes()
if _eventos_existentes:
    with st.expander("Fechas con eventos programados", expanded=False):
        for fecha_iso in sorted(_eventos_existentes.keys()):
            dt = date.fromisoformat(fecha_iso)
            nombres = _eventos_existentes[fecha_iso]
            for nombre in nombres:
                es_cerrado = nombre.upper().startswith("CERRADO")
                tipo_tag = "CERRADO" if es_cerrado else ""
                st.markdown(f"- **{dt.strftime('%d/%m/%Y')}** — {tipo_tag} {nombre}")

# ── FECHA (fuera del form para reacción en tiempo real) ──────────────────────

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

    # ── Modo Test ────────────────────────────────────────────────────────────
    st.markdown("---")
    modo_test = st.checkbox("Modo test")
    st.caption("Crea el evento como privado (no visible para clientes). Precio forzado a 0,01 €.")

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

    # Precio (no validar si es modo test)
    precio = None
    if modo_test:
        precio = 0.01
    elif not precio_str or not precio_str.strip():
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

    # Aviso plazas inusuales (solo eventos normales, no test)
    if not es_cerrado and not modo_test and (plazas_normales < 7 or plazas_normales > 11):
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

    if modo_test:
        nombre_producto = f"[TEST] {nombre_base} {fecha_yy}"
    elif es_cerrado:
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
    if modo_test:
        st.caption("MODO TEST — el evento se creará como privado")
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

    if modo_test:
        payload = {
            "name": nombre_producto,
            "type": "simple",
            "status": "private",
            "catalog_visibility": "hidden",
            "regular_price": "0.01",
            "description": descripcion,
            "manage_stock": True,
            "stock_quantity": plazas_normales if not es_cerrado else (plazas_totales - plazas_pagadas),
            "stock_status": "instock",
            "categories": [{"id": cat_id}] if cat_id else [],
        }
    elif es_cerrado:
        stock_qty = plazas_totales - plazas_pagadas
        payload = {
            "name": nombre_producto,
            "type": "simple",
            "status": "publish",
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
        prod_id = resultado["id"]
        url = resultado.get("permalink", "")

        if modo_test:
            st.info(f"Evento TEST creado (privado, no visible en la tienda). ID: {prod_id}")
            wc_url = st.secrets.get("WC_URL", "")
            if wc_url:
                admin_url = f"{wc_url}/wp-admin/post.php?post={prod_id}&action=edit"
                st.markdown(f"[Ver en el admin de WordPress]({admin_url})")
            _contar_tests.clear()
        elif es_cerrado and url:
            st.success(f"Evento CERRADO publicado (ID: {prod_id})")
            st.markdown("---")
            st.subheader("Enlace privado para el grupo")
            st.caption("Comparte este enlace con los asistentes para que paguen sus plazas.")
            st.code(url, language=None)
            texto_wa = f"Reserva tu plaza para {nombre_base} ({fecha.strftime('%d/%m/%Y')}): {url}"
            wa_url = f"https://wa.me/?text={urllib.parse.quote(texto_wa)}"
            st.link_button("Enviar por WhatsApp", wa_url, type="primary")
        else:
            st.success(f"Evento publicado correctamente (ID: {prod_id})")
            if url:
                st.markdown(f"[Ver en la tienda]({url})")

        if not modo_test:
            st.info("Aparecerá en el email semanal del próximo lunes.")
        _cargar_eventos_existentes.clear()
    else:
        msg = resultado.get("message", str(resultado))
        st.error(f"Error de WooCommerce: {msg}")

# ── Limpieza de tests ────────────────────────────────────────────────────────

st.markdown("---")
with st.expander("Limpiar eventos de prueba"):
    tests = _listar_tests()
    if not tests:
        st.info("No hay eventos de prueba.")
    else:
        st.markdown(f"**{len(tests)}** evento(s) de prueba encontrados:")

        # Formulario de borrado selectivo
        with st.form("form_borrar_tests"):
            seleccionados = []
            for t in tests:
                checked = st.checkbox(
                    f"{t['name']} — creado {t['date_created']} — {t['price']} €",
                    key=f"del_{t['id']}",
                )
                if checked:
                    seleccionados.append(t["id"])

            col_del1, col_del2 = st.columns(2)
            with col_del1:
                borrar_sel = st.form_submit_button("Eliminar seleccionados")
            with col_del2:
                borrar_todos = st.form_submit_button("Eliminar TODOS")

        if borrar_sel and seleccionados:
            errores_borrado = []
            for pid in seleccionados:
                try:
                    wc.delete(f"products/{pid}", params={"force": True})
                except Exception as e:
                    errores_borrado.append(f"ID {pid}: {e}")
            if errores_borrado:
                for eb in errores_borrado:
                    st.error(eb)
            else:
                st.success(f"{len(seleccionados)} test(s) eliminados.")
            _contar_tests.clear()
            _listar_tests.clear()
            _cargar_eventos_existentes.clear()
            st.rerun()

        if borrar_sel and not seleccionados:
            st.warning("Selecciona al menos un test para eliminar.")

        if borrar_todos:
            # Doble confirmación via session_state
            if st.session_state.get("confirmar_borrar_todos"):
                errores_borrado = []
                for t in tests:
                    try:
                        wc.delete(f"products/{t['id']}", params={"force": True})
                    except Exception as e:
                        errores_borrado.append(f"ID {t['id']}: {e}")
                if errores_borrado:
                    for eb in errores_borrado:
                        st.error(eb)
                else:
                    st.success(f"{len(tests)} test(s) eliminados.")
                st.session_state["confirmar_borrar_todos"] = False
                _contar_tests.clear()
                _listar_tests.clear()
                _cargar_eventos_existentes.clear()
                st.rerun()
            else:
                st.session_state["confirmar_borrar_todos"] = True
                st.warning("Pulsa de nuevo 'Eliminar TODOS' para confirmar.")
                st.rerun()
