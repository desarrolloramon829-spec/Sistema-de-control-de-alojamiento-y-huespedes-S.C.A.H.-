"""
S.C.A.H. Web - Servicio de Autenticación
Encapsula la lógica de login, verificación de permisos y gestión de sesiones.
"""

import bcrypt
from datetime import datetime

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from database.connection import db
from utils.logger import log_info, log_error
from config import ROLES


def autenticar_usuario(username: str, password: str) -> dict | None:
    """
    Autentica un usuario con username y contraseña.
    Retorna dict del usuario si es correcto, None si falla.
    """
    try:
        resultado = db.ejecutar_query_one(
            "SELECT id, username, password_hash, nombre_completo, rol, activo "
            "FROM usuarios WHERE username = %s",
            (username,)
        )

        if not resultado:
            log_info(f"Login fallido: usuario '{username}' no encontrado")
            return None

        if not resultado["activo"]:
            log_info(f"Login con usuario inactivo: '{username}'")
            return None

        if bcrypt.checkpw(password.encode("utf-8"),
                          resultado["password_hash"].encode("utf-8")):
            db.ejecutar_query(
                "UPDATE usuarios SET ultimo_acceso = %s WHERE id = %s",
                (datetime.now(), resultado["id"])
            )
            log_info(f"Login exitoso: '{username}'")
            return {
                "id": resultado["id"],
                "username": resultado["username"],
                "nombre_completo": resultado["nombre_completo"],
                "rol": resultado["rol"],
            }
        else:
            log_info(f"Login fallido: contraseña incorrecta para '{username}'")
            return None

    except Exception as e:
        log_error(f"Error en autenticación de '{username}'", e)
        return None


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


def listar_roles() -> list:
    """Retorna la lista de roles disponibles."""
    return [
        {"clave": clave, "nombre": datos["nombre"], "descripcion": datos["descripcion"]}
        for clave, datos in ROLES.items()
    ]
