@echo off
chcp 65001 >nul 2>&1
title S.C.A.H. - Sistema de Control de Alojamiento y Huéspedes

echo ============================================================
echo   S.C.A.H. - Sistema de Control de Alojamiento y Huéspedes
echo ============================================================
echo.

REM Detectar si estamos ejecutando desde el .exe o desde código fuente
if exist "%~dp0SCAH.exe" (
    echo [INFO] Ejecutando desde ejecutable compilado...
    start "" "%~dp0SCAH.exe"
    exit
)

REM === MODO CÓDIGO FUENTE (con Python) ===
echo [INFO] Ejecutando desde código fuente...
echo.

REM Verificar si Python está instalado
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python no está instalado o no está en el PATH.
    echo.
    echo Descargue Python 3.10+ desde: https://www.python.org/downloads/
    echo Asegúrese de marcar "Add Python to PATH" durante la instalación.
    echo.
    pause
    exit /b 1
)

REM Verificar versión de Python
for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo [OK] Python %PYTHON_VERSION% detectado

REM Verificar si existe el entorno virtual
if exist "%~dp0.venv\Scripts\activate.bat" (
    echo [OK] Entorno virtual encontrado
    call "%~dp0.venv\Scripts\activate.bat"
) else if exist "%~dp0venv\Scripts\activate.bat" (
    echo [OK] Entorno virtual encontrado
    call "%~dp0venv\Scripts\activate.bat"
) else (
    echo [WARN] No se encontró entorno virtual. Usando Python del sistema.
    echo        Se recomienda ejecutar instalar.bat primero.
)

REM Verificar que las dependencias estén instaladas
python -c "import customtkinter" >nul 2>&1
if %errorlevel% neq 0 (
    echo [WARN] Dependencias no instaladas. Instalando...
    pip install -r "%~dp0requirements.txt"
    echo.
)

REM Verificar PostgreSQL
echo.
echo [INFO] Verificando conexión a PostgreSQL...
python -c "import psycopg2; conn=psycopg2.connect(host='localhost',port=5432,user='postgres',password='postgres',dbname='postgres'); conn.close(); print('[OK] PostgreSQL accesible')" 2>nul
if %errorlevel% neq 0 (
    echo [WARN] No se pudo verificar PostgreSQL.
    echo        Asegúrese de que PostgreSQL esté en ejecución.
    echo.
)

echo.
echo [INFO] Iniciando S.C.A.H....
echo.
cd /d "%~dp0"
python main.py

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] La aplicación se cerró con errores.
    echo         Revise el archivo crash_log.txt para más detalles.
    pause
)
