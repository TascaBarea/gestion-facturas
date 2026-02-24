@echo off
REM ============================================================================
REM CONFIGURADOR DE TAREA PROGRAMADA - GMAIL FACTURAS
REM ============================================================================
REM Ejecutar como ADMINISTRADOR
REM Crea tarea que se ejecuta cada viernes a las 03:00
REM Despierta el PC de suspensión si es necesario
REM ============================================================================

echo.
echo ============================================
echo  CONFIGURADOR GMAIL FACTURAS AUTOMATICO
echo ============================================
echo.

REM Verificar si se ejecuta como administrador
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo ERROR: Este script debe ejecutarse como ADMINISTRADOR
    echo.
    echo Haz clic derecho en este archivo y selecciona "Ejecutar como administrador"
    pause
    exit /b 1
)

REM Configuración
set "TASK_NAME=Gmail_Facturas_Semanal"
set "BAT_PATH=C:\_ARCHIVOS\TRABAJO\Facturas\gestion-facturas\gmail\gmail_auto.bat"

echo Creando tarea programada: %TASK_NAME%
echo.
echo Configuración:
echo   - Ejecuta cada VIERNES a las 03:00
echo   - Despierta el PC de suspensión
echo   - Se ejecuta aunque el usuario no haya iniciado sesión
echo.

REM Eliminar tarea existente si existe
schtasks /delete /tn "%TASK_NAME%" /f >nul 2>&1

REM Crear nueva tarea
schtasks /create ^
    /tn "%TASK_NAME%" ^
    /tr "\"%BAT_PATH%\"" ^
    /sc weekly ^
    /d FRI ^
    /st 03:00 ^
    /ru SYSTEM ^
    /rl HIGHEST ^
    /f

if %errorLevel% equ 0 (
    echo.
    echo ============================================
    echo  TAREA CREADA EXITOSAMENTE
    echo ============================================
    echo.
    
    REM Configurar wake timer (despertar de suspensión)
    echo Configurando despertar de suspensión...
    
    REM Exportar tarea, modificar XML y reimportar para añadir WakeToRun
    set "TEMP_XML=%TEMP%\gmail_task.xml"
    schtasks /query /tn "%TASK_NAME%" /xml > "%TEMP_XML%"
    
    REM Usar PowerShell para modificar el XML
    powershell -Command ^
        "$xml = [xml](Get-Content '%TEMP_XML%'); ^
        $settings = $xml.Task.Settings; ^
        $wake = $xml.CreateElement('WakeToRun', $xml.Task.NamespaceURI); ^
        $wake.InnerText = 'true'; ^
        $settings.AppendChild($wake) | Out-Null; ^
        $xml.Save('%TEMP_XML%')"
    
    REM Reimportar con wake timer
    schtasks /delete /tn "%TASK_NAME%" /f >nul 2>&1
    schtasks /create /tn "%TASK_NAME%" /xml "%TEMP_XML%" /f
    
    del "%TEMP_XML%" >nul 2>&1
    
    echo.
    echo La tarea se ejecutará cada viernes a las 03:00
    echo El PC se despertará de suspensión automáticamente.
    echo.
    echo Para verificar: Abre "Programador de tareas" y busca "%TASK_NAME%"
    echo.
) else (
    echo.
    echo ERROR: No se pudo crear la tarea
    echo Verifica que tienes permisos de administrador
    echo.
)

echo.
pause
