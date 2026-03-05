"""
S.C.A.H. - Conexión a PostgreSQL
Pool de conexiones y gestión de la base de datos
"""

import os
import psycopg2
import psycopg2.pool
import psycopg2.extras
from config import DB_CONFIG
from utils.logger import log_info, log_error


def _get_connection_params() -> dict:
    """
    Obtiene los parámetros de conexión.
    Prioriza DATABASE_URL (para Render/Neon/Railway) sobre parámetros individuales.
    """
    database_url = os.environ.get("DATABASE_URL", "")

    if database_url:
        # Parsear DATABASE_URL (formato: postgresql://user:pass@host:port/dbname?sslmode=require)
        from urllib.parse import urlparse
        parsed = urlparse(database_url)
        params = {
            "host": parsed.hostname,
            "port": parsed.port or 5432,
            "dbname": parsed.path.lstrip("/"),
            "user": parsed.username,
            "password": parsed.password,
        }
        # Agregar sslmode para conexiones en la nube
        if parsed.query:
            params["sslmode"] = "require"
        else:
            params["sslmode"] = "require"  # Siempre SSL para URLs de nube
        return params

    # Fallback: parámetros individuales (uso local)
    return {
        "host": DB_CONFIG["host"],
        "port": DB_CONFIG["port"],
        "dbname": DB_CONFIG["dbname"],
        "user": DB_CONFIG["user"],
        "password": DB_CONFIG["password"],
    }


class DatabaseConnection:
    """Gestiona la conexión y pool de conexiones a PostgreSQL."""

    _instance = None
    _pool = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def inicializar(self):
        """Inicializa el pool de conexiones."""
        try:
            conn_params = _get_connection_params()
            self._conn_params = conn_params
            self._pool = psycopg2.pool.ThreadedConnectionPool(
                minconn=1,
                maxconn=10,
                **conn_params
            )
            log_info("Pool de conexiones a PostgreSQL inicializado correctamente")
            return True
        except UnicodeDecodeError:
            # Windows con locale en español puede generar errores de encoding
            # en los mensajes de error de psycopg2/socket
            log_error("Error de encoding al conectar a PostgreSQL. "
                      "Verifique que PostgreSQL esté en ejecución.")
            return False
        except psycopg2.OperationalError as e:
            log_error("No se pudo conectar a PostgreSQL", e)
            return False
        except Exception as e:
            log_error("Error al inicializar pool de conexiones", e)
            return False

    def obtener_conexion(self):
        """Obtiene una conexión del pool."""
        if self._pool is None:
            if not self.inicializar():
                return None
        try:
            conn = self._pool.getconn()
            conn.autocommit = False
            return conn
        except Exception as e:
            log_error("Error al obtener conexión del pool", e)
            return None

    def liberar_conexion(self, conn):
        """Devuelve una conexión al pool."""
        if self._pool and conn:
            try:
                self._pool.putconn(conn)
            except Exception as e:
                log_error("Error al liberar conexión", e)

    def cerrar_pool(self):
        """Cierra todas las conexiones del pool."""
        if self._pool:
            try:
                self._pool.closeall()
                log_info("Pool de conexiones cerrado")
            except Exception as e:
                log_error("Error al cerrar pool de conexiones", e)

    def ejecutar_query(self, query: str, params: tuple = None, fetch: bool = False):
        """Ejecuta una query y opcionalmente retorna resultados."""
        conn = self.obtener_conexion()
        if not conn:
            return None

        try:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute(query, params)

            if fetch:
                resultado = cursor.fetchall()
            else:
                resultado = cursor.rowcount

            conn.commit()
            cursor.close()
            return resultado
        except Exception as e:
            conn.rollback()
            log_error(f"Error ejecutando query: {query[:100]}", e)
            return None
        finally:
            self.liberar_conexion(conn)

    def ejecutar_query_one(self, query: str, params: tuple = None):
        """Ejecuta una query y retorna un solo resultado."""
        conn = self.obtener_conexion()
        if not conn:
            return None

        try:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute(query, params)
            resultado = cursor.fetchone()
            conn.commit()
            cursor.close()
            return resultado
        except Exception as e:
            conn.rollback()
            log_error(f"Error ejecutando query: {query[:100]}", e)
            return None
        finally:
            self.liberar_conexion(conn)

    def ejecutar_many(self, query: str, params_list: list):
        """Ejecuta una query múltiples veces con distintos parámetros."""
        conn = self.obtener_conexion()
        if not conn:
            return False

        try:
            cursor = conn.cursor()
            cursor.executemany(query, params_list)
            conn.commit()
            cursor.close()
            return True
        except Exception as e:
            conn.rollback()
            log_error(f"Error ejecutando query masiva: {query[:100]}", e)
            return False
        finally:
            self.liberar_conexion(conn)

    def test_conexion(self) -> tuple[bool, str]:
        """Prueba la conexión a la base de datos."""
        try:
            conn = self.obtener_conexion()
            if conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                cursor.close()
                self.liberar_conexion(conn)
                return True, "Conexión exitosa a PostgreSQL"
            return False, "No se pudo obtener conexión"
        except Exception as e:
            return False, f"Error de conexión: {str(e)}"

    @staticmethod
    def crear_base_datos():
        """Crea la base de datos si no existe (conecta a 'postgres' por defecto)."""
        # En entornos cloud (DATABASE_URL), la BD ya existe — no intentar crearla
        if os.environ.get("DATABASE_URL"):
            log_info("DATABASE_URL detectada — se omite creación de BD (ya existe en la nube)")
            return True

        try:
            conn = psycopg2.connect(
                host=DB_CONFIG["host"],
                port=DB_CONFIG["port"],
                dbname="postgres",
                user=DB_CONFIG["user"],
                password=DB_CONFIG["password"],
                client_encoding="utf8"
            )
            conn.autocommit = True
            cursor = conn.cursor()

            # Verificar si la base de datos existe
            cursor.execute(
                "SELECT 1 FROM pg_database WHERE datname = %s",
                (DB_CONFIG["dbname"],)
            )

            if not cursor.fetchone():
                cursor.execute(f'CREATE DATABASE "{DB_CONFIG["dbname"]}" ENCODING \'UTF8\'')
                log_info(f"Base de datos '{DB_CONFIG['dbname']}' creada exitosamente")
            else:
                log_info(f"Base de datos '{DB_CONFIG['dbname']}' ya existe")

            cursor.close()
            conn.close()
            return True
        except Exception as e:
            log_error("Error al crear base de datos", e)
            return False


# Instancia global (singleton)
db = DatabaseConnection()
