"""
S.C.A.H. Web - Rutas de Reportes.
"""

from flask import (Blueprint, render_template, request, session,
                   send_file, flash, redirect, url_for)
from web.routes.decorators import login_required, permission_required
from web.services.report_service import (
    obtener_datos_reporte, generar_excel, generar_pdf
)
import io
from datetime import datetime

reports_bp = Blueprint('reports', __name__, url_prefix='/reportes')


@reports_bp.route('/')
@login_required
@permission_required('reportes')
def index():
    return render_template('reports/index.html')


@reports_bp.route('/generar', methods=['POST'])
@login_required
@permission_required('reportes')
def generar():
    tipo = request.form.get('tipo', 'general')
    formato = request.form.get('formato', 'excel')

    params = {
        'desde': request.form.get('desde', ''),
        'hasta': request.form.get('hasta', ''),
    }

    datos, titulo = obtener_datos_reporte(tipo, params)

    if not datos:
        flash('No se encontraron datos para el reporte seleccionado.', 'warning')
        return redirect(url_for('reports.index'))

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    if formato == 'pdf':
        contenido = generar_pdf(datos, titulo)
        return send_file(
            io.BytesIO(contenido),
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f'SCAH_{tipo}_{timestamp}.pdf'
        )
    else:
        contenido = generar_excel(datos, titulo)
        return send_file(
            io.BytesIO(contenido),
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=f'SCAH_{tipo}_{timestamp}.xlsx'
        )


@reports_bp.route('/preview')
@login_required
@permission_required('reportes')
def preview():
    tipo = request.args.get('tipo', 'general')
    params = {
        'desde': request.args.get('desde', ''),
        'hasta': request.args.get('hasta', ''),
    }
    datos, titulo = obtener_datos_reporte(tipo, params)
    return render_template('reports/preview.html',
                           datos=datos[:100], titulo=titulo, tipo=tipo,
                           total=len(datos))
