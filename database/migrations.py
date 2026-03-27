"""
S.C.A.H. - Migraciones de base de datos
Creación inicial de tablas, índices y datos semilla
"""

import bcrypt
from database.connection import db
from database.models import ALL_TABLES, SQL_CREATE_INDICES
from config import DEFAULT_ADMIN
from utils.geography import normalizar_historico_huespedes
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
        migrar_v1_2()
        migrar_v1_3()
        migrar_v1_4()
        migrar_v1_5()

        return True

    except Exception as e:
        conn.rollback()
        log_error("Error durante las migraciones", e)
        return False
    finally:
        db.liberar_conexion(conn)


def verificar_esquema() -> tuple[bool, list]:
    """Verifica que todas las tablas necesarias existan."""
    tablas_necesarias = ["usuarios", "hoteles", "huespedes", "importaciones_log", "alertas_sistema", "auditoria"]
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


# ============================================================
# MIGRACIÓN V1.2: Columnas categoria y telefono en hoteles + datos semilla
# ============================================================
SQL_MIGRACION_V1_2 = [
    "ALTER TABLE hoteles ADD COLUMN IF NOT EXISTS categoria VARCHAR(200);",
    "ALTER TABLE hoteles ADD COLUMN IF NOT EXISTS telefono VARCHAR(300);",
    "CREATE INDEX IF NOT EXISTS idx_hoteles_categoria ON hoteles(categoria);",
]

