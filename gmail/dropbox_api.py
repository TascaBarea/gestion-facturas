"""
dropbox_api.py — Cliente Dropbox vía API para el VPS.
Reemplaza LocalDropboxClient cuando no hay carpeta local de Dropbox.
Misma interfaz: subir_archivo(contenido, nombre, fecha_factura, fecha_ejecucion) → (ruta, ya_existia)
"""
import os
import hashlib
import logging
from datetime import datetime
from typing import Tuple

logger = logging.getLogger(__name__)

try:
    import dropbox
    from dropbox.exceptions import ApiError
    from dropbox.files import WriteMode
    DROPBOX_DISPONIBLE = True
except ImportError:
    DROPBOX_DISPONIBLE = False


def _obtener_trimestre(fecha: datetime) -> str:
    """Devuelve el trimestre en formato XTyy (ej: 1T26)"""
    trimestre = (fecha.month - 1) // 3 + 1
    año = fecha.year % 100
    return f"{trimestre}T{año:02d}"


def _es_atrasada(fecha_factura: datetime, fecha_ejecucion: datetime) -> bool:
    """Compara trimestre factura vs ejecución (legacy)."""
    return _obtener_trimestre(fecha_factura) != _obtener_trimestre(fecha_ejecucion)


# Constantes ventana de gracia (mismas que en gmail.py)
_GRACIA_HASTA_DIA = 11
_PENDIENTE_HASTA_DIA = 20
_MESES_INICIO_TRIMESTRE = {1, 4, 7, 10}


def _determinar_destino(fecha_factura: datetime, fecha_proceso: datetime) -> str:
    """Versión local de determinar_destino_factura (evita import circular)."""
    trim_fac = (fecha_factura.month - 1) // 3 + 1
    year_fac = fecha_factura.year
    trim_hoy = (fecha_proceso.month - 1) // 3 + 1
    year_hoy = fecha_proceso.year

    if trim_fac == trim_hoy and year_fac == year_hoy:
        return 'NORMAL'

    # Trimestre inmediatamente anterior
    es_anterior = (trim_hoy == 1 and trim_fac == 4 and year_fac == year_hoy - 1) or \
                  (trim_hoy > 1 and trim_fac == trim_hoy - 1 and year_fac == year_hoy)

    if es_anterior and fecha_proceso.month in _MESES_INICIO_TRIMESTRE:
        dia = fecha_proceso.day
        if dia <= _GRACIA_HASTA_DIA:
            return 'GRACIA'
        elif dia <= _PENDIENTE_HASTA_DIA:
            return 'PENDIENTE_UBICACION'

    if trim_fac != trim_hoy or year_fac != year_hoy:
        return 'ATRASADA'
    return 'NORMAL'


