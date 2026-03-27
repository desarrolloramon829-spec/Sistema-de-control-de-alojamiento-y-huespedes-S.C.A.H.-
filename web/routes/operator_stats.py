"""
S.C.A.H. Web - Rutas de Control de Cargas por Operador.
Solo accesible para administradores.
"""

from flask import Blueprint, render_template, jsonify, request
from web.routes.decorators import login_required, role_required
from web.services.operator_stats_service import (
    obtener_resumen_cargas,
    obtener_cargas_por_operador,
    obtener_tendencia_cargas,
    obtener_detalle_operador,
)

operator_stats_bp = Blueprint('operator_stats', __name__, url_prefix='/control-cargas')


def _get_date_params():
    """Extrae parámetros de fecha del request."""
    return request.args.get('fecha_desde'), request.args.get('fecha_hasta')


@operator_stats_bp.route('/')
@login_required
@role_required('admin')
def index():
    return render_template('operator_stats/index.html')


@operator_stats_bp.route('/api/resumen')
@login_required
@role_required('admin')
def api_resumen():
    fecha_desde, fecha_hasta = _get_date_params()
    datos = obtener_resumen_cargas(fecha_desde, fecha_hasta)
    return jsonify(datos)


@operator_stats_bp.route('/api/operadores')
@login_required
@role_required('admin')
def api_operadores():
    fecha_desde, fecha_hasta = _get_date_params()
    datos = obtener_cargas_por_operador(fecha_desde, fecha_hasta)
    return jsonify(datos)


@operator_stats_bp.route('/api/tendencia')
@login_required
@role_required('admin')
def api_tendencia():
    fecha_desde, fecha_hasta = _get_date_params()
    datos = obtener_tendencia_cargas(fecha_desde, fecha_hasta)
    return jsonify(datos)


@operator_stats_bp.route('/api/operador/<int:usuario_id>')
@login_required
@role_required('admin')
def api_detalle_operador(usuario_id):
    fecha_desde, fecha_hasta = _get_date_params()
    datos = obtener_detalle_operador(usuario_id, fecha_desde, fecha_hasta)
    if datos is None:
        return jsonify({'error': 'Operador no encontrado'}), 404
    return jsonify(datos)
