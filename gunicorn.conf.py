"""
S.C.A.H. Web - Configuración de Gunicorn.

Se usa con:  gunicorn -c gunicorn.conf.py "web.app:create_app('production')"

Aquí vive la parte de concurrencia que NO puede resolverse dentro de Flask:
qué se ejecuta antes del fork, qué se reconstruye después, y cuántas
peticiones simultáneas acepta cada proceso.
"""

import multiprocessing
import os
import sys

# Asegurar que la raíz del proyecto esté importable desde los hooks.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


# ── Red ──────────────────────────────────────────────────────────
bind = f"0.0.0.0:{os.environ.get('PORT', '5000')}"

# ── Modelo de concurrencia ───────────────────────────────────────
# gthread: cada worker atiende varias peticiones en hilos. Encaja con esta
# aplicación porque casi todo el tiempo de una petición se va esperando a
# PostgreSQL (I/O), no calculando en Python.
worker_class = "gthread"

# En el plan gratuito de Render (0.1 CPU / 512 MB) más de 2 workers solo
# genera competencia por CPU y riesgo de OOM. En planes con más recursos,
# WEB_CONCURRENCY manda.
workers = int(os.environ.get("WEB_CONCURRENCY", 2))
threads = int(os.environ.get("GUNICORN_THREADS", 4))

# Capacidad simultánea = workers x threads. Debe ser <= (SCAH_DB_POOL_MAX x workers)
# para que ningún hilo se quede esperando conexión de forma sistemática.

# ── Tiempos ──────────────────────────────────────────────────────
timeout = int(os.environ.get("GUNICORN_TIMEOUT", 120))
graceful_timeout = 30
# Mantener vivas las conexiones del proxy de Render entre peticiones.
keepalive = 5

# ── Reciclado de workers ─────────────────────────────────────────
# Reinicia cada worker periódicamente para que una fuga de memoria (p. ej. un
# Excel grande) no termine provocando un OOM del contenedor. El jitter evita
# que los dos workers se reinicien a la vez y dejen el sitio sin capacidad.
max_requests = int(os.environ.get("GUNICORN_MAX_REQUESTS", 1000))
max_requests_jitter = 100

# ── Arranque ─────────────────────────────────────────────────────
# preload_app ahorra memoria (el código se carga una vez y se comparte tras el
# fork). Es seguro ÚNICAMENTE porque post_fork reconstruye el pool de conexiones
# en cada worker; sin ese hook, los workers compartirían sockets a PostgreSQL.
preload_app = True

# ── Logs ─────────────────────────────────────────────────────────
# A stdout/stderr para que Render los capture y sean consultables.
accesslog = "-"
errorlog = "-"
loglevel = os.environ.get("GUNICORN_LOG_LEVEL", "info")
# %(L)s = duración de la petición en segundos: imprescindible para detectar
# qué endpoint se está poniendo lento antes de que llegue a colgarse.
access_log_format = '%(h)s "%(r)s" %(s)s %(b)s %(L)ss "%(a)s"'


# ── Hooks del ciclo de vida ──────────────────────────────────────

def on_starting(server):
    """Se ejecuta UNA vez en el proceso maestro, antes de crear workers.

    Las migraciones van aquí y no en create_app(): si cada worker ejecutase el
    DDL, competirían por locks de tabla en PostgreSQL durante el arranque.
    """
    if os.environ.get("SCAH_SKIP_MIGRATIONS") == "1":
        server.log.info("SCAH: migraciones omitidas por SCAH_SKIP_MIGRATIONS=1")
        return

    try:
        from database.connection import db
        from database.migrations import ejecutar_migraciones

        conexion_ok, mensaje = db.test_conexion()
        if not conexion_ok:
            server.log.error("SCAH: sin conexión a la base de datos (%s)", mensaje)
            return

        ejecutar_migraciones()
        server.log.info("SCAH: migraciones verificadas")
    except Exception as e:
        # Un fallo migrando no debe impedir que el sitio levante: puede ser un
        # problema transitorio de red y la app sirve igual con el esquema previo.
        server.log.error("SCAH: error ejecutando migraciones: %s", e)
    finally:
        # Cerrar las conexiones del maestro para que los workers no las hereden.
        try:
            from database.connection import db
            db.cerrar_pool()
        except Exception:
            pass


def post_fork(server, worker):
    """Se ejecuta en cada worker recién creado.

    Descarta cualquier pool heredado del proceso maestro. Un socket TCP a
    PostgreSQL no puede usarse desde dos procesos: si dos workers escriben
    sobre el mismo, el protocolo se desincroniza y las peticiones se quedan
    colgadas hasta que vence `timeout`. Este es exactamente el síntoma de
    "dos dispositivos cargan a la vez y el sistema se traba".
    """
    try:
        from database.connection import db
        db.reiniciar_pool()
        worker.log.info("SCAH: pool de conexiones reiniciado en worker %s", worker.pid)
    except Exception as e:
        worker.log.error("SCAH: error reiniciando el pool tras el fork: %s", e)


def worker_exit(server, worker):
    """Cierra limpiamente las conexiones del worker que termina."""
    try:
        from database.connection import db
        db.cerrar_pool()
    except Exception:
        pass


def worker_abort(worker):
    """Se dispara cuando un worker es abortado por superar `timeout`."""
    worker.log.error(
        "SCAH: worker %s abortado por timeout (%ss). "
        "Suele indicar una consulta o importación demasiado larga.",
        worker.pid, timeout,
    )


# Sugerencia de dimensionado para cuando se suba de plan:
#   workers recomendados = (2 x nucleos) + 1
_NUCLEOS = multiprocessing.cpu_count()
_WORKERS_SUGERIDOS = (2 * _NUCLEOS) + 1
