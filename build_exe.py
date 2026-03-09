"""
S.C.A.H. - Script de compilación con PyInstaller
Genera un ejecutable .exe independiente para distribución.

Uso:
    python build_exe.py
"""

import subprocess
import sys
import os
import shutil


def instalar_pyinstaller():
    """Instala PyInstaller si no está disponible."""
    try:
        import PyInstaller
        print(f"[OK] PyInstaller {PyInstaller.__version__} ya está instalado")
    except ImportError:
        print("[...] Instalando PyInstaller...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
        print("[OK] PyInstaller instalado")


def limpiar_build():
    """Elimina carpetas de compilaciones anteriores."""
    for carpeta in ["build", "dist"]:
        if os.path.exists(carpeta):
            print(f"[...] Limpiando {carpeta}/")
            shutil.rmtree(carpeta)
    for archivo in os.listdir("."):
        if archivo.endswith(".spec"):
            os.remove(archivo)


def compilar():
    """Ejecuta PyInstaller para crear el ejecutable."""
    
    # Rutas de datos adicionales que deben incluirse
    separador = ";" if sys.platform == "win32" else ":"
    
    add_data = [
        f"config.py{separador}.",
        f"assets{separador}assets",
    ]

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name=SCAH",
        "--onedir",                     # Crear carpeta con todos los archivos
        "--windowed",                   # Sin consola (app de escritorio)
        "--noconfirm",                  # Sin confirmación de sobreescritura
        "--clean",                      # Limpiar cache
        "--add-data", add_data[0],
        "--add-data", add_data[1],
        # Módulos ocultos que PyInstaller podría no detectar
        "--hidden-import=customtkinter",
        "--hidden-import=psycopg2",
        "--hidden-import=psycopg2.extras",
        "--hidden-import=psycopg2.pool",
        "--hidden-import=openpyxl",
        "--hidden-import=xlrd",
        "--hidden-import=reportlab",
        "--hidden-import=reportlab.lib.pagesizes",
        "--hidden-import=reportlab.platypus",
        "--hidden-import=reportlab.lib.styles",
        "--hidden-import=bcrypt",
        "--hidden-import=bcrypt._bcrypt",
        "--hidden-import=PIL",
        "--hidden-import=PIL._tkinter_finder",
        "--hidden-import=tkcalendar",
        "--hidden-import=babel.numbers",
        "--hidden-import=matplotlib",
        "--hidden-import=matplotlib.backends.backend_tkagg",
        "--hidden-import=matplotlib.figure",
        # Recopilar todos los archivos de customtkinter (temas, widgets)
        "--collect-all=customtkinter",
        "--collect-all=tkcalendar",
        "--collect-all=babel",
        "main.py"
    ]

    # Si existe un icono, usarlo
    icon_path = os.path.join("assets", "icons", "scah.ico")
    if os.path.exists(icon_path):
        cmd.insert(-1, f"--icon={icon_path}")

    print("\n[...] Compilando ejecutable (esto puede tardar varios minutos)...\n")
    print(f"Comando: {' '.join(cmd)}\n")
    
    resultado = subprocess.run(cmd)
    
    if resultado.returncode == 0:
        print("\n" + "=" * 60)
        print("  COMPILACIÓN EXITOSA")
        print("=" * 60)
        print(f"\n  El ejecutable se encuentra en: dist/SCAH/")
        print(f"  Archivo principal: dist/SCAH/SCAH.exe")
        print(f"\n  Para distribuir, copie toda la carpeta 'dist/SCAH/'")
        print(f"  a la computadora de destino.")
        print("=" * 60)
    else:
        print("\n[ERROR] La compilación falló. Revise los errores anteriores.")
        sys.exit(1)


def copiar_archivos_extra():
    """Copia archivos adicionales necesarios a la carpeta dist."""
    dist_dir = os.path.join("dist", "SCAH")
    
    if not os.path.exists(dist_dir):
        return
    
    # Crear carpeta de logs
    os.makedirs(os.path.join(dist_dir, "logs"), exist_ok=True)
    
    # Copiar README
    if os.path.exists("README.md"):
        shutil.copy2("README.md", dist_dir)
    
    # Copiar archivos de instalación
    for archivo in ["instalar.bat", "crear_acceso_directo.vbs", "GUIA_INSTALACION.md"]:
        if os.path.exists(archivo):
            shutil.copy2(archivo, dist_dir)
    
    print("[OK] Archivos adicionales copiados a dist/SCAH/")


def main():
    print("=" * 60)
    print("  S.C.A.H. - Compilador de Ejecutable")
    print("  Sistema de Control de Alojamiento y Huéspedes")
    print("=" * 60)
    
    instalar_pyinstaller()
    limpiar_build()
    compilar()
    copiar_archivos_extra()
    
    print("\n¡Proceso completado!")


if __name__ == "__main__":
    main()
