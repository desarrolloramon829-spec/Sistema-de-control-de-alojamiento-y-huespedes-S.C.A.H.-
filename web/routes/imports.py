"""
S.C.A.H. Web - Rutas de Importación Excel.
"""

import os
import tempfile
from flask import (Blueprint, render_template, request, redirect,
                   url_for, flash, session, current_app)
from web.routes.decorators import login_required, permission_required
from web.services.import_service import (
    procesar_archivos_v1, procesar_archivos_v2,
    importar_datos_v1, importar_datos_v2,
    obtener_hoteles_activos
)

imports_bp = Blueprint('imports', __name__, url_prefix='/importar')

ALLOWED_EXTENSIONS = {'xlsx', 'xls'}


def _allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@imports_bp.route('/')
@login_required
@permission_required('importar_excel')
def index():
    """Selector de formato de importación."""
    return render_template('imports/index.html')


@imports_bp.route('/v1', methods=['GET', 'POST'])
@login_required
@permission_required('importar_excel')
def importar_v1():
    """Importación formato V1 (hotel por hoja)."""
    if request.method == 'POST':
        action = request.form.get('action', 'preview')

        if action == 'preview':
            return _preview_v1()
        elif action == 'import':
            return _ejecutar_import_v1()

    return render_template('imports/v1.html', preview=None)


@imports_bp.route('/v2', methods=['GET', 'POST'])
@login_required
@permission_required('importar_excel')
def importar_v2():
    """Importación formato V2 (tabular)."""
    hoteles = obtener_hoteles_activos()

    if request.method == 'POST':
        action = request.form.get('action', 'preview')

        if action == 'preview':
            return _preview_v2(hoteles)
        elif action == 'import':
            return _ejecutar_import_v2(hoteles)

    return render_template('imports/v2.html', preview=None, hoteles=hoteles)


def _guardar_archivos_temporales(files) -> list:
    """Guarda los archivos subidos en carpeta temporal y retorna rutas."""
    rutas = []
    upload_dir = current_app.config.get('UPLOAD_FOLDER', tempfile.gettempdir())
    os.makedirs(upload_dir, exist_ok=True)

    for f in files:
        if f and f.filename and _allowed_file(f.filename):
            filepath = os.path.join(upload_dir, f.filename)
            f.save(filepath)
            rutas.append(filepath)

    return rutas


def _limpiar_archivos(rutas: list):
    """Elimina archivos temporales."""
    for r in rutas:
        try:
            if os.path.exists(r):
                os.remove(r)
        except Exception:
            pass


def _preview_v1():
    files = request.files.getlist('archivos')
    if not files or not files[0].filename:
        flash('Seleccione al menos un archivo Excel.', 'warning')
        return render_template('imports/v1.html', preview=None)

    rutas = _guardar_archivos_temporales(files)
    if not rutas:
        flash('No se encontraron archivos Excel válidos.', 'warning')
        return render_template('imports/v1.html', preview=None)

    result = procesar_archivos_v1(rutas)

    # Guardar rutas en sesión para import posterior
    session['import_v1_files'] = rutas

    return render_template('imports/v1.html', preview=result)


def _ejecutar_import_v1():
    rutas = session.pop('import_v1_files', [])
    if not rutas:
        flash('No hay archivos para importar. Suba los archivos nuevamente.', 'warning')
        return redirect(url_for('imports.importar_v1'))

    result = procesar_archivos_v1(rutas)
    usuario_id = session['user']['id']

    import_result = importar_datos_v1(result['huespedes'], usuario_id)
    _limpiar_archivos(rutas)

    flash(f"Importación completada: {import_result['importados']} importados, "
          f"{import_result['duplicados']} duplicados, "
          f"{import_result['errores']} errores.", 'success')
    return redirect(url_for('imports.index'))


def _preview_v2(hoteles):
    files = request.files.getlist('archivos')
    if not files or not files[0].filename:
        flash('Seleccione al menos un archivo Excel.', 'warning')
        return render_template('imports/v2.html', preview=None, hoteles=hoteles)

    rutas = _guardar_archivos_temporales(files)
    if not rutas:
        flash('No se encontraron archivos Excel válidos.', 'warning')
        return render_template('imports/v2.html', preview=None, hoteles=hoteles)

    result = procesar_archivos_v2(rutas)
    session['import_v2_files'] = rutas

    return render_template('imports/v2.html', preview=result, hoteles=hoteles)


def _ejecutar_import_v2(hoteles):
    rutas = session.pop('import_v2_files', [])
    if not rutas:
        flash('No hay archivos para importar. Suba los archivos nuevamente.', 'warning')
        return redirect(url_for('imports.importar_v2'))

    hotel_nombre = request.form.get('hotel_nombre', '').strip()
    if not hotel_nombre:
        flash('Debe seleccionar un hotel.', 'warning')
        return redirect(url_for('imports.importar_v2'))

    nuevo_hotel = request.form.get('nuevo_hotel') == '1'
    hotel_extra = {
        'nro_orden': request.form.get('nro_orden', ''),
        'direccion': request.form.get('direccion', ''),
        'ciudad': request.form.get('ciudad', ''),
    }

    result = procesar_archivos_v2(rutas)
    usuario_id = session['user']['id']

    import_result = importar_datos_v2(
        result['huespedes'], hotel_nombre, usuario_id,
        nuevo_hotel=nuevo_hotel, hotel_extra=hotel_extra
    )
    _limpiar_archivos(rutas)

    flash(f"Importación completada: {import_result['importados']} importados, "
          f"{import_result['duplicados']} duplicados, "
          f"{import_result['errores']} errores.", 'success')
    return redirect(url_for('imports.index'))
