"""
S.C.A.H. Web - Punto de entrada.
Ejecutar: python run.py
"""

import os
import sys

# Asegurar que el directorio raíz del proyecto esté en sys.path
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from web.app import create_app

FLASK_ENV = os.environ.get('FLASK_ENV', 'production')

app = create_app(FLASK_ENV)

if __name__ == '__main__':
    host = os.environ.get('FLASK_HOST', '0.0.0.0')
    port = int(os.environ.get('FLASK_PORT', 5000))
    debug = FLASK_ENV == 'development'
    use_reloader = debug and os.environ.get('SCAH_WEB_RELOAD', '0').lower() in {
        '1', 'true', 'yes', 'on'
    }

    print(f"""
╔══════════════════════════════════════════════╗
║      S.C.A.H. - Sistema Web                 ║
║                                              ║
║  Abrir en el navegador:                      ║
║  >>> http://localhost:{port}                    ║
║                                              ║
║  Usuario: admin  Contraseña: admin123        ║
║  Modo debug: {'ACTIVO' if debug else 'DESACTIVADO':<28}║
╚══════════════════════════════════════════════╝
    """)

    app.run(host=host, port=port, debug=debug, use_reloader=use_reloader)
