"""
Tests de seguridad para la API FastAPI.

Verifica: path traversal, autenticación, RBAC, validación de uploads,
validación de argumentos de scripts.
"""

import os
import pytest


# ── Path traversal ───────────────────────────────────────────────────────────

@pytest.mark.unit
class TestPathTraversal:
    """S1: El endpoint /api/data/{filename} no permite path traversal."""

    async def test_dot_dot_slash_blocked(self, api_client, admin_headers):
        """Path traversal via ../ — FastAPI normaliza URL, basename limpia el resto."""
        r = await api_client.get("/api/data/../../../etc/passwd.json", headers=admin_headers)
        # FastAPI normaliza la URL → llega "passwd.json" → basename OK → 404 (no existe)
        # Lo importante: no devuelve 200 con contenido de /etc/passwd
        assert r.status_code in (400, 404)

    async def test_backslash_traversal_blocked(self, api_client, admin_headers):
        r = await api_client.get("/api/data/..\\..\\etc\\passwd.json", headers=admin_headers)
        assert r.status_code in (400, 404)  # basename limpia backslashes

    async def test_dot_dot_in_name_blocked(self, api_client, admin_headers):
        r = await api_client.get("/api/data/..%2F..%2Fetc%2Fpasswd.json", headers=admin_headers)
        # URL-encoded ../ — FastAPI puede decodificar o no
        assert r.status_code in (400, 404)

    async def test_simple_filename_allowed(self, api_client, admin_headers):
        """Un nombre limpio no se bloquea (puede dar 404 si no existe)."""
        r = await api_client.get("/api/data/ventas_comes.json", headers=admin_headers)
        assert r.status_code in (200, 404)

    async def test_non_json_blocked(self, api_client, admin_headers):
        r = await api_client.get("/api/data/test.xlsx", headers=admin_headers)
        assert r.status_code == 400


# ── Autenticación API key ────────────────────────────────────────────────────

@pytest.mark.unit
class TestAPIAuth:
    """S3: Sin API key válida, los endpoints protegidos rechazan."""

    async def test_no_auth_header_rejected(self, api_client):
        r = await api_client.get("/api/status")
        assert r.status_code in (401, 403, 500)

    async def test_bad_key_rejected(self, api_client, bad_headers):
        r = await api_client.get("/api/status", headers=bad_headers)
        assert r.status_code == 401

    async def test_admin_key_accepted(self, api_client, admin_headers):
        r = await api_client.get("/api/status", headers=admin_headers)
        assert r.status_code == 200

    async def test_readonly_key_accepted_for_get(self, api_client, readonly_headers):
        r = await api_client.get("/api/status", headers=readonly_headers)
        assert r.status_code == 200

    async def test_health_is_public(self, api_client):
        r = await api_client.get("/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"


# ── RBAC ─────────────────────────────────────────────────────────────────────

@pytest.mark.unit
class TestRBAC:
    """S8: Endpoints de escritura solo aceptan admin key."""

    async def test_readonly_cannot_run_scripts(self, api_client, readonly_headers):
        r = await api_client.post(
            "/api/scripts/ventas", headers=readonly_headers,
        )
        assert r.status_code == 403

    async def test_readonly_cannot_create_proveedor(self, api_client, readonly_headers):
        r = await api_client.post(
            "/api/maestro",
            headers=readonly_headers,
            json={"PROVEEDOR": "TEST"},
        )
        assert r.status_code == 403

    async def test_readonly_cannot_update_proveedor(self, api_client, readonly_headers):
        r = await api_client.put(
            "/api/maestro/TEST",
            headers=readonly_headers,
            json={"CIF": "B00000000"},
        )
        assert r.status_code == 403

    async def test_admin_can_read(self, api_client, admin_headers):
        r = await api_client.get("/api/scripts", headers=admin_headers)
        assert r.status_code == 200

    async def test_readonly_can_list_maestro(self, api_client, readonly_headers):
        """GET /api/maestro acepta readonly (es lectura)."""
        r = await api_client.get("/api/maestro", headers=readonly_headers)
        # Puede dar 500 si MAESTRO no existe en test, pero NO 403
        assert r.status_code != 403


# ── Validación de uploads ────────────────────────────────────────────────────

@pytest.mark.unit
class TestUploadValidation:
    """S5: Uploads validados por tamaño, extensión y magic bytes."""

    async def test_empty_file_rejected(self, api_client, admin_headers):
        from httpx import AsyncClient
        r = await api_client.post(
            "/api/upload/n43",
            headers=admin_headers,
            files={"file": ("test.xlsx", b"", "application/octet-stream")},
        )
        assert r.status_code == 400

    async def test_bad_extension_rejected(self, api_client, admin_headers):
        r = await api_client.post(
            "/api/upload/n43",
            headers=admin_headers,
            files={"file": ("malware.exe", b"MZmalicious", "application/octet-stream")},
        )
        assert r.status_code == 400

    async def test_xlsx_bad_magic_rejected(self, api_client, admin_headers):
        """XLSX que no empieza con PK (ZIP magic) es rechazado."""
        r = await api_client.post(
            "/api/upload/n43",
            headers=admin_headers,
            files={"file": ("test.xlsx", b"NOT_A_ZIP_FILE_CONTENT", "application/octet-stream")},
        )
        assert r.status_code == 400

    async def test_valid_xlsx_accepted(self, api_client, admin_headers):
        """XLSX con magic bytes PK es aceptado."""
        # Mínimo ZIP header válido
        xlsx_header = b"PK\x03\x04" + b"\x00" * 100
        r = await api_client.post(
            "/api/upload/n43",
            headers=admin_headers,
            files={"file": ("test.xlsx", xlsx_header, "application/octet-stream")},
        )
        assert r.status_code == 200

    async def test_readonly_cannot_upload(self, api_client, readonly_headers):
        r = await api_client.post(
            "/api/upload/n43",
            headers=readonly_headers,
            files={"file": ("test.xlsx", b"PK\x03\x04" + b"\x00" * 10, "application/octet-stream")},
        )
        assert r.status_code == 403


# ── Validación argumento archivo en scripts ──────────────────────────────────

@pytest.mark.unit
class TestScriptArgValidation:
    """S4: El argumento archivo en /api/scripts rechaza paths maliciosos."""

    async def test_dot_dot_in_archivo_rejected(self, api_client, admin_headers):
        r = await api_client.post(
            "/api/scripts/cuadre?archivo=../../etc/passwd",
            headers=admin_headers,
        )
        assert r.status_code == 400

    async def test_arbitrary_path_rejected(self, api_client, admin_headers):
        r = await api_client.post(
            "/api/scripts/cuadre?archivo=C:/Windows/System32/config/SAM",
            headers=admin_headers,
        )
        assert r.status_code == 400
