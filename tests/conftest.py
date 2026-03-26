"""
conftest.py — Fixtures compartidas para todos los tests.
"""

import os
import sys
import tempfile

import pytest

# Asegurar que el proyecto raíz está en sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


@pytest.fixture()
def temp_dir():
    """Directorio temporal que se limpia al finalizar."""
    with tempfile.TemporaryDirectory() as d:
        yield d


@pytest.fixture()
def temp_excel(temp_dir):
    """Crea un Excel MAESTRO temporal mínimo para tests."""
    import openpyxl

    path = os.path.join(temp_dir, "MAESTRO_TEST.xlsx")
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Hoja1"
    headers = [
        "CUENTA", "PROVEEDOR", "CLASE", "ALIAS", "CIF", "IBAN",
        "FORMA_PAGO", "EMAIL", "TIENE_EXTRACTOR", "ARCHIVO_EXTRACTOR",
        "TIPO_CATEGORIA", "CATEGORIA_FIJA", "METODO_PDF", "ACTIVO", "NOTAS",
    ]
    ws.append(headers)
    ws.append([
        "41000101", "ACEITES JALEO", "ALIMENTACION",
        "ACEITES JALEO|JALEO ACEITE", "B12345678", "ES1234567890123456789012",
        "TF", "info@jaleo.com", "SI", "aceites_jaleo.py",
        "FIJA", "ACEITES Y VINAGRES", "pdfplumber", "SI", "",
    ])
    ws.append([
        "41000102", "CERES CERVEZA", "BEBIDAS",
        "CERES|CERVEZA CERES", "B87654321", "",
        "RC", "", "NO", "",
        "", "", "pdfplumber", "SI", "Sin IBAN",
    ])
    wb.save(path)
    yield path


@pytest.fixture()
def api_client():
    """TestClient de FastAPI con API key de admin configurada."""
    # Configurar env ANTES de importar la app
    os.environ["API_KEY"] = "test-admin-key-12345"
    os.environ["API_KEY_READONLY"] = "test-readonly-key-67890"
    os.environ["DEV_MODE"] = ""
    os.environ["CORS_ORIGINS"] = "http://127.0.0.1:8501"

    # Forzar recarga de config
    import importlib
    import api.config
    importlib.reload(api.config)
    import api.auth
    importlib.reload(api.auth)
    import api.server
    importlib.reload(api.server)

    from httpx import ASGITransport, AsyncClient
    transport = ASGITransport(app=api.server.app)
    return AsyncClient(transport=transport, base_url="http://test")


@pytest.fixture()
def admin_headers():
    """Headers con API key admin."""
    return {"Authorization": "Bearer test-admin-key-12345"}


@pytest.fixture()
def readonly_headers():
    """Headers con API key readonly."""
    return {"Authorization": "Bearer test-readonly-key-67890"}


@pytest.fixture()
def bad_headers():
    """Headers con API key inválida."""
    return {"Authorization": "Bearer invalid-key"}
