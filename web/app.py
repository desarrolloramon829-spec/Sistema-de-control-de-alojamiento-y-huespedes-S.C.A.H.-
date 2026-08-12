"""
S.C.A.H. Web - Flask Application Factory
"""

import sys
import os
import time

# Agregar raíz del proyecto al path para acceder a database/, config, etc.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from flask import Flask
from web.config import config as app_config


def create_app(config_name: str = None) -> Flask:
    """Crea y configura la aplicación Flask."""
    if config_name is None:
        config_name = os.environ.get("FLASK_ENV", "default")

    app = Flask(
        __name__,
        template_folder=os.path.join(os.path.dirname(__file__), 'templates'),
        static_folder=os.path.join(os.path.dirname(__file__), 'static'),
    )
    app.config.from_object(app_config[config_name])

    # Crear carpeta de uploads
    os.makedirs(app.config.get('UPLOAD_FOLDER', 'uploads'), exist_ok=True)

    # Inicializar base de datos (solo fuera de Gunicorn: allí lo hace el hook
    # on_starting del proceso maestro, una única vez y antes del fork).
    if _debe_migrar_en_arranque():
        _init_database()

    # Registrar blueprints
    _register_blueprints(app)

    # Registrar filtros Jinja2
    _register_filters(app)

    # Versión de los assets: sella CSS/JS con su fecha de modificación para que
    # el navegador descargue la versión nueva tras un deploy y reutilice la
    # cacheada el resto del tiempo.
    asset_version = _calcular_version_assets(app.static_folder)

    # Contexto global para templates
    @app.context_processor
    def inject_globals():
        from flask import session, url_for

        def asset_url(filename: str) -> str:
            return url_for('static', filename=filename, v=asset_version)

        return {
            'app_name': 'S.C.A.H.',
            'app_version': '2.0 Web',
            'current_user': session.get('user'),
            'asset_version': asset_version,
            'asset_url': asset_url,
        }

    @app.after_request
    def add_performance_headers(response):
        from flask import request as req
        if req.path.startswith('/static/'):
            if req.args.get('v'):
                # Con sello de versión en la URL: cachear un año sin revalidar.
                response.headers['Cache-Control'] = 'public, max-age=31536000, immutable'
            else:
                # Sin sello no se puede invalidar la caché desde el servidor:
                # una hora y revalidación, para no servir CSS viejo tras deploy.
                response.headers['Cache-Control'] = 'public, max-age=3600'
        elif response.content_type and 'text/html' in response.content_type:
            # HTML: no cachear para siempre, pero permitir caché condicional
            response.headers.setdefault('Cache-Control', 'no-cache')
        return response

    _register_health_endpoints(app)

    return app


def _debe_migrar_en_arranque() -> bool:
    """Decide si create_app() debe tocar la base de datos.

    Bajo Gunicorn la respuesta es no: con --preload esta función corre en el
    proceso maestro y sin --preload correría una vez por worker, ejecutando DDL
    en paralelo y compitiendo por locks. El hook on_starting se encarga.
    """
    if os.environ.get("SCAH_RUN_MIGRATIONS") == "1":
        return True
    if os.environ.get("SCAH_SKIP_MIGRATIONS") == "1":
        return False
    return not os.environ.get("SERVER_SOFTWARE", "").startswith("gunicorn")


def _calcular_version_assets(static_folder: str) -> str:
    """Sello de versión basado en el archivo estático modificado más recientemente."""
    try:
        ultimo = 0.0
        for raiz, _, archivos in os.walk(static_folder):
            for nombre in archivos:
                try:
                    ultimo = max(ultimo, os.path.getmtime(os.path.join(raiz, nombre)))
                except OSError:
                    continue
        return str(int(ultimo)) if ultimo else str(int(time.time()))
    except Exception:
        return str(int(time.time()))


def _register_health_endpoints(app: Flask):
    """Endpoints de diagnóstico.

    /healthz no toca la base de datos: responde mientras el proceso esté vivo,
    que es lo que debe comprobar el health check de Render (si consultara la BD,
    una caída de Neon provocaría además el reinicio en bucle del servicio).
    /readyz sí la consulta, para diagnosticar a mano.
    """

    @app.route('/healthz')
    def healthz():
        return {'status': 'ok', 'pid': os.getpid()}, 200

    @app.route('/readyz')
    def readyz():
        from database.connection import db
        inicio = time.monotonic()
        ok, mensaje = db.test_conexion()
        latencia_ms = round((time.monotonic() - inicio) * 1000, 1)
        payload = {
            'status': 'ok' if ok else 'error',
            'database': mensaje,
            'latencia_ms': latencia_ms,
            'pid': os.getpid(),
        }
        return payload, (200 if ok else 503)


def _init_database():
    """Inicializa la conexión a la BD y ejecuta migraciones."""
    try:
        from database.connection import db
        conexion_ok, _ = db.test_conexion()
        if conexion_ok:
            from database.migrations import ejecutar_migraciones
            ejecutar_migraciones()
        else:
            # Intentar crear la BD
            from database.connection import DatabaseConnection
            if DatabaseConnection.crear_base_datos():
                from database.migrations import ejecutar_migraciones
                ejecutar_migraciones()
    except Exception as e:
        print(f"[WARN] Error inicializando BD: {e}")


def _register_blueprints(app: Flask):
    """Registra todos los blueprints de la aplicación."""
    from web.routes.auth import auth_bp
    from web.routes.dashboard import dashboard_bp
    from web.routes.guests import guests_bp
    from web.routes.hotels import hotels_bp
    from web.routes.imports import imports_bp
    from web.routes.reports import reports_bp
    from web.routes.users import users_bp
    from web.routes.stats import stats_bp
    from web.routes.backups import backups_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(guests_bp)
    app.register_blueprint(hotels_bp)
    app.register_blueprint(imports_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(users_bp)
    app.register_blueprint(stats_bp)
    app.register_blueprint(backups_bp)


def _register_filters(app: Flask):
    """Registra filtros personalizados de Jinja2."""

    @app.template_filter('fecha')
    def filtro_fecha(value, formato='%d/%m/%Y'):
        if value is None:
            return ''
        if hasattr(value, 'strftime'):
            return value.strftime(formato)
        return str(value)

    @app.template_filter('fecha_hora')
    def filtro_fecha_hora(value):
        if value is None:
            return ''
        if hasattr(value, 'strftime'):
            return value.strftime('%d/%m/%Y %H:%M')
        return str(value)

    @app.template_filter('truncar')
    def filtro_truncar(value, length=30):
        if not value:
            return ''
        s = str(value)
        return s[:length] + '...' if len(s) > length else s
