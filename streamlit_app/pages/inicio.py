"""
Página de inicio — Hub con 4 secciones principales.
"""

import streamlit as st
from utils.auth import require_role
from utils.data_client import backend_disponible, get_gmail, get_ventas_comes, fetch_backend_json

require_role(["admin", "socio", "comes", "eventos"])

# ── CSS tarjetas ──────────────────────────────────────────────────────────────

st.markdown(
    """
    <style>
    .hub-card {
        border-radius: 12px;
        padding: 1.5rem;
        min-height: 180px;
        display: flex;
        flex-direction: column;
        gap: 0.3rem;
        transition: transform 0.15s ease-out, box-shadow 0.15s ease-out;
    }
    .hub-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 16px rgba(0,0,0,0.08);
    }
    .hub-icon { font-size: 2.2rem; margin-bottom: 0.2rem; }
    .hub-title {
        font-family: 'Syne', sans-serif;
        font-weight: 700;
        font-size: 1.25rem;
        letter-spacing: -0.01em;
        margin: 0;
    }
    .hub-desc {
        font-family: 'DM Sans', sans-serif;
        font-size: 0.85rem;
        opacity: 0.7;
        margin: 0;
    }
    .hub-dato {
        font-family: 'DM Sans', sans-serif;
        font-weight: 500;
        font-size: 0.95rem;
        margin-top: auto;
        padding-top: 0.5rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ── Datos en vivo ─────────────────────────────────────────────────────────────

_backend_ok = backend_disponible()

def _dato_compras() -> str:
    if not _backend_ok:
        return "—"
    try:
        data = get_gmail()
        if data and "total_facturas" in data:
            return f"{data['total_facturas']} facturas procesadas"
        if data and "resumen" in data:
            return data["resumen"]
    except Exception:
        pass
    return "—"


def _dato_ventas() -> str:
    try:
        data = get_ventas_comes()
        if data and "total_semana" in data:
            total = data["total_semana"]
            if isinstance(total, (int, float)):
                formatted = f"{total:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                return f"{formatted} € esta semana"
        if data and "resumen" in data:
            return data["resumen"]
    except Exception:
        pass
    return "—"


def _dato_eventos() -> str:
    if not _backend_ok:
        return "—"
    try:
        data = fetch_backend_json("/api/data/eventos.json")
        if data and "proximo" in data:
            return data["proximo"]
    except Exception:
        pass
    return "—"


def _dato_operaciones() -> str:
    if _backend_ok:
        return "Backend conectado ✓"
    return "Backend no disponible"


# ── Renderizado ───────────────────────────────────────────────────────────────

st.markdown(
    """
    <h1 style="font-family:'Syne',sans-serif; font-weight:800; color:#8B0000;
               letter-spacing:-0.03em; margin-bottom:0.2rem;">
        Tasca Barea
    </h1>
    <p style="font-family:'DM Sans',sans-serif; color:#888; margin-bottom:2rem;">
        Panel de gestión
    </p>
    """,
    unsafe_allow_html=True,
)

SECCIONES = [
    {
        "icon": "📦", "titulo": "Compras",
        "desc": "Facturas, proveedores, parseo",
        "bg": "rgba(202,48,38,0.06)", "color": "#CA3026",
        "dato_fn": _dato_compras, "page": "pages/maestro.py",
    },
    {
        "icon": "📊", "titulo": "Ventas",
        "desc": "Dashboard ventas semanal",
        "bg": "rgba(172,200,162,0.09)", "color": "#1A2517",
        "dato_fn": _dato_ventas, "page": "pages/ventas.py",
    },
    {
        "icon": "🎪", "titulo": "Eventos",
        "desc": "Calendario y alta de eventos",
        "bg": "rgba(246,170,0,0.07)", "color": "#8B6D00",
        "dato_fn": _dato_eventos, "page": "pages/calendario_eventos.py",
    },
    {
        "icon": "⚙️", "titulo": "Operaciones",
        "desc": "Cuadre, scripts, monitor",
        "bg": "rgba(100,100,100,0.06)", "color": "#555",
        "dato_fn": _dato_operaciones, "page": "pages/ejecutar.py",
    },
]

cols = st.columns(2, gap="medium")

for i, sec in enumerate(SECCIONES):
    with cols[i % 2]:
        dato = sec["dato_fn"]()
        st.markdown(
            f"""
            <div class="hub-card" style="background:{sec['bg']}; border:1px solid {sec['color']}20;">
                <div class="hub-icon">{sec['icon']}</div>
                <p class="hub-title" style="color:{sec['color']};">{sec['titulo']}</p>
                <p class="hub-desc">{sec['desc']}</p>
                <p class="hub-dato" style="color:{sec['color']};">{dato}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button(f"Ir a {sec['titulo']}", key=f"btn_{sec['titulo'].lower()}", use_container_width=True):
            st.switch_page(sec["page"])
