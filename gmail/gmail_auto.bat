@echo off
REM ============================================================================
REM GMAIL FACTURAS - EJECUCION AUTOMATICA v1.7
REM ============================================================================
REM Cada viernes a las 03:00 via Programador de Tareas
REM
REM v1.7: curl HTTPS en vez de ping, espera 60s, 3 reintentos, alerta en bat
REM v1.6: powercfg anti-suspension, ping wait
REM ============================================================================

setlocal enabledelayedexpansion

REM Configuracion (rutas relativas al .bat via %~dp0)
set "PYTHON_PATH=python"
set "SCRIPT_DIR=%~dp0"
REM Quitar trailing backslash
if "%SCRIPT_DIR:~-1%"=="\" set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"
set "SCRIPT_PATH=%SCRIPT_DIR%\gmail.py"
for %%i in ("%SCRIPT_DIR%\..") do set "PROJECT_ROOT=%%~fi"
set "LOG_PATH=%PROJECT_ROOT%\outputs\logs_gmail"
set "DATE_STR=%date:~6,4%-%date:~3,2%-%date:~0,2%"
set "LOG_FILE=%LOG_PATH%\auto_%DATE_STR%.log"
set "EXIT_CODE=0"

REM Crear carpeta de logs si no existe
if not exist "%LOG_PATH%" mkdir "%LOG_PATH%"

REM ---- INICIO ----
echo ============================================== >> "%LOG_FILE%"
echo [%date% %time%] INICIO EJECUCION AUTOMATICA v1.7 >> "%LOG_FILE%"
echo ============================================== >> "%LOG_FILE%"

REM ============================================================================
REM ANTI-SUSPENSION: Impedir que Windows suspenda el PC durante la ejecucion
REM ============================================================================
echo [%date% %time%] Desactivando suspension del sistema... >> "%LOG_FILE%"
powercfg /change standby-timeout-ac 0 >> "%LOG_FILE%" 2>&1
powercfg /change standby-timeout-dc 0 >> "%LOG_FILE%" 2>&1
echo [%date% %time%] Suspension desactivada >> "%LOG_FILE%"

REM Espera 60s para estabilizar sistema y WiFi (NO se pausa con suspension)
echo [%date% %time%] Esperando 60s para estabilizar sistema y WiFi... >> "%LOG_FILE%"
ping -n 61 127.0.0.1 > nul 2>&1
echo [%date% %time%] Espera completada >> "%LOG_FILE%"

REM Verificar que Python existe
echo [%date% %time%] Verificando Python... >> "%LOG_FILE%"
%PYTHON_PATH% --version >> "%LOG_FILE%" 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [%date% %time%] ERROR: Python no encontrado en PATH >> "%LOG_FILE%"
    set "EXIT_CODE=2"
    goto :restaurar
)
echo [%date% %time%] Python OK >> "%LOG_FILE%"

REM Verificar que el script existe
if not exist "%SCRIPT_PATH%" (
    echo [%date% %time%] ERROR: No se encuentra %SCRIPT_PATH% >> "%LOG_FILE%"
    set "EXIT_CODE=3"
    goto :restaurar
)
echo [%date% %time%] Script encontrado OK >> "%LOG_FILE%"

REM Verificar credenciales
if not exist "%SCRIPT_DIR%\credentials.json" (
    echo [%date% %time%] ERROR: No se encuentra credentials.json >> "%LOG_FILE%"
    set "EXIT_CODE=4"
    goto :restaurar
)
if not exist "%SCRIPT_DIR%\token.json" (
    echo [%date% %time%] ERROR: No se encuentra token.json - requiere renovacion manual >> "%LOG_FILE%"
    set "EXIT_CODE=5"
    goto :restaurar
)
echo [%date% %time%] Credenciales OK >> "%LOG_FILE%"

REM Verificar red (HTTPS, no ping - muchos servidores bloquean ICMP)
echo [%date% %time%] Verificando conexion a internet... >> "%LOG_FILE%"
curl -s --max-time 10 -o nul -w "%%{http_code}" https://www.google.com > nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [%date% %time%] Sin internet, esperando 60s... >> "%LOG_FILE%"
    ping -n 61 127.0.0.1 > nul 2>&1
    curl -s --max-time 10 -o nul -w "%%{http_code}" https://www.google.com > nul 2>&1
    if %ERRORLEVEL% NEQ 0 (
        echo [%date% %time%] Reintento 2 en 60s... >> "%LOG_FILE%"
        ping -n 61 127.0.0.1 > nul 2>&1
        curl -s --max-time 10 -o nul -w "%%{http_code}" https://www.google.com > nul 2>&1
        if %ERRORLEVEL% NEQ 0 (
            echo [%date% %time%] ERROR: Sin conexion a internet tras 3 intentos >> "%LOG_FILE%"
            set "EXIT_CODE=6"
            goto :restaurar
        )
    )
)
echo [%date% %time%] Internet OK >> "%LOG_FILE%"

REM ============================================================================
REM EJECUTAR GMAIL MODULE
REM ============================================================================
echo [%date% %time%] Ejecutando Gmail Module... >> "%LOG_FILE%"
cd /d "%SCRIPT_DIR%"
%PYTHON_PATH% "%SCRIPT_PATH%" --produccion >> "%LOG_FILE%" 2>&1
set EXIT_CODE=%ERRORLEVEL%

REM ---- RESULTADO ----
echo. >> "%LOG_FILE%"
echo [%date% %time%] Codigo de salida: %EXIT_CODE% >> "%LOG_FILE%"

if %EXIT_CODE% EQU 0 (
    echo [%date% %time%] EXITO: Ejecucion completada correctamente >> "%LOG_FILE%"
) else (
    echo [%date% %time%] ERROR: Fallo con codigo %EXIT_CODE% >> "%LOG_FILE%"
)

REM ============================================================================
REM RESTAURAR SUSPENSION + ALERTA SI HUBO ERROR
REM ============================================================================
:restaurar

REM Enviar alerta si hubo error (intentar siempre, aunque sea fallo de red)
if "%EXIT_CODE%" NEQ "0" (
    if "%EXIT_CODE%" NEQ "" (
        echo [%date% %time%] Enviando alerta por email... >> "%LOG_FILE%"
        %PYTHON_PATH% "%PROJECT_ROOT%\alerta_fallo.py" "Gmail_Semanal" "%EXIT_CODE%" "%LOG_FILE%" >> "%LOG_FILE%" 2>&1
        if %ERRORLEVEL% NEQ 0 (
            echo [%date% %time%] No se pudo enviar alerta por email >> "%LOG_FILE%"
        )
    )
)

REM Valores originales del PC: AC=5 min (enchufado), DC=3 min (bateria)
echo [%date% %time%] Restaurando configuracion de suspension... >> "%LOG_FILE%"
powercfg /change standby-timeout-ac 5 >> "%LOG_FILE%" 2>&1
powercfg /change standby-timeout-dc 3 >> "%LOG_FILE%" 2>&1
echo [%date% %time%] Suspension restaurada (AC=5min, DC=3min) >> "%LOG_FILE%"

echo ============================================== >> "%LOG_FILE%"
echo [%date% %time%] FIN EJECUCION >> "%LOG_FILE%"
echo ============================================== >> "%LOG_FILE%"

exit /b %EXIT_CODE%
