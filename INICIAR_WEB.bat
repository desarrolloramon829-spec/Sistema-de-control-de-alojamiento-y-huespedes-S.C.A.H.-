@echo off
title S.C.A.H. - Sistema Web
color 0A
echo.
echo ==========================================
echo    S.C.A.H. - Sistema Web
echo ==========================================
echo.

:: Activar entorno virtual si existe
if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
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
python web/run.py

pause
