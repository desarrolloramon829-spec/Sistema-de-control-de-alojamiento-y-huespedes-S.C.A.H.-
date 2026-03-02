"""
S.C.A.H. - Ventana principal de la aplicación
Sidebar con menú de navegación + panel de contenido dinámico
"""

import customtkinter as ctk
from ui.themes import COLORS, obtener_fuente
from auth.roles import tiene_permiso, obtener_nombre_rol


class MainWindow:
    """Ventana principal del sistema S.C.A.H."""

    def __init__(self, root, usuario: dict):
        self.root = root
        self.usuario = usuario
        self.modulo_actual = None
        self.modulos = {}

        # Configurar ventana principal
        from config import APP_NAME, APP_FULL_NAME, WINDOW_WIDTH, WINDOW_HEIGHT
        from config import WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT

        self.root.title(f"{APP_NAME} - {APP_FULL_NAME}")
        self.root.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.root.minsize(WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT)

        # Centrar
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth() // 2) - (WINDOW_WIDTH // 2)
        y = (self.root.winfo_screenheight() // 2) - (WINDOW_HEIGHT // 2)
        self.root.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}+{x}+{y}")

        self._crear_layout()
        self._crear_sidebar()
        self._crear_topbar()
        self._crear_panel_contenido()
        self._registrar_atajos()

        # Cargar módulo inicial (Dashboard)
        self.root.after(100, lambda: self._navegar("dashboard"))

    def _crear_layout(self):
        """Crea el layout principal: sidebar + area de contenido."""
        self.root.grid_columnconfigure(1, weight=1)
        self.root.grid_rowconfigure(1, weight=1)

        # Sidebar
        self.sidebar = ctk.CTkFrame(
            self.root,
            width=240,
            fg_color=COLORS["sidebar_bg"],
            corner_radius=0
        )
        self.sidebar.grid(row=0, column=0, rowspan=2, sticky="nsew")
        self.sidebar.grid_propagate(False)

        # Topbar
        self.topbar = ctk.CTkFrame(
            self.root,
            height=50,
            fg_color=COLORS["bg_medium"],
            corner_radius=0
        )
        self.topbar.grid(row=0, column=1, sticky="ew")
        self.topbar.grid_propagate(False)

        # Panel de contenido
        self.content_frame = ctk.CTkFrame(
            self.root,
            fg_color=COLORS["bg_dark"],
            corner_radius=0
        )
        self.content_frame.grid(row=1, column=1, sticky="nsew")

    def _crear_sidebar(self):
        """Crea el menú lateral de navegación."""
        # Logo / Título
        logo_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        logo_frame.pack(fill="x", padx=15, pady=(20, 5))

        ctk.CTkLabel(
            logo_frame, text="🏨 S.C.A.H.",
            font=obtener_fuente("subtitulo"),
            text_color=COLORS["primary_light"]
        ).pack(anchor="w")

        ctk.CTkLabel(
            logo_frame, text="Control de Alojamiento",
            font=obtener_fuente("tiny"),
            text_color=COLORS["text_muted"]
        ).pack(anchor="w")

        # Separador
        ctk.CTkFrame(
            self.sidebar, height=1,
            fg_color=COLORS["border"]
        ).pack(fill="x", padx=15, pady=15)

        # Menú de navegación
        self.menu_buttons = {}

        items_menu = [
            ("dashboard", "📊", "Dashboard", None),
            ("importar", "📥", "Importar Excel", "importar_excel"),
            ("importar_v2", "📋", "Importar Tabular", "importar_excel"),
            ("carga_manual", "✏️", "Carga Manual", "carga_manual"),
            ("busqueda", "🔍", "Búsqueda", "busqueda"),
            ("hoteles", "🏨", "Hoteles", "gestionar_hoteles"),
            ("estadisticas", "📈", "Estadísticas", "estadisticas"),
            ("reportes", "📄", "Reportes", "reportes"),
            ("usuarios", "👥", "Usuarios", "gestionar_usuarios"),
        ]

        for item_id, icono, texto, permiso in items_menu:
            # Verificar permiso
            if permiso and not tiene_permiso(self.usuario["rol"], permiso):
                continue

            btn = ctk.CTkButton(
                self.sidebar,
                text=f"  {icono}  {texto}",
                anchor="w",
                height=40,
                font=obtener_fuente("sidebar"),
                fg_color="transparent",
                text_color=COLORS["sidebar_text"],
                hover_color=COLORS["sidebar_hover"],
                command=lambda iid=item_id: self._navegar(iid)
            )
            btn.pack(fill="x", padx=10, pady=2)
            self.menu_buttons[item_id] = btn

        # Espacio flexible
        spacer = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        spacer.pack(fill="both", expand=True)

        # Separador inferior
        ctk.CTkFrame(
            self.sidebar, height=1,
            fg_color=COLORS["border"]
        ).pack(fill="x", padx=15, pady=5)

        # Botón cerrar sesión
        ctk.CTkButton(
            self.sidebar,
            text="  🚪  Cerrar Sesión",
            anchor="w",
            height=40,
            font=obtener_fuente("sidebar"),
            fg_color="transparent",
            text_color=COLORS["error_light"],
            hover_color=COLORS["sidebar_hover"],
            command=self._cerrar_sesion
        ).pack(fill="x", padx=10, pady=(2, 15))

    def _crear_topbar(self):
        """Crea la barra superior con info del usuario."""
        self.topbar.grid_columnconfigure(0, weight=1)

        # Título del módulo actual
        self.label_titulo_modulo = ctk.CTkLabel(
            self.topbar,
            text="Dashboard",
            font=obtener_fuente("heading"),
            text_color=COLORS["text_primary"],
            anchor="w"
        )
        self.label_titulo_modulo.grid(row=0, column=0, sticky="w", padx=20, pady=10)

        # Info del usuario
        user_frame = ctk.CTkFrame(self.topbar, fg_color="transparent")
        user_frame.grid(row=0, column=1, sticky="e", padx=20)

        rol_nombre = obtener_nombre_rol(self.usuario["rol"])
        ctk.CTkLabel(
            user_frame,
            text=f"👤 {self.usuario['nombre_completo']}",
            font=obtener_fuente("small_bold"),
            text_color=COLORS["text_primary"]
        ).pack(side="left", padx=(0, 10))

        ctk.CTkLabel(
            user_frame,
            text=f"[{rol_nombre}]",
            font=obtener_fuente("small"),
            text_color=COLORS["primary_light"]
        ).pack(side="left")

    def _crear_panel_contenido(self):
        """Prepara el panel de contenido dinámico."""
        self.content_frame.grid_columnconfigure(0, weight=1)
        self.content_frame.grid_rowconfigure(0, weight=1)

    def _navegar(self, modulo_id: str):
        """Navega a un módulo específico."""
        # Actualizar botón activo en sidebar
        for btn_id, btn in self.menu_buttons.items():
            if btn_id == modulo_id:
                btn.configure(fg_color=COLORS["sidebar_active"],
                              text_color=COLORS["primary_light"])
            else:
                btn.configure(fg_color="transparent",
                              text_color=COLORS["sidebar_text"])

        # Limpiar contenido actual
        for widget in self.content_frame.winfo_children():
            widget.destroy()

        # Títulos de módulos
        titulos = {
            "dashboard": "📊 Dashboard",
            "importar": "📥 Importar desde Excel",
            "importar_v2": "📋 Importar Formato Tabular",
            "carga_manual": "✏️ Carga Manual de Huéspedes",
            "busqueda": "🔍 Búsqueda de Huéspedes",
            "hoteles": "🏨 Gestión de Hoteles",
            "estadisticas": "📈 Estadísticas",
            "reportes": "📄 Reportes y Exportación",
            "usuarios": "👥 Gestión de Usuarios",
        }
        self.label_titulo_modulo.configure(
            text=titulos.get(modulo_id, modulo_id)
        )

        # Cargar módulo
        try:
            if modulo_id == "dashboard":
                from modules.statistics import DashboardModule
                modulo = DashboardModule(self.content_frame, self.usuario)
            elif modulo_id == "importar":
                from modules.import_excel import ImportExcelModule
                modulo = ImportExcelModule(self.content_frame, self.usuario)
            elif modulo_id == "importar_v2":
                from modules.import_excel_v2 import ImportExcelV2Module
                modulo = ImportExcelV2Module(self.content_frame, self.usuario)
            elif modulo_id == "carga_manual":
                from modules.manual_entry import ManualEntryModule
                modulo = ManualEntryModule(self.content_frame, self.usuario)
            elif modulo_id == "busqueda":
                from modules.search import SearchModule
                modulo = SearchModule(self.content_frame, self.usuario)
            elif modulo_id == "hoteles":
                from modules.hotel_manager import HotelManagerModule
                modulo = HotelManagerModule(self.content_frame, self.usuario)
            elif modulo_id == "estadisticas":
                from modules.statistics import StatisticsModule
                modulo = StatisticsModule(self.content_frame, self.usuario)
            elif modulo_id == "reportes":
                from modules.reports import ReportsModule
                modulo = ReportsModule(self.content_frame, self.usuario)
            elif modulo_id == "usuarios":
                from modules.guest_manager import UserManagementModule
                modulo = UserManagementModule(self.content_frame, self.usuario)

            modulo.pack(fill="both", expand=True, padx=15, pady=15)
            self.modulo_actual = modulo_id

        except Exception as e:
            from utils.logger import log_error
            log_error(f"Error al cargar módulo '{modulo_id}'", e)
            ctk.CTkLabel(
                self.content_frame,
                text=f"Error al cargar el módulo: {str(e)}",
                font=obtener_fuente("body"),
                text_color=COLORS["error"]
            ).pack(expand=True)

    def _registrar_atajos(self):
        """Registra atajos de teclado globales."""
        self.root.bind("<Control-n>", lambda e: self._navegar("carga_manual"))
        self.root.bind("<Control-f>", lambda e: self._navegar("busqueda"))
        self.root.bind("<Control-i>", lambda e: self._navegar("importar"))
        self.root.bind("<Control-d>", lambda e: self._navegar("dashboard"))
        self.root.bind("<Control-h>", lambda e: self._navegar("hoteles"))

    def _cerrar_sesion(self):
        """Cierra la sesión y vuelve al login."""
        from ui.dialogs import confirmar
        if confirmar(self.root, "Cerrar Sesión",
                     "¿Está seguro que desea cerrar la sesión?"):
            from utils.logger import log_info
            log_info(f"Sesión cerrada: {self.usuario['username']}")

            # Limpiar ventana
            for widget in self.root.winfo_children():
                widget.destroy()

            # Reconfigurar grid
            self.root.grid_columnconfigure(0, weight=0)
            self.root.grid_columnconfigure(1, weight=0)
            self.root.grid_rowconfigure(0, weight=0)
            self.root.grid_rowconfigure(1, weight=0)

            # Reabrir login
            self.root.withdraw()
            from auth.login_window import LoginWindow
            LoginWindow(self.root, lambda u: self._reiniciar_sesion(u))
            self.root.deiconify()

    def _reiniciar_sesion(self, usuario: dict):
        """Reinicia la sesión con un nuevo usuario."""
        self.usuario = usuario
        for widget in self.root.winfo_children():
            widget.destroy()
        self._crear_layout()
        self._crear_sidebar()
        self._crear_topbar()
        self._crear_panel_contenido()
        self._registrar_atajos()
        self.root.after(100, lambda: self._navegar("dashboard"))
