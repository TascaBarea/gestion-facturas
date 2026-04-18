# -*- coding: utf-8 -*-
"""
Módulo GMAIL - Gestión de facturas
TASCA BAREA S.L.L.

Versión: 1.1
"""

from .gmail_config import *
try:
    from .auth import GmailConnection, test_conexion
except ImportError:
    # auth.py requiere config_local (credenciales IMAP) — no disponible en producción VPS (usa OAuth2)
    GmailConnection = None
    test_conexion = None
