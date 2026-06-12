"""
S.C.A.H. Web - Rutas de Huéspedes (búsqueda, carga manual, detalle).
"""

from flask import (Blueprint, render_template, request, redirect,
                   url_for, flash, session, jsonify)
from web.routes.decorators import login_required, permission_required
from web.services.guest_service import (
    busqueda_rapida, busqueda_avanzada, crear_huesped, actualizar_huesped,
    buscar_posibles_duplicados, crear_estadia_desde_huesped,
    obtener_huesped, eliminar_huesped, obtener_hoteles_lista,
    obtener_ciudades_lista, obtener_historial_estadias_relacionadas
)
from utils.geography import obtener_sugerencias_nacionalidad, obtener_sugerencias_procedencia
from utils.validators import validar_fecha

guests_bp = Blueprint('guests', __name__, url_prefix='/huespedes')


def _preparar_datos_formulario(huesped: dict) -> dict:
    """Adapta los datos del huésped al formato esperado por el formulario HTML."""
    datos = dict(huesped)

    if datos.get('dni_raw'):
        datos['dni_pasaporte'] = datos['dni_raw']

    for campo in ('fecha_nacimiento', 'fecha_entrada', 'fecha_salida'):
        valor = datos.get(campo)
        if not valor:
            datos[campo] = ''
            continue

        ok, _, fecha = validar_fecha(valor, permite_vacio=True)
        datos[campo] = fecha.isoformat() if ok and fecha else ''

    return datos


def _obtener_alertas_duplicados(datos: dict, exclude_id: int | None = None) -> list:
    """Obtiene alertas de duplicidad para mostrar en formulario o detalle."""
    return buscar_posibles_duplicados(
        dni_pasaporte=datos.get('dni_pasaporte', ''),
        apellido_nombre=datos.get('apellido_nombre', ''),
        telefono=datos.get('telefono', ''),
        hotel_id=datos.get('hotel_id'),
        fecha_entrada=datos.get('fecha_entrada', ''),
        fecha_salida=datos.get('fecha_salida', ''),
        exclude_id=exclude_id,
    )


def _contexto_geo_formulario() -> dict:
    return {
        'nacionalidades_sugeridas': obtener_sugerencias_nacionalidad()[1:],
        'procedencias_sugeridas': obtener_sugerencias_procedencia()[1:],
    }


def _obtener_datos_estadia_formulario() -> dict:
    """Obtiene únicamente los campos editables en el flujo de nueva estadía."""
    return {
        'hotel_id': request.form.get('hotel_id', type=int),
        'fecha_entrada': request.form.get('fecha_entrada', ''),
        'fecha_salida': request.form.get('fecha_salida', ''),
        'habitacion': request.form.get('habitacion', ''),
        'destino': request.form.get('destino', ''),
        'movilidad': request.form.get('movilidad', ''),
        'telefono': request.form.get('telefono', ''),
    }


def _preparar_datos_nueva_estadia(huesped: dict) -> dict:
    """Prepara el formulario derivado para registrar una nueva estadía."""
    datos = _preparar_datos_formulario(huesped)
    datos['fecha_entrada'] = ''
    datos['fecha_salida'] = ''
    return datos


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
                   'edad_min', 'edad_max', 'origen_carga', 'destino', 'movilidad',
                   'habitacion', 'telefono', 'ciudad']:
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
                                   es_edicion=False,
                                   duplicados=_obtener_alertas_duplicados(datos),
                                   **_contexto_geo_formulario())

    return render_template('guests/form.html', datos={}, hoteles=hoteles,
                           es_edicion=False, duplicados=[],
                           **_contexto_geo_formulario())


