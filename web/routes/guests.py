"""
S.C.A.H. Web - Rutas de Huéspedes (búsqueda, carga manual, detalle).
"""

from flask import (Blueprint, render_template, request, redirect,
                   url_for, flash, session, jsonify)
from web.routes.decorators import login_required, permission_required
from web.services.guest_service import (
    busqueda_rapida, busqueda_avanzada, crear_huesped,
    obtener_huesped, eliminar_huesped, obtener_hoteles_lista,
    obtener_ciudades_lista
)

guests_bp = Blueprint('guests', __name__, url_prefix='/huespedes')


@guests_bp.route('/')
@login_required
def index():
    """Página principal de búsqueda de huéspedes."""
    termino = request.args.get('q', '').strip()
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)

    # Verificar si hay filtros avanzados
    filtros = {}
    for campo in ['apellido_nombre', 'dni_pasaporte', 'nacionalidad', 'procedencia',
                   'profesion', 'hotel_id', 'fecha_desde', 'fecha_hasta',
                   'edad_min', 'edad_max', 'origen_carga', 'destino', 'movilidad']:
        val = request.args.get(campo, '').strip()
        if val:
            filtros[campo] = val

    if filtros:
        datos, total, total_pages, current_page = busqueda_avanzada(filtros, page, per_page)
    elif termino:
        datos, total, total_pages, current_page = busqueda_rapida(termino, page, per_page)
    else:
        datos, total, total_pages, current_page = busqueda_rapida('', page, per_page)

    hoteles = obtener_hoteles_lista()

    return render_template('guests/index.html',
                           datos=datos, total=total,
                           total_pages=total_pages, page=current_page,
                           termino=termino, filtros=filtros,
                           hoteles=hoteles, per_page=per_page)


@guests_bp.route('/nuevo', methods=['GET', 'POST'])
@login_required
@permission_required('carga_manual')
def nuevo():
    """Formulario de carga manual de huésped."""
    hoteles = obtener_hoteles_lista()

    if request.method == 'POST':
        datos = {
            'hotel_id': request.form.get('hotel_id', type=int),
            'apellido_nombre': request.form.get('apellido_nombre', ''),
            'dni_pasaporte': request.form.get('dni_pasaporte', ''),
            'nacionalidad': request.form.get('nacionalidad', ''),
            'procedencia': request.form.get('procedencia', ''),
            'profesion': request.form.get('profesion', ''),
            'edad': request.form.get('edad', ''),
            'fecha_nacimiento': request.form.get('fecha_nacimiento', ''),
            'fecha_entrada': request.form.get('fecha_entrada', ''),
            'fecha_salida': request.form.get('fecha_salida', ''),
            'habitacion': request.form.get('habitacion', ''),
            'domicilio': request.form.get('domicilio', ''),
            'destino': request.form.get('destino', ''),
            'movilidad': request.form.get('movilidad', ''),
            'telefono': request.form.get('telefono', ''),
        }

        usuario_id = session['user']['id']
        ok, msg, huesped_id = crear_huesped(datos, usuario_id)

        if ok:
            flash(msg, 'success')
            return redirect(url_for('guests.detalle', huesped_id=huesped_id))
        else:
            flash(msg, 'danger')
            return render_template('guests/form.html', datos=datos, hoteles=hoteles,
                                   es_edicion=False)

    return render_template('guests/form.html', datos={}, hoteles=hoteles,
                           es_edicion=False)


@guests_bp.route('/<int:huesped_id>')
@login_required
def detalle(huesped_id):
    """Detalle de un huésped."""
    huesped = obtener_huesped(huesped_id)
    if not huesped:
        flash('Huésped no encontrado.', 'warning')
        return redirect(url_for('guests.index'))
    return render_template('guests/detail.html', huesped=huesped)


@guests_bp.route('/<int:huesped_id>/eliminar', methods=['POST'])
@login_required
@permission_required('eliminar_registros')
def eliminar(huesped_id):
    """Elimina un huésped."""
    usuario_id = session['user']['id']
    ok, msg = eliminar_huesped(huesped_id, usuario_id)
    if ok:
        flash(msg, 'success')
    else:
        flash(msg, 'danger')
    return redirect(url_for('guests.index'))


@guests_bp.route('/api/ciudades')
@login_required
def api_ciudades():
    """API para autocompletar ciudades."""
    ciudades = obtener_ciudades_lista()
    return jsonify(ciudades)
