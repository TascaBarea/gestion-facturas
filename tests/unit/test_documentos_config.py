"""
tests/unit/test_documentos_config.py — verifica la config cerrada
CARPETAS_DOCUMENTOS de streamlit_app/pages/documentos.py.

No se ejecuta el módulo (Streamlit require_role fallaría en pytest);
se extrae la constante por AST.
"""
import ast
import pathlib


_ROOT = pathlib.Path(__file__).resolve().parents[2]
_DOC_PATH = _ROOT / "streamlit_app" / "pages" / "documentos.py"


def _cargar_config():
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
    assert len(cfg) == 6, f"Se esperaban 6 entradas, hay {len(cfg)}"


def test_carpetas_claves_esperadas():
    cfg = _cargar_config()
    claves = {c["clave"] for c in cfg}
    assert claves == {
        "ventas", "compras", "movimientos_banco",
        "articulos", "maestro", "cuadres",
    }


def test_carpetas_campos_obligatorios():
    cfg = _cargar_config()
    for c in cfg:
        for k in ("clave", "titulo", "icono", "descripcion", "ruta_drive", "subcarpetas"):
            assert k in c, f"Falta campo {k!r} en {c.get('clave')}"
        assert isinstance(c["ruta_drive"], list) and c["ruta_drive"], (
            f"ruta_drive debe ser lista no vacía: {c['clave']}"
        )
        assert c["subcarpetas"] is None or isinstance(c["subcarpetas"], list)


def test_subcarpetas_anio_en_curso_primero():
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


def test_ruta_drive_coincide_con_titulo_maestro_y_cuadres():
    cfg = _cargar_config()
    por_clave = {c["clave"]: c for c in cfg}
    assert por_clave["maestro"]["ruta_drive"] == ["Maestro"]
    assert por_clave["cuadres"]["ruta_drive"] == ["Cuadres"]
    assert por_clave["articulos"]["ruta_drive"] == ["Articulos"]
    assert por_clave["movimientos_banco"]["ruta_drive"] == ["Movimientos Banco"]
    assert por_clave["compras"]["ruta_drive"] == ["Compras"]
    assert por_clave["ventas"]["ruta_drive"] == ["Ventas"]
