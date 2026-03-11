"""
S.C.A.H. Web - Rutas de Backups.
"""

import io

from flask import Blueprint, render_template, send_file, session, flash, redirect, url_for

from database.connection import db
from utils.logger import Auditoria, log_error
from web.routes.decorators import login_required, permission_required
from web.services.backup_service import obtener_resumen_backup, generar_backup_zip


backups_bp = Blueprint('backups', __name__, url_prefix='/backups')


@backups_bp.route('/')
@login_required
@permission_required('backup')
def index():
    resumen = obtener_resumen_backup()
    return render_template('backups/index.html', resumen=resumen)


@backups_bp.route('/descargar')
@login_required
@permission_required('backup')
def descargar():
    try:
        contenido, timestamp, conteos = generar_backup_zip()

        try:
            conn = db.obtener_conexion()
            if conn:
                Auditoria(conn).registrar(
                    session['user']['id'],
                    'backup',
                    'sistema',
                    detalle=(
                        f"Backup generado. Huéspedes: {conteos.get('huespedes', 0)}, "
                        f"Hoteles: {conteos.get('hoteles', 0)}, Usuarios: {conteos.get('usuarios', 0)}"
                    ),
                )
                db.liberar_conexion(conn)
        except Exception as audit_error:
            log_error('No se pudo registrar auditoría de backup', audit_error)

        return send_file(
            io.BytesIO(contenido),
            mimetype='application/zip',
            as_attachment=True,
            download_name=f'SCAH_backup_{timestamp}.zip',
        )
    except Exception:
        flash('No se pudo generar el backup del sistema.', 'danger')
        return redirect(url_for('backups.index'))