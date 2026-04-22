"""
tests/unit/test_gmail_maestro_drive.py — tests de `load_maestro_from_drive`
y de la política v1.21 de proveedores nuevos.

Cubre:
- Windows (PC con G:): ruta existe → OK; no existe → MaestroDriveError.
- Linux (VPS): descarga Drive OK → devuelve path.
- Linux: descarga no encuentra archivo + caché existe → warning, usa caché.
- Linux: descarga no encuentra + sin caché → MaestroDriveError.
- Linux: descarga lanza excepción + caché existe → warning, usa caché.
- Linux: descarga lanza excepción + sin caché → MaestroDriveError.
- `_nombre_aproximado`: primera línea de PDF, fallback remitente, fallback email.

Todos los tests mockean sync_drive.descargar_archivo: NO tocan Drive real.
"""
import os
import sys
from unittest.mock import patch

import pytest

# Asegurar que el root del proyecto está en sys.path
_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from gmail.gmail import (
    GmailProcessor,
    MaestroDriveError,
    load_maestro_from_drive,
    resolver_maestro_path,
)


# ── resolver_maestro_path ────────────────────────────────────────────────────


def test_resolver_maestro_path_override(monkeypatch):
    monkeypatch.setenv("MAESTRO_OVERRIDE", "/tmp/custom/MAESTRO.xlsx")
    assert resolver_maestro_path(es_windows=True, base_path="/anything") == "/tmp/custom/MAESTRO.xlsx"
    assert resolver_maestro_path(es_windows=False, base_path="/anything") == "/tmp/custom/MAESTRO.xlsx"


def test_resolver_maestro_path_windows(monkeypatch):
    monkeypatch.delenv("MAESTRO_OVERRIDE", raising=False)
    path = resolver_maestro_path(es_windows=True, base_path=r"C:\whatever")
    assert path.endswith("MAESTRO_PROVEEDORES.xlsx")
    assert "Barea - Datos Compartidos" in path


def test_resolver_maestro_path_linux(monkeypatch):
    monkeypatch.delenv("MAESTRO_OVERRIDE", raising=False)
    path = resolver_maestro_path(es_windows=False, base_path="/opt/gestion-facturas")
    # os.path.join usa separador nativo; comparamos fin y segmentos relevantes
    assert path.endswith(os.path.join("datos", "MAESTRO_PROVEEDORES.xlsx"))
    assert "gestion-facturas" in path


# ── load_maestro_from_drive — Windows ────────────────────────────────────────


def test_windows_path_existe(tmp_path):
    ruta = tmp_path / "MAESTRO_PROVEEDORES.xlsx"
    ruta.write_bytes(b"fake-maestro")
    result = load_maestro_from_drive(str(ruta), es_windows=True)
    assert result == str(ruta)


def test_windows_path_no_existe(tmp_path):
    ruta = tmp_path / "no_existe" / "MAESTRO.xlsx"
    with pytest.raises(MaestroDriveError, match="MAESTRO no encontrado"):
        load_maestro_from_drive(str(ruta), es_windows=True)


# ── load_maestro_from_drive — Linux ──────────────────────────────────────────


def test_linux_drive_ok(tmp_path):
    """Descarga OK → devuelve ruta."""
    ruta = tmp_path / "MAESTRO.xlsx"

    def fake_descargar(nombre, carpeta, destino_local):
        # Simular descarga: escribir bytes en destino
        with open(destino_local, "wb") as f:
            f.write(b"descargado")
        return True

    with patch("nucleo.sync_drive.descargar_archivo", side_effect=fake_descargar):
        result = load_maestro_from_drive(str(ruta), es_windows=False)

    assert result == str(ruta)
    assert ruta.exists()
    assert ruta.read_bytes() == b"descargado"


def test_linux_drive_not_found_con_cache(tmp_path, caplog):
    """Drive dice 'no encontrado' + caché existe → warning + usa caché."""
    ruta = tmp_path / "MAESTRO.xlsx"
    ruta.write_bytes(b"cache-previa")

    with patch("nucleo.sync_drive.descargar_archivo", return_value=False):
        import logging
        with caplog.at_level(logging.WARNING, logger="gmail_module"):
            result = load_maestro_from_drive(str(ruta), es_windows=False)

    assert result == str(ruta)
    assert ruta.read_bytes() == b"cache-previa"
    assert any("usando caché" in rec.message.lower() for rec in caplog.records)


