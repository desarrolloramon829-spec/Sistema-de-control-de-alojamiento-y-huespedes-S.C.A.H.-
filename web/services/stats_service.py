"""
S.C.A.H. Web - Servicio de Estadísticas
Queries para dashboard y gráficos estadísticos.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from datetime import datetime
from collections import Counter
import re
import unicodedata
from database.connection import db
from utils.logger import log_error
from utils.formatters import formato_fecha


ARGENTINA_ALIASES = {
    'argentina', 'argentina republica', 'republica argentina', 'argentino',
    'arg', 'ar', 'argentina.', 'argentina republic', 'argento'
}

PROVINCIAS_ARGENTINAS = {
    'Buenos Aires': {'buenos aires', 'bs as', 'bs. as.', 'bsas', 'buenosaires', 'provincia de buenos aires', 'pba'},
    'CABA': {'caba', 'capital federal', 'ciudad autonoma de buenos aires', 'ciudad de buenos aires', 'capital', 'buenos aires capital'},
    'Catamarca': {'catamarca'},
    'Chaco': {'chaco'},
    'Chubut': {'chubut'},
    'Córdoba': {'cordoba', 'córdoba', 'cdoba'},
    'Corrientes': {'corrientes'},
    'Entre Ríos': {'entre rios', 'entre ríos'},
    'Formosa': {'formosa'},
    'Jujuy': {'jujuy'},
    'La Pampa': {'la pampa', 'lapampa'},
    'La Rioja': {'la rioja', 'larioja'},
    'Mendoza': {'mendoza'},
    'Misiones': {'misiones'},
    'Neuquén': {'neuquen', 'neuquén'},
    'Río Negro': {'rio negro', 'río negro'},
    'Salta': {'salta'},
    'San Juan': {'san juan', 'sanjuan', 's juan'},
    'San Luis': {'san luis', 'sanluis', 's luis'},
    'Santa Cruz': {'santa cruz', 'santacruz'},
    'Santa Fe': {'santa fe', 'santafe'},
    'Santiago del Estero': {'santiago del estero', 'santiagodelestero'},
    'Tierra del Fuego': {'tierra del fuego', 'tdf', 'tierra del fuego aiass'},
    'Tucumán': {'tucuman', 'tucumán', 'tuc'},
}

CONTINENTES = {
    'América del Sur': {
        'america del sur', 'sudamerica', 'sud américa', 'brasil', 'brazil', 'uruguay', 'paraguay',
        'bolivia', 'chile', 'peru', 'perú', 'ecuador', 'colombia', 'venezuela', 'guyana',
        'surinam', 'suriname', 'guayana francesa', 'venenzuela', 'argentina'
    },
    'América del Norte': {
        'america del norte', 'norteamerica', 'north america', 'estados unidos', 'usa', 'eeuu',
        'united states', 'canada', 'canadá', 'mexico', 'méxico', 'ee uu', 'ee. uu.', 'eeuu.', 'ee.uu.'
    },
    'América Central y Caribe': {
        'america central', 'centroamerica', 'caribe', 'costa rica', 'panama', 'panamá', 'guatemala',
        'honduras', 'el salvador', 'nicaragua', 'belice', 'cuba', 'republica dominicana',
        'república dominicana', 'haiti', 'haití', 'jamaica', 'puerto rico', 'trinidad y tobago'
    },
    'Europa': {
        'europa', 'españa', 'espana', 'spain', 'italia', 'italy', 'francia', 'france', 'alemania',
        'germany', 'portugal', 'reino unido', 'uk', 'inglaterra', 'england', 'irlanda', 'ireland',
        'suiza', 'switzerland', 'belgica', 'bélgica', 'holanda', 'paises bajos', 'países bajos',
        'netherlands', 'austria', 'polonia', 'poland', 'ucrania', 'ukraine', 'rusia', 'russia',
        'grecia', 'greece', 'croacia', 'croatia', 'suecia', 'sweden', 'noruega', 'norway',
        'dinamarca', 'denmark', 'finlandia', 'finland'
    },
    'Asia': {
        'asia', 'china', 'japon', 'japón', 'japan', 'corea', 'corea del sur', 'korea', 'india',
        'pakistan', 'pakistán', 'bangladesh', 'nepal', 'tailandia', 'thailand', 'vietnam',
        'filipinas', 'philippines', 'indonesia', 'malasia', 'malaysia', 'singapur', 'singapore',
        'israel', 'turquia', 'turquía', 'turkey', 'libano', 'líbano', 'arabia saudita', 'saudi arabia'
    },
    'África': {
        'africa', 'áfrica', 'marruecos', 'morocco', 'egipto', 'egypt', 'sudafrica', 'sudáfrica',
        'south africa', 'nigeria', 'kenia', 'kenya', 'etiopia', 'ethiopia', 'ghana', 'argelia',
        'algeria', 'tunisia', 'tunez', 'túnez'
    },
    'Oceanía': {
        'oceania', 'oceanía', 'australia', 'nueva zelanda', 'new zealand', 'fiji'
    },
}


def _normalizar_texto_geo(valor: str) -> str:
    if not valor:
        return ''

    texto = unicodedata.normalize('NFKD', str(valor))
    texto = ''.join(ch for ch in texto if not unicodedata.combining(ch))
    texto = texto.lower()
    texto = re.sub(r'[^a-z0-9\s]', ' ', texto)
    return re.sub(r'\s+', ' ', texto).strip()


def _es_argentino(nacionalidad: str) -> bool:
    nacionalidad_norm = _normalizar_texto_geo(nacionalidad)
    if not nacionalidad_norm:
        return False

    return nacionalidad_norm in ARGENTINA_ALIASES or nacionalidad_norm.startswith('argentin')


def _resolver_provincia(procedencia: str) -> str:
    procedencia_norm = _normalizar_texto_geo(procedencia)
    if not procedencia_norm:
        return 'Provincia no informada'

    for provincia, aliases in PROVINCIAS_ARGENTINAS.items():
        if procedencia_norm == _normalizar_texto_geo(provincia):
            return provincia
        if procedencia_norm in {_normalizar_texto_geo(alias) for alias in aliases}:
            return provincia
        if any(_normalizar_texto_geo(alias) in procedencia_norm for alias in aliases):
            return provincia

    return 'Provincia no reconocida'


def _resolver_continente(*valores: str) -> str:
    textos = [_normalizar_texto_geo(valor) for valor in valores if _normalizar_texto_geo(valor)]
    if not textos:
        return 'Continente no informado'

    for texto in textos:
        for continente, aliases in CONTINENTES.items():
            aliases_normalizados = {_normalizar_texto_geo(alias) for alias in aliases}
            if texto == _normalizar_texto_geo(continente):
                return continente
            if texto in aliases_normalizados:
                return continente
            if any(alias in texto for alias in aliases_normalizados):
                return continente

    return 'Continente no reconocido'


def _serie_desde_counter(counter: Counter, titulo: str, tipo_chart: str = 'bar') -> dict:
    items = sorted(counter.items(), key=lambda item: (-item[1], item[0]))
    return {
        'titulo': titulo,
        'labels': [label for label, _ in items],
        'values': [value for _, value in items],
        'tipo_chart': tipo_chart,
    }


def _obtener_estadistica_origen_geografico() -> dict:
    try:
        resultados = db.ejecutar_query(
            """
            SELECT nacionalidad, procedencia
            FROM huespedes
            WHERE COALESCE(TRIM(nacionalidad), '') != '' OR COALESCE(TRIM(procedencia), '') != ''
            """,
            fetch=True,
        ) or []

        argentinos = Counter()
        extranjeros = Counter()
        resumen = Counter({'Argentinos': 0, 'Extranjeros': 0, 'Sin clasificar': 0})

        for fila in resultados:
            nacionalidad = fila.get('nacionalidad') or ''
            procedencia = fila.get('procedencia') or ''

            if _es_argentino(nacionalidad):
                resumen['Argentinos'] += 1
                argentinos[_resolver_provincia(procedencia)] += 1
                continue

            if _normalizar_texto_geo(nacionalidad):
                resumen['Extranjeros'] += 1
                extranjeros[_resolver_continente(procedencia, nacionalidad)] += 1
                continue

            resumen['Sin clasificar'] += 1

        return {
            'modo': 'geografico',
            'titulo': 'Origen geográfico de huéspedes',
            'tipo_chart': 'bar',
            'labels': ['Argentinos', 'Extranjeros', 'Sin clasificar'],
            'values': [
                resumen['Argentinos'],
                resumen['Extranjeros'],
                resumen['Sin clasificar'],
            ],
            'series': {
                'argentinos': _serie_desde_counter(argentinos, 'Huéspedes argentinos por provincia'),
                'extranjeros': _serie_desde_counter(extranjeros, 'Huéspedes extranjeros por continente'),
            },
            'resumen': {
                'argentinos': resumen['Argentinos'],
                'extranjeros': resumen['Extranjeros'],
                'sin_clasificar': resumen['Sin clasificar'],
                'total': sum(resumen.values()),
            },
        }
    except Exception as e:
        log_error('Error al obtener estadística geográfica', e)
        return {
            'modo': 'geografico',
            'titulo': 'Origen geográfico de huéspedes',
            'tipo_chart': 'bar',
            'labels': ['Argentinos', 'Extranjeros', 'Sin clasificar'],
            'values': [0, 0, 0],
            'series': {
                'argentinos': {'titulo': 'Huéspedes argentinos por provincia', 'labels': [], 'values': [], 'tipo_chart': 'bar'},
                'extranjeros': {'titulo': 'Huéspedes extranjeros por continente', 'labels': [], 'values': [], 'tipo_chart': 'bar'},
            },
            'resumen': {'argentinos': 0, 'extranjeros': 0, 'sin_clasificar': 0, 'total': 0},
        }


def obtener_segmentacion_geografica() -> dict:
    """Retorna la segmentación geográfica reutilizable para dashboard, estadísticas y reportes."""
    return _obtener_estadistica_origen_geografico()


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
    if tipo == 'origen_geografico':
        return _obtener_estadistica_origen_geografico()

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
