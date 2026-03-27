"""
dia_tickets.py — Descarga tickets de Dia.es y los sube a Dropbox.

Usa la API interna de Dia con autenticación por cookies.
Requiere login manual previo para obtener el token JWT (customer_access).

Flujo:
1. Login en dia.es (Playwright con Edge real)
2. Capturar cookie customer_access (JWT)
3. Paginar API /tickets/reduced para listar tickets
4. Descargar detalle de cada ticket nuevo (anti-duplicación por código único)
5. (Futuro) Subir a Dropbox

Anti-duplicación:
- Cada ticket se identifica por ticket_unique_code (ej: ES13908039000107820260324122158)
- Registro en datos/dia_tickets/_registro.json con todos los códigos descargados
- Doble check: registro + existencia del fichero JSON

Uso:
    python scripts/dia_tickets.py              # descarga tickets nuevos
    python scripts/dia_tickets.py --all        # descarga todos (re-descarga existentes)
    python scripts/dia_tickets.py --list       # solo lista tickets sin descargar
    python scripts/dia_tickets.py --login      # forzar login (renovar sesión)
    python scripts/dia_tickets.py --stats      # estadísticas de tickets descargados
"""

import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("dia_tickets")

# ── Configuración ─────────────────────────────────────────────────────────────

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TICKETS_DIR = os.path.join(PROJECT_ROOT, "datos", "dia_tickets")
REGISTRO_FILE = os.path.join(TICKETS_DIR, "_registro.json")
TOKEN_FILE = os.path.join(PROJECT_ROOT, "datos", "dia_session.json")

API_BASE = "https://www.dia.es/api/v3/eservice-back"
TICKETS_URL = f"{API_BASE}/customer/current/tickets/reduced"
TICKET_DETAIL_URL = f"{API_BASE}/customer/current/tickets"
PAGE_SIZE = 20


# ── Registro anti-duplicación ─────────────────────────────────────────────────

