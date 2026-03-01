"""
S.C.A.H. - Definición de roles y permisos
"""

from config import ROLES


def tiene_permiso(rol: str, permiso: str) -> bool:
    """Verifica si un rol tiene un permiso específico."""
    if rol not in ROLES:
        return False
    return permiso in ROLES[rol]["permisos"]


def obtener_permisos(rol: str) -> list:
    """Retorna la lista de permisos de un rol."""
    if rol not in ROLES:
        return []
    return ROLES[rol]["permisos"]


def obtener_nombre_rol(rol: str) -> str:
    """Retorna el nombre legible de un rol."""
    if rol not in ROLES:
        return "Desconocido"
    return ROLES[rol]["nombre"]


def obtener_descripcion_rol(rol: str) -> str:
    """Retorna la descripción de un rol."""
    if rol not in ROLES:
        return ""
    return ROLES[rol]["descripcion"]


def listar_roles() -> list:
    """Retorna la lista de roles disponibles."""
    return [
        {"clave": clave, "nombre": datos["nombre"], "descripcion": datos["descripcion"]}
        for clave, datos in ROLES.items()
    ]
