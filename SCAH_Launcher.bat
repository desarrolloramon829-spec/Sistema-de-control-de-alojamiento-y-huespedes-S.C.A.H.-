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

set "PYTHON_EXE="

REM Preferir el Python del entorno virtual local
if exist "%~dp0.venv\Scripts\python.exe" (
    set "PYTHON_EXE=%~dp0.venv\Scripts\python.exe"
    echo [OK] Usando entorno virtual local (.venv)
) else if exist "%~dp0venv\Scripts\python.exe" (
    set "PYTHON_EXE=%~dp0venv\Scripts\python.exe"
    echo [OK] Usando entorno virtual local (venv)
)

REM Verificar si Python está instalado
if not defined PYTHON_EXE where python >nul 2>&1
if not defined PYTHON_EXE if %errorlevel% neq 0 (
    echo [ERROR] Python no está instalado o no está en el PATH.
    echo.
    echo Descargue Python 3.10+ desde: https://www.python.org/downloads/
    echo Asegúrese de marcar "Add Python to PATH" durante la instalación.
    echo.
    pause
    exit /b 1
)

if not defined PYTHON_EXE set "PYTHON_EXE=python"

REM Verificar versión de Python
for /f "tokens=2" %%i in ('"%PYTHON_EXE%" --version 2^>^&1') do set PYTHON_VERSION=%%i
echo [OK] Python %PYTHON_VERSION% detectado

REM Verificar si existe el entorno virtual
if exist "%~dp0.venv\Scripts\activate.bat" (
    echo [OK] Entorno virtual encontrado
) else if exist "%~dp0venv\Scripts\activate.bat" (
    echo [OK] Entorno virtual encontrado
) else (
    echo [WARN] No se encontró entorno virtual. Usando Python del sistema.
    echo        Se recomienda ejecutar instalar.bat primero.
)

REM Verificar que las dependencias estén instaladas
"%PYTHON_EXE%" -c "import customtkinter" >nul 2>&1
if %errorlevel% neq 0 (
    echo [WARN] Dependencias no instaladas. Instalando...
    "%PYTHON_EXE%" -m pip install -r "%~dp0requirements.txt"
    echo.
)

REM Verificar PostgreSQL
echo.
echo [INFO] Verificando conexión a PostgreSQL...
"%PYTHON_EXE%" -c "import psycopg2; conn=psycopg2.connect(host='localhost',port=5432,user='postgres',password='postgres',dbname='postgres'); conn.close(); print('[OK] PostgreSQL accesible')" 2>nul
if %errorlevel% neq 0 (
    echo [WARN] No se pudo verificar PostgreSQL.
    echo        Asegúrese de que PostgreSQL esté en ejecución.
    echo.
)

echo.
echo [INFO] Iniciando S.C.A.H....
echo.
cd /d "%~dp0"
"%PYTHON_EXE%" main.py

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] La aplicación se cerró con errores.
    echo         Revise el archivo crash_log.txt para más detalles.
    pause
)