# Datos de hoteles extraídos del listado oficial de alojamientos de Tucumán
# Formato: (nombre, categoria, direccion, telefono, ciudad_localidad)
HOTELES_SEMILLA = [
    # ===================== SAN MIGUEL DE TUCUMÁN (SMT) =====================
    ("CATALINAS PARK", "HOTEL 5*", "Av. Soldati N° 380", "(0381) 4220624", "San Miguel de Tucumán"),
    ("SHERATON", "HOTEL 5*", "Av. Soldati 440", "(0381) 4554700", "San Miguel de Tucumán"),
    ("DEL JARDIN", "HOTEL 4*", "Laprida 463", "(0381) 4522008", "San Miguel de Tucumán"),
    ("RAMADA PLAZA", "HOTEL 4*", "Laprida 35", "(0381) 4311755", "San Miguel de Tucumán"),
    ("METROPOL", "HOTEL 4*", "24 de Septiembre 524", "(0381) 5157338", "San Miguel de Tucumán"),
    ("GARDEN PARK", "HOTEL 4*", "Av. Soldati 330", "(0381) 4310700", "San Miguel de Tucumán"),
    ("TUCUMAN CENTER", "HOTEL 4*", "25 de Mayo 230", "(0381) 4525555", "San Miguel de Tucumán"),
    ("BICENTENARIO", "HOTEL 4*", "Las Heras 21", "(0381) 2546282 / (0381) 2546289 / 3815569205 WSP", "San Miguel de Tucumán"),
    ("HILTON", "HOTEL 4*", "Las Piedras 1550", "(0381) 4532000 / 3814434764 WSP", "San Miguel de Tucumán"),
    ("EMBAJADOR", "HOTEL 3*", "Las Heras 221", "(0381) 4311264", "San Miguel de Tucumán"),
    ("CARLOS V", "HOTEL 3*", "25 de Mayo 330", "(0381) 4311666", "San Miguel de Tucumán"),
    ("COLONIAL", "HOTEL 3*", "San Martín 35", "(0381) 4311523", "San Miguel de Tucumán"),
    ("AMERIAN", "HOTEL 3*", "Santiago del Estero 419", "(0381) 5601766", "San Miguel de Tucumán"),
    ("FRANCIA", "HOTEL 3*", "Crisóstomo Alvarez 467", "(0381) 4310781", "San Miguel de Tucumán"),
    ("MEDITERRANEO", "HOTEL 3*", "24 de Septiembre 346", "(0381) 3126849 / 3814867853 WSP", "San Miguel de Tucumán"),
    ("MIAMI", "HOTEL 3*", "Junín 580", "(0381) 5847361 WSP", "San Miguel de Tucumán"),
    ("PREMIER", "HOTEL 3*", "Crisóstomo Alvarez 510", "(0381) 4310382 / 3816580744", "San Miguel de Tucumán"),
    ("SOLAR DEL NORTE", "HOTEL 3*", "México 879", "(0381) 4272722", "San Miguel de Tucumán"),
    ("REPUBLICA", "HOTEL 3*", "Virgen de la Merced 71", "(0381) 4310481", "San Miguel de Tucumán"),
    ("LE PARK", "HOTEL 3*", "Junín 1134", "(0381) 4218818", "San Miguel de Tucumán"),
    ("AMERICA", "HOTEL 2*", "Santiago del Estero 1064", "(0381) 4224853", "San Miguel de Tucumán"),
    ("VERSAILLES", "HOTEL 2*", "Crisostomo Alvarez 481", "(0381) 4229760", "San Miguel de Tucumán"),
    ("HOTEL LA TERMINAL", "HOTEL 2*", "Av. Brígido Terán 227", "(0381) 4210647", "San Miguel de Tucumán"),
    ("LG GOLDEN", "HOTEL 2*", "Bernabé Aráoz 36", "(0381) 4216286", "San Miguel de Tucumán"),
    ("ASTORIA", "HOTEL 1*", "Congreso 88", "(0381) 2600959", "San Miguel de Tucumán"),
    ("GARDEN", "HOTEL 1*", "Crisostomo Alvarez 627", "(0381) 4311246", "San Miguel de Tucumán"),
    ("LORENZO SUITES", "HOTEL 1*", "San Lorenzo 590", "(0381) 3604382", "San Miguel de Tucumán"),
    ("CHARCAS", "HOTEL 1*", "Charcas 131", "(0381) 4219576", "San Miguel de Tucumán"),
    ("TP APART", "APART HOTEL", "Santa Fe 1635", "(0381) 3183733 / (0381) 4177559", "San Miguel de Tucumán"),
    ("BRISA", "HOSTEL", "Congreso 190", "(381) 5167770", "San Miguel de Tucumán"),
    ("DEL CENTRO", "HOSTEL", "San Martín 218", "(0381) 6643659", "San Miguel de Tucumán"),
    ("LAS CARRETAS", "HOSTAL", "Benjamín Aráoz 38", "(0381) 5813634", "San Miguel de Tucumán"),
    ("MERCER", "HOSTEL", "Suipacha 685", "(0381) 4331268", "San Miguel de Tucumán"),
    ("A LA GURDA", "HOSTEL", "Maipú 490", "(0381) 2324008", "San Miguel de Tucumán"),
    ("TU HOSTEL", "HOSTEL", "Mendoza 912", "(0381) 3982019 / (0381) 6565061", "San Miguel de Tucumán"),
    ("THE POINT CASA", "CONJ CASA/DEPTO", "Virgen de La Merced 120", "3816319589", "San Miguel de Tucumán"),
    ("UNIVERSO", "RESIDENCIAL", "Santiago del Estero 1060", "(0381) 4311136", "San Miguel de Tucumán"),
    # ===================== YERBA BUENA (YB) =====================
    ("HOWARD JHONSONS", "HOTEL 4*", "Av. Aconquija 1136", "(0381) 4257796", "Yerba Buena"),
    ("EL CORTE", "HOSTERIA", "Av. Aconquija 3297", "(0381) 4256764", "Yerba Buena"),
    ("RIO MOLLE", "CONJ CASA Y/O DEPA", "Av. Aconquija 334", "3816686686", "Yerba Buena"),
    ("TRES ARROYOS", "CABAÑAS", "Jorge Luis Borges 3150", "3815028402", "Yerba Buena"),
    ("CASA LOLA", "POSADA", "Florida Sur 167", "(381) 5479146", "Yerba Buena"),
    ("PURA VIDA MAE", "HOSTEL", "Pringles 1714", "3816712532", "Yerba Buena"),
    ("LA PROVIDENCIA", "HOSTAL", "Pje. San Luis 598", "3813330030", "Yerba Buena"),
    ("ARRULLO DE LUNA", "HOSTEL", "Bascary 36", "3815490660", "Yerba Buena"),
    # ===================== TAFÍ VIEJO =====================
    ("ATAHUALPA YUPANQUI", "HOTEL 3*", "Paisandú 2400", "3814595835", "Tafí Viejo"),
    # ===================== SAN JAVIER =====================
    ("SOL SAN JAVIER", "HOTEL 4*", "Ruta 340 km 23", "4929200", "San Javier"),
    ("FLOR DE LOTO", "HOSTEL/HOSTAL", "Calle 5 y Ruta 340", "3813019979", "San Javier"),
    ("LAS YUNGAS", "HOSTEL/HOSTAL", "Ruta Provincial 338 KM15", "3813514170", "San Javier"),
    ("SURI YACU", "POSADA", "Calle 9 s/n lote 6", "3815461531", "San Javier"),
    # ===================== RACO =====================
    ("CAMPING DEL VALLE", "HOSTEL/HOSTAL", "Ruta n°341 km 19", "3814426423", "Raco"),
    ("VALLE HERMOSO", "POSADA", "Ruta prov. n°341 km 23.5", "3814426423", "Raco"),
    ("LA PEDRERA", "HOTEL BOUTIQUE", "Atahualpa Yupanqui S/N Ruta 341 km 21", "3815179486", "Raco"),
    ("WILLKAY GLAMPING", "GLAMPING", "Ruta 341 km 22", "3813485491", "Raco"),
    ("DOMOS EL EDEN", "CASA/DPTO", "Ruta 340 km 22", "3815601744", "Raco"),
    # ===================== SAN JOSÉ DE CHASQUIVIL =====================
    ("POSADA SAN JOSE", "POSADA", "José de Chasquivil dpto Tafí Viejo", "3814001619", "San José de Chasquivil"),
    # ===================== EL CADILLAL =====================
    ("LA SOLANA", "POSADA", "Ruta prov 347 km 4,2", "3813034935", "El Cadillal"),
    ("CASA PALMERA", "HOSTAL", "Villa Jardín lote 48", "3816695512", "El Cadillal"),
    ("COMPLEJO SUTERH", "CABAÑA/POSADA", "Ruta 304 km 4", "3813476798", "El Cadillal"),
    # ===================== EL MOLLAR =====================
    ("EL REMANSO", "HOSTERIA", "Alpapuyo s/n", "03867 491153", "El Mollar"),
    ("LA ANGOSTURA", "HOSTERÍA", "La Angostura", "3812080481", "El Mollar"),
    ("PARAISO DEL LAGO", "HOSTERIA", "Ruta Pcial. 355 - El Mollar", "3816989048 / 3814734999", "El Mollar"),
    ("POTRERILLO TURISMO Y CULTURA", "HOSTAL/HOSTEL", "Ruta 355 km 7,5", "3814767764", "El Mollar"),
    ("AIRES DE TAFI", "CABAÑAS", "La Costa 2", "3816464553", "El Mollar"),
    ("COMPLEJO TURISTICO APEM", "CONJ CASA Y/O DEPA", "Camino del Potrerillo ruta 355", "3816328609", "El Mollar"),
    ("VIGIA DEL VALLE", "CONJUNTO DE CASA Y DEPA", "Alto la banda - cerro el pelao", "+5491132180810", "El Mollar"),
    # ===================== TAFÍ DEL VALLE =====================
    ("WAYNAY KILLA", "HOTEL 4*", "La Quesería, Calle Saúl Ubaldini S/N", "3815898514", "Tafí del Valle"),
    ("MIRADOR DEL TAFI", "HOTEL 3*", "Ruta provincial 307 km 61,2", "03867 421219", "Tafí del Valle"),
    ("TAFI", "HOTEL 3*", "Avda Belgrano 177", "03867 421007", "Tafí del Valle"),
    ("COLONIAL", "HOTEL 3*", "Av. Belgrano y Los Faroles", "03867 420140", "Tafí del Valle"),
    ("DEL VALLE SUMAJ", "HOTEL", "Ruta Prov. 307 km 60", "03867 421756", "Tafí del Valle"),
    ("VIRGEN DEL VALLE", "HOTEL 1*", "Lo Menhires 45", "03867 421016", "Tafí del Valle"),
    ("LOS CUARTOS", "HOSTERIA 2*", "Juan Calchaquí s/n", "03867 421444", "Tafí del Valle"),
    ("LA ROSADA", "HOSTERIA 3*", "Av. Belgrano 322", "03867 421323", "Tafí del Valle"),
    ("LUNAHUANA", "HOSTERIA 3*", "Av. Gobernador Critto 540", "03867 421330", "Tafí del Valle"),
    ("SOL DEL VALLE ACA", "HOSTERIA 3*", "Gob. Campero Esquina San Martín", "03867 421027", "Tafí del Valle"),
    ("BUENA VISTA", "HOSTERIA 3*", "Fray Santa María de Oro s/n", "03867 421637", "Tafí del Valle"),
    ("ATEP", "HOSTEL/HOSTERIA", "Los Menhires y Gob. Campero", "03867 421061", "Tafí del Valle"),
    ("ALONDRA", "HOSTEL/HOSTAL", "La Banda", "3816858344", "Tafí del Valle"),
    ("CELIA CORREA", "HOSTEL/HOSTAL", "Belgrano 443", "03867 421170", "Tafí del Valle"),
    ("DON GOYO", "HOTEL/HOSTAL", "Pje. Don Goyo s/n", "03867 421438", "Tafí del Valle"),
    ("DE MI VALLE", "HOSTEL/HOSTAL", "Av. Pte. Perón N° 56", "3813001001", "Tafí del Valle"),
    ("EL ANGEL", "HOSTEL/HOSTAL", "Tupac Amaru s/n", "03867 421581", "Tafí del Valle"),
    ("LA CUMBRE", "HOSTEL/HOSTAL", "Av Perón 120", "03867 421768", "Tafí del Valle"),
    ("LA QUERENCIA", "HOSTEL/HOSTAL", "Jorge Luis Borges s/n", "03867 421831", "Tafí del Valle"),
    ("LOMITA VERDE", "HOSTEL/HOSTAL", "Av. Perón 73", "03867 421757", "Tafí del Valle"),
    ("MEDINA", "HOSTEL/HOSTAL", "Avda. Calchaquí N° 756", "03867 421253", "Tafí del Valle"),
    ("YAYA KUNA HUASI", "HOSTEL/HOSTAL", "Ruta Prov. 315 - El Rincón", "3816641644", "Tafí del Valle"),
    ("LOS MENHIRES II", "HOSTEL/HOSTAL", "Av. Belgrano s/n", "3865314529", "Tafí del Valle"),
    ("LA CIENAGA", "HOSTEL/HOSTAL", "", "3815747548", "Tafí del Valle"),
    ("DEL SOL", "HOSTEL/HOSTAL", "Ruta 307 KM 60, Cost 1 - Bo Malvinas", "4314989", "Tafí del Valle"),
    ("ISABELLA HOSTAL", "HOSTEL/HOSTAL", "Huayra Capac S/N", "3816328609", "Tafí del Valle"),
    ("BALCONES DE TAFI", "CABAÑA", "Ruta Prov. 325 km 2,2 La Banda", "3815889570", "Tafí del Valle"),
    ("ALTOS DE TAFI", "CABAÑA", "Cerro El Pelao", "3815444441", "Tafí del Valle"),
    ("DESCANSO DE LAS PIEDRAS", "CABAÑA", "Madre Teresa de Calcuta s/n - El Churqui", "3815701266", "Tafí del Valle"),
    ("VIGIA DEL VALLE (CABAÑA)", "CABAÑA", "El Tala Casa 97", "1132188108 (solo WSP)", "Tafí del Valle"),
    ("ERNES HUASI", "CABAÑA", "Ruta Provincial 307 km 61", "03867 1549866", "Tafí del Valle"),
    ("ACO", "CABAÑA", "Ruta Prov. 307 Km 57", "3814722755", "Tafí del Valle"),
    ("LAS MARIVAS", "CABAÑA", "Mensebilla s/n La Ovejería", "3815600231", "Tafí del Valle"),
    ("PAQURINA", "CABAÑA", "Ruta 307 KM 60", "3815976138", "Tafí del Valle"),
    ("SAYACUNA HUASI", "CABAÑA", "Ruta 307 y Av. Gob. Critto", "0381 15576-8603", "Tafí del Valle"),
    ("RIO MOLLE", "CABAÑA", "Av. Gianfrancisco s/n - La Ovejería", "3816816849", "Tafí del Valle"),
    ("YACU HUASI", "CABAÑA", "Ruta 307 km 57", "03865 1541662244", "Tafí del Valle"),
    ("VILLA LUXOR", "CABAÑA", "Ruta 307 KM 60", "3813544648", "Tafí del Valle"),
    ("AYLLU", "CABAÑA", "Calle pública s/n camino a las Tacanas", "3813418418", "Tafí del Valle"),
    ("LA SUYANA", "CABAÑA", "Ruta 307 km 57 - Loteo Los Mimbres", "3815778188", "Tafí del Valle"),
    ("LOS MIMBRES", "CABAÑA", "Ruta 307 Km 58 - Loteo Los Mimbres", "3814572457", "Tafí del Valle"),
    ("INTI YANASU", "CABAÑA", "Ruta 307 km 60 Villa Chenaut", "3816611111", "Tafí del Valle"),
    ("WASI MAYU", "CABAÑA", "Calle pública s/n - La Ovejería", "3731 15624445", "Tafí del Valle"),
    ("MAGNOLIA", "CABAÑA", "Loteo Los Castaños Av. María Lidia Chenaut de Bossi s/n", "3814169914", "Tafí del Valle"),
    ("ERNESTINA", "CABAÑA", "Ruta Provincial 307 km 58", "3865417843", "Tafí del Valle"),
    ("COMPLEJO DE CABAÑAS SANTA", "CABAÑA", "Ruta 307 km 60 - Villa Chenaut", "3813382255", "Tafí del Valle"),
    ("LAS FLORES", "CABAÑA", "Ruta 307 km 60 - Villa Chenaut", "3816292716", "Tafí del Valle"),
    ("WINE VILLAGE", "CABAÑA", "Ruta 307 – B° Los Mimbres", "3814149968", "Tafí del Valle"),
    ("EL VIENTO DE MIS SUEÑOS", "APART", "Av. Juan Calchaquí 100", "03867 422557", "Tafí del Valle"),
    ("VENECIA", "APART", "Ruta Provincial 307, km 60", "3863412446", "Tafí del Valle"),
    ("LA MADRINA", "APART", "Ruta Provincial 307, Calle km 61 7", "3813506047", "Tafí del Valle"),
    ("APART DEL VALLE", "APART", "Calle s/n Costa 1", "3816212152", "Tafí del Valle"),
    ("ALTOS DE SANTA ROSA", "CONJ CASA Y/O DEPA", "Bo. Santa Rosa El Churquí", "3813338813", "Tafí del Valle"),
    ("CULTURA TAFI", "CONJ CASA Y/O DEPA", "Pje. Islas Malvinas 50", "3814094968", "Tafí del Valle"),
    ("DOÑA INES", "CONJ CASA Y/O DEPA", "Chenaut s/n – La Costa 1", "3815641776", "Tafí del Valle"),
    ("CACTUS", "CASA/DPTO", "Av. Francisco S/N – Los Cuartos", "3815484136", "Tafí del Valle"),
    ("ECOLAMPING", "CONJ CASA", "A 300 mts de ruta prov 307", "3815792437", "Tafí del Valle"),
    ("ENTRE MONTAÑAS", "CONJ CASA Y/O DEPA", "Ruta 307 - km 60", "3815561060", "Tafí del Valle"),
    ("LA MARINITA", "CONJ CASA Y/O DEPA", "Ruta 307 y Gervasio Cruz", "3813476982", "Tafí del Valle"),
    ("LA MARIA LOURDES", "CONJ CASA Y/O DEPA", "Rosendo Contreras 3a cuadra - Bo Malvinas", "3814647296", "Tafí del Valle"),
    ("LOS ABUELOS", "CONJ CASA Y/O DEPA", "Pje. Islas Malvinas y Pje Hipólito Irigoyen", "3815029057", "Tafí del Valle"),
    ("PURO CAMPO", "CONJ CASA Y/O DEPA", "Ruta 307 km 65", "3815398977", "Tafí del Valle"),
    ("VILLA RURAL SAN MIGUEL DE LA LOMA", "CONJ CASA Y/O DEPA", "Loma de la Ovejería", "3814025654", "Tafí del Valle"),
    ("EL CHURQUI", "CONJ CASA Y/O DEPA", "Pje René Favaloro s/n", "3814766198", "Tafí del Valle"),
    ("VIDITAY", "CONJ CASA", "Ruta 307 km 60 - Loteo Chenaut", "(011) 1523923466", "Tafí del Valle"),
    ("CIELO AZUL", "CONJ DE CASAS", "Barrio Malvinas - Costa 1", "3816212551", "Tafí del Valle"),
    ("TU TIEMPO DEPARTAMENTOS", "CONJ CASA Y/O DEPA", "Av. Belgrano N°55", "3816417785", "Tafí del Valle"),
    ("CASA DE PIEDRAS", "CONJ CASA Y/O DEPA", "Ruta Prov. 307 KM 60", "3815792437", "Tafí del Valle"),
    ("CASTILLO DE PIEDRA", "HOTEL BOUTIQUE", "Ruta 325 – La Banda", "3812215184", "Tafí del Valle"),
    ("LA GUADALUPE", "POSADA", "Av. Lola Mora 650 - Costa 1", "03867 421329", "Tafí del Valle"),
    ("LA POSADA DE TAFI", "POSADA", "Ruta 307 km 62, La Quebradita", "3816378867", "Tafí del Valle"),
    ("LA SOÑADA", "POSADA", "Ruta 307 km 64", "3816240028", "Tafí del Valle"),
    ("INTI WATANA", "POSADA", "Madre Teresa de Calcuta s/n El Churquí", "03867 420178", "Tafí del Valle"),
    ("ESTANCIA LAS CARRERAS", "ESTANCIA RURAL", "Ruta Provincial 325 km 13", "03867 421473", "Tafí del Valle"),
    ("ESTANCIA LOS CUARTOS", "ESTANCIA RURAL", "Miguel Crito S/N", "3815666344", "Tafí del Valle"),
    ("ESTANCIA LAS TACANAS", "ESTANCIA", "Av. Pte. Perón 372", "3814272182", "Tafí del Valle"),
    # ===================== AMPIMPA =====================
    ("OBSERVATORIO DE AMPIMPA", "HOSTEL/HOSTAL", "Ruta 307 Km 107,5 - Ampimpa", "3814027115", "Ampimpa"),
    # ===================== AMAICHA DEL VALLE =====================
    ("L'APACHETA", "HOSTEL/HOSTAL", "Hipólito Yrigoyen y Miguel Araoz", "3838601786", "Amaicha del Valle"),
    ("FINCA ALBARROSA", "ESTANCIA RURAL", "Ruta Nac. N° 40 km 4287", "3838601786", "Amaicha del Valle"),
    # ===================== COLALAO DEL VALLE =====================
    ("RIO DE ARENA", "ESTANCIA", "Ruta n 40 km 4295,5 (el bañado)", "3815870037", "Colalao del Valle"),
    ("DOÑA ROGELIA", "HOSTEL/HOSTAL", "Ruta Nac. 40 (entrada)", "3815879440", "Colalao del Valle"),
    ("DE LAS VIÑAS", "POSADA", "Ruta Nac. N° 40 KM 4314", "3815879440", "Colalao del Valle"),
    ("HOSTAL DEL VALLE", "HOSTEL/HOSTAL", "Ruta Nac. 40 (entrada)", "3815879440", "Colalao del Valle"),
    # ===================== SAN PEDRO DE COLALAO =====================
    ("EL PORTAL DE SAN PEDRO", "POSADA", "24 de Septiembre esq. Tucumán", "03862 481467", "San Pedro de Colalao"),
    ("LAS TACANAS", "POSADA", "24 de Septiembre esq. Tucumán", "3816031130", "San Pedro de Colalao"),
    ("COMPLEJO LOS LEONES", "CONJ CASA/DEPTO", "Ruta 311 km 23", "3816292669", "San Pedro de Colalao"),
    ("DEL ABUELO", "CONJ CASA/DEPTO", "Ruta 311 km 23", "3816292669", "San Pedro de Colalao"),
    ("HOSTERIA EL LAPACHO", "HOSTERIA", "Ruta 311 km 24", "03812370022", "San Pedro de Colalao"),
    ("EL PARAISO", "HOSTERIA", "Las Heras 2da cuadra", "(03862) 481752", "San Pedro de Colalao"),
    ("AQUI ME QUEDO", "HOSTEL/HOSTAL", "Ruta 311 km 24,5", "3815249424", "San Pedro de Colalao"),
    ("INTIHUATANA", "HOSTEL/HOSTAL", "Calle Ayacucho y 27 s/n", "3816295949", "San Pedro de Colalao"),
    ("ATEP SAN PEDRO DE COLALAO", "HOSTEL/HOSTAL", "Calle 25 de mayo s/n", "03862 481105", "San Pedro de Colalao"),
    ("ANTAKY", "HOSTEL/HOSTAL", "Calle Candelaria y Pje Crdena", "(03862) 481040", "San Pedro de Colalao"),
    ("FINCA CLUB DE CAMPO", "HOSTEL/HOSTAL", "Ruta 311 km 22", "3815634442", "San Pedro de Colalao"),
    ("HUAYCO", "HOSTEL/HOSTAL", "9 de julio 3ra cuadra", "03862 481040", "San Pedro de Colalao"),
    ("LA CAÑADA", "HOSTEL/HOSTAL", "Ruta 311 km 23", "3814471801", "San Pedro de Colalao"),
    ("LOS ARCOS", "HOSTEL/HOSTAL", "Las Heras 4ta cuadra", "3814023541", "San Pedro de Colalao"),
    ("LOS TARCOS", "HOSTEL/HOSTAL", "Congreso 3ra cuadra", "3814428559", "San Pedro de Colalao"),
    ("SANTA RITA", "HOSTEL/HOSTAL", "Pascual Contursi esq. Río Tipa", "03862 481303", "San Pedro de Colalao"),
    ("VICTORIA", "HOSTEL/HOSTAL", "25 de mayo 3ra cuadra", "03862 481200", "San Pedro de Colalao"),
    ("NIEVA", "HOSTEL/HOSTAL", "Las Heras y 9 de Julio", "03862 481111", "San Pedro de Colalao"),
    ("NUESTRO SUEÑO", "HOSTEL/HOSTAL", "Barrio Villa Silvita 5ta entrada Malvinas", "3815563170", "San Pedro de Colalao"),
    ("COMPLEJO LOURDES", "HOSTEL/HOSTAL", "Calle A. Heredia esq Pje. L. Padilla Villa Rita", "3815035429", "San Pedro de Colalao"),
    ("INTI HUANA", "CABAÑA", "Calandria s/n", "03862 481382", "San Pedro de Colalao"),
    ("DEL RIO", "CABAÑA", "Av. Martín Belmonte s/n", "3815061074", "San Pedro de Colalao"),
    # ===================== TRANCAS =====================
    ("LOS SAUCES", "HOSTEL/HOSTAL", "Ruta Nac. 9 km 1361", "3815267921", "Trancas"),
    # ===================== LULES =====================
    ("DIP", "HOSTEL/HOSTAL", "Miguel Lillo 300", "(0381) 4816945", "Lules"),
    ("NARCISO", "CABAÑA", "Ruta Prov. 321 intersección 301", "3815907009", "Lules"),
    # ===================== SIMOCA =====================
    ("EL PORTAL DE SIMOCA", "HOSTEL/HOSTAL", "9 de Julio 522", "03865 481247", "Simoca"),
    ("MI", "HOSTEL/HOSTAL", "Gómez Llues 1031", "3815600231", "Simoca"),
    ("HOSTAL DEL VALLE (SIMOCA)", "HOSTEL/HOSTAL", "25 de Mayo 0674", "03863 481990", "Simoca"),
    # ===================== MONTEROS =====================
    ("LAS HORTENSIAS", "HOTEL 3*", "Sarmiento N°170", "3863400393", "Monteros"),
    ("EL TIJAR", "POSADA", "Rivadavía N° 570", "381155727785", "Monteros"),
    # ===================== CONCEPCIÓN =====================
    ("EL MIRADOR DEL CENTRO", "HOTEL 1*", "Nassif Estefano 31", "03865 421053", "Concepción"),
    # ===================== AGUILARES =====================
    ("LA CASONA", "POSADA", "Sarmiento 960", "03865 481400", "Aguilares"),
    ("HOSTERIA MUNICIPAL", "HOSTERÍA", "Av. Independencia 951", "3816334160", "Aguilares"),
    ("LA MARMOL", "HOSTEL/HOSTAL", "José Marmol 663", "3815624299", "Aguilares"),
    # ===================== ALBERDI =====================
    ("ESCABA", "HOSTERIA 3*", "Ruta provincial N°308 - Escaba", "3817030229", "Alberdi"),
    ("ALBERDI", "HOSTEL/HOSTAL", "Moreno 440", "03865 471378", "Alberdi"),
    ("SAN MARTIN", "HOSTEL/HOSTAL", "San Martín 683", "03865 471532", "Alberdi"),
    # ===================== GRANEROS =====================
    ("TACO RALO", "HOSTERIA", "Buenos Aires s/n", "3814426881 / 3814388293", "Graneros"),
    # ===================== LAS QUEÑUAS =====================
    ("LAS QUEÑUAS", "POSADA", "José de Chasquivil", "3814001619", "San José de Chasquivil"),
]


