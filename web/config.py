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
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50 MB max upload
    
    # Sesiones
    SESSION_PERMANENT = True
    PERMANENT_SESSION_LIFETIME = 3600 * 8  # 8 horas
    
    # Paginación
    PER_PAGE = 50


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig,
}
