@echo off
REM ============================================================================
REM SETUP TAREA PROGRAMADA: Ventas_Barea_Semanal
REM ============================================================================
REM Ejecutar como Administrador (clic derecho > Ejecutar como administrador)
REM Crea una tarea que se ejecuta cada lunes a las 03:00
REM ============================================================================

echo.
echo ============================================
echo  SETUP: Ventas_Barea_Semanal
echo ============================================
echo.

REM Verificar permisos de administrador
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Este script necesita ejecutarse como Administrador.
    echo Haz clic derecho y selecciona "Ejecutar como administrador".
    echo.
    pause
    exit /b 1
)

set "TASK_NAME=Ventas_Barea_Semanal"
set "BAT_PATH=%~dp0barea_auto.bat"

REM Verificar que el bat existe
if not exist "%BAT_PATH%" (
    echo ERROR: No se encuentra %BAT_PATH%
    pause
    exit /b 1
)

echo Creando tarea: %TASK_NAME%
echo Comando: %BAT_PATH%
echo Frecuencia: Cada lunes a las 03:00
echo.

REM Eliminar tarea existente si la hay
schtasks /delete /tn "%TASK_NAME%" /f >nul 2>&1

REM Crear la tarea programada
schtasks /create ^
    /tn "%TASK_NAME%" ^
    /tr "\"%BAT_PATH%\"" ^
    /sc WEEKLY ^
    /d MON ^
    /st 03:00 ^
    /rl HIGHEST ^
    /f

if %errorlevel% equ 0 (
    echo.
    echo OK: Tarea creada correctamente.
    echo.

    REM Habilitar WakeToRun via PowerShell
    echo Configurando WakeToRun (despertar PC si esta en suspension)...
    powershell -Command ^
        "$xml = [xml](schtasks /query /tn '%TASK_NAME%' /xml); ^
         $ns = New-Object Xml.XmlNamespaceManager($xml.NameTable); ^
         $ns.AddNamespace('t','http://schemas.microsoft.com/windows/2004/02/mit/task'); ^
         $wake = $xml.SelectSingleNode('//t:WakeToRun', $ns); ^
         if ($wake) { $wake.InnerText = 'true' } ^
         else { ^
           $settings = $xml.SelectSingleNode('//t:Settings', $ns); ^
           $newNode = $xml.CreateElement('WakeToRun', 'http://schemas.microsoft.com/windows/2004/02/mit/task'); ^
           $newNode.InnerText = 'true'; ^
           $settings.AppendChild($newNode) | Out-Null ^
         }; ^
         $xml.Save([System.IO.Path]::GetTempPath() + 'barea_task.xml')"

    if exist "%TEMP%\barea_task.xml" (
        schtasks /delete /tn "%TASK_NAME%" /f >nul 2>&1
        schtasks /create /tn "%TASK_NAME%" /xml "%TEMP%\barea_task.xml" /f >nul 2>&1
        del "%TEMP%\barea_task.xml" >nul 2>&1
        echo OK: WakeToRun activado.
    ) else (
        echo AVISO: No se pudo activar WakeToRun. Configura manualmente en el Programador de Tareas.
    )

    echo.
    echo ============================================
    echo  RESUMEN
    echo ============================================
    echo  Tarea: %TASK_NAME%
    echo  Cada: Lunes a las 03:00
    echo  Accion: %BAT_PATH%
    echo  WakeToRun: Si
    echo  Dashboard mensual: 1er lunes (dia 1-7)
    echo ============================================
) else (
    echo ERROR: No se pudo crear la tarea.
    echo Verifica que tienes permisos de administrador.
)

echo.
pause
