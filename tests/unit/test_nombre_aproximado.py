"""
tests/unit/test_nombre_aproximado.py — heurística de proveedor nuevo.

Cubre `GmailProcessor._nombre_aproximado`: extrae el nombre del proveedor
nuevo desde el texto del PDF, con fallbacks al nombre del remitente y al
local-part del email.

Originalmente estos tests vivían en `test_gmail_maestro_drive.py` junto a
tests de `MaestroDriveError` y `load_maestro_from_drive`. Esos últimos
testaban API eliminada en v1.24 (sesión MAESTRO fuente verdad 06/05/2026)
y se borraron; estos tests se preservan en archivo propio porque la
funcionalidad sigue siendo válida.
"""
import os
import sys

import pytest

# Asegurar que el root del proyecto está en sys.path
_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from gmail.gmail import GmailProcessor


pytestmark = pytest.mark.unit


def test_nombre_aproximado_primera_linea_pdf():
    # v1.25: la heurística usa self (helpers + lista negra), por lo que se
    # invoca con instancia. Usamos __new__ para evitar cargar MAESTRO
    # (gitignored, no existe en CI runner).
    proc = GmailProcessor.__new__(GmailProcessor)
    texto = "Sabores de Paterna S.L.\nFactura Nº 12345\nFecha: 15/04/2026"
    result = proc._nombre_aproximado(
        texto_pdf=texto, nombre_remitente="X", remitente_email="x@y.com"
    )
    assert result == "Sabores de Paterna S.L."


def test_nombre_aproximado_salta_lineas_no_utiles():
    # Primera línea "Factura N°" → se salta; segunda línea con letras → se usa
    proc = GmailProcessor.__new__(GmailProcessor)
    texto = "Factura Nº 2026-001\nCeres Cerveza Artesana\nFecha: 20/03/2026"
    result = proc._nombre_aproximado(
        texto_pdf=texto, nombre_remitente="X", remitente_email="x@y.com"
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
