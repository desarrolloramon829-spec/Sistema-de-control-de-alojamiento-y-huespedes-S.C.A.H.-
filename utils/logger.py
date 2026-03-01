"""
S.C.A.H. - Sistema de Logging y Auditoría
Registra acciones del usuario y errores del sistema
"""

import logging
import os
from datetime import datetime
from config import BASE_DIR


# ============================================================
# LOGGER DE ARCHIVO (errores y debug)
# ============================================================
LOG_DIR = os.path.join(BASE_DIR, "logs")
os.makedirs(LOG_DIR, exist_ok=True)

log_file = os.path.join(LOG_DIR, f"scah_{datetime.now().strftime('%Y%m')}.log")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(log_file, encoding="utf-8"),
        logging.StreamHandler(open(os.devnull, "w"))  # Solo log a archivo, no a consola
    ]
)

logger = logging.getLogger("SCAH")


def log_info(mensaje: str):
    """Registra un mensaje informativo."""
    logger.info(mensaje)


def log_error(mensaje: str, exc: Exception = None):
    """Registra un error."""
    if exc:
        logger.error(f"{mensaje}: {exc}", exc_info=True)
    else:
        logger.error(mensaje)


def log_warning(mensaje: str):
    """Registra una advertencia."""
    logger.warning(mensaje)


def log_debug(mensaje: str):
    """Registra un mensaje de debug."""
    logger.debug(mensaje)


# ============================================================
# AUDITORÍA EN BASE DE DATOS
# ============================================================
class Auditoria:
    """Gestiona el registro de auditoría en la base de datos."""

    def __init__(self, db_connection):
        self.conn = db_connection

    def registrar(self, usuario_id: int, accion: str, tabla_afectada: str,
                  registro_id: int = None, detalle: str = None):
        """Registra una acción de auditoría en la base de datos."""
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                INSERT INTO auditoria (usuario_id, accion, tabla_afectada, registro_id, detalle, fecha)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (usuario_id, accion, tabla_afectada, registro_id, detalle, datetime.now()))
            self.conn.commit()
            cursor.close()
        except Exception as e:
            log_error(f"Error al registrar auditoría: {accion}", e)

    def obtener_historial(self, limite: int = 100, usuario_id: int = None,
                          tabla: str = None, fecha_desde: datetime = None,
                          fecha_hasta: datetime = None) -> list:
        """Obtiene el historial de auditoría con filtros opcionales."""
        try:
            cursor = self.conn.cursor()
            query = """
                SELECT a.id, a.usuario_id, u.username, u.nombre_completo,
                       a.accion, a.tabla_afectada, a.registro_id, a.detalle, a.fecha
                FROM auditoria a
                LEFT JOIN usuarios u ON a.usuario_id = u.id
                WHERE 1=1
            """
            params = []

            if usuario_id:
                query += " AND a.usuario_id = %s"
                params.append(usuario_id)
            if tabla:
                query += " AND a.tabla_afectada = %s"
                params.append(tabla)
            if fecha_desde:
                query += " AND a.fecha >= %s"
                params.append(fecha_desde)
            if fecha_hasta:
                query += " AND a.fecha <= %s"
                params.append(fecha_hasta)

            query += " ORDER BY a.fecha DESC LIMIT %s"
            params.append(limite)

            cursor.execute(query, params)
            columnas = [desc[0] for desc in cursor.description]
            resultados = [dict(zip(columnas, row)) for row in cursor.fetchall()]
            cursor.close()
            return resultados
        except Exception as e:
            log_error("Error al obtener historial de auditoría", e)
            return []
