# S.C.A.H. - Guía de Instalación en otra Computadora

## Resumen

Existen **dos métodos** para instalar el sistema en otra computadora:

| Método                             | Requiere Python | Requiere Internet |        Dificultad        |
| ---------------------------------- | :-------------: | :---------------: | :----------------------: |
| **A. Código fuente** (recomendado) |       Sí        | Sí (primera vez)  |          Fácil           |
| **B. Ejecutable compilado**        |       No        |        No         | Medio (compilar primero) |

---

## Requisitos en la computadora destino

### Obligatorios (ambos métodos)

- **Windows 10/11** (64 bits)
- **PostgreSQL 14+** instalado y en ejecución

### Solo para Método A (código fuente)

- **Python 3.10+** (con "Add to PATH" marcado durante instalación)
- **Conexión a Internet** (solo la primera vez, para instalar dependencias)

---

## Método A: Instalación desde Código Fuente (Recomendado)

### Paso 1: Copiar los archivos

Copie **toda la carpeta del proyecto** a la computadora destino. Puede usar:

- USB/Pendrive
- Carpeta compartida en red
- Comprimirla en ZIP y enviarla

**Archivos y carpetas necesarios:**

```
HOTELES/
├── main.py
├── config.py
├── requirements.txt
├── instalar.bat              ← Instalador automático
├── SCAH_Launcher.bat         ← Lanzador
├── crear_acceso_directo.vbs  ← Crea acceso directo
├── GUIA_INSTALACION.md       ← Esta guía
├── auth/
├── database/
├── modules/
├── ui/
├── utils/
├── assets/
└── logs/
```

> **NO copiar:** `.venv/`, `__pycache__/`, `build/`, `dist/`, `.git/`

### Paso 2: Instalar PostgreSQL (si no está instalado)

1. Descargue PostgreSQL desde: https://www.postgresql.org/download/windows/
2. Durante la instalación:
   - Puerto: **5432** (por defecto)
   - Contraseña del superusuario: **postgres**
   - Locale: **Spanish, Argentina** o su preferencia
3. Asegúrese de que el servicio PostgreSQL esté en ejecución

### Paso 3: Instalar Python (si no está instalado)

1. Descargue Python desde: https://www.python.org/downloads/
2. **IMPORTANTE:** Marque la casilla **"Add Python to PATH"** durante la instalación
3. Reinicie la computadora tras la instalación

### Paso 4: Ejecutar el instalador

1. Abra la carpeta `HOTELES/` copiada
2. Haga **doble clic** en `instalar.bat`
3. Siga las instrucciones en pantalla
4. Al finalizar, se creará un acceso directo en el Escritorio

### Paso 5: Iniciar la aplicación

- Use el acceso directo **"S.C.A.H."** en el Escritorio, o
- Ejecute `SCAH_Launcher.bat`

**Credenciales por defecto:**

- Usuario: `admin`
- Contraseña: `admin123`

---

## Método B: Ejecutable Compilado (sin Python)

Este método genera un `.exe` que no necesita Python instalado.

### En la computadora ORIGEN (donde está el código):

1. Abra una terminal en la carpeta del proyecto
2. Active el entorno virtual:
   ```
   .venv\Scripts\activate
   ```
3. Ejecute el compilador:
   ```
   python build_exe.py
   ```
4. Espere a que termine (puede tardar 5-10 minutos)
5. El resultado estará en la carpeta `dist/SCAH/`

### En la computadora DESTINO:

1. Copie toda la carpeta `dist/SCAH/` a la computadora destino
2. Instale PostgreSQL (ver Paso 2 del Método A)
3. Ejecute `crear_acceso_directo.vbs` para crear el acceso directo
4. Inicie la aplicación desde el acceso directo o ejecutando `SCAH.exe`

---

## Configuración de PostgreSQL

Si las credenciales de PostgreSQL son diferentes en la computadora destino, edite el archivo `config.py`:

```python
DB_CONFIG = {
    "host": "localhost",        # Dirección del servidor
    "port": 5432,               # Puerto
    "dbname": "scah_db",        # Nombre de la base de datos
    "user": "postgres",         # Usuario
    "password": "postgres",     # Contraseña
}
```

También puede usar **variables de entorno** en lugar de editar el archivo:

```
set SCAH_DB_HOST=localhost
set SCAH_DB_PORT=5432
set SCAH_DB_NAME=scah_db
set SCAH_DB_USER=postgres
set SCAH_DB_PASSWORD=mi_contraseña
```

---

## Solución de Problemas

### "Python no está instalado o no está en el PATH"

- Reinstale Python marcando **"Add Python to PATH"**
- O agregue manualmente `C:\Users\<usuario>\AppData\Local\Programs\Python\Python3XX\` al PATH del sistema

### "No se pudo conectar a PostgreSQL"

- Verifique que el servicio esté en ejecución:
  - Abra `services.msc` → busque "postgresql" → Estado: "En ejecución"
- Verifique las credenciales en `config.py`
- Intente conectarse con pgAdmin para confirmar acceso

### "Error al instalar dependencias"

- Verifique su conexión a Internet
- Ejecute manualmente: `pip install -r requirements.txt`
- Si `psycopg2-binary` falla, intente: `pip install psycopg2`

### La aplicación se cierra inmediatamente

- Ejecute desde terminal para ver errores: `python main.py`
- Revise el archivo `crash_log.txt` o la carpeta `logs/`

### Error "DLL load failed" o similar

- Instale **Microsoft Visual C++ Redistributable**: https://aka.ms/vs/17/release/vc_redist.x64.exe

---

## Crear acceso directo manualmente

Si el script automático no funciona:

1. Clic derecho en el Escritorio → **Nuevo** → **Acceso directo**
2. Ubicación: `"C:\ruta\a\HOTELES\SCAH_Launcher.bat"`
3. Nombre: `S.C.A.H.`
4. (Opcional) Clic derecho en el acceso directo → **Propiedades** → **Cambiar icono** → seleccione un icono

---

## Estructura de exportación rápida

Para copiar solo lo necesario, use este comando en PowerShell:

```powershell
# Desde la carpeta del proyecto
$destino = "D:\SCAH_Export"
$excluir = @('.venv', '__pycache__', 'build', 'dist', '.git', '*.pyc', 'crash_log.txt')

robocopy . $destino /E /XD .venv __pycache__ build dist .git /XF *.pyc crash_log.txt
```

O use el script `exportar.bat` incluido en el proyecto.
