"""
S.C.A.H. - Modelos / Esquema de base de datos
Definiciones SQL para todas las tablas del sistema
"""

# ============================================================
# TABLA: USUARIOS
# ============================================================
SQL_CREATE_USUARIOS = """
CREATE TABLE IF NOT EXISTS usuarios (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    nombre_completo VARCHAR(200) NOT NULL,
    rol VARCHAR(20) NOT NULL DEFAULT 'consulta',
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    fecha_creacion TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    ultimo_acceso TIMESTAMP,
    CONSTRAINT chk_rol CHECK (rol IN ('admin', 'operador', 'consulta'))
);
"""

# ============================================================
# TABLA: HOTELES
# ============================================================
SQL_CREATE_HOTELES = """
CREATE TABLE IF NOT EXISTS hoteles (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(300) NOT NULL,
    nro_orden VARCHAR(50),
    direccion VARCHAR(500),
    ciudad_localidad VARCHAR(200),
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    fecha_registro TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    usuario_registro_id INTEGER REFERENCES usuarios(id)
);
"""

# ============================================================
# TABLA: HUÉSPEDES
# ============================================================
SQL_CREATE_HUESPEDES = """
CREATE TABLE IF NOT EXISTS huespedes (
    id SERIAL PRIMARY KEY,
    hotel_id INTEGER NOT NULL REFERENCES hoteles(id) ON DELETE CASCADE,
    nacionalidad VARCHAR(100),
    procedencia VARCHAR(200),
    apellido_nombre VARCHAR(300) NOT NULL,
    dni_pasaporte VARCHAR(50),
    fecha_nacimiento DATE,
    edad INTEGER,
    profesion VARCHAR(200),
    fecha_entrada DATE,
    fecha_salida DATE,
    habitacion VARCHAR(20),
    domicilio VARCHAR(500),
    destino VARCHAR(200),
    movilidad VARCHAR(200),
    telefono VARCHAR(50),
    origen_carga VARCHAR(20) NOT NULL DEFAULT 'manual',
    usuario_carga_id INTEGER REFERENCES usuarios(id),
    fecha_registro TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_origen CHECK (origen_carga IN ('excel', 'excel_v2', 'manual'))
);
"""

# ============================================================
# TABLA: LOG DE IMPORTACIONES
# ============================================================
SQL_CREATE_IMPORTACIONES_LOG = """
CREATE TABLE IF NOT EXISTS importaciones_log (
    id SERIAL PRIMARY KEY,
    archivo_nombre VARCHAR(500) NOT NULL,
    hoja_nombre VARCHAR(200),
    fecha_importacion TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    usuario_id INTEGER REFERENCES usuarios(id),
    registros_importados INTEGER DEFAULT 0,
    registros_error INTEGER DEFAULT 0,
    registros_duplicados INTEGER DEFAULT 0,
    estado VARCHAR(20) NOT NULL DEFAULT 'completado',
    detalle TEXT,
    CONSTRAINT chk_estado_imp CHECK (estado IN ('completado', 'parcial', 'error'))
);
"""

# ============================================================
# TABLA: AUDITORÍA
# ============================================================
SQL_CREATE_AUDITORIA = """
CREATE TABLE IF NOT EXISTS auditoria (
    id SERIAL PRIMARY KEY,
    usuario_id INTEGER REFERENCES usuarios(id),
    accion VARCHAR(100) NOT NULL,
    tabla_afectada VARCHAR(50),
    registro_id INTEGER,
    detalle TEXT,
    fecha TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""

# ============================================================
# ÍNDICES
# ============================================================
SQL_CREATE_INDICES = [
    "CREATE INDEX IF NOT EXISTS idx_huespedes_hotel ON huespedes(hotel_id);",
    "CREATE INDEX IF NOT EXISTS idx_huespedes_dni ON huespedes(dni_pasaporte);",
    "CREATE INDEX IF NOT EXISTS idx_huespedes_nombre ON huespedes(apellido_nombre);",
    "CREATE INDEX IF NOT EXISTS idx_huespedes_entrada ON huespedes(fecha_entrada);",
    "CREATE INDEX IF NOT EXISTS idx_huespedes_salida ON huespedes(fecha_salida);",
    "CREATE INDEX IF NOT EXISTS idx_huespedes_nacionalidad ON huespedes(nacionalidad);",
    "CREATE INDEX IF NOT EXISTS idx_huespedes_habitacion ON huespedes(habitacion);",
    "CREATE INDEX IF NOT EXISTS idx_huespedes_telefono ON huespedes(telefono);",
    "CREATE INDEX IF NOT EXISTS idx_hoteles_nombre ON hoteles(nombre);",
    "CREATE INDEX IF NOT EXISTS idx_hoteles_ciudad ON hoteles(ciudad_localidad);",
    "CREATE INDEX IF NOT EXISTS idx_auditoria_usuario ON auditoria(usuario_id);",
    "CREATE INDEX IF NOT EXISTS idx_auditoria_fecha ON auditoria(fecha);",
    "CREATE INDEX IF NOT EXISTS idx_usuarios_username ON usuarios(username);",
]

# Lista de todas las sentencias de creación en orden
ALL_TABLES = [
    SQL_CREATE_USUARIOS,
    SQL_CREATE_HOTELES,
    SQL_CREATE_HUESPEDES,
    SQL_CREATE_IMPORTACIONES_LOG,
    SQL_CREATE_AUDITORIA,
]
