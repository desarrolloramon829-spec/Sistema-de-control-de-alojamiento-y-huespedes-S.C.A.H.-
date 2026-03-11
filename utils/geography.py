"""
S.C.A.H. - Utilidades geográficas
Normalización de nacionalidad y procedencia para formularios, importaciones y estadísticas.
"""

import re
import unicodedata


VALORES_INVALIDOS = {
    '', 'asd', 'ninguna', 'nacionalidad', 'procedencia', 'n a', 'na', 'n d',
    's d', 'sd', 'sin dato', 'sin datos', 'no informa', 'no informado',
    'no especifica', 'sin especificar', 'null', 'none'
}

ARGENTINA_ALIASES = {
    'argentina', 'argentina republica', 'republica argentina', 'argentino',
    'arg', 'ar', 'argentina.', 'argentina republic', 'argento'
}

PROVINCIAS_ARGENTINAS = {
    'Buenos Aires': {'buenos aires', 'bs as', 'bs. as.', 'bsas', 'buenosaires', 'provincia de buenos aires', 'pba'},
    'CABA': {'caba', 'capital federal', 'ciudad autonoma de buenos aires', 'ciudad de buenos aires', 'capital', 'buenos aires capital'},
    'Catamarca': {'catamarca'},
    'Chaco': {'chaco'},
    'Chubut': {'chubut'},
    'Córdoba': {'cordoba', 'córdoba', 'cdoba'},
    'Corrientes': {'corrientes'},
    'Entre Ríos': {'entre rios', 'entre ríos'},
    'Formosa': {'formosa'},
    'Jujuy': {'jujuy'},
    'La Pampa': {'la pampa', 'lapampa'},
    'La Rioja': {'la rioja', 'larioja'},
    'Mendoza': {'mendoza'},
    'Misiones': {'misiones'},
    'Neuquén': {'neuquen', 'neuquén'},
    'Río Negro': {'rio negro', 'río negro'},
    'Salta': {'salta'},
    'San Juan': {'san juan', 'sanjuan', 's juan'},
    'San Luis': {'san luis', 'sanluis', 's luis'},
    'Santa Cruz': {'santa cruz', 'santacruz'},
    'Santa Fe': {'santa fe', 'santafe'},
    'Santiago del Estero': {'santiago del estero', 'santiagodelestero'},
    'Tierra del Fuego': {'tierra del fuego', 'tdf', 'tierra del fuego aiass'},
    'Tucumán': {'tucuman', 'tucumán', 'tuc'},
}

PAISES_RECONOCIDOS = {
    'Argentina': ARGENTINA_ALIASES | {'argentina'},
    'Alemania': {'alemania', 'germany'},
    'Australia': {'australia'},
    'Bélgica': {'belgica', 'bélgica', 'belgium'},
    'Bolivia': {'bolivia'},
    'Brasil': {'brasil', 'brazil'},
    'Canadá': {'canada', 'canadá'},
    'Chile': {'chile'},
    'China': {'china'},
    'Colombia': {'colombia'},
    'Costa Rica': {'costa rica'},
    'Estados Unidos': {'estados unidos', 'usa', 'eeuu', 'ee uu', 'ee. uu.', 'eeuu.', 'ee.uu.', 'united states'},
    'España': {'españa', 'espana', 'spain'},
    'Filipinas': {'filipinas', 'philippines'},
    'Francia': {'francia', 'france'},
    'Holanda': {'holanda', 'paises bajos', 'países bajos', 'netherlands'},
    'Italia': {'italia', 'italy'},
    'México': {'mexico', 'méxico'},
    'Paraguay': {'paraguay'},
    'Perú': {'peru', 'perú'},
    'Rusia': {'rusia', 'russia'},
    'Suiza': {'suiza', 'switzerland'},
    'Turquía': {'turquia', 'turquía', 'turkey'},
    'Uruguay': {'uruguay'},
    'Venezuela': {'venezuela', 'venenzuela'},
}

CONTINENTES = {
    'América del Sur': {'Argentina', 'Bolivia', 'Brasil', 'Chile', 'Colombia', 'Paraguay', 'Perú', 'Uruguay', 'Venezuela'},
    'América del Norte': {'Canadá', 'Estados Unidos', 'México'},
    'América Central y Caribe': {'Costa Rica'},
    'Europa': {'Alemania', 'Bélgica', 'España', 'Francia', 'Holanda', 'Italia', 'Rusia', 'Suiza', 'Turquía'},
    'Asia': {'China', 'Filipinas'},
    'África': set(),
    'Oceanía': {'Australia'},
}


def normalizar_texto_geo(valor: str) -> str:
    if not valor:
        return ''

    texto = unicodedata.normalize('NFKD', str(valor))
    texto = ''.join(ch for ch in texto if not unicodedata.combining(ch))
    texto = texto.lower()
    texto = re.sub(r'[^a-z0-9\s]', ' ', texto)
    texto = re.sub(r'\s+', ' ', texto).strip()
    return '' if texto in VALORES_INVALIDOS else texto


