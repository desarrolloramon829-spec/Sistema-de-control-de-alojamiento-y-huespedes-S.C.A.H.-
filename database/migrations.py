"""
S.C.A.H. - Migraciones de base de datos
Creación inicial de tablas, índices y datos semilla
"""

import bcrypt
from database.connection import db
from database.models import ALL_TABLES, SQL_CREATE_INDICES
from config import DEFAULT_ADMIN
from utils.logger import log_info, log_error


def ejecutar_migraciones():
    """Ejecuta todas las migraciones: crear tablas, índices y usuario admin."""
    log_info("Iniciando migraciones de base de datos...")

    conn = db.obtener_conexion()
    if not conn:
        log_error("No se pudo obtener conexión para migraciones")
        return False

    try:
        cursor = conn.cursor()

        # 1. Crear tablas
        for sql in ALL_TABLES:
            cursor.execute(sql)
            log_info(f"Tabla verificada/creada correctamente")

        # 2. Crear índices
        for idx_sql in SQL_CREATE_INDICES:
            cursor.execute(idx_sql)

        log_info("Índices creados correctamente")

        # 3. Crear usuario admin por defecto si no existe
        cursor.execute("SELECT id FROM usuarios WHERE username = %s", (DEFAULT_ADMIN["username"],))
        if not cursor.fetchone():
            password_hash = bcrypt.hashpw(
                DEFAULT_ADMIN["password"].encode("utf-8"),
                bcrypt.gensalt()
            ).decode("utf-8")

            cursor.execute("""
                INSERT INTO usuarios (username, password_hash, nombre_completo, rol, activo)
                VALUES (%s, %s, %s, %s, TRUE)
            """, (
                DEFAULT_ADMIN["username"],
                password_hash,
                DEFAULT_ADMIN["nombre_completo"],
                DEFAULT_ADMIN["rol"]
            ))
            log_info(f"Usuario admin creado: {DEFAULT_ADMIN['username']}")
        else:
            log_info("Usuario admin ya existe")

        conn.commit()
        cursor.close()
        log_info("Migraciones completadas exitosamente")

        # Ejecutar migraciones incrementales
        migrar_v1_1()

        return True

    except Exception as e:
        conn.rollback()
        log_error("Error durante las migraciones", e)
        return False
    finally:
        db.liberar_conexion(conn)


def verificar_esquema() -> tuple[bool, list]:
    """Verifica que todas las tablas necesarias existan."""
    tablas_necesarias = ["usuarios", "hoteles", "huespedes", "importaciones_log", "auditoria"]
    tablas_faltantes = []

    conn = db.obtener_conexion()
    if not conn:
        return False, tablas_necesarias

    try:
        cursor = conn.cursor()
        for tabla in tablas_necesarias:
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' AND table_name = %s
                )
            """, (tabla,))
            if not cursor.fetchone()[0]:
                tablas_faltantes.append(tabla)

        cursor.close()
        db.liberar_conexion(conn)

        if tablas_faltantes:
            return False, tablas_faltantes
        return True, []

    except Exception as e:
        log_error("Error al verificar esquema", e)
        db.liberar_conexion(conn)


# ============================================================
# MIGRACIÓN V1.1: Nuevas columnas para formato tabular V2
# ============================================================
SQL_MIGRACION_V1_1 = [
    "ALTER TABLE huespedes ADD COLUMN IF NOT EXISTS habitacion VARCHAR(20);",
    "ALTER TABLE huespedes ADD COLUMN IF NOT EXISTS domicilio VARCHAR(500);",
    "ALTER TABLE huespedes ADD COLUMN IF NOT EXISTS destino VARCHAR(200);",
    "ALTER TABLE huespedes ADD COLUMN IF NOT EXISTS movilidad VARCHAR(200);",
    "ALTER TABLE huespedes ADD COLUMN IF NOT EXISTS telefono VARCHAR(50);",
    "CREATE INDEX IF NOT EXISTS idx_huespedes_habitacion ON huespedes(habitacion);",
    "CREATE INDEX IF NOT EXISTS idx_huespedes_telefono ON huespedes(telefono);",
]


def migrar_v1_1():
    """Migración v1.1: Agrega columnas de habitación, domicilio, destino, movilidad y teléfono.
    También actualiza el constraint de origen_carga para incluir 'excel_v2'."""
    log_info("Ejecutando migración v1.1 (columnas formato tabular)...")

    conn = db.obtener_conexion()
    if not conn:
        log_error("No se pudo obtener conexión para migración v1.1")
        return False

    try:
        cursor = conn.cursor()

        for sql in SQL_MIGRACION_V1_1:
            try:
                cursor.execute(sql)
            except Exception as e:
                log_info(f"Nota migración v1.1: {e}")

        # Actualizar constraint de origen_carga para incluir 'excel_v2'
        try:
            cursor.execute("ALTER TABLE huespedes DROP CONSTRAINT IF EXISTS chk_origen;")
            cursor.execute(
                "ALTER TABLE huespedes ADD CONSTRAINT chk_origen "
                "CHECK (origen_carga IN ('excel', 'excel_v2', 'manual'));"
            )
        except Exception as e:
            log_info(f"Nota constraint: {e}")

        conn.commit()
        cursor.close()
        log_info("Migración v1.1 completada exitosamente")
        return True

    except Exception as e:
        conn.rollback()
        log_error("Error durante migración v1.1", e)
        return False
    finally:
        db.liberar_conexion(conn)
