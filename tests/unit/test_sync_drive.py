"""
tests/unit/test_sync_drive.py — tests para soporte de paths anidados en Drive.

Todos los tests usan mocks del servicio de Drive: NUNCA llaman a la API real.
"""
import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest

from nucleo import sync_drive as sd


# ── Helpers ──────────────────────────────────────────────────────────────────

def _mk_service(existing_folders=None):
    """Construye un mock de service con comportamiento de búsqueda/creación.

    existing_folders: dict {(nombre, parent_id_o_None): folder_id}
        Estos IDs se devuelven al buscar; todo lo demás es "no existe".
    """
    existing = dict(existing_folders or {})
    created = {}
    id_counter = [0]

    def next_id(nombre):
        id_counter[0] += 1
        return f"mock-id-{id_counter[0]}-{nombre}"

    files_mock = MagicMock()

    def list_side_effect(**kwargs):
        q = kwargs.get("q", "")
        # Extraer nombre y parent del q (formato conocido de sync_drive)
        import re
        m_name = re.search(r"name = '([^']+)'", q)
        m_parent = re.search(r"'([^']+)' in parents", q)
        m_folder = "mimeType = 'application/vnd.google-apps.folder'" in q
        m_not_folder = "mimeType != 'application/vnd.google-apps.folder'" in q

        exec_mock = MagicMock()

        if m_name and m_folder:
            # Búsqueda de carpeta por nombre
            nombre = m_name.group(1)
            parent = m_parent.group(1) if m_parent else None
            key = (nombre, parent)
            if key in existing:
                exec_mock.execute.return_value = {"files": [{"id": existing[key], "name": nombre}]}
            else:
                exec_mock.execute.return_value = {"files": []}
        elif m_name and m_not_folder:
            # Búsqueda de archivo (no carpeta) por nombre
            exec_mock.execute.return_value = {"files": []}
        elif m_parent and not m_name:
            # Listado de hijos (para listar_carpeta)
            parent = m_parent.group(1)
            hijos = [
                {"id": fid, "name": n, "mimeType": "application/octet-stream",
                 "modifiedTime": "2026-04-22T10:00:00Z", "size": "100"}
                for (n, p), fid in existing.items() if p == parent and fid.startswith("file-")
            ]
            exec_mock.execute.return_value = {"files": hijos}
        else:
            exec_mock.execute.return_value = {"files": []}
        return exec_mock

    def create_side_effect(body=None, **kwargs):
        # Crea carpeta o archivo
        nombre = body["name"]
        parents = body.get("parents", [None])
        parent_id = parents[0] if parents else None
        is_folder = body.get("mimeType") == "application/vnd.google-apps.folder"

        new_id = next_id(nombre) if is_folder else f"file-{next_id(nombre)}"
        existing[(nombre, parent_id)] = new_id
        created[new_id] = {"name": nombre, "parent": parent_id, "is_folder": is_folder}

        exec_mock = MagicMock()
        exec_mock.execute.return_value = {"id": new_id, "name": nombre}
        return exec_mock

    def update_side_effect(**kwargs):
        exec_mock = MagicMock()
        exec_mock.execute.return_value = {"id": kwargs.get("fileId")}
        return exec_mock

    files_mock.list.side_effect = list_side_effect
    files_mock.create.side_effect = create_side_effect
    files_mock.update.side_effect = update_side_effect

    service = MagicMock()
    service.files.return_value = files_mock
    service._existing = existing
    service._created = created
    return service


@pytest.fixture(autouse=True)
def _patch_media_upload():
    """Evita que MediaFileUpload abra file handles (bloquearía borrado en Windows)."""
    with patch.object(sd, "MediaFileUpload", return_value=MagicMock()):
        yield


@pytest.fixture()
def tmp_file(tmp_path):
    """Archivo dummy para subir (lo gestiona pytest, sin handles persistentes)."""
    path = tmp_path / "dummy.txt"
    path.write_text("contenido de prueba", encoding="utf-8")
    return str(path)


# ── Tests de normalización ───────────────────────────────────────────────────

def test_normalizar_formas_equivalentes():
    """str simple, str anidado y list producen resultados consistentes."""
    assert sd._normalizar_carpeta(None) == []
    assert sd._normalizar_carpeta("") == []
    assert sd._normalizar_carpeta("Ventas") == ["Ventas"]
    assert sd._normalizar_carpeta("Ventas/Año en curso") == ["Ventas", "Año en curso"]
    assert sd._normalizar_carpeta(["Ventas", "Año en curso"]) == ["Ventas", "Año en curso"]
    assert sd._normalizar_carpeta(" Ventas / Año en curso ") == ["Ventas", "Año en curso"]


# ── a) test_carpeta_str_simple ───────────────────────────────────────────────

