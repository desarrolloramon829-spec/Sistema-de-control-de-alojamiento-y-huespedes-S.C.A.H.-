"""
S.C.A.H. - Conexión a PostgreSQL
Pool de conexiones y gestión de la base de datos
"""

import os
import threading
import time
import psycopg2
import psycopg2.pool
import psycopg2.extras
import psycopg2.extensions
from config import DB_CONFIG
from utils.logger import log_info, log_error

# Tiempo máximo (segundos) que una petición espera por una conexión libre
# antes de rendirse. Sin esto, psycopg2 lanza PoolError al instante.
POOL_WAIT_TIMEOUT = float(os.environ.get("SCAH_POOL_WAIT_TIMEOUT", 10))


def _is_cloud_environment() -> bool:
    """Detecta si estamos en un entorno cloud (Render/Neon/Railway)."""
    return bool(os.environ.get("DATABASE_URL") or os.environ.get("RENDER"))


def _get_connection_params() -> dict:
    """
    Obtiene los parámetros de conexión.
    Prioriza DATABASE_URL (para Render/Neon/Railway) sobre parámetros individuales.
    """
    database_url = os.environ.get("DATABASE_URL", "")

    if database_url:
        # Parsear DATABASE_URL (formato: postgresql://user:pass@host:port/dbname?sslmode=require)
        from urllib.parse import urlparse, parse_qs
        parsed = urlparse(database_url)
        query = parse_qs(parsed.query)
        return {
            "host": parsed.hostname,
            "port": parsed.port or 5432,
            "dbname": parsed.path.lstrip("/"),
            "user": parsed.username,
            "password": parsed.password,
            # SSL obligatorio por defecto (Neon, Render y similares lo exigen),
            # pero se respeta lo que indique la propia URL para poder apuntar a
            # un PostgreSQL local o dentro de una red privada sin TLS.
            "sslmode": query.get("sslmode", ["require"])[0],
        }

    # Fallback: parámetros individuales (uso local)
    return {
        "host": DB_CONFIG["host"],
        "port": DB_CONFIG["port"],
        "dbname": DB_CONFIG["dbname"],
        "user": DB_CONFIG["user"],
        "password": DB_CONFIG["password"],
    }


def _get_pool_limits() -> tuple[int, int]:
    """Retorna (minconn, maxconn) según el entorno.

    IMPORTANTE: el límite es POR PROCESO. El total de conexiones abiertas contra
    PostgreSQL es maxconn x (nro. de workers de Gunicorn). Con Neon Free
    (~20 conexiones) y 2 workers, 5 por worker deja margen para migraciones
    y para una consola psql abierta.
    """
    env_max = os.environ.get("SCAH_DB_POOL_MAX")
    if env_max:
        try:
            maxconn = max(2, int(env_max))
            return 1, maxconn
        except ValueError:
            pass

    if _is_cloud_environment():
        return 1, 5
    # Local: más generoso
    return 2, 10


def _conexion_utilizable(conn) -> bool:
    """Indica si una conexión del pool sigue siendo apta para usarse.

    Neon suspende el cómputo tras unos minutos de inactividad y cierra los
    sockets: sin esta comprobación, el pool devuelve conexiones muertas y la
    petición falla (o se cuelga) en vez de reconectar.
    """
    if conn is None or conn.closed:
        return False
    try:
        estado = conn.get_transaction_status()
    except Exception:
        return False
    if estado == psycopg2.extensions.TRANSACTION_STATUS_UNKNOWN:
        return False
    if estado != psycopg2.extensions.TRANSACTION_STATUS_IDLE:
        # Quedó una transacción abierta de un uso anterior: se aborta para no
        # heredar locks ni un "idle in transaction" que bloquee a otros.
        try:
            conn.rollback()
        except Exception:
            return False
    return True


def _get_keepalive_params() -> dict:
    """Retorna parámetros TCP keepalive para conexiones serverless (Neon.tech)."""
    if _is_cloud_environment():
        return {
            "keepalives": 1,
            "keepalives_idle": 30,
            "keepalives_interval": 10,
            "keepalives_count": 5,
            "options": "-c statement_timeout=30000",  # 30s max por query
        }
    return {
        "options": "-c statement_timeout=60000",  # 60s max local
    }


