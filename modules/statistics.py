"""
S.C.A.H. - Módulo de Estadísticas y Dashboard
Dashboard con resumen general y estadísticas detalladas con gráficos
"""

import customtkinter as ctk
from datetime import datetime, timedelta

from database.connection import db
from ui.themes import COLORS, obtener_fuente
from ui.components import PanelEstadistica
from utils.logger import log_error


class DashboardModule(ctk.CTkFrame):
    """Panel principal con resumen general del sistema."""

    def __init__(self, parent, usuario: dict):
        super().__init__(parent, fg_color="transparent")
        self.usuario = usuario
        self._crear_ui()
        self._cargar_datos()

    def _crear_ui(self):
        """Crea la interfaz del dashboard."""
        # Título
        header = ctk.CTkFrame(self, fg_color=COLORS["bg_card"], corner_radius=10)
        header.pack(fill="x", pady=(0, 15))

        header_inner = ctk.CTkFrame(header, fg_color="transparent")
        header_inner.pack(fill="x", padx=20, pady=15)

        ctk.CTkLabel(
            header_inner, text="📊 Panel de Control",
            font=obtener_fuente("heading"), anchor="w"
        ).pack(side="left")

        ctk.CTkButton(
            header_inner, text="🔄 Actualizar",
            font=obtener_fuente("small_bold"), height=36,
            fg_color=COLORS["primary"], hover_color=COLORS["primary_dark"],
            command=self._cargar_datos
        ).pack(side="right")

        # Tarjetas de estadísticas
        cards_frame = ctk.CTkFrame(self, fg_color="transparent")
        cards_frame.pack(fill="x", pady=(0, 15))
        cards_frame.grid_columnconfigure((0, 1, 2, 3), weight=1)

        self.card_huespedes = PanelEstadistica(cards_frame, "Total Huéspedes", "0", "👥")
        self.card_huespedes.grid(row=0, column=0, padx=5, sticky="nsew")

        self.card_hoteles = PanelEstadistica(cards_frame, "Hoteles Activos", "0", "🏨")
        self.card_hoteles.grid(row=0, column=1, padx=5, sticky="nsew")

        self.card_alojados = PanelEstadistica(cards_frame, "Alojados Hoy", "0", "🛏️")
        self.card_alojados.grid(row=0, column=2, padx=5, sticky="nsew")

        self.card_importaciones = PanelEstadistica(cards_frame, "Importaciones", "0", "📥")
        self.card_importaciones.grid(row=0, column=3, padx=5, sticky="nsew")

        # Sección inferior: últimos registros + resumen
        bottom_frame = ctk.CTkFrame(self, fg_color="transparent")
        bottom_frame.pack(fill="both", expand=True)
        bottom_frame.grid_columnconfigure(0, weight=2)
        bottom_frame.grid_columnconfigure(1, weight=1)

        # Últimos huéspedes
        left_card = ctk.CTkFrame(bottom_frame, fg_color=COLORS["bg_card"], corner_radius=10)
        left_card.grid(row=0, column=0, sticky="nsew", padx=(0, 5))

        ctk.CTkLabel(
            left_card, text="Últimos Huéspedes Registrados",
            font=obtener_fuente("subtitulo")
        ).pack(anchor="w", padx=20, pady=(15, 10))

        self.frame_ultimos = ctk.CTkScrollableFrame(
            left_card, fg_color="transparent", height=300
        )
        self.frame_ultimos.pack(fill="both", expand=True, padx=15, pady=(0, 15))

        # Resumen por ciudades
        right_card = ctk.CTkFrame(bottom_frame, fg_color=COLORS["bg_card"], corner_radius=10)
        right_card.grid(row=0, column=1, sticky="nsew", padx=(5, 0))

        ctk.CTkLabel(
            right_card, text="Top Ciudades",
            font=obtener_fuente("subtitulo")
        ).pack(anchor="w", padx=20, pady=(15, 10))

        self.frame_ciudades = ctk.CTkScrollableFrame(
            right_card, fg_color="transparent", height=300
        )
        self.frame_ciudades.pack(fill="both", expand=True, padx=15, pady=(0, 15))

    def _cargar_datos(self):
        """Carga todos los datos del dashboard."""
        try:
            # Total huéspedes
            res = db.ejecutar_query_one("SELECT COUNT(*) as total FROM huespedes")
            self.card_huespedes.actualizar(str(res["total"]) if res else "0")

            # Hoteles activos
            res = db.ejecutar_query_one("SELECT COUNT(*) as total FROM hoteles WHERE activo = TRUE")
            self.card_hoteles.actualizar(str(res["total"]) if res else "0")

            # Alojados hoy
            hoy = datetime.now().date()
            res = db.ejecutar_query_one("""
                SELECT COUNT(*) as total FROM huespedes
                WHERE fecha_entrada <= %s AND (fecha_salida IS NULL OR fecha_salida >= %s)
            """, (hoy, hoy))
            self.card_alojados.actualizar(str(res["total"]) if res else "0")

            # Importaciones
            res = db.ejecutar_query_one("SELECT COUNT(*) as total FROM importaciones_log")
            self.card_importaciones.actualizar(str(res["total"]) if res else "0")

            # Últimos huéspedes
            self._cargar_ultimos_huespedes()

            # Top ciudades
            self._cargar_top_ciudades()

        except Exception as e:
            log_error("Error al cargar dashboard", e)

    def _cargar_ultimos_huespedes(self):
        """Carga los últimos 10 huéspedes registrados."""
        for w in self.frame_ultimos.winfo_children():
            w.destroy()

        try:
            resultados = db.ejecutar_query("""
                SELECT hu.apellido_nombre, hu.dni_pasaporte, h.nombre as hotel,
                       hu.fecha_entrada, hu.nacionalidad
                FROM huespedes hu
                LEFT JOIN hoteles h ON hu.hotel_id = h.id
                ORDER BY hu.id DESC LIMIT 10
            """, fetch=True)

            if resultados:
                for r in resultados:
                    item = ctk.CTkFrame(self.frame_ultimos, fg_color="gray20", corner_radius=6)
                    item.pack(fill="x", pady=2)

                    entrada = ""
                    if r.get("fecha_entrada"):
                        entrada = r["fecha_entrada"].strftime("%d/%m/%Y") if hasattr(r["fecha_entrada"], 'strftime') else str(r["fecha_entrada"])

                    ctk.CTkLabel(
                        item,
                        text=f"  {r['apellido_nombre'] or 'S/N'}  |  {r.get('dni_pasaporte', '')}  |  {r.get('hotel', '')}",
                        font=obtener_fuente("small"), anchor="w"
                    ).pack(fill="x", padx=10, pady=3)

                    ctk.CTkLabel(
                        item,
                        text=f"    📅 {entrada}  •  🌍 {r.get('nacionalidad', '')}",
                        font=("Segoe UI", 11), anchor="w",
                        text_color=COLORS["text_secondary"]
                    ).pack(fill="x", padx=10, pady=(0, 3))
            else:
                ctk.CTkLabel(
                    self.frame_ultimos,
                    text="Sin registros aún",
                    font=obtener_fuente("small"),
                    text_color=COLORS["text_secondary"]
                ).pack(pady=20)

        except Exception as e:
            log_error("Error al cargar últimos huéspedes", e)

    def _cargar_top_ciudades(self):
        """Carga las ciudades con más huéspedes."""
        for w in self.frame_ciudades.winfo_children():
            w.destroy()

        try:
            resultados = db.ejecutar_query("""
                SELECT h.ciudad_localidad, COUNT(hu.id) as total
                FROM hoteles h
                JOIN huespedes hu ON h.id = hu.hotel_id
                WHERE h.ciudad_localidad IS NOT NULL AND h.ciudad_localidad != ''
                GROUP BY h.ciudad_localidad
                ORDER BY total DESC
                LIMIT 10
            """, fetch=True)

            if resultados:
                max_total = resultados[0]["total"] if resultados else 1
                for r in resultados:
                    item_frame = ctk.CTkFrame(self.frame_ciudades, fg_color="transparent")
                    item_frame.pack(fill="x", pady=3)

                    ctk.CTkLabel(
                        item_frame,
                        text=f"📍 {r['ciudad_localidad']}",
                        font=obtener_fuente("small"), anchor="w"
                    ).pack(anchor="w")

                    bar_frame = ctk.CTkFrame(item_frame, fg_color="transparent")
                    bar_frame.pack(fill="x")

                    progress = r["total"] / max_total if max_total > 0 else 0
                    bar = ctk.CTkProgressBar(bar_frame, height=14)
                    bar.pack(side="left", fill="x", expand=True, padx=(0, 8))
                    bar.set(progress)

                    ctk.CTkLabel(
                        bar_frame,
                        text=str(r["total"]),
                        font=("Segoe UI", 11, "bold"),
                        width=40
                    ).pack(side="right")
            else:
                ctk.CTkLabel(
                    self.frame_ciudades,
                    text="Sin datos aún",
                    font=obtener_fuente("small"),
                    text_color=COLORS["text_secondary"]
                ).pack(pady=20)

        except Exception as e:
            log_error("Error al cargar top ciudades", e)


