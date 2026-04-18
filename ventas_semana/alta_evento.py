"""
alta_evento.py v2 — Alta interactiva de eventos en WooCommerce
Comestibles Barea · Experiencias gastronómicas
Convención: "{nombre} — {fecha_legible}" | IVA 21% | SEO Yoast
"""

import json
import os
import re
import sys
import unicodedata
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
    VERDE   = "\033[38;2;46;125;50m"
    VERDE_C = "\033[38;2;168;232;192m"
    VERDE_B = "\033[48;2;27;94;32m"
    GRIS    = "\033[38;2;150;150;150m"
    BLANCO  = "\033[38;2;240;240;240m"
    AMARILLO= "\033[38;2;232;201;122m"
    ROJO    = "\033[38;2;183;28;28m"
    FONDO_O = "\033[48;2;12;15;14m"


W = 58

MESES = {
    1: "enero", 2: "febrero", 3: "marzo", 4: "abril",
    5: "mayo", 6: "junio", 7: "julio", 8: "agosto",
    9: "septiembre", 10: "octubre", 11: "noviembre", 12: "diciembre"
}
DIAS_SEMANA = {
    0: "Lunes", 1: "Martes", 2: "Miércoles", 3: "Jueves",
    4: "Viernes", 5: "Sábado", 6: "Domingo"
}

TEMPLATE_DESCRIPCION = """\
📅 {dia_semana} {dia} de {mes} de {año}
🕖 De {hora_inicio} a {hora_fin}
📍 Comestibles Barea — C/ Embajadores 38, Madrid (Lavapiés)

{descripcion_extra}

Precio: {precio}€ (IVA incluido) · Plazas limitadas a {plazas} personas

Reserva tu plaza online y disfruta de una experiencia gastronómica única en el corazón de Lavapiés."""


# ── Funciones de presentación ─────────────────────────────────────────────────

def _linea(char="─"):
    return C.VERDE + char * W + C.RESET

def _header():
    print()
    print(C.FONDO_O + C.VERDE_C + C.BOLD + " " * W + C.RESET)
    titulo = "COMESTIBLES BAREA"
    sub    = "Alta de Evento / Taller / Cata"
    print(C.FONDO_O + C.VERDE_C + C.BOLD + titulo.center(W) + C.RESET)
    print(C.FONDO_O + C.GRIS + sub.center(W) + C.RESET)
    print(C.FONDO_O + C.VERDE_C + C.BOLD + " " * W + C.RESET)
    print()

