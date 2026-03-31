"""
alta_evento.py — Alta interactiva de eventos en WooCommerce
Convención de nombres: "{nombre} {DD/MM/YY}" | Descripción: "HORARIO: de HH:MM a HH:MM"
Detecta automáticamente eventos ya programados en la misma fecha y avisa antes de continuar.
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

# ── Paleta de colores (marca Comestibles Barea) ────────────────────────────────
class C:
    RESET   = "\033[0m"
    BOLD    = "\033[1m"
    # Verdes Comestibles
    VERDE   = "\033[38;2;46;125;50m"       # #2E7D32
    VERDE_C = "\033[38;2;168;232;192m"     # #a8e8c0  (texto claro sobre oscuro)
    VERDE_B = "\033[48;2;27;94;32m"        # #1B5E20  fondo
    # Neutros
    GRIS    = "\033[38;2;150;150;150m"
    BLANCO  = "\033[38;2;240;240;240m"
    AMARILLO= "\033[38;2;232;201;122m"     # #e8c97a  (acento dorado)
    ROJO    = "\033[38;2;183;28;28m"
    FONDO_O = "\033[48;2;12;15;14m"        # #0c0f0e  fondo oscuro header


W = 58  # ancho de línea


def _linea(char="─"):
    return C.VERDE + char * W + C.RESET

def _header():
    """Cabecera con la identidad visual de Comestibles."""
    print()
    print(C.FONDO_O + C.VERDE_C + C.BOLD + " " * W + C.RESET)
    titulo = "COMESTIBLES BAREA"
    sub    = "Alta de Evento / Taller / Cata"
    print(C.FONDO_O + C.VERDE_C + C.BOLD +
          titulo.center(W) + C.RESET)
    print(C.FONDO_O + C.GRIS +
          sub.center(W) + C.RESET)
    print(C.FONDO_O + C.VERDE_C + C.BOLD + " " * W + C.RESET)
    print()

def _seccion(titulo):
    """Separador de sección con título."""
    print()
    print(_linea())
    print(C.VERDE + C.BOLD + f"  {titulo}" + C.RESET)
    print(_linea())

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


# ── WooCommerce API ────────────────────────────────────────────────────────────

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


def _cargar_eventos_existentes(wc):
    """Descarga productos publicados de WooCommerce y extrae fechas de sus nombres.
    Convención: "{nombre} DD/MM/YY" → se parsea la fecha del final.
    Devuelve dict {date: [nombre_producto, ...]} solo con fechas ≥ hoy."""
    _FECHA_RE = re.compile(r"\b(\d{1,2}/\d{2}/\d{2})\s*$")
    eventos = {}   # date → [nombre, ...]
    hoy = datetime.now().date()
    page = 1

    while True:
        resp = wc.get("products", params={
            "per_page": 100, "page": page,
            "status": "publish",
        }).json()
        if not isinstance(resp, list) or not resp:
            break
        for prod in resp:
            nombre = prod.get("name", "")
            m = _FECHA_RE.search(nombre)
            if m:
                try:
                    dt = datetime.strptime(m.group(1), "%d/%m/%y").date()
                    if dt >= hoy:
                        eventos.setdefault(dt, []).append(nombre)
                except ValueError:
                    pass
        page += 1
        if len(resp) < 100:
            break

    return eventos


# ── Helpers de entrada ─────────────────────────────────────────────────────────

def _pedir(prompt, *, opcional=False, default=None, ejemplo=None):
    """Input con estilo: prompt en verde, hint en gris."""
    hints = []
    if ejemplo:
        hints.append(C.GRIS + f"ej: {ejemplo}" + C.RESET)
    if opcional:
        hints.append(C.GRIS + "Enter para omitir" + C.RESET)
    elif default is not None:
        hints.append(C.GRIS + f"Enter = {default}" + C.RESET)

    sufijo = ("  " + "  |  ".join(hints)) if hints else ""
    linea  = C.VERDE + C.BOLD + f"  › {prompt}" + C.RESET + sufijo
    valor  = input(f"{linea}\n    ").strip()
    print()
    return valor if valor else default


def _pedir_fecha(eventos_existentes=None):
    """Pide fecha y comprueba si ya hay eventos programados ese día."""
    while True:
        raw = _pedir("Fecha del evento", ejemplo="28/03/26")
        if not raw:
            _error("La fecha es obligatoria.")
            continue
        try:
            dt = datetime.strptime(raw, "%d/%m/%y")
            if dt.date() < datetime.now().date():
                _aviso("La fecha ya ha pasado. Continúa si es correcto.")

            # ── Comprobar coincidencia con eventos existentes ──────────
            if eventos_existentes and dt.date() in eventos_existentes:
                nombres = eventos_existentes[dt.date()]
                print()
                print(C.ROJO + C.BOLD + "  ╔" + "═" * (W - 4) + "╗" + C.RESET)
                print(C.ROJO + C.BOLD + "  ║  ⚠ FECHA CON EVENTO YA PROGRAMADO" +
                      " " * (W - 40) + "║" + C.RESET)
                print(C.ROJO + C.BOLD + "  ╟" + "─" * (W - 4) + "╢" + C.RESET)
                for nombre in nombres:
                    linea_txt = f"  ║  → {nombre}"
                    pad = W - 2 - len(f"  ║  → {nombre}")
                    if pad < 0:
                        # Truncar si es muy largo
                        nombre_corto = nombre[:W - 12] + "…"
                        linea_txt = f"  ║  → {nombre_corto}"
                        pad = W - 2 - len(linea_txt)
                    print(C.ROJO + linea_txt + " " * max(pad, 0) + "║" + C.RESET)
                print(C.ROJO + C.BOLD + "  ╚" + "═" * (W - 4) + "╝" + C.RESET)
                print()

                resp = input(C.AMARILLO + C.BOLD +
                             "  ¿Continuar con esta fecha de todos modos? (s/n): " +
                             C.RESET).strip().lower()
                print()
                if resp not in ("s", "si", "sí", "y", "yes"):
                    _info("Elige otra fecha.")
                    continue

            return raw, dt
        except ValueError:
            _error(f"Formato incorrecto: '{raw}'. Usa DD/MM/YY  (ej: 28/03/26)")


def _pedir_hora(prompt, *, opcional=True):
    while True:
        raw = _pedir(prompt, opcional=opcional, ejemplo="18:30")
        if not raw:
            return None
        try:
            datetime.strptime(raw, "%H:%M")
            return raw
        except ValueError:
            _error(f"Formato incorrecto: '{raw}'. Usa HH:MM  (ej: 18:30)")


def _pedir_precio():
    while True:
        raw = _pedir("Precio por persona", ejemplo="35  ó  35,50")
        if not raw:
            _error("El precio es obligatorio.")
            continue
        try:
            precio = float(raw.replace(",", "."))
            if precio <= 0:
                raise ValueError()
            return precio
        except ValueError:
            _error(f"Precio inválido: '{raw}'. Usa un número positivo.")


def _pedir_plazas():
    while True:
        raw = _pedir("Número de plazas", opcional=True, ejemplo="20")
        if raw is None:
            return None
        try:
            n = int(raw)
            if n <= 0:
                raise ValueError()
            return n
        except ValueError:
            _error(f"Número inválido: '{raw}'. Introduce un entero positivo o Enter para sin límite.")


def _pedir_categoria(cats):
    if not cats:
        _aviso("No hay categorías en WooCommerce. Se creará sin categoría.")
        return None

    print(C.GRIS + "  Categorías disponibles:" + C.RESET)
    for i, (_, nombre) in enumerate(cats, 1):
        print(C.VERDE + f"    {i:>2}." + C.RESET + f" {nombre}")
    print()

    while True:
        raw = _pedir("Categoría", opcional=True, ejemplo="1")
        if raw is None:
            return None
        try:
            idx = int(raw) - 1
            if 0 <= idx < len(cats):
                return cats[idx]
            _error(f"Elige un número entre 1 y {len(cats)}.")
        except ValueError:
            _error("Introduce un número.")


# ── Descripción ────────────────────────────────────────────────────────────────

def _construir_descripcion(hora_inicio, hora_fin, descripcion_extra):
    partes = []
    if hora_inicio:
        horario = f"HORARIO: de {hora_inicio}"
        if hora_fin:
            horario += f" a {hora_fin}"
        partes.append(horario)
    if descripcion_extra:
        partes.append(descripcion_extra)
    return "\n".join(partes)


# ── Resumen visual ─────────────────────────────────────────────────────────────

def _fila(label, valor, color_val=None):
    col = color_val or C.BLANCO
    pad = 18
    print(C.GRIS + f"  {label:<{pad}}" + C.RESET +
          col + C.BOLD + str(valor) + C.RESET)


def _mostrar_resumen(nombre_producto, fecha_raw, hora_inicio, hora_fin,
                     precio, plazas, categoria, descripcion):
    _seccion("RESUMEN DEL EVENTO")
    print()
    _fila("Nombre",    nombre_producto,  C.VERDE_C)
    _fila("Fecha",     datetime.strptime(fecha_raw, "%d/%m/%y").strftime("%d/%m/%Y"), C.AMARILLO)
    horario_txt = f"{hora_inicio}" + (f" a {hora_fin}" if hora_fin else "") if hora_inicio else "(no especificado)"
    _fila("Horario",   horario_txt)
    _fila("Precio",    f"{precio:.2f} €".replace(".", ","), C.VERDE)
    _fila("Plazas",    plazas if plazas is not None else "Sin límite")
    _fila("Categoría", categoria[1] if categoria else "(ninguna)")
    if descripcion:
        desc_corta = descripcion[:60] + ("…" if len(descripcion) > 60 else "")
        _fila("Descripción", desc_corta)
    print()
    print(_linea())


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    _header()

    _info("Conectando con WooCommerce...")
    wc = _get_wc()
    _info("Cargando categorías...")
    cats = _cargar_categorias(wc)
    _ok(f"{len(cats)} categorías disponibles")
    _info("Cargando eventos programados...")
    eventos_existentes = _cargar_eventos_existentes(wc)
    _ok(f"{sum(len(v) for v in eventos_existentes.values())} eventos futuros detectados")

    _seccion("DATOS DEL EVENTO")
    _info("Pulsa Ctrl+C en cualquier momento para cancelar.\n")

    nombre_base = _pedir("Nombre del evento (sin fecha)", ejemplo="Cata de vinos naturales")
    while not nombre_base:
        _error("El nombre es obligatorio.")
        nombre_base = _pedir("Nombre del evento (sin fecha)", ejemplo="Cata de vinos naturales")

    fecha_raw, fecha_dt = _pedir_fecha(eventos_existentes)
    fecha_yy      = fecha_dt.strftime("%d/%m/%y")
    nombre_producto = f"{nombre_base} {fecha_yy}"
    _info(f"Nombre en WooCommerce: {C.BOLD}{nombre_producto}{C.RESET}{C.GRIS}")

    hora_inicio = _pedir_hora("Hora de inicio (HH:MM)")
    hora_fin    = _pedir_hora("Hora de fin (HH:MM)") if hora_inicio else None

    precio = _pedir_precio()
    plazas = _pedir_plazas()

    _seccion("CATEGORÍA")
    categoria = _pedir_categoria(cats)

    _seccion("DESCRIPCIÓN ADICIONAL")
    desc_extra  = _pedir("Texto extra (opcional)", opcional=True,
                         ejemplo="Incluye degustación de 6 vinos y maridaje")
    descripcion = _construir_descripcion(hora_inicio, hora_fin, desc_extra)

    _mostrar_resumen(nombre_producto, fecha_raw, hora_inicio, hora_fin,
                     precio, plazas, categoria, descripcion)

    respuesta = input(C.VERDE + C.BOLD +
                      "  ¿Publicar este evento en WooCommerce? (s/n): " +
                      C.RESET).strip().lower()
    print()
    if respuesta not in ("s", "si", "sí", "y", "yes"):
        _aviso("Cancelado. No se ha creado ningún evento.")
        return

    # ── Crear producto ─────────────────────────────────────────────────────────
    _info("Publicando en WooCommerce...")
    payload = {
        "name":          nombre_producto,
        "type":          "simple",
        "status":        "publish",
        "regular_price": str(precio),
        "description":   descripcion,
        "manage_stock":  plazas is not None,
    }
    if plazas is not None:
        payload["stock_quantity"] = plazas
        payload["stock_status"]   = "instock"
    if categoria:
        payload["categories"] = [{"id": categoria[0]}]

    resp      = wc.post("products", payload)
    resultado = resp.json()

    if "id" in resultado:
        print()
        print(_linea("═"))
        _ok(C.BOLD + "¡Evento publicado correctamente!" + C.RESET)
        _info(f"ID WooCommerce : {resultado['id']}")
        _info(f"URL            : {resultado.get('permalink', '(no disponible)')}")
        print()
        _info("Aparecerá en el email semanal del próximo lunes.")
        print(_linea("═"))
    else:
        _error("WooCommerce devolvió un error:")
        print(C.ROJO + "  " + (resultado.get("message") or str(resultado)) + C.RESET)
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print()
        _aviso("Cancelado por el usuario.")
        sys.exit(0)
