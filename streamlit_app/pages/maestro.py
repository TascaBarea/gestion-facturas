"""
pages/maestro.py — Editor MAESTRO_PROVEEDORES (solo admin).
Buscar, filtrar y editar proveedores desde la app web.
"""

import urllib.parse

import streamlit as st
from utils.auth import require_role
from utils.data_client import (
    backend_disponible, fetch_backend_json,
    put_backend_json, post_backend_json,
)

require_role(["admin"])

st.title("Proveedores")

# ── Comprobar backend ─────────────────────────────────────────────────────────

if not backend_disponible():
    st.warning("Backend no disponible. El PC puede estar apagado.")
    st.stop()

# ── Cargar datos ──────────────────────────────────────────────────────────────

@st.cache_data(ttl=30)
def _cargar_maestro():
    return fetch_backend_json("/api/maestro")

data = _cargar_maestro()
if not data or "proveedores" not in data:
    st.error("No se pudo cargar el MAESTRO_PROVEEDORES.")
    st.stop()

proveedores = data["proveedores"]

# ── Barra de búsqueda y filtros ──────────────────────────────────────────────

col_busq, col_pago, col_activo = st.columns([3, 1.5, 1.5])

with col_busq:
    busqueda = st.text_input(
        "Buscar", placeholder="Nombre, alias, CIF o email...",
        label_visibility="collapsed",
    )

with col_pago:
    filtro_pago = st.selectbox("Forma pago", ["Todos", "TF", "TJ", "RC", "EF"], label_visibility="collapsed")

with col_activo:
    filtro_activo = st.selectbox("Activo", ["Todos", "SI", "NO"], label_visibility="collapsed")


# ── Filtrado ──────────────────────────────────────────────────────────────────

def _match(prov: dict, texto: str) -> bool:
    """Busca texto en nombre, aliases, CIF y email."""
    texto = texto.upper()
    if texto in prov["PROVEEDOR"].upper():
        return True
    if texto in prov.get("CIF", "").upper():
        return True
    if texto in prov.get("EMAIL", "").upper():
        return True
    for alias in prov.get("ALIAS", []):
        if texto in alias.upper():
            return True
    return False


filtrados = proveedores
if busqueda:
    filtrados = [p for p in filtrados if _match(p, busqueda.strip())]
if filtro_pago != "Todos":
    filtrados = [p for p in filtrados if p.get("FORMA_PAGO", "").upper() == filtro_pago]
if filtro_activo != "Todos":
    filtrados = [p for p in filtrados if p.get("ACTIVO", "").upper() == filtro_activo]

# ── Métricas ──────────────────────────────────────────────────────────────────

m1, m2, m3, m4 = st.columns(4)
m1.metric("Total", len(proveedores))
m2.metric("Filtrados", len(filtrados))
con_ext = sum(1 for p in proveedores if p.get("TIENE_EXTRACTOR", "").upper() == "SI")
m3.metric("Con extractor", con_ext)
activos = sum(1 for p in proveedores if p.get("ACTIVO", "").upper() == "SI")
m4.metric("Activos", activos)

# ── Tabla ─────────────────────────────────────────────────────────────────────

if not filtrados:
    st.info("Sin resultados para esa búsqueda.")
    st.stop()

tabla = []
for p in filtrados:
    tabla.append({
        "Proveedor": p["PROVEEDOR"],
        "Cuenta": p.get("CUENTA", ""),
        "Pago": p.get("FORMA_PAGO", ""),
        "Extractor": p.get("TIENE_EXTRACTOR", ""),
        "Categoría": p.get("CATEGORIA_FIJA", ""),
        "Aliases": len(p.get("ALIAS", [])),
    })

st.dataframe(
    tabla,
    use_container_width=True,
    hide_index=True,
    column_config={
        "Proveedor": st.column_config.TextColumn(width="large"),
        "Aliases": st.column_config.NumberColumn(width="small"),
    },
)

# ── Selector de proveedor ────────────────────────────────────────────────────

st.markdown("---")

nombres_filtrados = [p["PROVEEDOR"] for p in filtrados]
seleccion = st.selectbox("Seleccionar proveedor para editar", nombres_filtrados)

