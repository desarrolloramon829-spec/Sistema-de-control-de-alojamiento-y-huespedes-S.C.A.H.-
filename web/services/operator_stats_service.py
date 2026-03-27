"""
S.C.A.H. Web - Servicio de Estadísticas de Cargas por Operador
Queries para el módulo de control de cargas (solo admin).
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from datetime import datetime, timedelta
from database.connection import db
from utils.logger import log_error


def obtener_resumen_cargas(fecha_desde=None, fecha_hasta=None):
    """Retorna KPIs globales de cargas en el período."""
    try:
        where, params = _build_date_filter(fecha_desde, fecha_hasta, "h.fecha_registro")

        # Total cargas en el período
        row = db.ejecutar_query_one(
            f"SELECT COUNT(*) AS total FROM huespedes h WHERE 1=1 {where}", params
        )
        total = row["total"] if row else 0

        # Operadores activos (que cargaron al menos 1 registro)
        row2 = db.ejecutar_query_one(
            f"""SELECT COUNT(DISTINCT h.usuario_carga_id) AS activos
                FROM huespedes h WHERE h.usuario_carga_id IS NOT NULL {where}""",
            params
        )
        operadores_activos = row2["activos"] if row2 else 0

        # Días en el rango para promedio diario
        if fecha_desde and fecha_hasta:
            try:
                d1 = datetime.strptime(fecha_desde, "%Y-%m-%d")
                d2 = datetime.strptime(fecha_hasta, "%Y-%m-%d")
                dias = max((d2 - d1).days, 1)
            except ValueError:
                dias = 30
        else:
            dias = 30
        promedio_diario = round(total / dias, 1) if dias > 0 else 0

        # Tipo de carga predominante
        rows = db.ejecutar_query(
            f"""SELECT h.origen_carga, COUNT(*) AS cnt
                FROM huespedes h WHERE 1=1 {where}
                GROUP BY h.origen_carga ORDER BY cnt DESC LIMIT 1""",
            params, fetch=True
        )
        tipo_predominante = _label_origen(rows[0]["origen_carga"]) if rows else "N/A"

        # Cargas por tipo
        rows_tipo = db.ejecutar_query(
            f"""SELECT h.origen_carga, COUNT(*) AS cnt
                FROM huespedes h WHERE 1=1 {where}
                GROUP BY h.origen_carga ORDER BY cnt DESC""",
            params, fetch=True
        ) or []
        por_tipo = {r["origen_carga"]: r["cnt"] for r in rows_tipo}

        return {
            "total": total,
            "operadores_activos": operadores_activos,
            "promedio_diario": promedio_diario,
            "tipo_predominante": tipo_predominante,
            "por_tipo": {
                "excel": por_tipo.get("excel", 0),
                "excel_v2": por_tipo.get("excel_v2", 0),
                "manual": por_tipo.get("manual", 0),
            }
        }
    except Exception as e:
        log_error("Error obteniendo resumen de cargas", e)
        return {
            "total": 0, "operadores_activos": 0,
            "promedio_diario": 0, "tipo_predominante": "N/A",
            "por_tipo": {"excel": 0, "excel_v2": 0, "manual": 0}
        }


def obtener_cargas_por_operador(fecha_desde=None, fecha_hasta=None):
    """Retorna tabla de métricas de cargas por cada usuario."""
    try:
        where, params = _build_date_filter(fecha_desde, fecha_hasta, "h.fecha_registro")

        rows = db.ejecutar_query(
            f"""SELECT
                    u.id AS usuario_id,
                    u.nombre_completo,
                    u.username,
                    u.rol,
                    COUNT(*) AS total,
                    SUM(CASE WHEN h.origen_carga = 'excel' THEN 1 ELSE 0 END) AS excel_v1,
                    SUM(CASE WHEN h.origen_carga = 'excel_v2' THEN 1 ELSE 0 END) AS excel_v2,
                    SUM(CASE WHEN h.origen_carga = 'manual' THEN 1 ELSE 0 END) AS manual,
                    MAX(h.fecha_registro) AS ultima_carga
                FROM huespedes h
                JOIN usuarios u ON h.usuario_carga_id = u.id
                WHERE 1=1 {where}
                GROUP BY u.id, u.nombre_completo, u.username, u.rol
                ORDER BY total DESC""",
            params, fetch=True
        ) or []

        # Obtener errores y duplicados de importaciones_log por usuario
        imp_where, imp_params = _build_date_filter(fecha_desde, fecha_hasta, "il.fecha_importacion")
        imp_rows = db.ejecutar_query(
            f"""SELECT
                    il.usuario_id,
                    COALESCE(SUM(il.registros_error), 0) AS errores,
                    COALESCE(SUM(il.registros_duplicados), 0) AS duplicados
                FROM importaciones_log il
                WHERE il.usuario_id IS NOT NULL {imp_where}
                GROUP BY il.usuario_id""",
            imp_params, fetch=True
        ) or []
        imp_map = {r["usuario_id"]: r for r in imp_rows}

        total_general = sum(r["total"] for r in rows)

        resultado = []
        for r in rows:
            imp = imp_map.get(r["usuario_id"], {})
            porcentaje = round((r["total"] / total_general * 100), 1) if total_general > 0 else 0
            resultado.append({
                "usuario_id": r["usuario_id"],
                "nombre": r["nombre_completo"] or r["username"],
                "username": r["username"],
                "rol": r["rol"],
                "total": r["total"],
                "excel_v1": r["excel_v1"],
                "excel_v2": r["excel_v2"],
                "manual": r["manual"],
                "errores": imp.get("errores", 0),
                "duplicados": imp.get("duplicados", 0),
                "ultima_carga": r["ultima_carga"].strftime("%d/%m/%Y %H:%M") if r["ultima_carga"] else "-",
                "porcentaje": porcentaje,
            })

        return resultado
    except Exception as e:
        log_error("Error obteniendo cargas por operador", e)
        return []


def obtener_tendencia_cargas(fecha_desde=None, fecha_hasta=None):
    """Retorna serie temporal de cargas agrupada por día y usuario para gráficos."""
    try:
        where, params = _build_date_filter(fecha_desde, fecha_hasta, "h.fecha_registro")

        rows = db.ejecutar_query(
            f"""SELECT
                    DATE(h.fecha_registro) AS dia,
                    u.nombre_completo,
                    u.username,
                    COUNT(*) AS cnt
                FROM huespedes h
                JOIN usuarios u ON h.usuario_carga_id = u.id
                WHERE 1=1 {where}
                GROUP BY DATE(h.fecha_registro), u.nombre_completo, u.username
                ORDER BY dia""",
            params, fetch=True
        ) or []

        # Agrupar por usuario → {nombre: {dia: cnt}}
        usuarios = {}
        dias_set = set()
        for r in rows:
            nombre = r["nombre_completo"] or r["username"]
            dia = r["dia"].strftime("%d/%m") if hasattr(r["dia"], "strftime") else str(r["dia"])
            dias_set.add(dia)
            if nombre not in usuarios:
                usuarios[nombre] = {}
            usuarios[nombre][dia] = r["cnt"]

        dias = sorted(dias_set, key=lambda d: datetime.strptime(d, "%d/%m") if "/" in d else d)

        datasets = []
        palette = [
            "#23c0ff", "#2bd67b", "#f3b63f", "#e25555", "#a97ef8",
            "#fd7e14", "#20c997", "#d63384", "#6610f2", "#0dcaf0"
        ]
        for i, (nombre, data) in enumerate(usuarios.items()):
            color = palette[i % len(palette)]
            datasets.append({
                "label": nombre,
                "data": [data.get(d, 0) for d in dias],
                "borderColor": color,
                "backgroundColor": color + "33",
                "tension": 0.3,
                "fill": False,
            })

        # Tendencia global por tipo
        rows_tipo = db.ejecutar_query(
            f"""SELECT
                    DATE(h.fecha_registro) AS dia,
                    h.origen_carga,
                    COUNT(*) AS cnt
                FROM huespedes h
                WHERE 1=1 {where}
                GROUP BY DATE(h.fecha_registro), h.origen_carga
                ORDER BY dia""",
            params, fetch=True
        ) or []

        tipo_data = {"excel": {}, "excel_v2": {}, "manual": {}}
        for r in rows_tipo:
            dia = r["dia"].strftime("%d/%m") if hasattr(r["dia"], "strftime") else str(r["dia"])
            origen = r["origen_carga"]
            if origen in tipo_data:
                tipo_data[origen][dia] = r["cnt"]

        tipo_datasets = []
        tipo_colors = {"excel": "#23c0ff", "excel_v2": "#2bd67b", "manual": "#f3b63f"}
        for origen, data in tipo_data.items():
            color = tipo_colors[origen]
            tipo_datasets.append({
                "label": _label_origen(origen),
                "data": [data.get(d, 0) for d in dias],
                "borderColor": color,
                "backgroundColor": color + "33",
                "tension": 0.3,
                "fill": False,
            })

        return {
            "labels": dias,
            "por_operador": datasets,
            "por_tipo": tipo_datasets,
        }
    except Exception as e:
        log_error("Error obteniendo tendencia de cargas", e)
        return {"labels": [], "por_operador": [], "por_tipo": []}


def obtener_detalle_operador(usuario_id, fecha_desde=None, fecha_hasta=None):
    """Retorna detalle de cargas de un operador específico."""
    try:
        where, params = _build_date_filter(fecha_desde, fecha_hasta, "h.fecha_registro")
        params_user = (usuario_id,) + params

        # Info del usuario
        usuario = db.ejecutar_query_one(
            "SELECT id, nombre_completo, username, rol FROM usuarios WHERE id = %s",
            (usuario_id,)
        )
        if not usuario:
            return None

        # Cargas del usuario por día
        por_dia = db.ejecutar_query(
            f"""SELECT DATE(h.fecha_registro) AS dia, COUNT(*) AS cnt
                FROM huespedes h
                WHERE h.usuario_carga_id = %s {where}
                GROUP BY DATE(h.fecha_registro) ORDER BY dia""",
            params_user, fetch=True
        ) or []

        # Por hotel
        por_hotel = db.ejecutar_query(
            f"""SELECT ho.nombre AS hotel, COUNT(*) AS cnt
                FROM huespedes h
                JOIN hoteles ho ON h.hotel_id = ho.id
                WHERE h.usuario_carga_id = %s {where}
                GROUP BY ho.nombre ORDER BY cnt DESC LIMIT 15""",
            params_user, fetch=True
        ) or []

        # Por tipo de carga
        por_tipo = db.ejecutar_query(
            f"""SELECT h.origen_carga, COUNT(*) AS cnt
                FROM huespedes h
                WHERE h.usuario_carga_id = %s {where}
                GROUP BY h.origen_carga ORDER BY cnt DESC""",
            params_user, fetch=True
        ) or []

        # Importaciones del usuario (errores/duplicados)
        imp_where, imp_params = _build_date_filter(fecha_desde, fecha_hasta, "il.fecha_importacion")
        imp_params_user = (usuario_id,) + imp_params
        importaciones = db.ejecutar_query(
            f"""SELECT
                    COALESCE(SUM(il.registros_importados), 0) AS importados,
                    COALESCE(SUM(il.registros_error), 0) AS errores,
                    COALESCE(SUM(il.registros_duplicados), 0) AS duplicados,
                    COUNT(*) AS total_importaciones
                FROM importaciones_log il
                WHERE il.usuario_id = %s {imp_where}""",
            imp_params_user, fetch=True
        )
        imp = importaciones[0] if importaciones else {}

        total_cargados = sum(r["cnt"] for r in por_tipo)
        total_importados = imp.get("importados", 0)
        total_errores = imp.get("errores", 0)
        total_duplicados = imp.get("duplicados", 0)
        calidad = round(
            (total_importados / (total_importados + total_errores + total_duplicados) * 100), 1
        ) if (total_importados + total_errores + total_duplicados) > 0 else 100.0

        return {
            "usuario": {
                "id": usuario["id"],
                "nombre": usuario["nombre_completo"] or usuario["username"],
                "username": usuario["username"],
                "rol": usuario["rol"],
            },
            "total": total_cargados,
            "calidad": calidad,
            "importaciones": {
                "total": imp.get("total_importaciones", 0),
                "importados": total_importados,
                "errores": total_errores,
                "duplicados": total_duplicados,
            },
            "por_dia": {
                "labels": [r["dia"].strftime("%d/%m") if hasattr(r["dia"], "strftime") else str(r["dia"]) for r in por_dia],
                "values": [r["cnt"] for r in por_dia],
            },
            "por_hotel": {
                "labels": [r["hotel"] for r in por_hotel],
                "values": [r["cnt"] for r in por_hotel],
            },
            "por_tipo": {
                "labels": [_label_origen(r["origen_carga"]) for r in por_tipo],
                "values": [r["cnt"] for r in por_tipo],
            },
        }
    except Exception as e:
        log_error(f"Error obteniendo detalle de operador {usuario_id}", e)
        return None


# ---------- Utilidades ----------

def _build_date_filter(fecha_desde, fecha_hasta, col):
    """Construye cláusula WHERE y parámetros para filtro de fechas."""
    where = ""
    params = ()
    if fecha_desde:
        where += f" AND {col} >= %s"
        params += (fecha_desde,)
    if fecha_hasta:
        where += f" AND {col} <= %s"
        params += (fecha_hasta + " 23:59:59",)
    return where, params


def _label_origen(origen):
    """Retorna etiqueta legible del origen de carga."""
    return {
        "excel": "Excel V1",
        "excel_v2": "Excel V2",
        "manual": "Manual",
    }.get(origen, origen or "Desconocido")
