"""
S.C.A.H. Web - Decorador de autenticación para rutas.
"""

from functools import wraps
from flask import session, redirect, url_for, flash, abort


def login_required(f):
    """Requiere que el usuario esté autenticado."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user' not in session:
            flash('Debe iniciar sesión para acceder.', 'warning')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated


def role_required(*roles):
    """Requiere que el usuario tenga uno de los roles indicados."""
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if 'user' not in session:
                flash('Debe iniciar sesión para acceder.', 'warning')
                return redirect(url_for('auth.login'))
            user_role = session['user'].get('rol', '')
            if user_role not in roles:
                abort(403)
            return f(*args, **kwargs)
        return decorated
    return decorator


def permission_required(permiso: str):
    """Requiere que el usuario tenga un permiso específico."""
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if 'user' not in session:
                flash('Debe iniciar sesión para acceder.', 'warning')
                return redirect(url_for('auth.login'))
            from web.services.auth_service import tiene_permiso
            user_role = session['user'].get('rol', '')
            if not tiene_permiso(user_role, permiso):
                abort(403)
            return f(*args, **kwargs)
        return decorated
    return decorator
