"""
S.C.A.H. Web - Rutas del Dashboard.
"""

from flask import Blueprint, render_template, session
from web.routes.decorators import login_required
from web.services.stats_service import obtener_kpis, obtener_ultimos_huespedes, obtener_top_ciudades
from web.services.alert_service import obtener_metricas_alertas

dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route('/dashboard')
@login_required
def index():
    kpis = obtener_kpis()
    ultimos = obtener_ultimos_huespedes(10)
    ciudades = obtener_top_ciudades(5)
    alert_metrics = obtener_metricas_alertas() if session.get('user', {}).get('rol') in ('admin', 'operador') else None
    return render_template('dashboard/index.html',
                           kpis=kpis, ultimos=ultimos, ciudades=ciudades,
                           alert_metrics=alert_metrics)
