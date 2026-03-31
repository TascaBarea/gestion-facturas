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
    try:
        import importlib.util
        _auth_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                  "gmail", "auth_manager.py")
        spec = importlib.util.spec_from_file_location("gmail_auth_manager", _auth_path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        # gmail.modify (en el token) ya permite enviar emails
        service = mod.get_gmail_service()
    except (FileNotFoundError, RuntimeError) as e:
        print(f"No se puede enviar alerta: {e}")
        return
    except Exception as e:
        print(f"Error de autenticación: {e}")
        return

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
