@echo off
:: alta_evento.bat — Dar de alta un evento/taller/cata en WooCommerce
:: Uso: doble clic (funciona desde cualquier ubicacion, incluido acceso directo en escritorio)
cd /d "%~dp0"
title Alta de Evento — Barea
python alta_evento.py
echo.
pause
