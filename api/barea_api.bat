@echo off
REM barea_api.bat — Arranca el servidor FastAPI de Barea con watchdog
REM Registrado en Task Scheduler: "Al iniciar sesión del usuario"
REM Si el proceso muere, espera 10s y reinicia automáticamente.

cd /d "C:\_ARCHIVOS\TRABAJO\Facturas\gestion-facturas"

set LOGFILE=outputs\api_startup.log

:loop
echo [%date% %time%] Arrancando Barea API... >> %LOGFILE%
python -m api.server >> %LOGFILE% 2>&1
set EXIT_CODE=%ERRORLEVEL%

echo [%date% %time%] API terminó con código %EXIT_CODE% >> %LOGFILE%

REM Si salió con código 0 (shutdown limpio), no reiniciar
if %EXIT_CODE%==0 (
    echo [%date% %time%] Shutdown limpio, no reiniciando. >> %LOGFILE%
    goto end
)

echo [%date% %time%] Reiniciando en 10 segundos... >> %LOGFILE%
timeout /t 10 /nobreak >nul
goto loop

:end
echo [%date% %time%] Barea API finalizado. >> %LOGFILE%
