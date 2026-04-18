"""
migrar_productos.py — Corregir productos/eventos existentes en WooCommerce
Comestibles Barea · Migración a formato v2
Uso: python migrar_productos.py [--auto] [--dry-run] [--include-past]
"""

import os
import re
import sys
from datetime import datetime
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
    BLANCO  = "\033[38;2;240;240;240m"
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


# ── WooCommerce ───────────────────────────────────────────────────────────────

def _get_wc():
    url    = os.getenv("WC_URL")
    key    = os.getenv("WC_KEY")
    secret = os.getenv("WC_SECRET")
    if not url or not key or not secret:
        _error("Faltan credenciales WooCommerce en el .env (WC_URL, WC_KEY, WC_SECRET).")
        sys.exit(1)
    return WC_API(url=url, consumer_key=key, consumer_secret=secret,
                  version="wc/v3", timeout=30)


def _cargar_categorias(wc):
    cats, page = [], 1
    while True:
        resp = wc.get("products/categories", params={"per_page": 100, "page": page}).json()
        if not isinstance(resp, list) or not resp:
            break
        cats.extend(resp)
        page += 1
        if len(resp) < 100:
            break
    return [(c["id"], c["name"]) for c in cats if c.get("name") != "Sin categoría"]


def _autosugerir_categoria(nombre, cats):
    """Auto-sugiere categoría basándose en el nombre del evento."""
    nombre_lower = nombre.lower()
    reglas = [
        (["cata", "vino", "queso"], "cata"),
        (["taller", "kombucha", "fermenta", "vermú", "vermut"], "taller"),
        (["degustaci"], "degustaci"),
    ]
    for keywords, buscar in reglas:
        if any(kw in nombre_lower for kw in keywords):
            for cat_id, cat_nombre in cats:
                if buscar in cat_nombre.lower():
                    return cat_id, cat_nombre
    return None


# ── Exclusiones ───────────────────────────────────────────────────────────────

PRODUCTOS_EXCLUIDOS = [
    "Regalismo mágico",
]

_FECHA_RE = re.compile(r"\b(\d{1,2}/\d{2}/\d{2})\s*$")


def _es_evento(nombre):
    """Un producto es evento si su nombre contiene una fecha DD/MM/YY."""
    return bool(_FECHA_RE.search(nombre))


def _extraer_fecha(nombre):
    m = _FECHA_RE.search(nombre)
    if m:
        try:
            return datetime.strptime(m.group(1), "%d/%m/%y").date()
        except ValueError:
            pass
    return None


def _generar_short_desc(nombre):
    """Genera short_description básica para productos que no la tienen."""
    return f"{nombre} · Comestibles Barea, Lavapiés (Madrid)"


# ── Análisis y corrección ─────────────────────────────────────────────────────

def _limpiar_html(texto):
    """Elimina tags HTML y colapsa espacios múltiples."""
    limpio = re.sub(r'<[^>]+>', ' ', texto)
    limpio = re.sub(r'\s+', ' ', limpio).strip()
    return limpio


def _analizar_producto(prod, cats):
    """Analiza un producto y devuelve lista de correcciones necesarias."""
    cambios = {}
    nombre = prod.get("name", "")

    # HTML en el nombre
    if re.search(r'<[^>]+>', nombre):
        cambios["name"] = (nombre, _limpiar_html(nombre))

    # virtual
    if not prod.get("virtual", False):
        cambios["virtual"] = (prod.get("virtual"), True)

    # tax_class
    if prod.get("tax_class", "") != "IVA 21":
        cambios["tax_class"] = (prod.get("tax_class", "(vacío)"), "IVA 21")

    # backorders
    if prod.get("backorders", "") != "no":
        cambios["backorders"] = (prod.get("backorders", "(vacío)"), "no")

    # low_stock_amount
    if prod.get("low_stock_amount") != 3:
        cambios["low_stock_amount"] = (prod.get("low_stock_amount"), 3)

    # sin categoría
    categorias = prod.get("categories", [])
    cats_reales = [c for c in categorias if c.get("name") != "Sin categoría"]
    if not cats_reales:
        sugerencia = _autosugerir_categoria(nombre, cats)
        if sugerencia:
            cambios["categories"] = ("(ninguna)", sugerencia[1])
            cambios["_cat_id"] = sugerencia[0]

    # sin short_description
    if not prod.get("short_description", "").strip():
        nombre_limpio = cambios["name"][1] if "name" in cambios else nombre
        short = _generar_short_desc(nombre_limpio)
        if len(short) > 125:
            short = short[:122] + "…"
        cambios["short_description"] = ("(vacía)", short)

    return cambios


