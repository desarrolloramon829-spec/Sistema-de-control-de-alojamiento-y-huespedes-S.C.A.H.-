"""
S.C.A.H. - Componentes UI reutilizables
Tablas con scroll, inputs con validación, etc.
"""

import customtkinter as ctk
import tkinter as tk
from tkinter import ttk
from ui.themes import COLORS, obtener_fuente


class TablaScrollable(ctk.CTkFrame):
    """Tabla con scroll horizontal y vertical usando Treeview."""

    def __init__(self, parent, columnas: list, on_doble_click=None,
                 on_seleccion=None, altura: int = 15):
        super().__init__(parent, fg_color="transparent")

        self.columnas = columnas
        self.on_doble_click = on_doble_click
        self.on_seleccion = on_seleccion

        # Estilo del Treeview
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("SCAH.Treeview",
                         background=COLORS["bg_medium"],
                         foreground=COLORS["text_primary"],
                         fieldbackground=COLORS["bg_medium"],
                         borderwidth=0,
                         font=("Segoe UI", 11),
                         rowheight=28)
        style.configure("SCAH.Treeview.Heading",
                         background=COLORS["table_header"],
                         foreground=COLORS["text_primary"],
                         font=("Segoe UI", 11, "bold"),
                         borderwidth=1,
                         relief="flat")
        style.map("SCAH.Treeview",
                   background=[("selected", COLORS["table_selected"])],
                   foreground=[("selected", COLORS["text_primary"])])
        style.map("SCAH.Treeview.Heading",
                   background=[("active", COLORS["primary"])])

        # Frame contenedor
        tree_frame = ctk.CTkFrame(self, fg_color=COLORS["bg_medium"], corner_radius=8)
        tree_frame.pack(fill="both", expand=True)

        # Scrollbars
        scroll_y = ttk.Scrollbar(tree_frame, orient="vertical")
        scroll_x = ttk.Scrollbar(tree_frame, orient="horizontal")

        # Treeview
        col_ids = [c["id"] for c in columnas]
        self.tree = ttk.Treeview(
            tree_frame,
            columns=col_ids,
            show="headings",
            style="SCAH.Treeview",
            height=altura,
            yscrollcommand=scroll_y.set,
            xscrollcommand=scroll_x.set,
            selectmode="browse"
        )

        scroll_y.config(command=self.tree.yview)
        scroll_x.config(command=self.tree.xview)

        # Configurar columnas
        for col in columnas:
            self.tree.heading(col["id"], text=col["texto"],
                              command=lambda c=col["id"]: self._ordenar(c))
            self.tree.column(col["id"],
                             width=col.get("ancho", 120),
                             minwidth=col.get("min_ancho", 60),
                             anchor=col.get("anchor", "w"))

        # Layout
        self.tree.grid(row=0, column=0, sticky="nsew")
        scroll_y.grid(row=0, column=1, sticky="ns")
        scroll_x.grid(row=1, column=0, sticky="ew")
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)

        # Tags para filas alternadas
        self.tree.tag_configure("even", background=COLORS["table_row_even"])
        self.tree.tag_configure("odd", background=COLORS["table_row_odd"])

        # Eventos
        if on_doble_click:
            self.tree.bind("<Double-1>", self._on_double_click)
        if on_seleccion:
            self.tree.bind("<<TreeviewSelect>>", self._on_select)

        self._orden_ascendente = {}

    def cargar_datos(self, datos: list):
        """Carga datos en la tabla. Cada dato es una tupla/lista con los valores."""
        # Limpiar tabla
        for item in self.tree.get_children():
            self.tree.delete(item)

        # Insertar datos
        for i, fila in enumerate(datos):
            tag = "even" if i % 2 == 0 else "odd"
            valores = []
            for col in self.columnas:
                idx = col.get("data_index", col["id"])
                if isinstance(fila, dict):
                    valores.append(str(fila.get(idx, "")))
                elif isinstance(fila, (list, tuple)):
                    col_idx = [c["id"] for c in self.columnas].index(col["id"])
                    valores.append(str(fila[col_idx]) if col_idx < len(fila) else "")
                else:
                    valores.append("")
            self.tree.insert("", "end", values=valores, tags=(tag,))

    def obtener_seleccion(self) -> dict | None:
        """Retorna los valores de la fila seleccionada como diccionario."""
        seleccion = self.tree.selection()
        if not seleccion:
            return None

        valores = self.tree.item(seleccion[0])["values"]
        return {col["id"]: valores[i] for i, col in enumerate(self.columnas)}

    def obtener_total(self) -> int:
        """Retorna el número total de filas."""
        return len(self.tree.get_children())

    def limpiar(self):
        """Elimina todas las filas."""
        for item in self.tree.get_children():
            self.tree.delete(item)

    def _on_double_click(self, event):
        datos = self.obtener_seleccion()
        if datos and self.on_doble_click:
            self.on_doble_click(datos)

    def _on_select(self, event):
        datos = self.obtener_seleccion()
        if datos and self.on_seleccion:
            self.on_seleccion(datos)

    def _ordenar(self, columna):
        """Ordena la tabla por una columna."""
        asc = self._orden_ascendente.get(columna, True)
        items = [(self.tree.set(k, columna), k) for k in self.tree.get_children("")]
        items.sort(reverse=not asc, key=lambda t: t[0].lower())

        for index, (val, k) in enumerate(items):
            self.tree.move(k, "", index)
            tag = "even" if index % 2 == 0 else "odd"
            self.tree.item(k, tags=(tag,))

        self._orden_ascendente[columna] = not asc


