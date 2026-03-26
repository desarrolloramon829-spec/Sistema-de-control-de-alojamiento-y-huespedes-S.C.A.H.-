"""
S.C.A.H. - Sistema de Control de Alojamiento y Huéspedes
Punto de entrada principal de la aplicación

Ejecutar: python main.py
"""

import sys
import os
import threading
import traceback
from datetime import datetime

# Forzar encoding UTF-8 en la consola de Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Agregar directorio actual al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import customtkinter as ctk
from tkinter import messagebox

from config import APP_NAME, APP_VERSION
from utils.logger import log_info, log_error


CRASH_LOG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "crash_log.txt")


def registrar_crash(origen, exc_type, exc_value, exc_traceback):
    """Guarda un reporte simple de crash para diagnosticar cierres inesperados."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    detalle = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))

    try:
        with open(CRASH_LOG_PATH, "a", encoding="utf-8") as crash_file:
            crash_file.write(f"\n=== {timestamp} | {origen} ===\n")
            crash_file.write(detalle)
            crash_file.write("\n")
    except Exception as log_exc:
        print(f"[WARN] No se pudo escribir crash_log.txt: {log_exc}")


def instalar_handlers_globales():
    """Instala handlers para capturar excepciones fuera del ciclo principal de Tk."""
    def _handle_exception(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return

        log_error("Excepcion no controlada", exc_value)
        registrar_crash("sys.excepthook", exc_type, exc_value, exc_traceback)
        sys.__excepthook__(exc_type, exc_value, exc_traceback)

    def _handle_thread_exception(args):
        log_error(f"Excepcion no controlada en hilo '{args.thread.name}'", args.exc_value)
        registrar_crash(
            f"threading.excepthook:{args.thread.name}",
            args.exc_type,
            args.exc_value,
            args.exc_traceback,
        )

    sys.excepthook = _handle_exception
    threading.excepthook = _handle_thread_exception


def inicializar_sistema():
    """Inicializa la base de datos y ejecuta migraciones."""
    from database.connection import db
    from database.migrations import ejecutar_migraciones, verificar_esquema

    print(f"\n{'='*50}")
    print(f"  {APP_NAME} v{APP_VERSION}")
    print(f"  Sistema de Control de Alojamiento y Huéspedes")
    print(f"{'='*50}\n")

    # Paso 1: Intentar conexion a BD
    print("[1/3] Conectando a la base de datos...")
    if db.inicializar():
        print("  [OK] Conexion establecida")
    else:
        print("  [ERROR] Conexion directa fallida")
        print("  Intentando crear la base de datos...")
        try:
            if db.crear_base_datos():
                if db.inicializar():
                    print("  [OK] Base de datos creada y conectada")
                else:
                    print("  [ERROR] No se pudo conectar tras crear la BD")
                    return False
            else:
                print("  [ERROR] No se pudo crear la BD")
                return False
        except (UnicodeDecodeError, Exception) as e:
            print(f"  [ERROR] {str(e)}")
            print("\n  Verifique que PostgreSQL esta en ejecucion")
            print("  y que los datos de conexion en config.py son correctos.")
            return False

    # Paso 2: Ejecutar migraciones
    print("[2/3] Verificando esquema de base de datos...")
    try:
        if ejecutar_migraciones():
            print("  [OK] Esquema verificado/actualizado")
        else:
            print("  [ERROR] Error al ejecutar migraciones")
            return False
    except Exception as e:
        log_error("Error en migraciones", e)
        print(f"  [ERROR] Error en migraciones: {str(e)}")
        return False

    # Paso 3: Verificar esquema
    print("[3/3] Validando tablas...")
    try:
        tablas_ok, tablas_faltantes = verificar_esquema()
        if tablas_ok:
            print("  [OK] Todas las tablas estan presentes")
        else:
            print(f"  [WARN] Tablas faltantes: {', '.join(tablas_faltantes)}")
            return False
    except Exception as e:
        print(f"  [WARN] No se pudo verificar: {str(e)}")
        return False

    print(f"\n{'='*50}")
    print("  Sistema inicializado correctamente")
    print(f"{'='*50}\n")

    log_info("Sistema inicializado correctamente")
    return True


def main():
    """Funcion principal de la aplicacion."""
    # Crear directorio de logs si no existe
    os.makedirs("logs", exist_ok=True)
    instalar_handlers_globales()

    # Configuracion de CustomTkinter
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")

    # Inicializar sistema (base de datos)
    if not inicializar_sistema():
        root = ctk.CTk()
        root.withdraw()
        messagebox.showerror(
            "Error de Inicializacion",
            "No se pudo conectar a la base de datos PostgreSQL.\n\n"
            "Verifique que:\n"
            "1. PostgreSQL esta en ejecucion\n"
            "2. Los datos de conexion en config.py son correctos\n"
            "3. El usuario tiene permisos para crear bases de datos\n\n"
            "Consulte la documentacion para mas informacion."
        )
        root.destroy()
        sys.exit(1)

    # Crear ventana raiz (oculta hasta login exitoso)
    root = ctk.CTk()
    root.withdraw()

    def on_root_close():
        log_info("Cierre solicitado sobre la ventana principal")
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_root_close)

    # Capturar excepciones no manejadas en Tkinter
    def handle_tk_exception(exc, val, tb):
        log_error(f"Error no manejado en UI: {val}")
        registrar_crash("tkinter.callback", exc, val, tb)
        traceback.print_exception(exc, val, tb)

    root.report_callback_exception = handle_tk_exception

    def on_login_success(usuario):
        """Callback cuando el login es exitoso - crea la ventana principal."""
        log_info(f"Usuario '{usuario['username']}' inicio sesion")
        print(f"Bienvenido, {usuario.get('nombre_completo', usuario['username'])}!")

        # Mostrar ventana principal
        root.deiconify()

        from ui.main_window import MainWindow
        try:
            app = MainWindow(root, usuario)
        except Exception as e:
            log_error("Error al crear ventana principal", e)
            messagebox.showerror("Error", f"Error al iniciar la ventana principal:\n{e}")
            root.destroy()

    # Mostrar ventana de login
    from auth.login_window import LoginWindow
    login = LoginWindow(root, on_login_success)

    # Iniciar el loop principal de la aplicacion
    root.mainloop()

    log_info("Aplicacion cerrada")
    print("\nAplicacion cerrada. Hasta pronto!")


if __name__ == "__main__":
    main()