def test_linux_drive_not_found_sin_cache(tmp_path):
    """Drive dice 'no encontrado' + sin caché → raise."""
    ruta = tmp_path / "MAESTRO.xlsx"  # no creada

    with patch("nucleo.sync_drive.descargar_archivo", return_value=False):
        with pytest.raises(MaestroDriveError, match="no existe"):
            load_maestro_from_drive(str(ruta), es_windows=False)


def test_linux_drive_excepcion_con_cache(tmp_path, caplog):
    """Drive lanza excepción + caché existe → warning + usa caché."""
    ruta = tmp_path / "MAESTRO.xlsx"
    ruta.write_bytes(b"cache-previa")

    def boom(*args, **kwargs):
        raise RuntimeError("Drive 500")

    with patch("nucleo.sync_drive.descargar_archivo", side_effect=boom):
        import logging
        with caplog.at_level(logging.WARNING, logger="gmail_module"):
            result = load_maestro_from_drive(str(ruta), es_windows=False)

    assert result == str(ruta)
    assert any("drive" in rec.message.lower() for rec in caplog.records)


def test_linux_drive_excepcion_sin_cache(tmp_path):
    """Drive lanza excepción + sin caché → raise."""
    ruta = tmp_path / "MAESTRO.xlsx"  # no creada

    def boom(*args, **kwargs):
        raise RuntimeError("Drive 500")

    with patch("nucleo.sync_drive.descargar_archivo", side_effect=boom):
        with pytest.raises(MaestroDriveError, match="Fallo al descargar"):
            load_maestro_from_drive(str(ruta), es_windows=False)


# ── _nombre_aproximado (heurística PDF/remitente/email) ──────────────────────


def test_nombre_aproximado_primera_linea_pdf():
    texto = "Sabores de Paterna S.L.\nFactura Nº 12345\nFecha: 15/04/2026"
    result = GmailProcessor._nombre_aproximado(
        None, texto_pdf=texto, nombre_remitente="X", remitente_email="x@y.com"
    )
    assert result == "Sabores de Paterna S.L."


def test_nombre_aproximado_salta_lineas_no_utiles():
    # Primera línea "Factura N°" → se salta; segunda línea con letras → se usa
    texto = "Factura Nº 2026-001\nCeres Cerveza Artesana\nFecha: 20/03/2026"
    result = GmailProcessor._nombre_aproximado(
        None, texto_pdf=texto, nombre_remitente="X", remitente_email="x@y.com"
    )
    assert result == "Ceres Cerveza Artesana"


def test_nombre_aproximado_fallback_remitente():
    # PDF sin texto útil → usa nombre_remitente
    result = GmailProcessor._nombre_aproximado(
        None,
        texto_pdf="",
        nombre_remitente="Bodegas XYZ",
        remitente_email="contacto@bodegasxyz.com",
    )
    assert result == "Bodegas XYZ"


def test_nombre_aproximado_fallback_email_user():
    # Sin texto PDF ni nombre_remitente → usa parte antes del @
    result = GmailProcessor._nombre_aproximado(
        None,
        texto_pdf="",
        nombre_remitente="",
        remitente_email="proveedor.nuevo@dominio.com",
    )
    assert result == "proveedor.nuevo"


def test_nombre_aproximado_con_display_name():
    # remitente_email viene como "Nombre <email@host.com>"
    result = GmailProcessor._nombre_aproximado(
        None,
        texto_pdf="",
        nombre_remitente="",
        remitente_email='"Proveedor Nuevo" <pn@host.com>',
    )
    assert result == "pn"


def test_nombre_aproximado_desconocido():
    result = GmailProcessor._nombre_aproximado(
        None, texto_pdf="", nombre_remitente="", remitente_email=""
    )
    assert result == "DESCONOCIDO"
