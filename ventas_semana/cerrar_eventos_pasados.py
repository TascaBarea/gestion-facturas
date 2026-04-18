"""
cerrar_eventos_pasados.py — Archivar eventos cuya fecha ya pasó
Comestibles Barea · Cambia status a "private" (no borra ni modifica nombre/stock)
Uso: python cerrar_eventos_pasados.py [--ejecutar] [--dias-gracia N]
Default: dry-run (muestra qué cerraría sin hacer cambios)
Importable: from cerrar_eventos_pasados import cerrar_pasados
"""

import os
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

# ── Activar colores ANSI en Windows ───────────────────────────────────────────
if sys.platform == "win32":
    import ctypes
    kernel32 = ctypes.windll.kernel32
    kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)

# ── Colores ───────────────────────────────────────────────────────────────────
class C:
    RESET   = "\033[0m"
    BOLD    = "\033[1m"
    VERDE   = "\033[38;2;46;125;50m"
    GRIS    = "\033[38;2;150;150;150m"
    AMARILLO= "\033[38;2;232;201;122m"
    ROJO    = "\033[38;2;183;28;28m"

def _ok(msg):
    print(C.VERDE + C.BOLD + "  ✓ " + C.RESET + msg)

def _error(msg):
    print(C.ROJO + C.BOLD + "  ✗ " + C.RESET + C.ROJO + msg + C.RESET)

def _info(msg):
    print(C.GRIS + "  · " + msg + C.RESET)

def _aviso(msg):
    print(C.AMARILLO + "  ⚠ " + msg + C.RESET)

# ── Cargar .env ────────────────────────────────────────────────────────────────
_SCRIPT_DIR = Path(__file__).parent
_ENV_PATH = _SCRIPT_DIR / ".env"
if _ENV_PATH.exists():
    try:
        from dotenv import load_dotenv
        load_dotenv(_ENV_PATH)
    except ImportError:
        with open(_ENV_PATH, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

try:
    from woocommerce import API as WC_API
except ImportError:
    _error("Librería 'woocommerce' no instalada. Ejecuta: pip install woocommerce")
    sys.exit(1)


def _get_wc():
    url    = os.getenv("WC_URL")
    key    = os.getenv("WC_KEY")
    secret = os.getenv("WC_SECRET")
    if not url or not key or not secret:
        _error("Faltan credenciales WooCommerce en el .env (WC_URL, WC_KEY, WC_SECRET).")
        sys.exit(1)
    return WC_API(url=url, consumer_key=key, consumer_secret=secret,
                  version="wc/v3", timeout=30)


_FECHA_RE = re.compile(r"\b(\d{1,2}/\d{2}/\d{2})\s*$")


def _extraer_fecha(nombre):
    m = _FECHA_RE.search(nombre)
    if m:
        try:
            return datetime.strptime(m.group(1), "%d/%m/%y").date()
        except ValueError:
            pass
    return None


# ── Función principal (importable) ────────────────────────────────────────────

def cerrar_pasados(dias_gracia=1, dry_run=True):
    """Cierra eventos pasados cambiando status a 'private'.

    Args:
        dias_gracia: No cerrar si la fecha fue hace menos de N días (default: 1)
        dry_run: Si True, solo muestra qué haría sin hacer cambios

    Returns:
        dict con claves: cerrados, saltados, errores
    """
    wc = _get_wc()
    hoy = datetime.now().date()
    limite = hoy - timedelta(days=dias_gracia)

    _info("Descargando productos publicados...")
    productos = []
    page = 1
    while True:
        resp = wc.get("products", params={"per_page": 100, "page": page, "status": "publish"}).json()
        if not isinstance(resp, list) or not resp:
            break
        productos.extend(resp)
        page += 1
        if len(resp) < 100:
            break
    _ok(f"{len(productos)} productos publicados")

    cerrados = 0
    saltados = 0
    errores = 0

    for prod in productos:
        nombre = prod.get("name", "")
        fecha = _extraer_fecha(nombre)

        if not fecha:
            continue

        if fecha > limite:
            saltados += 1
            continue

        dias_pasados = (hoy - fecha).days

        if dry_run:
            _aviso(f"CERRARÍA: {nombre} (hace {dias_pasados} días)")
            cerrados += 1
            continue

        try:
            result = wc.put(f"products/{prod['id']}", {"status": "private"}).json()
            if "id" in result:
                _ok(f"Cerrado: {nombre} (hace {dias_pasados} días)")
                cerrados += 1
            else:
                _error(f"Error API en {nombre}: {result.get('message', str(result))}")
                errores += 1
        except Exception as e:
            _error(f"Excepción en {nombre}: {e}")
            errores += 1

    return {"cerrados": cerrados, "saltados": saltados, "errores": errores}


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    args = sys.argv[1:]

    ejecutar = "--ejecutar" in args
    dry_run = not ejecutar

    dias_gracia = 1
    if "--dias-gracia" in args:
        idx = args.index("--dias-gracia")
        if idx + 1 < len(args):
            try:
                dias_gracia = int(args[idx + 1])
            except ValueError:
                _error(f"Valor inválido para --dias-gracia: {args[idx + 1]}")
                sys.exit(1)

    print()
    print(C.VERDE + C.BOLD + "  CERRAR EVENTOS PASADOS — Comestibles Barea" + C.RESET)
    modo = "EJECUTAR" if ejecutar else "DRY-RUN (simulación)"
    print(C.GRIS + f"  Modo: {modo}  |  Días de gracia: {dias_gracia}" + C.RESET)
    print()

    if not ejecutar:
        _aviso("Modo DRY-RUN: no se harán cambios. Usa --ejecutar para aplicar.")
        print()

    resultado = cerrar_pasados(dias_gracia=dias_gracia, dry_run=dry_run)

    print()
    print(C.VERDE + C.BOLD + "  ═══ RESUMEN ═══" + C.RESET)
    verbo = "Se cerrarían" if dry_run else "Cerrados"
    _ok(f"{verbo}: {resultado['cerrados']}")
    _info(f"Saltados (dentro de gracia o sin fecha): {resultado['saltados']}")
    if resultado["errores"]:
        _error(f"Errores: {resultado['errores']}")
    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print()
        _aviso("Cancelado por el usuario.")
        sys.exit(0)
