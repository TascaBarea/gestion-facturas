#!/usr/bin/env python3
"""
Script ONE-SHOT: Regenera token.json incluyendo el scope de Business Profile.
Abre el navegador para re-autorizar. Ejecutar UNA SOLA VEZ.

Uso: python renovar_token_business.py
"""
import os
import json

from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CREDENTIALS_PATH = os.path.join(SCRIPT_DIR, "credentials.json")
TOKEN_PATH = os.path.join(SCRIPT_DIR, "token.json")

# Todos los scopes que necesita el proyecto
SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/business.manage",
    "https://www.googleapis.com/auth/drive.file",
]

def main():
    print("=" * 50)
    print("RENOVAR TOKEN CON SCOPES BUSINESS + DRIVE")
    print("=" * 50)

    # Backup del token actual
    if os.path.exists(TOKEN_PATH):
        backup = TOKEN_PATH + ".backup"
        with open(TOKEN_PATH) as f:
            data = f.read()
        with open(backup, "w") as f:
            f.write(data)
        print(f"Backup guardado en {backup}")

    # Forzar re-autorización con todos los scopes
    print("\nSe abrirá el navegador para autorizar.")
    print("Inicia sesión con la cuenta de tascabarea@gmail.com")
    print("y acepta TODOS los permisos.\n")

    flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
    creds = flow.run_local_server(port=0)

    # Guardar nuevo token
    with open(TOKEN_PATH, "w") as f:
        f.write(creds.to_json())

    print(f"\nToken guardado en {TOKEN_PATH}")
    print(f"Scopes: {creds.scopes}")
    print("Listo.")


if __name__ == "__main__":
    main()
