#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de limpieza ONE-SHOT: mueve todos los emails pendientes en FACTURAS
a FACTURAS_PROCESADAS y establece el cursor temporal en el JSON.

Ejecutar UNA SOLA VEZ antes de la primera ejecución con v1.13.
Después se puede borrar este script.

Uso: python limpiar_emails_viejos.py
"""
import os
import sys
import json
from datetime import datetime

# Importar directamente del módulo gmail.py (no del paquete gmail/)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from gmail import GmailClient, ControlDuplicados, CONFIG


def main():
    print("=" * 60)
    print("LIMPIEZA DE EMAILS VIEJOS EN FACTURAS")
    print("=" * 60)

    # Conectar Gmail
    credentials_path = os.path.join(CONFIG.GMAIL_PATH, "credentials.json")
    token_path = os.path.join(CONFIG.GMAIL_PATH, "token.json")

    gmail = GmailClient(credentials_path, token_path)
    gmail.conectar()
    print("Gmail conectado.")

    # Obtener todos los emails en FACTURAS (sin filtro de fecha)
    emails = gmail.obtener_emails_pendientes(max_results=500)
    print(f"\nEmails pendientes en FACTURAS: {len(emails)}")

    if not emails:
        print("No hay emails pendientes. Nada que limpiar.")
    else:
        # Confirmar
        respuesta = input(f"\nMover {len(emails)} emails a PROCESADAS? (s/n): ").strip().lower()
        if respuesta != 's':
            print("Cancelado.")
            return

        # Cargar control de duplicados
        control = ControlDuplicados(CONFIG.JSON_PATH)

        # Mover cada email
        movidos = 0
        errores = 0
        for email in emails:
            email_id = email['id']
            asunto = email.get('subject', '')[:50]
            try:
                gmail.mover_a_procesados_y_marcar_leido(email_id)
                # Registrar como visto si no estaba ya
                if not control.email_procesado(email_id):
                    control.registrar_email_visto(email_id, "limpieza_pre_v1.13")
                movidos += 1
                print(f"  OK: {asunto}")
            except Exception as e:
                errores += 1
                print(f"  ERROR: {asunto} - {e}")

        control.guardar()
        print(f"\nMovidos: {movidos}, Errores: {errores}")

    # Establecer cursor temporal
    control = ControlDuplicados(CONFIG.JSON_PATH)
    ahora = datetime.now().isoformat()
    control.set_ultima_ejecucion(ahora)
    control.guardar()
    print(f"\nCursor temporal establecido: {ahora}")
    print("Listo. A partir de ahora gmail.py v1.13 solo procesara emails nuevos.")


if __name__ == "__main__":
    main()
