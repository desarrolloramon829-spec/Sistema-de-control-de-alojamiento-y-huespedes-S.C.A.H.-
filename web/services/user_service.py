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


def _registrar_auditoria(usuario_id: int, accion: str, registro_id: int = None,
                         detalle: str = None):
    """Registra auditoría usando una conexión dedicada del pool."""
    conn = None
    try:
        conn = db.obtener_conexion()
        if not conn:
            return

        auditoria = Auditoria(conn)
        auditoria.registrar(
            usuario_id,
            accion,
            "usuarios",
            registro_id=registro_id,
            detalle=detalle
        )
    except Exception as e:
        log_error(f"Error al registrar auditoría de usuarios: {accion}", e)
    finally:
        if conn:
            db.liberar_conexion(conn)


def _contar_admins_activos() -> int:
    """Retorna la cantidad de administradores activos."""
    try:
        resultado = db.ejecutar_query_one(
            "SELECT COUNT(*) AS total FROM usuarios WHERE rol = 'admin' AND activo = TRUE"
        )
        return int(resultado["total"]) if resultado else 0
    except Exception as e:
        log_error("Error al contar administradores activos", e)
        return 0


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

    if len(password.strip()) < 4:
        return False, "La contraseña debe tener al menos 4 caracteres"

    if rol not in ROLES:
        return False, "Rol inválido"

    try:
        username_limpio = sanitizar_texto(username)
        nombre_limpio = sanitizar_texto(nombre_completo)

        existe = db.ejecutar_query_one(
            "SELECT id FROM usuarios WHERE username = %s",
            (username_limpio,)
        )
        if existe:
            return False, "Ya existe un usuario con ese nombre"

        hashed = bcrypt.hashpw(
            password.strip().encode("utf-8"),
            bcrypt.gensalt()
        ).decode("utf-8")

        nuevo_usuario = db.ejecutar_query_one("""
            INSERT INTO usuarios (username, password_hash, nombre_completo, rol)
            VALUES (%s, %s, %s, %s)
            RETURNING id
        """, (
            username_limpio,
            hashed,
            nombre_limpio,
            rol
        ))

        if not nuevo_usuario:
            return False, "No se pudo crear el usuario"

        log_info(f"Usuario creado: {username_limpio}")
        _registrar_auditoria(
            admin_id,
            "usuario_creado",
            registro_id=nuevo_usuario["id"],
            detalle=f"Nuevo usuario: {username_limpio}"
        )
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
        usuario_actual = db.ejecutar_query_one(
            "SELECT id, username, rol, activo FROM usuarios WHERE id = %s",
            (user_id,)
        )
        if not usuario_actual:
            return False, "Usuario no encontrado"

        username_limpio = sanitizar_texto(username)
        nombre_limpio = sanitizar_texto(nombre_completo)

        existente = db.ejecutar_query_one(
            "SELECT id FROM usuarios WHERE username = %s AND id <> %s",
            (username_limpio, user_id)
        )
        if existente:
            return False, "Ya existe un usuario con ese nombre"

        if (usuario_actual["activo"] and usuario_actual["rol"] == "admin" and
                rol != "admin" and _contar_admins_activos() <= 1):
            return False, "No se puede quitar el rol al último administrador activo"

        if password and password.strip() and len(password.strip()) < 4:
            return False, "La contraseña debe tener al menos 4 caracteres"

        actualizados = db.ejecutar_query("""
            UPDATE usuarios SET username=%s, nombre_completo=%s, rol=%s
            WHERE id=%s
        """, (
            username_limpio,
            nombre_limpio,
            rol,
            user_id
        ))

        if actualizados is None:
            return False, "No se pudo actualizar el usuario"

        if password and password.strip():
            hashed = bcrypt.hashpw(
                password.strip().encode("utf-8"),
                bcrypt.gensalt()
            ).decode("utf-8")
            password_actualizada = db.ejecutar_query(
                "UPDATE usuarios SET password_hash=%s WHERE id=%s",
                (hashed, user_id)
            )
            if password_actualizada is None:
                return False, "No se pudo actualizar la contraseña"

        log_info(f"Usuario actualizado: {username_limpio}")
        if admin_id:
            _registrar_auditoria(
                admin_id,
                "usuario_actualizado",
                registro_id=user_id,
                detalle=f"Usuario actualizado: {username_limpio}"
            )
        return True, "Usuario actualizado correctamente"

    except Exception as e:
        log_error("Error al actualizar usuario", e)
        return False, f"Error al actualizar: {str(e)}"


def toggle_activo(user_id: int, admin_id: int) -> tuple[bool, str]:
    """Activa/desactiva un usuario."""
    if user_id == admin_id:
        return False, "No puede desactivarse a sí mismo"

    try:
        usuario = db.ejecutar_query_one(
            "SELECT id, username, rol, activo FROM usuarios WHERE id = %s",
            (user_id,)
        )
        if not usuario:
            return False, "Usuario no encontrado"

        if usuario["activo"] and usuario["rol"] == "admin" and _contar_admins_activos() <= 1:
            return False, "No se puede desactivar el último administrador activo"

        actualizados = db.ejecutar_query(
            "UPDATE usuarios SET activo = NOT activo WHERE id = %s",
            (user_id,)
        )

        if actualizados is None:
            return False, "No se pudo actualizar el estado del usuario"

        accion = "usuario_reactivado" if not usuario["activo"] else "usuario_desactivado"
        detalle = f"Usuario {'reactivado' if not usuario['activo'] else 'desactivado'}: {usuario['username']}"
        _registrar_auditoria(admin_id, accion, registro_id=user_id, detalle=detalle)
        return True, "Usuario reactivado correctamente" if not usuario["activo"] else "Usuario desactivado correctamente"
    except Exception as e:
        log_error(f"Error al cambiar estado de usuario {user_id}", e)
        return False, f"Error: {str(e)}"


def obtener_roles() -> list:
    """Retorna lista de roles disponibles con su nombre legible."""
    return [{"id": k, "nombre": obtener_nombre_rol(k)} for k in ROLES.keys()]
