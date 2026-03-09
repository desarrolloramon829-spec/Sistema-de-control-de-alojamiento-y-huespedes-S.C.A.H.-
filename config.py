"""
S.C.A.H. - Sistema de Control de Alojamiento y Huéspedes
Archivo de configuración principal
"""

import os

# ============================================================
# CONFIGURACIÓN DE BASE DE DATOS POSTGRESQL
# ============================================================
DB_CONFIG = {
    "host": os.environ.get("SCAH_DB_HOST", "localhost"),
    "port": int(os.environ.get("SCAH_DB_PORT", 5432)),
    "dbname": os.environ.get("SCAH_DB_NAME", "scah_db"),
    "user": os.environ.get("SCAH_DB_USER", "postgres"),
    "password": os.environ.get("SCAH_DB_PASSWORD", "postgres"),
}

# ============================================================
# CONFIGURACIÓN DE LA APLICACIÓN
# ============================================================
APP_NAME = "S.C.A.H."
APP_FULL_NAME = "Sistema de Control de Alojamiento y Huéspedes"
APP_VERSION = "1.0.0"

# Dimensiones de la ventana principal
WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 720
WINDOW_MIN_WIDTH = 1024
WINDOW_MIN_HEIGHT = 600

# ============================================================
# ROLES DE USUARIO
# ============================================================
ROLES = {
    "admin": {
        "nombre": "Administrador",
        "descripcion": "Acceso total al sistema",
        "permisos": [
            "importar_excel", "carga_manual", "busqueda",
            "gestionar_hoteles", "gestionar_huespedes",
            "estadisticas", "reportes", "gestionar_usuarios",
            "editar_registros", "eliminar_registros", "backup"
        ]
    },
    "operador": {
        "nombre": "Operador",
        "descripcion": "Importar, cargar, buscar y exportar",
        "permisos": [
            "importar_excel", "carga_manual", "busqueda",
            "gestionar_hoteles", "gestionar_huespedes",
            "estadisticas", "reportes", "editar_registros"
        ]
    },
    "consulta": {
        "nombre": "Consulta",
        "descripcion": "Solo búsqueda y visualización",
        "permisos": [
            "busqueda", "estadisticas", "reportes"
        ]
    }
}

# ============================================================
# MAPEO DE COLUMNAS DEL EXCEL
# ============================================================
# Datos del hotel (columna A, filas fijas)
EXCEL_HOTEL_MAP = {
    "nombre": {"col": "A", "row": 2},
    "nro_orden": {"col": "A", "row": 4},
    "direccion": {"col": "A", "row": 5},
    "ciudad_localidad": {"col": "A", "row": 6},
}

# Datos de huéspedes (columnas fijas, filas dinámicas desde fila 2)
EXCEL_HUESPED_COLS = {
    "nacionalidad": "C",
    "procedencia": "D",
    "apellido_nombre": "E",
    "dni_pasaporte": "F",
    "fecha_nacimiento": "G",
    "edad": "H",
    "profesion": "I",
    "fecha_entrada": "J",
    "fecha_salida": "K",
}

EXCEL_HUESPED_START_ROW = 2  # Fila donde comienzan los datos de huéspedes

# ============================================================
# MAPEO DE COLUMNAS DEL EXCEL - FORMATO V2 (Tabular con encabezados)
# ============================================================
# Formato tabular con encabezados en fila 1, datos desde fila 2
# Columnas: FECHA | HABITACION | NOMBRE Y APELLIDO | EDAD | NACIONALIDAD |
#           PROFESION | PROCEDE | DOMICILIO | DESTINO | DOC | SALIDA | MOVILIDAD | TELEFONO
EXCEL_V2_HUESPED_COLS = {
    "fecha_entrada": "A",
    "habitacion": "B",
    "apellido_nombre": "C",
    "edad": "D",
    "nacionalidad": "E",
    "profesion": "F",
    "procedencia": "G",
    "domicilio": "H",
    "destino": "I",
    "dni_pasaporte": "J",
    "fecha_salida": "K",
    "movilidad": "L",
    "telefono": "M",
}

EXCEL_V2_HUESPED_START_ROW = 2

# Alias de encabezados para auto-detección del formato V2
EXCEL_V2_HEADER_ALIASES = {
    "fecha": "fecha_entrada",
    "fecha de entrada": "fecha_entrada",
    "entrada": "fecha_entrada",
    "habitacion": "habitacion",
    "habitación": "habitacion",
    "hab": "habitacion",
    "hab.": "habitacion",
    "nro hab": "habitacion",
    "nombre y apellido": "apellido_nombre",
    "apellido y nombre": "apellido_nombre",
    "nombre": "apellido_nombre",
    "apellido": "apellido_nombre",
    "huesped": "apellido_nombre",
    "huésped": "apellido_nombre",
    "edad": "edad",
    "nacionalidad": "nacionalidad",
    "nacion": "nacionalidad",
    "profesion": "profesion",
    "profesión": "profesion",
    "ocupacion": "profesion",
    "ocupación": "profesion",
    "procede": "procedencia",
    "procedencia": "procedencia",
    "origen": "procedencia",
    "domicilio": "domicilio",
    "direccion": "domicilio",
    "dirección": "domicilio",
    "destino": "destino",
    "doc": "dni_pasaporte",
    "documento": "dni_pasaporte",
    "dni": "dni_pasaporte",
    "dni/pasaporte": "dni_pasaporte",
    "pasaporte": "dni_pasaporte",
    "salida": "fecha_salida",
    "fecha de salida": "fecha_salida",
    "fecha salida": "fecha_salida",
    "movilidad": "movilidad",
    "vehiculo": "movilidad",
    "vehículo": "movilidad",
    "telefono": "telefono",
    "teléfono": "telefono",
    "tel": "telefono",
    "tel.": "telefono",
    "celular": "telefono",
}

# ============================================================
# CONFIGURACIÓN DE EXPORTACIÓN
# ============================================================
EXPORT_DIR = os.path.join(os.path.expanduser("~"), "Documents", "SCAH_Reportes")
os.makedirs(EXPORT_DIR, exist_ok=True)

# ============================================================
# RUTAS DE ASSETS
# ============================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
ICONS_DIR = os.path.join(ASSETS_DIR, "icons")

# ============================================================
# PAGINACIÓN
# ============================================================
DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 500

# ============================================================
# FORMATOS DE FECHA ACEPTADOS
# ============================================================
DATE_FORMATS = [
    "%d/%m/%Y",
    "%d-%m-%Y",
    "%Y-%m-%d",
    "%d/%m/%y",
    "%d-%m-%y",
]

DATE_DISPLAY_FORMAT = "%d/%m/%Y"

# ============================================================
# USUARIO ADMIN POR DEFECTO
# ============================================================
DEFAULT_ADMIN = {
    "username": "admin",
    "password": "admin123",  # Se cambiará en primer inicio
    "nombre_completo": "Administrador del Sistema",
    "rol": "admin"
}
