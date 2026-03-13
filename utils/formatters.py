"""
S.C.A.H. - Formateadores de datos
Funciones para formatear datos para presentación y almacenamiento
"""

from datetime import datetime, date
from config import DATE_DISPLAY_FORMAT


def formato_fecha(valor, formato: str = DATE_DISPLAY_FORMAT) -> str:
    """Convierte una fecha a string en el formato indicado."""
    if not valor:
        return ""
    if isinstance(valor, datetime):
        return valor.strftime(formato)
    if isinstance(valor, date):
        return valor.strftime(formato)
    return str(valor)


def formato_nombre(apellido_nombre: str) -> str:
    """Formatea un nombre: primera letra mayúscula de cada palabra."""
    if not apellido_nombre:
        return ""
    return " ".join(word.capitalize() for word in str(apellido_nombre).strip().split())


def formato_dni(dni: str) -> str:
    """Formatea un DNI argentino con puntos separadores."""
    if not dni:
        return ""
    dni_str = str(dni).strip()
    dni_numerico = dni_str.replace(".", "").replace("-", "").replace(" ", "")
    if dni_numerico.isdigit() and len(dni_numerico) >= 7:
        # Formato: XX.XXX.XXX
        if len(dni_numerico) == 8:
            return f"{dni_numerico[:2]}.{dni_numerico[2:5]}.{dni_numerico[5:]}"
        elif len(dni_numerico) == 7:
            return f"{dni_numerico[0]}.{dni_numerico[1:4]}.{dni_numerico[4:]}"
    return dni_str


def formato_edad(edad) -> str:
    """Formatea la edad como texto."""
    if edad is None or str(edad).strip() == "":
        return ""
    try:
        return str(int(float(str(edad))))
    except (ValueError, TypeError):
        return ""


def truncar_texto(texto: str, max_len: int = 30) -> str:
    """Trunca un texto largo añadiendo '...' al final."""
    if not texto:
        return ""
    texto = str(texto).strip()
    if len(texto) <= max_len:
        return texto
    return texto[:max_len - 3] + "..."


def formato_numero(numero: int) -> str:
    """Formatea un número con separador de miles."""
    if numero is None:
        return "0"
    return f"{int(numero):,}".replace(",", ".")


def formato_timestamp(dt: datetime = None) -> str:
    """Retorna un timestamp formateado para logs y reportes."""
    if dt is None:
        dt = datetime.now()
    return dt.strftime("%d/%m/%Y %H:%M:%S")


def formato_nombre_archivo(base: str, extension: str = "xlsx") -> str:
    """Genera un nombre de archivo con timestamp."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_limpio = "".join(c for c in base if c.isalnum() or c in (' ', '-', '_')).strip()
    base_limpio = base_limpio.replace(' ', '_')
    return f"{base_limpio}_{timestamp}.{extension}"
