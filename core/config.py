"""
core/config.py — Configuración centralizada del proyecto.

FUENTE ÚNICA de rutas. Todos los módulos deben importar de aquí.
En Windows (Jaime): usa los fallback hardcoded.
En VPS (Contabo): lee de variables de entorno o .env, fallback a /opt/
"""
import os
import platform
from pathlib import Path
from dataclasses import dataclass, field


VERSION = "5.17"

_ES_WINDOWS = platform.system() == "Windows"

# Fallbacks por OS (solo se usan si no hay env var)
_DEFAULT_BASE = r"C:\_ARCHIVOS\TRABAJO\Facturas\gestion-facturas" if _ES_WINDOWS else "/opt/gestion-facturas"
_DEFAULT_PARSEO = r"C:\_ARCHIVOS\TRABAJO\Facturas\Parseo" if _ES_WINDOWS else "/opt/Parseo"
_DEFAULT_DROPBOX = r"C:\Users\jaime\Dropbox\File inviati\TASCA BAREA S.L.L\CONTABILIDAD" if _ES_WINDOWS else ""


@dataclass
class Config:
    """Configuración del proyecto. Lee de env vars con fallback a rutas locales."""

    base_dir: Path = field(default_factory=lambda: Path(
        os.environ.get("GESTION_FACTURAS_DIR", _DEFAULT_BASE)
    ))

    parseo_dir: Path = field(default_factory=lambda: Path(
        os.environ.get("PARSEO_DIR", _DEFAULT_PARSEO)
    ))

    dropbox_base: Path = field(default_factory=lambda: Path(
        os.environ.get("DROPBOX_BASE", _DEFAULT_DROPBOX)
    ) if os.environ.get("DROPBOX_BASE", _DEFAULT_DROPBOX) else Path())

    @property
    def datos_dir(self) -> Path:
        return self.base_dir / "datos"

    @property
    def outputs_dir(self) -> Path:
        return self.base_dir / "outputs"

    @property
    def maestro_path(self) -> Path:
        return self.datos_dir / "MAESTRO_PROVEEDORES.xlsx"

    @property
    def diccionario_path(self) -> Path:
        return self.datos_dir / "DiccionarioProveedoresCategoria.xlsx"

    @property
    def alias_path(self) -> Path:
        return self.datos_dir / "alias_diccionario.json"

    @property
    def emails_json_path(self) -> Path:
        return self.datos_dir / "emails_procesados.json"

    @property
    def extractores_dir(self) -> Path:
        return self.parseo_dir / "extractores"

    @classmethod
    def from_env(cls) -> "Config":
        """Carga config desde .env si existe, luego construye."""
        env_file = Path(__file__).resolve().parent.parent / ".env"
        if env_file.exists():
            try:
                from dotenv import load_dotenv
                load_dotenv(env_file)
            except ImportError:
                pass  # dotenv no instalado, usar solo env vars del sistema
        return cls()


# Instancia global (singleton)
_config: Config | None = None


def get_config() -> Config:
    """Devuelve la configuración global (lazy singleton)."""
    global _config
    if _config is None:
        _config = Config.from_env()
    return _config
