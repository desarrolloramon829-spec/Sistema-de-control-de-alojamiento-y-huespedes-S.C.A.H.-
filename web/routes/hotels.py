"""
S.C.A.H. Web - Rutas de Hoteles.
"""

from flask import (Blueprint, render_template, request, redirect,
                   url_for, flash, session)
from web.routes.decorators import login_required, permission_required
from web.services.hotel_service import (
    listar_hoteles, obtener_hotel, crear_hotel,
    actualizar_hotel, toggle_activo
)

hotels_bp = Blueprint('hotels', __name__, url_prefix='/hoteles')


@hotels_bp.route('/')
@login_required
def index():
    filtro = request.args.get('q', '').strip()
    hoteles = listar_hoteles(filtro)
    return render_template('hotels/index.html', hoteles=hoteles, filtro=filtro)


@hotels_bp.route('/nuevo', methods=['GET', 'POST'])
@login_required
@permission_required('gestionar_hoteles')
def nuevo():
    if request.method == 'POST':
        datos = {
            'nombre': request.form.get('nombre', ''),
            'categoria': request.form.get('categoria', ''),
            'nro_orden': request.form.get('nro_orden', ''),
            'direccion': request.form.get('direccion', ''),
            'telefono': request.form.get('telefono', ''),
            'ciudad_localidad': request.form.get('ciudad_localidad', ''),
        }
        usuario_id = session['user']['id']
        ok, msg = crear_hotel(datos, usuario_id)
        if ok:
            flash(msg, 'success')
            return redirect(url_for('hotels.index'))
        flash(msg, 'danger')
        return render_template('hotels/form.html', datos=datos, es_edicion=False)

    return render_template('hotels/form.html', datos={}, es_edicion=False)


@hotels_bp.route('/<int:hotel_id>/editar', methods=['GET', 'POST'])
@login_required
@permission_required('gestionar_hoteles')
def editar(hotel_id):
    hotel = obtener_hotel(hotel_id)
    if not hotel:
        flash('Hotel no encontrado.', 'warning')
        return redirect(url_for('hotels.index'))

    if request.method == 'POST':
        datos = {
            'nombre': request.form.get('nombre', ''),
            'categoria': request.form.get('categoria', ''),
            'nro_orden': request.form.get('nro_orden', ''),
            'direccion': request.form.get('direccion', ''),
            'telefono': request.form.get('telefono', ''),
            'ciudad_localidad': request.form.get('ciudad_localidad', ''),
        }
        ok, msg = actualizar_hotel(hotel_id, datos)
        if ok:
            flash(msg, 'success')
            return redirect(url_for('hotels.index'))
        flash(msg, 'danger')
        return render_template('hotels/form.html', datos=datos, es_edicion=True,
                               hotel_id=hotel_id)

    return render_template('hotels/form.html', datos=hotel, es_edicion=True,
                           hotel_id=hotel_id)


@hotels_bp.route('/<int:hotel_id>/toggle', methods=['POST'])
@login_required
@permission_required('gestionar_hoteles')
def toggle(hotel_id):
    ok, msg = toggle_activo(hotel_id)
    if ok:
        flash(msg, 'success')
    else:
        flash(msg, 'danger')
    return redirect(url_for('hotels.index'))
