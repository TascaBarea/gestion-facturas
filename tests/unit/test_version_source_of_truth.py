from __future__ import annotations

import importlib.util
import os
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

EXPECTED_VERSION = "5.26"


def _load_parseo_settings(parseo_root: Path):
    settings_path = parseo_root / "config" / "settings.py"
    assert settings_path.exists(), f"No existe el settings canonico de Parseo: {settings_path}"

    spec = importlib.util.spec_from_file_location("parseo_settings_test", settings_path)
    assert spec is not None and spec.loader is not None, f"No se pudo cargar: {settings_path}"

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_version_source_of_truth_matches_parseo_canonico():
    from config.settings import VERSION as gestion_facturas_version

    default_parseo_root = Path(__file__).resolve().parents[2].parent / "Parseo"
    parseo_root = Path(os.environ.get("PARSEO_ROOT", default_parseo_root))
    parseo_settings = _load_parseo_settings(parseo_root)

    assert gestion_facturas_version == parseo_settings.VERSION
    assert parseo_settings.VERSION == EXPECTED_VERSION
    assert gestion_facturas_version == EXPECTED_VERSION
