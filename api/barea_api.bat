@echo off
REM barea_api.bat — Arranca el servidor FastAPI de Barea
REM Usar en Task Scheduler: "Al iniciar sesión" o manualmente

cd /d "C:\_ARCHIVOS\TRABAJO\Facturas\gestion-facturas"
echo [%date% %time%] Arrancando Barea API...
python -m api.server
pause
