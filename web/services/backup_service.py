"""
S.C.A.H. Web - Servicio de Backups
Genera respaldos exportables de la base de datos operativa.
"""

import io
import json
import zipfile
from datetime import date, datetime

from database.connection import db
from database.models import ALL_TABLES, SQL_CREATE_INDICES
from utils.logger import log_error


BACKUP_TABLES = {
    "usuarios": """
        SELECT id, username, password_hash, nombre_completo, rol, activo,
               fecha_creacion, ultimo_acceso
        FROM usuarios
        ORDER BY id
    """,
    "hoteles": """
        SELECT id, nombre, nro_orden, categoria, direccion, telefono,
               ciudad_localidad, activo, fecha_registro, usuario_registro_id
        FROM hoteles
        ORDER BY id
    """,
    "huespedes": """
        SELECT id, hotel_id, nacionalidad, procedencia, apellido_nombre,
               dni_pasaporte, fecha_nacimiento, edad, profesion, fecha_entrada,
               fecha_salida, habitacion, domicilio, destino, movilidad,
               telefono, origen_carga, usuario_carga_id, fecha_registro
        FROM huespedes
        ORDER BY id
    """,
    "importaciones_log": """
        SELECT id, archivo_nombre, hoja_nombre, fecha_importacion, usuario_id,
               registros_importados, registros_error, registros_duplicados,
               estado, detalle
        FROM importaciones_log
        ORDER BY id
    """,
    "auditoria": """
        SELECT id, usuario_id, accion, tabla_afectada, registro_id, detalle, fecha
        FROM auditoria
        ORDER BY id
    """,
}


def _serializar_valor(valor):
    """Convierte fechas y valores especiales a JSON estable."""
    if isinstance(valor, (datetime, date)):
        return valor.isoformat()
    return valor


def obtener_resumen_backup() -> dict:
    """Obtiene métricas básicas para la pantalla de backups."""
    try:
        resultado = db.ejecutar_query_one("""
            SELECT
                (SELECT COUNT(*) FROM huespedes) AS huespedes,
                (SELECT COUNT(*) FROM hoteles) AS hoteles,
                (SELECT COUNT(*) FROM usuarios) AS usuarios,
                (SELECT COUNT(*) FROM auditoria) AS auditoria,
                (SELECT MAX(fecha) FROM auditoria WHERE accion = 'backup') AS ultimo_backup
        """)
        return resultado or {
            "huespedes": 0,
            "hoteles": 0,
            "usuarios": 0,
            "auditoria": 0,
            "ultimo_backup": None,
        }
    except Exception as e:
        log_error("Error obteniendo resumen de backup", e)
        return {
            "huespedes": 0,
            "hoteles": 0,
            "usuarios": 0,
            "auditoria": 0,
            "ultimo_backup": None,
        }


def generar_backup_zip() -> tuple[bytes, str, dict]:
    """Genera un ZIP con el respaldo JSON y el esquema SQL."""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    payload = {
        "metadata": {
            "app": "S.C.A.H.",
            "tipo": "backup_web",
            "generado_en": datetime.now().isoformat(),
            "version": "2.0 Web",
        },
        "tables": {},
    }
    conteos = {}

    try:
        for tabla, query in BACKUP_TABLES.items():
            filas = db.ejecutar_query(query, fetch=True) or []
            serializadas = [
                {clave: _serializar_valor(valor) for clave, valor in fila.items()}
                for fila in filas
            ]
            payload["tables"][tabla] = serializadas
            conteos[tabla] = len(serializadas)

        payload["metadata"]["conteos"] = conteos
        esquema = "\n\n".join(ALL_TABLES + SQL_CREATE_INDICES)

        instrucciones = "S.C.A.H. - Respaldo Web\n\n"
        instrucciones += "Contenido del ZIP:\n"
        instrucciones += "- backup.json: datos exportados en formato JSON\n"
        instrucciones += "- schema.sql: esquema base de tablas e índices\n\n"
        instrucciones += "La restauración no está automatizada en esta versión web.\n"
        instrucciones += "Se recomienda conservar el ZIP completo.\n"

        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            zip_file.writestr(
                f'SCAH_backup_{timestamp}.json',
                json.dumps(payload, ensure_ascii=False, indent=2),
            )
            zip_file.writestr('schema.sql', esquema)
            zip_file.writestr('LEEME_RESTAURACION.txt', instrucciones)

        return buffer.getvalue(), timestamp, conteos
    except Exception as e:
        log_error("Error generando backup ZIP", e)
        raise