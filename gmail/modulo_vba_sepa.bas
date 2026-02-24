' ============================================================================
' MÓDULO VBA - GENERADOR SEPA
' ============================================================================
' Este código se añade al Excel PAGOS_Gmail_XTYY.xlsx
' Crea un botón que llama al script Python para generar el fichero SEPA XML
'
' INSTRUCCIONES DE INSTALACIÓN:
' 1. Abrir el Excel PAGOS_Gmail_*.xlsx
' 2. Alt + F11 (Editor VBA)
' 3. Insertar > Módulo
' 4. Pegar este código
' 5. Cerrar editor VBA
' 6. Guardar como .xlsm (Excel con macros)
' 7. Insertar > Formas > Rectángulo
' 8. Escribir "Generar SEPA XML"
' 9. Click derecho > Asignar macro > GenerarSEPAXML
' ============================================================================

Option Explicit

' Ruta al script Python
Const PYTHON_PATH As String = "python"
Const SCRIPT_PATH As String = "C:\_ARCHIVOS\TRABAJO\Facturas\gestion-facturas\gmail\generar_sepa.py"
Const OUTPUT_PATH As String = "C:\_ARCHIVOS\TRABAJO\Facturas\gestion-facturas\outputs\"

Sub GenerarSEPAXML()
    ' Genera fichero SEPA XML desde las transferencias marcadas
    
    Dim ws As Worksheet
    Dim contadorMarcadas As Integer
    Dim totalImporte As Double
    Dim fila As Long
    Dim respuesta As VbMsgBoxResult
    Dim comando As String
    Dim resultado As Integer
    Dim rutaExcel As String
    Dim archivoSEPA As String
    
    On Error GoTo ErrorHandler
    
    ' Verificar que existe la pestaña SEPA
    On Error Resume Next
    Set ws = ThisWorkbook.Sheets("SEPA")
    On Error GoTo ErrorHandler
    
    If ws Is Nothing Then
        MsgBox "No se encontró la pestaña SEPA en este libro.", vbExclamation, "Error"
        Exit Sub
    End If
    
    ' Contar transferencias marcadas
    contadorMarcadas = 0
    totalImporte = 0
    
    For fila = 8 To ws.Cells(ws.Rows.Count, 1).End(xlUp).Row
        If ws.Cells(fila, 2).Value = ChrW(10003) Then  ' ✓
            contadorMarcadas = contadorMarcadas + 1
            If IsNumeric(ws.Cells(fila, 6).Value) Then
                totalImporte = totalImporte + CDbl(ws.Cells(fila, 6).Value)
            End If
        End If
    Next fila
    
    If contadorMarcadas = 0 Then
        MsgBox "No hay transferencias marcadas con ✓ en la columna INCLUIR." & vbCrLf & vbCrLf & _
               "Marca las transferencias que quieras incluir y vuelve a intentar.", _
               vbExclamation, "Sin transferencias"
        Exit Sub
    End If
    
    ' Confirmar
    respuesta = MsgBox("Se generará un fichero SEPA XML con:" & vbCrLf & vbCrLf & _
                       "• Transferencias: " & contadorMarcadas & vbCrLf & _
                       "• Importe total: " & Format(totalImporte, "#,##0.00") & " €" & vbCrLf & vbCrLf & _
                       "¿Continuar?", _
                       vbQuestion + vbYesNo, "Generar SEPA XML")
    
    If respuesta <> vbYes Then
        Exit Sub
    End If
    
    ' Guardar el libro primero
    Application.StatusBar = "Guardando libro..."
    ThisWorkbook.Save
    
    rutaExcel = ThisWorkbook.FullName
    
    ' Ejecutar script Python
    Application.StatusBar = "Generando fichero SEPA XML..."
    
    comando = PYTHON_PATH & " """ & SCRIPT_PATH & """ """ & rutaExcel & """"
    
    ' Ejecutar y esperar
    resultado = Shell("cmd /c " & comando, vbHide)
    
    ' Esperar a que termine (máximo 30 segundos)
    Application.Wait (Now + TimeValue("0:00:05"))
    
    ' Buscar el archivo generado (el más reciente)
    archivoSEPA = BuscarArchivoSEPAReciente()
    
    Application.StatusBar = False
    
    If archivoSEPA <> "" Then
        MsgBox "✅ Fichero SEPA generado correctamente:" & vbCrLf & vbCrLf & _
               archivoSEPA & vbCrLf & vbCrLf & _
               "Sube este fichero al banco para ejecutar las transferencias.", _
               vbInformation, "SEPA Generado"
        
        ' Abrir carpeta
        Shell "explorer.exe /select,""" & archivoSEPA & """", vbNormalFocus
    Else
        MsgBox "El script se ejecutó pero no se encontró el archivo generado." & vbCrLf & vbCrLf & _
               "Revisa la carpeta: " & OUTPUT_PATH, _
               vbExclamation, "Verificar resultado"
    End If
    
    Exit Sub
    
ErrorHandler:
    Application.StatusBar = False
    MsgBox "Error: " & Err.Description, vbCritical, "Error"
End Sub

Function BuscarArchivoSEPAReciente() As String
    ' Busca el archivo SEPA_*.xml más reciente
    
    Dim fso As Object
    Dim carpeta As Object
    Dim archivo As Object
    Dim archivoReciente As String
    Dim fechaReciente As Date
    
    Set fso = CreateObject("Scripting.FileSystemObject")
    
    If Not fso.FolderExists(OUTPUT_PATH) Then
        BuscarArchivoSEPAReciente = ""
        Exit Function
    End If
    
    Set carpeta = fso.GetFolder(OUTPUT_PATH)
    fechaReciente = DateSerial(1900, 1, 1)
    archivoReciente = ""
    
    For Each archivo In carpeta.Files
        If Left(archivo.Name, 5) = "SEPA_" And Right(archivo.Name, 4) = ".xml" Then
            If archivo.DateCreated > fechaReciente Then
                fechaReciente = archivo.DateCreated
                archivoReciente = archivo.Path
            End If
        End If
    Next archivo
    
    BuscarArchivoSEPAReciente = archivoReciente
End Function

Sub VerificarIBANsVacios()
    ' Resalta las filas con IBAN ordenante vacío
    
    Dim ws As Worksheet
    Dim fila As Long
    Dim contador As Integer
    
    Set ws = ThisWorkbook.Sheets("SEPA")
    contador = 0
    
    For fila = 8 To ws.Cells(ws.Rows.Count, 1).End(xlUp).Row
        If ws.Cells(fila, 2).Value = ChrW(10003) Then  ' Marcada
            If Trim(ws.Cells(fila, 10).Value) = "" Then  ' IBAN ordenante vacío
                ws.Rows(fila).Interior.Color = RGB(255, 255, 200)  ' Amarillo
                contador = contador + 1
            End If
        End If
    Next fila
    
    If contador > 0 Then
        MsgBox contador & " transferencias marcadas no tienen IBAN ordenante seleccionado." & vbCrLf & vbCrLf & _
               "Selecciona el IBAN del ordenante en la columna J para cada una.", _
               vbExclamation, "IBANs pendientes"
    Else
        MsgBox "Todas las transferencias marcadas tienen IBAN ordenante.", vbInformation, "OK"
    End If
End Sub