@guests_bp.route('/<int:huesped_id>/editar', methods=['GET', 'POST'])
@login_required
@permission_required('editar_registros')
def editar(huesped_id):
    """Formulario de edición de huésped."""
    huesped = obtener_huesped(huesped_id)
    if not huesped:
        flash('Huésped no encontrado.', 'warning')
        return redirect(url_for('guests.index'))

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
        ok, msg = actualizar_huesped(huesped_id, datos, usuario_id)

        if ok:
            flash(msg, 'success')
            return redirect(url_for('guests.detalle', huesped_id=huesped_id))

        flash(msg, 'danger')
        return render_template('guests/form.html', datos=datos, hoteles=hoteles,
                               es_edicion=True, huesped_id=huesped_id,
                               duplicados=_obtener_alertas_duplicados(datos, huesped_id),
                               **_contexto_geo_formulario())

    return render_template('guests/form.html', datos=_preparar_datos_formulario(huesped),
                           hoteles=hoteles, es_edicion=True, huesped_id=huesped_id,
                           duplicados=_obtener_alertas_duplicados(huesped, huesped_id),
                           **_contexto_geo_formulario())


@guests_bp.route('/<int:huesped_id>/nueva-estadia', methods=['GET', 'POST'])
@login_required
@permission_required('carga_manual')
def nueva_estadia(huesped_id):
    """Crea una nueva estadía reutilizando los datos de un expediente existente."""
    huesped_base = obtener_huesped(huesped_id)
    if not huesped_base:
        flash('Huésped no encontrado.', 'warning')
        return redirect(url_for('guests.index'))

    hoteles = obtener_hoteles_lista()
    datos_base = _preparar_datos_nueva_estadia(huesped_base)

    if request.method == 'POST':
        datos_estadia = _obtener_datos_estadia_formulario()
        datos_formulario = dict(datos_base)
        datos_formulario.update(datos_estadia)

        usuario_id = session['user']['id']
        ok, msg, nuevo_huesped_id = crear_estadia_desde_huesped(huesped_id, datos_estadia, usuario_id)

        if ok:
            flash(msg, 'success')
            return redirect(url_for('guests.detalle', huesped_id=nuevo_huesped_id))

        flash(msg, 'danger')
        return render_template(
            'guests/form.html',
            datos=datos_formulario,
            hoteles=hoteles,
            es_edicion=False,
            modo_nueva_estadia=True,
            huesped_base=huesped_base,
            huesped_base_id=huesped_id,
            duplicados=_obtener_alertas_duplicados(datos_formulario, huesped_id),
            **_contexto_geo_formulario(),
        )

    return render_template(
        'guests/form.html',
        datos=datos_base,
        hoteles=hoteles,
        es_edicion=False,
        modo_nueva_estadia=True,
        huesped_base=huesped_base,
        huesped_base_id=huesped_id,
        duplicados=[],
        **_contexto_geo_formulario(),
    )


@guests_bp.route('/<int:huesped_id>')
@login_required
def detalle(huesped_id):
    """Detalle de un huésped."""
    huesped = obtener_huesped(huesped_id)
    if not huesped:
        flash('Huésped no encontrado.', 'warning')
        return redirect(url_for('guests.index'))
    duplicados = _obtener_alertas_duplicados(huesped, huesped_id)
    _, _, fecha_entrada_actual = validar_fecha(huesped.get('fecha_entrada'), permite_vacio=True)
    _, _, fecha_salida_actual = validar_fecha(huesped.get('fecha_salida'), permite_vacio=True)
    historial_estadias = obtener_historial_estadias_relacionadas(
        huesped.get('dni_raw', ''),
        huesped_id,
        hotel_id_actual=huesped.get('hotel_id'),
        fecha_entrada_actual=fecha_entrada_actual,
        fecha_salida_actual=fecha_salida_actual,
    )
    return render_template(
        'guests/detail.html',
        huesped=huesped,
        duplicados=duplicados,
        historial_estadias=historial_estadias,
    )


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


@guests_bp.route('/api/duplicados')
@login_required
def api_duplicados():
    """API para verificar posibles duplicados de huéspedes."""
    duplicados = buscar_posibles_duplicados(
        dni_pasaporte=request.args.get('dni_pasaporte', ''),
        apellido_nombre=request.args.get('apellido_nombre', ''),
        telefono=request.args.get('telefono', ''),
        hotel_id=request.args.get('hotel_id', type=int),
        fecha_entrada=request.args.get('fecha_entrada', ''),
        fecha_salida=request.args.get('fecha_salida', ''),
        exclude_id=request.args.get('exclude_id', type=int),
    )
    return jsonify({
        'total': len(duplicados),
        'duplicados': duplicados,
    })
