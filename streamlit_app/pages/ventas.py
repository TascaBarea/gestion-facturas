"""
Dashboard de Ventas — Tasca Barea y Comestibles Barea.
Muestra datos agregados desde JSON exportado a Netlify.
Gráficos interactivos con Plotly.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from utils.auth import require_role, get_role
from utils.data_client import get_ventas_comes, get_ventas_tasca, ultima_actualizacion

require_role(["admin", "socio", "comes"])

MESES = ["Ene", "Feb", "Mar", "Abr", "May", "Jun",
         "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]

# Paleta categorías Comestibles
CAT_COLORS_COMES = {
    "QUESOS": "#e8c97a", "CHACINAS": "#dc7070", "VINOS": "#7a3b6e",
    "BODEGA": "#9b59b6", "CONSERVAS": "#3498db", "DESPENSA": "#e67e22",
    "ACEITES Y VINAGRES": "#c8b83e", "DULCES": "#e87ec0", "BAZAR": "#8aa898",
    "EXPERIENCIAS": "#7ec8a0", "OTROS": "#6a7a70",
}
# Paleta categorías Tasca
CAT_COLORS_TASCA = {
    "COMIDA": "#e67e22", "BEBIDA": "#3498db", "VINOS": "#7a3b6e",
    "MOLLETES": "#c8b83e", "PROMOCIONES": "#dc7070", "OTROS": "#6a7a70",
}

NETLIFY_DASHBOARD = "https://barea-dashboards.netlify.app"

role = get_role()

# ── Sidebar ──
st.sidebar.caption(f"Datos: {ultima_actualizacion()}")

# ── Selector de tienda ──
if role == "comes":
    tiendas = ["Comestibles"]
else:
    tiendas = ["Comestibles", "Tasca"]

tienda = st.radio("Tienda", tiendas, horizontal=True) if len(tiendas) > 1 else tiendas[0]

# ── Cargar datos ──
if tienda == "Comestibles":
    datos = get_ventas_comes()
    color_1 = "#2E7D32"
    color_2 = "#81C784"
    cat_colors = CAT_COLORS_COMES
else:
    datos = get_ventas_tasca()
    color_1 = "#1B2A4A"
    color_2 = "#5B8DB8"
    cat_colors = CAT_COLORS_TASCA

if not datos or "años" not in datos:
    st.warning("Datos no disponibles todavía. Se actualizarán en la próxima ejecución semanal.")
    st.stop()

años_disponibles = sorted(datos["años"].keys(), reverse=True)
año = st.selectbox("Año", años_disponibles)
data_año = datos["años"][año]
mensual = data_año.get("mensual", {})

# Año anterior para comparativas
año_ant = str(int(año) - 1)
tiene_ant = año_ant in datos["años"]
mensual_ant = datos["años"][año_ant].get("mensual", {}) if tiene_ant else {}

# ── Helpers Plotly ──
PLOTLY_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="DM Sans, sans-serif", size=12),
    margin=dict(l=40, r=20, t=30, b=40),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    hoverlabel=dict(bgcolor="white", font_size=12),
)


def meses_con_datos(mens: dict) -> list[int]:
    return sorted(int(m) for m, v in mens.items() if v.get("tickets", 0) > 0)


def plotly_config():
    return {"displayModeBar": False, "responsive": True}


# ══════════════════════════════════════════════════════════════════════════
# KPIs (fuera de tabs, siempre visibles)
# ══════════════════════════════════════════════════════════════════════════
st.header(f"{'🛒' if tienda == 'Comestibles' else '🍺'} {tienda} — {año}")

meses_act = meses_con_datos(mensual)
total_euros = sum(mensual.get(str(m), {}).get("euros", 0) for m in meses_act)
total_tickets = sum(mensual.get(str(m), {}).get("tickets", 0) for m in meses_act)
total_unidades = sum(mensual.get(str(m), {}).get("unidades", 0) for m in meses_act)
ticket_medio = total_euros / total_tickets if total_tickets > 0 else 0

# Delta interanual (solo meses comparables)
variacion = None
if tiene_ant:
    euros_ant = sum(mensual_ant.get(str(m), {}).get("euros", 0) for m in meses_act)
    if euros_ant > 0:
        variacion = (total_euros - euros_ant) / euros_ant * 100

col1, col2, col3, col4 = st.columns(4)
col1.metric("Facturación", f"{total_euros:,.0f} €",
            delta=f"{variacion:+.1f}%" if variacion is not None else None)
col2.metric("Tickets", f"{total_tickets:,}")
col3.metric("Ticket medio", f"{ticket_medio:.2f} €")
col4.metric("Unidades", f"{total_unidades:,.0f}")

# ══════════════════════════════════════════════════════════════════════════
# TABS
# ══════════════════════════════════════════════════════════════════════════
tab_resumen, tab_productos = st.tabs(["📊 Resumen", "📦 Productos"])

# ─────────────────────────────────────────────────────────────────────────
# TAB RESUMEN
# ─────────────────────────────────────────────────────────────────────────
with tab_resumen:

    # ── Evolución mensual € ──
    st.subheader("Evolución mensual")
    fig_euros = go.Figure()

    # Año anterior (si existe)
    if tiene_ant:
        meses_ant_list = meses_con_datos(mensual_ant)
        fig_euros.add_trace(go.Scatter(
            x=[MESES[m - 1] for m in meses_ant_list],
            y=[mensual_ant[str(m)].get("euros", 0) for m in meses_ant_list],
            name=año_ant, mode="lines+markers",
            line=dict(color="#CCCCCC", width=2, dash="dot"),
            marker=dict(size=5), hovertemplate="%{x}: %{y:,.0f} €<extra>" + año_ant + "</extra>",
        ))

    # Año actual
    fig_euros.add_trace(go.Scatter(
        x=[MESES[m - 1] for m in meses_act],
        y=[mensual[str(m)].get("euros", 0) for m in meses_act],
        name=año, mode="lines+markers",
        line=dict(color=color_1, width=3),
        marker=dict(size=7), fill="tozeroy",
        fillcolor=f"rgba({int(color_1[1:3],16)},{int(color_1[3:5],16)},{int(color_1[5:7],16)},0.08)",
        hovertemplate="%{x}: %{y:,.0f} €<extra>" + año + "</extra>",
    ))
    fig_euros.update_layout(**PLOTLY_LAYOUT, height=300, yaxis_tickformat=",", yaxis_ticksuffix=" €")
    st.plotly_chart(fig_euros, use_container_width=True, config=plotly_config())

    # ── Tickets + Ticket medio lado a lado ──
    c_left, c_right = st.columns(2)

    with c_left:
        st.caption("Tickets por mes")
        fig_tix = go.Figure()
        if tiene_ant:
            meses_ant_list = meses_con_datos(mensual_ant)
            fig_tix.add_trace(go.Bar(
                x=[MESES[m - 1] for m in meses_ant_list],
                y=[mensual_ant[str(m)].get("tickets", 0) for m in meses_ant_list],
                name=año_ant, marker_color="#DDDDDD",
                hovertemplate="%{x}: %{y:,}<extra>" + año_ant + "</extra>",
            ))
        fig_tix.add_trace(go.Bar(
            x=[MESES[m - 1] for m in meses_act],
            y=[mensual[str(m)].get("tickets", 0) for m in meses_act],
            name=año, marker_color=color_1,
            hovertemplate="%{x}: %{y:,}<extra>" + año + "</extra>",
        ))
        fig_tix.update_layout(**PLOTLY_LAYOUT, height=250, barmode="group",
                              yaxis_tickformat=",", showlegend=False)
        st.plotly_chart(fig_tix, use_container_width=True, config=plotly_config())

    with c_right:
        st.caption("Ticket medio por mes")
        fig_tm = go.Figure()
        if tiene_ant:
            meses_ant_list = meses_con_datos(mensual_ant)
            fig_tm.add_trace(go.Scatter(
                x=[MESES[m - 1] for m in meses_ant_list],
                y=[mensual_ant[str(m)].get("prom_ticket", 0) for m in meses_ant_list],
                name=año_ant, mode="lines+markers",
                line=dict(color="#CCCCCC", width=2, dash="dot"), marker=dict(size=4),
                hovertemplate="%{x}: %{y:.2f} €<extra>" + año_ant + "</extra>",
            ))
        fig_tm.add_trace(go.Scatter(
            x=[MESES[m - 1] for m in meses_act],
            y=[mensual[str(m)].get("prom_ticket", 0) for m in meses_act],
            name=año, mode="lines+markers",
            line=dict(color=color_2, width=3), marker=dict(size=6),
            hovertemplate="%{x}: %{y:.2f} €<extra>" + año + "</extra>",
        ))
        fig_tm.update_layout(**PLOTLY_LAYOUT, height=250, yaxis_tickformat=".1f",
                              yaxis_ticksuffix=" €", showlegend=False)
        st.plotly_chart(fig_tm, use_container_width=True, config=plotly_config())

    # ── Categorías: donut + tabla ──
    st.subheader("Categorías")
    categorias_total = {}
    for mes_str, cats in data_año.get("categorias", {}).items():
        euros_mes = mensual.get(mes_str, {}).get("euros", 0)
        for cat, pct in cats.items():
            categorias_total[cat] = categorias_total.get(cat, 0) + euros_mes * pct / 100

    if categorias_total:
        cats_sorted = sorted(categorias_total.items(), key=lambda x: x[1], reverse=True)
        cat_names = [c[0] for c in cats_sorted]
        cat_euros = [round(c[1], 2) for c in cats_sorted]
        total_cats = sum(cat_euros)
        cat_pcts = [round(e / total_cats * 100, 1) if total_cats > 0 else 0 for e in cat_euros]
        colors = [cat_colors.get(c, "#6a7a70") for c in cat_names]

        col_donut, col_tabla = st.columns([1, 1])

        with col_donut:
            fig_donut = go.Figure(data=[go.Pie(
                labels=cat_names, values=cat_euros,
                hole=0.55, marker=dict(colors=colors),
                textinfo="percent", textposition="outside",
                textfont=dict(size=11),
                hovertemplate="%{label}<br>%{value:,.0f} €<br>%{percent}<extra></extra>",
            )])
            fig_donut.update_layout(**PLOTLY_LAYOUT, height=300, showlegend=False,
                                     margin=dict(l=20, r=20, t=10, b=10))
            st.plotly_chart(fig_donut, use_container_width=True, config=plotly_config())

        with col_tabla:
            df_cats = pd.DataFrame({
                "Categoría": cat_names,
                "Euros": [f"{e:,.0f} €" for e in cat_euros],
                "%": [f"{p:.1f}%" for p in cat_pcts],
            })
            st.dataframe(df_cats, use_container_width=True, hide_index=True, height=300)

    # ── Márgenes (solo Comestibles) ──
    if tienda == "Comestibles" and data_año.get("margenes"):
        st.subheader("Márgenes por categoría")
        margenes_total = {}
        for mes_str, cats in data_año.get("margenes", {}).items():
            for cat, val in cats.items():
                if cat not in margenes_total:
                    margenes_total[cat] = {"euros": 0, "margen_sum": 0, "n": 0}
                margenes_total[cat]["euros"] += val.get("euros", 0)
                margenes_total[cat]["margen_sum"] += val.get("margen_pct", 0)
                margenes_total[cat]["n"] += 1

        mg_sorted = sorted(margenes_total.items(), key=lambda x: x[1]["euros"], reverse=True)
        mg_names = [c[0] for c in mg_sorted]
        mg_pcts = [round(c[1]["margen_sum"] / c[1]["n"], 1) if c[1]["n"] > 0 else 0 for c in mg_sorted]
        mg_colors = ["#2E7D32" if p >= 40 else "#e8c97a" if p >= 25 else "#dc7070" for p in mg_pcts]

        fig_mg = go.Figure(data=[go.Bar(
            y=mg_names, x=mg_pcts, orientation="h",
            marker_color=mg_colors, text=[f"{p}%" for p in mg_pcts], textposition="outside",
            hovertemplate="%{y}: %{x:.1f}%<extra></extra>",
        )])
        fig_mg.update_layout(**PLOTLY_LAYOUT, height=max(200, len(mg_names) * 35),
                              xaxis_range=[0, max(mg_pcts) * 1.2 if mg_pcts else 100],
                              xaxis_ticksuffix="%", yaxis_autorange="reversed")
        st.plotly_chart(fig_mg, use_container_width=True, config=plotly_config())


# ─────────────────────────────────────────────────────────────────────────
# TAB PRODUCTOS
# ─────────────────────────────────────────────────────────────────────────
with tab_productos:

    # Filtros
    col_cat, col_per, col_n = st.columns([2, 2, 1])

    # Recopilar categorías disponibles
    todas_cats = set()
    for prods in data_año.get("top_productos", {}).values():
        for p in prods:
            todas_cats.add(p.get("cat", ""))
    todas_cats = sorted(c for c in todas_cats if c)

    with col_cat:
        cat_filtro = st.selectbox("Categoría", ["Todas"] + todas_cats, key="prod_cat")
    with col_per:
        meses_disponibles = sorted(mensual.keys(), key=int)
        opciones_mes = ["Acumulado"] + [MESES[int(m) - 1] for m in meses_disponibles]
        sel_mes = st.selectbox("Periodo", opciones_mes, key="prod_mes")
    with col_n:
        top_n = st.selectbox("Mostrar", [10, 15, 20], key="prod_n")

    # Agregar productos
    productos_acum = {}
    if sel_mes == "Acumulado":
        for mes_str, prods in data_año.get("top_productos", {}).items():
            for p in prods:
                if cat_filtro != "Todas" and p.get("cat", "") != cat_filtro:
                    continue
                nombre = p["art"]
                if nombre not in productos_acum:
                    productos_acum[nombre] = {"cat": p.get("cat", ""), "euros": 0, "cant": 0}
                productos_acum[nombre]["euros"] += p.get("euros", 0)
                productos_acum[nombre]["cant"] += p.get("cant", 0)
    else:
        mes_idx = opciones_mes.index(sel_mes)
        mes_str = meses_disponibles[mes_idx - 1]
        for p in data_año.get("top_productos", {}).get(mes_str, []):
            if cat_filtro != "Todas" and p.get("cat", "") != cat_filtro:
                continue
            nombre = p["art"]
            if nombre not in productos_acum:
                productos_acum[nombre] = {"cat": p.get("cat", ""), "euros": 0, "cant": 0}
            productos_acum[nombre]["euros"] += p.get("euros", 0)
            productos_acum[nombre]["cant"] += p.get("cant", 0)

    prods_sorted = sorted(productos_acum.items(), key=lambda x: x[1]["euros"], reverse=True)

    if prods_sorted:
        # Top N
        top_list = prods_sorted[:top_n]
        max_euros = top_list[0][1]["euros"] if top_list else 1

        st.caption(f"Top {min(top_n, len(top_list))} productos — {sel_mes}")
        fig_top = go.Figure(data=[go.Bar(
            y=[p[0] for p in top_list],
            x=[p[1]["euros"] for p in top_list],
            orientation="h",
            marker_color=color_1,
            text=[f"{p[1]['euros']:,.0f} €" for p in top_list],
            textposition="outside",
            hovertemplate="%{y}<br>%{x:,.0f} €<br>%{customdata} uds<extra></extra>",
            customdata=[round(p[1]["cant"], 1) for p in top_list],
        )])
        fig_top.update_layout(
            **PLOTLY_LAYOUT, height=max(250, len(top_list) * 32),
            xaxis_tickformat=",", xaxis_ticksuffix=" €",
            yaxis_autorange="reversed",
            margin=dict(l=10, r=80, t=10, b=30),
        )
        st.plotly_chart(fig_top, use_container_width=True, config=plotly_config())

        # Tabla completa en expander
        with st.expander(f"Ver tabla completa ({len(prods_sorted)} productos)"):
            df_prods = pd.DataFrame([
                {"#": i + 1, "Producto": k, "Categoría": v["cat"],
                 "Ventas €": f"{v['euros']:,.2f}", "Unidades": round(v["cant"], 1)}
                for i, (k, v) in enumerate(prods_sorted)
            ])
            st.dataframe(df_prods, use_container_width=True, hide_index=True)

        # Bottom N en expander
        if len(prods_sorted) > top_n:
            with st.expander(f"Menos vendidos (bottom {min(top_n, len(prods_sorted) - top_n)})"):
                bottom_list = prods_sorted[-top_n:][::-1]
                df_bottom = pd.DataFrame([
                    {"Producto": k, "Categoría": v["cat"],
                     "Ventas €": f"{v['euros']:,.2f}", "Unidades": round(v["cant"], 1)}
                    for k, v in bottom_list
                ])
                st.dataframe(df_bottom, use_container_width=True, hide_index=True)
    else:
        st.info("Sin datos de productos para este periodo y categoría.")


# ══════════════════════════════════════════════════════════════════════════
# Secciones condicionales (fuera de tabs)
# ══════════════════════════════════════════════════════════════════════════

# ── WooCommerce (solo Comestibles) ──
if tienda == "Comestibles" and datos.get("woo"):
    woo_data = datos["woo"]
    woo_meses = {m: v for m, v in woo_data.items() if v.get("euros", 0) > 0}
    woo_euros = sum(v.get("euros", 0) for v in woo_meses.values())
    woo_pedidos = sum(v.get("pedidos", 0) for v in woo_meses.values())
    if woo_euros > 0:
        st.divider()
        st.subheader("🌐 WooCommerce")
        c1, c2, c3 = st.columns(3)
        c1.metric("Ventas online", f"{woo_euros:,.0f} €")
        c2.metric("Pedidos", f"{woo_pedidos:,}")
        c3.metric("Ticket medio", f"{woo_euros / woo_pedidos:.2f} €" if woo_pedidos > 0 else "—")

        woo_sorted = sorted(woo_meses.items(), key=lambda x: int(x[0]))
        fig_woo = go.Figure(data=[go.Bar(
            x=[MESES[int(m) - 1] for m, _ in woo_sorted],
            y=[v.get("euros", 0) for _, v in woo_sorted],
            marker_color="#7ec8a0",
            hovertemplate="%{x}: %{y:,.0f} €<extra></extra>",
        )])
        fig_woo.update_layout(**PLOTLY_LAYOUT, height=200, yaxis_tickformat=",",
                               yaxis_ticksuffix=" €", showlegend=False)
        st.plotly_chart(fig_woo, use_container_width=True, config=plotly_config())

# ── Días de la semana (solo Tasca) ──
if tienda == "Tasca" and datos.get("dias_semana", {}).get(año):
    st.divider()
    st.subheader("📅 Ventas por día de la semana")
    dias_nombres = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
    dias_data = datos["dias_semana"][año]

    filas_dias = []
    for i in range(7):
        d = dias_data.get(str(i), {})
        filas_dias.append({
            "dia": dias_nombres[i],
            "euros": d.get("euros", 0),
            "tickets": d.get("tickets", 0),
            "tm": round(d.get("ticket_medio", 0), 2),
        })

    df_dias = pd.DataFrame(filas_dias)
    total_dias = df_dias["euros"].sum()

    fig_dias = go.Figure(data=[go.Bar(
        x=df_dias["dia"], y=df_dias["euros"],
        marker_color=[color_1 if e == df_dias["euros"].max() else color_2 for e in df_dias["euros"]],
        text=[f"{e:,.0f} €" for e in df_dias["euros"]], textposition="outside",
        hovertemplate="%{x}<br>%{y:,.0f} €<extra></extra>",
    )])
    fig_dias.update_layout(**PLOTLY_LAYOUT, height=280, yaxis_tickformat=",",
                            yaxis_ticksuffix=" €", showlegend=False)
    st.plotly_chart(fig_dias, use_container_width=True, config=plotly_config())

    # Tabla con % del total
    df_dias_show = pd.DataFrame([
        {"Día": r["dia"], "Ventas": f"{r['euros']:,.0f} €", "Tickets": r["tickets"],
         "Ticket medio": f"{r['tm']:.2f} €",
         "% total": f"{r['euros'] / total_dias * 100:.1f}%" if total_dias > 0 else "—"}
        for r in filas_dias if r["euros"] > 0
    ])
    st.dataframe(df_dias_show, use_container_width=True, hide_index=True)

# ── Link al dashboard completo ──
st.divider()
url_html = f"{NETLIFY_DASHBOARD}/{'comestibles' if tienda == 'Comestibles' else 'tasca'}.html"
st.link_button("📈 Ver dashboard completo en Netlify", url_html)
st.caption("Rotación, rentabilidad, análisis por canal y más visualizaciones avanzadas.")