class InputConLabel(ctk.CTkFrame):
    """Campo de entrada con label y mensaje de error."""

    def __init__(self, parent, label: str, placeholder: str = "",
                 obligatorio: bool = False, tipo: str = "text",
                 ancho_label: int = 130, **kwargs):
        super().__init__(parent, fg_color="transparent")

        self.obligatorio = obligatorio
        self.tipo = tipo

        # Layout horizontal
        self.grid_columnconfigure(1, weight=1)

        # Label
        label_text = f"{label} *" if obligatorio else label
        self.label = ctk.CTkLabel(
            self, text=label_text,
            font=obtener_fuente("small_bold"),
            width=ancho_label,
            anchor="w"
        )
        self.label.grid(row=0, column=0, sticky="w", padx=(0, 10))

        # Entry
        if tipo == "text" or tipo == "number":
            self.entry = ctk.CTkEntry(
                self,
                placeholder_text=placeholder,
                height=35,
                font=obtener_fuente("body"),
                **kwargs
            )
        elif tipo == "combo":
            valores = kwargs.pop("values", [])
            self.entry = ctk.CTkComboBox(
                self,
                values=valores,
                height=35,
                font=obtener_fuente("body"),
                **kwargs
            )
        elif tipo == "date":
            self.entry = ctk.CTkEntry(
                self,
                placeholder_text=placeholder or "dd/mm/aaaa",
                height=35,
                font=obtener_fuente("body"),
                **kwargs
            )

        self.entry.grid(row=0, column=1, sticky="ew")

        # Mensaje de error
        self.label_error = ctk.CTkLabel(
            self, text="",
            font=obtener_fuente("tiny"),
            text_color=COLORS["error"],
            anchor="w"
        )
        self.label_error.grid(row=1, column=1, sticky="w")

    def get(self) -> str:
        """Obtiene el valor del campo."""
        if hasattr(self.entry, 'get'):
            return self.entry.get().strip()
        return ""

    def set(self, valor: str):
        """Establece el valor del campo."""
        if isinstance(self.entry, ctk.CTkComboBox):
            self.entry.set(valor)
        else:
            self.entry.delete(0, "end")
            self.entry.insert(0, str(valor))

    def limpiar(self):
        """Limpia el campo y el error."""
        if isinstance(self.entry, ctk.CTkComboBox):
            self.entry.set("")
        else:
            self.entry.delete(0, "end")
        self.label_error.configure(text="")

    def mostrar_error(self, mensaje: str):
        """Muestra un mensaje de error."""
        self.label_error.configure(text=mensaje)
        if hasattr(self.entry, 'configure'):
            self.entry.configure(border_color=COLORS["error"])

    def limpiar_error(self):
        """Limpia el mensaje de error."""
        self.label_error.configure(text="")
        if hasattr(self.entry, 'configure'):
            self.entry.configure(border_color=COLORS["input_border"])


class BarraProgreso(ctk.CTkFrame):
    """Barra de progreso con etiqueta y porcentaje."""

    def __init__(self, parent, texto: str = "Procesando..."):
        super().__init__(parent, fg_color="transparent")

        self.label = ctk.CTkLabel(
            self, text=texto,
            font=obtener_fuente("small"),
            anchor="w"
        )
        self.label.pack(fill="x", pady=(0, 5))

        self.progress = ctk.CTkProgressBar(self, height=20)
        self.progress.pack(fill="x")
        self.progress.set(0)

        self.label_porcentaje = ctk.CTkLabel(
            self, text="0%",
            font=obtener_fuente("small_bold")
        )
        self.label_porcentaje.pack(pady=(5, 0))

    def actualizar(self, valor: float, texto: str = None):
        """Actualiza la barra de progreso (valor entre 0 y 1)."""
        self.progress.set(valor)
        self.label_porcentaje.configure(text=f"{int(valor * 100)}%")
        if texto:
            self.label.configure(text=texto)
        self.update()

    def completar(self, texto: str = "¡Completado!"):
        """Marca la barra como completada."""
        self.progress.set(1)
        self.label_porcentaje.configure(text="100%")
        self.label.configure(text=texto)
        self.update()


