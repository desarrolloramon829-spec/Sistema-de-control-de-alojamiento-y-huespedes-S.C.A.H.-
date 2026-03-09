@echo off
chcp 65001 >nul 2>&1
title S.C.A.H. - Exportar Proyecto
color 0B

echo ============================================================
echo   S.C.A.H. - Exportar Proyecto para otra Computadora
echo ============================================================
echo.
echo Este script creará una copia limpia del proyecto lista
echo para ser transferida a otra computadora.
echo.

REM Solicitar ruta de destino
set /p DESTINO="Ingrese la ruta de destino (ej: D:\SCAH_Export): "

if "%DESTINO%"=="" (
    echo [ERROR] Debe ingresar una ruta de destino.
    pause
    exit /b 1
)

echo.
echo [INFO] Exportando a: %DESTINO%
echo.

REM Crear carpeta destino
mkdir "%DESTINO%" 2>nul

REM ============================================================
REM Copiar archivos principales
REM ============================================================
echo [1/8] Copiando archivos principales...
copy "%~dp0main.py" "%DESTINO%\" >nul
copy "%~dp0config.py" "%DESTINO%\" >nul
copy "%~dp0requirements.txt" "%DESTINO%\" >nul
copy "%~dp0README.md" "%DESTINO%\" >nul 2>nul

REM ============================================================
REM Copiar scripts de instalación y lanzamiento
REM ============================================================
echo [2/8] Copiando scripts de instalación...
copy "%~dp0instalar.bat" "%DESTINO%\" >nul
copy "%~dp0SCAH_Launcher.bat" "%DESTINO%\" >nul
copy "%~dp0crear_acceso_directo.vbs" "%DESTINO%\" >nul
copy "%~dp0GUIA_INSTALACION.md" "%DESTINO%\" >nul
copy "%~dp0build_exe.py" "%DESTINO%\" >nul 2>nul

REM ============================================================
REM Copiar módulos del sistema
REM ============================================================
echo [3/8] Copiando módulo auth/...
mkdir "%DESTINO%\auth" 2>nul
copy "%~dp0auth\*.py" "%DESTINO%\auth\" >nul

echo [4/8] Copiando módulo database/...
mkdir "%DESTINO%\database" 2>nul
copy "%~dp0database\*.py" "%DESTINO%\database\" >nul

echo [5/8] Copiando módulo modules/...
mkdir "%DESTINO%\modules" 2>nul
copy "%~dp0modules\*.py" "%DESTINO%\modules\" >nul

echo [6/8] Copiando módulo ui/...
mkdir "%DESTINO%\ui" 2>nul
copy "%~dp0ui\*.py" "%DESTINO%\ui\" >nul

echo [7/8] Copiando módulo utils/...
mkdir "%DESTINO%\utils" 2>nul
copy "%~dp0utils\*.py" "%DESTINO%\utils\" >nul

REM ============================================================
REM Copiar assets y crear carpetas necesarias
REM ============================================================
echo [8/8] Copiando assets y creando estructura...
mkdir "%DESTINO%\assets\icons" 2>nul
mkdir "%DESTINO%\logs" 2>nul

REM Copiar assets si existen
if exist "%~dp0assets\icons\*" (
    copy "%~dp0assets\icons\*" "%DESTINO%\assets\icons\" >nul 2>nul
)

REM ============================================================
REM Resumen
REM ============================================================
echo.
echo ============================================================
echo   EXPORTACIÓN COMPLETADA
echo ============================================================
echo.
echo Carpeta exportada: %DESTINO%
echo.

REM Calcular tamaño
for /f "tokens=3" %%a in ('dir "%DESTINO%" /s /-c 2^>nul ^| findstr "archivos"') do set TAMAÑO=%%a
echo.
echo Contenido exportado:
dir "%DESTINO%" /b
echo.
echo ---
echo.
echo PASOS SIGUIENTES:
echo   1. Copie la carpeta "%DESTINO%" a un USB o comparta por red
echo   2. En la otra computadora, instale Python 3.10+ y PostgreSQL 14+
echo   3. Ejecute "instalar.bat" dentro de la carpeta copiada
echo   4. El instalador creará el entorno virtual, instalará
echo      dependencias y creará un acceso directo en el Escritorio
echo.
echo   ¡Consulte GUIA_INSTALACION.md para instrucciones detalladas!
echo.
pause
