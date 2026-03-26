"""
nucleo/logging_config.py — Configuración centralizada de logging.

Uso:
    from nucleo.logging_config import setup_logging
    log = setup_logging("gmail", log_subdir="logs_gmail")

Cada módulo obtiene un logger con:
- FileHandler rotativo diario (DEBUG) en outputs/<log_subdir>/
- StreamHandler consola (INFO)
- Formato consistente: HH:MM:SS | LEVEL    | mensaje
"""

import os
import logging
from datetime import datetime
from logging.handlers import RotatingFileHandler

# Raíz del proyecto (gestion-facturas/)
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_OUTPUTS_DIR = os.path.join(_PROJECT_ROOT, "outputs")

# Formato unificado
_LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(message)s"
_LOG_FORMAT_CONSOLE = "%(asctime)s | %(levelname)-8s | %(message)s"
_DATE_FORMAT = "%H:%M:%S"

# Rotación: 5 MB por archivo, 5 backups
_MAX_BYTES = 5 * 1024 * 1024
_BACKUP_COUNT = 5


def setup_logging(
    nombre: str,
    *,
    log_subdir: str = "",
    nivel_archivo: int = logging.DEBUG,
    nivel_consola: int = logging.INFO,
    sufijo: str = "",
    consola_simple: bool = False,
    force: bool = False,
) -> logging.Logger:
    """Configura y devuelve un logger con FileHandler + StreamHandler.

    Args:
        nombre: Nombre del logger (ej. "gmail", "ventas", "cuadre").
        log_subdir: Subdirectorio dentro de outputs/ (ej. "logs_gmail").
                    Si vacío, usa "logs_{nombre}".
        nivel_archivo: Nivel mínimo para el fichero (default DEBUG).
        nivel_consola: Nivel mínimo para consola (default INFO).
        sufijo: Sufijo para el nombre del fichero (ej. "_test").
        consola_simple: Si True, formato consola solo muestra el mensaje.

    Returns:
        Logger configurado.
    """
    logger = logging.getLogger(nombre)

    # Evitar duplicar handlers si se llama varias veces
    if logger.handlers and not force:
        return logger
    if force:
        logger.handlers.clear()

    logger.setLevel(logging.DEBUG)

    # Directorio de logs
    if not log_subdir:
        log_subdir = f"logs_{nombre}"
    log_dir = os.path.join(_OUTPUTS_DIR, log_subdir)
    os.makedirs(log_dir, exist_ok=True)

    # Nombre del fichero: YYYY-MM-DD{sufijo}.log
    fecha = datetime.now().strftime("%Y-%m-%d")
    log_file = os.path.join(log_dir, f"{fecha}{sufijo}.log")

    # Formatter
    fmt_file = logging.Formatter(_LOG_FORMAT, datefmt=_DATE_FORMAT)
    if consola_simple:
        fmt_console = logging.Formatter("%(message)s")
    else:
        fmt_console = logging.Formatter(_LOG_FORMAT_CONSOLE, datefmt=_DATE_FORMAT)

    # FileHandler con rotación
    fh = RotatingFileHandler(
        log_file, maxBytes=_MAX_BYTES, backupCount=_BACKUP_COUNT,
        encoding="utf-8",
    )
    fh.setLevel(nivel_archivo)
    fh.setFormatter(fmt_file)
    logger.addHandler(fh)

    # StreamHandler (consola)
    ch = logging.StreamHandler()
    ch.setLevel(nivel_consola)
    ch.setFormatter(fmt_console)
    logger.addHandler(ch)

    return logger


def get_logger(nombre: str) -> logging.Logger:
    """Obtiene un logger existente (sin configurar handlers).

    Para módulos que no necesitan su propio FileHandler
    (ej. api/maestro.py usa el logger de la API).
    """
    return logging.getLogger(nombre)
