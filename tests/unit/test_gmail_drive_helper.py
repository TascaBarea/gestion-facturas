"""
tests/unit/test_gmail_drive_helper.py — tests del helper `subir_pdf_a_drive_compras`.

Cubre los dos caminos del desacople Dropbox/Drive introducido en gmail.py v1.20:
- Con ruta_preexistente válida (PC con Dropbox) → reusa el path
- Sin ruta_preexistente (VPS sin Dropbox) → tmpdir con nombre canónico

Todos los tests mockean sync_archivos: NUNCA hablan con Drive real.
"""
import os
import sys
from datetime import datetime
from unittest.mock import patch, MagicMock

import pytest

# Asegurar que nucleo/ es importable desde el root del proyecto
_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from gmail.gmail import subir_pdf_a_drive_compras


# ── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture
def captura_sync():
    """Parchea sync_archivos dentro del helper; captura args de cada llamada."""
    calls = []

    def fake_sync(paths, carpeta):
        # Leer bytes del fichero para validar que el tmpdir tenía el contenido
        contenido = None
        if paths and os.path.exists(paths[0]):
            with open(paths[0], "rb") as f:
                contenido = f.read()
        calls.append({
            "paths": list(paths),
            "basenames": [os.path.basename(p) for p in paths],
            "carpeta": list(carpeta),
            "contenido": contenido,
        })
        return {os.path.basename(paths[0]): "mock-file-id"}

    with patch("nucleo.sync_drive.sync_archivos", side_effect=fake_sync):
        yield calls


# ── Tests ────────────────────────────────────────────────────────────────────

def test_sin_dropbox_escribe_tmpdir_y_sube(captura_sync):
    """VPS sin Dropbox: helper escribe bytes a tmpdir con nombre canónico y sube a Drive."""
    contenido = b"%PDF-1.4 contenido de prueba"
    nombre = "1T26 0315 PROVEEDOR TF.pdf"
    fecha = datetime(2026, 3, 15)

    ok = subir_pdf_a_drive_compras(
        contenido=contenido,
        nombre_archivo=nombre,
        fecha_factura=fecha,
        tiene_fecha=True,
        ruta_preexistente=None,
    )

    assert ok is True
    assert len(captura_sync) == 1
    call = captura_sync[0]
    # El path generado debe tener el nombre canónico (no un sufijo aleatorio de mkstemp)
    assert call["basenames"] == [nombre]
    assert call["carpeta"] == ["Compras", "Año en curso", "T1"]
    # Los bytes que Drive recibe coinciden con los originales
    assert call["contenido"] == contenido


def test_sin_dropbox_tmpdir_se_limpia(captura_sync):
    """Tras subir, el tmpdir no debe quedarse en disco."""
    paths_vistos = []

    def capture_and_return(paths, carpeta):
        paths_vistos.extend(paths)
        return {os.path.basename(paths[0]): "mock-id"}

    with patch("nucleo.sync_drive.sync_archivos", side_effect=capture_and_return):
        subir_pdf_a_drive_compras(
            contenido=b"x",
            nombre_archivo="test.pdf",
            fecha_factura=datetime(2026, 7, 1),
            tiene_fecha=True,
            ruta_preexistente=None,
        )

    assert paths_vistos, "sync_archivos debe haber sido llamado"
    # El fichero temporal y su directorio padre no deben existir tras el return
    tmp_file = paths_vistos[0]
    assert not os.path.exists(tmp_file), f"tmpfile no limpiado: {tmp_file}"
    assert not os.path.exists(os.path.dirname(tmp_file)), "tmpdir no limpiado"


def test_con_ruta_preexistente_reusa_path(captura_sync, tmp_path):
    """PC con Dropbox: si la ruta existe, se pasa tal cual a sync_archivos."""
    ruta_existente = tmp_path / "preexistente.pdf"
    ruta_existente.write_bytes(b"bytes en dropbox")

    ok = subir_pdf_a_drive_compras(
        contenido=b"otros-bytes-ignorados",
        nombre_archivo="nombre-distinto.pdf",
        fecha_factura=datetime(2026, 9, 30),
        tiene_fecha=True,
        ruta_preexistente=str(ruta_existente),
    )

    assert ok is True
    assert len(captura_sync) == 1
    call = captura_sync[0]
    assert call["paths"] == [str(ruta_existente)]
    # Sube el path pre-existente, NO crea ni sube el nombre_archivo alternativo
    assert call["basenames"] == ["preexistente.pdf"]
    assert call["carpeta"] == ["Compras", "Año en curso", "T3"]


def test_ruta_preexistente_inexistente_cae_a_tmpdir(captura_sync):
    """Si ruta_preexistente se pasa pero no existe en disco, se cae al path tmpdir."""
    ok = subir_pdf_a_drive_compras(
        contenido=b"bytes",
        nombre_archivo="factura.pdf",
        fecha_factura=datetime(2026, 11, 5),
        tiene_fecha=True,
        ruta_preexistente="/ruta/inexistente.pdf",
    )

    assert ok is True
    call = captura_sync[0]
    assert call["basenames"] == ["factura.pdf"]
    assert call["carpeta"] == ["Compras", "Año en curso", "T4"]


def test_sin_fecha_va_a_tpendiente(captura_sync):
    """tiene_fecha=False → subcarpeta T_pendiente."""
    ok = subir_pdf_a_drive_compras(
        contenido=b"x",
        nombre_archivo="sin-fecha.pdf",
        fecha_factura=datetime(2026, 5, 10),  # fecha_proceso (fallback)
        tiene_fecha=False,
        ruta_preexistente=None,
    )

    assert ok is True
    assert captura_sync[0]["carpeta"] == ["Compras", "Año en curso", "T_pendiente"]


def test_drive_fallo_propaga_excepcion():
    """Si sync_archivos lanza, el helper deja que la excepción suba (el caller decide)."""
    def boom(paths, carpeta):
        raise RuntimeError("Drive 500")

    with patch("nucleo.sync_drive.sync_archivos", side_effect=boom):
        with pytest.raises(RuntimeError, match="Drive 500"):
            subir_pdf_a_drive_compras(
                contenido=b"x",
                nombre_archivo="x.pdf",
                fecha_factura=datetime(2026, 1, 1),
                tiene_fecha=True,
                ruta_preexistente=None,
            )


def test_drive_devuelve_vacio_retorna_false(captura_sync):
    """Si sync_archivos devuelve dict vacío, el helper retorna False."""
    with patch("nucleo.sync_drive.sync_archivos", return_value={}):
        ok = subir_pdf_a_drive_compras(
            contenido=b"x",
            nombre_archivo="x.pdf",
            fecha_factura=datetime(2026, 2, 1),
            tiene_fecha=True,
            ruta_preexistente=None,
        )
    assert ok is False
