# S.C.A.H. - Sistema de Control de Alojamiento y Huéspedes

Sistema de escritorio para la gestión integral de huéspedes en establecimientos hoteleros. Permite importar datos desde archivos Excel, registrar huéspedes manualmente, realizar búsquedas avanzadas y generar reportes en Excel y PDF.

## Requisitos

- **Python 3.10+**
- **PostgreSQL 14+** (en ejecución)
- Sistema operativo: Windows 10/11

## Instalación

### 1. Clonar el repositorio

```bash
git clone <url-del-repositorio>
cd HOTELES
```

### 2. Crear entorno virtual e instalar dependencias

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Configurar PostgreSQL

Asegúrese de tener PostgreSQL en ejecución. La configuración por defecto está en `config.py`:

| Parámetro     | Valor por defecto |
| ------------- | ----------------- |
| Host          | localhost         |
| Puerto        | 5432              |
| Base de datos | scah_db           |
| Usuario       | postgres          |
| Contraseña    | postgres          |

Modifique `config.py` si sus credenciales son diferentes.

### 4. Ejecutar la aplicación

```bash
python main.py
```

En Windows también puede iniciar directamente con los lanzadores del proyecto:

- `SCAH_Launcher.bat` para la versión de escritorio
- `INICIAR_WEB.bat` para la versión web en `http://localhost:5000`

Para forzar manualmente la sincronización de alertas por hoteles sin cargas:

```bash
python scripts/sincronizar_alertas_hoteles.py
```

La aplicación creará automáticamente la base de datos y las tablas necesarias en el primer inicio.

## Credenciales por defecto

| Usuario | Contraseña | Rol           |
| ------- | ---------- | ------------- |
| admin   | admin123   | Administrador |

> **Importante:** Cambie la contraseña del administrador después del primer inicio de sesión.

## Estructura del Proyecto

```
HOTELES/
├── main.py                  # Punto de entrada
├── config.py                # Configuración general
├── requirements.txt         # Dependencias Python
├── auth/                    # Autenticación y roles
│   ├── login_window.py      # Ventana de login
│   ├── roles.py             # Sistema de permisos
│   └── user_manager.py      # Gestión de usuarios
├── database/                # Capa de datos
│   ├── connection.py        # Pool de conexiones PostgreSQL
│   ├── models.py            # Definición de tablas SQL
│   └── migrations.py        # Migraciones automáticas
├── modules/                 # Módulos funcionales
│   ├── import_excel.py      # Importación desde Excel
│   ├── manual_entry.py      # Registro manual de huéspedes
│   ├── search.py            # Búsqueda general y avanzada
│   ├── hotel_manager.py     # ABM de hoteles
│   ├── guest_manager.py     # ABM de usuarios del sistema
│   ├── statistics.py        # Dashboard y estadísticas
│   └── reports.py           # Generación de reportes
├── ui/                      # Interfaz gráfica
│   ├── main_window.py       # Ventana principal con sidebar
│   ├── themes.py            # Colores y fuentes
│   ├── dialogs.py           # Diálogos de confirmación/error
│   └── components.py        # Componentes reutilizables
├── utils/                   # Utilidades
│   ├── validators.py        # Validaciones de datos
│   ├── formatters.py        # Formateadores de texto/fechas
│   └── logger.py            # Logging y auditoría
└── logs/                    # Archivos de log (generados)
```

## Módulos Principales

### Importar Excel

Importa archivos `.xlsx` con mapeo específico de columnas:

- **Hotel:** A2=nombre, A4=nro_orden, A5=dirección, A6=ciudad
- **Huéspedes (fila 2+):** C=nacionalidad, D=procedencia, E=nombre, F=DNI, G=nacimiento, H=edad, I=profesión, J=entrada, K=salida

### Registro Manual

Formulario para registrar huéspedes uno a uno con validación en tiempo real, detección de duplicados y cálculo automático de edad.

### Búsqueda

- Búsqueda rápida por texto libre (nombre, DNI, nacionalidad, etc.)
- Filtros avanzados: hotel, ciudad, nacionalidad, profesión, procedencia, rango de fechas, rango de edades
- Exportación de resultados a Excel

### Estadísticas

- Dashboard con indicadores: total huéspedes, hoteles activos, alojados hoy
- Gráficos: nacionalidades, profesiones, procedencias, edades, tendencia mensual

### Reportes

Generación de reportes en Excel y PDF:

- Listado general de huéspedes
- Huéspedes por hotel
- Huéspedes por rango de fechas
- Reporte estadístico
- Historial de importaciones
- Auditoría del sistema

## Roles de Usuario

| Rol               | Permisos                                                                                  |
| ----------------- | ----------------------------------------------------------------------------------------- |
| **Administrador** | Acceso total: gestión de usuarios, hoteles, importación, búsqueda, reportes, estadísticas |
| **Operador**      | Importación, registro manual, búsqueda, reportes                                          |
| **Consulta**      | Solo búsqueda y visualización de estadísticas                                             |

## Tecnologías

- **GUI:** CustomTkinter (tema oscuro moderno)
- **Base de datos:** PostgreSQL con psycopg2
- **Excel:** openpyxl (lectura/escritura .xlsx)
- **PDF:** ReportLab
- **Gráficos:** Matplotlib (embebido en tkinter)
- **Seguridad:** bcrypt para hashing de contraseñas

## Licencia

Proyecto privado - Todos los derechos reservados.