def migrar_v1_2():
    """Migración v1.2: Agrega columnas categoria y telefono a hoteles + carga datos semilla de alojamientos."""
    log_info("Ejecutando migración v1.2 (categoría, teléfono y datos de alojamientos)...")

    conn = db.obtener_conexion()
    if not conn:
        log_error("No se pudo obtener conexión para migración v1.2")
        return False

    try:
        cursor = conn.cursor()

        # 1. Agregar columnas nuevas
        for sql in SQL_MIGRACION_V1_2:
            try:
                cursor.execute(sql)
            except Exception as e:
                log_info(f"Nota migración v1.2 (columna): {e}")

        # 2. Insertar hoteles semilla (solo si no existen)
        insertados = 0
        existentes = 0
        for nombre, categoria, direccion, telefono, ciudad in HOTELES_SEMILLA:
            # Verificar si ya existe por nombre y ciudad
            cursor.execute(
                "SELECT id FROM hoteles WHERE UPPER(nombre) = UPPER(%s) AND UPPER(ciudad_localidad) = UPPER(%s)",
                (nombre, ciudad)
            )
            if cursor.fetchone():
                # Actualizar categoria y telefono si faltan
                cursor.execute(
                    "UPDATE hoteles SET categoria = COALESCE(categoria, %s), telefono = COALESCE(telefono, %s) "
                    "WHERE UPPER(nombre) = UPPER(%s) AND UPPER(ciudad_localidad) = UPPER(%s)",
                    (categoria, telefono, nombre, ciudad)
                )
                existentes += 1
            else:
                cursor.execute(
                    "INSERT INTO hoteles (nombre, categoria, direccion, telefono, ciudad_localidad) "
                    "VALUES (%s, %s, %s, %s, %s)",
                    (nombre, categoria, direccion, telefono, ciudad)
                )
                insertados += 1

        conn.commit()
        cursor.close()
        log_info(f"Migración v1.2 completada: {insertados} hoteles insertados, {existentes} ya existían")
        return True

    except Exception as e:
        conn.rollback()
        log_error("Error durante migración v1.2", e)
        return False
    finally:
        db.liberar_conexion(conn)


