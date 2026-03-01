@echo off
REM ============================================================================
REM VENTAS BAREA - EJECUCION AUTOMATICA v1.0
REM ============================================================================
REM Cada lunes a las 03:00 via Programador de Tareas
REM - Siempre: descarga ventas semana + regenera dashboard
REM - 1er lunes del mes (dia <= 7): dashboard meses cerrados + email socios
REM
REM Basado en gmail_auto.bat v1.6
REM ============================================================================

setlocal enabledelayedexpansion

REM Configuracion (rutas relativas al .bat via %~dp0)
set "PYTHON_PATH=python"
set "SCRIPT_DIR=%~dp0"
REM Quitar trailing backslash
if "%SCRIPT_DIR:~-1%"=="\" set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"
set "SCRIPT_PATH=%SCRIPT_DIR%\script_barea.py"
for %%i in ("%SCRIPT_DIR%\..") do set "PROJECT_ROOT=%%~fi"
set "LOG_PATH=%PROJECT_ROOT%\outputs\logs_barea"
set "DATE_STR=%date:~6,4%-%date:~3,2%-%date:~0,2%"
set "LOG_FILE=%LOG_PATH%\auto_%DATE_STR%.log"

REM Crear carpeta de logs si no existe
if not exist "%LOG_PATH%" mkdir "%LOG_PATH%"

REM ---- INICIO ----
echo ============================================== >> "%LOG_FILE%"
echo [%date% %time%] INICIO EJECUCION AUTOMATICA v1.0 >> "%LOG_FILE%"
echo ============================================== >> "%LOG_FILE%"

REM ============================================================================
REM ANTI-SUSPENSION: Impedir que Windows suspenda el PC durante la ejecucion
REM ============================================================================
echo [%date% %time%] Desactivando suspension del sistema... >> "%LOG_FILE%"
powercfg /change standby-timeout-ac 0 >> "%LOG_FILE%" 2>&1
powercfg /change standby-timeout-dc 0 >> "%LOG_FILE%" 2>&1
echo [%date% %time%] Suspension desactivada >> "%LOG_FILE%"

REM Espera 30s con ping (NO se pausa con suspension)
echo [%date% %time%] Esperando 30s para estabilizar sistema... >> "%LOG_FILE%"
ping -n 31 127.0.0.1 > nul 2>&1
echo [%date% %time%] Espera completada >> "%LOG_FILE%"

REM Verificar que Python existe
echo [%date% %time%] Verificando Python... >> "%LOG_FILE%"
%PYTHON_PATH% --version >> "%LOG_FILE%" 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [%date% %time%] ERROR: Python no encontrado >> "%LOG_FILE%"
    goto :restaurar
)

REM Verificar que el script existe
if not exist "%SCRIPT_PATH%" (
    echo [%date% %time%] ERROR: No se encuentra %SCRIPT_PATH% >> "%LOG_FILE%"
    goto :restaurar
)

REM Verificar conexion a internet (necesaria para APIs)
echo [%date% %time%] Verificando conexion a internet... >> "%LOG_FILE%"
ping -n 2 api.loyverse.com > nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [%date% %time%] Sin conexion a internet, reintentando en 30s... >> "%LOG_FILE%"
    ping -n 31 127.0.0.1 > nul 2>&1
    ping -n 2 api.loyverse.com > nul 2>&1
    if %ERRORLEVEL% NEQ 0 (
        echo [%date% %time%] ERROR: Sin conexion a internet >> "%LOG_FILE%"
        goto :restaurar
    )
)
echo [%date% %time%] Conexion OK >> "%LOG_FILE%"

REM ============================================================================
REM DETECTAR SI ES 1ER LUNES DEL MES (dia <= 7)
REM ============================================================================
set "EXTRA_FLAGS="
set "DAY=%date:~0,2%"
REM Quitar espacios y ceros iniciales
for /f "tokens=* delims=0 " %%a in ("%DAY%") do set "DAY_NUM=%%a"
if "%DAY_NUM%"=="" set "DAY_NUM=0"

if %DAY_NUM% LEQ 7 (
    echo [%date% %time%] 1er lunes del mes - dashboard mensual + email >> "%LOG_FILE%"
    set "EXTRA_FLAGS=--dashboard-mensual"
) else (
    echo [%date% %time%] Lunes normal - solo carga semanal >> "%LOG_FILE%"
)

REM ============================================================================
REM EJECUTAR
REM ============================================================================
echo [%date% %time%] Ejecutando: %PYTHON_PATH% "%SCRIPT_PATH%" %EXTRA_FLAGS% >> "%LOG_FILE%"
echo ---------------------------------------- >> "%LOG_FILE%"

%PYTHON_PATH% "%SCRIPT_PATH%" %EXTRA_FLAGS% >> "%LOG_FILE%" 2>&1
set EXIT_CODE=%ERRORLEVEL%

echo ---------------------------------------- >> "%LOG_FILE%"
echo [%date% %time%] Script finalizado (exit code: %EXIT_CODE%) >> "%LOG_FILE%"

if %EXIT_CODE% EQU 0 (
    echo [%date% %time%] EXITO: Ejecucion completada correctamente >> "%LOG_FILE%"
) else (
    echo [%date% %time%] ERROR: Fallo con codigo %EXIT_CODE% >> "%LOG_FILE%"
    echo [%date% %time%] Enviando alerta por email... >> "%LOG_FILE%"
    %PYTHON_PATH% "%PROJECT_ROOT%\alerta_fallo.py" "Ventas_Barea_Semanal" "%EXIT_CODE%" "%LOG_FILE%" >> "%LOG_FILE%" 2>&1
)

REM ============================================================================
REM RESTAURAR SUSPENSION
REM ============================================================================
:restaurar
echo [%date% %time%] Restaurando suspension del sistema... >> "%LOG_FILE%"
powercfg /change standby-timeout-ac 30 >> "%LOG_FILE%" 2>&1
powercfg /change standby-timeout-dc 15 >> "%LOG_FILE%" 2>&1
echo [%date% %time%] Suspension restaurada >> "%LOG_FILE%"

echo [%date% %time%] FIN >> "%LOG_FILE%"
echo ============================================== >> "%LOG_FILE%"

endlocal