def _titulo_inteligente(valor: str) -> str:
    texto = re.sub(r'\s+', ' ', str(valor or '')).strip()
    return texto.title() if texto else ''


def normalizar_nacionalidad(valor: str) -> str:
    texto = normalizar_texto_geo(valor)
    if not texto:
        return ''

    for pais, aliases in PAISES_RECONOCIDOS.items():
        aliases_normalizados = {normalizar_texto_geo(alias) for alias in aliases}
        if texto == normalizar_texto_geo(pais) or texto in aliases_normalizados:
            return pais

    return _titulo_inteligente(valor)


def resolver_provincia(procedencia: str) -> str:
    procedencia_norm = normalizar_texto_geo(procedencia)
    if not procedencia_norm:
        return ''

    for provincia, aliases in PROVINCIAS_ARGENTINAS.items():
        aliases_normalizados = {normalizar_texto_geo(alias) for alias in aliases}
        if procedencia_norm == normalizar_texto_geo(provincia):
            return provincia
        if procedencia_norm in aliases_normalizados:
            return provincia
        if any(alias in procedencia_norm for alias in aliases_normalizados):
            return provincia

    return ''


def es_argentino(nacionalidad: str) -> bool:
    nacionalidad_norm = normalizar_texto_geo(nacionalidad)
    return bool(nacionalidad_norm) and (
        nacionalidad_norm in {normalizar_texto_geo(alias) for alias in ARGENTINA_ALIASES}
        or nacionalidad_norm.startswith('argentin')
    )


def normalizar_procedencia(valor: str, nacionalidad: str = '') -> str:
    texto = normalizar_texto_geo(valor)
    if not texto:
        return ''

    if es_argentino(nacionalidad):
        return resolver_provincia(valor) or _titulo_inteligente(valor)

    pais = normalizar_nacionalidad(valor)
    if pais:
        return pais

    provincia = resolver_provincia(valor)
    if provincia:
        return provincia

    return _titulo_inteligente(valor)


def resolver_continente(nacionalidad: str = '', procedencia: str = '') -> str:
    pais = normalizar_nacionalidad(procedencia) or normalizar_nacionalidad(nacionalidad)
    if not pais:
        return 'Continente no informado'

    for continente, paises in CONTINENTES.items():
        if pais in paises:
            return continente

    return 'Continente no reconocido'


def normalizar_campos_geograficos(nacionalidad: str, procedencia: str) -> tuple[str, str]:
    nacionalidad_norm = normalizar_nacionalidad(nacionalidad)
    procedencia_norm = normalizar_procedencia(procedencia, nacionalidad_norm)

    if not nacionalidad_norm and procedencia_norm:
        provincia = resolver_provincia(procedencia_norm)
        pais = normalizar_nacionalidad(procedencia_norm)
        if provincia:
            nacionalidad_norm = 'Argentina'
            procedencia_norm = provincia
        elif pais:
            nacionalidad_norm = pais
            procedencia_norm = pais

    if nacionalidad_norm == 'Argentina' and procedencia_norm:
        procedencia_norm = resolver_provincia(procedencia_norm) or procedencia_norm

    return nacionalidad_norm, procedencia_norm


def normalizar_huesped_geografia(huesped: dict) -> dict:
    copia = dict(huesped)
    nacionalidad, procedencia = normalizar_campos_geograficos(
        copia.get('nacionalidad', ''),
        copia.get('procedencia', ''),
    )
    copia['nacionalidad'] = nacionalidad
    copia['procedencia'] = procedencia
    return copia


def obtener_sugerencias_nacionalidad() -> list[str]:
    return [''] + sorted(PAISES_RECONOCIDOS.keys())


def obtener_sugerencias_procedencia() -> list[str]:
    items = list(PROVINCIAS_ARGENTINAS.keys()) + [pais for pais in PAISES_RECONOCIDOS.keys() if pais != 'Argentina']
    return [''] + sorted(items)


def normalizar_historico_huespedes(conn) -> dict:
    cursor = conn.cursor()
    cursor.execute('SELECT id, nacionalidad, procedencia FROM huespedes')
    filas = cursor.fetchall() or []

    actualizados = 0
    for huesped_id, nacionalidad, procedencia in filas:
        nacionalidad_norm, procedencia_norm = normalizar_campos_geograficos(nacionalidad or '', procedencia or '')
        if nacionalidad_norm != (nacionalidad or '') or procedencia_norm != (procedencia or ''):
            cursor.execute(
                'UPDATE huespedes SET nacionalidad = %s, procedencia = %s WHERE id = %s',
                (nacionalidad_norm, procedencia_norm, huesped_id),
            )
            actualizados += 1

    cursor.close()
    return {'total': len(filas), 'actualizados': actualizados}