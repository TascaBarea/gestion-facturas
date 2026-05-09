# -*- coding: utf-8 -*-
"""
Tests v1.26 — lock-safe Excel handling en gmail/gmail.py.

Cubre:
  · Cambio 1 — pre-flight check de Excels (r+b, no open('a'))
  · Cambio 2 — filtro de pendientes ignora motivos "error:..." y "limpieza_pre_v1.13"
  · Cambio 3 — ExcelBloqueadoError mid-flight + reordering del move al final
  · Recovery counter

Ejecutar: pytest tests/unit/test_gmail_lock_safe.py -v
"""
import json
import os
import sys
from unittest.mock import MagicMock, patch

import pytest


pytestmark = pytest.mark.unit


# ============================================================================
# Helpers de fixtures
# ============================================================================

@pytest.fixture
def control_factory(tmp_path):
    """Factory que crea un ControlDuplicados con un JSON inicial."""
    from gmail.gmail import ControlDuplicados

    def _make(emails: dict):
        ruta = tmp_path / "emails_procesados.json"
        ruta.write_text(
            json.dumps({"emails": emails, "hashes": {}, "facturas": {}}),
            encoding="utf-8",
        )
        return ControlDuplicados(str(ruta))

    return _make


# ============================================================================
# CAMBIO 1 — Pre-flight check
# ============================================================================

class TestPreFlight:
    def test_excel_disponible_ok_si_no_existe(self, tmp_path):
        """Si el Excel no existe, _excel_disponible devuelve OK (lo creará el script)."""
        from gmail.gmail import _excel_disponible

        ruta = str(tmp_path / "no_existe.xlsx")
        ok, motivo = _excel_disponible(ruta)
        assert ok is True
        assert motivo is None

    def test_excel_disponible_ok_si_se_puede_abrir_rb(self, tmp_path):
        """Si el archivo existe y se puede abrir en r+b, devuelve OK."""
        from gmail.gmail import _excel_disponible

        ruta = tmp_path / "vacio.xlsx"
        ruta.write_bytes(b"contenido")
        ok, motivo = _excel_disponible(str(ruta))
        assert ok is True
        assert motivo is None

    def test_excel_disponible_detecta_permission_error(self, tmp_path):
        """Si open('r+b') lanza PermissionError, devuelve (False, motivo)."""
        from gmail.gmail import _excel_disponible

        ruta = tmp_path / "bloqueado.xlsx"
        ruta.write_bytes(b"contenido")

        # Mock open() para que solo lance PermissionError sobre nuestra ruta
        original_open = open

        def mock_open(path, *args, **kwargs):
            if str(path) == str(ruta) and "r+b" in (args[0] if args else kwargs.get("mode", "")):
                raise PermissionError("[Errno 13] Permission denied")
            return original_open(path, *args, **kwargs)

        with patch("builtins.open", side_effect=mock_open):
            ok, motivo = _excel_disponible(str(ruta))

        assert ok is False
        assert motivo is not None
        assert "bloqueado" in motivo.lower()

    def test_pre_flight_aborta_si_excel_bloqueado(self, tmp_path, monkeypatch):
        """Si pre_flight_check_excels detecta un Excel bloqueado → SystemExit(1)."""
        from gmail import gmail as g

        # Forzar OUTPUT_PATH a tmp_path para no tocar outputs/ reales
        monkeypatch.setattr(g.CONFIG, "OUTPUT_PATH", str(tmp_path))

        # Crear el PAGOS_Gmail del trimestre actual y mockear _excel_disponible
        # para que devuelva False sobre él.
        from datetime import datetime
        trim = g.obtener_trimestre(datetime.now())
        excel_path = tmp_path / f"PAGOS_Gmail_{trim}.xlsx"
        excel_path.write_bytes(b"x")

        proc = g.GmailProcessor(modo_test=True)
        proc.dropbox = None  # sin Dropbox: solo se chequean los locales

        def fake_disponible(path):
            if str(path) == str(excel_path):
                return False, "bloqueado (probablemente abierto en Excel)"
            return True, None

        with patch.object(g, "_excel_disponible", side_effect=fake_disponible):
            with pytest.raises(SystemExit) as exc_info:
                proc.pre_flight_check_excels(datetime.now())

        assert exc_info.value.code == 1

    def test_pre_flight_pasa_si_excels_no_existen(self, tmp_path, monkeypatch):
        """Pre-flight pasa si los archivos no existen (los creará el script)."""
        from gmail import gmail as g
        from datetime import datetime

        monkeypatch.setattr(g.CONFIG, "OUTPUT_PATH", str(tmp_path))

        proc = g.GmailProcessor(modo_test=True)
        proc.dropbox = None

        # No raise → pasa
        proc.pre_flight_check_excels(datetime.now())