class PanelEstadistica(ctk.CTkFrame):
    """Panel para mostrar un dato estadístico con icono."""

    def __init__(self, parent, titulo: str, valor: str, icono: str,
                 color: str = None):
        super().__init__(parent, fg_color=COLORS["bg_card"], corner_radius=12, height=100)
        self.pack_propagate(False)

        content = ctk.CTkFrame(self, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=15, pady=10)

        # Icono
        ctk.CTkLabel(
            content, text=icono,
            font=ctk.CTkFont(size=28)
        ).pack(anchor="w")

        # Valor
        self.label_valor = ctk.CTkLabel(
            content, text=str(valor),
            font=obtener_fuente("subtitulo"),
            text_color=color or COLORS["primary_light"],
            anchor="w"
        )
        self.label_valor.pack(anchor="w")

        # Título
        ctk.CTkLabel(
            content, text=titulo,
            font=obtener_fuente("small"),
            text_color=COLORS["text_secondary"],
            anchor="w"
        ).pack(anchor="w")

    def actualizar(self, valor: str):
        """Actualiza el valor mostrado."""
        self.label_valor.configure(text=str(valor))


class Paginador(ctk.CTkFrame):
    """Control de paginación para tablas."""

    def __init__(self, parent, on_cambio_pagina, registros_por_pagina: int = 50):
        super().__init__(parent, fg_color="transparent")

        self.on_cambio_pagina = on_cambio_pagina
        self.registros_por_pagina = registros_por_pagina
        self.pagina_actual = 1
        self.total_paginas = 1
        self.total_registros = 0

        # Layout
        self.grid_columnconfigure(1, weight=1)

        # Info de registros
        self.label_info = ctk.CTkLabel(
            self, text="0 registros",
            font=obtener_fuente("small"),
            text_color=COLORS["text_secondary"]
        )
        self.label_info.grid(row=0, column=0, sticky="w")

        # Controles de navegación
        nav_frame = ctk.CTkFrame(self, fg_color="transparent")
        nav_frame.grid(row=0, column=2, sticky="e")

        self.btn_primera = ctk.CTkButton(
            nav_frame, text="⏮", width=35, height=30,
            command=lambda: self._ir_pagina(1)
        )
        self.btn_primera.pack(side="left", padx=2)

        self.btn_anterior = ctk.CTkButton(
            nav_frame, text="◀", width=35, height=30,
            command=lambda: self._ir_pagina(self.pagina_actual - 1)
        )
        self.btn_anterior.pack(side="left", padx=2)

        self.label_pagina = ctk.CTkLabel(
            nav_frame, text="1 / 1",
            font=obtener_fuente("small_bold"),
            width=80
        )
        self.label_pagina.pack(side="left", padx=5)

        self.btn_siguiente = ctk.CTkButton(
            nav_frame, text="▶", width=35, height=30,
            command=lambda: self._ir_pagina(self.pagina_actual + 1)
        )
        self.btn_siguiente.pack(side="left", padx=2)

        self.btn_ultima = ctk.CTkButton(
            nav_frame, text="⏭", width=35, height=30,
            command=lambda: self._ir_pagina(self.total_paginas)
        )
        self.btn_ultima.pack(side="left", padx=2)

    def configurar(self, total_registros: int):
        """Configura el paginador con el total de registros."""
        self.total_registros = total_registros
        self.total_paginas = max(1, (total_registros + self.registros_por_pagina - 1) // self.registros_por_pagina)
        self.pagina_actual = 1
        self._actualizar_ui()

    def _ir_pagina(self, pagina: int):
        if pagina < 1 or pagina > self.total_paginas:
            return
        self.pagina_actual = pagina
        self._actualizar_ui()
        offset = (pagina - 1) * self.registros_por_pagina
        self.on_cambio_pagina(offset, self.registros_por_pagina)

    def _actualizar_ui(self):
        self.label_pagina.configure(text=f"{self.pagina_actual} / {self.total_paginas}")
        inicio = (self.pagina_actual - 1) * self.registros_por_pagina + 1
        fin = min(self.pagina_actual * self.registros_por_pagina, self.total_registros)
        self.label_info.configure(
            text=f"Mostrando {inicio}-{fin} de {self.total_registros} registros"
        )

        self.btn_primera.configure(state="normal" if self.pagina_actual > 1 else "disabled")
        self.btn_anterior.configure(state="normal" if self.pagina_actual > 1 else "disabled")
        self.btn_siguiente.configure(state="normal" if self.pagina_actual < self.total_paginas else "disabled")
        self.btn_ultima.configure(state="normal" if self.pagina_actual < self.total_paginas else "disabled")
