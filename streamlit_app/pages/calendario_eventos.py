"""
Calendario de eventos: lista de eventos con asistentes y plazas libres.
Indicador visual CERRADO + enlace privado. Exportable a Excel.
"""

import io
import urllib.parse
import streamlit as st
import pandas as pd
from datetime import datetime, date
from utils.auth import require_role

require_role(["admin", "eventos"])

from utils.wc_client import (
    get_wc_api,
    cargar_eventos_futuros,
    cargar_pedidos_evento,
)

st.title("Calendario de Eventos")
st.markdown("Eventos programados con asistentes y plazas disponibles.")

# ── Conexión WooCommerce ─────────────────────────────────────────────────────

try:
    wc = get_wc_api()
except Exception as e:
    st.error(f"Error conectando con WooCommerce: {e}")
    st.stop()


# ── Cargar eventos ───────────────────────────────────────────────────────────

@st.cache_data(ttl=120)
def _eventos():
    _wc = get_wc_api()
    return cargar_eventos_futuros(_wc)


with st.spinner("Cargando eventos..."):
    eventos = _eventos()

if not eventos:
    st.info("No hay eventos programados.")
    st.stop()

# ── Resumen de eventos ───────────────────────────────────────────────────────

st.subheader("Eventos programados")

hoy = datetime.combine(date.today(), datetime.min.time())

resumen = []
for ev in eventos:
    plazas_total = ev["stock_quantity"] if ev["manage_stock"] else None
    vendidas = ev["total_sales"] or 0
    plazas_libres = (plazas_total - vendidas) if plazas_total is not None else None
    fecha_str = ev.get("fecha", "")
    nombre_raw = ev.get("nombre_raw", ev.get("nombre", ""))
    es_cerrado = nombre_raw.upper().startswith("CERRADO")

    # Parsear fecha para ordenar y filtrar
    fecha_dt = None
    if fecha_str:
        try:
            if len(fecha_str) == 8:  # DD/MM/YY
                fecha_dt = datetime.strptime(fecha_str, "%d/%m/%y")
            else:
                fecha_dt = datetime.strptime(fecha_str, "%d/%m/%Y")
        except ValueError:
            pass

    if fecha_dt is None or fecha_dt < hoy:
        continue

    resumen.append({
        "Tipo": "CERRADO" if es_cerrado else "Abierto",
        "Evento": ev["nombre"],
        "Fecha": fecha_str or "Sin fecha",
        "_fecha_dt": fecha_dt,
        "Vendidas": vendidas,
        "Plazas totales": plazas_total if plazas_total is not None else "Sin limite",
        "Plazas libres": plazas_libres if plazas_libres is not None else "Sin limite",
        "id": ev["id"],
        "_es_cerrado": es_cerrado,
    })

# Ordenar por fecha (más próximos primero)
resumen.sort(key=lambda x: x["_fecha_dt"] or datetime.max)

if not resumen:
    st.info("No hay eventos futuros programados.")
    st.stop()

df_resumen = pd.DataFrame(resumen)
st.dataframe(
    df_resumen[["Tipo", "Evento", "Fecha", "Vendidas", "Plazas totales", "Plazas libres"]],
    use_container_width=True,
    hide_index=True,
)

# ── Selector de evento para ver asistentes ───────────────────────────────────

st.markdown("---")
st.subheader("Asistentes por evento")

opciones_map = {}
for ev in eventos:
    fecha_str = ev.get("fecha", "")
    nombre_raw = ev.get("nombre_raw", ev.get("nombre", ""))
    es_cerrado = nombre_raw.upper().startswith("CERRADO")
    prefijo = "CERRADO " if es_cerrado else ""
    label = f"{prefijo}{ev['nombre']} — {fecha_str}" if fecha_str else f"{prefijo}{ev['nombre']}"
    if label in opciones_map:
        label += f" (#{ev['id']})"
    opciones_map[label] = ev["id"]

