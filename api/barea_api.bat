@echo off
REM barea_api.bat — Arranca el servidor FastAPI de Barea
REM Registrado en Task Scheduler: "Al iniciar sesión del usuario"

cd /d "C:\_ARCHIVOS\TRABAJO\Facturas\gestion-facturas"

set LOGFILE=outputs\api_startup.log
echo [%date% %time%] Arrancando Barea API... >> %LOGFILE%
python -m api.server >> %LOGFILE% 2>&1
