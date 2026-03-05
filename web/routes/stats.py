"""
S.C.A.H. Web - Rutas de Estadísticas.
"""

from flask import Blueprint, render_template, request, jsonify
from web.routes.decorators import login_required, permission_required
from web.services.stats_service import obtener_estadistica

stats_bp = Blueprint('stats', __name__, url_prefix='/estadisticas')


@stats_bp.route('/')
@login_required
@permission_required('estadisticas')
def index():
    return render_template('stats/index.html')


@stats_bp.route('/api/<tipo>')
@login_required
@permission_required('estadisticas')
def api_datos(tipo):
    """API que retorna datos para gráficos Chart.js."""
    tipos_validos = ['nacionalidades', 'profesiones', 'procedencia',
                     'destinos', 'por_hotel', 'edades', 'tendencia']
    if tipo not in tipos_validos:
        return jsonify({'error': 'Tipo inválido'}), 400

    datos = obtener_estadistica(tipo)
    return jsonify(datos)
