"""
nucleo/sync_drive.py — Sincronización de archivos a Google Drive.

Estrategia B: copiar resultados post-ejecución a carpeta compartida.
Requiere scope drive en el token OAuth2 (drive.file no basta: no ve
carpetas creadas manualmente).

Uso:
    from nucleo.sync_drive import sync_archivos
    sync_archivos(archivos)                               # raíz
    sync_archivos(archivos, carpeta="Facturas")           # 1 nivel
    sync_archivos(archivos, carpeta="Ventas/Año en curso")# anidado (str)
    sync_archivos(archivos, carpeta=["Ventas", "Año en curso"])  # anidado (list)
"""

import io
import logging
import os
import sys

from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload

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


def _normalizar_carpeta(carpeta):
    """Normaliza `carpeta` (None, str, list/tuple) a lista de segmentos.

    Reglas:
    - None o "" → [] (raíz)
    - str con "/" → split y strip
    - str sin "/" → [str.strip()]
    - list/tuple → strip cada segmento

    Rechaza segmentos vacíos tras strip (ej. "A//B", "/A", "A/").
    """
    if carpeta is None:
        return []
    if isinstance(carpeta, (list, tuple)):
        segmentos = [str(s).strip() for s in carpeta]
    elif isinstance(carpeta, str):
        if carpeta.strip() == "":
            return []
        segmentos = [s.strip() for s in carpeta.split("/")]
    else:
        raise TypeError(
            f"`carpeta` debe ser None, str o lista de str; recibido {type(carpeta).__name__}"
        )

    for s in segmentos:
        if not s:
            raise ValueError(
                f"Segmento vacío en path de carpeta: {carpeta!r}. "
                "No se permiten '//' ni slashes al inicio/final."
            )
    return segmentos


def _resolver_o_crear_carpeta_anidada(service, segmentos, parent_id):
    """Recorre la lista de segmentos desde parent_id, creando los que falten.

    Idempotente. Devuelve el ID del último segmento. Si la lista está vacía,
    devuelve parent_id sin tocar nada.
    """
    current = parent_id
    for seg in segmentos:
        current = _obtener_carpeta(service, seg, current)
    return current


def _resolver_carpeta_anidada(service, segmentos, parent_id):
    """Recorre segmentos desde parent_id SIN CREAR. Devuelve ID o None.

    Pensado para lectura: si cualquier segmento falta, devuelve None.
    """
    current = parent_id
    for seg in segmentos:
        found = _buscar_carpeta(service, seg, current)
        if not found:
            return None
        current = found
    return current


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
    """Sube lista de archivos a Drive (carpeta raíz o subcarpeta anidada).

    Args:
        archivos: lista de paths locales (ignora los que no existen)
        carpeta: None | str | list[str]. Acepta "Ventas/Año en curso" o
                 ["Ventas", "Año en curso"]. Los segmentos inexistentes se crean.

    Returns:
        dict con {nombre_archivo: file_id} de los subidos
    """
    segmentos = _normalizar_carpeta(carpeta)

    existentes = [a for a in archivos if os.path.exists(a)]
    if not existentes:
        log.warning("sync_drive: ningún archivo para subir")
        return {}

    try:
        service = _get_service()
    except Exception as e:
        log.error("sync_drive: error de autenticación: %s", e)
        return {}

    raiz_id = _obtener_carpeta(service, CARPETA_RAIZ)
    destino_id = _resolver_o_crear_carpeta_anidada(service, segmentos, raiz_id)

    resultados = {}
    for path in existentes:
        try:
            file_id = _subir_o_actualizar(service, path, destino_id)
            resultados[os.path.basename(path)] = file_id
        except Exception as e:
            log.error("sync_drive: error subiendo %s: %s", os.path.basename(path), e)

    sub_legible = "/".join(segmentos)
    log.info(
        "sync_drive: %d/%d archivos sincronizados a Drive/%s%s",
        len(resultados), len(existentes),
        CARPETA_RAIZ, f"/{sub_legible}" if sub_legible else ""
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


def descargar_archivo(nombre, carpeta, destino_local):
    """Descarga un archivo de Drive a una ruta local.

    Args:
        nombre: nombre exacto del archivo en Drive (p.ej. "MAESTRO_PROVEEDORES.xlsx").
        carpeta: None | str | list[str]. Ruta en Drive donde vive el archivo.
                 Misma semántica que sync_archivos/listar_carpeta.
        destino_local: path local donde escribir los bytes descargados.
                       El directorio padre se crea si no existe.

    Returns:
        True si descargado, False si no encontrado en Drive.

    Raises:
        RuntimeError en fallo de autenticación o red.
    """
    segmentos = _normalizar_carpeta(carpeta)

    service = _get_service()
    raiz_id = _buscar_carpeta(service, CARPETA_RAIZ)
    if not raiz_id:
        log.warning("descargar_archivo: raíz %s no existe en Drive", CARPETA_RAIZ)
        return False

    target_id = _resolver_carpeta_anidada(service, segmentos, raiz_id)
    if target_id is None:
        log.warning(
            "descargar_archivo: path no existe: %s/%s",
            CARPETA_RAIZ, "/".join(segmentos),
        )
        return False

    file_id = _buscar_archivo(service, nombre, target_id)
    if not file_id:
        log.warning("descargar_archivo: %s no encontrado en %s", nombre, "/".join(segmentos))
        return False

    os.makedirs(os.path.dirname(os.path.abspath(destino_local)), exist_ok=True)

    request = service.files().get_media(fileId=file_id)
    buf = io.BytesIO()
    downloader = MediaIoBaseDownload(buf, request)
    done = False
    while not done:
        _status, done = downloader.next_chunk()

    with open(destino_local, "wb") as f:
        f.write(buf.getvalue())

    log.info("Descargado de Drive: %s → %s", nombre, destino_local)
    return True


def listar_carpeta(carpeta=None):
    """Lista archivos en una carpeta anidada de Drive (para Streamlit).

    Args:
        carpeta: None | str | list[str]. "Ventas/Año en curso" o
                 ["Ventas", "Año en curso"] son equivalentes.

    NO crea carpetas. Si cualquier segmento intermedio no existe,
    devuelve [] y registra un warning.

    Returns:
        lista de dicts con {name, id, modifiedTime, size, webViewLink, mimeType}
    """
    segmentos = _normalizar_carpeta(carpeta)

    service = _get_service()
    raiz_id = _buscar_carpeta(service, CARPETA_RAIZ)
    if not raiz_id:
        return []

    target_id = _resolver_carpeta_anidada(service, segmentos, raiz_id)
    if target_id is None:
        log.warning(
            "listar_carpeta: path no existe en Drive: %s/%s",
            CARPETA_RAIZ, "/".join(segmentos),
        )
        return []

    resultado = service.files().list(
        q=f"'{target_id}' in parents and trashed = false",
        spaces="drive",
        fields="files(id, name, modifiedTime, size, webViewLink, mimeType)",
        orderBy="modifiedTime desc",
        pageSize=50,
    ).execute()

    return resultado.get("files", [])