class StatisticsModule(ctk.CTkFrame):
    """Módulo de estadísticas detalladas con gráficos matplotlib."""

    def __init__(self, parent, usuario: dict):
        super().__init__(parent, fg_color="transparent")
        self.usuario = usuario
        self._crear_ui()

    def _crear_ui(self):
        """Crea la interfaz de estadísticas."""
        header = ctk.CTkFrame(self, fg_color=COLORS["bg_card"], corner_radius=10)
        header.pack(fill="x", pady=(0, 10))

        header_inner = ctk.CTkFrame(header, fg_color="transparent")
        header_inner.pack(fill="x", padx=20, pady=15)

        ctk.CTkLabel(
            header_inner, text="📈 Estadísticas Detalladas",
            font=obtener_fuente("heading")
        ).pack(side="left")

        ctk.CTkButton(
            header_inner, text="🔄 Generar",
            font=obtener_fuente("small_bold"), height=36,
            command=self._generar_estadisticas
        ).pack(side="right")

        # Selector de tipo
        tipo_frame = ctk.CTkFrame(self, fg_color=COLORS["bg_card"], corner_radius=10)
        tipo_frame.pack(fill="x", pady=(0, 10))

        tipo_inner = ctk.CTkFrame(tipo_frame, fg_color="transparent")
        tipo_inner.pack(fill="x", padx=20, pady=10)

        ctk.CTkLabel(tipo_inner, text="Tipo de Estadística:",
                     font=obtener_fuente("small_bold")).pack(side="left", padx=(0, 10))

        self.tipo_stat = ctk.CTkComboBox(
            tipo_inner,
            values=[
                "Nacionalidades",
                "Profesiones",
                "Procedencia",
                "Destinos",
                "Huéspedes por Hotel",
                "Rango de Edades",
                "Tendencia Mensual"
            ],
            font=obtener_fuente("small"),
            height=36, width=250,
            state="readonly"
        )
        self.tipo_stat.pack(side="left")
        self.tipo_stat.set("Nacionalidades")

        # Contenedor de gráficos
        self.chart_frame = ctk.CTkFrame(self, fg_color=COLORS["bg_card"], corner_radius=10)
        self.chart_frame.pack(fill="both", expand=True)

        self.chart_container = ctk.CTkFrame(self.chart_frame, fg_color="transparent")
        self.chart_container.pack(fill="both", expand=True, padx=20, pady=20)

        # Mensaje inicial
        ctk.CTkLabel(
            self.chart_container,
            text="Seleccione un tipo de estadística y presione 'Generar'",
            font=obtener_fuente("body"),
            text_color=COLORS["text_secondary"]
        ).pack(expand=True)

    def _generar_estadisticas(self):
        """Genera las estadísticas seleccionadas."""
        tipo = self.tipo_stat.get()

        # Limpiar
        for w in self.chart_container.winfo_children():
            w.destroy()

        try:
            if tipo == "Nacionalidades":
                self._stat_nacionalidades()
            elif tipo == "Profesiones":
                self._stat_profesiones()
            elif tipo == "Procedencia":
                self._stat_procedencia()
            elif tipo == "Destinos":
                self._stat_destinos()
            elif tipo == "Huéspedes por Hotel":
                self._stat_por_hotel()
            elif tipo == "Rango de Edades":
                self._stat_edades()
            elif tipo == "Tendencia Mensual":
                self._stat_tendencia_mensual()

        except Exception as e:
            log_error(f"Error al generar estadística '{tipo}'", e)
            ctk.CTkLabel(
                self.chart_container,
                text=f"Error al generar: {str(e)}",
                font=obtener_fuente("body"),
                text_color=COLORS["error"]
            ).pack(expand=True)

    def _mostrar_grafico_barras(self, datos: list, titulo: str,
                                 xlabel: str = "", ylabel: str = "Cantidad"):
        """Muestra un gráfico de barras usando matplotlib embebido en tkinter."""
        try:
            import matplotlib
            matplotlib.use("TkAgg")
            from matplotlib.figure import Figure
            from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

            fig = Figure(figsize=(10, 5), dpi=100, facecolor="#1a1a2e")
            ax = fig.add_subplot(111)
            ax.set_facecolor("#16213e")

            if datos:
                etiquetas = [d[0][:20] if d[0] else "S/D" for d in datos[:15]]
                valores = [d[1] for d in datos[:15]]

                bars = ax.bar(range(len(etiquetas)), valores, color="#4fc3f7", edgecolor="#0288d1")
                ax.set_xticks(range(len(etiquetas)))
                ax.set_xticklabels(etiquetas, rotation=45, ha="right", fontsize=8, color="white")
                ax.set_ylabel(ylabel, color="white", fontsize=10)
                ax.set_title(titulo, color="white", fontsize=13, fontweight="bold", pad=15)
                ax.tick_params(colors="white")

                for bar, val in zip(bars, valores):
                    ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.5,
                            str(val), ha="center", va="bottom", color="white", fontsize=8)

                for spine in ax.spines.values():
                    spine.set_color("#333")
            else:
                ax.text(0.5, 0.5, "Sin datos disponibles",
                        ha="center", va="center", color="white",
                        fontsize=14, transform=ax.transAxes)

            fig.tight_layout()

            canvas = FigureCanvasTkAgg(fig, master=self.chart_container)
            canvas.draw()
            canvas.get_tk_widget().pack(fill="both", expand=True)

        except ImportError:
            self._mostrar_tabla_fallback(datos, titulo)

    def _mostrar_grafico_lineas(self, datos: list, titulo: str,
                                  xlabel: str = "", ylabel: str = "Cantidad"):
        """Muestra un gráfico de líneas."""
        try:
            import matplotlib
            matplotlib.use("TkAgg")
            from matplotlib.figure import Figure
            from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

            fig = Figure(figsize=(10, 5), dpi=100, facecolor="#1a1a2e")
            ax = fig.add_subplot(111)
            ax.set_facecolor("#16213e")

            if datos:
                etiquetas = [d[0] for d in datos]
                valores = [d[1] for d in datos]

                ax.plot(etiquetas, valores, color="#4fc3f7", marker="o",
                        linewidth=2, markersize=6)
                ax.fill_between(range(len(valores)), valores, alpha=0.2, color="#4fc3f7")
                ax.set_xticks(range(len(etiquetas)))
                ax.set_xticklabels(etiquetas, rotation=45, ha="right", fontsize=8, color="white")
                ax.set_ylabel(ylabel, color="white")
                ax.set_title(titulo, color="white", fontsize=13, fontweight="bold", pad=15)
                ax.tick_params(colors="white")
                ax.grid(True, alpha=0.2, color="white")

                for spine in ax.spines.values():
                    spine.set_color("#333")

            fig.tight_layout()

            canvas = FigureCanvasTkAgg(fig, master=self.chart_container)
            canvas.draw()
            canvas.get_tk_widget().pack(fill="both", expand=True)

        except ImportError:
            self._mostrar_tabla_fallback(datos, titulo)

    def _mostrar_tabla_fallback(self, datos: list, titulo: str):
        """Muestra datos en formato tabla si matplotlib no está disponible."""
        ctk.CTkLabel(
            self.chart_container, text=f"📊 {titulo}",
            font=obtener_fuente("subtitulo")
        ).pack(anchor="w", pady=(0, 10))

        scroll = ctk.CTkScrollableFrame(self.chart_container, fg_color="transparent")
        scroll.pack(fill="both", expand=True)

        for i, (etiqueta, valor) in enumerate(datos[:30]):
            row = ctk.CTkFrame(scroll, fg_color="gray20" if i % 2 else "gray18", corner_radius=4)
            row.pack(fill="x", pady=1)

            ctk.CTkLabel(
                row, text=etiqueta or "S/D",
                font=obtener_fuente("small"), anchor="w"
            ).pack(side="left", padx=15, pady=6)

            ctk.CTkLabel(
                row, text=str(valor),
                font=obtener_fuente("small_bold"), anchor="e"
            ).pack(side="right", padx=15, pady=6)

    def _stat_nacionalidades(self):
        datos = db.ejecutar_query("""
            SELECT nacionalidad, COUNT(*) as total FROM huespedes
            WHERE nacionalidad IS NOT NULL AND nacionalidad != ''
            GROUP BY nacionalidad ORDER BY total DESC LIMIT 15
        """, fetch=True)
        if datos:
            self._mostrar_grafico_barras(
                [(d["nacionalidad"], d["total"]) for d in datos],
                "Distribución por Nacionalidad"
            )
        else:
            self._mostrar_grafico_barras([], "Distribución por Nacionalidad")

    def _stat_profesiones(self):
        datos = db.ejecutar_query("""
            SELECT profesion_ocupacion, COUNT(*) as total FROM huespedes
            WHERE profesion_ocupacion IS NOT NULL AND profesion_ocupacion != ''
            GROUP BY profesion_ocupacion ORDER BY total DESC LIMIT 15
        """, fetch=True)
        if datos:
            self._mostrar_grafico_barras(
                [(d["profesion_ocupacion"], d["total"]) for d in datos],
                "Top 15 Profesiones/Ocupaciones"
            )
        else:
            self._mostrar_grafico_barras([], "Profesiones/Ocupaciones")

    def _stat_procedencia(self):
        datos = db.ejecutar_query("""
            SELECT procedencia, COUNT(*) as total FROM huespedes
            WHERE procedencia IS NOT NULL AND procedencia != ''
            GROUP BY procedencia ORDER BY total DESC LIMIT 15
        """, fetch=True)
        if datos:
            self._mostrar_grafico_barras(
                [(d["procedencia"], d["total"]) for d in datos],
                "Principales Procedencias"
            )
        else:
            self._mostrar_grafico_barras([], "Procedencias")

    def _stat_por_hotel(self):
        datos = db.ejecutar_query("""
            SELECT h.nombre, COUNT(hu.id) as total
            FROM hoteles h
            LEFT JOIN huespedes hu ON h.id = hu.hotel_id
            WHERE h.activo = TRUE
            GROUP BY h.nombre ORDER BY total DESC
        """, fetch=True)
        if datos:
            self._mostrar_grafico_barras(
                [(d["nombre"], d["total"]) for d in datos],
                "Huéspedes por Hotel"
            )
        else:
            self._mostrar_grafico_barras([], "Huéspedes por Hotel")

    def _stat_destinos(self):
        datos = db.ejecutar_query("""
            SELECT destino, COUNT(*) as total FROM huespedes
            WHERE destino IS NOT NULL AND destino != ''
            GROUP BY destino ORDER BY total DESC LIMIT 15
        """, fetch=True)
        if datos:
            self._mostrar_grafico_barras(
                [(d["destino"], d["total"]) for d in datos],
                "Principales Destinos"
            )
        else:
            self._mostrar_grafico_barras([], "Destinos")

    def _stat_edades(self):
        datos = db.ejecutar_query("""
            SELECT
                CASE
                    WHEN edad < 18 THEN '0-17'
                    WHEN edad BETWEEN 18 AND 25 THEN '18-25'
                    WHEN edad BETWEEN 26 AND 35 THEN '26-35'
                    WHEN edad BETWEEN 36 AND 45 THEN '36-45'
                    WHEN edad BETWEEN 46 AND 55 THEN '46-55'
                    WHEN edad BETWEEN 56 AND 65 THEN '56-65'
                    WHEN edad > 65 THEN '65+'
                    ELSE 'S/D'
                END as rango,
                COUNT(*) as total
            FROM huespedes
            WHERE edad IS NOT NULL
            GROUP BY rango
            ORDER BY rango
        """, fetch=True)
        if datos:
            self._mostrar_grafico_barras(
                [(d["rango"], d["total"]) for d in datos],
                "Distribución por Rango de Edad"
            )
        else:
            self._mostrar_grafico_barras([], "Rangos de Edad")

    def _stat_tendencia_mensual(self):
        datos = db.ejecutar_query("""
            SELECT TO_CHAR(fecha_entrada, 'YYYY-MM') as mes, COUNT(*) as total
            FROM huespedes
            WHERE fecha_entrada IS NOT NULL
              AND fecha_entrada >= CURRENT_DATE - INTERVAL '12 months'
            GROUP BY mes ORDER BY mes
        """, fetch=True)
        if datos:
            self._mostrar_grafico_lineas(
                [(d["mes"], d["total"]) for d in datos],
                "Tendencia Mensual de Ingresos (último año)"
            )
        else:
            self._mostrar_grafico_lineas([], "Tendencia Mensual")
