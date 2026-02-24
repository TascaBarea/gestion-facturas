# tests/test_categorias.py
import os
import sys
import shutil
from pathlib import Path
import contextlib
import importlib
import pandas as pd
import pytest

# Asegura que `import facturas.categorias` funcione cuando ejecutas pytest desde la raíz del repo
# (raíz)
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def _make_excel(path: Path):
    df = pd.DataFrame(
        [
            {"Proveedor": "*", "Patron": "CERVEZA", "Categoria": "BEBIDAS", "Tipo": "SUBSTR"},
            {"Proveedor": "MARITA", "Patron": "ENVASE", "Categoria": "ENVASES", "Tipo": "SUBSTR"},
            {"Proveedor": "*", "Patron": r"^SODA\\s+\\d+L$", "Categoria": "REFRESCOS", "Tipo": "REGEX"},
            {"Proveedor": "*", "Patron": "VERMUT BENDITO BOX 20L", "Categoria": "BEBIDAS", "Tipo": "EXACT"},
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_excel(path, index=False)


@contextlib.contextmanager
def _temp_environ(**env):
    old = {k: os.environ.get(k) for k in env}
    try:
        for k, v in env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        yield
    finally:
        for k, v in old.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


@pytest.fixture()
def categorias_module():
    # Siempre recarga el módulo para que `from_default()` reevalúe rutas
    import facturas.categorias as categorias
    importlib.reload(categorias)
    return categorias


def test_from_default_uses_env_var(tmp_path, categorias_module):
    excel = tmp_path / "dict.xlsx"
    _make_excel(excel)

    with _temp_environ(FACTURAS_DICT=str(excel)):
        matcher = categorias_module.CategoriaMatcher.from_default()
        cat, motivo = matcher.match("MARITA", "Cerveza rubia 33cl pack")
        assert cat == "BEBIDAS"
        assert motivo and motivo.startswith("CatAuto:")


def test_from_default_uses_cwd(tmp_path, categorias_module, monkeypatch):
    # Copia el Excel con el nombre exacto esperado al CWD
    excel = tmp_path / categorias_module.DEFAULT_DICT_FILENAME
    _make_excel(excel)

    with monkeypatch.context() as m:
        m.chdir(tmp_path)
        with _temp_environ(FACTURAS_DICT=None):
            matcher = categorias_module.CategoriaMatcher.from_default()
            # Regla por proveedor
            cat, _ = matcher.match("MARITA", "Envase retorno 20 uds")
            assert cat == "ENVASES"
            # Regla REGEX
            cat, _ = matcher.match("CUALQUIERA", "SODA 2L")
            assert cat == "REFRESCOS"


def test_exact_and_fuzzy(categorias_module, tmp_path):
    excel = tmp_path / categorias_module.DEFAULT_DICT_FILENAME
    _make_excel(excel)

    with _temp_environ(FACTURAS_DICT=str(excel)):
        matcher = categorias_module.CategoriaMatcher.from_default()
        # EXACT
        cat, motivo = matcher.match("OTRO", "Vermut Bendito Box 20L")
        assert cat == "BEBIDAS"
        assert motivo and motivo.startswith("CatAuto:EXACT")
        # FUZZY (descripcion con pequeña variación)
        cat2, motivo2 = matcher.match("OTRO", "Vermut Benditto Bx 20 L")
        assert cat2 == "BEBIDAS"
        assert motivo2 and motivo2.startswith("CatAuto:FUZZY")
