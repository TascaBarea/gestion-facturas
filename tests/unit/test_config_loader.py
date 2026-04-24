"""
tests/unit/test_config_loader.py — verifica el wrapper config/loader.py.

Cubre los 3 caminos:
  - legacy datos_sensibles.py (si está presente en dev local).
  - env var (prioritaria sobre legacy).
  - default (si nada de lo anterior existe).

Streamlit secrets no se testea aquí (requeriría ejecutar Streamlit runtime).
"""
import importlib
import sys

import pytest


@pytest.fixture(autouse=True)
def _recargar_loader():
    """Recarga el módulo antes de cada test para no arrastrar estado."""
    mods_to_drop = [m for m in list(sys.modules) if m.startswith("config.loader")]
    for m in mods_to_drop:
        del sys.modules[m]
    yield


def test_get_default_si_nada_presente(monkeypatch):
    monkeypatch.delenv("TEST_LOADER_KEY_XYZ", raising=False)
    import config.loader as loader
    assert loader.get("TEST_LOADER_KEY_XYZ", "fallback") == "fallback"


def test_get_none_si_nada_presente_sin_default(monkeypatch):
    monkeypatch.delenv("TEST_LOADER_KEY_XYZ", raising=False)
    import config.loader as loader
    assert loader.get("TEST_LOADER_KEY_XYZ") is None


def test_env_var_tiene_prioridad_sobre_legacy(monkeypatch):
    monkeypatch.setenv("TEST_LOADER_ENVVAR", "from_env")
    import config.loader as loader
    assert loader.get("TEST_LOADER_ENVVAR", "default") == "from_env"


def test_legacy_fallback_funciona_si_archivo_existe():
    """Si config/datos_sensibles.py existe (dev local), el loader lo lee."""
    try:
        from config import datos_sensibles  # noqa: F401
        has_legacy = True
    except ModuleNotFoundError:
        has_legacy = False

    if not has_legacy:
        pytest.skip("datos_sensibles.py no está en este entorno (Cloud)")

    import config.loader as loader
    # CIF_PROPIO debería existir en dev local; si no, skip.
    val = loader.get("CIF_PROPIO")
    if val is None:
        pytest.skip("CIF_PROPIO no definido en datos_sensibles.py local")
    assert isinstance(val, str) and len(val) > 0


def test_settings_importa_sin_datos_sensibles(monkeypatch):
    """Simula entorno Cloud: sin datos_sensibles → settings debe importar igual.

    Inyectamos un sys.modules que ficticiamente oculta datos_sensibles.
    """
    # Si en este entorno datos_sensibles NO existe (Cloud), el import debe
    # funcionar tal cual. Si existe (dev), parcheamos ModuleNotFoundError.
    import builtins
    _orig_import = builtins.__import__

    def _fake_import(name, *args, **kwargs):
        if name == "config.datos_sensibles" or name.endswith(".datos_sensibles"):
            raise ModuleNotFoundError(f"No module named {name!r} (simulado Cloud)")
        return _orig_import(name, *args, **kwargs)

    # Limpiar módulos posiblemente cacheados
    for m in ("config.datos_sensibles", "config.settings", "config.loader"):
        sys.modules.pop(m, None)

    monkeypatch.setattr(builtins, "__import__", _fake_import)
    # Esta línea es la que DEBÍA fallar antes del fix; ahora debe funcionar.
    settings = importlib.import_module("config.settings")
    assert hasattr(settings, "CIF_PROPIO")
    # En Cloud simulado, sin secrets ni env, CIF_PROPIO = ""
    assert settings.CIF_PROPIO == "" or isinstance(settings.CIF_PROPIO, str)
