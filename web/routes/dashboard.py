"""
S.C.A.H. Web - Rutas del Dashboard.
"""

from flask import Blueprint, render_template
from web.routes.decorators import login_required
from web.services.stats_service import obtener_kpis, obtener_ultimos_huespedes, obtener_top_ciudades

dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route('/dashboard')
@login_required
def index():
    kpis = obtener_kpis()
    ultimos = obtener_ultimos_huespedes(10)
    ciudades = obtener_top_ciudades(5)
    return render_template('dashboard/index.html',
                           kpis=kpis, ultimos=ultimos, ciudades=ciudades)
