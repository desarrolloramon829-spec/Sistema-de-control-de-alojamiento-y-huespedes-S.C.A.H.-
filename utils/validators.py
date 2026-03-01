"""
S.C.A.H. - Validadores de datos
Funciones de validación para campos del sistema
"""

import re
from datetime import datetime, date
from config import DATE_FORMATS


def validar_dni(valor: str) -> tuple[bool, str]:
    """
    Valida un DNI argentino (7-8 dígitos) o pasaporte.
    Retorna (es_valido, mensaje_error).
    """
    if not valor or not valor.strip():
        return False, "DNI/Pasaporte es obligatorio"

    valor = valor.strip().replace(".", "").replace("-", "").replace(" ", "")

    # DNI argentino: 7(viejos)-8 dígitos
    if valor.isdigit():
        if 7 <= len(valor) <= 8:
            return True, ""
        else:
            return False, "El DNI debe tener entre 7 y 8 dígitos"

    # Pasaporte: letras y números, entre 5 y 15 caracteres
    if re.match(r'^[A-Za-z0-9]{5,15}$', valor):
        return True, ""

    return False, "Formato de DNI/Pasaporte inválido"


def validar_fecha(valor, permite_vacio: bool = False) -> tuple[bool, str, date | None]:
    """
    Valida una fecha en múltiples formatos.
    Retorna (es_valido, mensaje_error, fecha_parseada).
    """
    if not valor:
        if permite_vacio:
            return True, "", None
        return False, "La fecha es obligatoria", None

    # Si ya es un objeto date/datetime
    if isinstance(valor, datetime):
        return True, "", valor.date()
    if isinstance(valor, date):
        return True, "", valor

    valor_str = str(valor).strip()
    if not valor_str:
        if permite_vacio:
            return True, "", None
        return False, "La fecha es obligatoria", None

    for fmt in DATE_FORMATS:
        try:
            parsed = datetime.strptime(valor_str, fmt).date()
            return True, "", parsed
        except ValueError:
            continue

    return False, f"Formato de fecha inválido: '{valor_str}'. Use dd/mm/aaaa", None


def validar_texto_obligatorio(valor: str, nombre_campo: str, min_len: int = 1, max_len: int = 255) -> tuple[bool, str]:
    """Valida que un campo de texto no esté vacío y tenga longitud adecuada."""
    if not valor or not str(valor).strip():
        return False, f"{nombre_campo} es obligatorio"

    valor = str(valor).strip()
    if len(valor) < min_len:
        return False, f"{nombre_campo} debe tener al menos {min_len} caracteres"
    if len(valor) > max_len:
        return False, f"{nombre_campo} no debe exceder {max_len} caracteres"

    return True, ""


def validar_edad(valor) -> tuple[bool, str, int | None]:
    """Valida que la edad sea un número razonable."""
    if valor is None or str(valor).strip() == "":
        return True, "", None

    try:
        edad = int(float(str(valor)))
    except (ValueError, TypeError):
        return False, "La edad debe ser un número válido", None

    if edad < 0:
        return False, "La edad no puede ser negativa", None
    if edad > 150:
        return False, "La edad ingresada no es válida", None

    return True, "", edad


def validar_fechas_estadia(entrada, salida) -> tuple[bool, str]:
    """Valida que la fecha de salida sea posterior o igual a la de entrada."""
    if entrada is None or salida is None:
        return True, ""

    # Convertir a date si son datetime
    if isinstance(entrada, datetime):
        entrada = entrada.date()
    if isinstance(salida, datetime):
        salida = salida.date()

    if salida < entrada:
        return False, "La fecha de salida no puede ser anterior a la fecha de entrada"

    return True, ""


def sanitizar_texto(valor: str) -> str:
    """Limpia un texto: quita espacios extras, caracteres peligrosos."""
    if not valor:
        return ""
    # Quitar espacios múltiples y extremos
    texto = re.sub(r'\s+', ' ', str(valor)).strip()
    # Quitar caracteres potencialmente peligrosos para SQL (extra seguridad)
    texto = texto.replace("'", "'").replace('"', '"')
    return texto


def calcular_edad(fecha_nacimiento: date, fecha_referencia: date = None) -> int | None:
    """Calcula la edad a partir de la fecha de nacimiento."""
    if not fecha_nacimiento:
        return None

    if fecha_referencia is None:
        fecha_referencia = date.today()

    edad = fecha_referencia.year - fecha_nacimiento.year
    if (fecha_referencia.month, fecha_referencia.day) < (fecha_nacimiento.month, fecha_nacimiento.day):
        edad -= 1

    return edad