def _seccion(titulo):
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
    """Descarga productos y extrae fechas. Devuelve dict {date: [nombre, ...]}."""
    _FECHA_RE = re.compile(r"\b(\d{1,2}/\d{2}/\d{2})\s*$")
    eventos = {}
    hoy = datetime.now().date()
    page = 1
    while True:
        resp = wc.get("products", params={
            "per_page": 100, "page": page, "status": "publish",
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


def _cargar_skus_existentes(wc):
    """Devuelve set de SKUs existentes en WooCommerce."""
    skus = set()
    page = 1
    while True:
        resp = wc.get("products", params={"per_page": 100, "page": page}).json()
        if not isinstance(resp, list) or not resp:
            break
        for prod in resp:
            sku = prod.get("sku")
            if sku:
                skus.add(sku)
        page += 1
        if len(resp) < 100:
            break
    return skus


# ── Catálogo de imágenes ──────────────────────────────────────────────────────

def _cargar_imagenes():
    """Carga imagenes_eventos.json. Devuelve (catalogo, keywords) o (None, None)."""
    path = _SCRIPT_DIR / "imagenes_eventos.json"
    if not path.exists():
        return None, None
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        catalogo = data.get("catalogo", {})
        keywords = data.get("keywords", {})
        # Filtrar entradas sin ID asignado
        catalogo_activo = {k: v for k, v in catalogo.items() if v is not None}
        if not catalogo_activo:
            return None, None
        return catalogo_activo, keywords
    except (json.JSONDecodeError, KeyError):
        return None, None


def _detectar_imagen(nombre, catalogo, keywords):
    """Auto-detecta imagen basándose en keywords del nombre. Devuelve (clave, id) o None."""
    nombre_lower = nombre.lower()
    for kw, clave in keywords.items():
        if kw.lower() in nombre_lower:
            if clave in catalogo:
                return clave, catalogo[clave]
    return None


# ── Helpers ───────────────────────────────────────────────────────────────────

def slugify(text):
    """Convierte texto a slug URL-friendly."""
    text = unicodedata.normalize('NFKD', text)
    text = text.encode('ascii', 'ignore').decode('ascii')
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[-\s]+', '-', text)
    text = text.strip('-')
    return text


def _generar_sku(fecha_dt, skus_existentes):
    """Genera SKU único: evento-YYYYMMDD, con sufijo -2, -3... si hay colisión."""
    base = f"evento-{fecha_dt.strftime('%Y%m%d')}"
    if base not in skus_existentes:
        return base
    n = 2
    while f"{base}-{n}" in skus_existentes:
        n += 1
    return f"{base}-{n}"


# ── Helpers de entrada ─────────────────────────────────────────────────────────

def _pedir(prompt, *, opcional=False, default=None, ejemplo=None):
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


# ── Paso [1/8] Nombre ─────────────────────────────────────────────────────────

def _pedir_nombre():
    _seccion("[1/8] NOMBRE DEL EVENTO")
    while True:
        nombre = _pedir("Nombre del evento (sin fecha)", ejemplo="Cata de vinos naturales")
        if not nombre:
            _error("El nombre es obligatorio.")
            continue
        if len(nombre) < 5:
            _error("El nombre debe tener al menos 5 caracteres.")
            continue
        if len(nombre) > 80:
            _error("El nombre no puede superar 80 caracteres.")
            continue
        if nombre == nombre.upper() and len(nombre) > 5:
            _aviso(f"El nombre está todo en MAYÚSCULAS: \"{nombre}\"")
            resp = input(C.AMARILLO + "  ¿Continuar así? (s/n): " + C.RESET).strip().lower()
            print()
            if resp not in ("s", "si", "sí", "y", "yes"):
                continue
        return nombre


# ── Paso [2/8] Fecha ──────────────────────────────────────────────────────────

def _pedir_fecha(eventos_existentes=None):
    _seccion("[2/8] FECHA")
    while True:
        raw = _pedir("Fecha del evento", ejemplo="28/04/26")
        if not raw:
            _error("La fecha es obligatoria.")
            continue
        try:
            dt = datetime.strptime(raw, "%d/%m/%y")
            if dt.date() < datetime.now().date():
                _aviso("La fecha ya ha pasado. Continúa si es correcto.")

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

            # Datos derivados
            dia = dt.day
            mes_num = dt.month
            año = dt.year
            mes_nombre = MESES[mes_num]
            dia_semana = DIAS_SEMANA[dt.weekday()]
            fecha_legible = f"{dia} de {mes_nombre} {año}"
            fecha_corta = f"{dia} {mes_nombre[:3]} {año}"

            _ok(f"{dia_semana} {fecha_legible}")
            return raw, dt, fecha_legible, fecha_corta, dia_semana, dia, mes_nombre, año

        except ValueError:
            _error(f"Formato incorrecto: '{raw}'. Usa DD/MM/YY  (ej: 28/04/26)")


# ── Paso [3/8] Horario ────────────────────────────────────────────────────────

def _pedir_horario():
    _seccion("[3/8] HORARIO")
    while True:
        raw = _pedir("Hora de inicio (HH:MM)", default="19:00")
        if not raw:
            _error("La hora de inicio es obligatoria.")
            continue
        try:
            datetime.strptime(raw, "%H:%M")
            hora_inicio = raw
            break
        except ValueError:
            _error(f"Formato incorrecto: '{raw}'. Usa HH:MM (ej: 19:00)")

    while True:
        raw = _pedir("Hora de fin (HH:MM)", opcional=True, ejemplo="21:00")
        if not raw:
            hora_fin = None
            break
        try:
            datetime.strptime(raw, "%H:%M")
            hora_fin = raw
            break
        except ValueError:
            _error(f"Formato incorrecto: '{raw}'. Usa HH:MM (ej: 21:00)")

    if hora_fin:
        _ok(f"De {hora_inicio} a {hora_fin}")
    else:
        _ok(f"Desde las {hora_inicio}")
    return hora_inicio, hora_fin


# ── Paso [4/8] Precio ─────────────────────────────────────────────────────────

def _pedir_precio():
    _seccion("[4/8] PRECIO")
    while True:
        raw = _pedir("Precio por persona (IVA 21% incluido)", default="30", ejemplo="35")
        if not raw:
            _error("El precio es obligatorio.")
            continue
        try:
            precio = float(raw.replace(",", "."))
            if precio <= 0:
                raise ValueError()
            precio_fmt = f"{precio:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            _ok(f"{precio_fmt} € (IVA 21% incluido)")
            return precio
        except ValueError:
            _error(f"Precio inválido: '{raw}'. Usa un número positivo.")


# ── Paso [5/8] Plazas ─────────────────────────────────────────────────────────

def _pedir_plazas():
    _seccion("[5/8] PLAZAS")
    while True:
        raw = _pedir("Número de plazas", default="10")
        if not raw:
            _error("El número de plazas es obligatorio.")
            continue
        try:
            n = int(raw)
            if n == 0:
                _error("No puedes publicar sin plazas.")
                continue
            if n < 0 or n > 20:
                _error("El rango válido es de 1 a 20 plazas.")
                continue
            if n > 10:
                _aviso("El espacio tiene máximo 10 plazas. ¿Seguro?")
                resp = input(C.AMARILLO + "  (s/n): " + C.RESET).strip().lower()
                print()
                if resp not in ("s", "si", "sí", "y", "yes"):
                    continue
            elif n < 8:
                _info("Evento con plazas reducidas.")
            _ok(f"{n} plazas")
            return n
        except ValueError:
            _error(f"Número inválido: '{raw}'. Introduce un entero.")


# ── Paso [6/8] Categoría ──────────────────────────────────────────────────────

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


def _pedir_categoria(cats, nombre_evento):
    _seccion("[6/8] CATEGORÍA")
    if not cats:
        _aviso("No hay categorías en WooCommerce. Se creará sin categoría.")
        return None

    # Filtrar relevantes
    relevantes = [(cid, cn) for cid, cn in cats
                  if any(kw in cn.lower() for kw in ("cata", "taller", "degustaci"))]
    lista = relevantes if relevantes else cats

    # Auto-sugerencia
    sugerencia = _autosugerir_categoria(nombre_evento, lista)

    print(C.GRIS + "  Categorías disponibles:" + C.RESET)
    for i, (_, nombre) in enumerate(lista, 1):
        marca = " ◄ sugerida" if sugerencia and nombre == sugerencia[1] else ""
        print(C.VERDE + f"    {i:>2}." + C.RESET + f" {nombre}" +
              C.AMARILLO + marca + C.RESET)
    print()

    if sugerencia:
        _info(f"Sugerencia automática: {sugerencia[1]}")
        raw = _pedir("Categoría (Enter para aceptar sugerencia)", ejemplo="1")
        if not raw:
            _ok(f"Categoría: {sugerencia[1]}")
            return sugerencia
    else:
        raw = None

    while True:
        if raw is None:
            raw = _pedir("Categoría (número)", ejemplo="1")
        if not raw:
            _error("La categoría es obligatoria. Elige un número.")
            raw = None
            continue
        try:
            idx = int(raw) - 1
            if 0 <= idx < len(lista):
                elegida = lista[idx]
                _ok(f"Categoría: {elegida[1]}")
                return elegida
            _error(f"Elige un número entre 1 y {len(lista)}.")
        except ValueError:
            _error("Introduce un número.")
        raw = None


# ── Paso [7/8] Imagen ─────────────────────────────────────────────────────────

def _pedir_imagen(nombre_evento):
    _seccion("[7/8] IMAGEN")
    catalogo, keywords = _cargar_imagenes()

    if not catalogo:
        _aviso("Sin catálogo de imágenes. El evento se creará sin imagen.")
        _info("Puedes añadirla después en wp-admin.")
        return None

    # Auto-detectar
    match = _detectar_imagen(nombre_evento, catalogo, keywords)
    if match:
        clave, img_id = match
        _info(f"Imagen auto-asignada: {clave} (ID: {img_id})")
        resp = input(C.VERDE + "  ¿OK? (s/n): " + C.RESET).strip().lower()
        print()
        if resp in ("s", "si", "sí", "y", "yes", ""):
            _ok(f"Imagen: {clave}")
            return img_id

    # Mostrar lista
    print(C.GRIS + "  Imágenes disponibles:" + C.RESET)
    claves = list(catalogo.keys())
    for i, clave in enumerate(claves, 1):
        print(C.VERDE + f"    {i:>2}." + C.RESET + f" {clave} (ID: {catalogo[clave]})")
    print(C.GRIS + f"    {len(claves)+1:>2}." + C.RESET + " Sin imagen")
    print()

    while True:
        raw = _pedir("Imagen (número)", ejemplo="1")
        if not raw:
            _aviso("Sin imagen. Puedes añadirla después en wp-admin.")
            return None
        try:
            idx = int(raw) - 1
            if idx == len(claves):
                _aviso("Sin imagen. Puedes añadirla después en wp-admin.")
                return None
            if 0 <= idx < len(claves):
                _ok(f"Imagen: {claves[idx]}")
                return catalogo[claves[idx]]
            _error(f"Elige un número entre 1 y {len(claves)+1}.")
        except ValueError:
            _error("Introduce un número.")


# ── Paso [8/8] Descripción extra ──────────────────────────────────────────────

def _pedir_descripcion_extra():
    _seccion("[8/8] DESCRIPCIÓN EXTRA")
    return _pedir("Texto extra (opcional)", opcional=True,
                  ejemplo="Incluye degustación de 6 vinos y maridaje con quesos artesanales")


# ── Generación de datos derivados ─────────────────────────────────────────────

def _generar_datos(nombre_base, fecha_dt, fecha_legible, fecha_corta,
                   dia_semana, dia, mes_nombre, año,
                   hora_inicio, hora_fin, precio, plazas,
                   desc_extra, skus_existentes):
    """Genera todos los datos derivados del evento."""

    nombre_producto = f"{nombre_base} — {fecha_legible}"

    horario_str = hora_inicio
    if hora_fin:
        horario_str += f"-{hora_fin}"

    # Short description (≤125 chars)
    short_base = f"{nombre_base} · {fecha_corta} · {horario_str} · Comestibles Barea"
    if len(short_base) > 125:
        max_nombre = 125 - len(f" · {fecha_corta} · {horario_str} · Comestibles Barea")
        short_base = f"{nombre_base[:max_nombre]}… · {fecha_corta} · {horario_str} · Comestibles Barea"
    short_desc = short_base

    # Descripción completa
    descripcion_extra = desc_extra or "Una experiencia gastronómica en la trastienda de Comestibles Barea."
    precio_str = f"{precio:.0f}" if precio == int(precio) else f"{precio:.2f}"
    descripcion = TEMPLATE_DESCRIPCION.format(
        dia_semana=dia_semana,
        dia=dia, mes=mes_nombre, año=año,
        hora_inicio=hora_inicio, hora_fin=hora_fin or "...",
        descripcion_extra=descripcion_extra,
        precio=precio_str,
        plazas=plazas
    )

    # SKU
    sku = _generar_sku(fecha_dt, skus_existentes)

    # Slug
    slug = slugify(f"{nombre_base}-{mes_nombre}-{año}")

    # SEO
    seo_title = f"{nombre_base} en Madrid — {fecha_corta} | Comestibles Barea"
    seo_desc = (f"Disfruta de {nombre_base.lower()} en Lavapiés, Madrid. "
                f"{precio_str}€ IVA incluido. Plazas limitadas a {plazas} personas. "
                f"Reserva online.")
    seo_keywords = f"{nombre_base.lower()} madrid {mes_nombre} {año}"

    return {
        "nombre_producto": nombre_producto,
        "short_desc": short_desc,
        "descripcion": descripcion,
        "sku": sku,
        "slug": slug,
        "seo_title": seo_title,
        "seo_desc": seo_desc,
        "seo_keywords": seo_keywords,
    }


# ── Resumen visual ─────────────────────────────────────────────────────────────

def _fila(label, valor, color_val=None):
    col = color_val or C.BLANCO
    pad = 18
    print(C.GRIS + f"  {label:<{pad}}" + C.RESET +
          col + C.BOLD + str(valor) + C.RESET)


def _mostrar_resumen(datos, fecha_raw, hora_inicio, hora_fin, precio, plazas,
                     categoria, image_id):
    _seccion("RESUMEN DEL EVENTO")
    print()
    _fila("Nombre",      datos["nombre_producto"], C.VERDE_C)
    _fila("Fecha",       datetime.strptime(fecha_raw, "%d/%m/%y").strftime("%d/%m/%Y"), C.AMARILLO)
    horario_txt = f"{hora_inicio}" + (f" a {hora_fin}" if hora_fin else "") if hora_inicio else "(no especificado)"
    _fila("Horario",     horario_txt)
    precio_fmt = f"{precio:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    _fila("Precio",      f"{precio_fmt} € (IVA 21%)", C.VERDE)
    _fila("Plazas",      plazas)
    _fila("Categoría",   categoria[1] if categoria else "(ninguna)")
    _fila("SKU",         datos["sku"])
    _fila("Slug",        datos["slug"])
    _fila("Imagen",      f"ID {image_id}" if image_id else "Sin imagen")
    print()
    _info(f"Short: {datos['short_desc'][:60]}…" if len(datos['short_desc']) > 60 else f"Short: {datos['short_desc']}")
    print()
    print(_linea())


# ── Actualizar talleres_programados.json ──────────────────────────────────────

def _actualizar_talleres_json(resultado, nombre_producto, fecha_raw,
                               hora_inicio, hora_fin, plazas, precio):
    path = _SCRIPT_DIR / "talleres_programados.json"
    try:
        if path.exists():
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
        else:
            data = {"generado": None, "talleres": []}

        nuevo = {
            "id": resultado["id"],
            "nombre": nombre_producto,
            "fecha": fecha_raw,
            "hora_inicio": hora_inicio,
            "hora_fin": hora_fin,
            "stock_quantity": plazas,
            "stock_status": "instock",
            "precio": precio,
        }
        data["talleres"].insert(0, nuevo)
        data["generado"] = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        _ok("talleres_programados.json actualizado")
    except Exception as e:
        _aviso(f"No se pudo actualizar talleres_programados.json: {e}")


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
    _info("Cargando SKUs existentes...")
    skus_existentes = _cargar_skus_existentes(wc)
    _ok(f"{len(skus_existentes)} SKUs registrados")

    _info("Pulsa Ctrl+C en cualquier momento para cancelar.\n")

    # [1/8] Nombre
    nombre_base = _pedir_nombre()

    # [2/8] Fecha
    (fecha_raw, fecha_dt, fecha_legible, fecha_corta,
     dia_semana, dia, mes_nombre, año) = _pedir_fecha(eventos_existentes)

    # [3/8] Horario
    hora_inicio, hora_fin = _pedir_horario()

    # [4/8] Precio
    precio = _pedir_precio()

    # [5/8] Plazas
    plazas = _pedir_plazas()

    # [6/8] Categoría
    categoria = _pedir_categoria(cats, nombre_base)

    # [7/8] Imagen
    image_id = _pedir_imagen(nombre_base)

    # [8/8] Descripción extra
    desc_extra = _pedir_descripcion_extra()

    # Generar datos derivados
    datos = _generar_datos(
        nombre_base, fecha_dt, fecha_legible, fecha_corta,
        dia_semana, dia, mes_nombre, año,
        hora_inicio, hora_fin, precio, plazas,
        desc_extra, skus_existentes
    )

    # Resumen
    _mostrar_resumen(datos, fecha_raw, hora_inicio, hora_fin, precio, plazas,
                     categoria, image_id)

    respuesta = input(C.VERDE + C.BOLD +
                      "  ¿Publicar este evento en WooCommerce? (s/n): " +
                      C.RESET).strip().lower()
    print()
    if respuesta not in ("s", "si", "sí", "y", "yes"):
        _aviso("Cancelado. No se ha creado ningún evento.")
        return

    # ── Crear producto ────────────────────────────────────────────────────────
    _info("Publicando en WooCommerce...")
    payload = {
        "name":              datos["nombre_producto"],
        "type":              "simple",
        "virtual":           True,
        "status":            "publish",
        "regular_price":     str(precio),
        "tax_status":        "taxable",
        "tax_class":         "IVA 21",
        "description":       datos["descripcion"],
        "short_description": datos["short_desc"],
        "manage_stock":      True,
        "stock_quantity":    plazas,
        "backorders":        "no",
        "low_stock_amount":  3,
        "sku":               datos["sku"],
        "slug":              datos["slug"],
        "categories":        [{"id": categoria[0]}] if categoria else [],
        "meta_data": [
            {"key": "_yoast_wpseo_focuskw", "value": datos["seo_keywords"]},
            {"key": "_yoast_wpseo_title",    "value": datos["seo_title"]},
            {"key": "_yoast_wpseo_metadesc", "value": datos["seo_desc"]},
        ],
    }

    if image_id:
        payload["images"] = [{"id": image_id}]

    resp      = wc.post("products", payload)
    resultado = resp.json()

    if "id" in resultado:
        print()
        print(_linea("═"))
        _ok(C.BOLD + "¡Evento publicado correctamente!" + C.RESET)
        _info(f"ID WooCommerce : {resultado['id']}")
        _info(f"SKU            : {datos['sku']}")
        _info(f"URL            : {resultado.get('permalink', '(no disponible)')}")
        print()
        _info("Aparecerá en el email semanal del próximo lunes.")
        print(_linea("═"))

        _actualizar_talleres_json(resultado, datos["nombre_producto"], fecha_raw,
                                   hora_inicio, hora_fin, plazas, precio)
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
