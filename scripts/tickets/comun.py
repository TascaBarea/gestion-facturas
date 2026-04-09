"""
comun.py — Lógica compartida para el módulo de tickets de proveedores.

Funciones reutilizables: trimestre, nomenclatura PDF, registro anti-duplicación,
extracción de texto, logging estándar.

Todos los scripts de tickets (bm.py, dia.py, makro.py) importan de aquí.
"""

import json
import logging
import re
from datetime import datetime
from pathlib import Path

# ── Rutas base ───────────────────────────────────────────────────────────────

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent  # gestion-facturas/
DATOS_DIR = PROJECT_ROOT / "datos"
REGISTROS_DIR = DATOS_DIR / "tickets_registros"


# ── Logging ──────────────────────────────────────────────────────────────────

def configurar_logging(nombre: str, verbose: bool = False) -> logging.Logger:
    """Configura y devuelve un logger estándar para el proveedor.

    Args:
        nombre: Nombre del proveedor (ej: "bm", "dia").
        verbose: Si True, nivel DEBUG; si no, INFO.

    Returns:
        Logger configurado.
    """
    nivel = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=nivel,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )
    return logging.getLogger(f"tickets.{nombre}")


# ── Trimestre y nomenclatura ─────────────────────────────────────────────────

def calcular_trimestre(fecha: datetime) -> str:
    """Calcula el código de trimestre: '2T26', '1T25', etc.

    Args:
        fecha: Fecha del ticket.

    Returns:
        String con formato '{trimestre}T{año_2dígitos}'.
    """
    trimestre = (fecha.month - 1) // 3 + 1
    return f"{trimestre}T{fecha.strftime('%y')}"


def obtener_carpeta_trimestre(fecha: datetime) -> Path:
    """Crea y devuelve la carpeta del trimestre en gestion-facturas.

    Args:
        fecha: Fecha del ticket.

    Returns:
        Path a la carpeta del trimestre (ej: gestion-facturas/2T26/).
    """
    trimestre = calcular_trimestre(fecha)
    carpeta = PROJECT_ROOT / trimestre
    carpeta.mkdir(parents=True, exist_ok=True)
    return carpeta


def generar_nombre_pdf(fecha: datetime, proveedor: str, modo_pago: str = "TJ",
                       carpeta: Path | None = None) -> str:
    """Genera nombre de PDF según convención gestion-facturas.

    Formato: TTYY_MMDD_{PROV}_{MODO}.pdf
    Si ya existe en carpeta, añade sufijo: _2, _3, etc.

    Args:
        fecha: Fecha del ticket.
        proveedor: Código del proveedor (ej: "BM", "DIA").
        modo_pago: Código de método de pago (default: "TJ" = tarjeta).
        carpeta: Carpeta destino para comprobar duplicados. Si None, no comprueba.

    Returns:
        Nombre del archivo (ej: "2T26_0401_BM_TJ.pdf").
    """
    trimestre = calcular_trimestre(fecha)
    mmdd = fecha.strftime("%m%d")
    nombre_base = f"{trimestre}_{mmdd}_{proveedor}_{modo_pago}"
    nombre = f"{nombre_base}.pdf"

    if carpeta:
        contador = 2
        while (carpeta / nombre).exists():
            nombre = f"{nombre_base}_{contador}.pdf"
            contador += 1

    return nombre


# ── Registro anti-duplicación ────────────────────────────────────────────────

def _ruta_registro(proveedor: str) -> Path:
    """Devuelve la ruta al archivo de registro del proveedor."""
    return REGISTROS_DIR / f"registro_{proveedor.lower()}.json"