class DropboxAPIClient:
    """
    Cliente Dropbox vía API REST. Interfaz compatible con LocalDropboxClient.
    Usa refresh token (no expira) para obtener access tokens automáticamente.
    """

    def __init__(self, refresh_token: str, base_path: str,
                 app_key: str = "", app_secret: str = ""):
        """
        Args:
            refresh_token: Refresh token OAuth2 (no expira)
            base_path: Ruta base en Dropbox (ej: /File inviati/TASCA BAREA S.L.L/CONTABILIDAD)
            app_key: App key de la aplicación Dropbox
            app_secret: App secret de la aplicación Dropbox
        """
        if not DROPBOX_DISPONIBLE:
            raise ImportError("pip install dropbox")

        if app_key and app_secret:
            # Modo refresh token (recomendado, no expira)
            self.dbx = dropbox.Dropbox(
                oauth2_refresh_token=refresh_token,
                app_key=app_key,
                app_secret=app_secret,
            )
        else:
            # Fallback: access token directo (expira en 4h)
            self.dbx = dropbox.Dropbox(refresh_token)

        self.base_path = base_path.rstrip('/')
        # Verificar conexión
        try:
            self.dbx.users_get_current_account()
            logger.info("Dropbox API conectado ✓")
        except Exception as e:
            raise ConnectionError(f"Error conectando a Dropbox API: {e}")

    def subir_archivo(self, contenido: bytes, nombre_archivo: str, fecha_factura: datetime,
                      fecha_ejecucion: datetime, destino: str = None) -> Tuple[str, bool]:
        """
        Sube archivo a Dropbox vía API con deduplicación.
        Misma interfaz que LocalDropboxClient.subir_archivo().
        v1.18: Ventana de gracia — destino controla carpeta.

        Returns:
            Tuple (ruta_dropbox, ya_existia)
        """
        # v1.18: Usar destino si se proporciona
        if destino is None:
            destino = _determinar_destino(fecha_factura, fecha_ejecucion)

        if destino == 'GRACIA':
            carpeta_trimestre = self.obtener_ruta_trimestre(fecha_factura)
            ruta_remota = f"{self.base_path}/{carpeta_trimestre}/{nombre_archivo}"
        elif destino == 'ATRASADA':
            carpeta_trimestre = self.obtener_ruta_trimestre(fecha_ejecucion)
            ruta_remota = f"{self.base_path}/{carpeta_trimestre}/ATRASADAS/{nombre_archivo}"
        else:  # NORMAL
            carpeta_trimestre = self.obtener_ruta_trimestre(fecha_ejecucion)
            ruta_remota = f"{self.base_path}/{carpeta_trimestre}/{nombre_archivo}"

        # Dedup: buscar contenido idéntico en la carpeta destino
        carpeta_remota = '/'.join(ruta_remota.rsplit('/', 1)[:-1])
        hash_nuevo = hashlib.sha256(contenido).hexdigest()
        tamaño_nuevo = len(contenido)

        try:
            resultado = self.dbx.files_list_folder(carpeta_remota)
            for entry in resultado.entries:
                if hasattr(entry, 'size') and entry.size == tamaño_nuevo:
                    # Comparar descargando si tamaño coincide
                    _, response = self.dbx.files_download(entry.path_display)
                    contenido_existente = response.content
                    if hashlib.sha256(contenido_existente).hexdigest() == hash_nuevo:
                        logger.info(f"  ↳ Ya existe en Dropbox (contenido idéntico): {entry.path_display}")
                        return entry.path_display, True
        except ApiError as e:
            if e.error.is_path() and e.error.get_path().is_not_found():
                pass  # Carpeta no existe, se creará al subir
            else:
                logger.warning(f"  ↳ Error listando Dropbox: {e}")

        # Subir
        try:
            meta = self.dbx.files_upload(contenido, ruta_remota, mode=WriteMode.add, autorename=True)
            logger.info(f"  ↳ Subido a Dropbox API: {meta.path_display}")
            return meta.path_display, False
        except ApiError as e:
            logger.error(f"  ↳ Error subiendo a Dropbox: {e}")
            raise

    def subir_archivo_a_ruta(self, contenido: bytes, ruta_relativa: str) -> str:
        """v1.22: sube `contenido` a `ruta_relativa` dentro de base_path remoto.

        La ruta es relativa (la base la añade el cliente). Sobrescribe si existe
        — semántica "última versión gana", pensada para Excels que crecen cada
        run (no facturas donde sí queremos dedup).

        Returns:
            Ruta remota completa donde quedó el archivo.
        """
        rel = ruta_relativa.lstrip('/')
        ruta_remota = f"{self.base_path}/{rel}"
        meta = self.dbx.files_upload(contenido, ruta_remota, mode=WriteMode.overwrite)
        logger.info("  ↳ Subido a Dropbox API (overwrite): %s", meta.path_display)
        return meta.path_display

    def obtener_ruta_trimestre(self, fecha: datetime) -> str:
        """Genera ruta relativa: FACTURAS 2026/FACTURAS RECIBIDAS/2 TRIMESTRE 2026"""
        año = fecha.year
        trimestre = (fecha.month - 1) // 3 + 1
        nombre_trimestre = {1: "1 TRIMESTRE", 2: "2 TRIMESTRE", 3: "3 TRIMESTRE", 4: "4 TRIMESTRE"}
        return f"FACTURAS {año}/FACTURAS RECIBIDAS/{nombre_trimestre[trimestre]} {año}"

    def archivo_existe(self, ruta_relativa: str) -> bool:
        """Verifica si un archivo existe en Dropbox"""
        ruta_completa = f"{self.base_path}/{ruta_relativa.lstrip('/')}"
        try:
            self.dbx.files_get_metadata(ruta_completa)
            return True
        except ApiError:
            return False
