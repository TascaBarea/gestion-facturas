# -*- coding: utf-8 -*-
"""
Tests unitarios para v1.24 — fuente de verdad MAESTRO unificada.

Cubre:
  · resolver_maestro_path() siempre apunta a <base_path>/datos/
    MAESTRO_PROVEEDORES.xlsx, sin importar plataforma.
  · MAESTRO_OVERRIDE env var sigue funcionando.
  · _MAESTRO_PATH_WINDOWS, MaestroDriveError, load_maestro_from_drive
    han sido eliminados.

Ejecutar: pytest tests/unit/test_maestro_path.py -v
"""
import os
import pytest


pytestmark = pytest.mark.unit


def test_resolver_maestro_path_windows_apunta_a_datos():
    """En Windows, debe apuntar a <base_path>/datos/, no a G:\\."""
    from gmail.gmail import resolver_maestro_path
    ruta = resolver_maestro_path(es_windows=True, base_path="/tmp/repo")
    assert ruta.endswith("MAESTRO_PROVEEDORES.xlsx")
    assert "datos" in ruta
    assert "G:" not in ruta
    assert "Maestro" not in ruta or "datos" in ruta  # 'Maestro' solo dentro del nombre


def test_resolver_maestro_path_linux_apunta_a_datos():
    """En Linux, sigue apuntando a <base_path>/datos/."""
    from gmail.gmail import resolver_maestro_path
    ruta = resolver_maestro_path(es_windows=False, base_path="/opt/gestion-facturas")
    assert ruta.endswith("MAESTRO_PROVEEDORES.xlsx")
    assert "datos" in ruta


def test_resolver_maestro_path_windows_y_linux_dan_misma_ruta():
    """Tras v1.24, Windows y Linux dan la misma ruta para el mismo base_path."""
    from gmail.gmail import resolver_maestro_path
    base = "/cualquier/base"
    assert resolver_maestro_path(True, base) == resolver_maestro_path(False, base)


def test_maestro_override_env_var_funciona(monkeypatch):
    """MAESTRO_OVERRIDE env var sigue forzando ruta para tests/dev."""
    from gmail.gmail import resolver_maestro_path
    monkeypatch.setenv("MAESTRO_OVERRIDE", "/ruta/custom/MAESTRO.xlsx")
    ruta = resolver_maestro_path(es_windows=True, base_path="/no/usado")
    assert ruta == "/ruta/custom/MAESTRO.xlsx"


def test_maestro_drive_error_no_existe():
    """v1.24: MaestroDriveError ha sido eliminado."""
    import gmail.gmail
    assert not hasattr(gmail.gmail, 'MaestroDriveError'), \
        "MaestroDriveError debería haber sido eliminado en v1.24"


def test_load_maestro_from_drive_no_existe():
    """v1.24: load_maestro_from_drive ha sido eliminada."""
    import gmail.gmail
    assert not hasattr(gmail.gmail, 'load_maestro_from_drive'), \
        "load_maestro_from_drive debería haber sido eliminada en v1.24"


def test_maestro_path_windows_no_existe():
    """v1.24: _MAESTRO_PATH_WINDOWS ha sido eliminada."""
    import gmail.gmail
    assert not hasattr(gmail.gmail, '_MAESTRO_PATH_WINDOWS'), \
        "_MAESTRO_PATH_WINDOWS debería haber sido eliminada en v1.24"
