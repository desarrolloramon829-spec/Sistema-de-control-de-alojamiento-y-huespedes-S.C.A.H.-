@echo off
chcp 65001 >nul 2>&1
title S.C.A.H. - Instalador
color 0A

echo ============================================================
echo   S.C.A.H. - Instalador del Sistema
echo   Sistema de Control de Alojamiento y Huéspedes
echo ============================================================
echo.
echo Este instalador configurará todo lo necesario para ejecutar
echo el sistema S.C.A.H. en esta computadora.
echo.
echo Requisitos:
echo   - Python 3.10 o superior
echo   - PostgreSQL 14 o superior (en ejecución)
echo   - Conexión a Internet (para descargar dependencias)
echo.
pause

REM ============================================================
REM PASO 1: Verificar Python
REM ============================================================
echo.
echo [1/5] Verificando Python...
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Python NO está instalado o no está en el PATH.
    echo.
    echo Instrucciones:
    echo   1. Descargue Python desde: https://www.python.org/downloads/
    echo   2. Durante la instalación, marque "Add Python to PATH"
    echo   3. Reinicie esta terminal y ejecute este instalador de nuevo
    echo.
    pause
    exit /b 1
)
for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo [OK] Python %PYTHON_VERSION% detectado

REM ============================================================
REM PASO 2: Crear entorno virtual
REM ============================================================
echo.
echo [2/5] Configurando entorno virtual...
if exist "%~dp0.venv\Scripts\activate.bat" (
    echo [OK] Entorno virtual ya existe
) else (
    echo [INFO] Creando entorno virtual...
    python -m venv "%~dp0.venv"
    if %errorlevel% neq 0 (
        echo [ERROR] No se pudo crear el entorno virtual
        pause
        exit /b 1
    )
    echo [OK] Entorno virtual creado
)

REM Activar entorno virtual
call "%~dp0.venv\Scripts\activate.bat"
echo [OK] Entorno virtual activado

REM ============================================================
REM PASO 3: Instalar dependencias
REM ============================================================
echo.
echo [3/5] Instalando dependencias de Python...
pip install --upgrade pip >nul 2>&1
pip install -r "%~dp0requirements.txt"
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Error al instalar dependencias.
    echo         Verifique su conexión a Internet.
    pause
    exit /b 1
)
echo [OK] Dependencias instaladas correctamente

REM ============================================================
REM PASO 4: Verificar PostgreSQL
REM ============================================================
echo.
echo [4/5] Verificando PostgreSQL...
python -c "import psycopg2; conn=psycopg2.connect(host='localhost',port=5432,user='postgres',password='postgres',dbname='postgres'); conn.close(); print('[OK] PostgreSQL accesible')" 2>nul
if %errorlevel% neq 0 (
    echo.
    echo [ADVERTENCIA] No se pudo conectar a PostgreSQL.
    echo.
    echo Asegúrese de que:
    echo   1. PostgreSQL está instalado y en ejecución
    echo   2. El usuario 'postgres' tiene contraseña 'postgres'
    echo   3. El puerto 5432 está disponible
    echo.
    echo Si usa credenciales diferentes, edite el archivo config.py
    echo.
    echo ¿Desea continuar de todos modos? (S/N)
    set /p CONTINUAR="> "
    if /i not "%CONTINUAR%"=="S" (
        echo Instalación cancelada.
        pause
        exit /b 1
    )
) else (
    echo [OK] PostgreSQL accesible
)

REM ============================================================
REM PASO 5: Crear acceso directo
REM ============================================================
echo.
echo [5/5] Creando acceso directo en el Escritorio...
if exist "%~dp0crear_acceso_directo.vbs" (
    cscript //nologo "%~dp0crear_acceso_directo.vbs"
    echo [OK] Acceso directo creado
) else (
    echo [WARN] No se encontró el script de acceso directo
)

REM Crear directorio de logs
mkdir "%~dp0logs" 2>nul

echo.
echo ============================================================
echo   INSTALACIÓN COMPLETADA EXITOSAMENTE
echo ============================================================
echo.
echo Puede iniciar la aplicación de las siguientes formas:
echo   1. Acceso directo "S.C.A.H." en el Escritorio
echo   2. Ejecutar SCAH_Launcher.bat
echo   3. Desde terminal: python main.py
echo.
echo Credenciales por defecto:
echo   Usuario:    admin
echo   Contraseña: admin123
echo.
echo IMPORTANTE: Cambie la contraseña después del primer inicio.
echo.
pause
