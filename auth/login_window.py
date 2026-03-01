"""
S.C.A.H. - Ventana de Login
Interfaz de autenticación con CustomTkinter
"""

import customtkinter as ctk
from auth.user_manager import UserManager
from utils.logger import log_info


class LoginWindow(ctk.CTkToplevel):
    """Ventana de inicio de sesión del sistema."""

    def __init__(self, parent, on_login_success):
        super().__init__(parent)

        self.on_login_success = on_login_success
        self.usuario_autenticado = None

        # Configurar ventana
        self.title("S.C.A.H. - Iniciar Sesión")
        self.geometry("450x520")
        self.resizable(False, False)
        self.grab_set()  # Modal

        # Centrar en pantalla
        self.update_idletasks()
        x = (self.winfo_screenwidth() // 2) - (450 // 2)
        y = (self.winfo_screenheight() // 2) - (520 // 2)
        self.geometry(f"450x520+{x}+{y}")

        # Evitar cerrar con X (debe loguearse o cerrar app)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        self._crear_widgets()

    def _crear_widgets(self):
        """Crea los widgets de la ventana de login."""
        # Frame principal
        main_frame = ctk.CTkFrame(self, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=40, pady=30)

        # Logo / Título
        titulo_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        titulo_frame.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(
            titulo_frame,
            text="🏨",
            font=ctk.CTkFont(size=60)
        ).pack()

        ctk.CTkLabel(
            titulo_frame,
            text="S.C.A.H.",
            font=ctk.CTkFont(size=32, weight="bold")
        ).pack()

        ctk.CTkLabel(
            titulo_frame,
            text="Sistema de Control de\nAlojamiento y Huéspedes",
            font=ctk.CTkFont(size=14),
            text_color="gray"
        ).pack(pady=(5, 0))

        # Separador
        ctk.CTkFrame(main_frame, height=2, fg_color="gray30").pack(fill="x", pady=20)

        # Formulario
        form_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        form_frame.pack(fill="x")

        # Usuario
        ctk.CTkLabel(
            form_frame, text="Usuario",
            font=ctk.CTkFont(size=14, weight="bold"),
            anchor="w"
        ).pack(fill="x", pady=(0, 5))

        self.entry_usuario = ctk.CTkEntry(
            form_frame,
            placeholder_text="Ingrese su usuario",
            height=40,
            font=ctk.CTkFont(size=14)
        )
        self.entry_usuario.pack(fill="x", pady=(0, 15))

        # Contraseña
        ctk.CTkLabel(
            form_frame, text="Contraseña",
            font=ctk.CTkFont(size=14, weight="bold"),
            anchor="w"
        ).pack(fill="x", pady=(0, 5))

        self.entry_password = ctk.CTkEntry(
            form_frame,
            placeholder_text="Ingrese su contraseña",
            show="●",
            height=40,
            font=ctk.CTkFont(size=14)
        )
        self.entry_password.pack(fill="x", pady=(0, 5))

        # Mostrar/ocultar contraseña
        self.show_pass_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            form_frame,
            text="Mostrar contraseña",
            variable=self.show_pass_var,
            command=self._toggle_password,
            font=ctk.CTkFont(size=12)
        ).pack(anchor="w", pady=(0, 20))

        # Mensaje de error
        self.label_error = ctk.CTkLabel(
            form_frame,
            text="",
            text_color="#FF6B6B",
            font=ctk.CTkFont(size=12),
            wraplength=350
        )
        self.label_error.pack(fill="x", pady=(0, 10))

        # Botón de login
        self.btn_login = ctk.CTkButton(
            form_frame,
            text="Iniciar Sesión",
            height=45,
            font=ctk.CTkFont(size=16, weight="bold"),
            command=self._intentar_login
        )
        self.btn_login.pack(fill="x")

        # Binds de teclado
        self.entry_usuario.bind("<Return>", lambda e: self.entry_password.focus_set())
        self.entry_password.bind("<Return>", lambda e: self._intentar_login())

        # Focus inicial
        self.after(100, lambda: self.entry_usuario.focus_set())

    def _toggle_password(self):
        """Alterna la visibilidad de la contraseña."""
        if self.show_pass_var.get():
            self.entry_password.configure(show="")
        else:
            self.entry_password.configure(show="●")

    def _intentar_login(self):
        """Intenta autenticar al usuario."""
        username = self.entry_usuario.get().strip()
        password = self.entry_password.get().strip()

        # Validaciones básicas
        if not username:
            self.label_error.configure(text="⚠ Ingrese su nombre de usuario")
            self.entry_usuario.focus_set()
            return

        if not password:
            self.label_error.configure(text="⚠ Ingrese su contraseña")
            self.entry_password.focus_set()
            return

        # Deshabilitar botón mientras autentica
        self.btn_login.configure(state="disabled", text="Verificando...")
        self.update()

        # Intentar autenticación
        usuario = UserManager.autenticar(username, password)

        if usuario:
            self.usuario_autenticado = usuario
            log_info(f"Login exitoso: {usuario['username']} ({usuario['rol']})")
            self.label_error.configure(text="")
            self.grab_release()
            self.on_login_success(usuario)
            self.destroy()
        else:
            self.label_error.configure(
                text="Usuario o contrasena incorrectos.\n"
                     "Verifique sus credenciales e intente nuevamente."
            )
            self.btn_login.configure(state="normal", text="Iniciar Sesión")
            self.entry_password.delete(0, "end")
            self.entry_password.focus_set()

    def _on_close(self):
        """Maneja el cierre de la ventana de login."""
        self.grab_release()
        self.destroy()
        # Cerrar toda la aplicacion
        self.master.destroy()
