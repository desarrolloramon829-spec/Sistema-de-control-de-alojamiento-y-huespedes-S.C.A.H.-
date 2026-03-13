"""
S.C.A.H. Web - Flask Application Factory
"""

import sys
import os

# Agregar raíz del proyecto al path para acceder a database/, config, etc.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from flask import Flask, send_from_directory, url_for
from web.config import config as app_config
from config import ALERT_NOTIFICATION_POLL_SECONDS


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

    # Inicializar base de datos
    _init_database()

    # Registrar blueprints
    _register_blueprints(app)

    # Registrar rutas PWA
    _register_pwa_routes(app)

    # Registrar filtros Jinja2
    _register_filters(app)

    # Contexto global para templates
    @app.context_processor
    def inject_globals():
        from flask import session

        def asset_url(filename: str) -> str:
            asset_path = os.path.join(app.static_folder, filename)
            try:
                version = int(os.path.getmtime(asset_path))
            except OSError:
                version = 1
            return url_for('static', filename=filename, v=version)

        return {
            'app_name': 'S.C.A.H.',
            'app_version': '2.0 Web',
            'current_user': session.get('user'),
            'alert_poll_seconds': ALERT_NOTIFICATION_POLL_SECONDS,
            'asset_url': asset_url,
        }

    return app


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
    from web.routes.alerts import alerts_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(guests_bp)
    app.register_blueprint(hotels_bp)
    app.register_blueprint(imports_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(users_bp)
    app.register_blueprint(stats_bp)
    app.register_blueprint(backups_bp)
    app.register_blueprint(alerts_bp)


def _register_pwa_routes(app: Flask):
    """Expone assets PWA con el scope correcto para instalación."""

    @app.route('/sw.js')
    def service_worker():
        response = send_from_directory(app.static_folder, 'sw.js', mimetype='application/javascript')
        response.headers['Cache-Control'] = 'no-cache'
        response.headers['Service-Worker-Allowed'] = '/'
        return response


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