def _cargar_registro() -> dict:
    """Carga el registro de tickets descargados.

    Formato: {ticket_unique_code: {fecha, total, descargado, fichero}}
    """
    if not os.path.exists(REGISTRO_FILE):
        return {}
    try:
        with open(REGISTRO_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def _guardar_registro(registro: dict):
    """Guarda el registro de tickets descargados."""
    os.makedirs(TICKETS_DIR, exist_ok=True)
    with open(REGISTRO_FILE, "w", encoding="utf-8") as f:
        json.dump(registro, f, indent=2, ensure_ascii=False)


def _ticket_ya_descargado(code: str, registro: dict) -> bool:
    """Comprueba si un ticket ya fue descargado (registro + fichero)."""
    if code in registro:
        # Verificar que el fichero existe
        fichero = registro[code].get("fichero", "")
        if fichero and os.path.exists(os.path.join(TICKETS_DIR, fichero)):
            return True
        # Fichero en registro pero no existe → marcar para re-descarga
        return False
    # Comprobar si existe el fichero aunque no esté en registro
    if os.path.exists(os.path.join(TICKETS_DIR, f"{code}.json")):
        return True
    return False


# ── Sesión y autenticación ────────────────────────────────────────────────────

def _load_session() -> dict | None:
    """Carga token de sesión guardado."""
    if not os.path.exists(TOKEN_FILE):
        return None
    try:
        with open(TOKEN_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def _save_session(session_data: dict):
    """Guarda token de sesión."""
    os.makedirs(os.path.dirname(TOKEN_FILE), exist_ok=True)
    with open(TOKEN_FILE, "w", encoding="utf-8") as f:
        json.dump(session_data, f, indent=2)
    logger.info("Sesión guardada en %s", TOKEN_FILE)


def login_playwright() -> dict | None:
    """Login en dia.es usando Edge real. Captura cookies de sesión.

    Abre Edge con perfil limpio, hace login. Si el auto-login falla
    (anti-bot de Dia), permite login manual y captura el JWT.
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        logger.error("Playwright no instalado. Ejecutar: pip install playwright && playwright install chromium")
        return None

    from config.datos_sensibles import DIA_EMAIL, DIA_PASSWORD

    logger.info("Iniciando login en dia.es...")

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            channel="msedge",
            args=["--disable-blink-features=AutomationControlled"],
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36 Edg/134.0.0.0",
            viewport={"width": 1366, "height": 768},
            locale="es-ES",
        )
        context.add_init_script("Object.defineProperty(navigator, 'webdriver', { get: () => false });")
        page = context.new_page()

        # Capturar cookies de respuesta
        captured_jwt = None
        captured_session = None
        captured_customer_code = None

        def on_response(response):
            nonlocal captured_jwt, captured_session, captured_customer_code
            for header_name, header_value in response.headers_array():
                if header_name.lower() == "set-cookie":
                    if "customer_access=" in header_value:
                        token = header_value.split("customer_access=")[1].split(";")[0]
                        if len(token) > 50:
                            captured_jwt = token
                    elif "session_id=" in header_value:
                        captured_session = header_value.split("session_id=")[1].split(";")[0]
                    elif "customer_code=" in header_value:
                        captured_customer_code = header_value.split("customer_code=")[1].split(";")[0]

        page.on("response", on_response)

        # Ir a dia.es
        try:
            page.goto("https://www.dia.es", timeout=60000)
        except Exception:
            pass
        page.wait_for_timeout(3000)

        # Aceptar cookies
        try:
            page.locator('button:has-text("Aceptar")').first.click(timeout=5000)
            page.wait_for_timeout(1000)
        except Exception:
            pass

        # Ir al login
        try:
            page.locator('a:has-text("Iniciar sesión"), a[href*="login"]').first.click()
            page.wait_for_timeout(5000)
        except Exception:
            pass

        # Email
        email_input = page.locator('input[type="email"], input[name="email"], input[placeholder*="mail"], input[id*="email"]')
        if email_input.count() == 0:
            email_input = page.locator("input[type='text'], input:not([type])")
        if email_input.count() > 0:
            email_input.first.click()
            page.wait_for_timeout(500)
            email_input.first.type(DIA_EMAIL, delay=80)
            email_input.first.press("Tab")
            page.wait_for_timeout(2000)

        # Botón Continuar (email)
        try:
            btn = page.locator('button:not([disabled]):has-text("Continuar")')
            btn.first.wait_for(state="visible", timeout=10000)
            btn.first.click()
            page.wait_for_timeout(4000)
        except Exception:
            email_input.first.press("Enter")
            page.wait_for_timeout(4000)

        # Contraseña
        pwd_input = page.locator('input[type="password"]')
        if pwd_input.count() > 0:
            pwd_input.first.click()
            page.wait_for_timeout(500)
            pwd_input.first.fill(DIA_PASSWORD)
            page.wait_for_timeout(1000)

            # Botón Continuar (password)
            try:
                btn_pwd = page.locator('button:not([disabled]):has-text("Continuar")')
                btn_pwd.first.click()
                page.wait_for_timeout(8000)
            except Exception:
                pwd_input.first.press("Enter")
                page.wait_for_timeout(8000)

        # Verificar login
        if captured_jwt:
            logger.info("Login exitoso. JWT capturado.")
            session_data = {
                "customer_access": captured_jwt,
                "session_id": captured_session or "",
                "customer_code": captured_customer_code or "",
                "timestamp": datetime.now().isoformat(),
            }
            browser.close()
            return session_data
        else:
            logger.warning("Login automático falló (anti-bot de Dia).")
            logger.info("Haz login MANUALMENTE en la ventana del navegador.")
            logger.info("Navega a 'Mi cuenta' > 'Tickets' cuando estés logueado.")

            # Esperar hasta 120s a que aparezca el JWT
            for i in range(24):
                page.wait_for_timeout(5000)
                if captured_jwt:
                    break

            if captured_jwt:
                logger.info("JWT capturado tras login manual.")
                session_data = {
                    "customer_access": captured_jwt,
                    "session_id": captured_session or "",
                    "customer_code": captured_customer_code or "",
                    "timestamp": datetime.now().isoformat(),
                }
                browser.close()
                return session_data
            else:
                logger.error("No se pudo obtener el JWT. Abortando.")
                browser.close()
                return None


def _build_session(session_data: dict) -> requests.Session:
    """Construye sesión HTTP con cookies de Dia."""
    s = requests.Session()
    s.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36 Edg/134.0.0.0",
        "Accept": "application/json",
        "Accept-Language": "es-ES,es;q=0.9",
        "Referer": "https://www.dia.es/my-account/tickets",
        "x-locale": "es",
        "x-requested-with": "XMLHttpRequest",
    })
    s.cookies.set("customer_access", session_data["customer_access"], domain="www.dia.es")
    if session_data.get("session_id"):
        s.cookies.set("session_id", session_data["session_id"], domain="www.dia.es")
    if session_data.get("customer_code"):
        s.cookies.set("customer_code", session_data["customer_code"], domain="www.dia.es")
    return s


# ── API de tickets ─────────────────────────────────────────────────────────────

def listar_tickets(session: requests.Session, max_tickets: int = 500) -> list[dict]:
    """Lista todos los tickets via API paginada."""
    tickets = []
    offset = 0

    while offset < max_tickets:
        url = f"{TICKETS_URL}?offset={offset}&page_size={PAGE_SIZE}"
        r = session.get(url, timeout=15)

        if r.status_code == 401:
            logger.error("Sesión expirada (401). Ejecutar con --login para renovar.")
            return tickets
        if r.status_code != 200:
            logger.error("Error %d en %s: %s", r.status_code, url, r.text[:200])
            break

        data = r.json()
        batch = data.get("tickets", [])
        if not batch:
            break

        tickets.extend(batch)
        logger.info("  Tickets %d-%d descargados (%d en lote)",
                     offset + 1, offset + len(batch), len(batch))

        if len(batch) < PAGE_SIZE:
            break
        offset += PAGE_SIZE

    logger.info("Total tickets en Dia: %d", len(tickets))
    return tickets


def descargar_ticket_detalle(session: requests.Session, ticket: dict) -> dict | None:
    """Descarga el detalle completo de un ticket (con líneas de productos).

    Endpoint: /tickets/{ticket_id}?begin=...&business=...&country=...&pos=...&store=...
    Devuelve: amount, corporate (items + taxes), header, invoice, payment, tef
    """
    params = ticket.get("detail_params", {})
    if not params:
        return None

    ticket_id = params.get("ticket", "")
    query_params = {k: v for k, v in params.items() if k != "ticket"}
    query = "&".join(f"{k}={v}" for k, v in query_params.items())
    url = f"{TICKET_DETAIL_URL}/{ticket_id}?{query}"

    r = session.get(url, timeout=15)
    if r.status_code == 401:
        logger.error("Sesión expirada durante descarga de detalle.")
        return None
    if r.status_code != 200:
        logger.warning("Error %d descargando detalle de ticket %s",
                       r.status_code, ticket.get("ticket_unique_code", "?"))
        return None

    return r.json()


def guardar_ticket(ticket: dict, detalle: dict | None, registro: dict) -> str:
    """Guarda ticket (resumen + detalle) como JSON y actualiza registro."""
    os.makedirs(TICKETS_DIR, exist_ok=True)
    code = ticket["ticket_unique_code"]
    fichero = f"{code}.json"
    data = {
        "resumen": ticket,
        "detalle": detalle,
        "descargado": datetime.now().isoformat(),
    }
    path = os.path.join(TICKETS_DIR, fichero)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    # Actualizar registro
    n_items = 0
    if detalle and detalle.get("corporate"):
        n_items = len(detalle["corporate"].get("items", []))

    registro[code] = {
        "fecha": ticket.get("submitted_date", "")[:10],
        "total": ticket.get("total_amount", 0),
        "tienda": ticket.get("store_info", {}).get("address", ""),
        "items": n_items,
        "fichero": fichero,
        "descargado": datetime.now().isoformat(),
    }

    return path


def mostrar_stats(registro: dict):
    """Muestra estadísticas de tickets descargados."""
    if not registro:
        logger.info("No hay tickets en el registro.")
        return

    totales = [r["total"] for r in registro.values()]
    fechas = sorted(r["fecha"] for r in registro.values() if r.get("fecha"))

    logger.info("=== Estadísticas de tickets Dia ===")
    logger.info("  Total tickets: %d", len(registro))
    logger.info("  Período: %s a %s", fechas[0] if fechas else "?", fechas[-1] if fechas else "?")
    logger.info("  Gasto total: %.2f€", sum(totales))
    logger.info("  Ticket medio: %.2f€", sum(totales) / len(totales) if totales else 0)
    logger.info("  Ticket máximo: %.2f€", max(totales) if totales else 0)
    logger.info("  Ticket mínimo: %.2f€", min(totales) if totales else 0)

    # Por tienda
    tiendas = {}
    for r in registro.values():
        t = r.get("tienda", "Desconocida")
        if t not in tiendas:
            tiendas[t] = {"n": 0, "total": 0}
        tiendas[t]["n"] += 1
        tiendas[t]["total"] += r.get("total", 0)

    logger.info("  --- Por tienda ---")
    for tienda, info in sorted(tiendas.items(), key=lambda x: -x[1]["total"]):
        logger.info("    %s: %d tickets, %.2f€", tienda, info["n"], info["total"])


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Descarga tickets de Dia.es")
    parser.add_argument("--all", action="store_true", help="Re-descargar todos los tickets")
    parser.add_argument("--list", action="store_true", help="Solo listar tickets sin descargar")
    parser.add_argument("--login", action="store_true", help="Forzar login (renovar sesión)")
    parser.add_argument("--stats", action="store_true", help="Mostrar estadísticas")
    args = parser.parse_args()

    # Stats: no necesita sesión
    if args.stats:
        registro = _cargar_registro()
        mostrar_stats(registro)
        return

    # 1. Obtener sesión
    session_data = _load_session()
    if not session_data or args.login:
        logger.info("Sesión no encontrada o forzando login...")
        session_data = login_playwright()
        if not session_data:
            logger.error("No se pudo hacer login. Abortando.")
            sys.exit(1)
        _save_session(session_data)

    http = _build_session(session_data)

    # 2. Listar tickets
    logger.info("Listando tickets de Dia...")
    tickets = listar_tickets(http)

    if not tickets:
        logger.warning("No se encontraron tickets (sesión expirada?).")
        sys.exit(1)

    # Mostrar resumen
    for t in tickets[:5]:
        fecha = t.get("submitted_date", "")[:10]
        total = t.get("total_amount", 0)
        tienda = t.get("store_info", {}).get("address", "?")
        logger.info("  %s | %7.2f€ | %s", fecha, total, tienda)
    if len(tickets) > 5:
        logger.info("  ... y %d más", len(tickets) - 5)

    if args.list:
        return

    # 3. Filtrar tickets nuevos (anti-duplicación)
    registro = _cargar_registro()

    if args.all:
        nuevos = tickets
        logger.info("Modo --all: re-descargando todos los tickets.")
    else:
        nuevos = [
            t for t in tickets
            if not _ticket_ya_descargado(t["ticket_unique_code"], registro)
        ]

    if not nuevos:
        logger.info("No hay tickets nuevos. Ya tienes %d tickets descargados.", len(registro))
        return

    logger.info("Descargando %d tickets nuevos (ya descargados: %d)...",
                len(nuevos), len(registro))
    descargados = 0
    errores = 0

    for t in nuevos:
        code = t["ticket_unique_code"]
        fecha = t.get("submitted_date", "")[:10]
        total = t.get("total_amount", 0)

        # Descargar detalle
        detalle = descargar_ticket_detalle(http, t)
        if detalle is None and http.cookies.get("customer_access") is None:
            logger.error("Sesión perdida. Abortando descarga.")
            break

        path = guardar_ticket(t, detalle, registro)
        descargados += 1
        if detalle is None:
            errores += 1

        n_items = 0
        if detalle and detalle.get("corporate"):
            n_items = len(detalle["corporate"].get("items", []))

        logger.info("  [%d/%d] %s | %6.2f€ | %d items → %s",
                     descargados, len(nuevos), fecha, total, n_items,
                     os.path.basename(path))

        time.sleep(0.5)  # ser amable con el servidor

    # Guardar registro actualizado
    _guardar_registro(registro)

    logger.info("Descarga completada: %d nuevos, %d errores, %d total en registro.",
                descargados, errores, len(registro))


if __name__ == "__main__":
    main()