# ============================================================
# MIGRACIÓN V1.3: Alertas operativas y trazabilidad avanzada
# ============================================================
SQL_MIGRACION_V1_3 = [
    """
    CREATE TABLE IF NOT EXISTS alertas_sistema (
        id SERIAL PRIMARY KEY,
        tipo VARCHAR(50) NOT NULL,
        severidad VARCHAR(20) NOT NULL DEFAULT 'warning',
        estado VARCHAR(20) NOT NULL DEFAULT 'pendiente',
        bloqueante BOOLEAN NOT NULL DEFAULT FALSE,
        sujeto_nombre VARCHAR(300) NOT NULL,
        sujeto_documento VARCHAR(50),
        hotel_origen VARCHAR(300),
        hotel_relacionado VARCHAR(300),
        huesped_id INTEGER REFERENCES huespedes(id) ON DELETE SET NULL,
        huesped_relacionado_id INTEGER REFERENCES huespedes(id) ON DELETE SET NULL,
        fecha_entrada DATE,
        fecha_salida DATE,
        horas_lapso INTEGER,
        resumen TEXT NOT NULL,
        payload_json TEXT,
        importacion_tipo VARCHAR(20),
        usuario_creacion_id INTEGER REFERENCES usuarios(id),
        usuario_revision_id INTEGER REFERENCES usuarios(id),
        fecha_creacion TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        fecha_revision TIMESTAMP,
        CONSTRAINT chk_alerta_severidad CHECK (severidad IN ('info', 'warning', 'danger', 'critical')),
        CONSTRAINT chk_alerta_estado CHECK (estado IN ('pendiente', 'revisada', 'descartada', 'confirmada'))
    );
    """,
    "CREATE INDEX IF NOT EXISTS idx_alertas_estado ON alertas_sistema(estado);",
    "CREATE INDEX IF NOT EXISTS idx_alertas_tipo ON alertas_sistema(tipo);",
    "CREATE INDEX IF NOT EXISTS idx_alertas_fecha ON alertas_sistema(fecha_creacion DESC);",
    "CREATE INDEX IF NOT EXISTS idx_alertas_documento ON alertas_sistema(sujeto_documento);",
]