def _mostrar_cambios(prod, cambios):
    """Muestra los cambios propuestos para un producto."""
    print()
    print(C.VERDE + C.BOLD + f"  ── {prod['name']}" + C.RESET)
    print(C.GRIS + f"     ID: {prod['id']}  |  SKU: {prod.get('sku', '(sin SKU)')}" + C.RESET)
    for campo, (antes, despues) in cambios.items():
        if campo.startswith("_"):
            continue
        antes_str = str(antes) if antes is not None else "(vacío)"
        print(f"     {C.ROJO}{campo}: {antes_str}{C.RESET} → {C.VERDE}{despues}{C.RESET}")


def _construir_payload(cambios):
    """Construye el payload de actualización a partir de los cambios."""
    payload = {}
    for campo, (_, nuevo) in cambios.items():
        if campo.startswith("_"):
            continue
        if campo == "categories":
            cat_id = cambios.get("_cat_id")
            if cat_id:
                payload["categories"] = [{"id": cat_id}]
        else:
            payload[campo] = nuevo
    return payload


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    args = sys.argv[1:]
    auto = "--auto" in args
    dry_run = "--dry-run" in args
    include_past = "--include-past" in args

    # --ids 3274 3272 3276 → forzar migración de IDs específicos
    forced_ids = set()
    if "--ids" in args:
        idx = args.index("--ids")
        for val in args[idx + 1:]:
            if val.startswith("--"):
                break
            try:
                forced_ids.add(int(val))
            except ValueError:
                _error(f"ID inválido: '{val}'. Los IDs deben ser números enteros.")
                sys.exit(1)
        if not forced_ids:
            _error("--ids requiere al menos un ID de producto.")
            sys.exit(1)

    print()
    print(C.VERDE + C.BOLD + "  MIGRAR PRODUCTOS — Comestibles Barea" + C.RESET)
    modo = "DRY-RUN" if dry_run else ("AUTO" if auto else "INTERACTIVO")
    print(C.GRIS + f"  Modo: {modo}" + C.RESET)
    if forced_ids:
        print(C.GRIS + f"  IDs forzados: {', '.join(str(i) for i in sorted(forced_ids))}" + C.RESET)
    print()

    wc = _get_wc()
    _info("Cargando categorías...")
    cats = _cargar_categorias(wc)
    _ok(f"{len(cats)} categorías")

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
    _ok(f"{len(productos)} productos descargados")

    hoy = datetime.now().date()
    corregidos = 0
    sin_cambios = 0
    errores = 0
    saltados = 0

    for prod in productos:
        nombre = prod.get("name", "")

        prod_id = prod.get("id")
        forzado = prod_id in forced_ids

        # ¿Es evento? (skip si no tiene fecha, salvo que esté en --ids)
        if not _es_evento(nombre) and not forzado:
            continue

        # ¿Excluido?
        if any(excl.lower() in nombre.lower() for excl in PRODUCTOS_EXCLUIDOS):
            _info(f"EXCLUIDO: {nombre}")
            saltados += 1
            continue

        # ¿Fecha pasada? (no aplica a IDs forzados)
        fecha = _extraer_fecha(nombre)
        if fecha and fecha < hoy and not include_past and not forzado:
            saltados += 1
            continue

        # Si hay --ids, filtrar solo esos
        if forced_ids and not forzado:
            continue

        # Analizar
        cambios = _analizar_producto(prod, cats)
        if not cambios:
            sin_cambios += 1
            continue

        _mostrar_cambios(prod, cambios)

        if dry_run:
            _info("  (dry-run: no se aplican cambios)")
            corregidos += 1
            continue

        # Confirmación
        if not auto:
            resp = input(C.AMARILLO + "     ¿Aplicar cambios? (s/n): " + C.RESET).strip().lower()
            if resp not in ("s", "si", "sí", "y", "yes"):
                _info("  Saltado.")
                saltados += 1
                continue

        # Aplicar
        payload = _construir_payload(cambios)
        try:
            result = wc.put(f"products/{prod['id']}", payload).json()
            if "id" in result:
                _ok(f"  Corregido (ID: {prod['id']})")
                corregidos += 1
            else:
                _error(f"  Error API: {result.get('message', str(result))}")
                errores += 1
        except Exception as e:
            _error(f"  Excepción: {e}")
            errores += 1

    # Resumen
    print()
    print(C.VERDE + C.BOLD + "  ═══ RESUMEN ═══" + C.RESET)
    _ok(f"Corregidos: {corregidos}")
    _info(f"Sin cambios: {sin_cambios}")
    _info(f"Saltados: {saltados}")
    if errores:
        _error(f"Errores: {errores}")
    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print()
        _aviso("Cancelado por el usuario.")
        sys.exit(0)