opciones_ordenadas = sorted(opciones_map.keys(), key=lambda x: next(
    (r["_fecha_dt"] for r in resumen if r["id"] == opciones_map[x]),
    datetime.max,
))

evento_sel_label = st.selectbox("Selecciona un evento", opciones_ordenadas)
evento_sel_id = opciones_map[evento_sel_label]

eventos_match = [ev for ev in eventos if ev["id"] == evento_sel_id]

if not eventos_match:
    st.warning("Evento no encontrado.")
    st.stop()

# ── Enlace privado para eventos CERRADOS ─────────────────────────────────────

ev_seleccionado = eventos_match[0]
nombre_raw_sel = ev_seleccionado.get("nombre_raw", ev_seleccionado.get("nombre", ""))
es_cerrado_sel = nombre_raw_sel.upper().startswith("CERRADO")

if es_cerrado_sel:
    st.info("Este es un evento **CERRADO** (reservado por un grupo).")
    # Construir permalink (WC lo guarda como slug)
    # Usamos la API para obtener el permalink real
    try:
        prod_data = wc.get(f"products/{evento_sel_id}").json()
        permalink = prod_data.get("permalink", "")
        if permalink:
            st.caption("Enlace privado para que los asistentes paguen sus plazas:")
            st.code(permalink, language=None)
            nombre_corto = ev_seleccionado.get("nombre", "")
            fecha_ev = ev_seleccionado.get("fecha", "")
            texto_wa = f"Reserva tu plaza para {nombre_corto} ({fecha_ev}): {permalink}"
            wa_url = f"https://wa.me/?text={urllib.parse.quote(texto_wa)}"
            st.link_button("Enviar por WhatsApp", wa_url)
    except Exception:
        pass

# ── Asistentes ───────────────────────────────────────────────────────────────

@st.cache_data(ttl=120)
def _pedidos_evento(product_ids):
    _wc = get_wc_api()
    todos = []
    for pid in product_ids:
        todos.extend(cargar_pedidos_evento(_wc, pid))
    return todos


product_ids = tuple(ev["id"] for ev in eventos_match)

with st.spinner("Cargando asistentes..."):
    pedidos = _pedidos_evento(product_ids)

if not pedidos:
    st.info("No hay asistentes registrados para este evento.")
else:
    asistentes = []
    for pedido in pedidos:
        billing = pedido.get("billing", {})
        nombre = f"{billing.get('first_name', '')} {billing.get('last_name', '')}".strip()
        email = billing.get("email", "")
        telefono = billing.get("phone", "")
        fecha_compra = pedido.get("date_created", "")[:10]

        tickets = 0
        for li in pedido.get("line_items", []):
            if li.get("product_id") in product_ids:
                tickets += li.get("quantity", 1)

        asistentes.append({
            "Nombre": nombre,
            "Email": email,
            "Teléfono": telefono,
            "Tickets": tickets,
            "Fecha compra": fecha_compra,
        })

    df_asistentes = pd.DataFrame(asistentes)

    # Métricas
    total_tickets = df_asistentes["Tickets"].sum()
    total_personas = len(df_asistentes)
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Personas", total_personas)
    with col2:
        st.metric("Tickets vendidos", total_tickets)

    st.dataframe(df_asistentes, use_container_width=True, hide_index=True)

    # ── Exportar a Excel ─────────────────────────────────────────────────────

    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df_asistentes.to_excel(writer, sheet_name="Asistentes", index=False)
        ws = writer.sheets["Asistentes"]
        for col_idx, col_name in enumerate(df_asistentes.columns, 1):
            max_len = max(
                len(str(col_name)),
                df_asistentes[col_name].astype(str).str.len().max() if len(df_asistentes) > 0 else 0,
            )
            ws.column_dimensions[chr(64 + col_idx)].width = min(max_len + 3, 40)

    nombre_archivo = f"asistentes_{evento_sel_label.replace(' ', '_')[:30]}.xlsx"
    st.download_button(
        label="Descargar Excel",
        data=buffer.getvalue(),
        file_name=nombre_archivo,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        type="primary",
    )
