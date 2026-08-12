# Plan de rendimiento y escalabilidad — S.C.A.H.

**Problema reportado:** cuando dos dispositivos cargan el sistema al mismo tiempo,
la aplicación se traba y deja de funcionar.

Este documento explica **por qué** pasaba, **qué se corrigió** (Fase 0, ya aplicada
y verificada) y **qué conviene hacer después** (Fases 1 a 3), en orden de impacto.

---

## 1. Diagnóstico

Se revisó el código, se levantó el sistema contra un PostgreSQL real con 200.000
huéspedes y se midió con varios dispositivos simultáneos. No había *una* causa:
había cinco defectos que se potenciaban entre sí.

### 1.1 La rama estaba rota — el sistema devolvía error 500 en todas las páginas

Dos fallos convivían en el último commit (`39af4ed`, *"optimizacion integral de
rendimiento"*):

| Defecto | Efecto |
|---|---|
| `database/migrations.py` tenía marcadores de conflicto de merge (`<<<<<<<`, `=======`, `>>>>>>>`) sin resolver, commiteados | El archivo **no compila**. El arranque lo captura con un `try/except` y sigue: `[WARN] Error inicializando BD: invalid syntax`. Resultado: **ninguna migración se ejecuta jamás**, y con ellas **ningún índice de rendimiento se llega a crear** |
| `base.html` usaba `asset_url(...)`, una función que nunca se definió en el código | `UndefinedError: 'asset_url' is undefined` → **HTTP 500 en toda página que extienda `base.html`** |

Comprobado ejecutando el commit original tal cual:

```
[WARN] Error inicializando BD: invalid syntax (migrations.py, line 477)
UndefinedError -> 'asset_url' is undefined     (al pedir /dashboard)
```

Es decir: los índices que el commit anterior pretendía añadir **nunca existieron en
la base de datos**, y la aplicación no renderizaba ninguna pantalla interna.

### 1.2 Causa raíz del bloqueo con dos dispositivos: un socket compartido entre procesos

Esta es la que explica el síntoma exacto que se reportó.

El arranque era:

```
gunicorn "web.app:create_app('production')" --workers 2 --preload
```

Con `--preload`, Gunicorn ejecuta `create_app()` **una sola vez en el proceso
maestro** y después hace `fork()` para crear los 2 workers. Y `create_app()`
llamaba a `_init_database()`, que abría el pool de conexiones.

El pool de psycopg2 abre `minconn` conexiones de inmediato. Por lo tanto:

```
    maestro ── abre conexión TCP a PostgreSQL ──┐
        │                                       │  el MISMO descriptor de socket
        ├── fork() → worker 1 ──────────────────┤  queda duplicado en los dos
        └── fork() → worker 2 ──────────────────┘  procesos hijos
```

Un socket a PostgreSQL **no puede compartirse entre procesos**: el protocolo es
una conversación con estado. Mientras solo un dispositivo usaba el sistema, un
único worker atendía y todo parecía funcionar. Con **dos peticiones simultáneas
repartidas entre los dos workers**, ambos escribían sobre la misma conexión: el
protocolo se desincroniza y las peticiones **se quedan colgadas hasta que vence
`--timeout 120`**, momento en que Gunicorn mata al worker.

Eso es literalmente *"cuando 2 dispositivos quieren cargar al mismo tiempo el
sistema se traba y no deja de funcionar"*.

### 1.3 Fugas de conexiones que dejaban el sistema muerto de forma permanente

Con solo 5 conexiones por worker, cualquier fuga es fatal. Había tres:

- **`import_service.py`**: `db.liberar_conexion(conn)` solo se llamaba en el
  camino feliz. Si una importación fallaba, esa conexión **no volvía nunca al
  pool**. Cinco importaciones fallidas = pool agotado = sistema bloqueado para
  todos hasta reiniciar.
- **`migrations.py`**: seis puntos devolvían la misma conexión al pool **dos
  veces** (una explícita y otra en el `finally`). Una conexión duplicada en la
  lista de libres puede entregarse a dos hilos a la vez → misma corrupción de
  protocolo del punto anterior.
- **`_registrar_auditoria()`**: misma fuga que la importación.

Además, `obtener_conexion()` no comprobaba si la conexión seguía viva. Neon
suspende el cómputo tras unos minutos de inactividad y cierra los sockets: el
pool devolvía conexiones muertas y la petición fallaba en vez de reconectar.

### 1.4 El listado de huéspedes recorría la tabla entera en cada carga

`/huespedes/` sin término de búsqueda ejecutaba `busqueda_rapida('')`, que
construía `ILIKE '%%'` sobre **11 columnas** —una condición que hace *match* con
todo— y la envolvía en `COUNT(*) OVER()`. Esa *window function* obliga a
PostgreSQL a **materializar todas las filas coincidentes con sus 16 columnas**
para poder contarlas, aunque en pantalla solo se muestren 50.

Medido con 200.000 huéspedes:

```
Consulta anterior : 707 ms   (recorrido secuencial + ordenación completa)
```

Con 2 workers × 0,1 CPU del plan gratuito, dos de esas consultas a la vez saturan
la instancia.

### 1.5 La importación de Excel mataba al worker por timeout

Por **cada fila** del Excel se hacían 2 viajes a la base de datos: un `SELECT` para
comprobar duplicados y un `INSERT`. Todo dentro de una transacción larga.

```
2.000 filas → 4.000 viajes a la base de datos
```

Contra una base remota tipo Neon (~30 ms de ida y vuelta):

```
4.000 × 30 ms = 120 s  →  justo el límite de --timeout 120
```

El worker se mataba a mitad de la importación. Con solo 2 workers, perder uno
significa **perder la mitad de la capacidad**, y el segundo dispositivo caía en el
worker moribundo.

### 1.6 Otros problemas encontrados

| Problema | Consecuencia |
|---|---|
| Los archivos subidos se guardaban con su nombre original en una carpeta compartida | Dos operadores importando `planilla.xlsx` a la vez **se pisaban el archivo**; el segundo importaba los datos del primero. Además `secure_filename` faltaba: un nombre tipo `../../config.py` escribía fuera de la carpeta |
| Logs a un archivo dentro del contenedor | En Render ese disco es efímero y **nadie puede leerlo**: los errores 500 eran invisibles |
| `Cache-Control: immutable` por un año sobre archivos estáticos **sin** sello de versión | Tras un deploy los navegadores seguían usando el CSS viejo durante un año |
| `render.yaml` instalaba `customtkinter`, `matplotlib` y `Pillow` (dependencias del cliente de escritorio) en el servidor web | Builds más lentos y una imagen mucho más pesada, sin usarse |
| `?per_page=` sin tope | Un solo parámetro en la URL podía forzar una página gigante y agotar la memoria de la instancia |
| Migraciones ejecutándose en cada `create_app()` | Sin `--preload` correrían **una vez por worker**, ejecutando DDL en paralelo y compitiendo por locks |

---

## 2. Fase 0 — Correcciones aplicadas

Todo lo de esta sección ya está implementado en esta rama y verificado.

### 2.1 Reparar lo que estaba roto
- Eliminados los marcadores de conflicto de `migrations.py`; el archivo vuelve a
  compilar y **las migraciones se ejecutan de verdad**: los 16 índices ya existen.
- Definida la función `asset_url()` que faltaba (en `web/app.py`), con sello de
  versión calculado a partir de la fecha de modificación de los archivos estáticos.
- `migrar_v1_4()` llamaba a `normalizar_historico_huespedes()`, **una función que
  no existe en ninguna versión del repositorio** (se perdió en el mismo conflicto).
  Se dejó **deshabilitada de forma explícita y sin marcarse como aplicada**, en vez
  de reescribirla adivinando: modifica los campos `nacionalidad` y `procedencia` de
  registros históricos y una conversión equivocada corrompería datos reales.
  **Queda pendiente de decisión** (ver §3.1).

### 2.2 Un pool de conexiones por proceso
`database/connection.py` y el nuevo `gunicorn.conf.py`:
- El pool queda **atado al PID** que lo creó; si detecta otro PID, lo reconstruye.
- El hook `post_fork` de Gunicorn **reinicia el pool en cada worker**. Las
  conexiones heredadas se abandonan sin cerrarlas a propósito (cerrarlas enviaría
  un `Terminate` por un socket que el proceso padre considera suyo).
- Inicialización protegida con lock, para que dos hilos no creen dos pools.
- `obtener_conexion()` **valida la conexión** antes de entregarla (descarta las que
  Neon cerró) y **espera hasta 10 s** si el pool está lleno, en vez de fallar al
  instante.
- `liberar_conexion(conn, descartar=...)` cierra las conexiones que quedaron en
  mal estado y **ignora las devoluciones duplicadas**.
- Se puede mantener `--preload` (ahorra memoria) porque `post_fork` lo hace seguro.

### 2.3 Fugas cerradas
- `try/finally` en las dos funciones de importación y en `_registrar_auditoria()`.
- Eliminadas las seis dobles devoluciones al pool en `migrations.py`.
- Las migraciones se ejecutan **una sola vez**, en el hook `on_starting` del
  proceso maestro, protegidas además con un **advisory lock de PostgreSQL**.

### 2.4 Listado de huéspedes
- Sin término de búsqueda ya no se genera `ILIKE '%%'`: se usa el listado directo.
- Se eliminó `COUNT(*) OVER()`. Ahora son dos consultas: la página de datos
  (`LIMIT`/`OFFSET`, que lee solo 50 filas por el índice) y el conteo, **cacheado
  60 segundos** en memoria del worker e invalidado al crear, borrar o importar.
- `per_page` acotado a 200.

### 2.5 Importación por lotes
- Los hoteles se resuelven **una vez cada uno**, no una vez por fila.
- Los duplicados existentes se traen **en una sola consulta** y se comparan en
  memoria (detectando también los repetidos dentro del propio archivo).
- Inserción agrupada con `execute_values` en páginas de 500.
- Si un lote falla, **se reintenta fila a fila sobre un `SAVEPOINT`**, de modo que
  un registro defectuoso no invalida el resto de la importación.

### 2.6 Operación y diagnóstico
- **`/healthz`**: responde sin tocar la base de datos — es lo que debe usar el
  health check de Render. (Si consultara la base, una caída de Neon provocaría
  además el reinicio en bucle del servicio.) Configurado en `render.yaml`.
- **`/readyz`**: sí consulta la base y devuelve la latencia, para diagnóstico manual.
- **Logs a stdout** en la nube, para que Render los capture.
- Log de acceso con **duración de cada petición** (`%(L)s`): permite ver qué
  endpoint se está poniendo lento *antes* de que llegue a colgarse.
- `max_requests=1000` con jitter: recicla workers para que una fuga de memoria no
  termine en un OOM del contenedor.
- Uploads en carpeta única por subida + `secure_filename` + purga de restos de más
  de 6 horas.
- `render.yaml` instala solo `web/requirements.txt`.
- Cookie de sesión `HttpOnly`, `SameSite=Lax` y `Secure` en producción
  (desactivable con `SCAH_COOKIE_SECURE=0` para despliegues internos por HTTP).
- `sslmode` de `DATABASE_URL` ahora se respeta si viene en la URL (antes se forzaba
  `require` siempre, lo que impedía apuntar a un PostgreSQL local o en red privada).

### 2.7 Resultados medidos

Entorno: PostgreSQL 16 local, 200.000 huéspedes, 50 hoteles, Gunicorn con
2 workers × 4 hilos.

**Consulta del listado**

| | Antes | Después |
|---|---|---|
| Página de datos | 707 ms (recorrido secuencial) | **0,43 ms** (índice) |
| Conteo | incluido en los 707 ms | 13,9 ms, cacheado 60 s |

**Importación de 2.000 filas**

| | Antes | Después |
|---|---|---|
| Viajes a la base de datos | 4.000 | **~7** |
| Tiempo (base local) | 2,50 s | **0,30 s** (6.716 filas/s) |
| Proyección con base remota (30 ms RTT) | **120 s → mata al worker** | **~0,2 s** |

**Concurrencia** (dashboard + listado + página 3 + estadísticas, con sesión real)

| Dispositivos simultáneos | Peticiones | Correctas | Latencia media | p95 | Workers caídos |
|---|---|---|---|---|---|
| 2 | 40 | **40 (100%)** | 25 ms | 63 ms | 0 |
| 20 | 320 | **320 (100%)** | 162 ms | 366 ms | 0 |

Las 8 pantallas principales (`/dashboard`, `/huespedes/`, `/estadisticas/`,
`/hoteles/`, `/reportes/`, `/usuarios/`, `/backups/`, `/importar/`) responden
**200** donde antes devolvían **500**.

Verificación de la importación: 2.000 filas nuevas → 2.000 importadas; reimportar
el mismo archivo → 2.000 duplicados detectados y 0 insertados; archivo con filas
repetidas internamente → solo las únicas; lote con 1 fila inválida de 5 → 4
importadas y 1 error (el `SAVEPOINT` protege al resto).

---

## 3. Fase 1 — Siguientes pasos recomendados (1 a 2 días)

### 3.1 Decidir qué hacer con la migración v1.4 *(requiere criterio del negocio)*
Está deshabilitada porque su implementación se perdió. Hay que definir **qué
significa "normalizar" nacionalidad y procedencia** (¿unificar "ARG"/"Argentina"?
¿corregir mayúsculas?) antes de escribirla. Recomendación: implementarla como un
script manual que primero muestre un informe de los cambios que haría, se revise, y
solo entonces se apliquen. Nunca como migración automática al arrancar.

### 3.2 No parsear el Excel dos veces
Hoy la vista previa parsea el archivo y, al confirmar, `_ejecutar_import_*` lo
**vuelve a parsear**. Guardar el resultado del parseo junto al archivo subido y
reutilizarlo reduce a la mitad el trabajo de CPU de una importación.

### 3.3 Índices que faltan para las búsquedas por texto
La búsqueda rápida usa `ILIKE '%termino%'`, que **ningún índice B-tree puede
acelerar**. La extensión `pg_trgm` ya se habilita en la migración v1.6, pero faltan
los índices GIN:

```sql
CREATE INDEX CONCURRENTLY idx_huespedes_nombre_trgm
  ON huespedes USING gin (apellido_nombre gin_trgm_ops);
CREATE INDEX CONCURRENTLY idx_huespedes_dni_trgm
  ON huespedes USING gin (dni_pasaporte gin_trgm_ops);
```

Usar `CONCURRENTLY` para no bloquear la tabla. Con la tabla creciendo, esto es la
diferencia entre una búsqueda instantánea y una de varios segundos.

### 3.4 Paginación por *keyset* en lugar de `OFFSET`
`OFFSET 10000` obliga a PostgreSQL a leer y descartar 10.000 filas. Si se llega a
listados muy profundos, conviene paginar por `WHERE fecha_registro < :ultima_vista`.
Con el uso actual (pocas páginas) no es urgente.

### 3.5 Backups y reportes: no construirlos en memoria
`generar_backup_zip()` carga **todas las filas de todas las tablas** en memoria,
las serializa a JSON con `indent=2` y comprime en un `BytesIO`. En una instancia de
512 MB, con la tabla creciendo, esto termina en un OOM que **se lleva por delante
las peticiones de los demás usuarios**. Conviene generarlo por streaming
(`stream_with_context` + escritura incremental) o moverlo a una tarea programada.
Lo mismo aplica a los reportes grandes en PDF/Excel.

---

## 4. Fase 2 — Escalar de verdad (cuando crezca el uso)

### 4.1 Subir de plan antes que optimizar más
El plan gratuito de Render son **0,1 CPU y 512 MB**, y además **apaga el servicio
tras 15 minutos de inactividad** (el primer acceso siguiente tarda ~50 s: eso
también se percibe como "el sistema está trabado"). Neon Free suspende la base tras
5 minutos. Pasar a un plan de pago **sin tocar código** es la mejora más grande
disponible y elimina los arranques en frío.

Al subir de plan, ajustar en `render.yaml`:
- `WEB_CONCURRENCY` = `(2 × núcleos) + 1`
- `SCAH_DB_POOL_MAX` de forma que `SCAH_DB_POOL_MAX × WEB_CONCURRENCY` quede por
  debajo del límite de conexiones del plan de Neon.

### 4.2 Pooler de conexiones
Neon ofrece un endpoint *pooled* (PgBouncer). Usar esa URL permite muchos más
workers sin agotar el límite de conexiones. **Atención:** en modo *transaction
pooling* no se pueden usar sentencias preparadas ni `SET` de sesión.

### 4.3 Sesiones y archivos fuera del proceso
Hoy la ruta del archivo subido se guarda en la sesión y el archivo vive en el disco
local del contenedor. **Con más de una instancia eso se rompe**: la segunda
petición puede caer en otra máquina que no tiene el archivo. Antes de escalar
horizontalmente hace falta almacenamiento compartido (S3/R2) o enrutado *sticky*.

### 4.4 Importaciones como trabajo en segundo plano
Una importación grande no debería vivir dentro de una petición HTTP. Con una cola
(Redis + RQ/Celery, o un worker de Render), la web responde al instante con "importación
en curso" y el usuario ve el progreso. Esto **elimina por completo** la clase de
problema del §1.5.

### 4.5 Caché compartida
El caché de conteos actual es **por worker** y en memoria. Con más workers, Redis
permitiría compartirlo y cachear también el dashboard y las estadísticas, que hoy
se recalculan en cada carga.

---

## 5. Fase 3 — Sostenerlo en el tiempo

1. **Pruebas automatizadas.** El repositorio no tiene ninguna. Un fallo tan grave
   como un archivo que no compila llegó a la rama principal sin que nada lo
   detectara. Con un test mínimo que arranque la app y pida las pantallas
   principales habría bastado.
2. **Verificación de sintaxis antes de commitear.** `python -m compileall` en CI, o
   un pre-commit hook, habría bloqueado los marcadores de conflicto.
3. **Vigilar `pg_stat_statements`** para detectar consultas lentas antes de que se
   noten.
4. **Alerta sobre el log de acceso**: si el p95 sube o aparecen `WORKER TIMEOUT`,
   avisar. Ya está el `worker_abort` registrando el evento con una explicación.

---

## 6. Cómo verificar que todo sigue bien

```bash
# 1. Que todo compila (esto habría evitado el fallo original)
python -m compileall -q web/ database/ utils/ config.py gunicorn.conf.py

# 2. El servicio está vivo
curl https://<tu-app>.onrender.com/healthz     # {"status":"ok",...}

# 3. La base responde y con qué latencia
curl https://<tu-app>.onrender.com/readyz      # {"status":"ok","latencia_ms":...}
```

En los logs de Render, tras un deploy correcto deben aparecer:

```
SCAH: migraciones verificadas                          <- una sola vez
SCAH: pool de conexiones reiniciado en worker <pid>    <- una vez por worker
```

Si aparece `SCAH: worker <pid> abortado por timeout`, hay una operación demasiado
larga: buscar en el log de acceso la petición con mayor duración.

---

## 7. Resumen

| | Antes | Después |
|---|---|---|
| Páginas internas | **HTTP 500** (`asset_url` sin definir) | 200 |
| Migraciones e índices | **Nunca se ejecutaban** (archivo sin compilar) | 16 índices creados |
| 2 dispositivos a la vez | **Bloqueo hasta el timeout de 120 s** | 100% correctas, 25 ms de media |
| 20 dispositivos a la vez | — | 100% correctas, p95 366 ms |
| Listado de huéspedes | 707 ms | 0,43 ms |
| Importar 2.000 filas | 4.000 viajes a la BD (~120 s en remoto) | ~7 viajes (~0,3 s) |
| Importación fallida | **Fugaba la conexión → sistema muerto** | Conexión devuelta siempre |
| Errores en producción | Invisibles (log a archivo efímero) | En los logs de Render |

La corrección decisiva para el problema reportado es la del **§2.2**: cada proceso
con su propio pool de conexiones. Las demás evitan que el sistema vuelva a
degradarse por otras vías.
