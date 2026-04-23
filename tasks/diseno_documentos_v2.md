# PASO 2 — Diseño propuesto /documentos v2

**Fecha:** 24/04/2026

## Config cerrada

Constante al inicio del módulo. Orden = orden de aparición en la página.

```python
CARPETAS_DOCUMENTOS = [
    {
        "clave": "ventas",
        "titulo": "Ventas",
        "icono": "📊",
        "descripcion": "Dashboards y datos de ventas semanales",
        "ruta_drive": ["Ventas"],
        "subcarpetas": ["Año en curso", "Histórico"],
    },
    {
        "clave": "compras",
        "titulo": "Compras",
        "icono": "🧾",
        "descripcion": "Facturas procesadas y pagos registrados",
        "ruta_drive": ["Compras"],
        "subcarpetas": ["Año en curso", "Histórico"],
    },
    {
        "clave": "movimientos_banco",
        "titulo": "Movimientos Banco",
        "icono": "🏦",
        "descripcion": "Extractos y consolidados bancarios",
        "ruta_drive": ["Movimientos Banco"],
        "subcarpetas": ["Año en curso", "Histórico"],
    },
    {
        "clave": "articulos",
        "titulo": "Artículos",
        "icono": "📦",
        "descripcion": "Catálogo de productos",
        "ruta_drive": ["Articulos"],
        "subcarpetas": None,
    },
    {
        "clave": "maestro",
        "titulo": "Maestro",
        "icono": "📚",
        "descripcion": "MAESTRO_PROVEEDORES + Diccionario artículo→categoría",
        "ruta_drive": ["Maestro"],
        "subcarpetas": None,
    },
    {
        "clave": "cuadres",
        "titulo": "Cuadres",
        "icono": "⚖️",
        "descripcion": "Cuadres bancarios generados por cuadre.py",
        "ruta_drive": ["Cuadres"],
        "subcarpetas": None,
    },
]
```

**Orden de subcarpetas**: `["Año en curso", "Histórico"]` — "Año en curso" va primero por ser el más consultado.

## Lógica de render

Por cada entrada:

```python
for cfg in CARPETAS_DOCUMENTOS:
    st.markdown(f"### {cfg['icono']} {cfg['titulo']}")
    st.caption(cfg['descripcion'])

    if cfg["subcarpetas"]:
        # 2 pestañas (Año en curso | Histórico)
        tabs = st.tabs(cfg["subcarpetas"])
        for tab, sub in zip(tabs, cfg["subcarpetas"]):
            with tab:
                _listar_archivos(cfg["ruta_drive"] + [sub])
    else:
        _listar_archivos(cfg["ruta_drive"])
    st.markdown("")   # separador visual
```

Donde `_listar_archivos(ruta)` hace el trabajo actual de `_mostrar_carpeta` (llamar `listar_carpeta(ruta)` y pintar cards), sin el encabezado (ahora fuera en el caller).

**Por qué `st.tabs` vs expandir todo**: Ventas/Histórico tiene 1 archivo de 24MB que no queremos que domine la vista inicial. Pestañas mantiene la página corta y coherente; quien necesite histórico, un click.

## Cambios en la UI

- **"Facturas" → "Compras"** (alineado con Drive y con la estructura R.5).
- **6 secciones** en orden fijo: Ventas, Compras, Movimientos Banco, Artículos, Maestro, Cuadres.
- **Subcarpetas**: Ventas, Compras, Movimientos Banco tienen pestañas Año en curso/Histórico. Artículos, Maestro, Cuadres son planas.
- **Mensaje "Sin archivos en esta carpeta"**: se reusa el patrón existente (`st.info`).
- **Bloque "Otros archivos" de la raíz**: se elimina (tras R.5 no debería haber archivos sueltos, y si los hay son basura/error de sync — no se muestran en UI oficial).
- **Sidebar izquierdo**: NO se toca.

## Test mínimo (a añadir)

Como la página es Streamlit puro y no hay infra de tests de UI, añado un test sobre la **estructura de configuración**:

```python
# tests/unit/test_documentos_config.py
import importlib.util, pathlib, sys

_ROOT = pathlib.Path(__file__).resolve().parents[2]
_DOC_PATH = _ROOT / "streamlit_app" / "pages" / "documentos.py"

def _cargar_config():
    # Importar sin ejecutar el guard de require_role (monkeypatch Streamlit)
    # Truco: leer el AST y extraer CARPETAS_DOCUMENTOS sin ejecutar el módulo.
    import ast
    src = _DOC_PATH.read_text(encoding="utf-8")
    tree = ast.parse(src)
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "CARPETAS_DOCUMENTOS":
                    return ast.literal_eval(node.value)
    return None


def test_carpetas_documentos_existe():
    cfg = _cargar_config()
    assert cfg is not None, "CARPETAS_DOCUMENTOS no definida"
    assert len(cfg) == 6


def test_carpetas_claves_esperadas():
    cfg = _cargar_config()
    claves = {c["clave"] for c in cfg}
    assert claves == {"ventas", "compras", "movimientos_banco", "articulos", "maestro", "cuadres"}


def test_carpetas_con_subcarpetas_tienen_Año_en_curso_primero():
    cfg = _cargar_config()
    for c in cfg:
        if c["subcarpetas"]:
            assert c["subcarpetas"][0] == "Año en curso", (
                f"{c['clave']}: 'Año en curso' debe ir primero"
            )


def test_carpetas_planas_correctas():
    cfg = _cargar_config()
    planas = {c["clave"] for c in cfg if c["subcarpetas"] is None}
    assert planas == {"articulos", "maestro", "cuadres"}
```

El `ast.literal_eval` evita ejecutar el módulo (lo cual llamaría a `require_role` de Streamlit y fallaría en pytest). Limita el test a verificar la config, sin intentar renderizar Streamlit.

## Verificación manual

- Desde el propio Streamlit Cloud tras push: cargar `/documentos`, confirmar 6 secciones en el orden correcto, pestañas OK para las 3 primeras, archivos listados en Maestro (2 ficheros), Cuadres (vacío → "Sin archivos"), Articulos (1 fichero).
- `curl` contra `gestion.tascabarea.com/documentos` requiere login de Streamlit — no es verificable sin cookie. Valoraremos si merece la pena un test de `requests.get` con sesión. Por simplicidad, verificación visual.

## Riesgos

- **Ninguno fuera de esta página.** No se modifica `nucleo/sync_drive.py`, ni backends de otros módulos, ni scripts productivos.
- Si `listar_carpeta(["Cuadres"])` falla porque la carpeta no existe: el try/except actual captura y muestra error amigable — pero post-R.5 la carpeta existe (id `1iaW1BmqT1JALvVDCb0byCw8aR1u0gkoy`).
- **Tiempo de carga**: 6 secciones × hasta 2 subcarpetas = hasta 15 llamadas a Drive API por página load. Si resulta lento, considerar `@st.cache_data(ttl=60)` sobre `listar_carpeta`, pero lo dejo fuera de esta iteración.

## Aprobación implícita

Según la instrucción del usuario ("si lanzas autoaccept directo, asumo que el diseño es correcto"), procedo con la implementación tras guardar este documento.
