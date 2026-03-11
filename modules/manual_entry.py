"""
S.C.A.H. - Módulo de Carga Manual de Huéspedes
Formulario con validación en tiempo real para registrar huéspedes manualmente
"""

import customtkinter as ctk
from datetime import date, datetime

from database.connection import db
from ui.themes import COLORS, obtener_fuente
from ui.components import InputConLabel
from ui.dialogs import mostrar_exito, mostrar_error, mostrar_advertencia
from utils.validators import (validar_dni, validar_fecha, validar_texto_obligatorio,
                               validar_edad, validar_fechas_estadia, calcular_edad,
                               sanitizar_texto, validar_telefono, validar_habitacion)
from utils.geography import (
    normalizar_campos_geograficos,
    obtener_sugerencias_nacionalidad,
    obtener_sugerencias_procedencia,
)
from utils.logger import log_info, log_error, Auditoria


class ManualEntryModule(ctk.CTkFrame):
    """Módulo para la carga manual de datos de huéspedes."""

    def __init__(self, parent, usuario: dict):
        super().__init__(parent, fg_color="transparent")

        self.usuario = usuario
        self.hoteles = []
        self.sugerencias_nacionalidad = obtener_sugerencias_nacionalidad()
        self.sugerencias_procedencia = obtener_sugerencias_procedencia()

        self._cargar_hoteles()
        self._crear_ui()

    def _cargar_hoteles(self):
        """Carga la lista de hoteles desde la BD."""
        try:
            resultado = db.ejecutar_query(
                "SELECT id, nombre, ciudad_localidad FROM hoteles WHERE activo = TRUE ORDER BY nombre",
                fetch=True
            )
            self.hoteles = resultado if resultado else []
        except Exception as e:
            log_error("Error al cargar hoteles", e)
            self.hoteles = []

    def _crear_ui(self):
        """Crea la interfaz del formulario de carga manual."""
        # Scroll frame
        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll.pack(fill="both", expand=True)

        # --- Card: Datos del Hotel ---
        hotel_card = ctk.CTkFrame(scroll, fg_color=COLORS["bg_card"], corner_radius=10)
        hotel_card.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(
            hotel_card, text="🏨 Datos del Hotel",
            font=obtener_fuente("heading"),
            anchor="w"
        ).pack(fill="x", padx=20, pady=(15, 10))

        form_hotel = ctk.CTkFrame(hotel_card, fg_color="transparent")
        form_hotel.pack(fill="x", padx=20, pady=(0, 15))

        # Hotel (combo)
        nombres_hoteles = [h["nombre"] for h in self.hoteles] if self.hoteles else []
        self.input_hotel = InputConLabel(
            form_hotel, "Hotel", "Seleccione o escriba el hotel",
            obligatorio=True, tipo="combo",
            values=[""] + nombres_hoteles
        )
        self.input_hotel.pack(fill="x", pady=3)

        # Opción nuevo hotel
        nuevo_frame = ctk.CTkFrame(form_hotel, fg_color="transparent")
        nuevo_frame.pack(fill="x", pady=3)

        self.check_nuevo = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            nuevo_frame, text="Registrar nuevo hotel",
            variable=self.check_nuevo,
            command=self._toggle_nuevo_hotel,
            font=obtener_fuente("small")
        ).pack(anchor="w")

        # Campos de nuevo hotel (ocultos por defecto)
        self.frame_nuevo_hotel = ctk.CTkFrame(form_hotel, fg_color="transparent")

        self.input_nro_orden = InputConLabel(
            self.frame_nuevo_hotel, "Nro. Orden", "Número de orden"
        )
        self.input_nro_orden.pack(fill="x", pady=3)

        self.input_direccion = InputConLabel(
            self.frame_nuevo_hotel, "Dirección", "Dirección del hotel"
        )
        self.input_direccion.pack(fill="x", pady=3)

        self.input_ciudad = InputConLabel(
            self.frame_nuevo_hotel, "Ciudad/Localidad", "Ciudad o localidad",
            obligatorio=True
        )
        self.input_ciudad.pack(fill="x", pady=3)

        # --- Card: Datos del Huésped ---
        huesped_card = ctk.CTkFrame(scroll, fg_color=COLORS["bg_card"], corner_radius=10)
        huesped_card.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(
            huesped_card, text="👤 Datos del Huésped",
            font=obtener_fuente("heading"),
            anchor="w"
        ).pack(fill="x", padx=20, pady=(15, 10))

        form_huesped = ctk.CTkFrame(huesped_card, fg_color="transparent")
        form_huesped.pack(fill="x", padx=20, pady=(0, 15))

        # Fila 1: Apellido y Nombre + DNI
        row1 = ctk.CTkFrame(form_huesped, fg_color="transparent")
        row1.pack(fill="x", pady=3)
        row1.grid_columnconfigure((0, 1), weight=1)

        self.input_nombre = InputConLabel(
            row1, "Apellido y Nombre", "Ej: PÉREZ, Juan",
            obligatorio=True
        )
        self.input_nombre.grid(row=0, column=0, sticky="ew", padx=(0, 10))

        self.input_dni = InputConLabel(
            row1, "DNI/Pasaporte", "Ej: 12345678",
            obligatorio=True
        )
        self.input_dni.grid(row=0, column=1, sticky="ew")

        # Fila 2: Nacionalidad + Procedencia
        row2 = ctk.CTkFrame(form_huesped, fg_color="transparent")
        row2.pack(fill="x", pady=3)
        row2.grid_columnconfigure((0, 1), weight=1)

        self.input_nacionalidad = InputConLabel(
            row2, "Nacionalidad", "Argentina", tipo="combo",
            values=self.sugerencias_nacionalidad
        )
        self.input_nacionalidad.grid(row=0, column=0, sticky="ew", padx=(0, 10))

        self.input_procedencia = InputConLabel(
            row2, "Procedencia", "Buenos Aires", tipo="combo",
            values=self.sugerencias_procedencia
        )
        self.input_procedencia.grid(row=0, column=1, sticky="ew")

        # Fila 3: Fecha Nac. + Edad + Profesión
        row3 = ctk.CTkFrame(form_huesped, fg_color="transparent")
        row3.pack(fill="x", pady=3)
        row3.grid_columnconfigure((0, 1, 2), weight=1)

        self.input_fecha_nac = InputConLabel(
            row3, "Fec. Nacimiento", "dd/mm/aaaa",
            tipo="date"
        )
        self.input_fecha_nac.grid(row=0, column=0, sticky="ew", padx=(0, 10))

        self.input_edad = InputConLabel(
            row3, "Edad", "Ej: 35"
        )
        self.input_edad.grid(row=0, column=1, sticky="ew", padx=(0, 10))

        self.input_profesion = InputConLabel(
            row3, "Profesión", "Ej: Ingeniero"
        )
        self.input_profesion.grid(row=0, column=2, sticky="ew")

        # Bind para auto-calcular edad
        self.input_fecha_nac.entry.bind("<FocusOut>", self._auto_calcular_edad)

        # --- Card: Datos de Estadía ---
        estadia_card = ctk.CTkFrame(scroll, fg_color=COLORS["bg_card"], corner_radius=10)
        estadia_card.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(
            estadia_card, text="📅 Datos de Estadía",
            font=obtener_fuente("heading"),
            anchor="w"
        ).pack(fill="x", padx=20, pady=(15, 10))

        form_estadia = ctk.CTkFrame(estadia_card, fg_color="transparent")
        form_estadia.pack(fill="x", padx=20, pady=(0, 15))

        row_estadia = ctk.CTkFrame(form_estadia, fg_color="transparent")
        row_estadia.pack(fill="x", pady=3)
        row_estadia.grid_columnconfigure((0, 1), weight=1)

        self.input_entrada = InputConLabel(
            row_estadia, "Fecha Entrada", "dd/mm/aaaa",
            tipo="date"
        )
        self.input_entrada.grid(row=0, column=0, sticky="ew", padx=(0, 10))

        self.input_salida = InputConLabel(
            row_estadia, "Fecha Salida", "dd/mm/aaaa",
            tipo="date"
        )
        self.input_salida.grid(row=0, column=1, sticky="ew")

        # --- Card: Datos Adicionales ---
        adicional_card = ctk.CTkFrame(scroll, fg_color=COLORS["bg_card"], corner_radius=10)
        adicional_card.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(
            adicional_card, text="🏠 Datos Adicionales",
            font=obtener_fuente("heading"),
            anchor="w"
        ).pack(fill="x", padx=20, pady=(15, 10))

        form_adicional = ctk.CTkFrame(adicional_card, fg_color="transparent")
        form_adicional.pack(fill="x", padx=20, pady=(0, 15))

        # Fila 1: Habitación + Teléfono
        row_adic1 = ctk.CTkFrame(form_adicional, fg_color="transparent")
        row_adic1.pack(fill="x", pady=3)
        row_adic1.grid_columnconfigure((0, 1), weight=1)

        self.input_habitacion = InputConLabel(
            row_adic1, "Habitación", "Ej: 205"
        )
        self.input_habitacion.grid(row=0, column=0, sticky="ew", padx=(0, 10))

        self.input_telefono = InputConLabel(
            row_adic1, "Teléfono", "Ej: 11 39106166"
        )
        self.input_telefono.grid(row=0, column=1, sticky="ew")

        # Fila 2: Domicilio
        self.input_domicilio = InputConLabel(
            form_adicional, "Domicilio", "Ej: GORRITI 420"
        )
        self.input_domicilio.pack(fill="x", pady=3)

        # Fila 3: Destino + Movilidad
        row_adic2 = ctk.CTkFrame(form_adicional, fg_color="transparent")
        row_adic2.pack(fill="x", pady=3)
        row_adic2.grid_columnconfigure((0, 1), weight=1)

        self.input_destino = InputConLabel(
            row_adic2, "Destino", "Ej: JUJUY"
        )
        self.input_destino.grid(row=0, column=0, sticky="ew", padx=(0, 10))

        self.input_movilidad = InputConLabel(
            row_adic2, "Movilidad", "SI / NO",
            tipo="combo", values=["", "SI", "NO"]
        )
        self.input_movilidad.grid(row=0, column=1, sticky="ew")

        # --- Mensaje de alerta duplicados ---
        self.label_alerta = ctk.CTkLabel(
            scroll, text="",
            font=obtener_fuente("small"),
            text_color=COLORS["warning"],
            anchor="w",
            wraplength=800
        )
        self.label_alerta.pack(fill="x", pady=(0, 5))

        # --- Botones de acción ---
        btn_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        btn_frame.pack(fill="x", pady=(5, 10))

        ctk.CTkButton(
            btn_frame, text="💾 Guardar",
            font=obtener_fuente("button"),
            height=42,
            fg_color=COLORS["success"],
            hover_color="#388E3C",
            command=self._guardar
        ).pack(side="right", padx=5)

        ctk.CTkButton(
            btn_frame, text="💾 Guardar y nuevo",
            font=obtener_fuente("button"),
            height=42,
            fg_color=COLORS["primary"],
            hover_color=COLORS["primary_hover"],
            command=self._guardar_y_nuevo
        ).pack(side="right", padx=5)

        ctk.CTkButton(
            btn_frame, text="🧹 Limpiar",
            font=obtener_fuente("button"),
            height=42,
            fg_color=COLORS["secondary"],
            hover_color=COLORS["secondary_hover"],
            command=self._limpiar_formulario
        ).pack(side="right", padx=5)

        # Bind para verificar duplicados al salir del campo DNI
        self.input_dni.entry.bind("<FocusOut>", self._verificar_duplicado)

    def _toggle_nuevo_hotel(self):
        """Muestra/oculta los campos de nuevo hotel."""
        if self.check_nuevo.get():
            self.frame_nuevo_hotel.pack(fill="x", pady=5)
            self.input_hotel.entry.configure(state="normal")
        else:
            self.frame_nuevo_hotel.pack_forget()

    def _auto_calcular_edad(self, event=None):
        """Calcula automáticamente la edad a partir de la fecha de nacimiento."""
        fecha_str = self.input_fecha_nac.get()
        if fecha_str:
            ok, _, fecha = validar_fecha(fecha_str, permite_vacio=True)
            if ok and fecha:
                edad = calcular_edad(fecha)
                if edad is not None:
                    self.input_edad.set(str(edad))

    def _verificar_duplicado(self, event=None):
        """Verifica si ya existe un huésped con el mismo DNI."""
        dni = self.input_dni.get()
        if not dni:
            self.label_alerta.configure(text="")
            return

        try:
            resultado = db.ejecutar_query(
                "SELECT h.apellido_nombre, ht.nombre as hotel "
                "FROM huespedes h JOIN hoteles ht ON h.hotel_id = ht.id "
                "WHERE h.dni_pasaporte = %s ORDER BY h.fecha_entrada DESC LIMIT 3",
                (dni.replace(".", "").replace("-", ""),),
                fetch=True
            )
            if resultado:
                registros = ", ".join(
                    [f"{r['apellido_nombre']} ({r['hotel']})" for r in resultado]
                )
                self.label_alerta.configure(
                    text=f"⚠️ DNI ya registrado: {registros}"
                )
            else:
                self.label_alerta.configure(text="")
        except Exception:
            pass

    def _validar_formulario(self) -> tuple[bool, list]:
        """Valida todos los campos del formulario. Retorna (ok, errores)."""
        errores = []

        # Limpiar errores anteriores
        for inp in [self.input_hotel, self.input_nombre, self.input_dni,
                     self.input_fecha_nac, self.input_edad,
                     self.input_entrada, self.input_salida,
                     self.input_habitacion, self.input_telefono]:
            inp.limpiar_error()

        # Hotel
        hotel = self.input_hotel.get()
        if not hotel:
            self.input_hotel.mostrar_error("Seleccione un hotel")
            errores.append("Hotel requerido")

        if self.check_nuevo.get():
            ok, msg = validar_texto_obligatorio(hotel, "Nombre del hotel")
            if not ok:
                self.input_hotel.mostrar_error(msg)
                errores.append(msg)

        # Apellido y Nombre
        ok, msg = validar_texto_obligatorio(self.input_nombre.get(), "Apellido y Nombre", min_len=3)
        if not ok:
            self.input_nombre.mostrar_error(msg)
            errores.append(msg)

        # DNI
        ok, msg = validar_dni(self.input_dni.get())
        if not ok:
            self.input_dni.mostrar_error(msg)
            errores.append(msg)

        # Fecha de nacimiento (opcional)
        if self.input_fecha_nac.get():
            ok, msg, _ = validar_fecha(self.input_fecha_nac.get(), permite_vacio=True)
            if not ok:
                self.input_fecha_nac.mostrar_error(msg)
                errores.append(msg)

        # Edad (opcional)
        if self.input_edad.get():
            ok, msg, _ = validar_edad(self.input_edad.get())
            if not ok:
                self.input_edad.mostrar_error(msg)
                errores.append(msg)

        # Fecha de entrada (opcional pero recomendada)
        fecha_entrada = None
        if self.input_entrada.get():
            ok, msg, fecha_entrada = validar_fecha(self.input_entrada.get(), permite_vacio=True)
            if not ok:
                self.input_entrada.mostrar_error(msg)
                errores.append(msg)

        # Fecha de salida (opcional)
        fecha_salida = None
        if self.input_salida.get():
            ok, msg, fecha_salida = validar_fecha(self.input_salida.get(), permite_vacio=True)
            if not ok:
                self.input_salida.mostrar_error(msg)
                errores.append(msg)

        # Validar coherencia entrada/salida
        if fecha_entrada and fecha_salida:
            ok, msg = validar_fechas_estadia(fecha_entrada, fecha_salida)
            if not ok:
                self.input_salida.mostrar_error(msg)
                errores.append(msg)

        # Habitación (opcional)
        if self.input_habitacion.get():
            ok, msg, _ = validar_habitacion(self.input_habitacion.get())
            if not ok:
                self.input_habitacion.mostrar_error(msg)
                errores.append(msg)

        # Teléfono (opcional)
        if self.input_telefono.get():
            ok, msg, _ = validar_telefono(self.input_telefono.get())
            if not ok:
                self.input_telefono.mostrar_error(msg)
                errores.append(msg)

        return len(errores) == 0, errores

    def _guardar(self):
        """Valida y guarda los datos en la base de datos."""
        ok, errores = self._validar_formulario()
        if not ok:
            mostrar_advertencia(self, "Errores de validación",
                                "Corrija los siguientes errores:\n\n• " + "\n• ".join(errores))
            return

        try:
            conn = db.obtener_conexion()
            if not conn:
                mostrar_error(self, "Error", "No se pudo conectar a la base de datos")
                return

            cursor = conn.cursor()

            # Obtener o crear hotel
            hotel_nombre = self.input_hotel.get()
            if self.check_nuevo.get():
                cursor.execute("""
                    INSERT INTO hoteles (nombre, nro_orden, direccion, ciudad_localidad, usuario_registro_id)
                    VALUES (%s, %s, %s, %s, %s) RETURNING id
                """, (
                    sanitizar_texto(hotel_nombre),
                    sanitizar_texto(self.input_nro_orden.get()),
                    sanitizar_texto(self.input_direccion.get()),
                    sanitizar_texto(self.input_ciudad.get()),
                    self.usuario["id"]
                ))
                hotel_id = cursor.fetchone()[0]
            else:
                cursor.execute("SELECT id FROM hoteles WHERE nombre = %s", (hotel_nombre,))
                result = cursor.fetchone()
                if not result:
                    mostrar_error(self, "Error", "Hotel no encontrado. Marque 'Registrar nuevo hotel'.")
                    db.liberar_conexion(conn)
                    return
                hotel_id = result[0]

            # Procesar fechas
            _, _, fecha_nac = validar_fecha(self.input_fecha_nac.get(), permite_vacio=True)
            _, _, fecha_entrada = validar_fecha(self.input_entrada.get(), permite_vacio=True)
            _, _, fecha_salida = validar_fecha(self.input_salida.get(), permite_vacio=True)
            _, _, edad = validar_edad(self.input_edad.get())
            nacionalidad, procedencia = normalizar_campos_geograficos(
                sanitizar_texto(self.input_nacionalidad.get()),
                sanitizar_texto(self.input_procedencia.get()),
            )

            # Insertar huésped
            cursor.execute("""
                INSERT INTO huespedes (
                    hotel_id, nacionalidad, procedencia, apellido_nombre,
                    dni_pasaporte, fecha_nacimiento, edad, profesion,
                    fecha_entrada, fecha_salida,
                    habitacion, domicilio, destino, movilidad, telefono,
                    origen_carga, usuario_carga_id
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'manual', %s)
                RETURNING id
            """, (
                hotel_id,
                nacionalidad,
                procedencia,
                sanitizar_texto(self.input_nombre.get()),
                sanitizar_texto(self.input_dni.get().replace(".", "").replace("-", "")),
                fecha_nac,
                edad,
                sanitizar_texto(self.input_profesion.get()),
                fecha_entrada,
                fecha_salida,
                sanitizar_texto(self.input_habitacion.get()),
                sanitizar_texto(self.input_domicilio.get()),
                sanitizar_texto(self.input_destino.get()),
                sanitizar_texto(self.input_movilidad.get()),
                sanitizar_texto(self.input_telefono.get()),
                self.usuario["id"]
            ))
            huesped_id = cursor.fetchone()[0]

            conn.commit()
            cursor.close()
            db.liberar_conexion(conn)

            # Auditoría
            try:
                conn_aud = db.obtener_conexion()
                if conn_aud:
                    Auditoria(conn_aud).registrar(
                        self.usuario["id"], "carga_manual", "huespedes",
                        registro_id=huesped_id,
                        detalle=f"Huésped: {self.input_nombre.get()}"
                    )
                    db.liberar_conexion(conn_aud)
            except Exception:
                pass

            log_info(f"Huésped registrado manualmente: {self.input_nombre.get()} (ID: {huesped_id})")
            mostrar_exito(self, "Registro exitoso",
                          f"Huésped '{self.input_nombre.get()}' registrado correctamente.")

            return True

        except Exception as e:
            log_error("Error al guardar huésped manual", e)
            mostrar_error(self, "Error", f"Error al guardar: {str(e)}")
            return False

    def _guardar_y_nuevo(self):
        """Guarda y limpia para un nuevo registro."""
        if self._guardar():
            self._limpiar_formulario(mantener_hotel=True)

    def _limpiar_formulario(self, mantener_hotel: bool = False):
        """Limpia todos los campos del formulario."""
        if not mantener_hotel:
            self.input_hotel.limpiar()
            self.input_nro_orden.limpiar()
            self.input_direccion.limpiar()
            self.input_ciudad.limpiar()
            self.check_nuevo.set(False)
            self.frame_nuevo_hotel.pack_forget()

        self.input_nombre.limpiar()
        self.input_dni.limpiar()
        self.input_nacionalidad.limpiar()
        self.input_procedencia.limpiar()
        self.input_fecha_nac.limpiar()
        self.input_edad.limpiar()
        self.input_profesion.limpiar()
        self.input_entrada.limpiar()
        self.input_salida.limpiar()
        self.input_habitacion.limpiar()
        self.input_domicilio.limpiar()
        self.input_destino.limpiar()
        self.input_movilidad.limpiar()
        self.input_telefono.limpiar()
        self.label_alerta.configure(text="")
