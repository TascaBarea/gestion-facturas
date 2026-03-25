"""
Dashboard de Ventas — Tasca Barea y Comestibles Barea.
Muestra datos agregados desde JSON exportado a Netlify.
"""

import streamlit as st
import pandas as pd
from utils.auth import require_role, get_role
from utils.data_client import get_ventas_comes, get_ventas_tasca, ultima_actualizacion

require_role(["admin", "socio", "comes"])

MESES = ["Ene", "Feb", "Mar", "Abr", "May", "Jun",
         "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]

role = get_role()

# ── Sidebar: última actualización ──
st.sidebar.caption(f"Datos: {ultima_actualizacion()}")

# ── Selector de tienda (Elena solo ve Comestibles) ──
if role == "comes":
    tiendas = ["Comestibles"]
else:
    tiendas = ["Comestibles", "Tasca"]

tienda = st.radio("Tienda", tiendas, horizontal=True) if len(tiendas) > 1 else tiendas[0]

# ── Cargar datos ──
if tienda == "Comestibles":
    datos = get_ventas_comes()
    color_principal = "#2E7D32"
else:
    datos = get_ventas_tasca()
    color_principal = "#1B2A4A"

if not datos or "años" not in datos:
    st.warning("Datos no disponibles todavía. Se actualizarán en la próxima ejecución semanal.")
    st.stop()

años_disponibles = sorted(datos["años"].keys(), reverse=True)

# ── Selector de año ──
año = st.selectbox("Año", años_disponibles)
data_año = datos["años"][año]

# ══════════════════════════════════════════════════════════════════════════
# KPIs
# ══════════════════════════════════════════════════════════════════════════
st.header(f"{'🛒' if tienda == 'Comestibles' else '🍺'} {tienda} — {año}")

mensual = data_año.get("mensual", {})
total_euros = sum(v.get("euros", 0) for v in mensual.values())
total_tickets = sum(v.get("tickets", 0) for v in mensual.values())
total_unidades = sum(v.get("unidades", 0) for v in mensual.values())
ticket_medio = total_euros / total_tickets if total_tickets > 0 else 0

# Comparativa interanual
año_anterior = str(int(año) - 1)
variacion = None
if año_anterior in datos["años"]:
    mensual_ant = datos["años"][año_anterior].get("mensual", {})
    # Comparar solo meses que existen en el año actual
    meses_actual = set(mensual.keys())
    euros_ant = sum(v.get("euros", 0) for k, v in mensual_ant.items() if k in meses_actual)
    if euros_ant > 0:
        variacion = (total_euros - euros_ant) / euros_ant * 100

col1, col2, col3, col4 = st.columns(4)
col1.metric("Facturación", f"{total_euros:,.0f} €",
            delta=f"{variacion:+.1f}%" if variacion is not None else None)
col2.metric("Tickets", f"{total_tickets:,}")
col3.metric("Ticket medio", f"{ticket_medio:.2f} €")
col4.metric("Unidades", f"{total_unidades:,.0f}")

# ══════════════════════════════════════════════════════════════════════════
# Gráfico mensual
# ══════════════════════════════════════════════════════════════════════════
st.subheader("Evolución mensual")

filas = []
for mes_str, val in sorted(mensual.items(), key=lambda x: int(x[0])):
    idx = int(mes_str) - 1
    filas.append({
        "Mes": MESES[idx],
        "mes_num": int(mes_str),
        "Euros": val.get("euros", 0),
        "Tickets": val.get("tickets", 0),
    })
df_mensual = pd.DataFrame(filas).sort_values("mes_num")

# Comparativa con año anterior
if año_anterior in datos["años"]:
    filas_ant = []
    for mes_str, val in datos["años"][año_anterior].get("mensual", {}).items():
        idx = int(mes_str) - 1
        filas_ant.append({
            "Mes": MESES[idx],
            "mes_num": int(mes_str),
            "Euros": val.get("euros", 0),
        })
    df_ant = pd.DataFrame(filas_ant).sort_values("mes_num")
    # Combinar
    df_chart = pd.merge(
        df_mensual[["Mes", "mes_num", "Euros"]].rename(columns={"Euros": año}),
        df_ant[["mes_num", "Euros"]].rename(columns={"Euros": año_anterior}),
        on="mes_num", how="outer"
    ).sort_values("mes_num").set_index("Mes")
    df_chart = df_chart.drop(columns=["mes_num"])
    st.line_chart(df_chart, color=[color_principal, "#CCCCCC"])
else:
    st.bar_chart(df_mensual.set_index("Mes")["Euros"], color=color_principal)

# ══════════════════════════════════════════════════════════════════════════
# Categorías
# ══════════════════════════════════════════════════════════════════════════
st.subheader("Desglose por categoría")

# Agregar categorías del año completo
categorias_total = {}
for mes_str, cats in data_año.get("categorias", {}).items():
    euros_mes = mensual.get(mes_str, {}).get("euros", 0)
    for cat, pct in cats.items():
        categorias_total[cat] = categorias_total.get(cat, 0) + euros_mes * pct / 100

if categorias_total:
    df_cats = pd.DataFrame([
        {"Categoría": cat, "Euros": round(euros, 2)}
        for cat, euros in sorted(categorias_total.items(), key=lambda x: x[1], reverse=True)
    ])
    total_cats = df_cats["Euros"].sum()
    df_cats["%"] = (df_cats["Euros"] / total_cats * 100).round(1)
    df_cats["Euros"] = df_cats["Euros"].apply(lambda x: f"{x:,.2f} €")

    st.dataframe(df_cats, use_container_width=True, hide_index=True)

# ══════════════════════════════════════════════════════════════════════════
# Márgenes (solo Comestibles)
# ══════════════════════════════════════════════════════════════════════════
if tienda == "Comestibles" and data_año.get("margenes"):
    st.subheader("Márgenes por categoría")

    margenes_total = {}
    for mes_str, cats in data_año.get("margenes", {}).items():
        for cat, val in cats.items():
            if cat not in margenes_total:
                margenes_total[cat] = {"euros": 0, "margen_pct_sum": 0, "n": 0}
            margenes_total[cat]["euros"] += val.get("euros", 0)
            margenes_total[cat]["margen_pct_sum"] += val.get("margen_pct", 0)
            margenes_total[cat]["n"] += 1

    filas_margen = []
    for cat, val in sorted(margenes_total.items(), key=lambda x: x[1]["euros"], reverse=True):
        avg_pct = val["margen_pct_sum"] / val["n"] if val["n"] > 0 else 0
        filas_margen.append({
            "Categoría": cat,
            "Ventas": f"{val['euros']:,.2f} €",
            "Margen medio": f"{avg_pct:.1f}%"
        })

    st.dataframe(pd.DataFrame(filas_margen), use_container_width=True, hide_index=True)

# ══════════════════════════════════════════════════════════════════════════
# Top productos
# ══════════════════════════════════════════════════════════════════════════
st.subheader("Top productos")

# Selector de mes o acumulado
meses_disponibles = sorted(mensual.keys(), key=int)
opciones_mes = ["Acumulado"] + [MESES[int(m) - 1] for m in meses_disponibles]
sel_mes = st.selectbox("Periodo", opciones_mes, key="top_mes")

if sel_mes == "Acumulado":
    # Agrupar todos los meses
    productos_acum = {}
    for mes_str, prods in data_año.get("top_productos", {}).items():
        for p in prods:
            nombre = p["art"]
            if nombre not in productos_acum:
                productos_acum[nombre] = {"cat": p.get("cat", ""), "euros": 0, "cant": 0}
            productos_acum[nombre]["euros"] += p.get("euros", 0)
            productos_acum[nombre]["cant"] += p.get("cant", 0)
    top_list = sorted(productos_acum.items(), key=lambda x: x[1]["euros"], reverse=True)[:15]
    filas_top = [{"Producto": k, "Categoría": v["cat"],
                  "Euros": f"{v['euros']:,.2f} €", "Unidades": round(v["cant"], 1)}
                 for k, v in top_list]
else:
    mes_idx = opciones_mes.index(sel_mes)
    mes_str = meses_disponibles[mes_idx - 1]
    prods = data_año.get("top_productos", {}).get(mes_str, [])
    filas_top = [{"Producto": p["art"], "Categoría": p.get("cat", ""),
                  "Euros": f"{p['euros']:,.2f} €", "Unidades": round(p.get("cant", 0), 1)}
                 for p in prods[:15]]

if filas_top:
    st.dataframe(pd.DataFrame(filas_top), use_container_width=True, hide_index=True)
else:
    st.info("Sin datos de productos para este periodo.")

# ══════════════════════════════════════════════════════════════════════════
# WooCommerce (solo Comestibles)
# ══════════════════════════════════════════════════════════════════════════
if tienda == "Comestibles" and datos.get("woo"):
    woo_data = datos["woo"]
    woo_euros = sum(v.get("euros", 0) for v in woo_data.values())
    woo_pedidos = sum(v.get("pedidos", 0) for v in woo_data.values())
    if woo_euros > 0:
        st.subheader("WooCommerce (online)")
        c1, c2 = st.columns(2)
        c1.metric("Ventas online", f"{woo_euros:,.0f} €")
        c2.metric("Pedidos", f"{woo_pedidos:,}")

# ══════════════════════════════════════════════════════════════════════════
# Días de la semana (solo Tasca)
# ══════════════════════════════════════════════════════════════════════════
if tienda == "Tasca" and datos.get("dias_semana", {}).get(año):
    st.subheader("Ventas por día de la semana")
    dias_nombres = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
    dias_data = datos["dias_semana"][año]
    filas_dias = []
    for i, nombre in enumerate(dias_nombres):
        d = dias_data.get(str(i), {})
        filas_dias.append({
            "Día": nombre,
            "Euros": d.get("euros", 0),
            "Tickets": d.get("tickets", 0),
            "Ticket medio": round(d.get("ticket_medio", 0), 2)
        })
    df_dias = pd.DataFrame(filas_dias)
    st.bar_chart(df_dias.set_index("Día")["Euros"], color=color_principal)
    st.dataframe(df_dias, use_container_width=True, hide_index=True)
