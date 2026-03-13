"""
S.C.A.H. - Script de carga masiva de hoteles
Inserta los hoteles oficiales extraídos de las planillas de referencia.
Solo inserta si el hotel NO existe en la BD (comparación case-insensitive por nombre).
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from database.connection import db

# ─── Listado completo de hoteles ─────────────────────────────────────────────
# Formato: (nombre, categoria, direccion, telefono, ciudad_localidad)

HOTELES = [
    # ═══════════════════════════ SAN MIGUEL DE TUCUMÁN ═══════════════════════
    # Hotel 5*
    ("CATALINAS PARK", "SMT - HOTEL 5*", "Av. Soldati N° 380", "(0381) 4220624", "San Miguel de Tucumán"),
    ("SHERATON", "SMT - HOTEL 5*", "Av. Soldati 440", "(0381) 4554700", "San Miguel de Tucumán"),
    # Hotel 4*
    ("DEL JARDIN", "SMT - HOTEL 4*", "Laprida 463", "(0381) 4522008", "San Miguel de Tucumán"),
    ("RAMADA PLAZA", "SMT - HOTEL 4*", "Laprida 35", "(0381) 4311755", "San Miguel de Tucumán"),
    ("METROPOL", "SMT - HOTEL 4*", "24 de Septiembre 524", "(0381) 5157338", "San Miguel de Tucumán"),
    ("GARDEN PARK", "SMT - HOTEL 4*", "Av. Soldati 330", "(0381) 4310700", "San Miguel de Tucumán"),
    ("TUCUMAN CENTER", "SMT - HOTEL 4*", "25 de Mayo 230", "(0381) 4525555", "San Miguel de Tucumán"),
    ("BICENTENARIO", "SMT - HOTEL 4*", "Las Heras 21", "(0381) 2546282", "San Miguel de Tucumán"),
    ("HILTON", "SMT - HOTEL 4*", "Las Piedras 1550", "(0381) 4532000", "San Miguel de Tucumán"),
    # Hotel 3*
    ("EMBAJADOR", "SMT - HOTEL 3*", "Las Heras 221", "(0381) 4311264", "San Miguel de Tucumán"),
    ("CARLOS V", "SMT - HOTEL 3*", "25 de Mayo 330", "(0381) 4311666", "San Miguel de Tucumán"),
    ("COLONIAL", "SMT - HOTEL 3*", "San Martín 35", "(0381) 4311523", "San Miguel de Tucumán"),
    ("AMERIAN", "SMT - HOTEL 3*", "Santiago del Estero 419", "(0381) 5601766", "San Miguel de Tucumán"),
    ("FRANCIA", "SMT - HOTEL 3*", "Crisóstomo Alvarez 467", "(0381) 4310781", "San Miguel de Tucumán"),
    ("MEDITERRANEO", "SMT - HOTEL 3*", "24 de Septiembre 346", "(0381) 3126849", "San Miguel de Tucumán"),
    ("MIAMI", "SMT - HOTEL 3*", "Junín 580", "(0381) 5847361", "San Miguel de Tucumán"),
    ("PREMIER", "SMT - HOTEL 3*", "Crisóstomo Alvarez 510", "(0381) 4310382", "San Miguel de Tucumán"),
    ("SOLAR DEL NORTE", "SMT - HOTEL 3*", "México 879", "(0381) 4272722", "San Miguel de Tucumán"),
    ("REPUBLICA", "SMT - HOTEL 3*", "Virgen de la Merced 71", "(0381) 4310481", "San Miguel de Tucumán"),
    ("LE PARK", "SMT - HOTEL 3*", "Junín 1134", "(0381) 4218818", "San Miguel de Tucumán"),
    # Hotel 2*
    ("AMERICA", "SMT - HOTEL 2*", "Santiago del Estero 1064", "(0381) 4224853", "San Miguel de Tucumán"),
    ("VERSAILLES", "SMT - HOTEL 2*", "Crisóstomo Alvarez 481", "(0381) 4229760", "San Miguel de Tucumán"),
    ("HOTEL LA TERMINAL", "SMT - HOTEL 2*", "Av. Brígido Terán 227", "(0381) 4210647", "San Miguel de Tucumán"),
    ("LG GOLDEN", "SMT - HOTEL 2*", "Bernabé Aráoz 36", "(0381) 4216286", "San Miguel de Tucumán"),
    # Hotel 1*
    ("ASTORIA", "SMT - HOTEL 1*", "Congreso 88", "(0381) 2600959", "San Miguel de Tucumán"),
    ("GARDEN", "SMT - HOTEL 1*", "Crisóstomo Alvarez 627", "(0381) 4311246", "San Miguel de Tucumán"),
    ("LORENZO SUITES", "SMT - HOTEL 1*", "San Lorenzo 590", "(0381) 3604382", "San Miguel de Tucumán"),
    ("CHARCAS", "SMT - HOTEL 1*", "Charcas 131", "(0381) 4219576", "San Miguel de Tucumán"),
    # Apart Hotel
    ("TP APART", "SMT - APART HOTEL", "Santa Fe 1635", "(0381) 3183733", "San Miguel de Tucumán"),
    # Hostel / Hostal
    ("BRISA", "SMT - HOSTEL", "Congreso 190", "(381) 5167770", "San Miguel de Tucumán"),
    ("DEL CENTRO", "SMT - HOSTEL", "San Martín 218", "(0381) 6643659", "San Miguel de Tucumán"),
    ("LAS CARRETAS", "SMT - HOSTAL", "Benjamín Aráoz 38", "(0381) 5813634", "San Miguel de Tucumán"),
    ("MERCER", "SMT - HOSTEL", "Suipacha 685", "(0381) 4331268", "San Miguel de Tucumán"),
    ("A LA GURDA", "SMT - HOSTEL", "Maipú 490", "(0381) 2324008", "San Miguel de Tucumán"),
    ("TU HOSTEL", "SMT - HOSTEL", "Mendoza 912", "(0381) 3982019", "San Miguel de Tucumán"),
    # Otros
    ("THE POINT CASA", "SMT - CONJ CASA/DEPTO", "Virgen de La Merced 120", "3816319589", "San Miguel de Tucumán"),
    ("UNIVERSO", "SMT - RESIDENCIAL", "Santiago del Estero 1060", "(0381) 4311136", "San Miguel de Tucumán"),

    # ═══════════════════════════ YERBA BUENA ═════════════════════════════════
    ("HOWARD JHONSONS", "YB - 4*", "Av. Aconquija 1136", "(0381) 4257796", "Yerba Buena"),
    ("EL CORTE", "YB - HOSTERIA", "Av. Aconquija 3297", "(0381) 4256764", "Yerba Buena"),
    ("RIO MOLLE", "YB - CONJ CASA Y/O DEPA", "Av. Aconquija 334", "3816686686", "Yerba Buena"),
    ("TRES ARROYOS", "YB - CABAÑAS", "Jorge Luis Borges 3150", "3815028402", "Yerba Buena"),
    ("CASA LOLA", "YB - POSADA", "Florida Sur 167", "(381) 5479146", "Yerba Buena"),
    ("PURA VIDA MAE", "YB - HOSTEL", "Pringles 1714", "3816712532", "Yerba Buena"),
    ("LA PROVIDENCIA", "YB - HOSTAL", "Pje. San Luis 598", "3813330030", "Yerba Buena"),
    ("ARRULLO DE LUNA", "YB - HOSTEL", "Bascary 36", "3815490660", "Yerba Buena"),

    # ═══════════════════════════ TAFÍ VIEJO ══════════════════════════════════
    ("ATAHUALPA YUPANQUI", "Tafi Viejo 3*", "Paisandú 2400", "3814595835", "Tafí Viejo"),

    # ═══════════════════════════ TAFÍ DEL VALLE ═════════════════════════════
    # Hostel/Hostal
    ("DE MI VALLE", "TAFI DEL VALLE - HOSTEL/HOSTAL", "Av. Pte. Perón N° 56", "", "Tafí del Valle"),
    ("EL ANGEL", "TAFI DEL VALLE - HOSTEL/HOSTAL", "Túpac Amaru s/n", "3813001001", "Tafí del Valle"),
    ("LA CUMBRE", "TAFI DEL VALLE - HOSTEL/HOSTAL", "Av Peron 120", "03867 421768", "Tafí del Valle"),
    ("LA QUERENCIA", "TAFI DEL VALLE - HOSTEL/HOSTAL", "Jorge Luis Borges s/n", "03867 421261", "Tafí del Valle"),
    ("LOMITA VERDE", "TAFI DEL VALLE - HOSTEL/HOSTAL", "Av. Peron 73", "03867 421757", "Tafí del Valle"),
    ("MEDINA", "TAFI DEL VALLE - HOSTEL/HOSTAL", "Avda. Calchaquí N° 756", "03867 421253", "Tafí del Valle"),
    ("YAYA KUNA HUASI", "TAFI DEL VALLE - HOSTEL/HOSTAL", "Ruta Prov. 315- El Rincon", "3816641644", "Tafí del Valle"),
    ("LOS MENHIRES II", "TAFI DEL VALLE - HOSTEL/HOSTAL", "Av. Belgrano s/n", "3865314529", "Tafí del Valle"),
    ("LA CIENAGA", "TAFI DEL VALLE - HOSTEL/HOSTAL", "", "3815747548", "Tafí del Valle"),
    ("DEL SOL", "TAFI DEL VALLE - HOSTEL/HOSTAL", "Ruta 307 KM 60, Cost 1 - Bo Malvinas", "4314989", "Tafí del Valle"),
    ("ISABELLA HOSTAL", "TAFI DEL VALLE - HOSTEL/HOSTAL", "Huayra Capac S/N", "3816328609", "Tafí del Valle"),
    # Cabaña
    ("BALCONES DE TAFI", "TAFI DEL VALLE - CABAÑA", "Ruta Prov. 325 km 2,3 La Banda", "3815889570", "Tafí del Valle"),
    ("ALTOS DE TAFI", "TAFI DEL VALLE - CABAÑA", "Cerro El Pelao", "3815444441", "Tafí del Valle"),
    ("DESCANSO DE LAS PIEDRAS", "TAFI DEL VALLE - CABAÑA", "Madre Teresa de Calcuta s/n- El Churqui", "3815701266", "Tafí del Valle"),
    ("VIGIA DEL VALLE", "TAFI DEL VALLE - CABAÑA", "El Tala Casa 97", "1132180810", "Tafí del Valle"),
    ("ERNES HUASI", "TAFI DEL VALLE - CABAÑA", "Ruta Provincial 307 km 61", "03867 15494866", "Tafí del Valle"),
    ("JACY", "TAFI DEL VALLE - CABAÑA", "Ruta 307 Km 57", "3814722755", "Tafí del Valle"),
    ("LAS MARIAS", "TAFI DEL VALLE - CABAÑA", "Mensebillas s/n La Ovejería", "3815600231", "Tafí del Valle"),
    ("PAQARINA", "TAFI DEL VALLE - CABAÑA", "Ruta 307 KM 60", "3815976138", "Tafí del Valle"),
    ("SAYACUNA HUASI", "TAFI DEL VALLE - CABAÑA", "Ruta 307 y Av. Gob. Critto", "03867 15576-8603", "Tafí del Valle"),
    ("RIO MOLLE", "TAFI DEL VALLE - CABAÑA", "Av. Gianfrancisco s/n- La Ovejería", "3816168849", "Tafí del Valle"),
    ("YACU HUASI", "TAFI DEL VALLE - CABAÑA", "Ruta 307 Av. KM 57", "03865 1541662244", "Tafí del Valle"),
    ("VILLA LUXOR", "TAFI DEL VALLE - CABAÑA", "Ruta 307 KM 60", "3813544648", "Tafí del Valle"),
    ("AYLLU", "TAFI DEL VALLE - CABAÑA", "Calle publica s/n camino a las Tacanas", "3813418418", "Tafí del Valle"),
    ("LA SUYANA", "TAFI DEL VALLE - CABAÑA", "Ruta 307- km 57- Loteo Los Mimbres", "3815778188", "Tafí del Valle"),
    ("LOS MIMBRES", "TAFI DEL VALLE - CABAÑA", "Ruta 307 Km58- Loteo Los Mimbres", "3814572439", "Tafí del Valle"),
    ("INTI YANASU", "TAFI DEL VALLE - CABAÑA", "Ruta 307 km 60 Villa Chenaut", "3816611117", "Tafí del Valle"),
    ("WASI MAYU", "TAFI DEL VALLE - CABAÑA", "Callepublica s/n - La ovejería", "3731 15624448", "Tafí del Valle"),
    ("MAGNOLIA", "TAFI DEL VALLE - CABAÑA", "Loteo Los Castaños Avenida, María Lidia Chenaut de Bossi s/n", "3814166914", "Tafí del Valle"),
    ("ERNESTINA", "TAFI DEL VALLE - CABAÑA", "Ruta Provincial 307 km58", "3865417843", "Tafí del Valle"),
    ("COMPLEJO DE CABAÑAS SHANTA", "TAFI DEL VALLE - CABAÑA", "Ruta307 km 60 -villachenaut", "3813382255", "Tafí del Valle"),
    ("LAS FLORES", "TAFI DEL VALLE - CABAÑA", "Ruta307 km 60 -villachenaut", "3816292716", "Tafí del Valle"),
    ("WINE VILLAGE", "TAFI DEL VALLE - CABAÑA", "Ruta 307 – B° Los Mimbres", "3814149688", "Tafí del Valle"),
    # Apart
    ("EL VIENTO DE MIS SUEÑOS", "TAFI DEL VALLE - APART", "Av. Juan Calchaquí 100", "03867 422557", "Tafí del Valle"),
    ("VENECIA", "TAFI DEL VALLE - APART", "Ruta Provincial 307, km 60", "3863412446", "Tafí del Valle"),
    ("LA MADRINA", "TAFI DEL VALLE - APART", "Ruta Provincial 307, Calle km 61 7", "3813506047", "Tafí del Valle"),
    ("APART DEL VALLE", "TAFI DEL VALLE - APART", "Calle s/n Costa 1", "3816212551", "Tafí del Valle"),
    # CONJ CASA Y/O DEPA
    ("ALTOS DE SANTA ROSA", "TAFI DEL VALLE - CONJ CASA Y/O DEPA", "Bo. Santa Rosa El Churqui", "3813338813", "Tafí del Valle"),
    ("CULTURA TAFI", "TAFI DEL VALLE - CONJ CASA Y/O DEPA", "Pje. Islas Malvinas 50", "3814094968", "Tafí del Valle"),
    ("CACTUS", "TAFI DEL VALLE - CASA/DPTO", "Av. Francisco S/N – Los Cuartos", "3815484136", "Tafí del Valle"),
    ("ECOGLAMPING", "TAFI DEL VALLE - CONJ CASA Y/O DEPA", "A 300 mts de ruta prov 307", "3815792437", "Tafí del Valle"),
    ("ENTRE MONTAÑAS", "TAFI DEL VALLE - CONJ CASA", "Ruta 307 - km 60", "3815561060", "Tafí del Valle"),
    ("LA MARINITA", "TAFI DEL VALLE - CONJ CASA Y/O DEPA", "Ruta 307 y Gervasio Cruz", "3813476982", "Tafí del Valle"),
    ("LA MARIA LOURDES", "TAFI DEL VALLE - CONJ CASA Y/O DEPA", "Rosendo Contreras 3a cuadra- Bo Malvinas", "3814647296", "Tafí del Valle"),
    ("LOS ABUELOS", "TAFI DEL VALLE - CONJ CASA Y/O DEPA", "Pje. Islas Malvinas y Pje Hipolito Irigoyen", "3815029057", "Tafí del Valle"),
    ("PURO CAMPO", "TAFI DEL VALLE - CONJ CASA Y/O DEPA", "Ruta 307 km 65", "3815398977", "Tafí del Valle"),
    ("VILLA RURAL SAN MIGUEL DE LA LOMA", "TAFI DEL VALLE - CONJ CASA", "Loma de la Ovejería", "3814025654", "Tafí del Valle"),
    ("EL CHURQUI", "TAFI DEL VALLE - CONJ CASA", "Pje Rene Favaloro s/n", "3814766198", "Tafí del Valle"),
    ("VIDITAY", "TAFI DEL VALLE - CONJ CASA Y/O DEPA", "Ruta 307 km 60 - Loteo Chenaut", "(011)1523923466", "Tafí del Valle"),
    ("CIELO AZUL", "TAFI DEL VALLE - CONJ DE CASAS", "Barrio Malvinas -Costa 1", "3816212551", "Tafí del Valle"),
    ("TU TIEMPO DEPARTAMENTOS", "TAFI DEL VALLE - CONJ CASA Y/O DEPA", "Av. Belgrano N°55", "3816417785", "Tafí del Valle"),
    ("CASA DE PIEDRAS", "TAFI DEL VALLE - CONJ CASA", "Ruta Prov. 307 KM 60", "3815792437", "Tafí del Valle"),
    # Hotel Boutique
    ("CASTILLO DE PIEDRA", "TAFI DEL VALLE - HOTEL BOUTIQUE", "Ruta 325 – La Banda", "3812215184", "Tafí del Valle"),
    # Posada
    ("LA GUADALUPE", "TAFI DEL VALLE - POSADA", "Av. Lola Mora 650- Costa 1", "03867 421329", "Tafí del Valle"),
    ("LA POSADA DE TAFI", "TAFI DEL VALLE - POSADA", "Ruta 307 km 62, La Quebradita", "3816378867", "Tafí del Valle"),
    ("LA SOÑADA", "TAFI DEL VALLE - POSADA", "Ruta 307 km 64", "3816240028", "Tafí del Valle"),
    ("INTI WATANA", "TAFI DEL VALLE - POSADA", "Madre Teresa de Calcuta s/n El Churqui", "03867 420178", "Tafí del Valle"),
    # Estancia Rural
    ("ESTANCIA LAS CARRERAS", "TAFI DEL VALLE - ESTANCIA RURAL", "Ruta Provincial 325 km 13", "03867 421473", "Tafí del Valle"),
    ("ESTANCIA LOS CUARTOS", "TAFI DEL VALLE - ESTANCIA RURAL", "Miguel Crito S/N", "3815666344", "Tafí del Valle"),
    ("ESTANCIA LAS TACANAS", "TAFI DEL VALLE - ESTANCIA RURAL", "Av. Pte. Peron 372", "386742182", "Tafí del Valle"),
    # Hotel
    ("WAYNAY KILLA", "TAFI DEL VALLE - HOTEL 4*", "La Quesería, Calle Saúl Ubaldini S/n", "3815898514", "Tafí del Valle"),
    ("MIRADOR DEL TAFI", "TAFI DEL VALLE - HOTEL 3*", "Ruta Provincial 307 km 61,2", "03867 421219", "Tafí del Valle"),
    ("TAFI", "TAFI DEL VALLE - HOTEL 3*", "Avda Belgrano 177", "03867 421007", "Tafí del Valle"),
    ("COLONIAL", "TAFI DEL VALLE - HOTEL 3*", "Av. Belgrano y Los Faroles", "03867 420140", "Tafí del Valle"),
    ("DEL VALLE SUMAJ", "TAFI DEL VALLE - HOTEL", "Ruta Prov 307 km 60", "03867 421756", "Tafí del Valle"),
    ("VIRGEN DEL VALLE", "TAFI DEL VALLE - HOTEL 1*", "Lo Menhires 45", "", "Tafí del Valle"),
    # Hostería
    ("LOS CUARTOS", "TAFI DEL VALLE - HOSTERÍA 2*", "Juan Calchaquí s/n", "03867 421444", "Tafí del Valle"),
    ("LA ROSADA", "TAFI DEL VALLE - HOSTERÍA 3*", "Av. Belgrano 322", "03867 421323", "Tafí del Valle"),
    ("LUNAHUANA", "TAFI DEL VALLE - HOSTERÍA 3*", "Av. Gobernador Critto 540", "", "Tafí del Valle"),
    ("SOL DEL VALLE ACA", "TAFI DEL VALLE - HOSTERÍA 3*", "Gob. Campero Esquina San Martín", "03867 421027", "Tafí del Valle"),
    ("BUENA VISTA", "TAFI DEL VALLE - HOSTERÍA 3*", "Fray Santa María de Oro s/n", "03867 421637", "Tafí del Valle"),
    ("ATEP", "TAFI DEL VALLE - HOSTEL/HOSTAL", "Los Menhires y Gob. Campero", "03867 421061", "Tafí del Valle"),
    ("ALONDRA", "TAFI DEL VALLE - HOSTEL/HOSTAL", "", "", "Tafí del Valle"),
    ("CELIA CORREA", "TAFI DEL VALLE - HOSTEL/HOSTAL", "Belgrano 443", "03867 421170", "Tafí del Valle"),
    ("DON GOYO", "TAFI DEL VALLE - HOSTEL/HOSTAL", "Pje. Don Goyo s/n", "03867 421438", "Tafí del Valle"),

    # ═══════════════════════════ SAN JAVIER ══════════════════════════════════
    ("SOL SAN JAVIER", "SAN JAVIER - 4*", "Ruta 340 km 23", "4929200", "San Javier"),
    ("FLOR DE LOTO", "SAN JAVIER - HOSTEL/HOSTAL", "Calles 5 y Ruta 340", "3813019779", "San Javier"),
    ("LAS YUNGAS", "SAN JAVIER - HOSTEL/HOSTAL", "Ruta Provincial 338 KM15", "3813514170", "San Javier"),
    ("SURI YACU", "SAN JAVIER - POSADA", "Calle 9 s/n lote 6", "3815461531", "San Javier"),

    # ═══════════════════════════ RACO ════════════════════════════════════════
    ("CAMPING DEL VALLE", "RACO - HOSTAL/HOSTEL", "Ruta n°341 km 19", "3814426418", "Raco"),
    ("VALLE HERMOSO", "RACO - POSADA", "Ruta prov. n°341km 23.5", "3814426243", "Raco"),
    ("LA PEDRERA", "RACO - HOTEL BOUTIQUE", "Atahualpa Yupanqui S/N Ruta 341 km 21", "3815179486", "Raco"),
    ("WILLKAY GLAMPING", "RACO - Glamping", "Ruta 341 km 22", "3813485941", "Raco"),
    ("DOMOS EL EDEN", "RACO - CASA/DPTO", "Ruta 340 km 22", "3815601744", "Raco"),

    # ═══════════════════════════ SAN JOSE DE CHASQUIVIL ══════════════════════
    ("LAS QUEÑUAS", "POSADA - SAN JOSE DE CHASQUIVIL", "Jose de Chasquivil dpto Tafi viejo", "3814001619", "San José de Chasquivil"),

    # ═══════════════════════════ EL CADILLAL ═════════════════════════════════
    ("LA SOLARIA", "EL CADILLAL - POSADA", "Ruta prov 347 km 4,2", "3813034935", "El Cadillal"),
    ("CASA PALMERA", "EL CADILLAL - HOSTAL", "Villa Jardín lote 48", "3816695512", "El Cadillal"),
    ("COMPLEJO SUTERH", "EL CADILLAL - CABAÑA/POSADA", "Ruta 304 km 4", "3813476769", "El Cadillal"),

    # ═══════════════════════════ EL MOLLAR ═══════════════════════════════════
    ("EL REMANSO", "EL MOLLAR - HOSTERÍA", "Alpapuyo s/n", "03867 491153", "El Mollar"),
    ("LA ANGOSTURA", "EL MOLLAR - HOSTERÍA", "La angostura", "3812080481", "El Mollar"),
    ("PARAISO DEL LAGO", "EL MOLLAR - HOSTERÍA", "Ruta Pcial. 355- el Mollar", "3816989048", "El Mollar"),
    ("POTRERILLO TURISMO Y CULTURA", "EL MOLLAR - HOSTAL/HOSTEL", "Ruta Pcial. km 7,5", "3814767764", "El Mollar"),
    ("AIRES DE TAFI", "EL MOLLAR - CABAÑAS", "La costa 2", "3816464552", "El Mollar"),
    ("COMPLEJO TURISTICO APEM", "EL MOLLAR - CONJ CASA Y/O DEPA", "Camino del Potrerillo ruta 355", "3816328609", "El Mollar"),
    ("VIGIA DEL VALLE", "EL MOLLAR - CONJUNTO DE CASA Y DEPA", "Alto la banda – cerro el pelao", "+5491132180810", "El Mollar"),

    # ═══════════════════════════ AMPIMPA ═════════════════════════════════════
    ("OBSERVATORIO DE AMPIMPA", "AMPIMPA - HOSTEL/HOSTAL", "Ruta 307 Km 107,5- Ampimpa", "3814027115", "Ampimpa"),

    # ═══════════════════════════ AMAICHA DEL VALLE ═══════════════════════════
    ("L'APACHETA", "AMAICHA DEL VALLE - HOSTEL/HOSTAL", "Hipólito Yrigoyen y Miguel Araoz", "3383601786", "Amaicha del Valle"),
    ("FINCA ALBARROSA", "AMAICHA DEL VALLE - ESTANCIA RURAL", "Ruta Nac. Nº 40 km", "3838 601786", "Amaicha del Valle"),

    # ═══════════════════════════ COLALAO DEL VALLE ═══════════════════════════
    ("RIO DE ARENA", "COLALAO DEL VALLE - ESTANCIA RURAL", "Ruta n 40 km 4295,5 (el bañado)", "3815870037", "Colalao del Valle"),
    ("DOÑA ROGELIA", "COLALAO DEL VALLE - HOSTEL/HOSTAL", "Ruta Nac. 40 (entrada)", "3815879440", "Colalao del Valle"),
    ("DE LAS VIÑAS", "COLALAO DEL VALLE - POSADA", "Ruta Nac. Nº 40 KM 4314", "3815879440", "Colalao del Valle"),

    # ═══════════════════════════ SAN PEDRO DE COLALAO ════════════════════════
    ("EL PORTAL DE SAN PEDRO", "SAN PEDRO DE COLALAO - POSADA", "24 de Septiembre esq. Tucuman", "03862 481467", "San Pedro de Colalao"),
    ("LAS TACANAS", "SAN PEDRO DE COLALAO - POSADA", "24 de Septiembre esq. Tucuman", "3816031130", "San Pedro de Colalao"),
    ("COMPLEJO LOS LEONES", "SAN PEDRO DE COLALAO - CONJ CASA/DEPTO", "Ruta 311 km 23", "3816292669", "San Pedro de Colalao"),
    ("DEL ABUELO", "SAN PEDRO DE COLALAO - CONJ CASA/DEPTO", "Ruta 311 km 23", "3816292669", "San Pedro de Colalao"),
    ("HOSTERIA EL LAPACHO", "SAN PEDRO DE COLALAO - HOSTERIA", "Ruta 311 km 24", "03812370022", "San Pedro de Colalao"),
    ("EL PARAISO", "SAN PEDRO DE COLALAO - HOSTERIA", "Las Heras 2da cuadra", "(03862) 481752", "San Pedro de Colalao"),
    ("AQUÍ ME QUEDO", "SAN PEDRO DE COLALAO - HOSTEL/HOSTAL", "Ruta 311 km 24,5", "3815249424", "San Pedro de Colalao"),
    ("INTIHUATANA", "SAN PEDRO DE COLALAO - HOSTEL/HOSTAL", "Calle Ayacucho y 27 s/n", "3816295949", "San Pedro de Colalao"),
    ("ATEP SAN PEDRO DE COLALAO", "SAN PEDRO DE COLALAO - HOSTEL/HOSTAL", "Calle 25 de mayo s/n", "03862 481105", "San Pedro de Colalao"),
    ("AMTARY", "SAN PEDRO DE COLALAO - HOSTEL/HOSTAL", "Calle Candelaria y Pje Crdena", "(03862) 481040", "San Pedro de Colalao"),
    ("FINCA CLUB DE CAMPO", "SAN PEDRO DE COLALAO - HOSTEL/HOSTAL", "Ruta 311 km 22", "3815634442", "San Pedro de Colalao"),
    ("HUAYCO", "SAN PEDRO DE COLALAO - HOSTEL/HOSTAL", "9 de julio 3ra cuadra", "03862 481040", "San Pedro de Colalao"),
    ("LA CAÑADA", "SAN PEDRO DE COLALAO - HOSTEL/HOSTAL", "Ruta 311 km 23", "3814471801", "San Pedro de Colalao"),
    ("LOS ARCOS", "SAN PEDRO DE COLALAO - HOSTEL/HOSTAL", "Las Heras 4ta cuadra", "3814023541", "San Pedro de Colalao"),
    ("LOS PARCOS", "SAN PEDRO DE COLALAO - HOSTEL/HOSTAL", "Congreso 3ra cuadra", "3814428559", "San Pedro de Colalao"),
    ("SANTA RITA", "SAN PEDRO DE COLALAO - HOSTEL/HOSTAL", "Pascual Contursi esq. Rio Tipa", "03862 481303", "San Pedro de Colalao"),
    ("VICTORIA", "SAN PEDRO DE COLALAO - HOSTEL/HOSTAL", "25 de mayo 3ra cuadra", "03862 481220", "San Pedro de Colalao"),
    ("NIEVA", "SAN PEDRO DE COLALAO - HOSTEL/HOSTAL", "Las Heras y 9 de Julio", "03862 481111", "San Pedro de Colalao"),
    ("NUESTRO SUEÑO", "SAN PEDRO DE COLALAO - HOSTEL/HOSTAL", "Barrio Villa Silvita 5ta entrada Malvinas", "3815563170", "San Pedro de Colalao"),
    ("COMPLEJO LOURDES", "SAN PEDRO DE COLALAO - HOSTEL/HOSTAL", "Calle Alejandro Heredia esq Pje. Luis Padilla Villa Rita", "3815035429", "San Pedro de Colalao"),
    ("INTI HUANA", "SAN PEDRO DE COLALAO - CABAÑA", "Calandria s/n", "03862 481382", "San Pedro de Colalao"),
    ("DEL RIO", "SAN PEDRO DE COLALAO - CABAÑA", "Av. Martín Belmonte s/n", "3815061074", "San Pedro de Colalao"),

    # ═══════════════════════════ TRANCAS ═════════════════════════════════════
    ("LOS SAUCES", "TRANCAS - HOSTEL/HOSTAL", "Ruta Nac. 9 km 1361", "3815267921", "Trancas"),

    # ═══════════════════════════ LULES ════════════════════════════════════════
    ("DIP", "LULES - HOSTEL/HOSTAL", "Miguel Lillo 300", "(0381) 4816945", "Lules"),
    ("NARCIZO", "LULES - CABAÑA", "Ruta Prov.321 intersección 301", "3815907067", "Lules"),

    # ═══════════════════════════ SIMOCA ═══════════════════════════════════════
    ("EL PORTAL DE SIMOCA", "SIMOCA - HOSTEL/HOSTAL", "9 de Julio 522", "03863 481347", "Simoca"),
    ("MI", "SIMOCA - HOSTEL/HOSTAL", "Gómez Llueca 1031", "3815600121", "Simoca"),
    ("HOSTAL DEL VALLE", "SIMOCA - HOSTEL/HOSTAL", "25 de May 0674", "03863 481990", "Simoca"),

    # ═══════════════════════════ MONTEROS ═════════════════════════════════════
    ("LAS HORTENSIAS", "MONTEROS - HOTEL 3*", "Sarmiento N°170", "3863400393", "Monteros"),
    ("EL TOJAR", "MONTEROS - POSADA", "Rivadavia N° 570", "3811557277", "Monteros"),

    # ═══════════════════════════ CONCEPCIÓN ═══════════════════════════════════
    ("EL MIRADOR DEL CENTRO", "CONCEPCION - HOTEL 1*", "Nassif Estefano 31", "03865 421055", "Concepción"),

    # ═══════════════════════════ AGUILARES ════════════════════════════════════
    ("LA CASONA", "AGUILARES - POSADA", "Sarmiento 960", "03865 481400", "Aguilares"),
    ("HOSTERIA MUNICIPAL", "AGUILARES - HOSTERIA", "Av. Independencia 951", "3816334160", "Aguilares"),
    ("LA MARMOL", "AGUILARES - HOSTEL/HOSTAL", "José Mármol 663", "3815624299", "Aguilares"),

    # ═══════════════════════════ ALBERDI ══════════════════════════════════════
    ("ESCABA", "ALBERDI - HOSTERIA 3*", "Ruta provincial N°308 - Escaba", "3817003000", "Alberdi"),
    ("ALBERDI", "ALBERDI - HOSTEL/HOSTAL", "Moreno 440", "03865 471378", "Alberdi"),
    ("SAN MARTIN", "ALBERDI - HOSTEL/HOSTAL", "San Martín 683", "03865 471532", "Alberdi"),

    # ═══════════════════════════ GRANEROS ═════════════════════════════════════
    ("TACO RALO", "GRANEROS - HOSTERIA", "Buenos Aires s/n", "3814426881", "Graneros"),
]


def seed_hoteles():
    """Inserta hoteles que no existan en la BD."""
    conn = db.obtener_conexion()
    if not conn:
        print("ERROR: No se pudo conectar a la base de datos.")
        return

    cursor = conn.cursor()
    insertados = 0
    existentes = 0

    try:
        for nombre, categoria, direccion, telefono, ciudad in HOTELES:
            # Verificar si ya existe (case-insensitive)
            cursor.execute(
                "SELECT id FROM hoteles WHERE LOWER(TRIM(nombre)) = LOWER(TRIM(%s))",
                (nombre,)
            )
            if cursor.fetchone():
                existentes += 1
                continue

            cursor.execute("""
                INSERT INTO hoteles (nombre, categoria, direccion, telefono, ciudad_localidad, activo)
                VALUES (%s, %s, %s, %s, %s, TRUE)
            """, (nombre, categoria, direccion, telefono, ciudad))
            insertados += 1

        conn.commit()
        print(f"\n✅ Carga completada:")
        print(f"   - Hoteles insertados: {insertados}")
        print(f"   - Ya existían:        {existentes}")
        print(f"   - Total en lista:     {len(HOTELES)}")

    except Exception as e:
        conn.rollback()
        print(f"\n❌ Error durante la carga: {e}")
    finally:
        cursor.close()
        db.liberar_conexion(conn)


if __name__ == "__main__":
    print("🏨 S.C.A.H. - Carga masiva de hoteles")
    print("=" * 45)
    seed_hoteles()
