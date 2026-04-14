"""
nucleo/sync_drive.py — Sincronización de archivos a Google Drive.

Estrategia B: copiar resultados post-ejecución a carpeta compartida.
Requiere scope drive.file en el token OAuth2.

Uso:
    from nucleo.sync_drive import sync_archivos
    sync_archivos(archivos)  # lista de paths locales
    sync_archivos(archivos, carpeta="Facturas")  # subcarpeta
"""

import logging
import os
import sys

from googleapiclient.http import MediaFileUpload

log = logging.getLogger("sync_drive")

# ── Config ────────────────────────────────────────────────────────────────────

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

CARPETA_RAIZ = "Barea - Datos Compartidos"

# Extensión → MIME type para uploads
_MIME_TYPES = {
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".xls": "application/vnd.ms-excel",
    ".pdf": "application/pdf",
    ".html": "text/html",
    ".json": "application/json",
    ".csv": "text/csv",
}


def _get_service():
    """Obtiene servicio Drive autenticado usando auth_manager centralizado."""
    import importlib.util
    _auth_path = os.path.join(_PROJECT_ROOT, "gmail", "auth_manager.py")
    spec = importlib.util.spec_from_file_location("gmail_auth_manager", _auth_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.get_drive_service()


def _buscar_carpeta(service, nombre, parent_id=None):
    """Busca una carpeta por nombre. Devuelve ID o None."""
    q = (
        f"name = '{nombre}' and mimeType = 'application/vnd.google-apps.folder'"
        f" and trashed = false"
    )
    if parent_id:
        q += f" and '{parent_id}' in parents"

    resultado = service.files().list(
        q=q, spaces="drive", fields="files(id, name)", pageSize=1
    ).execute()

    archivos = resultado.get("files", [])
    return archivos[0]["id"] if archivos else None


def _crear_carpeta(service, nombre, parent_id=None):
    """Crea carpeta en Drive. Devuelve ID."""
    metadata = {
        "name": nombre,
        "mimeType": "application/vnd.google-apps.folder",
    }
    if parent_id:
        metadata["parents"] = [parent_id]

    carpeta = service.files().create(body=metadata, fields="id").execute()
    log.info("Carpeta creada en Drive: %s (id: %s)", nombre, carpeta["id"])
    return carpeta["id"]


def _obtener_carpeta(service, nombre, parent_id=None):
    """Busca carpeta, la crea si no existe. Devuelve ID."""
    folder_id = _buscar_carpeta(service, nombre, parent_id)
    if folder_id:
        return folder_id
    return _crear_carpeta(service, nombre, parent_id)


def _buscar_archivo(service, nombre, parent_id):
    """Busca archivo por nombre en carpeta. Devuelve ID o None."""
    q = (
        f"name = '{nombre}' and '{parent_id}' in parents"
        f" and trashed = false"
        f" and mimeType != 'application/vnd.google-apps.folder'"
    )
    resultado = service.files().list(
        q=q, spaces="drive", fields="files(id, name)", pageSize=1
    ).execute()

    archivos = resultado.get("files", [])
    return archivos[0]["id"] if archivos else None


def _mime_type(path):
    """Detecta MIME type por extensión."""
    ext = os.path.splitext(path)[1].lower()
    return _MIME_TYPES.get(ext, "application/octet-stream")


def _subir_o_actualizar(service, path_local, parent_id):
    """Sube archivo nuevo o actualiza si ya existe. Devuelve ID."""
    nombre = os.path.basename(path_local)
    mime = _mime_type(path_local)
    media = MediaFileUpload(path_local, mimetype=mime, resumable=True)

    file_id = _buscar_archivo(service, nombre, parent_id)

    if file_id:
        # Actualizar existente
        resultado = service.files().update(
            fileId=file_id, media_body=media
        ).execute()
        log.info("Actualizado en Drive: %s", nombre)
    else:
        # Crear nuevo
        metadata = {"name": nombre, "parents": [parent_id]}
        resultado = service.files().create(
            body=metadata, media_body=media, fields="id"
        ).execute()
        log.info("Subido a Drive: %s", nombre)

    return resultado.get("id")


# ── API pública ───────────────────────────────────────────────────────────────

def sync_archivos(archivos, carpeta=None):
    """Sube lista de archivos a Drive (carpeta raíz o subcarpeta).

    Args:
        archivos: lista de paths locales (ignora los que no existen)
        carpeta: nombre de subcarpeta dentro de CARPETA_RAIZ (opcional)

    Returns:
        dict con {nombre_archivo: file_id} de los subidos
    """
    # Filtrar archivos que existen
    existentes = [a for a in archivos if os.path.exists(a)]
    if not existentes:
        log.warning("sync_drive: ningún archivo para subir")
        return {}

    try:
        service = _get_service()
    except Exception as e:
        log.error("sync_drive: error de autenticación: %s", e)
        return {}

    # Obtener/crear carpeta raíz
    raiz_id = _obtener_carpeta(service, CARPETA_RAIZ)

    # Subcarpeta si se indica
    destino_id = raiz_id
    if carpeta:
        destino_id = _obtener_carpeta(service, carpeta, raiz_id)

    # Subir cada archivo
    resultados = {}
    for path in existentes:
        try:
            file_id = _subir_o_actualizar(service, path, destino_id)
            resultados[os.path.basename(path)] = file_id
        except Exception as e:
            log.error("sync_drive: error subiendo %s: %s", os.path.basename(path), e)

    log.info(
        "sync_drive: %d/%d archivos sincronizados a Drive/%s%s",
        len(resultados), len(existentes),
        CARPETA_RAIZ, f"/{carpeta}" if carpeta else ""
    )
    return resultados


def sync_datos(base_path=None):
    """
    Sincroniza archivos de datos de referencia con Google Drive.
    Carpeta destino: Barea - Datos Compartidos/Datos
    """
    import platform

    if base_path is None:
        if platform.system() == "Windows":
            base_path = r"C:\_ARCHIVOS\TRABAJO\Facturas\gestion-facturas"
        else:
            base_path = "/opt/gestion-facturas"

    archivos = []
    datos_dir = os.path.join(base_path, "datos")

    # Archivos de datos a sincronizar
    nombres = [
        "Movimientos_Cuenta_26.xlsx",
        "MAESTRO_PROVEEDORES.xlsx",
        "DiccionarioProveedoresCategoria.xlsx",
    ]

    # Buscar archivo de artículos (nombre puede variar)
    if os.path.isdir(datos_dir):
        for f in os.listdir(datos_dir):
            if f.lower().startswith("articulos") and f.endswith(".xlsx"):
                nombres.append(f)
                break

    for nombre in nombres:
        ruta = os.path.join(datos_dir, nombre)
        if os.path.exists(ruta):
            archivos.append(ruta)

    if archivos:
        sync_archivos(archivos, carpeta="Datos")

    return archivos


def listar_carpeta(carpeta=None):
    """Lista archivos en la carpeta compartida (para Streamlit).

    Returns:
        lista de dicts con {name, id, modifiedTime, size, webViewLink}
    """
    service = _get_service()
    raiz_id = _buscar_carpeta(service, CARPETA_RAIZ)
    if not raiz_id:
        return []

    target_id = raiz_id
    if carpeta:
        target_id = _buscar_carpeta(service, carpeta, raiz_id)
        if not target_id:
            return []

    resultado = service.files().list(
        q=f"'{target_id}' in parents and trashed = false",
        spaces="drive",
        fields="files(id, name, modifiedTime, size, webViewLink, mimeType)",
        orderBy="modifiedTime desc",
        pageSize=50,
    ).execute()

    return resultado.get("files", [])