class DatabaseConnection:
    """Gestiona la conexión y pool de conexiones a PostgreSQL.

    El pool está atado al PID del proceso que lo creó. Un socket a PostgreSQL
    NO puede compartirse entre procesos: si el proceso maestro de Gunicorn abre
    conexiones (por ejemplo con --preload) y luego hace fork, los workers
    heredan el mismo descriptor. Dos peticiones simultáneas escribiendo sobre
    ese socket desincronizan el protocolo y la aplicación se cuelga hasta que
    vence el timeout del worker. Por eso cada proceso reconstruye su propio pool.
    """

    _instance = None
    _pool = None
    _pool_pid = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._lock = threading.RLock()
        return cls._instance

    def inicializar(self):
        """Inicializa el pool de conexiones para el proceso actual."""
        with self._lock:
            # Otro hilo pudo haberlo creado mientras esperábamos el lock.
            if self._pool is not None and self._pool_pid == os.getpid():
                return True
            try:
                conn_params = _get_connection_params()
                self._conn_params = conn_params
                minconn, maxconn = _get_pool_limits()
                keepalive = _get_keepalive_params()
                self._pool = psycopg2.pool.ThreadedConnectionPool(
                    minconn=minconn,
                    maxconn=maxconn,
                    **conn_params,
                    **keepalive,
                )
                self._pool_pid = os.getpid()
                log_info(
                    f"Pool de conexiones inicializado en PID {self._pool_pid} "
                    f"(min={minconn}, max={maxconn}, cloud={_is_cloud_environment()})"
                )
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

    def reiniciar_pool(self):
        """Descarta el pool actual y fuerza su recreación.

        Se llama desde el hook post_fork de Gunicorn. Las conexiones heredadas
        se abandonan SIN cerrarlas a propósito: cerrarlas enviaría un Terminate
        por un socket que el proceso padre todavía considera suyo.
        """
        with self._lock:
            self._pool = None
            self._pool_pid = None

    def _pool_del_proceso(self):
        """Retorna el pool válido para este proceso, creándolo si hace falta."""
        if self._pool is None or self._pool_pid != os.getpid():
            if self._pool is not None:
                # Heredado de un fork: se descarta sin cerrar.
                self.reiniciar_pool()
            if not self.inicializar():
                return None
        return self._pool

    def obtener_conexion(self, autocommit: bool = False):
        """Obtiene del pool una conexión viva y lista para usar.

        Espera hasta POOL_WAIT_TIMEOUT si el pool está agotado, en vez de
        fallar de inmediato, y descarta las conexiones que el servidor cerró.

        autocommit=True evita el par BEGIN/COMMIT que psycopg2 emite alrededor
        de cada sentencia: sirve para las operaciones de una sola sentencia
        (ver ejecutar_query/ejecutar_query_one). El default es False para que
        los llamadores que agrupan varias sentencias —migraciones, importación,
        auditoría— sigan controlando la transacción a mano.
        """
        pool = self._pool_del_proceso()
        if pool is None:
            return None

        limite = time.monotonic() + POOL_WAIT_TIMEOUT
        ultimo_error = None

        while True:
            try:
                conn = pool.getconn()
            except psycopg2.pool.PoolError as e:
                # Pool agotado: esperar a que otro hilo devuelva una conexión.
                ultimo_error = e
                if time.monotonic() >= limite:
                    log_error(
                        "Pool de conexiones agotado: todas las conexiones están "
                        "en uso. Revise consultas lentas o suba SCAH_DB_POOL_MAX",
                        e,
                    )
                    return None
                time.sleep(0.05)
                continue
            except Exception as e:
                log_error("Error al obtener conexión del pool", e)
                return None

            if _conexion_utilizable(conn):
                try:
                    conn.autocommit = autocommit
                except psycopg2.ProgrammingError:
                    # psycopg2 rechaza cambiar autocommit con una transacción
                    # abierta: la conexión volvió al pool en mal estado.
                    self.liberar_conexion(conn, descartar=True)
                    if time.monotonic() >= limite:
                        return None
                    continue
                return conn

            # Conexión muerta (Neon suspendido, reinicio del servidor, red caída):
            # se devuelve cerrada para que el pool abra una nueva en su lugar.
            self.liberar_conexion(conn, descartar=True)

            if time.monotonic() >= limite:
                log_error("No se obtuvo una conexión utilizable a PostgreSQL",
                          ultimo_error)
                return None

    def liberar_conexion(self, conn, descartar: bool = False):
        """Devuelve una conexión al pool.

        descartar=True cierra la conexión en vez de reutilizarla: se usa cuando
        quedó en un estado inconsistente tras un error.
        """
        if conn is None:
            return
        pool = self._pool
        if pool is None or self._pool_pid != os.getpid():
            # El pool ya no existe (o es de otro proceso): cerrar y salir.
            try:
                conn.close()
            except Exception:
                pass
            return
        try:
            pool.putconn(conn, close=descartar or conn.closed != 0)
        except psycopg2.pool.PoolError:
            # Conexión ya devuelta al pool: devolverla de nuevo la duplicaría en
            # la lista de libres y dos hilos acabarían usando el mismo socket.
            pass
        except Exception as e:
            log_error("Error al liberar conexión", e)

    def cerrar_pool(self):
        """Cierra todas las conexiones del pool."""
        with self._lock:
            if self._pool and self._pool_pid == os.getpid():
                try:
                    self._pool.closeall()
                    log_info("Pool de conexiones cerrado")
                except Exception as e:
                    log_error("Error al cerrar pool de conexiones", e)
            self._pool = None
            self._pool_pid = None

    def _revertir(self, conn) -> bool:
        """Hace rollback tras un error. Retorna True si la conexión quedó inservible."""
        try:
            conn.rollback()
            return False
        except Exception:
            # El rollback falla cuando el socket ya está roto: hay que descartarla.
            return True

    def ejecutar_query(self, query: str, params: tuple = None, fetch: bool = False):
        """Ejecuta una query y opcionalmente retorna resultados.

        Corre en autocommit: es una única sentencia, así que el COMMIT explícito
        no aportaba atomicidad y costaba dos viajes extra a la base (psycopg2
        emitía BEGIN antes y COMMIT después de cada SELECT).
        """
        conn = self.obtener_conexion(autocommit=True)
        if not conn:
            return None

        descartar = False
        try:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute(query, params)

            if fetch:
                resultado = cursor.fetchall()
            else:
                resultado = cursor.rowcount

            cursor.close()
            return resultado
        except Exception as e:
            descartar = self._revertir(conn)
            log_error(f"Error ejecutando query: {query[:100]}", e)
            return None
        finally:
            self.liberar_conexion(conn, descartar=descartar)

    def ejecutar_query_one(self, query: str, params: tuple = None):
        """Ejecuta una query y retorna un solo resultado.

        En autocommit por el mismo motivo que ejecutar_query.
        """
        conn = self.obtener_conexion(autocommit=True)
        if not conn:
            return None

        descartar = False
        try:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute(query, params)
            resultado = cursor.fetchone()
            cursor.close()
            return resultado
        except Exception as e:
            descartar = self._revertir(conn)
            log_error(f"Error ejecutando query: {query[:100]}", e)
            return None
        finally:
            self.liberar_conexion(conn, descartar=descartar)

    def ejecutar_many(self, query: str, params_list: list):
        """Ejecuta una query múltiples veces con distintos parámetros."""
        conn = self.obtener_conexion()
        if not conn:
            return False

        descartar = False
        try:
            cursor = conn.cursor()
            cursor.executemany(query, params_list)
            conn.commit()
            cursor.close()
            return True
        except Exception as e:
            descartar = self._revertir(conn)
            log_error(f"Error ejecutando query masiva: {query[:100]}", e)
            return False
        finally:
            self.liberar_conexion(conn, descartar=descartar)

    def ejecutar_batch_insert(self, query_template: str, values_list: list,
                              page_size: int = 500) -> int:
        """
        Inserta registros en lote usando execute_values (mucho más rápido que executemany).
        query_template: 'INSERT INTO tabla (col1, col2) VALUES %s'
        values_list: lista de tuplas con los valores
        Retorna la cantidad de filas insertadas o -1 en caso de error.
        """
        if not values_list:
            return 0
        conn = self.obtener_conexion()
        if not conn:
            return -1

        descartar = False
        try:
            cursor = conn.cursor()
            psycopg2.extras.execute_values(
                cursor, query_template, values_list,
                page_size=page_size,
            )
            rowcount = cursor.rowcount
            conn.commit()
            cursor.close()
            return rowcount
        except Exception as e:
            descartar = self._revertir(conn)
            log_error(f"Error en batch insert: {query_template[:100]}", e)
            return -1
        finally:
            self.liberar_conexion(conn, descartar=descartar)

    def test_conexion(self) -> tuple[bool, str]:
        """Prueba la conexión a la base de datos."""
        conn = None
        descartar = False
        try:
            conn = self.obtener_conexion()
            if not conn:
                return False, "No se pudo obtener conexión"
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.close()
            conn.commit()
            return True, "Conexión exitosa a PostgreSQL"
        except Exception as e:
            if conn is not None:
                descartar = self._revertir(conn)
            return False, f"Error de conexión: {str(e)}"
        finally:
            if conn is not None:
                self.liberar_conexion(conn, descartar=descartar)

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
