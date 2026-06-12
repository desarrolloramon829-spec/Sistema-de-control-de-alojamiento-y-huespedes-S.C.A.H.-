"""
S.C.A.H. - Módulo de Búsqueda de Huéspedes
Búsqueda general y avanzada con filtros combinables
"""

import customtkinter as ctk
import threading
from datetime import datetime

from database.connection import db
from ui.themes import COLORS, obtener_fuente
from ui.components import TablaScrollable, InputConLabel, Paginador
from ui.dialogs import mostrar_info, mostrar_advertencia, confirmar_eliminar, mostrar_exito, mostrar_error
from utils.formatters import formato_fecha, formato_dni
from utils.logger import log_info
from config import DEFAULT_PAGE_SIZE


class SearchModule(ctk.CTkFrame):
    """Módulo de búsqueda general y avanzada de huéspedes."""

    def __init__(self, parent, usuario: dict):
        super().__init__(parent, fg_color="transparent")

        self.usuario = usuario
        self.resultados = []
        self.modo_avanzado = False

        self._crear_ui()

    def _crear_ui(self):
        """Crea la interfaz del módulo de búsqueda."""
        # --- Búsqueda rápida ---
        search_card = ctk.CTkFrame(self, fg_color=COLORS["bg_card"], corner_radius=10)
        search_card.pack(fill="x", pady=(0, 10))

        quick_frame = ctk.CTkFrame(search_card, fg_color="transparent")
        quick_frame.pack(fill="x", padx=20, pady=15)
        quick_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            quick_frame, text="🔍",
            font=ctk.CTkFont(size=24)
        ).grid(row=0, column=0, padx=(0, 10))

        self.entry_busqueda = ctk.CTkEntry(
            quick_frame,
            placeholder_text="Buscar por nombre, DNI, hotel, ciudad, nacionalidad...",
            height=42,
            font=obtener_fuente("body")
        )
        self.entry_busqueda.grid(row=0, column=1, sticky="ew", padx=(0, 10))
        self.entry_busqueda.bind("<Return>", lambda e: self._buscar_rapida())

        ctk.CTkButton(
            quick_frame, text="Buscar",
            font=obtener_fuente("button"),
            height=42, width=100,
            command=self._buscar_rapida
        ).grid(row=0, column=2, padx=(0, 5))

        self.btn_avanzada = ctk.CTkButton(
            quick_frame, text="▼ Avanzada",
            font=obtener_fuente("small_bold"),
            height=42, width=110,
            fg_color=COLORS["secondary"],
            hover_color=COLORS["secondary_hover"],
            command=self._toggle_avanzada
        )
        self.btn_avanzada.grid(row=0, column=3)

        # --- Filtros avanzados (ocultos por defecto) ---
        self.frame_avanzada = ctk.CTkFrame(search_card, fg_color=COLORS["bg_light"], corner_radius=8)

        filtros_inner = ctk.CTkFrame(self.frame_avanzada, fg_color="transparent")
        filtros_inner.pack(fill="x", padx=15, pady=15)

        # Fila 1: Hotel + Ciudad + Nacionalidad
        row1 = ctk.CTkFrame(filtros_inner, fg_color="transparent")
        row1.pack(fill="x", pady=3)
        row1.grid_columnconfigure((0, 1, 2), weight=1)

        self.filtro_hotel = InputConLabel(row1, "Hotel", "Todos los hoteles",
                                          tipo="combo", values=self._obtener_hoteles())
        self.filtro_hotel.grid(row=0, column=0, sticky="ew", padx=(0, 10))

        self.filtro_ciudad = InputConLabel(row1, "Ciudad", "Todas las ciudades",
                                           tipo="combo", values=self._obtener_ciudades())
        self.filtro_ciudad.grid(row=0, column=1, sticky="ew", padx=(0, 10))

        self.filtro_nacionalidad = InputConLabel(row1, "Nacionalidad", "Ej: Argentina")
        self.filtro_nacionalidad.grid(row=0, column=2, sticky="ew")

        # Fila 2: DNI + Profesión + Procedencia
        row2 = ctk.CTkFrame(filtros_inner, fg_color="transparent")
        row2.pack(fill="x", pady=3)
        row2.grid_columnconfigure((0, 1, 2), weight=1)

        self.filtro_dni = InputConLabel(row2, "DNI/Pasaporte", "Búsqueda parcial")
        self.filtro_dni.grid(row=0, column=0, sticky="ew", padx=(0, 10))

        self.filtro_profesion = InputConLabel(row2, "Profesión", "Ej: Ingeniero")
        self.filtro_profesion.grid(row=0, column=1, sticky="ew", padx=(0, 10))

        self.filtro_procedencia = InputConLabel(row2, "Procedencia", "Ej: Buenos Aires")
        self.filtro_procedencia.grid(row=0, column=2, sticky="ew")

        # Fila 3: Fechas + Edad
        row3 = ctk.CTkFrame(filtros_inner, fg_color="transparent")
        row3.pack(fill="x", pady=3)
        row3.grid_columnconfigure((0, 1, 2, 3), weight=1)

        self.filtro_fecha_desde = InputConLabel(row3, "Entrada desde", "dd/mm/aaaa", tipo="date")
        self.filtro_fecha_desde.grid(row=0, column=0, sticky="ew", padx=(0, 10))

        self.filtro_fecha_hasta = InputConLabel(row3, "Entrada hasta", "dd/mm/aaaa", tipo="date")
        self.filtro_fecha_hasta.grid(row=0, column=1, sticky="ew", padx=(0, 10))

        self.filtro_edad_min = InputConLabel(row3, "Edad mín.", "Ej: 18")
        self.filtro_edad_min.grid(row=0, column=2, sticky="ew", padx=(0, 10))

        self.filtro_edad_max = InputConLabel(row3, "Edad máx.", "Ej: 65")
        self.filtro_edad_max.grid(row=0, column=3, sticky="ew")

        # Fila 4: Habitación + Destino + Teléfono
        row4 = ctk.CTkFrame(filtros_inner, fg_color="transparent")
        row4.pack(fill="x", pady=3)
        row4.grid_columnconfigure((0, 1, 2), weight=1)

        self.filtro_habitacion = InputConLabel(row4, "Habitación", "Ej: 205")
        self.filtro_habitacion.grid(row=0, column=0, sticky="ew", padx=(0, 10))

        self.filtro_destino = InputConLabel(row4, "Destino", "Ej: Jujuy")
        self.filtro_destino.grid(row=0, column=1, sticky="ew", padx=(0, 10))

        self.filtro_telefono = InputConLabel(row4, "Teléfono", "Búsqueda parcial")
        self.filtro_telefono.grid(row=0, column=2, sticky="ew")

        # Botones de filtro
        filtro_btn_frame = ctk.CTkFrame(filtros_inner, fg_color="transparent")
        filtro_btn_frame.pack(fill="x", pady=(10, 0))

        ctk.CTkButton(
            filtro_btn_frame, text="🔍 Buscar con filtros",
            font=obtener_fuente("button"), height=38,
            command=self._buscar_avanzada
        ).pack(side="right", padx=5)

        ctk.CTkButton(
            filtro_btn_frame, text="🧹 Limpiar filtros",
            font=obtener_fuente("small_bold"), height=38,
            fg_color=COLORS["secondary"],
            hover_color=COLORS["secondary_hover"],
            command=self._limpiar_filtros
        ).pack(side="right", padx=5)

        # --- Tabla de resultados ---
        results_card = ctk.CTkFrame(self, fg_color=COLORS["bg_card"], corner_radius=10)
        results_card.pack(fill="both", expand=True, pady=(0, 10))

        # Header de resultados
        res_header = ctk.CTkFrame(results_card, fg_color="transparent")
        res_header.pack(fill="x", padx=20, pady=(15, 5))

        self.label_resultados = ctk.CTkLabel(
            res_header, text="Resultados de búsqueda",
            font=obtener_fuente("heading"), anchor="w"
        )
        self.label_resultados.pack(side="left")

        # Botones de acción sobre resultados
        action_frame = ctk.CTkFrame(res_header, fg_color="transparent")
        action_frame.pack(side="right")

        ctk.CTkButton(
            action_frame, text="📥 Exportar Excel",
            font=obtener_fuente("small_bold"), height=32, width=130,
            fg_color=COLORS["success"],
            hover_color="#388E3C",
            command=self._exportar_resultados
        ).pack(side="left", padx=3)

        # Tabla
        self.tabla = TablaScrollable(
            results_card,
            columnas=[
                {"id": "id", "texto": "ID", "ancho": 50},
                {"id": "hotel", "texto": "Hotel", "ancho": 140},
                {"id": "apellido_nombre", "texto": "Apellido y Nombre", "ancho": 170},
                {"id": "dni_pasaporte", "texto": "DNI/Pasaporte", "ancho": 100},
                {"id": "nacionalidad", "texto": "Nacionalidad", "ancho": 90},
                {"id": "procedencia", "texto": "Procedencia", "ancho": 100},
                {"id": "edad", "texto": "Edad", "ancho": 50},
                {"id": "profesion", "texto": "Profesión", "ancho": 100},
                {"id": "fecha_entrada", "texto": "Entrada", "ancho": 90},
                {"id": "fecha_salida", "texto": "Salida", "ancho": 90},
                {"id": "habitacion", "texto": "Hab.", "ancho": 50},
                {"id": "telefono", "texto": "Teléfono", "ancho": 95},
                {"id": "origen", "texto": "Origen", "ancho": 65},
            ],
            on_doble_click=self._ver_detalle,
            altura=14
        )
        self.tabla.pack(fill="both", expand=True, padx=20, pady=(0, 10))

        # Paginador
        self.paginador = Paginador(
            results_card,
            on_cambio_pagina=self._cambiar_pagina,
            registros_por_pagina=DEFAULT_PAGE_SIZE
        )
        self.paginador.pack(fill="x", padx=20, pady=(0, 15))

        # Estado de búsqueda actual
        self._query_actual = ""
        self._params_actuales = []

    def _toggle_avanzada(self):
        """Muestra/oculta los filtros avanzados."""
        if self.modo_avanzado:
            self.frame_avanzada.pack_forget()
            self.btn_avanzada.configure(text="▼ Avanzada")
        else:
            self.frame_avanzada.pack(fill="x", padx=20, pady=(0, 15))
            self.btn_avanzada.configure(text="▲ Ocultar")
        self.modo_avanzado = not self.modo_avanzado

    def _obtener_hoteles(self) -> list:
        """Obtiene lista de hoteles para el combo."""
        try:
            result = db.ejecutar_query(
                "SELECT DISTINCT nombre FROM hoteles WHERE activo = TRUE ORDER BY nombre",
                fetch=True
            )
            return [""] + [r["nombre"] for r in result] if result else [""]
        except Exception:
            return [""]

    def _obtener_ciudades(self) -> list:
        """Obtiene lista de ciudades para el combo."""
        try:
            result = db.ejecutar_query(
                "SELECT DISTINCT ciudad_localidad FROM hoteles "
                "WHERE ciudad_localidad IS NOT NULL AND ciudad_localidad != '' ORDER BY ciudad_localidad",
                fetch=True
            )
            return [""] + [r["ciudad_localidad"] for r in result] if result else [""]
        except Exception:
            return [""]

    def _buscar_rapida(self):
        """Ejecuta búsqueda rápida en todos los campos."""
        termino = self.entry_busqueda.get().strip()
        if not termino:
            mostrar_advertencia(self, "Búsqueda", "Ingrese un término de búsqueda")
            return

        patron = f"%{termino}%"
        query = """
            SELECT h.id, ht.nombre as hotel, h.apellido_nombre, h.dni_pasaporte,
                   h.nacionalidad, h.procedencia, h.edad, h.profesion,
                   h.fecha_entrada, h.fecha_salida, h.habitacion, h.telefono,
                   h.domicilio, h.destino, h.movilidad, h.origen_carga
            FROM huespedes h
            JOIN hoteles ht ON h.hotel_id = ht.id
            WHERE h.apellido_nombre ILIKE %s
               OR h.dni_pasaporte ILIKE %s
               OR ht.nombre ILIKE %s
               OR ht.ciudad_localidad ILIKE %s
               OR h.nacionalidad ILIKE %s
               OR h.procedencia ILIKE %s
               OR h.profesion ILIKE %s
               OR h.habitacion ILIKE %s
               OR h.telefono ILIKE %s
               OR h.domicilio ILIKE %s
               OR h.destino ILIKE %s
            ORDER BY h.fecha_registro DESC
        """
        params = [patron] * 11

        self._query_actual = query
        self._params_actuales = params
        self._ejecutar_busqueda(query, params)

    def _buscar_avanzada(self):
        """Ejecuta búsqueda con filtros avanzados."""
        query = """
            SELECT h.id, ht.nombre as hotel, h.apellido_nombre, h.dni_pasaporte,
                   h.nacionalidad, h.procedencia, h.edad, h.profesion,
                   h.fecha_entrada, h.fecha_salida, h.habitacion, h.telefono,
                   h.domicilio, h.destino, h.movilidad, h.origen_carga
            FROM huespedes h
            JOIN hoteles ht ON h.hotel_id = ht.id
            WHERE 1=1
        """
        params = []

        # Hotel
        if self.filtro_hotel.get():
            query += " AND ht.nombre = %s"
            params.append(self.filtro_hotel.get())

        # Ciudad
        if self.filtro_ciudad.get():
            query += " AND ht.ciudad_localidad = %s"
            params.append(self.filtro_ciudad.get())

        # Nacionalidad
        if self.filtro_nacionalidad.get():
            query += " AND h.nacionalidad ILIKE %s"
            params.append(f"%{self.filtro_nacionalidad.get()}%")

        # DNI
        if self.filtro_dni.get():
            query += " AND h.dni_pasaporte ILIKE %s"
            params.append(f"%{self.filtro_dni.get()}%")

        # Profesión
        if self.filtro_profesion.get():
            query += " AND h.profesion ILIKE %s"
            params.append(f"%{self.filtro_profesion.get()}%")

        # Procedencia
        if self.filtro_procedencia.get():
            query += " AND h.procedencia ILIKE %s"
            params.append(f"%{self.filtro_procedencia.get()}%")

        # Fechas
        if self.filtro_fecha_desde.get():
            from utils.validators import validar_fecha
            ok, _, fecha = validar_fecha(self.filtro_fecha_desde.get(), permite_vacio=True)
            if ok and fecha:
                query += " AND h.fecha_entrada >= %s"
                params.append(fecha)

        if self.filtro_fecha_hasta.get():
            from utils.validators import validar_fecha
            ok, _, fecha = validar_fecha(self.filtro_fecha_hasta.get(), permite_vacio=True)
            if ok and fecha:
                query += " AND h.fecha_entrada <= %s"
                params.append(fecha)

        # Edad
        if self.filtro_edad_min.get():
            try:
                query += " AND h.edad >= %s"
                params.append(int(self.filtro_edad_min.get()))
            except ValueError:
                pass

        if self.filtro_edad_max.get():
            try:
                query += " AND h.edad <= %s"
                params.append(int(self.filtro_edad_max.get()))
            except ValueError:
                pass

        # Habitación
        if self.filtro_habitacion.get():
            query += " AND h.habitacion ILIKE %s"
            params.append(f"%{self.filtro_habitacion.get()}%")

        # Destino
        if self.filtro_destino.get():
            query += " AND h.destino ILIKE %s"
            params.append(f"%{self.filtro_destino.get()}%")

        # Teléfono
        if self.filtro_telefono.get():
            query += " AND h.telefono ILIKE %s"
            params.append(f"%{self.filtro_telefono.get()}%")

        query += " ORDER BY h.fecha_registro DESC"

        self._query_actual = query
        self._params_actuales = params
        self._ejecutar_busqueda(query, params)

    def _ejecutar_busqueda(self, query: str, params: list, offset: int = 0):
        """Ejecuta la búsqueda en un hilo secundario."""
        self.label_resultados.configure(text="⏳ Buscando...")

        def tarea():
            try:
                count_query = f"SELECT COUNT(*) as total FROM ({query}) sub"
                count_result = db.ejecutar_query_one(count_query, tuple(params))
                total = count_result["total"] if count_result else 0

                query_paginada = query + f" LIMIT {DEFAULT_PAGE_SIZE} OFFSET {offset}"
                resultados = db.ejecutar_query(query_paginada, tuple(params), fetch=True)

                self.after(0, lambda: self._busqueda_completada(resultados, total))

            except Exception as e:
                from utils.logger import log_error
                log_error("Error en búsqueda", e)
                self.after(0, lambda: mostrar_error(self, "Error de búsqueda",
                              f"Error al ejecutar la búsqueda:\n{str(e)}"))
                self.after(0, lambda: self.label_resultados.configure(
                    text="Resultados de búsqueda"))

        threading.Thread(target=tarea, daemon=True).start()

    def _busqueda_completada(self, resultados, total):
        """Callback en el hilo principal con los resultados de la búsqueda."""
        self.resultados = resultados if resultados else []

        datos_tabla = []
        for r in self.resultados:
            datos_tabla.append({
                "id": str(r["id"]),
                "hotel": r["hotel"],
                "apellido_nombre": r["apellido_nombre"],
                "dni_pasaporte": formato_dni(str(r["dni_pasaporte"])) if r["dni_pasaporte"] else "",
                "nacionalidad": r["nacionalidad"] or "",
                "procedencia": r["procedencia"] or "",
                "edad": str(r["edad"]) if r["edad"] else "",
                "profesion": r["profesion"] or "",
                "fecha_entrada": formato_fecha(r["fecha_entrada"]),
                "fecha_salida": formato_fecha(r["fecha_salida"]),
                "habitacion": r.get("habitacion", "") or "",
                "telefono": r.get("telefono", "") or "",
                "origen": r["origen_carga"] or "",
            })
        self.tabla.cargar_datos(datos_tabla)

        self.paginador.configurar(total)

        self.label_resultados.configure(
            text=f"Resultados: {total} registro(s) encontrado(s)"
        )

        log_info(f"Búsqueda ejecutada: {total} resultados")

    def _cambiar_pagina(self, offset: int, limit: int):
        """Callback del paginador para cambiar de página."""
        if self._query_actual:
            self._ejecutar_busqueda(self._query_actual, self._params_actuales, offset)

    def _ver_detalle(self, datos: dict):
        """Muestra el detalle completo de un huésped seleccionado."""
        huesped_id = datos.get("id")
        if not huesped_id:
            return

        try:
            resultado = db.ejecutar_query_one("""
                SELECT h.*, ht.nombre as hotel_nombre, ht.direccion as hotel_direccion,
                       ht.ciudad_localidad, u.nombre_completo as cargado_por
                FROM huespedes h
                JOIN hoteles ht ON h.hotel_id = ht.id
                LEFT JOIN usuarios u ON h.usuario_carga_id = u.id
                WHERE h.id = %s
            """, (int(huesped_id),))

            if resultado:
                detalle = (
                    f"Hotel: {resultado['hotel_nombre']}\n"
                    f"Dirección: {resultado.get('hotel_direccion', 'N/A')}\n"
                    f"Ciudad: {resultado.get('ciudad_localidad', 'N/A')}\n\n"
                    f"Apellido y Nombre: {resultado['apellido_nombre']}\n"
                    f"DNI/Pasaporte: {formato_dni(str(resultado['dni_pasaporte'])) if resultado['dni_pasaporte'] else 'N/A'}\n"
                    f"Nacionalidad: {resultado.get('nacionalidad', 'N/A')}\n"
                    f"Procedencia: {resultado.get('procedencia', 'N/A')}\n"
                    f"Fecha Nac.: {formato_fecha(resultado.get('fecha_nacimiento'))}\n"
                    f"Edad: {resultado.get('edad', 'N/A')}\n"
                    f"Profesión: {resultado.get('profesion', 'N/A')}\n"
                    f"Entrada: {formato_fecha(resultado.get('fecha_entrada'))}\n"
                    f"Salida: {formato_fecha(resultado.get('fecha_salida'))}\n\n"
                    f"Habitación: {resultado.get('habitacion', 'N/A') or 'N/A'}\n"
                    f"Domicilio: {resultado.get('domicilio', 'N/A') or 'N/A'}\n"
                    f"Destino: {resultado.get('destino', 'N/A') or 'N/A'}\n"
                    f"Movilidad: {resultado.get('movilidad', 'N/A') or 'N/A'}\n"
                    f"Teléfono: {resultado.get('telefono', 'N/A') or 'N/A'}\n\n"
                    f"Origen: {resultado.get('origen_carga', 'N/A')}\n"
                    f"Cargado por: {resultado.get('cargado_por', 'N/A')}\n"
                    f"Fecha registro: {formato_fecha(resultado.get('fecha_registro'))}"
                )

                # Ventana de detalle
                self._mostrar_ventana_detalle(resultado, detalle)

        except Exception as e:
            from utils.logger import log_error
            log_error(f"Error al obtener detalle de huésped {huesped_id}", e)

    def _mostrar_ventana_detalle(self, datos: dict, detalle_texto: str):
        """Muestra una ventana con el detalle completo del huésped."""
        ventana = ctk.CTkToplevel(self)
        ventana.title(f"Detalle - {datos['apellido_nombre']}")
        ventana.geometry("500x550")
        ventana.resizable(False, False)
        ventana.grab_set()
        ventana.transient(self)

        # Centrar
        ventana.update_idletasks()
        x = (ventana.winfo_screenwidth() // 2) - 250
        y = (ventana.winfo_screenheight() // 2) - 275
        ventana.geometry(f"500x550+{x}+{y}")

        # Contenido
        frame = ctk.CTkScrollableFrame(ventana, fg_color="transparent")
        frame.pack(fill="both", expand=True, padx=20, pady=20)

        ctk.CTkLabel(
            frame, text=f"👤 {datos['apellido_nombre']}",
            font=obtener_fuente("subtitulo"),
            anchor="w"
        ).pack(fill="x", pady=(0, 15))

        ctk.CTkLabel(
            frame, text=detalle_texto,
            font=obtener_fuente("body"),
            justify="left",
            anchor="nw",
            wraplength=440
        ).pack(fill="x")

        # Botones
        btn_frame = ctk.CTkFrame(ventana, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=(0, 15))

        from auth.roles import tiene_permiso
        if tiene_permiso(self.usuario["rol"], "eliminar_registros"):
            ctk.CTkButton(
                btn_frame, text="🗑️ Eliminar",
                fg_color=COLORS["error"],
                hover_color="#C62828",
                height=36,
                command=lambda: self._eliminar_huesped(datos["id"], ventana)
            ).pack(side="left", padx=5)

        ctk.CTkButton(
            btn_frame, text="Cerrar",
            height=36,
            command=ventana.destroy
        ).pack(side="right", padx=5)

    def _eliminar_huesped(self, huesped_id: int, ventana):
        """Elimina un huésped de la base de datos."""
        if confirmar_eliminar(ventana, "este registro de huésped"):
            try:
                db.ejecutar_query(
                    "DELETE FROM huespedes WHERE id = %s", (huesped_id,)
                )
                log_info(f"Huésped ID {huesped_id} eliminado")
                mostrar_exito(ventana, "Eliminado", "Registro eliminado correctamente")
                ventana.destroy()
                # Refrescar búsqueda
                if self._query_actual:
                    self._ejecutar_busqueda(self._query_actual, self._params_actuales)
            except Exception as e:
                from utils.logger import log_error
                log_error(f"Error al eliminar huésped {huesped_id}", e)
                mostrar_error(ventana, "Error", f"No se pudo eliminar: {str(e)}")

    def _exportar_resultados(self):
        """Exporta los resultados actuales a Excel."""
        if not self.resultados:
            mostrar_advertencia(self, "Sin datos", "No hay resultados para exportar")
            return

        try:
            from modules.reports import exportar_a_excel
            from tkinter import filedialog
            from utils.formatters import formato_nombre_archivo

            archivo = filedialog.asksaveasfilename(
                title="Guardar resultados",
                defaultextension=".xlsx",
                initialfile=formato_nombre_archivo("busqueda_huespedes"),
                filetypes=[("Excel", "*.xlsx")]
            )
            if archivo:
                exportar_a_excel(self.resultados, archivo, "Resultados de búsqueda")
                mostrar_exito(self, "Exportado", f"Resultados exportados a:\n{archivo}")
        except Exception as e:
            from utils.logger import log_error
            log_error("Error al exportar resultados", e)
            mostrar_error(self, "Error", f"Error al exportar: {str(e)}")

    def _limpiar_filtros(self):
        """Limpia todos los filtros avanzados."""
        for filtro in [self.filtro_hotel, self.filtro_ciudad, self.filtro_nacionalidad,
                       self.filtro_dni, self.filtro_profesion, self.filtro_procedencia,
                       self.filtro_fecha_desde, self.filtro_fecha_hasta,
                       self.filtro_edad_min, self.filtro_edad_max,
                       self.filtro_habitacion, self.filtro_destino, self.filtro_telefono]:
            filtro.limpiar()
