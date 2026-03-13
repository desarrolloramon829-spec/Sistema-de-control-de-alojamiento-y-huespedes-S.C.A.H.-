"""
S.C.A.H. Web - Servicio de Hoteles
CRUD completo de hoteles con búsqueda y estadísticas.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from database.connection import db
from utils.validators import validar_texto_obligatorio, sanitizar_texto
from utils.logger import log_info, log_error


def listar_hoteles(filtro: str = None) -> list:
    """Lista hoteles con conteo de huéspedes. Permite filtrar por texto."""
    try:
        query = """
            SELECT h.id, h.nombre, h.categoria, h.nro_orden, h.direccion,
                   h.telefono, h.ciudad_localidad,
                   h.activo,
                   COUNT(hu.id) as total_huespedes,
                   SUM(CASE WHEN hu.fecha_entrada >= CURRENT_DATE - INTERVAL '1 day' THEN 1 ELSE 0 END) as huespedes_dia,
                   SUM(CASE WHEN hu.fecha_entrada >= CURRENT_DATE - INTERVAL '7 days' THEN 1 ELSE 0 END) as huespedes_semana,
                   SUM(CASE WHEN hu.fecha_entrada >= CURRENT_DATE - INTERVAL '30 days' THEN 1 ELSE 0 END) as huespedes_mes
            FROM hoteles h
            LEFT JOIN huespedes hu ON h.id = hu.hotel_id
        """
        params = []

        if filtro:
            query += (" WHERE (h.nombre ILIKE %s OR h.ciudad_localidad ILIKE %s"
                      " OR h.direccion ILIKE %s OR h.categoria ILIKE %s"
                      " OR h.telefono ILIKE %s)")
            patron = f"%{filtro}%"
            params = [patron] * 5

        query += " GROUP BY h.id ORDER BY h.nombre"

        resultados = db.ejecutar_query(query, tuple(params) if params else None, fetch=True)
        return resultados if resultados else []

    except Exception as e:
        log_error("Error al listar hoteles", e)
        return []


def obtener_hotel(hotel_id: int) -> dict | None:
    """Obtiene un hotel por su ID."""
    try:
        return db.ejecutar_query_one(
            "SELECT * FROM hoteles WHERE id = %s", (hotel_id,)
        )
    except Exception as e:
        log_error(f"Error al obtener hotel {hotel_id}", e)
        return None


def crear_hotel(datos: dict, usuario_id: int) -> tuple[bool, str]:
    """Crea un nuevo hotel."""
    ok, msg = validar_texto_obligatorio(datos.get("nombre", ""), "Nombre")
    if not ok:
        return False, msg

    try:
        db.ejecutar_query("""
            INSERT INTO hoteles (nombre, categoria, nro_orden, direccion,
            telefono, ciudad_localidad, usuario_registro_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (
            sanitizar_texto(datos.get("nombre", "")),
            sanitizar_texto(datos.get("categoria", "")),
            sanitizar_texto(datos.get("nro_orden", "")),
            sanitizar_texto(datos.get("direccion", "")),
            sanitizar_texto(datos.get("telefono", "")),
            sanitizar_texto(datos.get("ciudad_localidad", "")),
            usuario_id
        ))
        log_info(f"Hotel creado: {datos.get('nombre')}")
        return True, "Hotel creado correctamente"

    except Exception as e:
        log_error("Error al crear hotel", e)
        return False, f"Error al crear hotel: {str(e)}"


def actualizar_hotel(hotel_id: int, datos: dict) -> tuple[bool, str]:
    """Actualiza un hotel existente."""
    ok, msg = validar_texto_obligatorio(datos.get("nombre", ""), "Nombre")
    if not ok:
        return False, msg

    try:
        db.ejecutar_query("""
            UPDATE hoteles SET nombre=%s, categoria=%s, nro_orden=%s,
            direccion=%s, telefono=%s, ciudad_localidad=%s
            WHERE id=%s
        """, (
            sanitizar_texto(datos.get("nombre", "")),
            sanitizar_texto(datos.get("categoria", "")),
            sanitizar_texto(datos.get("nro_orden", "")),
            sanitizar_texto(datos.get("direccion", "")),
            sanitizar_texto(datos.get("telefono", "")),
            sanitizar_texto(datos.get("ciudad_localidad", "")),
            hotel_id
        ))
        log_info(f"Hotel actualizado: {datos.get('nombre')}")
        return True, "Hotel actualizado correctamente"

    except Exception as e:
        log_error("Error al actualizar hotel", e)
        return False, f"Error: {str(e)}"


def toggle_activo(hotel_id: int) -> tuple[bool, str]:
    """Activa/desactiva un hotel."""
    try:
        db.ejecutar_query(
            "UPDATE hoteles SET activo = NOT activo WHERE id = %s",
            (hotel_id,)
        )
        log_info(f"Hotel {hotel_id} estado cambiado")
        return True, "Estado del hotel actualizado"
    except Exception as e:
        log_error(f"Error al cambiar estado hotel {hotel_id}", e)
        return False, f"Error: {str(e)}"
