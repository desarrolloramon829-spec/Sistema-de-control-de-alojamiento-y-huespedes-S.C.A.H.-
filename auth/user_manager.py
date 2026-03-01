"""
S.C.A.H. - Gestión de usuarios
CRUD completo de usuarios del sistema
"""

import bcrypt
from datetime import datetime
from database.connection import db
from utils.logger import log_info, log_error


class UserManager:
    """Gestiona las operaciones CRUD de usuarios."""

    @staticmethod
    def autenticar(username: str, password: str) -> dict | None:
        """
        Autentica un usuario con username y contraseña.
        Retorna el dict del usuario si es correcto, None si falla.
        """
        try:
            resultado = db.ejecutar_query_one(
                "SELECT id, username, password_hash, nombre_completo, rol, activo "
                "FROM usuarios WHERE username = %s",
                (username,)
            )

            if not resultado:
                log_info(f"Intento de login fallido: usuario '{username}' no encontrado")
                return None

            if not resultado["activo"]:
                log_info(f"Intento de login con usuario inactivo: '{username}'")
                return None

            # Verificar contraseña
            if bcrypt.checkpw(password.encode("utf-8"), resultado["password_hash"].encode("utf-8")):
                # Actualizar último acceso
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
                log_info(f"Intento de login fallido: contraseña incorrecta para '{username}'")
                return None

        except Exception as e:
            log_error(f"Error en autenticación de '{username}'", e)
            return None

    @staticmethod
    def crear_usuario(username: str, password: str, nombre_completo: str, rol: str) -> tuple[bool, str]:
        """Crea un nuevo usuario."""
        try:
            # Verificar que no exista
            existente = db.ejecutar_query_one(
                "SELECT id FROM usuarios WHERE username = %s", (username,)
            )
            if existente:
                return False, f"El usuario '{username}' ya existe"

            # Hashear contraseña
            password_hash = bcrypt.hashpw(
                password.encode("utf-8"), bcrypt.gensalt()
            ).decode("utf-8")

            db.ejecutar_query(
                "INSERT INTO usuarios (username, password_hash, nombre_completo, rol) "
                "VALUES (%s, %s, %s, %s)",
                (username, password_hash, nombre_completo, rol)
            )

            log_info(f"Usuario creado: '{username}' con rol '{rol}'")
            return True, "Usuario creado exitosamente"

        except Exception as e:
            log_error(f"Error al crear usuario '{username}'", e)
            return False, f"Error al crear usuario: {str(e)}"

    @staticmethod
    def actualizar_usuario(user_id: int, nombre_completo: str = None,
                           rol: str = None, activo: bool = None) -> tuple[bool, str]:
        """Actualiza datos de un usuario (sin contraseña)."""
        try:
            campos = []
            params = []

            if nombre_completo is not None:
                campos.append("nombre_completo = %s")
                params.append(nombre_completo)
            if rol is not None:
                campos.append("rol = %s")
                params.append(rol)
            if activo is not None:
                campos.append("activo = %s")
                params.append(activo)

            if not campos:
                return False, "No hay datos para actualizar"

            params.append(user_id)
            query = f"UPDATE usuarios SET {', '.join(campos)} WHERE id = %s"
            db.ejecutar_query(query, tuple(params))

            log_info(f"Usuario ID {user_id} actualizado")
            return True, "Usuario actualizado exitosamente"

        except Exception as e:
            log_error(f"Error al actualizar usuario ID {user_id}", e)
            return False, f"Error al actualizar: {str(e)}"

    @staticmethod
    def cambiar_password(user_id: int, nueva_password: str) -> tuple[bool, str]:
        """Cambia la contraseña de un usuario."""
        try:
            if len(nueva_password) < 4:
                return False, "La contraseña debe tener al menos 4 caracteres"

            password_hash = bcrypt.hashpw(
                nueva_password.encode("utf-8"), bcrypt.gensalt()
            ).decode("utf-8")

            db.ejecutar_query(
                "UPDATE usuarios SET password_hash = %s WHERE id = %s",
                (password_hash, user_id)
            )

            log_info(f"Contraseña cambiada para usuario ID {user_id}")
            return True, "Contraseña actualizada exitosamente"

        except Exception as e:
            log_error(f"Error al cambiar contraseña de usuario ID {user_id}", e)
            return False, f"Error al cambiar contraseña: {str(e)}"

    @staticmethod
    def listar_usuarios(incluir_inactivos: bool = False) -> list:
        """Lista todos los usuarios del sistema."""
        try:
            query = """
                SELECT id, username, nombre_completo, rol, activo, 
                       fecha_creacion, ultimo_acceso
                FROM usuarios
            """
            if not incluir_inactivos:
                query += " WHERE activo = TRUE"
            query += " ORDER BY nombre_completo"

            resultado = db.ejecutar_query(query, fetch=True)
            return resultado if resultado else []

        except Exception as e:
            log_error("Error al listar usuarios", e)
            return []

    @staticmethod
    def obtener_usuario(user_id: int) -> dict | None:
        """Obtiene un usuario por su ID."""
        try:
            return db.ejecutar_query_one(
                "SELECT id, username, nombre_completo, rol, activo, "
                "fecha_creacion, ultimo_acceso FROM usuarios WHERE id = %s",
                (user_id,)
            )
        except Exception as e:
            log_error(f"Error al obtener usuario ID {user_id}", e)
            return None

    @staticmethod
    def eliminar_usuario(user_id: int) -> tuple[bool, str]:
        """Desactiva (baja lógica) un usuario."""
        try:
            # No permitir desactivar el último admin
            admins = db.ejecutar_query(
                "SELECT id FROM usuarios WHERE rol = 'admin' AND activo = TRUE",
                fetch=True
            )
            usuario = db.ejecutar_query_one(
                "SELECT rol FROM usuarios WHERE id = %s", (user_id,)
            )

            if usuario and usuario["rol"] == "admin" and len(admins) <= 1:
                return False, "No se puede desactivar el último administrador"

            db.ejecutar_query(
                "UPDATE usuarios SET activo = FALSE WHERE id = %s", (user_id,)
            )

            log_info(f"Usuario ID {user_id} desactivado")
            return True, "Usuario desactivado exitosamente"

        except Exception as e:
            log_error(f"Error al desactivar usuario ID {user_id}", e)
            return False, f"Error al desactivar: {str(e)}"