if seleccion:
    prov = next((p for p in filtrados if p["PROVEEDOR"] == seleccion), None)
    if prov:
        st.subheader(f"Editar: {seleccion}")

        def _safe_index(opciones, valor):
            """Índice seguro para selectbox."""
            val = valor.upper() if valor else ""
            return opciones.index(val) if val in opciones else 0

        with st.form("form_editar", clear_on_submit=False):
            col1, col2 = st.columns(2)

            with col1:
                nuevo_cuenta = st.text_input("Cuenta (código)", value=prov.get("CUENTA", ""))
                nuevo_cif = st.text_input("CIF", value=prov.get("CIF", ""))
                nuevo_iban = st.text_input("IBAN", value=prov.get("IBAN", ""))
                nuevo_pago = st.selectbox(
                    "Forma de pago",
                    ["", "TF", "TJ", "RC", "EF"],
                    index=_safe_index(["", "TF", "TJ", "RC", "EF"], prov.get("FORMA_PAGO", "")),
                )
                nuevo_email = st.text_input("Email", value=prov.get("EMAIL", ""))

            with col2:
                nuevo_extractor = st.selectbox(
                    "Tiene extractor",
                    ["", "SI", "NO"],
                    index=_safe_index(["", "SI", "NO"], prov.get("TIENE_EXTRACTOR", "")),
                )
                nuevo_archivo = st.text_input(
                    "Archivo extractor", value=prov.get("ARCHIVO_EXTRACTOR", ""),
                )
                nueva_cat = st.text_input("Categoría fija", value=prov.get("CATEGORIA_FIJA", ""))
                nuevo_activo = st.selectbox(
                    "Activo",
                    ["", "SI", "NO"],
                    index=_safe_index(["", "SI", "NO"], prov.get("ACTIVO", "")),
                )
                nuevas_notas = st.text_input("Notas", value=prov.get("NOTAS", ""))

            aliases_text = st.text_area(
                "Aliases (uno por línea)",
                value="\n".join(prov.get("ALIAS", [])),
                height=100,
            )

            st.caption("Los cambios se aplican en la próxima ejecución de Gmail/Cuadre.")

            submitted = st.form_submit_button("Guardar cambios", type="primary")

            if submitted:
                alias_list = [a.strip() for a in aliases_text.split("\n") if a.strip()]

                cambios = {}
                campos = {
                    "CUENTA": nuevo_cuenta,
                    "CIF": nuevo_cif,
                    "IBAN": nuevo_iban,
                    "FORMA_PAGO": nuevo_pago,
                    "EMAIL": nuevo_email,
                    "TIENE_EXTRACTOR": nuevo_extractor,
                    "ARCHIVO_EXTRACTOR": nuevo_archivo,
                    "CATEGORIA_FIJA": nueva_cat,
                    "ACTIVO": nuevo_activo,
                    "NOTAS": nuevas_notas,
                }
                for campo, nuevo_val in campos.items():
                    if nuevo_val != prov.get(campo, ""):
                        cambios[campo] = nuevo_val
                if alias_list != prov.get("ALIAS", []):
                    cambios["ALIAS"] = alias_list

                if not cambios:
                    st.info("No hay cambios.")
                else:
                    encoded_name = urllib.parse.quote(seleccion, safe="")
                    result = put_backend_json(f"/api/maestro/{encoded_name}", cambios)
                    if result is None:
                        st.error("Error de conexión con el backend.")
                    elif result.get("error"):
                        st.error(f"Error: {result.get('detail', 'desconocido')}")
                    else:
                        st.success("Proveedor actualizado correctamente.")
                        _cargar_maestro.clear()
                        st.rerun()

# ── Nuevo proveedor ──────────────────────────────────────────────────────────

st.markdown("---")

with st.expander("Crear nuevo proveedor"):
    with st.form("form_crear", clear_on_submit=True):
        col1, col2 = st.columns(2)

        with col1:
            np_nombre = st.text_input("Nombre del proveedor *")
            np_cuenta = st.text_input("Cuenta (código)", key="np_cuenta")
            np_cif = st.text_input("CIF", key="np_cif")
            np_iban = st.text_input("IBAN", key="np_iban")
            np_pago = st.selectbox("Forma de pago", ["", "TF", "TJ", "RC", "EF"], key="np_pago")
            np_email = st.text_input("Email", key="np_email")

        with col2:
            np_extractor = st.selectbox("Tiene extractor", ["", "SI", "NO"], key="np_ext")
            np_archivo = st.text_input("Archivo extractor", key="np_archivo")
            np_cat = st.text_input("Categoría fija", key="np_cat")
            np_activo = st.selectbox("Activo", ["SI", "NO"], key="np_activo")

        np_aliases = st.text_area("Aliases (uno por línea)", key="np_aliases", height=80)

        crear = st.form_submit_button("Crear proveedor", type="primary")

        if crear:
            if not np_nombre.strip():
                st.error("El nombre del proveedor es obligatorio.")
            else:
                body = {"PROVEEDOR": np_nombre.strip(), "ACTIVO": np_activo}
                for campo, val in [("CUENTA", np_cuenta), ("CIF", np_cif),
                                   ("IBAN", np_iban), ("FORMA_PAGO", np_pago),
                                   ("EMAIL", np_email), ("TIENE_EXTRACTOR", np_extractor),
                                   ("ARCHIVO_EXTRACTOR", np_archivo),
                                   ("CATEGORIA_FIJA", np_cat)]:
                    if val:
                        body[campo] = val
                aliases = [a.strip() for a in np_aliases.split("\n") if a.strip()]
                if aliases:
                    body["ALIAS"] = aliases

                result = post_backend_json("/api/maestro", body)
                if result is None:
                    st.error("Error de conexión con el backend.")
                elif result.get("error"):
                    st.error(f"Error: {result.get('detail', 'desconocido')}")
                else:
                    st.success(f"Proveedor '{np_nombre}' creado correctamente.")
                    _cargar_maestro.clear()
                    st.rerun()
