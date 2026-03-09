' ============================================================
' S.C.A.H. - Crear Acceso Directo en el Escritorio
' Ejecutar este archivo para crear un acceso directo
' ============================================================

Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

' Obtener ruta del escritorio
strDesktop = WshShell.SpecialFolders("Desktop")

' Obtener ruta del directorio actual (donde está este script)
strAppDir = fso.GetParentFolderName(WScript.ScriptFullName)

' Verificar si existe el ejecutable compilado o el launcher
strExePath = strAppDir & "\SCAH.exe"
strBatPath = strAppDir & "\SCAH_Launcher.bat"
strMainPy = strAppDir & "\main.py"

If fso.FileExists(strExePath) Then
    ' Modo ejecutable compilado
    Set oShortcut = WshShell.CreateShortcut(strDesktop & "\S.C.A.H..lnk")
    oShortcut.TargetPath = strExePath
    oShortcut.WorkingDirectory = strAppDir
    oShortcut.Description = "Sistema de Control de Alojamiento y Huéspedes"
    oShortcut.WindowStyle = 1
    
    ' Buscar icono
    strIconPath = strAppDir & "\assets\icons\scah.ico"
    If fso.FileExists(strIconPath) Then
        oShortcut.IconLocation = strIconPath
    End If
    
    oShortcut.Save
    MsgBox "Acceso directo creado en el Escritorio." & vbCrLf & vbCrLf & _
           "Apunta a: " & strExePath, vbInformation, "S.C.A.H."

ElseIf fso.FileExists(strBatPath) Then
    ' Modo launcher .bat
    Set oShortcut = WshShell.CreateShortcut(strDesktop & "\S.C.A.H..lnk")
    oShortcut.TargetPath = strBatPath
    oShortcut.WorkingDirectory = strAppDir
    oShortcut.Description = "Sistema de Control de Alojamiento y Huéspedes"
    oShortcut.WindowStyle = 1
    
    ' Buscar icono
    strIconPath = strAppDir & "\assets\icons\scah.ico"
    If fso.FileExists(strIconPath) Then
        oShortcut.IconLocation = strIconPath
    End If
    
    oShortcut.Save
    MsgBox "Acceso directo creado en el Escritorio." & vbCrLf & vbCrLf & _
           "Apunta a: " & strBatPath, vbInformation, "S.C.A.H."

ElseIf fso.FileExists(strMainPy) Then
    ' Modo Python directo
    strPython = "pythonw.exe"
    
    Set oShortcut = WshShell.CreateShortcut(strDesktop & "\S.C.A.H..lnk")
    oShortcut.TargetPath = strPython
    oShortcut.Arguments = """" & strMainPy & """"
    oShortcut.WorkingDirectory = strAppDir
    oShortcut.Description = "Sistema de Control de Alojamiento y Huéspedes"
    oShortcut.WindowStyle = 1
    
    ' Buscar icono
    strIconPath = strAppDir & "\assets\icons\scah.ico"
    If fso.FileExists(strIconPath) Then
        oShortcut.IconLocation = strIconPath
    End If
    
    oShortcut.Save
    MsgBox "Acceso directo creado en el Escritorio." & vbCrLf & vbCrLf & _
           "Apunta a: python " & strMainPy, vbInformation, "S.C.A.H."
Else
    MsgBox "No se encontró el ejecutable ni el archivo principal." & vbCrLf & _
           "Asegúrese de ejecutar este script desde la carpeta de la aplicación.", _
           vbExclamation, "S.C.A.H. - Error"
End If

Set oShortcut = Nothing
Set WshShell = Nothing
Set fso = Nothing
