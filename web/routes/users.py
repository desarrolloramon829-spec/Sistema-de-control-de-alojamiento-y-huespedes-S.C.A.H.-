"""
S.C.A.H. Web - Rutas de Gestión de Usuarios.
"""

from flask import (Blueprint, render_template, request, redirect,
                   url_for, flash, session)
from web.routes.decorators import login_required, role_required
from web.services.user_service import (
    listar_usuarios, obtener_usuario, crear_usuario,
    actualizar_usuario, toggle_activo, obtener_roles
)

users_bp = Blueprint('users', __name__, url_prefix='/usuarios')


@users_bp.route('/')
@login_required
@role_required('admin')
def index():
    usuarios = listar_usuarios()
    return render_template('users/index.html', usuarios=usuarios)


@users_bp.route('/nuevo', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def nuevo():
    roles = obtener_roles()

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        nombre = request.form.get('nombre_completo', '').strip()
        rol = request.form.get('rol', '')
        admin_id = session['user']['id']

        ok, msg = crear_usuario(username, password, nombre, rol, admin_id)
        if ok:
            flash(msg, 'success')
            return redirect(url_for('users.index'))
        flash(msg, 'danger')
        return render_template('users/form.html', datos=request.form,
                               roles=roles, es_edicion=False)

    return render_template('users/form.html', datos={}, roles=roles,
                           es_edicion=False)


@users_bp.route('/<int:user_id>/editar', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def editar(user_id):
    user = obtener_usuario(user_id)
    if not user:
        flash('Usuario no encontrado.', 'warning')
        return redirect(url_for('users.index'))

    roles = obtener_roles()

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        nombre = request.form.get('nombre_completo', '').strip()
        rol = request.form.get('rol', '')
        admin_id = session['user']['id']

        ok, msg = actualizar_usuario(user_id, username, nombre, rol,
                                      password or None, admin_id)
        if ok:
            flash(msg, 'success')
            return redirect(url_for('users.index'))
        flash(msg, 'danger')
        return render_template('users/form.html', datos=request.form,
                               roles=roles, es_edicion=True, user_id=user_id)

    return render_template('users/form.html', datos=user, roles=roles,
                           es_edicion=True, user_id=user_id)


@users_bp.route('/<int:user_id>/toggle', methods=['POST'])
@login_required
@role_required('admin')
def toggle(user_id):
    admin_id = session['user']['id']
    ok, msg = toggle_activo(user_id, admin_id)
    if ok:
        flash(msg, 'success')
    else:
        flash(msg, 'danger')
    return redirect(url_for('users.index'))
