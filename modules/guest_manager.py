"""
S.C.A.H. - Módulo de Gestión de Usuarios
ABM de usuarios del sistema (solo administradores)
"""

import customtkinter as ctk
import bcrypt

from database.connection import db
from ui.themes import COLORS, obtener_fuente
from ui.components import TablaScrollable, InputConLabel
from ui.dialogs import (mostrar_exito, mostrar_error, mostrar_advertencia,
                         confirmar, confirmar_eliminar)
from utils.validators import validar_texto_obligatorio, sanitizar_texto
from utils.logger import log_info, log_error, Auditoria
from auth.roles import tiene_permiso, listar_roles, obtener_nombre_rol
from config import ROLES


class UserManagementModule(ctk.CTkFrame):
    """Módulo para la gestión de usuarios del sistema (solo admin)."""

    def __init__(self, parent, usuario: dict):
        super().__init__(parent, fg_color="transparent")

        self.usuario = usuario
        self._crear_ui()
        self._cargar_usuarios()

    def _crear_ui(self):
        """Crea la interfaz de gestión de usuarios."""
        # Header
        header_card = ctk.CTkFrame(self, fg_color=COLORS["bg_card"], corner_radius=10)
        header_card.pack(fill="x", pady=(0, 10))

        header = ctk.CTkFrame(header_card, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=15)

        ctk.CTkLabel(
            header, text="👤 Gestión de Usuarios",
            font=obtener_fuente("heading"), anchor="w"
        ).pack(side="left")

        ctk.CTkButton(
            header, text="➕ Nuevo Usuario",
            font=obtener_fuente("small_bold"),
            height=36,
            fg_color=COLORS["success"],
            hover_color="#388E3C",
            command=self._formulario_nuevo
        ).pack(side="right")

        # Tabla
        table_card = ctk.CTkFrame(self, fg_color=COLORS["bg_card"], corner_radius=10)
        table_card.pack(fill="both", expand=True)

        self.tabla = TablaScrollable(
            table_card,
            columnas=[
                {"id": "id", "texto": "ID", "ancho": 50},
                {"id": "username", "texto": "Usuario", "ancho": 200},
                {"id": "nombre", "texto": "Nombre Completo", "ancho": 250},
                {"id": "rol", "texto": "Rol", "ancho": 150},
                {"id": "ultimo_acceso", "texto": "Último Acceso", "ancho": 180},
                {"id": "estado", "texto": "Estado", "ancho": 80},
            ],
            on_doble_click=self._editar_usuario,
            altura=15
        )
        self.tabla.pack(fill="both", expand=True, padx=20, pady=15)

        # Info
        self.label_info = ctk.CTkLabel(
            table_card, text="",
            font=obtener_fuente("small"),
            text_color=COLORS["text_secondary"]
        )
        self.label_info.pack(padx=20, pady=(0, 15))

    def _cargar_usuarios(self):
        """Carga la lista de usuarios desde la BD."""
        try:
            resultados = db.ejecutar_query(
                "SELECT * FROM usuarios ORDER BY username",
                fetch=True
            )

            if resultados:
                datos = []
                for r in resultados:
                    ultimo = ""
                    if r.get("ultimo_acceso"):
                        ultimo = r["ultimo_acceso"].strftime("%d/%m/%Y %H:%M")
                    datos.append({
                        "id": str(r["id"]),
                        "username": r["username"],
                        "nombre": r.get("nombre_completo", "") or "",
                        "rol": obtener_nombre_rol(r["rol"]),
                        "ultimo_acceso": ultimo,
                        "estado": "Activo" if r["activo"] else "Inactivo",
                    })
                self.tabla.cargar_datos(datos)
                self.label_info.configure(text=f"Total: {len(datos)} usuarios")
            else:
                self.tabla.limpiar()
                self.label_info.configure(text="No hay usuarios registrados")

        except Exception as e:
            log_error("Error al cargar usuarios", e)
            mostrar_error(self, "Error", f"Error al cargar usuarios: {str(e)}")

    def _formulario_nuevo(self):
        """Abre formulario para crear un nuevo usuario."""
        self._abrir_formulario_usuario()

    def _editar_usuario(self, datos: dict):
        """Abre formulario para editar un usuario."""
        user_id = int(datos["id"])
        user = db.ejecutar_query_one(
            "SELECT * FROM usuarios WHERE id = %s", (user_id,)
        )
        if user:
            self._abrir_formulario_usuario(user)

    def _abrir_formulario_usuario(self, user: dict = None):
        """Abre ventana de formulario para crear/editar usuario."""
        es_edicion = user is not None
        titulo = "Editar Usuario" if es_edicion else "Nuevo Usuario"

        ventana = ctk.CTkToplevel(self)
        ventana.title(titulo)
        ventana.geometry("480x520")
        ventana.resizable(False, False)
        ventana.grab_set()
        ventana.transient(self)

        ventana.update_idletasks()
        x = (ventana.winfo_screenwidth() // 2) - 240
        y = (ventana.winfo_screenheight() // 2) - 260
        ventana.geometry(f"480x520+{x}+{y}")

        frame = ctk.CTkFrame(ventana, fg_color="transparent")
        frame.pack(fill="both", expand=True, padx=25, pady=20)

        ctk.CTkLabel(
            frame, text=f"👤 {titulo}",
            font=obtener_fuente("subtitulo")
        ).pack(anchor="w", pady=(0, 20))

        # Campos
        inp_username = InputConLabel(frame, "Usuario", "Nombre de usuario", obligatorio=True)
        inp_username.pack(fill="x", pady=5)

        inp_nombre = InputConLabel(frame, "Nombre Completo", "Nombre y apellido")
        inp_nombre.pack(fill="x", pady=5)

        # Password
        if es_edicion:
            inp_pass = InputConLabel(frame, "Contraseña", "Dejar vacío para no cambiar")
        else:
            inp_pass = InputConLabel(frame, "Contraseña", "Contraseña del usuario", obligatorio=True)
        inp_pass.pack(fill="x", pady=5)
        inp_pass.entry.configure(show="*")

        # Rol
        rol_frame = ctk.CTkFrame(frame, fg_color="transparent")
        rol_frame.pack(fill="x", pady=5)
        ctk.CTkLabel(
            rol_frame, text="Rol *",
            font=obtener_fuente("small_bold")
        ).pack(anchor="w")

        roles_keys = list(ROLES.keys())
        roles_nombres = [obtener_nombre_rol(r) for r in roles_keys]

        combo_rol = ctk.CTkComboBox(
            rol_frame, values=roles_nombres,
            font=obtener_fuente("small"), height=36,
            state="readonly"
        )
        combo_rol.pack(fill="x", pady=(3, 0))
        combo_rol.set(roles_nombres[0])

        # Cargar datos si es edición
        if es_edicion:
            inp_username.set(user.get("username", ""))
            inp_nombre.set(user.get("nombre_completo", "") or "")
            if user.get("rol") in roles_keys:
                idx = roles_keys.index(user["rol"])
                combo_rol.set(roles_nombres[idx])

        # Botones
        btn_frame = ctk.CTkFrame(frame, fg_color="transparent")
        btn_frame.pack(fill="x", pady=(20, 0))

        def guardar():
            ok, msg = validar_texto_obligatorio(inp_username.get(), "Usuario")
            if not ok:
                inp_username.mostrar_error(msg)
                return

            if not es_edicion:
                if not inp_pass.get().strip():
                    inp_pass.mostrar_error("La contraseña es obligatoria")
                    return

            # Obtener rol key
            rol_idx = roles_nombres.index(combo_rol.get()) if combo_rol.get() in roles_nombres else 0
            rol_key = roles_keys[rol_idx]

            try:
                if es_edicion:
                    # Actualizar datos básicos
                    db.ejecutar_query("""
                        UPDATE usuarios SET username=%s, nombre_completo=%s, rol=%s
                        WHERE id=%s
                    """, (
                        sanitizar_texto(inp_username.get()),
                        sanitizar_texto(inp_nombre.get()),
                        rol_key,
                        user["id"]
                    ))

                    # Cambiar password si se proporcionó
                    if inp_pass.get().strip():
                        hashed = bcrypt.hashpw(
                            inp_pass.get().strip().encode("utf-8"),
                            bcrypt.gensalt()
                        ).decode("utf-8")
                        db.ejecutar_query(
                            "UPDATE usuarios SET password_hash=%s WHERE id=%s",
                            (hashed, user["id"])
                        )

                    log_info(f"Usuario actualizado: {inp_username.get()}")
                    Auditoria.registrar(
                        self.usuario["id"], "usuario_actualizado",
                        f"Usuario actualizado: {inp_username.get()}"
                    )
                else:
                    # Verificar que no exista
                    existe = db.ejecutar_query_one(
                        "SELECT id FROM usuarios WHERE username = %s",
                        (inp_username.get().strip(),)
                    )
                    if existe:
                        mostrar_error(ventana, "Error", "Ya existe un usuario con ese nombre")
                        return

                    hashed = bcrypt.hashpw(
                        inp_pass.get().strip().encode("utf-8"),
                        bcrypt.gensalt()
                    ).decode("utf-8")

                    db.ejecutar_query("""
                        INSERT INTO usuarios (username, password_hash, nombre_completo, rol)
                        VALUES (%s, %s, %s, %s)
                    """, (
                        sanitizar_texto(inp_username.get()),
                        hashed,
                        sanitizar_texto(inp_nombre.get()),
                        rol_key
                    ))

                    log_info(f"Usuario creado: {inp_username.get()}")
                    Auditoria.registrar(
                        self.usuario["id"], "usuario_creado",
                        f"Nuevo usuario: {inp_username.get()}"
                    )

                mostrar_exito(ventana, "Guardado", "Usuario guardado correctamente")
                ventana.destroy()
                self._cargar_usuarios()

            except Exception as e:
                log_error("Error al guardar usuario", e)
                mostrar_error(ventana, "Error", f"Error al guardar: {str(e)}")

        ctk.CTkButton(
            btn_frame, text="💾 Guardar",
            font=obtener_fuente("button"), height=40,
            fg_color=COLORS["success"], hover_color="#388E3C",
            command=guardar
        ).pack(side="right", padx=5)

        if es_edicion:
            def toggle_activo():
                if user["id"] == self.usuario["id"]:
                    mostrar_advertencia(ventana, "Aviso", "No puede desactivarse a sí mismo")
                    return
                if confirmar(ventana, "Cambiar estado",
                             f"¿Cambiar estado del usuario '{user['username']}'?"):
                    db.ejecutar_query(
                        "UPDATE usuarios SET activo = NOT activo WHERE id = %s",
                        (user["id"],)
                    )
                    ventana.destroy()
                    self._cargar_usuarios()

            ctk.CTkButton(
                btn_frame, text="⛔ Activar/Desactivar",
                font=obtener_fuente("small_bold"), height=40,
                fg_color=COLORS["warning"], hover_color="#E65100",
                command=toggle_activo
            ).pack(side="left", padx=5)

        ctk.CTkButton(
            btn_frame, text="Cancelar",
            font=obtener_fuente("button"), height=40,
            fg_color="gray30",
            command=ventana.destroy
        ).pack(side="right", padx=5)
