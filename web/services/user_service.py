"""
S.C.A.H. Web - Servicio de Gestión de Usuarios
CRUD de usuarios del sistema.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import bcrypt
from database.connection import db
from utils.validators import validar_texto_obligatorio, sanitizar_texto
from utils.logger import log_info, log_error, Auditoria
from auth.roles import obtener_nombre_rol
from config import ROLES


def listar_usuarios() -> list:
    """Retorna lista de usuarios con info formateada."""
    try:
        resultados = db.ejecutar_query(
            "SELECT * FROM usuarios ORDER BY username",
            fetch=True
        )
        if not resultados:
            return []

        datos = []
        for r in resultados:
            ultimo = ""
            if r.get("ultimo_acceso"):
                ultimo = r["ultimo_acceso"].strftime("%d/%m/%Y %H:%M")
            datos.append({
                "id": r["id"],
                "username": r["username"],
                "nombre_completo": r.get("nombre_completo", "") or "",
                "rol": r["rol"],
                "rol_nombre": obtener_nombre_rol(r["rol"]),
                "ultimo_acceso": ultimo,
                "activo": r["activo"],
            })
        return datos
    except Exception as e:
        log_error("Error al cargar usuarios", e)
        return []


def obtener_usuario(user_id: int) -> dict | None:
    """Obtiene un usuario por ID."""
    try:
        user = db.ejecutar_query_one(
            "SELECT * FROM usuarios WHERE id = %s", (user_id,)
        )
        if user:
            return dict(user)
        return None
    except Exception as e:
        log_error(f"Error al obtener usuario {user_id}", e)
        return None


def crear_usuario(username: str, password: str, nombre_completo: str,
                  rol: str, admin_id: int) -> tuple[bool, str]:
    """
    Crea un nuevo usuario.
    Retorna (exito, mensaje).
    """
    ok, msg = validar_texto_obligatorio(username, "Usuario")
    if not ok:
        return False, msg

    if not password.strip():
        return False, "La contraseña es obligatoria"

    if rol not in ROLES:
        return False, "Rol inválido"

    try:
        existe = db.ejecutar_query_one(
            "SELECT id FROM usuarios WHERE username = %s",
            (username.strip(),)
        )
        if existe:
            return False, "Ya existe un usuario con ese nombre"

        hashed = bcrypt.hashpw(
            password.strip().encode("utf-8"),
            bcrypt.gensalt()
        ).decode("utf-8")

        db.ejecutar_query("""
            INSERT INTO usuarios (username, password_hash, nombre_completo, rol)
            VALUES (%s, %s, %s, %s)
        """, (
            sanitizar_texto(username),
            hashed,
            sanitizar_texto(nombre_completo),
            rol
        ))

        log_info(f"Usuario creado: {username}")
        Auditoria.registrar(admin_id, "usuario_creado", f"Nuevo usuario: {username}")
        return True, "Usuario creado correctamente"

    except Exception as e:
        log_error("Error al crear usuario", e)
        return False, f"Error al crear usuario: {str(e)}"


def actualizar_usuario(user_id: int, username: str, nombre_completo: str,
                       rol: str, password: str = None,
                       admin_id: int = None) -> tuple[bool, str]:
    """
    Actualiza un usuario existente.
    Si password es vacío/None, no se cambia.
    """
    ok, msg = validar_texto_obligatorio(username, "Usuario")
    if not ok:
        return False, msg

    if rol not in ROLES:
        return False, "Rol inválido"

    try:
        db.ejecutar_query("""
            UPDATE usuarios SET username=%s, nombre_completo=%s, rol=%s
            WHERE id=%s
        """, (
            sanitizar_texto(username),
            sanitizar_texto(nombre_completo),
            rol,
            user_id
        ))

        if password and password.strip():
            hashed = bcrypt.hashpw(
                password.strip().encode("utf-8"),
                bcrypt.gensalt()
            ).decode("utf-8")
            db.ejecutar_query(
                "UPDATE usuarios SET password_hash=%s WHERE id=%s",
                (hashed, user_id)
            )

        log_info(f"Usuario actualizado: {username}")
        if admin_id:
            Auditoria.registrar(admin_id, "usuario_actualizado",
                                f"Usuario actualizado: {username}")
        return True, "Usuario actualizado correctamente"

    except Exception as e:
        log_error("Error al actualizar usuario", e)
        return False, f"Error al actualizar: {str(e)}"


def toggle_activo(user_id: int, admin_id: int) -> tuple[bool, str]:
    """Activa/desactiva un usuario."""
    if user_id == admin_id:
        return False, "No puede desactivarse a sí mismo"

    try:
        db.ejecutar_query(
            "UPDATE usuarios SET activo = NOT activo WHERE id = %s",
            (user_id,)
        )
        return True, "Estado del usuario actualizado"
    except Exception as e:
        log_error(f"Error al cambiar estado de usuario {user_id}", e)
        return False, f"Error: {str(e)}"


def obtener_roles() -> list:
    """Retorna lista de roles disponibles con su nombre legible."""
    return [{"key": k, "nombre": obtener_nombre_rol(k)} for k in ROLES.keys()]
