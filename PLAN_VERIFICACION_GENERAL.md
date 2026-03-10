# Plan General de Verificación - S.C.A.H.

## Objetivo

Validar de forma sistemática la aplicación de escritorio y la aplicación web para detectar errores de sintaxis, configuración, base de datos, permisos, navegación, importación y generación de reportes antes de publicar cambios.

## Alcance

- Aplicación de escritorio iniciada desde main.py.
- Aplicación web iniciada desde web/run.py.
- Base de datos PostgreSQL local.
- Scripts de arranque en Windows.
- Servicios, rutas, vistas y utilidades compartidas.

## Precondiciones

- PostgreSQL en ejecución.
- Entorno virtual creado en .venv.
- Dependencias instaladas con requirements.txt.
- Base scah_db accesible con las credenciales configuradas.

## Verificación Automática

### 1. Sintaxis global

Objetivo: detectar errores de sintaxis en cualquier módulo Python.

Comando:

```bash
.venv/Scripts/python.exe -m compileall .
```

Criterio de aprobación:

- No debe haber SyntaxError.

### 2. Imports y construcción de la app web

Objetivo: confirmar que los puntos de entrada principales importan correctamente y que Flask registra sus rutas.

Comando:

```bash
.venv/Scripts/python.exe -c "import main; from web.app import create_app; app=create_app('development'); print(app.url_map)"
```

Criterio de aprobación:

- El comando debe finalizar sin excepción.
- Deben aparecer las rutas principales de login, dashboard, huéspedes, hoteles, importación, reportes, usuarios y estadísticas.

### 3. Inicialización del sistema y migraciones

Objetivo: validar conexión a la base, migraciones y verificación de tablas.

Comando:

```bash
.venv/Scripts/python.exe -c "from main import inicializar_sistema; print(inicializar_sistema())"
```

Criterio de aprobación:

- Debe devolver True.
- No deben fallar las migraciones.

### 4. Smoke test web autenticado

Objetivo: validar navegación básica y endpoints críticos con un cliente Flask.

Cobertura mínima:

- GET /login
- POST /login con admin/admin123
- GET /dashboard
- GET /huespedes/
- GET /hoteles/
- GET /importar/
- GET /reportes/
- GET /usuarios/
- GET /estadisticas/
- GET /estadisticas/api/procedencia
- GET /estadisticas/api/tendencia

Criterio de aprobación:

- Login debe redirigir al dashboard.
- Las páginas autenticadas deben responder 200.
- Las APIs de estadísticas deben responder 200.

### 5. Scripts de arranque

Objetivo: verificar que los lanzadores locales usen el entorno virtual y no dependan del PATH del sistema.

Archivos a revisar:

- SCAH_Launcher.bat
- INICIAR_WEB.bat
- instalar.bat

Criterio de aprobación:

- Deben preferir .venv cuando exista.
- Deben mostrar mensajes claros ante fallos de Python o PostgreSQL.

## Verificación Manual Recomendada

### 6. Login y permisos

Validar:

- Inicio de sesión como admin.
- Restricción de acceso sin sesión.
- Menús y vistas según rol.
- Cierre de sesión.

### 7. Gestión de hoteles

Validar:

- Alta de hotel.
- Edición de hotel.
- Activación/desactivación.
- Búsqueda y listado.

### 8. Gestión de huéspedes

Validar:

- Alta manual.
- Visualización de detalle.
- Eliminación controlada.
- Filtros y búsquedas.

### 9. Importación Excel

Validar:

- Importación v1 con archivo válido.
- Importación v2 con archivo válido.
- Mensajes de error ante columnas o formato inválido.
- Registro en importaciones_log.

### 10. Reportes

Validar:

- Vista previa de reportes.
- Generación en Excel.
- Generación en PDF.
- Manejo correcto cuando no hay datos.

### 11. Estadísticas

Validar:

- Cambio entre categorías.
- Render de gráfico en barras, pie y línea.
- Tabla de datos alineada con el gráfico.
- Comportamiento con base vacía.

### 12. Escritorio

Validar:

- Inicio desde SCAH_Launcher.bat.
- Login en interfaz CustomTkinter.
- Apertura de módulos principales.
- Manejo de error si PostgreSQL no está disponible.

## Registro de resultados

Para cada verificación registrar:

- Fecha.
- Rama verificada.
- Entorno usado.
- Resultado: OK o FAIL.
- Evidencia breve del error.
- Acción correctiva aplicada.

## Resultado de la pasada actual

Validaciones ejecutadas en esta revisión:

- Sintaxis global con compileall: OK.
- Imports principales y app factory Flask: OK.
- Inicialización de sistema y migraciones: OK.
- Smoke test web de login, dashboard, módulos y APIs críticas: OK.

Observación:

- No se detectaron errores funcionales reales en esta pasada de verificación.
- No hay tests automatizados en el repositorio; conviene agregar una suite mínima de smoke tests con pytest para no depender solo de validación manual.
