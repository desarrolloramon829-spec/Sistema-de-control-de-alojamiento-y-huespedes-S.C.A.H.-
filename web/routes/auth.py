"""
S.C.A.H. Web - Rutas de autenticación.
"""

from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from web.services.auth_service import autenticar_usuario

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if 'user' in session:
        return redirect(url_for('dashboard.index'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()

        if not username or not password:
            flash('Complete todos los campos.', 'danger')
            return render_template('auth/login.html')

        user = autenticar_usuario(username, password)
        if user:
            session.permanent = True
            session['user'] = {
                'id': user['id'],
                'username': user['username'],
                'nombre_completo': user.get('nombre_completo', ''),
                'rol': user['rol'],
            }
            flash(f'Bienvenido, {user.get("nombre_completo") or user["username"]}', 'success')
            return redirect(url_for('dashboard.index'))
        else:
            flash('Usuario o contraseña incorrectos.', 'danger')

    return render_template('auth/login.html')


@auth_bp.route('/logout')
def logout():
    session.clear()
    flash('Sesión cerrada correctamente.', 'info')
    return redirect(url_for('auth.login'))


@auth_bp.route('/')
def root():
    if 'user' in session:
        return redirect(url_for('dashboard.index'))
    return redirect(url_for('auth.login'))
