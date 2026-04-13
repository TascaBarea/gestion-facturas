"""
ventas_semana/email_sender.py — Envío de emails con dashboards y PDFs.

Extrae la lógica de email de generar_dashboard.py para reducir tamaño
y facilitar mantenimiento.
"""

import base64
import os
import sys
from datetime import datetime
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email import encoders
from pathlib import Path

# Asegurar directorio raíz en sys.path (para nucleo/)
_ROOT = str(Path(__file__).resolve().parent.parent)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from nucleo.utils import fmt_eur

# ── Config email (import seguro) ─────────────────────────────────────────────
try:
    from config.datos_sensibles import (EMAILS_FULL, EMAILS_COMES_ONLY)
except ImportError:
    EMAILS_FULL = []
    EMAILS_COMES_ONLY = []

GITHUB_PAGES_URL = "https://tascabarea.github.io/gestion-facturas"


def _conectar_gmail():
    """Conecta con Gmail API y devuelve service, o None si falla."""
    try:
        import importlib.util
        _auth_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                  "..", "gmail", "auth_manager.py")
        spec = importlib.util.spec_from_file_location("gmail_auth_manager", _auth_path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod.get_gmail_service()
    except ImportError:
        print("  Aviso: google-auth/google-api-python-client no instalados")
        return None
    except (FileNotFoundError, RuntimeError) as e:
        print(f"  Aviso: {e}")
        return None


def _adjuntar_archivo(message, path, filename,
                      mime_type="application", mime_subtype="octet-stream"):
    """Adjunta un archivo a un MIMEMultipart."""
    if not path or not os.path.exists(path):
        return
    with open(path, "rb") as f:
        adj = MIMEBase(mime_type, mime_subtype)
        adj.set_payload(f.read())
        encoders.encode_base64(adj)
        adj.add_header("Content-Disposition", "attachment", filename=filename)
        message.attach(adj)


def _enviar_mensaje(service, email_dest, asunto, html_body, adjuntos):
    """Envia un email con adjuntos via Gmail API."""
    message = MIMEMultipart("mixed")
    message["To"] = email_dest
    message["Subject"] = asunto
    message.attach(MIMEText(html_body, "html"))
    for path, filename, mtype, msubtype in adjuntos:
        _adjuntar_archivo(message, path, filename, mtype, msubtype)
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    service.users().messages().send(userId="me", body={"raw": raw}).execute()


def _kpis_variacion_html(data_dict, year, mes, color):
    """Genera HTML de KPIs para un negocio."""
    d_mes = data_dict.get(year, {}).get("mensual", {}).get(str(mes), {})
    euros = d_mes.get("euros", 0)
    tickets = d_mes.get("tickets", 0)
    prom = d_mes.get("prom_ticket", 0)

    year_ant = str(int(year) - 1)
    d_ant = data_dict.get(year_ant, {}).get("mensual", {}).get(str(mes), {})
    euros_ant = d_ant.get("euros", 0)
    var_html = ""
    if euros_ant > 0:
        var = (euros - euros_ant) / euros_ant * 100
        sign = "+" if var >= 0 else ""
        vc = "#155724" if var >= 0 else "#721C24"
        var_html = f'<span style="color:{vc};font-weight:bold">{sign}{var:.1f}%</span> vs {year_ant}'

    kpi_html = f"""
        <table style="width:100%;border-collapse:collapse;margin-bottom:8px">
          <tr>
            <td style="padding:10px;background:white;border:1px solid #eee;text-align:center;width:33%">
              <div style="font-size:10px;color:#888;text-transform:uppercase">Ventas</div>
              <div style="font-size:20px;font-weight:bold;color:{color}">{fmt_eur(euros, 0)}</div>
            </td>
            <td style="padding:10px;background:white;border:1px solid #eee;text-align:center;width:33%">
              <div style="font-size:10px;color:#888;text-transform:uppercase">Tickets</div>
              <div style="font-size:20px;font-weight:bold;color:{color}">{tickets:,}</div>
            </td>
            <td style="padding:10px;background:white;border:1px solid #eee;text-align:center;width:33%">
              <div style="font-size:10px;color:#888;text-transform:uppercase">Ticket medio</div>
              <div style="font-size:20px;font-weight:bold;color:{color}">{fmt_eur(prom)}</div>
            </td>
          </tr>
        </table>
        {f'<div style="font-size:12px;margin-bottom:12px">{var_html}</div>' if var_html else ''}"""
    return kpi_html


def enviar_email_dashboard(D, RAW, path_comes, path_tasca,
                           path_pdf=None, path_pdf_comes=None,
                           year_list=None, meses_full=None):
    """Envia emails: completo a EMAILS_FULL, solo Comestibles a EMAILS_COMES_ONLY."""
    service = _conectar_gmail()
    if not service:
        return

    if year_list is None:
        year_list = ["2025", "2026"]
    if meses_full is None:
        from nucleo.utils import MESES_FULL
        meses_full = MESES_FULL

    mes_cerrado = datetime.now().month - 1
    year_actual = year_list[-1]
    if mes_cerrado < 1:
        mes_cerrado = 12
        year_actual = str(int(year_actual) - 1)
    mes_nombre = meses_full[mes_cerrado - 1]
    fecha_gen = datetime.now().strftime('%d/%m/%Y %H:%M')

    url_comes = GITHUB_PAGES_URL + "comestibles.html" if GITHUB_PAGES_URL else ""
    url_tasca = GITHUB_PAGES_URL + "tasca.html" if GITHUB_PAGES_URL else ""

    # ── EMAIL COMPLETO (Tasca + Comestibles) → EMAILS_FULL ──
    tasca_kpis = _kpis_variacion_html(RAW, year_actual, mes_cerrado, "#8B6914")
    comes_kpis = _kpis_variacion_html(D, year_actual, mes_cerrado, "#2E7D32")

    links_full = ""
    if url_comes:
        links_full = (
            f'<div style="margin:16px 0;text-align:center">'
            f'<a href="{url_comes}" style="background:#2E7D32;color:white;'
            f'padding:10px 20px;border-radius:6px;text-decoration:none;'
            f'font-weight:bold;font-size:13px;display:inline-block;margin:4px">'
            f'Dashboard Comestibles</a>'
            f'<a href="{url_tasca}" style="background:#8B6914;color:white;'
            f'padding:10px 20px;border-radius:6px;text-decoration:none;'
            f'font-weight:bold;font-size:13px;display:inline-block;margin:4px">'
            f'Dashboard Tasca</a></div>'
        )

    html_full = f"""
    <html>
    <body style="font-family:Arial,sans-serif;font-size:14px;color:#333;max-width:600px;margin:0 auto">
      <div style="background:#1a1a1a;color:#f0ece4;padding:20px;border-radius:8px 8px 0 0;text-align:center">
        <h2 style="margin:0;font-size:20px;color:#e8c97a">Barea</h2>
        <p style="margin:4px 0 0;color:#9a9488;font-size:12px">
          Cómo nos ha ido en {mes_nombre.lower()} {year_actual}</p>
      </div>
      <div style="background:#f8f9fa;padding:20px;border:1px solid #ddd">
        <h3 style="margin:0 0 12px;color:#8B6914;font-size:16px">Tasca</h3>
        {tasca_kpis}
        <h3 style="margin:12px 0 12px;color:#2E7D32;font-size:16px">Comestibles</h3>
        {comes_kpis}
        {links_full}
        <div style="background:#e8f4fd;border:1px solid #bee5eb;border-radius:6px;
                    padding:10px 14px;margin:12px 0;font-size:12px;color:#0c5460">
          El informe detallado va adjunto en PDF. Los dashboards interactivos
          se pueden abrir en el navegador.
        </div>
      </div>
      <div style="padding:10px;font-size:10px;color:#999;text-align:center">
        Generado el {fecha_gen}
      </div>
    </body>
    </html>
    """

    asunto_full = f"Barea - Informe {mes_nombre} {year_actual}"
    adjuntos_full = [
        (path_pdf, os.path.basename(path_pdf) if path_pdf else "", "application", "pdf"),
        (path_comes, "dashboard_comestibles.html", "text", "html"),
        (path_tasca, "dashboard_tasca.html", "text", "html"),
    ]

    for email_dest in EMAILS_FULL:
        _enviar_mensaje(service, email_dest, asunto_full, html_full, adjuntos_full)

    if EMAILS_FULL:
        print(f"  Email completo enviado a: {', '.join(EMAILS_FULL)}")

    # ── EMAIL SOLO COMESTIBLES → EMAILS_COMES_ONLY ──
    if not EMAILS_COMES_ONLY:
        return

    link_comes = ""
    if url_comes:
        link_comes = (
            f'<div style="margin:16px 0;text-align:center">'
            f'<a href="{url_comes}" style="background:#2E7D32;color:white;'
            f'padding:10px 20px;border-radius:6px;text-decoration:none;'
            f'font-weight:bold;font-size:13px;display:inline-block">'
            f'Dashboard Comestibles</a></div>'
        )

    html_comes = f"""
    <html>
    <body style="font-family:Arial,sans-serif;font-size:14px;color:#333;max-width:600px;margin:0 auto">
      <div style="background:#0c0f0e;color:#a8e8c0;padding:20px;border-radius:8px 8px 0 0;text-align:center">
        <h2 style="margin:0;font-size:20px">Comestibles Barea</h2>
        <p style="margin:4px 0 0;color:#8aa898;font-size:12px">
          Cómo nos ha ido en {mes_nombre.lower()} {year_actual}</p>
      </div>
      <div style="background:#f8f9fa;padding:20px;border:1px solid #ddd">
        <h3 style="margin:0 0 12px;color:#2E7D32;font-size:16px">Resumen {mes_nombre}</h3>
        {comes_kpis}
        {link_comes}
        <div style="background:#e8f4fd;border:1px solid #bee5eb;border-radius:6px;
                    padding:10px 14px;margin:12px 0;font-size:12px;color:#0c5460">
          El informe detallado va adjunto en PDF. El dashboard interactivo
          se puede abrir en el navegador.
        </div>
      </div>
      <div style="padding:10px;font-size:10px;color:#999;text-align:center">
        Generado el {fecha_gen}
      </div>
    </body>
    </html>
    """

    asunto_comes = f"Comestibles Barea - Informe {mes_nombre} {year_actual}"
    adjuntos_comes = [
        (path_pdf_comes, os.path.basename(path_pdf_comes) if path_pdf_comes else "",
         "application", "pdf"),
        (path_comes, "dashboard_comestibles.html", "text", "html"),
    ]

    for email_dest in EMAILS_COMES_ONLY:
        _enviar_mensaje(service, email_dest, asunto_comes, html_comes, adjuntos_comes)

    print(f"  Email Comestibles enviado a: {', '.join(EMAILS_COMES_ONLY)}")
