@echo off
REM ============================================================================
REM VENTAS BAREA - EJECUCION AUTOMATICA v1.2
REM ============================================================================
REM Cada lunes a las 03:00 via Programador de Tareas
REM - Siempre: descarga ventas semana + regenera dashboard
REM - 1er lunes del mes (dia <= 7): dashboard meses cerrados + email socios
REM - Alerta por email a tascabarea@gmail.com si falla (cualquier paso)
REM
REM v1.2: fix reintentos internet (ERRORLEVEL en bloques anidados no se actualizaba)
REM v1.1: curl HTTPS en vez de ping, espera 60s, 3 reintentos, alerta en bat
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
set "EXIT_CODE=0"
set "ERROR_MSG="

REM Crear carpeta de logs si no existe
if not exist "%LOG_PATH%" mkdir "%LOG_PATH%"

REM ---- INICIO ----
echo ============================================== >> "%LOG_FILE%"
echo [%date% %time%] INICIO EJECUCION AUTOMATICA v1.2 >> "%LOG_FILE%"
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
    echo [%date% %time%] ERROR: Python no encontrado >> "%LOG_FILE%"
    set "EXIT_CODE=2"
    set "ERROR_MSG=Python no encontrado en PATH"
    goto :restaurar
)

REM Verificar que el script existe
if not exist "%SCRIPT_PATH%" (
    echo [%date% %time%] ERROR: No se encuentra %SCRIPT_PATH% >> "%LOG_FILE%"
    set "EXIT_CODE=3"
    set "ERROR_MSG=Script no encontrado: %SCRIPT_PATH%"
    goto :restaurar
)

REM Verificar conexion a internet (HTTPS, no ping - muchos servidores bloquean ICMP)
REM v1.2 fix: usar goto en vez de if anidados (ERRORLEVEL no se actualiza dentro de bloques)
echo [%date% %time%] Verificando conexion a internet... >> "%LOG_FILE%"
set "RETRY_COUNT=0"

:check_internet
curl -s --max-time 15 -o nul https://api.loyverse.com > nul 2>&1
if !ERRORLEVEL! EQU 0 goto :internet_ok

set /a RETRY_COUNT+=1
if !RETRY_COUNT! GEQ 3 (
    echo [%date% %time%] ERROR: Sin conexion a internet tras 3 intentos >> "%LOG_FILE%"
    set "EXIT_CODE=6"
    set "ERROR_MSG=Sin conexion a internet tras 3 intentos (WiFi no reconecto)"
    goto :restaurar
)
echo [%date% %time%] Sin conexion, reintento !RETRY_COUNT! de 3 en 60s... >> "%LOG_FILE%"
ping -n 61 127.0.0.1 > nul 2>&1
goto :check_internet

:internet_ok
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

    REM ============================================================================
    REM PUBLICAR INVENTARIO TALLERES EN GITHUB (para GitHub Actions)
    REM ============================================================================
    echo [%date% %time%] Publicando inventario talleres en GitHub... >> "%LOG_FILE%"
    set "JSON_FILE=%SCRIPT_DIR%\talleres_programados.json"
    if exist "%JSON_FILE%" (
        cd /d "%PROJECT_ROOT%"
        git add ventas_semana/talleres_programados.json >> "%LOG_FILE%" 2>&1
        git commit -m "inventario talleres actualizado (%date%)" >> "%LOG_FILE%" 2>&1
        git push >> "%LOG_FILE%" 2>&1
        if !ERRORLEVEL! EQU 0 (
            echo [%date% %time%] Inventario talleres publicado en GitHub >> "%LOG_FILE%"
        ) else (
            echo [%date% %time%] AVISO: No se pudo hacer push a GitHub (no critico) >> "%LOG_FILE%"
        )
    ) else (
        echo [%date% %time%] AVISO: No existe %JSON_FILE%, sin push >> "%LOG_FILE%"
    )
) else (
    echo [%date% %time%] ERROR: Fallo con codigo %EXIT_CODE% >> "%LOG_FILE%"
    set "ERROR_MSG=Script Python fallo con exit code %EXIT_CODE%"
)

REM ============================================================================
REM RESTAURAR SUSPENSION + ALERTA SI HUBO ERROR
REM ============================================================================
:restaurar

REM Enviar alerta si hubo error (intentar siempre, aunque sea fallo de red)
if "%EXIT_CODE%" NEQ "0" (
    if "%EXIT_CODE%" NEQ "" (
        echo [%date% %time%] Enviando alerta por email... >> "%LOG_FILE%"
        %PYTHON_PATH% "%PROJECT_ROOT%\alerta_fallo.py" "Ventas_Barea_Semanal" "%EXIT_CODE%" "%LOG_FILE%" >> "%LOG_FILE%" 2>&1
        if %ERRORLEVEL% NEQ 0 (
            echo [%date% %time%] No se pudo enviar alerta por email >> "%LOG_FILE%"
        )
    )
)

echo [%date% %time%] Restaurando suspension del sistema... >> "%LOG_FILE%"
powercfg /change standby-timeout-ac 30 >> "%LOG_FILE%" 2>&1
powercfg /change standby-timeout-dc 15 >> "%LOG_FILE%" 2>&1
echo [%date% %time%] Suspension restaurada >> "%LOG_FILE%"

echo [%date% %time%] FIN >> "%LOG_FILE%"
echo ============================================== >> "%LOG_FILE%"

endlocal
