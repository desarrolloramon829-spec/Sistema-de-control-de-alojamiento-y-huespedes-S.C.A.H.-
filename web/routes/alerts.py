"""
S.C.A.H. Web - Rutas de Alertas Operativas.
"""

from flask import Blueprint, flash, jsonify, redirect, render_template, request, session, url_for

from web.routes.decorators import login_required, permission_required
from web.services.alert_service import (
    actualizar_estado_alerta,
    contar_alertas_pendientes,
    listar_alertas,
    obtener_configuracion_alertas,
    obtener_metricas_alertas,
)

alerts_bp = Blueprint('alerts', __name__, url_prefix='/alertas')

_METRICAS_VACIO = {
    "resumen": {"pendientes": 0, "pendientes_prioritarios": 0, "bloqueantes_pendientes": 0, "ultimas_24h": 0},
    "por_tipo": [],
    "por_severidad": [],
    "recientes": [],
}


@alerts_bp.route('/')
@login_required
@permission_required('ver_alertas')
def index():
    estado = request.args.get('estado', '').strip()
    severidad = request.args.get('severidad', '').strip()
    tipo = request.args.get('tipo', '').strip()

    try:
        alertas = listar_alertas(limit=200, estado=estado, severidad=severidad, tipo=tipo)
    except Exception:
        alertas = []

    try:
        pendientes = contar_alertas_pendientes()
    except Exception:
        pendientes = 0

    try:
        metricas = obtener_metricas_alertas()
        if not metricas or not isinstance(metricas.get("resumen"), dict):
            metricas = _METRICAS_VACIO
    except Exception:
        metricas = _METRICAS_VACIO

    configuracion = obtener_configuracion_alertas()

    return render_template(
        'alerts/index.html',
        alertas=alertas,
        filtros={'estado': estado, 'severidad': severidad, 'tipo': tipo},
        pendientes=pendientes,
        configuracion_alertas=configuracion,
        metricas_alertas=metricas,
    )


@alerts_bp.route('/api/count')
@login_required
@permission_required('ver_alertas')
def api_count():
    return jsonify({'pending_count': contar_alertas_pendientes()})


@alerts_bp.route('/<int:alerta_id>/estado', methods=['POST'])
@login_required
@permission_required('ver_alertas')
def cambiar_estado(alerta_id: int):
    estado = request.form.get('estado', '').strip()
    usuario_id = session['user']['id']
    if not actualizar_estado_alerta(alerta_id, estado, usuario_id):
      flash('No se pudo actualizar el estado de la alerta.', 'danger')
      return redirect(url_for('alerts.index'))

    flash('Estado de alerta actualizado correctamente.', 'success')
    return redirect(url_for(
        'alerts.index',
        estado=request.args.get('estado', ''),
        severidad=request.args.get('severidad', ''),
        tipo=request.args.get('tipo', ''),
    ))