"""
Envia email de alerta cuando una tarea programada falla.
Uso: python alerta_fallo.py <nombre_tarea> <exit_code> <log_file>
Reutiliza las credenciales OAuth2 de gmail/.
"""
import sys
import os
import base64
from email.mime.text import MIMEText
from pathlib import Path

ALERTA_EMAIL = "tascabarea@gmail.com"

def enviar_alerta(nombre_tarea, exit_code, log_file):
    proyecto = Path(__file__).parent
    gmail_dir = proyecto / "gmail"

    # Cargar credenciales Gmail
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    token_path = gmail_dir / "token.json"
    if not token_path.exists():
        print(f"No se puede enviar alerta: {token_path} no existe")
        return

    creds = Credentials.from_authorized_user_file(
        str(token_path),
        scopes=["https://www.googleapis.com/auth/gmail.modify"]
    )
    service = build("gmail", "v1", credentials=creds)

    # Leer ultimas 30 lineas del log
    log_tail = ""
    if log_file and os.path.exists(log_file):
        with open(log_file, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
            log_tail = "".join(lines[-30:])

    asunto = f"FALLO: {nombre_tarea} (exit code {exit_code})"
    cuerpo = (
        f"La tarea programada '{nombre_tarea}' ha fallado.\n\n"
        f"Exit code: {exit_code}\n"
        f"Log: {log_file}\n\n"
        f"--- Ultimas lineas del log ---\n{log_tail}"
    )

    msg = MIMEText(cuerpo, "plain", "utf-8")
    msg["To"] = ALERTA_EMAIL
    msg["Subject"] = asunto
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()

    service.users().messages().send(
        userId="me", body={"raw": raw}
    ).execute()
    print(f"Alerta enviada a {ALERTA_EMAIL}")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Uso: python alerta_fallo.py <nombre_tarea> <exit_code> [log_file]")
        sys.exit(1)
    nombre = sys.argv[1]
    code = sys.argv[2]
    log = sys.argv[3] if len(sys.argv) > 3 else ""
    enviar_alerta(nombre, code, log)