def migrar_v1_3():
    """Migración v1.3: crea tabla de alertas del sistema."""
    log_info("Ejecutando migración v1.3 (alertas operativas)...")

    conn = db.obtener_conexion()
    if not conn:
        log_error("No se pudo obtener conexión para migración v1.3")
        return False

    try:
        cursor = conn.cursor()

        for sql in SQL_MIGRACION_V1_3:
            try:
                cursor.execute(sql)
            except Exception as e:
                log_info(f"Nota migración v1.3: {e}")

        conn.commit()
        cursor.close()
        log_info("Migración v1.3 completada exitosamente")
        return True

    except Exception as e:
        conn.rollback()
        log_error("Error durante migración v1.3", e)
        return False
    finally:
        db.liberar_conexion(conn)


def migrar_v1_4():
    """Migración v1.4: normaliza nacionalidad y procedencia históricas."""
    log_info("Ejecutando migración v1.4 (normalización geográfica)...")

    conn = db.obtener_conexion()
    if not conn:
        log_error("No se pudo obtener conexión para migración v1.4")
        return False

    try:
        resultado = normalizar_historico_huespedes(conn)
        conn.commit()
        log_info(
            f"Migración v1.4 completada: {resultado['actualizados']} huéspedes normalizados de {resultado['total']}"
        )
        return True
    except Exception as e:
        conn.rollback()
        log_error("Error durante migración v1.4", e)
        return False
    finally:
        db.liberar_conexion(conn)