# ============================================================================
# CAMBIO 2 — Filtro de pendientes
# ============================================================================

class TestFiltroPendientes:
    def test_excluye_errores_antiguos(self, control_factory):
        """Entrada con motivo 'error: ...' NO cuenta como procesado."""
        ctrl = control_factory({
            "id_ok": {"archivo": "1T26 0101 X TF.pdf", "fecha_proceso": "2026-01-01"},
            "id_error": {"motivo": "error: [Errno 13] Permission denied"},
            "id_reenvio": {"motivo": "reenvío propio"},
        })

        assert ctrl.email_procesado("id_ok") is True
        assert ctrl.email_procesado("id_error") is False  # ← se reprocesará
        assert ctrl.email_procesado("id_reenvio") is True

    def test_excluye_limpieza_pre_v113(self, control_factory):
        """Entrada con motivo 'limpieza_pre_v1.13' NO cuenta como procesado."""
        ctrl = control_factory({
            "id_limpieza": {"motivo": "limpieza_pre_v1.13"},
        })

        assert ctrl.email_procesado("id_limpieza") is False

    def test_motivos_descarte_legitimo_si_cuentan(self, control_factory):
        """Motivos de descarte legítimo SÍ cuentan como procesados (no reprocesar)."""
        ctrl = control_factory({
            "id1": {"motivo": "reenvío propio"},
            "id2": {"motivo": "sin adjuntos"},
            "id3": {"motivo": "duplicado"},
            "id4": {"motivo": "Duplicado (CIF+REF) — descartado"},
        })

        for k in ("id1", "id2", "id3", "id4"):
            assert ctrl.email_procesado(k) is True, f"{k} debería contar como procesado"

    def test_email_inexistente_no_es_procesado(self, control_factory):
        ctrl = control_factory({})
        assert ctrl.email_procesado("id_que_no_existe") is False

    def test_entrada_anomala_se_reprocesa(self, control_factory):
        """Entrada sin motivo y sin archivo (estado raro) → reprocesar por seguridad."""
        ctrl = control_factory({
            "id_raro": {"fecha_proceso": "2026-01-01"},  # sin motivo, sin archivo
        })
        assert ctrl.email_procesado("id_raro") is False

    def test_contar_emails_a_recuperar(self, control_factory):
        """contar_emails_a_recuperar cuenta error: + limpieza_pre_v1.13."""
        ctrl = control_factory({
            "ok1": {"archivo": "x.pdf"},
            "err1": {"motivo": "error: [Errno 13] Permission denied"},
            "err2": {"motivo": "error: timeout"},
            "limp": {"motivo": "limpieza_pre_v1.13"},
            "ren": {"motivo": "reenvío propio"},
        })
        assert ctrl.contar_emails_a_recuperar() == 3


# ============================================================================
# CAMBIO 3 — ExcelBloqueadoError mid-flight + reordering del move
# ============================================================================

