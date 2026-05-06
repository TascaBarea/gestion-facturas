# -*- coding: utf-8 -*-
"""
Tests unitarios para quick wins Bloque A (auditoría 06/05/2026).

Cubre:
  · QW1 — versión ya no hardcodeada en strings activos
  · QW3 — validación defensiva de scopes en GmailClient.conectar()
  · QW4 — LocalDropboxClient lanza FileNotFoundError
  · QW5 — ProveedorNuevoDetectado dataclass

QW2 (race condition OCR) no se testea unitariamente: requiere PDF
imagen + Windows + AV; cubierto por validación natural en producción.

Ejecutar: pytest tests/unit/test_gmail_quick_wins.py -v
"""
import pytest
from datetime import datetime
from unittest.mock import patch, MagicMock


pytestmark = pytest.mark.unit


# ============================================================================
# QW1 — VERSIÓN NO HARDCODEADA
# ============================================================================

def test_no_hay_v1_14_hardcoded_en_codigo_activo():
    """En gmail/gmail.py no debe quedar 'v1.14' hardcoded fuera de docstrings.

    Excepción válida: las cabeceras de notas históricas dentro del docstring
    inicial ('MEJORAS v1.14:', 'v1.14 fix:') sí pueden mantenerse como
    histórico documental.
    """
    import os
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    ruta = os.path.join(repo_root, 'gmail', 'gmail.py')
    with open(ruta, encoding='utf-8') as f:
        contenido = f.read()

    # Strings NO permitidas en código activo
    prohibidos = [
        '<h2>📧 Gmail Module v1.14',
        'asunto = f"Gmail Module v1.14',
        'description="Gmail Module v1.15',
    ]
    for s in prohibidos:
        assert s not in contenido, f"String hardcodeada encontrada: {s!r}"


def test_version_constante_se_usa_en_strings_visibles():
    """VERSION debe usarse vía f-string en HTML, asunto y argparse."""
    import os
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    ruta = os.path.join(repo_root, 'gmail', 'gmail.py')
    with open(ruta, encoding='utf-8') as f:
        contenido = f.read()

    assert 'Gmail Module v{self.version}' in contenido
    assert 'description=f"Gmail Module v{VERSION}' in contenido


def test_notificador_acepta_parametro_version():
    """Notificador.__init__ debe aceptar `version` como keyword argument."""
    import inspect
    from gmail.gmail import Notificador

    sig = inspect.signature(Notificador.__init__)
    assert 'version' in sig.parameters, \
        "Notificador.__init__ debe aceptar parámetro `version`"


# ============================================================================
# QW3 — VALIDACIÓN SCOPES TOKEN
# ============================================================================

def test_token_scopes_insuficientes_lanza_runtime_error(tmp_path):
    """Si el token tiene menos scopes de los esperados, conectar() debe abortar."""
    from gmail.gmail import GmailClient

    token_path = tmp_path / "token.json"
    token_path.write_text("{}")

    creds_mock = MagicMock()
    creds_mock.scopes = [
        'https://www.googleapis.com/auth/gmail.readonly',
        # falta gmail.modify, drive — subset incompleto
    ]
    creds_mock.valid = True
    creds_mock.expired = False

    client = GmailClient(str(tmp_path / "creds.json"), str(token_path))

    with patch('gmail.gmail.Credentials.from_authorized_user_file',
               return_value=creds_mock):
        with pytest.raises(RuntimeError) as exc_info:
            client.conectar()

    assert 'scopes' in str(exc_info.value).lower()


def test_token_con_todos_los_scopes_no_aborta_por_validacion(tmp_path):
    """Si el token tiene TODOS los scopes esperados, la validación no debe
    abortar (otros mocks pueden fallar pero NO por scopes)."""
    from gmail.gmail import GmailClient, CONFIG

    token_path = tmp_path / "token.json"
    token_path.write_text("{}")

    creds_mock = MagicMock()
    creds_mock.scopes = list(CONFIG.GMAIL_SCOPES)
    creds_mock.valid = True
    creds_mock.expired = False

    client = GmailClient(str(tmp_path / "creds.json"), str(token_path))

    with patch('gmail.gmail.Credentials.from_authorized_user_file',
               return_value=creds_mock):
        with patch('gmail.gmail.build'):
            with patch.object(GmailClient, '_cargar_labels'):
                try:
                    client.conectar()
                except RuntimeError as e:
                    if 'scopes' in str(e).lower():
                        pytest.fail(f"RuntimeError de scopes inesperado: {e}")


# ============================================================================
# QW4 — FileNotFoundError
# ============================================================================

def test_local_dropbox_client_lanza_file_not_found_error():
    """LocalDropboxClient debe lanzar FileNotFoundError, no Exception."""
    from gmail.gmail import LocalDropboxClient

    with pytest.raises(FileNotFoundError):
        LocalDropboxClient("/ruta/que/no/existe/jamas")


# ============================================================================
# QW5 — ProveedorNuevoDetectado dataclass
# ============================================================================

def test_proveedor_nuevo_detectado_dataclass_existe():
    """Debe existir el dataclass ProveedorNuevoDetectado con defaults."""
    from gmail.gmail import ProveedorNuevoDetectado
    p = ProveedorNuevoDetectado(cif="B85501989", nombre_aproximado="COMPROVINO SL")
    assert p.cif == "B85501989"
    assert p.nombre_aproximado == "COMPROVINO SL"
    assert p.iban == ""
    assert p.referencia == ""
    assert p.total is None
    assert p.fecha is None


def test_proveedor_nuevo_detectado_acepta_todos_los_campos():
    """Todos los campos pueden poblarse."""
    from gmail.gmail import ProveedorNuevoDetectado
    fecha = datetime(2026, 4, 30)
    p = ProveedorNuevoDetectado(
        cif="B85501989",
        nombre_aproximado="COMPROVINO SL",
        iban="ES34 0049 6129 0020 1603 4741",
        referencia="A/261096",
        total=255.21,
        fecha=fecha,
    )
    assert p.iban.startswith("ES34")
    assert p.total == 255.21
    assert p.fecha == fecha
