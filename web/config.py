"""
S.C.A.H. Web - Configuración Flask
"""

import os
import secrets


class Config:
    """Configuración base."""
    SECRET_KEY = os.environ.get("FLASK_SECRET_KEY") or "scah-dev-key-cambiar-en-produccion-2024"

    # Carpeta para uploads temporales
    UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
    # Tope de subida. Cada archivo en curso ocupa memoria al parsearse, así que
    # en instancias de 512 MB conviene bajarlo vía SCAH_MAX_UPLOAD_MB.
    MAX_CONTENT_LENGTH = int(os.environ.get("SCAH_MAX_UPLOAD_MB", 50)) * 1024 * 1024

    # Sesiones
    SESSION_PERMANENT = True
    PERMANENT_SESSION_LIFETIME = 3600 * 8  # 8 horas
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'

    # Paginación
    PER_PAGE = 50
    # Tope duro: evita que ?per_page=100000 fuerce al servidor a construir una
    # página enorme y agote la memoria del worker.
    MAX_PER_PAGE = 200

    # Segundos que se reutiliza el conteo total de un listado antes de volver a
    # calcularlo. Contar filas es la parte cara de paginar sobre tablas grandes.
    COUNT_CACHE_TTL = int(os.environ.get("SCAH_COUNT_CACHE_TTL", 60))


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False
    # La app va detrás del proxy HTTPS de Render: la cookie de sesión no debe
    # viajar nunca por HTTP. Se puede desactivar con SCAH_COOKIE_SECURE=0 para
    # despliegues internos servidos solo por HTTP (si no, no se podría iniciar
    # sesión: el navegador retendría la cookie).
    SESSION_COOKIE_SECURE = os.environ.get("SCAH_COOKIE_SECURE", "1") != "0"


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig,
}
