"""
S.C.A.H. Web - Servicio de Estadísticas
Queries para dashboard y gráficos estadísticos.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from datetime import datetime
from database.connection import db
from utils.logger import log_error
from utils.formatters import formato_fecha


def obtener_kpis() -> dict:
    """Obtiene los 4 KPIs del dashboard."""
    kpis = {"total_huespedes": 0, "hoteles_activos": 0, "alojados_hoy": 0, "importaciones": 0}
    try:
        res = db.ejecutar_query_one("SELECT COUNT(*) as total FROM huespedes")
        kpis["total_huespedes"] = res["total"] if res else 0

        res = db.ejecutar_query_one("SELECT COUNT(*) as total FROM hoteles WHERE activo = TRUE")
        kpis["hoteles_activos"] = res["total"] if res else 0

        hoy = datetime.now().date()
        res = db.ejecutar_query_one("""
            SELECT COUNT(*) as total FROM huespedes
            WHERE fecha_entrada <= %s AND (fecha_salida IS NULL OR fecha_salida >= %s)
        """, (hoy, hoy))
        kpis["alojados_hoy"] = res["total"] if res else 0

        res = db.ejecutar_query_one("SELECT COUNT(*) as total FROM importaciones_log")
        kpis["importaciones"] = res["total"] if res else 0

    except Exception as e:
        log_error("Error al obtener KPIs", e)

    return kpis


def obtener_ultimos_huespedes(limite: int = 10) -> list:
    """Obtiene los últimos huéspedes registrados."""
    try:
        resultados = db.ejecutar_query("""
            SELECT hu.id, hu.apellido_nombre, hu.dni_pasaporte, h.nombre as hotel,
                   hu.fecha_entrada, hu.nacionalidad
            FROM huespedes hu
            LEFT JOIN hoteles h ON hu.hotel_id = h.id
            ORDER BY hu.id DESC LIMIT %s
        """, (limite,), fetch=True)

        datos = []
        for r in (resultados or []):
            entrada = ""
            if r.get("fecha_entrada"):
                entrada = formato_fecha(r["fecha_entrada"])
            datos.append({
                "id": r.get("id"),
                "apellido_nombre": r.get("apellido_nombre") or "S/N",
                "dni_pasaporte": r.get("dni_pasaporte") or "",
                "hotel": r.get("hotel") or "",
                "fecha_entrada": entrada,
                "nacionalidad": r.get("nacionalidad") or "",
            })
        return datos

    except Exception as e:
        log_error("Error al obtener últimos huéspedes", e)
        return []


def obtener_top_ciudades(limite: int = 10) -> list:
    """Obtiene las ciudades con más huéspedes."""
    try:
        resultados = db.ejecutar_query("""
            SELECT h.ciudad_localidad, COUNT(hu.id) as total
            FROM hoteles h
            JOIN huespedes hu ON h.id = hu.hotel_id
            WHERE h.ciudad_localidad IS NOT NULL AND h.ciudad_localidad != ''
            GROUP BY h.ciudad_localidad
            ORDER BY total DESC
            LIMIT %s
        """, (limite,), fetch=True)

        if not resultados:
            return []

        max_total = resultados[0]["total"] if resultados else 1
        datos = []
        for r in resultados:
            datos.append({
                "ciudad": r["ciudad_localidad"],
                "total": r["total"],
                "porcentaje": round((r["total"] / max_total) * 100) if max_total > 0 else 0
            })
        return datos

    except Exception as e:
        log_error("Error al obtener top ciudades", e)
        return []


def obtener_estadistica(tipo: str) -> dict:
    """
    Obtiene datos de una estadística por tipo.
    Retorna dict con 'labels', 'values' y 'titulo'.
    """
    queries = {
        "nacionalidades": {
            "sql": """SELECT nacionalidad as label, COUNT(*) as total FROM huespedes
                      WHERE nacionalidad IS NOT NULL AND nacionalidad != ''
                      GROUP BY nacionalidad ORDER BY total DESC LIMIT 15""",
            "titulo": "Distribución por Nacionalidad",
            "tipo_chart": "bar"
        },
        "profesiones": {
            "sql": """SELECT profesion as label, COUNT(*) as total FROM huespedes
                      WHERE profesion IS NOT NULL AND profesion != ''
                      GROUP BY profesion ORDER BY total DESC LIMIT 15""",
            "titulo": "Top 15 Profesiones",
            "tipo_chart": "horizontalBar"
        },
        "procedencia": {
            "sql": """SELECT procedencia as label, COUNT(*) as total FROM huespedes
                      WHERE procedencia IS NOT NULL AND procedencia != ''
                      GROUP BY procedencia ORDER BY total DESC LIMIT 15""",
            "titulo": "Principales Procedencias",
            "tipo_chart": "bar"
        },
        "destinos": {
            "sql": """SELECT destino as label, COUNT(*) as total FROM huespedes
                      WHERE destino IS NOT NULL AND destino != ''
                      GROUP BY destino ORDER BY total DESC LIMIT 15""",
            "titulo": "Principales Destinos",
            "tipo_chart": "bar"
        },
        "por_hotel": {
            "sql": """SELECT h.nombre as label, COUNT(hu.id) as total
                      FROM hoteles h
                      LEFT JOIN huespedes hu ON h.id = hu.hotel_id
                      WHERE h.activo = TRUE
                      GROUP BY h.nombre ORDER BY total DESC""",
            "titulo": "Huéspedes por Hotel",
            "tipo_chart": "bar"
        },
        "edades": {
            "sql": """SELECT
                        CASE
                            WHEN edad < 18 THEN '0-17'
                            WHEN edad BETWEEN 18 AND 25 THEN '18-25'
                            WHEN edad BETWEEN 26 AND 35 THEN '26-35'
                            WHEN edad BETWEEN 36 AND 45 THEN '36-45'
                            WHEN edad BETWEEN 46 AND 55 THEN '46-55'
                            WHEN edad BETWEEN 56 AND 65 THEN '56-65'
                            WHEN edad > 65 THEN '65+'
                            ELSE 'S/D'
                        END as label,
                        COUNT(*) as total
                      FROM huespedes WHERE edad IS NOT NULL
                      GROUP BY label ORDER BY label""",
            "titulo": "Distribución por Rango de Edad",
            "tipo_chart": "bar"
        },
        "tendencia": {
            "sql": """SELECT TO_CHAR(fecha_entrada, 'YYYY-MM') as label, COUNT(*) as total
                      FROM huespedes
                      WHERE fecha_entrada IS NOT NULL
                        AND fecha_entrada >= CURRENT_DATE - INTERVAL '12 months'
                      GROUP BY label ORDER BY label""",
            "titulo": "Tendencia Mensual (último año)",
            "tipo_chart": "line"
        },
    }

    if tipo not in queries:
        return {"labels": [], "values": [], "titulo": "Estadística no encontrada", "tipo_chart": "bar"}

    config = queries[tipo]
    try:
        resultados = db.ejecutar_query(config["sql"], fetch=True)
        if resultados:
            labels = [r["label"] or "S/D" for r in resultados]
            values = [r["total"] for r in resultados]
        else:
            labels = []
            values = []

        return {
            "labels": labels,
            "values": values,
            "titulo": config["titulo"],
            "tipo_chart": config["tipo_chart"]
        }

    except Exception as e:
        log_error(f"Error en estadística '{tipo}'", e)
        return {"labels": [], "values": [], "titulo": config["titulo"], "tipo_chart": config["tipo_chart"]}