def cargar_registro(proveedor: str) -> dict:
    """Carga el registro anti-duplicación de un proveedor.

    Args:
        proveedor: Nombre del proveedor (ej: "BM", "DIA").

    Returns:
        Dict con el registro. Si no existe, devuelve dict vacío.
    """
    ruta = _ruta_registro(proveedor)
    if not ruta.exists():
        return {}
    try:
        with open(ruta, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def guardar_registro(proveedor: str, registro: dict):
    """Guarda el registro anti-duplicación de un proveedor.

    Args:
        proveedor: Nombre del proveedor (ej: "BM", "DIA").
        registro: Dict con el registro a guardar.
    """
    REGISTROS_DIR.mkdir(parents=True, exist_ok=True)
    ruta = _ruta_registro(proveedor)
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(registro, f, indent=2, ensure_ascii=False)


def esta_procesado(huella: str, registro: dict) -> bool:
    """Comprueba si un ticket ya fue procesado.

    Args:
        huella: Identificador único del ticket.
        registro: Dict del registro cargado.

    Returns:
        True si ya está registrado.
    """
    return huella in registro


def registrar_ticket(huella: str, info: dict, registro: dict) -> dict:
    """Añade un ticket al registro.

    Args:
        huella: Identificador único del ticket.
        info: Dict con metadatos del ticket (fecha, total, fichero, etc.).
        registro: Dict del registro donde añadir.

    Returns:
        El registro actualizado.
    """
    registro[huella] = {
        **info,
        "registrado": datetime.now().isoformat(),
    }
    return registro


# ── Extracción de texto PDF ──────────────────────────────────────────────────

def extraer_texto_pdf(ruta: Path) -> str:
    """Extrae texto de un PDF usando pdfplumber.

    Args:
        ruta: Path al archivo PDF.

    Returns:
        Texto extraído del PDF, o string vacío si falla.
    """
    try:
        import pdfplumber
    except ImportError:
        logging.error("pdfplumber no instalado. Ejecutar: pip install pdfplumber")
        return ""

    try:
        with pdfplumber.open(ruta) as pdf:
            textos = []
            for pagina in pdf.pages:
                texto = pagina.extract_text()
                if texto:
                    textos.append(texto)
            return "\n".join(textos)
    except Exception as e:
        logging.error("Error leyendo %s: %s", ruta.name, e)
        return ""


def extraer_fecha_generica(texto: str) -> datetime | None:
    """Extrae fecha de un texto de ticket (DD/MM/YY o DD/MM/YYYY).

    Busca patrones de fecha comunes en tickets de supermercado.

    Args:
        texto: Texto extraído del PDF.

    Returns:
        datetime con la fecha encontrada, o None.
    """
    patrones = [
        # Fecha: DD/MM/YY o DD/MM/YYYY
        r'[Ff]echa[:\s]*(\d{1,2})[/\-](\d{1,2})[/\-](\d{2,4})',
        # DD/MM/YY HH:MM
        r'(\d{1,2})[/\-](\d{1,2})[/\-](\d{2,4})\s+\d{1,2}:\d{2}',
        # DD/MM/YY suelto
        r'(\d{1,2})[/\-](\d{1,2})[/\-](\d{2,4})',
    ]

    for patron in patrones:
        match = re.search(patron, texto)
        if match:
            dia = int(match.group(1))
            mes = int(match.group(2))
            anyo = int(match.group(3))

            if anyo < 100:
                anyo += 2000

            if 1 <= dia <= 31 and 1 <= mes <= 12 and 2020 <= anyo <= 2030:
                try:
                    return datetime(anyo, mes, dia)
                except ValueError:
                    continue

    return None


# ── Copia a carpeta de trimestre ─────────────────────────────────────────────

def copiar_a_trimestre(origen: Path, fecha: datetime, proveedor: str,
                       modo_pago: str = "TJ") -> Path | None:
    """Copia un PDF a la carpeta del trimestre con el nombre correcto.

    Args:
        origen: Path al PDF original.
        fecha: Fecha del ticket.
        proveedor: Código del proveedor (ej: "BM").
        modo_pago: Código de método de pago (default: "TJ").

    Returns:
        Path al archivo destino, o None si falla.
    """
    import shutil

    carpeta = obtener_carpeta_trimestre(fecha)
    nombre = generar_nombre_pdf(fecha, proveedor, modo_pago, carpeta)
    destino = carpeta / nombre

    try:
        shutil.copy2(origen, destino)
        return destino
    except Exception as e:
        logging.error("Error copiando %s → %s: %s", origen.name, destino, e)
        return None


# ── Resumen de procesamiento ─────────────────────────────────────────────────

def imprimir_resumen(proveedor: str, analizados: int = 0, nuevos: int = 0,
                     duplicados: int = 0, errores: int = 0, dry_run: bool = False):
    """Imprime resumen del procesamiento de tickets.

    Args:
        proveedor: Nombre del proveedor.
        analizados: Total de items analizados.
        nuevos: Tickets nuevos procesados.
        duplicados: Tickets ya procesados (saltados).
        errores: Tickets con error.
        dry_run: Si True, indica que fue simulación.
    """
    print()
    print("=" * 50)
    print(f"  RESUMEN — {proveedor}")
    print("=" * 50)
    print(f"  Analizados:         {analizados}")
    print(f"  Ya procesados:      {duplicados}")
    print(f"  Nuevos procesados:  {nuevos}")
    if errores:
        print(f"  Errores:            {errores}")
    if dry_run:
        print(f"  [DRY-RUN: nada se ha copiado/descargado]")
    print("=" * 50)
