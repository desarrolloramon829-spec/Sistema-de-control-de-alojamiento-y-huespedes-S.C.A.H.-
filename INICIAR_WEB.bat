@echo off
title S.C.A.H. - Sistema Web
color 0A
echo.
echo ==========================================
echo    S.C.A.H. - Sistema Web
echo ==========================================
echo.

set "PYTHON_EXE=python"

:: Preferir el Python del entorno virtual local
if exist "%~dp0.venv\Scripts\python.exe" (
    set "PYTHON_EXE=%~dp0.venv\Scripts\python.exe"
) else if exist "%~dp0venv\Scripts\python.exe" (
    set "PYTHON_EXE=%~dp0venv\Scripts\python.exe"
)

echo  Iniciando servidor...
echo  Accede en tu navegador a:
echo.
echo        http://localhost:5000
echo.
echo  Usuario: admin
echo  Contrasena: admin123
echo.
echo  Para CERRAR el servidor presiona Ctrl+C
echo ==========================================

:: Abrir el navegador despues de 3 segundos
start /b cmd /c "timeout /t 3 /nobreak >nul && start http://localhost:5000"

:: Iniciar el servidor
"%PYTHON_EXE%" web/run.py

pause
