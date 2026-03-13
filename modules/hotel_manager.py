"""
S.C.A.H. - Módulo de Gestión de Hoteles
ABM de hoteles con listado, búsqueda y estadísticas por hotel
"""

import customtkinter as ctk

from database.connection import db
from ui.themes import COLORS, obtener_fuente
from ui.components import TablaScrollable, InputConLabel
from ui.dialogs import (mostrar_exito, mostrar_error, mostrar_advertencia,
                         confirmar, confirmar_eliminar)
from utils.validators import validar_texto_obligatorio, sanitizar_texto
from utils.logger import log_info, log_error, Auditoria
from auth.roles import tiene_permiso


class HotelManagerModule(ctk.CTkFrame):
    """Módulo para la gestión de hoteles (ABM)."""

    def __init__(self, parent, usuario: dict):
        super().__init__(parent, fg_color="transparent")

        self.usuario = usuario
        self._crear_ui()
        self._cargar_hoteles()

    def _crear_ui(self):
        """Crea la interfaz de gestión de hoteles."""
        # --- Header con búsqueda y botón nuevo ---
        header_card = ctk.CTkFrame(self, fg_color=COLORS["bg_card"], corner_radius=10)
        header_card.pack(fill="x", pady=(0, 10))

        header = ctk.CTkFrame(header_card, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=15)
        header.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            header, text="Lista de Hoteles",
            font=obtener_fuente("heading"), anchor="w"
        ).grid(row=0, column=0, sticky="w")

        # Búsqueda
        search_frame = ctk.CTkFrame(header, fg_color="transparent")
        search_frame.grid(row=0, column=1, sticky="e")

        self.entry_buscar = ctk.CTkEntry(
            search_frame, placeholder_text="Buscar hotel...",
            height=36, width=250, font=obtener_fuente("small")
        )
        self.entry_buscar.pack(side="left", padx=5)
        self.entry_buscar.bind("<Return>", lambda e: self._buscar_hoteles())

        ctk.CTkButton(
            search_frame, text="🔍", width=40, height=36,
            command=self._buscar_hoteles
        ).pack(side="left", padx=2)

        if tiene_permiso(self.usuario["rol"], "gestionar_hoteles"):
            ctk.CTkButton(
                search_frame, text="➕ Nuevo Hotel",
                font=obtener_fuente("small_bold"),
                height=36,
                fg_color=COLORS["success"],
                hover_color="#388E3C",
                command=self._formulario_nuevo
            ).pack(side="left", padx=(10, 0))

        # --- Tabla de hoteles ---
        table_card = ctk.CTkFrame(self, fg_color=COLORS["bg_card"], corner_radius=10)
        table_card.pack(fill="both", expand=True)

        self.tabla = TablaScrollable(
            table_card,
            columnas=[
                {"id": "id", "texto": "ID", "ancho": 50},
                {"id": "nombre", "texto": "Nombre del Hotel", "ancho": 200},
                {"id": "categoria", "texto": "Categoría", "ancho": 130},
                {"id": "direccion", "texto": "Dirección", "ancho": 200},
                {"id": "telefono", "texto": "Teléfono", "ancho": 150},
                {"id": "ciudad", "texto": "Ciudad/Localidad", "ancho": 150},
                {"id": "huespedes", "texto": "Huéspedes", "ancho": 80},
                {"id": "estado", "texto": "Estado", "ancho": 70},
            ],
            on_doble_click=self._editar_hotel,
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

    def _cargar_hoteles(self, filtro: str = None):
        """Carga la lista de hoteles desde la BD."""
        try:
            query = """
                SELECT h.id, h.nombre, h.categoria, h.nro_orden, h.direccion,
                       h.telefono, h.ciudad_localidad,
                       h.activo,
                       COUNT(hu.id) as total_huespedes
                FROM hoteles h
                LEFT JOIN huespedes hu ON h.id = hu.hotel_id
            """
            params = []

            if filtro:
                query += (" WHERE (h.nombre ILIKE %s OR h.ciudad_localidad ILIKE %s"
                          " OR h.direccion ILIKE %s OR h.categoria ILIKE %s"
                          " OR h.telefono ILIKE %s)")
                patron = f"%{filtro}%"
                params = [patron, patron, patron, patron, patron]

            query += " GROUP BY h.id ORDER BY h.nombre"

            resultados = db.ejecutar_query(query, tuple(params) if params else None, fetch=True)

            if resultados:
                datos = []
                for r in resultados:
                    datos.append({
                        "id": str(r["id"]),
                        "nombre": r["nombre"],
                        "categoria": r["categoria"] or "",
                        "direccion": r["direccion"] or "",
                        "telefono": r["telefono"] or "",
                        "ciudad": r["ciudad_localidad"] or "",
                        "huespedes": str(r["total_huespedes"]),
                        "estado": "Activo" if r["activo"] else "Inactivo",
                    })
                self.tabla.cargar_datos(datos)
                self.label_info.configure(text=f"Total: {len(datos)} hoteles registrados")
            else:
                self.tabla.limpiar()
                self.label_info.configure(text="No se encontraron hoteles")

        except Exception as e:
            log_error("Error al cargar hoteles", e)
            mostrar_error(self, "Error", f"Error al cargar hoteles: {str(e)}")

    def _buscar_hoteles(self):
        """Busca hoteles con el término ingresado."""
        self._cargar_hoteles(self.entry_buscar.get().strip() or None)

    def _formulario_nuevo(self):
        """Abre formulario para crear un nuevo hotel."""
        self._abrir_formulario_hotel()

    def _editar_hotel(self, datos: dict):
        """Abre formulario para editar un hotel existente."""
        if not tiene_permiso(self.usuario["rol"], "gestionar_hoteles"):
            return
        hotel_id = int(datos["id"])
        hotel = db.ejecutar_query_one(
            "SELECT * FROM hoteles WHERE id = %s", (hotel_id,)
        )
        if hotel:
            self._abrir_formulario_hotel(hotel)

    def _abrir_formulario_hotel(self, hotel: dict = None):
        """Abre la ventana de formulario para crear/editar hotel."""
        es_edicion = hotel is not None
        titulo = "Editar Hotel" if es_edicion else "Nuevo Hotel"

        ventana = ctk.CTkToplevel(self)
        ventana.title(titulo)
        ventana.geometry("500x520")
        ventana.resizable(False, False)
        ventana.grab_set()
        ventana.transient(self)

        # Centrar
        ventana.update_idletasks()
        x = (ventana.winfo_screenwidth() // 2) - 250
        y = (ventana.winfo_screenheight() // 2) - 260
        ventana.geometry(f"500x520+{x}+{y}")

        frame = ctk.CTkFrame(ventana, fg_color="transparent")
        frame.pack(fill="both", expand=True, padx=25, pady=20)

        ctk.CTkLabel(
            frame, text=f"🏨 {titulo}",
            font=obtener_fuente("subtitulo")
        ).pack(anchor="w", pady=(0, 20))

        # Campos
        inp_nombre = InputConLabel(frame, "Nombre", "Nombre del hotel", obligatorio=True)
        inp_nombre.pack(fill="x", pady=5)

        inp_categoria = InputConLabel(frame, "Categoría", "Ej: HOTEL 5*, HOSTEL, CABAÑA...")
        inp_categoria.pack(fill="x", pady=5)

        inp_orden = InputConLabel(frame, "Nro. Orden", "Número de orden")
        inp_orden.pack(fill="x", pady=5)

        inp_dir = InputConLabel(frame, "Dirección", "Dirección del hotel")
        inp_dir.pack(fill="x", pady=5)

        inp_telefono = InputConLabel(frame, "Teléfono", "Teléfono de contacto")
        inp_telefono.pack(fill="x", pady=5)

        inp_ciudad = InputConLabel(frame, "Ciudad", "Ciudad o localidad", obligatorio=True)
        inp_ciudad.pack(fill="x", pady=5)

        # Cargar datos si es edición
        if es_edicion:
            inp_nombre.set(hotel.get("nombre", ""))
            inp_categoria.set(hotel.get("categoria", "") or "")
            inp_orden.set(hotel.get("nro_orden", "") or "")
            inp_dir.set(hotel.get("direccion", "") or "")
            inp_telefono.set(hotel.get("telefono", "") or "")
            inp_ciudad.set(hotel.get("ciudad_localidad", "") or "")

        # Botones
        btn_frame = ctk.CTkFrame(frame, fg_color="transparent")
        btn_frame.pack(fill="x", pady=(20, 0))

        def guardar():
            # Validar
            ok1, msg1 = validar_texto_obligatorio(inp_nombre.get(), "Nombre")
            if not ok1:
                inp_nombre.mostrar_error(msg1)
                return

            try:
                if es_edicion:
                    db.ejecutar_query("""
                        UPDATE hoteles SET nombre=%s, categoria=%s, nro_orden=%s,
                        direccion=%s, telefono=%s, ciudad_localidad=%s
                        WHERE id=%s
                    """, (
                        sanitizar_texto(inp_nombre.get()),
                        sanitizar_texto(inp_categoria.get()),
                        sanitizar_texto(inp_orden.get()),
                        sanitizar_texto(inp_dir.get()),
                        sanitizar_texto(inp_telefono.get()),
                        sanitizar_texto(inp_ciudad.get()),
                        hotel["id"]
                    ))
                    log_info(f"Hotel actualizado: {inp_nombre.get()}")
                else:
                    db.ejecutar_query("""
                        INSERT INTO hoteles (nombre, categoria, nro_orden, direccion,
                        telefono, ciudad_localidad, usuario_registro_id)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """, (
                        sanitizar_texto(inp_nombre.get()),
                        sanitizar_texto(inp_categoria.get()),
                        sanitizar_texto(inp_orden.get()),
                        sanitizar_texto(inp_dir.get()),
                        sanitizar_texto(inp_telefono.get()),
                        sanitizar_texto(inp_ciudad.get()),
                        self.usuario["id"]
                    ))
                    log_info(f"Hotel creado: {inp_nombre.get()}")

                mostrar_exito(ventana, "Guardado", "Hotel guardado correctamente")
                ventana.destroy()
                self._cargar_hoteles()

            except Exception as e:
                log_error("Error al guardar hotel", e)
                mostrar_error(ventana, "Error", f"Error al guardar: {str(e)}")

        ctk.CTkButton(
            btn_frame, text="💾 Guardar",
            font=obtener_fuente("button"), height=40,
            fg_color=COLORS["success"], hover_color="#388E3C",
            command=guardar
        ).pack(side="right", padx=5)

        if es_edicion:
            def desactivar():
                if confirmar(ventana, "Desactivar hotel",
                             f"¿Desactivar '{hotel['nombre']}'?"):
                    db.ejecutar_query(
                        "UPDATE hoteles SET activo = NOT activo WHERE id = %s",
                        (hotel["id"],)
                    )
                    ventana.destroy()
                    self._cargar_hoteles()

            ctk.CTkButton(
                btn_frame, text="⛔ Activar/Desactivar",
                font=obtener_fuente("small_bold"), height=40,
                fg_color=COLORS["warning"], hover_color="#E65100",
                command=desactivar
            ).pack(side="left", padx=5)

        ctk.CTkButton(
            btn_frame, text="Cancelar",
            font=obtener_fuente("button"), height=40,
            fg_color="gray30",
            command=ventana.destroy
        ).pack(side="right", padx=5)
