@echo off
REM ============================================================================
REM GMAIL FACTURAS - EJECUCION AUTOMATICA v1.6
REM ============================================================================
REM Cada viernes a las 03:00 via Programador de Tareas
REM
REM MEJORAS v1.6:
REM   - powercfg: desactiva suspension DURANTE la ejecucion
REM   - ping wait: no se pausa con suspension (timeout /t si se pausa)
REM   - Restaura suspension al final (siempre, incluso si falla)
REM   - Espera inicial reducida de 60s a 30s
REM ============================================================================

setlocal enabledelayedexpansion

REM Configuracion
set "PYTHON_PATH=python"
set "SCRIPT_DIR=C:\_ARCHIVOS\TRABAJO\Facturas\gestion-facturas\gmail"
set "SCRIPT_PATH=%SCRIPT_DIR%\gmail.py"
set "LOG_PATH=C:\_ARCHIVOS\TRABAJO\Facturas\gestion-facturas\outputs\logs_gmail"
set "DATE_STR=%date:~6,4%-%date:~3,2%-%date:~0,2%"
set "LOG_FILE=%LOG_PATH%\auto_%DATE_STR%.log"

REM Crear carpeta de logs si no existe
if not exist "%LOG_PATH%" mkdir "%LOG_PATH%"

REM ---- INICIO ----
echo ============================================== >> "%LOG_FILE%"
echo [%date% %time%] INICIO EJECUCION AUTOMATICA v1.6 >> "%LOG_FILE%"
echo ============================================== >> "%LOG_FILE%"

REM ============================================================================
REM ANTI-SUSPENSION: Impedir que Windows suspenda el PC durante la ejecucion
REM Se usa powercfg /change para poner standby a 0 (=nunca)
REM Se restaura al final con goto :restaurar
REM ============================================================================
echo [%date% %time%] Desactivando suspension del sistema... >> "%LOG_FILE%"
powercfg /change standby-timeout-ac 0 >> "%LOG_FILE%" 2>&1
powercfg /change standby-timeout-dc 0 >> "%LOG_FILE%" 2>&1
echo [%date% %time%] Suspension desactivada >> "%LOG_FILE%"

REM Espera 30s con ping (NO se pausa con suspension, a diferencia de timeout /t)
echo [%date% %time%] Esperando 30s para estabilizar sistema... >> "%LOG_FILE%"
ping -n 31 127.0.0.1 > nul 2>&1
echo [%date% %time%] Espera completada >> "%LOG_FILE%"

REM Verificar que Python existe
echo [%date% %time%] Verificando Python... >> "%LOG_FILE%"
%PYTHON_PATH% --version >> "%LOG_FILE%" 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [%date% %time%] ERROR: Python no encontrado en PATH >> "%LOG_FILE%"
    set EXIT_CODE=2
    goto :restaurar
)
echo [%date% %time%] Python OK >> "%LOG_FILE%"

REM Verificar que el script existe
if not exist "%SCRIPT_PATH%" (
    echo [%date% %time%] ERROR: No se encuentra %SCRIPT_PATH% >> "%LOG_FILE%"
    set EXIT_CODE=3
    goto :restaurar
)
echo [%date% %time%] Script encontrado OK >> "%LOG_FILE%"

REM Verificar credenciales
if not exist "%SCRIPT_DIR%\credentials.json" (
    echo [%date% %time%] ERROR: No se encuentra credentials.json >> "%LOG_FILE%"
    set EXIT_CODE=4
    goto :restaurar
)
if not exist "%SCRIPT_DIR%\token.json" (
    echo [%date% %time%] ERROR: No se encuentra token.json - requiere renovacion manual >> "%LOG_FILE%"
    set EXIT_CODE=5
    goto :restaurar
)
echo [%date% %time%] Credenciales OK >> "%LOG_FILE%"

REM Verificar red (con retry usando ping wait)
echo [%date% %time%] Verificando conexion a internet... >> "%LOG_FILE%"
ping -n 1 google.com > nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [%date% %time%] Sin internet, esperando 30s mas... >> "%LOG_FILE%"
    ping -n 31 127.0.0.1 > nul 2>&1
    ping -n 1 google.com > nul 2>&1
    if %ERRORLEVEL% NEQ 0 (
        echo [%date% %time%] ERROR: Sin conexion a internet >> "%LOG_FILE%"
        set EXIT_CODE=6
        goto :restaurar
    )
)
echo [%date% %time%] Internet OK >> "%LOG_FILE%"

REM ============================================================================
REM EJECUTAR GMAIL MODULE
REM Ejecucion directa (sincrona) - el BAT espera a que Python termine
REM La suspension esta desactivada, asi que no habra gaps de horas
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
REM RESTAURAR SUSPENSION (se ejecuta SIEMPRE, incluso tras errores)
REM Valores originales del PC: AC=5 min (enchufado), DC=3 min (bateria)
REM ============================================================================
:restaurar
echo [%date% %time%] Restaurando configuracion de suspension... >> "%LOG_FILE%"
powercfg /change standby-timeout-ac 5 >> "%LOG_FILE%" 2>&1
powercfg /change standby-timeout-dc 3 >> "%LOG_FILE%" 2>&1
echo [%date% %time%] Suspension restaurada (AC=5min, DC=3min) >> "%LOG_FILE%"

echo ============================================== >> "%LOG_FILE%"
echo [%date% %time%] FIN EJECUCION >> "%LOG_FILE%"
echo ============================================== >> "%LOG_FILE%"

exit /b %EXIT_CODE%
