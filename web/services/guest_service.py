"""
S.C.A.H. Web - Servicio de Huéspedes
Lógica de negocio para búsqueda, carga, detalle y eliminación de huéspedes.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from database.connection import db
from utils.validators import (validar_dni, validar_fecha, validar_texto_obligatorio,
                               validar_edad, validar_fechas_estadia, calcular_edad,
                               sanitizar_texto, validar_telefono, validar_habitacion)
from utils.formatters import formato_fecha, formato_dni
from utils.logger import log_info, log_error, Auditoria
from config import DEFAULT_PAGE_SIZE


def busqueda_rapida(termino: str, page: int = 1, per_page: int = DEFAULT_PAGE_SIZE):
    """
    Búsqueda rápida en 11 campos ILIKE.
    Retorna (resultados, total, paginas).
    """
    patron = f"%{termino}%"
    query = """
        SELECT h.id, ht.nombre as hotel, h.apellido_nombre, h.dni_pasaporte,
               h.nacionalidad, h.procedencia, h.edad, h.profesion,
               h.fecha_entrada, h.fecha_salida, h.habitacion, h.telefono,
               h.domicilio, h.destino, h.movilidad, h.origen_carga
        FROM huespedes h
        JOIN hoteles ht ON h.hotel_id = ht.id
        WHERE h.apellido_nombre ILIKE %s
           OR h.dni_pasaporte ILIKE %s
           OR ht.nombre ILIKE %s
           OR ht.ciudad_localidad ILIKE %s
           OR h.nacionalidad ILIKE %s
           OR h.procedencia ILIKE %s
           OR h.profesion ILIKE %s
           OR h.habitacion ILIKE %s
           OR h.telefono ILIKE %s
           OR h.domicilio ILIKE %s
           OR h.destino ILIKE %s
        ORDER BY h.fecha_registro DESC
    """
    params = [patron] * 11
    return _ejecutar_busqueda_paginada(query, params, page, per_page)


def busqueda_avanzada(filtros: dict, page: int = 1, per_page: int = DEFAULT_PAGE_SIZE):
    """
    Búsqueda avanzada con filtros combinables.
    filtros puede contener: hotel, ciudad, nacionalidad, dni, profesion,
    procedencia, fecha_desde, fecha_hasta, edad_min, edad_max,
    habitacion, destino, telefono.
    """
    query = """
        SELECT h.id, ht.nombre as hotel, h.apellido_nombre, h.dni_pasaporte,
               h.nacionalidad, h.procedencia, h.edad, h.profesion,
               h.fecha_entrada, h.fecha_salida, h.habitacion, h.telefono,
               h.domicilio, h.destino, h.movilidad, h.origen_carga
        FROM huespedes h
        JOIN hoteles ht ON h.hotel_id = ht.id
        WHERE 1=1
    """
    params = []

    if filtros.get("hotel"):
        query += " AND ht.nombre = %s"
        params.append(filtros["hotel"])

    if filtros.get("ciudad"):
        query += " AND ht.ciudad_localidad = %s"
        params.append(filtros["ciudad"])

    if filtros.get("nacionalidad"):
        query += " AND h.nacionalidad ILIKE %s"
        params.append(f"%{filtros['nacionalidad']}%")

    if filtros.get("dni"):
        query += " AND h.dni_pasaporte ILIKE %s"
        params.append(f"%{filtros['dni']}%")

    if filtros.get("profesion"):
        query += " AND h.profesion ILIKE %s"
        params.append(f"%{filtros['profesion']}%")

    if filtros.get("procedencia"):
        query += " AND h.procedencia ILIKE %s"
        params.append(f"%{filtros['procedencia']}%")

    if filtros.get("fecha_desde"):
        ok, _, fecha = validar_fecha(filtros["fecha_desde"], permite_vacio=True)
        if ok and fecha:
            query += " AND h.fecha_entrada >= %s"
            params.append(fecha)

    if filtros.get("fecha_hasta"):
        ok, _, fecha = validar_fecha(filtros["fecha_hasta"], permite_vacio=True)
        if ok and fecha:
            query += " AND h.fecha_entrada <= %s"
            params.append(fecha)

    if filtros.get("edad_min"):
        try:
            query += " AND h.edad >= %s"
            params.append(int(filtros["edad_min"]))
        except ValueError:
            pass

    if filtros.get("edad_max"):
        try:
            query += " AND h.edad <= %s"
            params.append(int(filtros["edad_max"]))
        except ValueError:
            pass

    if filtros.get("habitacion"):
        query += " AND h.habitacion ILIKE %s"
        params.append(f"%{filtros['habitacion']}%")

    if filtros.get("destino"):
        query += " AND h.destino ILIKE %s"
        params.append(f"%{filtros['destino']}%")

    if filtros.get("telefono"):
        query += " AND h.telefono ILIKE %s"
        params.append(f"%{filtros['telefono']}%")

    query += " ORDER BY h.fecha_registro DESC"
    return _ejecutar_busqueda_paginada(query, params, page, per_page)


def _ejecutar_busqueda_paginada(query, params, page, per_page):
    """Ejecuta una búsqueda con paginación server-side."""
    try:
        # Contar total
        count_query = f"SELECT COUNT(*) as total FROM ({query}) sub"
        count_result = db.ejecutar_query_one(count_query, tuple(params))
        total = count_result["total"] if count_result else 0

        # Calcular páginas
        total_pages = max(1, (total + per_page - 1) // per_page)
        page = max(1, min(page, total_pages))
        offset = (page - 1) * per_page

        # Ejecutar con paginación
        query_paginada = query + f" LIMIT {per_page} OFFSET {offset}"
        resultados = db.ejecutar_query(query_paginada, tuple(params), fetch=True)

        # Formatear resultados
        datos = []
        for r in (resultados or []):
            datos.append({
                "id": r["id"],
                "hotel": r["hotel"],
                "apellido_nombre": r["apellido_nombre"],
                "dni_pasaporte": formato_dni(str(r["dni_pasaporte"])) if r["dni_pasaporte"] else "",
                "dni_raw": r["dni_pasaporte"] or "",
                "nacionalidad": r.get("nacionalidad") or "",
                "procedencia": r.get("procedencia") or "",
                "edad": r.get("edad") or "",
                "profesion": r.get("profesion") or "",
                "fecha_entrada": formato_fecha(r.get("fecha_entrada")),
                "fecha_salida": formato_fecha(r.get("fecha_salida")),
                "habitacion": r.get("habitacion") or "",
                "telefono": r.get("telefono") or "",
                "domicilio": r.get("domicilio") or "",
                "destino": r.get("destino") or "",
                "movilidad": r.get("movilidad") or "",
                "origen_carga": r.get("origen_carga") or "",
            })

        return datos, total, total_pages, page

    except Exception as e:
        log_error("Error en búsqueda paginada", e)
        return [], 0, 1, 1


def obtener_huesped(huesped_id: int) -> dict | None:
    """Obtiene el detalle completo de un huésped."""
    try:
        resultado = db.ejecutar_query_one("""
            SELECT h.*, ht.nombre as hotel_nombre, ht.direccion as hotel_direccion,
                   ht.ciudad_localidad, u.nombre_completo as cargado_por
            FROM huespedes h
            JOIN hoteles ht ON h.hotel_id = ht.id
            LEFT JOIN usuarios u ON h.usuario_carga_id = u.id
            WHERE h.id = %s
        """, (huesped_id,))

        if resultado:
            return {
                "id": resultado["id"],
                "hotel_id": resultado["hotel_id"],
                "hotel_nombre": resultado["hotel_nombre"],
                "hotel_direccion": resultado.get("hotel_direccion") or "",
                "ciudad_localidad": resultado.get("ciudad_localidad") or "",
                "apellido_nombre": resultado["apellido_nombre"],
                "dni_pasaporte": formato_dni(str(resultado["dni_pasaporte"])) if resultado["dni_pasaporte"] else "",
                "dni_raw": resultado.get("dni_pasaporte") or "",
                "nacionalidad": resultado.get("nacionalidad") or "",
                "procedencia": resultado.get("procedencia") or "",
                "fecha_nacimiento": formato_fecha(resultado.get("fecha_nacimiento")),
                "edad": resultado.get("edad") or "",
                "profesion": resultado.get("profesion") or "",
                "fecha_entrada": formato_fecha(resultado.get("fecha_entrada")),
                "fecha_salida": formato_fecha(resultado.get("fecha_salida")),
                "habitacion": resultado.get("habitacion") or "",
                "domicilio": resultado.get("domicilio") or "",
                "destino": resultado.get("destino") or "",
                "movilidad": resultado.get("movilidad") or "",
                "telefono": resultado.get("telefono") or "",
                "origen_carga": resultado.get("origen_carga") or "",
                "cargado_por": resultado.get("cargado_por") or "",
                "fecha_registro": formato_fecha(resultado.get("fecha_registro")),
            }
        return None

    except Exception as e:
        log_error(f"Error al obtener huésped {huesped_id}", e)
        return None


def eliminar_huesped(huesped_id: int, usuario_id: int) -> tuple[bool, str]:
    """Elimina un huésped de la base de datos."""
    try:
        db.ejecutar_query("DELETE FROM huespedes WHERE id = %s", (huesped_id,))
        log_info(f"Huésped ID {huesped_id} eliminado por usuario {usuario_id}")
        return True, "Registro eliminado correctamente"
    except Exception as e:
        log_error(f"Error al eliminar huésped {huesped_id}", e)
        return False, f"Error al eliminar: {str(e)}"


def verificar_duplicado_dni(dni: str) -> list:
    """Verifica si ya existe un huésped con el mismo DNI."""
    if not dni:
        return []
    try:
        resultado = db.ejecutar_query(
            "SELECT h.apellido_nombre, ht.nombre as hotel "
            "FROM huespedes h JOIN hoteles ht ON h.hotel_id = ht.id "
            "WHERE h.dni_pasaporte = %s ORDER BY h.fecha_entrada DESC LIMIT 3",
            (dni.replace(".", "").replace("-", ""),),
            fetch=True
        )
        return resultado if resultado else []
    except Exception:
        return []


def crear_huesped(datos: dict, usuario_id: int) -> tuple[bool, str, int | None]:
    """
    Crea un nuevo huésped. 
    datos debe contener: hotel_id, apellido_nombre, dni_pasaporte, 
    y opcionalmente todos los demás campos.
    Retorna (exito, mensaje, huesped_id).
    """
    # Validaciones
    errores = []

    if not datos.get("hotel_id") and not datos.get("hotel_nombre"):
        errores.append("Hotel es requerido")

    ok, msg = validar_texto_obligatorio(datos.get("apellido_nombre", ""), "Apellido y Nombre", min_len=3)
    if not ok:
        errores.append(msg)

    ok, msg = validar_dni(datos.get("dni_pasaporte", ""))
    if not ok:
        errores.append(msg)

    # Fechas opcionales
    fecha_nac = None
    if datos.get("fecha_nacimiento"):
        ok, msg, fecha_nac = validar_fecha(datos["fecha_nacimiento"], permite_vacio=True)
        if not ok:
            errores.append(msg)

    fecha_entrada = None
    if datos.get("fecha_entrada"):
        ok, msg, fecha_entrada = validar_fecha(datos["fecha_entrada"], permite_vacio=True)
        if not ok:
            errores.append(msg)

    fecha_salida = None
    if datos.get("fecha_salida"):
        ok, msg, fecha_salida = validar_fecha(datos["fecha_salida"], permite_vacio=True)
        if not ok:
            errores.append(msg)

    if fecha_entrada and fecha_salida:
        ok, msg = validar_fechas_estadia(fecha_entrada, fecha_salida)
        if not ok:
            errores.append(msg)

    edad = None
    if datos.get("edad"):
        ok, msg, edad = validar_edad(datos["edad"])
        if not ok:
            errores.append(msg)

    if datos.get("habitacion"):
        ok, msg, _ = validar_habitacion(datos["habitacion"])
        if not ok:
            errores.append(msg)

    if datos.get("telefono"):
        ok, msg, _ = validar_telefono(datos["telefono"])
        if not ok:
            errores.append(msg)

    if errores:
        return False, "Errores de validación:\n• " + "\n• ".join(errores), None

    try:
        conn = db.obtener_conexion()
        if not conn:
            return False, "No se pudo conectar a la base de datos", None

        cursor = conn.cursor()

        # Obtener o crear hotel
        hotel_id = datos.get("hotel_id")
        if datos.get("nuevo_hotel") and datos.get("hotel_nombre"):
            cursor.execute("""
                INSERT INTO hoteles (nombre, nro_orden, direccion, ciudad_localidad, usuario_registro_id)
                VALUES (%s, %s, %s, %s, %s) RETURNING id
            """, (
                sanitizar_texto(datos["hotel_nombre"]),
                sanitizar_texto(datos.get("nro_orden", "")),
                sanitizar_texto(datos.get("direccion_hotel", "")),
                sanitizar_texto(datos.get("ciudad_hotel", "")),
                usuario_id
            ))
            hotel_id = cursor.fetchone()[0]
        elif not hotel_id and datos.get("hotel_nombre"):
            cursor.execute("SELECT id FROM hoteles WHERE nombre = %s", (datos["hotel_nombre"],))
            result = cursor.fetchone()
            if not result:
                db.liberar_conexion(conn)
                return False, "Hotel no encontrado. Marque 'Registrar nuevo hotel'.", None
            hotel_id = result[0]

        # Insertar huésped
        cursor.execute("""
            INSERT INTO huespedes (
                hotel_id, nacionalidad, procedencia, apellido_nombre,
                dni_pasaporte, fecha_nacimiento, edad, profesion,
                fecha_entrada, fecha_salida,
                habitacion, domicilio, destino, movilidad, telefono,
                origen_carga, usuario_carga_id
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'manual', %s)
            RETURNING id
        """, (
            hotel_id,
            sanitizar_texto(datos.get("nacionalidad", "")),
            sanitizar_texto(datos.get("procedencia", "")),
            sanitizar_texto(datos.get("apellido_nombre", "")),
            sanitizar_texto(datos.get("dni_pasaporte", "").replace(".", "").replace("-", "")),
            fecha_nac,
            edad,
            sanitizar_texto(datos.get("profesion", "")),
            fecha_entrada,
            fecha_salida,
            sanitizar_texto(datos.get("habitacion", "")),
            sanitizar_texto(datos.get("domicilio", "")),
            sanitizar_texto(datos.get("destino", "")),
            sanitizar_texto(datos.get("movilidad", "")),
            sanitizar_texto(datos.get("telefono", "")),
            usuario_id
        ))
        huesped_id = cursor.fetchone()[0]

        conn.commit()
        cursor.close()
        db.liberar_conexion(conn)

        # Auditoría
        try:
            conn_aud = db.obtener_conexion()
            if conn_aud:
                Auditoria(conn_aud).registrar(
                    usuario_id, "carga_manual", "huespedes",
                    registro_id=huesped_id,
                    detalle=f"Huésped: {datos.get('apellido_nombre', '')}"
                )
                db.liberar_conexion(conn_aud)
        except Exception:
            pass

        log_info(f"Huésped creado: {datos.get('apellido_nombre', '')} (ID: {huesped_id})")
        return True, "Huésped registrado correctamente", huesped_id

    except Exception as e:
        log_error("Error al crear huésped", e)
        return False, f"Error al guardar: {str(e)}", None


def obtener_hoteles_lista() -> list:
    """Obtiene lista de hoteles activos para combos/selects."""
    try:
        resultado = db.ejecutar_query(
            "SELECT id, nombre, ciudad_localidad FROM hoteles WHERE activo = TRUE ORDER BY nombre",
            fetch=True
        )
        return resultado if resultado else []
    except Exception as e:
        log_error("Error al obtener hoteles", e)
        return []


def obtener_ciudades_lista() -> list:
    """Obtiene lista de ciudades distintas."""
    try:
        result = db.ejecutar_query(
            "SELECT DISTINCT ciudad_localidad FROM hoteles "
            "WHERE ciudad_localidad IS NOT NULL AND ciudad_localidad != '' ORDER BY ciudad_localidad",
            fetch=True
        )
        return [r["ciudad_localidad"] for r in result] if result else []
    except Exception:
        return []