def test_carpeta_str_simple(tmp_file):
    """sync_archivos(..., carpeta='Ventas') crea raíz + Ventas y sube 1 archivo."""
    service = _mk_service()
    with patch.object(sd, "_get_service", return_value=service):
        res = sd.sync_archivos([tmp_file], carpeta="Ventas")

    assert len(res) == 1
    assert os.path.basename(tmp_file) in res
    # Raíz y "Ventas" deben haberse creado (parent=None y parent=raíz respectivamente)
    assert (sd.CARPETA_RAIZ, None) in service._existing
    raiz_id = service._existing[(sd.CARPETA_RAIZ, None)]
    assert ("Ventas", raiz_id) in service._existing


# ── b) test_carpeta_str_anidada ──────────────────────────────────────────────

def test_carpeta_str_anidada(tmp_file):
    """'Ventas/Año en curso' crea ambos niveles y el archivo cuelga del último."""
    service = _mk_service()
    with patch.object(sd, "_get_service", return_value=service):
        res = sd.sync_archivos([tmp_file], carpeta="Ventas/Año en curso")

    assert len(res) == 1
    raiz_id = service._existing[(sd.CARPETA_RAIZ, None)]
    ventas_id = service._existing[("Ventas", raiz_id)]
    anio_id = service._existing[("Año en curso", ventas_id)]
    # El archivo creado tiene como parent la carpeta "Año en curso"
    creados_archivos = [
        info for info in service._created.values() if not info["is_folder"]
    ]
    assert len(creados_archivos) == 1
    assert creados_archivos[0]["parent"] == anio_id


# ── c) test_carpeta_lista ────────────────────────────────────────────────────

def test_carpeta_lista(tmp_file):
    """La forma lista produce el mismo árbol que la forma string."""
    service = _mk_service()
    with patch.object(sd, "_get_service", return_value=service):
        res = sd.sync_archivos([tmp_file], carpeta=["Compras", "Histórico"])

    assert len(res) == 1
    raiz_id = service._existing[(sd.CARPETA_RAIZ, None)]
    compras_id = service._existing[("Compras", raiz_id)]
    assert ("Histórico", compras_id) in service._existing


# ── d) test_idempotencia ─────────────────────────────────────────────────────

def test_idempotencia(tmp_file):
    """Dos llamadas consecutivas no crean carpetas duplicadas."""
    service = _mk_service()
    with patch.object(sd, "_get_service", return_value=service):
        sd.sync_archivos([tmp_file], carpeta=["Ventas", "Año en curso"])
        folders_tras_1 = {
            k for k, v in service._existing.items()
            if not v.startswith("file-")
        }
        sd.sync_archivos([tmp_file], carpeta=["Ventas", "Año en curso"])
        folders_tras_2 = {
            k for k, v in service._existing.items()
            if not v.startswith("file-")
        }

    # Las mismas 3 carpetas (raíz + Ventas + Año en curso), ningún duplicado
    assert folders_tras_1 == folders_tras_2
    assert len(folders_tras_2) == 3


# ── e) test_segmento_vacio_rechazado ─────────────────────────────────────────

def test_segmento_vacio_rechazado():
    """Paths con '//', '/A', 'A/' o segmentos en blanco lanzan ValueError."""
    for bad in ["Ventas//Año", "/Ventas", "Ventas/", "A/ /B", ["A", "", "B"], ["A", "  "]]:
        with pytest.raises(ValueError):
            sd._normalizar_carpeta(bad)


def test_tipo_invalido_rechazado():
    """Tipos no soportados lanzan TypeError."""
    with pytest.raises(TypeError):
        sd._normalizar_carpeta(123)


# ── f) test_listar_carpeta_path_inexistente_no_crea ──────────────────────────

def test_listar_carpeta_path_inexistente_no_crea(caplog):
    """listar_carpeta() con path inexistente devuelve [] y NO crea carpetas."""
    # Solo existe la raíz; el resto del path no.
    service = _mk_service(existing_folders={(sd.CARPETA_RAIZ, None): "raiz-id"})
    antes = dict(service._existing)

    with patch.object(sd, "_get_service", return_value=service):
        with caplog.at_level("WARNING"):
            resultado = sd.listar_carpeta(["Ventas", "Año en curso"])

    assert resultado == []
    # No se creó ninguna carpeta nueva
    assert service._existing == antes
    # Warning logueado
    assert any("no existe en Drive" in r.message for r in caplog.records)


def test_listar_carpeta_path_existente(tmp_file):
    """Si el path existe, listar_carpeta devuelve los hijos."""
    # Pre-poblar existing con la cadena y un archivo dentro
    service = _mk_service(existing_folders={
        (sd.CARPETA_RAIZ, None): "raiz-id",
        ("Ventas", "raiz-id"): "ventas-id",
        ("Año en curso", "ventas-id"): "anio-id",
        ("dummy.xlsx", "anio-id"): "file-dummy-1",
    })

    with patch.object(sd, "_get_service", return_value=service):
        archivos = sd.listar_carpeta("Ventas/Año en curso")

    assert len(archivos) == 1
    assert archivos[0]["name"] == "dummy.xlsx"