# ============================================================
# MIGRACIÓN V1.5: Índices para control de cargas por operador
# ============================================================
SQL_MIGRACION_V1_5 = [
    "CREATE INDEX IF NOT EXISTS idx_huespedes_usuario_carga ON huespedes(usuario_carga_id);",
    "CREATE INDEX IF NOT EXISTS idx_huespedes_origen_carga ON huespedes(origen_carga);",
    "CREATE INDEX IF NOT EXISTS idx_importaciones_usuario ON importaciones_log(usuario_id);",
]


def migrar_v1_5():
    """Migración v1.5: crea índices para optimizar consultas de control de cargas por operador."""
    log_info("Ejecutando migración v1.5 (índices control de cargas)...")

    conn = db.obtener_conexion()
    if not conn:
        log_error("No se pudo obtener conexión para migración v1.5")
        return False

    try:
        cursor = conn.cursor()

        for sql in SQL_MIGRACION_V1_5:
            try:
                cursor.execute(sql)
            except Exception as e:
                log_info(f"Nota migración v1.5: {e}")

        conn.commit()
        cursor.close()
        log_info("Migración v1.5 completada exitosamente")
        return True

    except Exception as e:
        conn.rollback()
        log_error("Error durante migración v1.5", e)
        return False
    finally:
        db.liberar_conexion(conn)