class TestExcelBloqueadoMidFlight:
    """Tests del flujo transaccional: si el Excel falla a mitad,
    NO se marca como procesado y NO se mueve la etiqueta Gmail.
    """

    def _make_processor_with_mocks(self, tmp_path, monkeypatch):
        """Crea GmailProcessor con maestro/control/gmail/dropbox mockeados."""
        from gmail import gmail as g

        monkeypatch.setattr(g.CONFIG, "OUTPUT_PATH", str(tmp_path))
        monkeypatch.setattr(g.CONFIG, "JSON_PATH", str(tmp_path / "emails.json"))
        monkeypatch.setattr(g.CONFIG, "BACKUPS_PATH", str(tmp_path / "backups"))

        # JSON vacío para que ControlDuplicados arranque limpio
        (tmp_path / "emails.json").write_text(
            json.dumps({"emails": {}, "hashes": {}, "facturas": {}}),
            encoding="utf-8",
        )

        with patch.object(g, "MaestroProveedores") as mock_maestro_cls:
            mock_maestro_cls.return_value = MagicMock()
            proc = g.GmailProcessor(modo_test=False)

        proc.gmail = MagicMock()
        proc.dropbox = MagicMock()
        # Simular subida Dropbox OK (no duplicado, ruta plausible)
        proc.dropbox.subir_archivo.return_value = (
            os.path.join(str(tmp_path), "fake_dropbox.pdf"), False
        )
        return proc, g

    def test_excel_falla_a_mitad_no_marca_procesado(self, tmp_path, monkeypatch):
        """Si _procesar_pdf lanza ExcelBloqueadoError, el email NO se registra
        en el JSON ni se mueve la etiqueta. La excepción se propaga.
        """
        proc, g = self._make_processor_with_mocks(tmp_path, monkeypatch)

        email_data = {
            "id": "msg_falla_excel",
            "from": "facturacion@proveedor.com",
            "subject": "Factura abril",
            "message_id": "<x@x>",
            "internal_date": None,
            "payload": {},
        }

        # Simular que descargar_adjuntos devuelve un PDF falso
        proc.gmail.descargar_adjuntos.return_value = [("factura.pdf", b"%PDF-1.4 fake")]

        # Forzar a _procesar_pdf a lanzar ExcelBloqueadoError directamente
        def fake_procesar_pdf(resultado, nombre, contenido, fecha):
            raise g.ExcelBloqueadoError("PermissionError simulado")

        with patch.object(proc, "_procesar_pdf", side_effect=fake_procesar_pdf):
            from datetime import datetime
            with pytest.raises(g.ExcelBloqueadoError):
                proc._procesar_email(email_data, datetime.now())

        # Verificar que el email NO está en el JSON
        assert "msg_falla_excel" not in proc.control.datos["emails"]
        # Verificar que NO se llamó a mover_a_procesados_y_marcar_leido
        proc.gmail.mover_a_procesados_y_marcar_leido.assert_not_called()

    def test_email_no_se_mueve_si_excel_falla_a_mitad(self, tmp_path, monkeypatch):
        """Test del reordering (paso 6 = move al final): si Excel falla,
        la etiqueta Gmail NO debe moverse. Distinto al test anterior porque
        este verifica explícitamente la consecuencia para el flujo Gmail.
        """
        proc, g = self._make_processor_with_mocks(tmp_path, monkeypatch)

        email_data = {
            "id": "msg_recuperable",
            "from": "x@y.com",
            "subject": "Factura X",
            "message_id": "",
            "internal_date": None,
            "payload": {},
        }

        proc.gmail.descargar_adjuntos.return_value = [("f.pdf", b"%PDF")]

        with patch.object(proc, "_procesar_pdf",
                          side_effect=g.ExcelBloqueadoError("simulado")):
            from datetime import datetime
            with pytest.raises(g.ExcelBloqueadoError):
                proc._procesar_email(email_data, datetime.now())

        # Etiqueta Gmail INTACTA → próxima ejecución verá el email como pendiente
        proc.gmail.mover_a_procesados_y_marcar_leido.assert_not_called()
        # Y no está marcado en el JSON
        assert proc.control.email_procesado("msg_recuperable") is False

    def test_procesado_normal_si_mueve_etiqueta_al_final(self, tmp_path, monkeypatch):
        """En el camino feliz: PDF procesado OK → JSON registrado → etiqueta movida."""
        proc, g = self._make_processor_with_mocks(tmp_path, monkeypatch)

        email_data = {
            "id": "msg_ok",
            "from": "x@y.com",
            "subject": "Factura OK",
            "message_id": "",
            "internal_date": None,
            "payload": {},
        }

        proc.gmail.descargar_adjuntos.return_value = [("f.pdf", b"%PDF")]

        # Simular _procesar_pdf que rellena el resultado mínimo y NO falla
        def fake_pdf(resultado, nombre, contenido, fecha):
            resultado.archivo_generado = "1T26 0101 PROVEEDOR TF.pdf"
            resultado.dropbox_path = "/dropbox/fake.pdf"

        with patch.object(proc, "_procesar_pdf", side_effect=fake_pdf):
            from datetime import datetime
            proc._procesar_email(email_data, datetime.now())

        # Email registrado
        assert "msg_ok" in proc.control.datos["emails"]
        # Etiqueta movida (paso final confirmatorio)
        proc.gmail.mover_a_procesados_y_marcar_leido.assert_called_once_with("msg_ok")


# ============================================================================
# Sanity: versión bumpeada
# ============================================================================

def test_version_es_1_26():
    from gmail.gmail import VERSION
    assert VERSION == "1.26"
