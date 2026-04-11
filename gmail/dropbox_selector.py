"""
dropbox_selector.py — Selecciona automáticamente LocalDropboxClient o DropboxAPIClient
según el entorno (Windows local vs VPS Linux).
"""
import os
import platform
import logging

logger = logging.getLogger(__name__)


def crear_cliente_dropbox(config):
    """
    Crea el cliente Dropbox apropiado según el entorno.

    En Windows (PC Jaime): usa LocalDropboxClient (carpeta local)
    En Linux (VPS): usa DropboxAPIClient (API REST)

    Args:
        config: objeto Config con DROPBOX_BASE, y opcionalmente DROPBOX_TOKEN, DROPBOX_API_BASE

    Returns:
        Cliente Dropbox (LocalDropboxClient o DropboxAPIClient) o None si no hay config
    """
    if platform.system() == 'Windows' and os.path.exists(config.DROPBOX_BASE):
        # PC local — carpeta Dropbox sincronizada
        from gmail.gmail import LocalDropboxClient
        logger.info("Usando Dropbox Local (carpeta sincronizada)")
        return LocalDropboxClient(config.DROPBOX_BASE)

    # VPS o entorno sin carpeta local — API con refresh token
    refresh_token = getattr(config, 'DROPBOX_REFRESH_TOKEN', '') or os.environ.get('DROPBOX_REFRESH_TOKEN', '')
    app_key = getattr(config, 'DROPBOX_APP_KEY', '') or os.environ.get('DROPBOX_APP_KEY', '')
    app_secret = getattr(config, 'DROPBOX_APP_SECRET', '') or os.environ.get('DROPBOX_APP_SECRET', '')
    dropbox_api_base = getattr(config, 'DROPBOX_API_BASE', '') or os.environ.get(
        'DROPBOX_API_BASE', '/File inviati/TASCA BAREA S.L.L/CONTABILIDAD'
    )

    if refresh_token and app_key and app_secret:
        from dropbox_api import DropboxAPIClient
        logger.info("Usando Dropbox API (refresh token)")
        return DropboxAPIClient(refresh_token, dropbox_api_base, app_key, app_secret)

    # Fallback: access token directo (legacy)
    dropbox_token = getattr(config, 'DROPBOX_TOKEN', '') or os.environ.get('DROPBOX_TOKEN', '')
    if dropbox_token:
        from dropbox_api import DropboxAPIClient
        logger.info("Usando Dropbox API (access token directo)")
        return DropboxAPIClient(dropbox_token, dropbox_api_base)

    logger.warning("Dropbox no disponible (ni carpeta local ni token API)")
    return None
