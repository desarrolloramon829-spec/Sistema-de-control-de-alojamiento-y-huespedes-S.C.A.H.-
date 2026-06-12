"""
S.C.A.H. - Módulo de Importación desde Excel - Formato V2 (Tabular)
Lee archivos .xlsx y .xls con formato tabular con encabezados:
FECHA | HABITACION | NOMBRE Y APELLIDO | EDAD | NACIONALIDAD |
PROFESION | PROCEDE | DOMICILIO | DESTINO | DOC | SALIDA | MOVILIDAD | TELEFONO
"""

import os
import threading
import customtkinter as ctk
from tkinter import filedialog
from datetime import datetime

from config import (EXCEL_V2_HUESPED_COLS, EXCEL_V2_HUESPED_START_ROW,
                    EXCEL_V2_HEADER_ALIASES)
from database.connection import db
from ui.themes import COLORS, obtener_fuente
from ui.components import TablaScrollable, BarraProgreso, InputConLabel
from ui.dialogs import mostrar_exito, mostrar_error, mostrar_advertencia, confirmar
from utils.geography import normalizar_huesped_geografia
from utils.validators import (validar_fecha, validar_edad, validar_telefono,
                               validar_habitacion, sanitizar_texto)
from utils.formatters import formato_fecha
from utils.logger import log_info, log_error, Auditoria


# Reusar la función de apertura de workbook del módulo V1
from modules.import_excel import _abrir_workbook


class ImportExcelV2Module(ctk.CTkFrame):
    """Módulo para importar datos desde archivos Excel en formato tabular V2."""

    def __init__(self, parent, usuario: dict):
        super().__init__(parent, fg_color="transparent")

        self.usuario = usuario
        self.archivos_seleccionados = []
        self.datos_preview = []
        self.mapeo_columnas = {}  # Mapeo detectado automáticamente
        self.hoteles = []

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
        """Crea la interfaz del módulo de importación V2."""
        # --- Sección superior: selección de hotel + archivos ---
        top_frame = ctk.CTkFrame(self, fg_color=COLORS["bg_card"], corner_radius=10)
        top_frame.pack(fill="x", pady=(0, 10))

        # Título
        header = ctk.CTkFrame(top_frame, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=(15, 10))

        ctk.CTkLabel(
            header,
            text="📋 Importar Excel - Formato Tabular",
            font=obtener_fuente("heading"),
            anchor="w"
        ).pack(side="left")

        # Selector de hotel
        hotel_frame = ctk.CTkFrame(top_frame, fg_color="transparent")
        hotel_frame.pack(fill="x", padx=20, pady=(0, 5))
        hotel_frame.grid_columnconfigure(1, weight=1)

        nombres_hoteles = [h["nombre"] for h in self.hoteles] if self.hoteles else []
        self.input_hotel = InputConLabel(
            hotel_frame, "Hotel destino", "Seleccione el hotel para estos datos",
            obligatorio=True, tipo="combo",
            values=[""] + nombres_hoteles
        )
        self.input_hotel.grid(row=0, column=0, columnspan=2, sticky="ew")

        # Opción nuevo hotel
        nuevo_frame = ctk.CTkFrame(top_frame, fg_color="transparent")
        nuevo_frame.pack(fill="x", padx=20, pady=(0, 5))

        self.check_nuevo = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            nuevo_frame, text="Registrar nuevo hotel",
            variable=self.check_nuevo,
            command=self._toggle_nuevo_hotel,
            font=obtener_fuente("small")
        ).pack(anchor="w")

        self.frame_nuevo_hotel = ctk.CTkFrame(top_frame, fg_color="transparent")

        nuevo_inner = ctk.CTkFrame(self.frame_nuevo_hotel, fg_color="transparent")
        nuevo_inner.pack(fill="x", padx=20, pady=5)
        nuevo_inner.grid_columnconfigure((0, 1, 2), weight=1)

        self.input_nro_orden = InputConLabel(
            nuevo_inner, "Nro. Orden", "Número de orden"
        )
        self.input_nro_orden.grid(row=0, column=0, sticky="ew", padx=(0, 10))

        self.input_direccion = InputConLabel(
            nuevo_inner, "Dirección", "Dirección del hotel"
        )
        self.input_direccion.grid(row=0, column=1, sticky="ew", padx=(0, 10))

        self.input_ciudad = InputConLabel(
            nuevo_inner, "Ciudad/Localidad", "Ciudad o localidad", obligatorio=True
        )
        self.input_ciudad.grid(row=0, column=2, sticky="ew")

        # Botones de selección de archivo
        file_frame = ctk.CTkFrame(top_frame, fg_color="transparent")
        file_frame.pack(fill="x", padx=20, pady=(5, 5))

        ctk.CTkButton(
            file_frame, text="📂 Seleccionar archivos",
            font=obtener_fuente("button"),
            height=38,
            command=self._seleccionar_archivos
        ).pack(side="left", padx=(0, 5))

        ctk.CTkButton(
            file_frame, text="🗂️ Seleccionar carpeta",
            font=obtener_fuente("button"),
            height=38,
            fg_color=COLORS["secondary"],
            hover_color=COLORS["secondary_hover"],
            command=self._seleccionar_carpeta
        ).pack(side="left", padx=5)

        self.label_archivos = ctk.CTkLabel(
            top_frame,
            text="No se han seleccionado archivos",
            font=obtener_fuente("small"),
            text_color=COLORS["text_secondary"],
            anchor="w",
            wraplength=900
        )
        self.label_archivos.pack(fill="x", padx=20, pady=(0, 5))

        # Info de columnas detectadas
        self.label_columnas = ctk.CTkLabel(
            top_frame,
            text="",
            font=obtener_fuente("small"),
            text_color=COLORS["primary_light"],
            anchor="w",
            wraplength=900
        )
        self.label_columnas.pack(fill="x", padx=20, pady=(0, 15))

        # --- Sección media: vista previa ---
        preview_frame = ctk.CTkFrame(self, fg_color=COLORS["bg_card"], corner_radius=10)
        preview_frame.pack(fill="both", expand=True, pady=(0, 10))

        prev_header = ctk.CTkFrame(preview_frame, fg_color="transparent")
        prev_header.pack(fill="x", padx=20, pady=(15, 10))

        ctk.CTkLabel(
            prev_header, text="Vista previa de datos",
            font=obtener_fuente("heading"),
            anchor="w"
        ).pack(side="left")

        self.label_conteo = ctk.CTkLabel(
            prev_header, text="",
            font=obtener_fuente("small"),
            text_color=COLORS["text_secondary"]
        )
        self.label_conteo.pack(side="right")

        # Tabla de huéspedes con las 13 columnas del formato V2
        self.tabla_huesped = TablaScrollable(
            preview_frame,
            columnas=[
                {"id": "fecha_entrada", "texto": "Fecha", "ancho": 90},
                {"id": "habitacion", "texto": "Hab.", "ancho": 55},
                {"id": "apellido_nombre", "texto": "Nombre y Apellido", "ancho": 170},
                {"id": "edad", "texto": "Edad", "ancho": 50},
                {"id": "nacionalidad", "texto": "Nacionalidad", "ancho": 90},
                {"id": "profesion", "texto": "Profesión", "ancho": 100},
                {"id": "procedencia", "texto": "Procede", "ancho": 100},
                {"id": "domicilio", "texto": "Domicilio", "ancho": 140},
                {"id": "destino", "texto": "Destino", "ancho": 90},
                {"id": "dni_pasaporte", "texto": "Doc", "ancho": 90},
                {"id": "fecha_salida", "texto": "Salida", "ancho": 90},
                {"id": "movilidad", "texto": "Movilidad", "ancho": 70},
                {"id": "telefono", "texto": "Teléfono", "ancho": 100},
            ],
            altura=12
        )
        self.tabla_huesped.pack(fill="both", expand=True, padx=20, pady=(0, 15))

        # --- Sección inferior: barra de progreso + botones ---
        bottom_frame = ctk.CTkFrame(self, fg_color=COLORS["bg_card"], corner_radius=10)
        bottom_frame.pack(fill="x")

        self.barra_progreso = BarraProgreso(bottom_frame, "Esperando datos...")
        self.barra_progreso.pack(fill="x", padx=20, pady=(15, 10))

        self.label_errores = ctk.CTkLabel(
            bottom_frame, text="",
            font=obtener_fuente("small"),
            text_color=COLORS["warning"],
            anchor="w",
            wraplength=700
        )
        self.label_errores.pack(fill="x", padx=20, pady=(0, 5))

        action_frame = ctk.CTkFrame(bottom_frame, fg_color="transparent")
        action_frame.pack(fill="x", padx=20, pady=(0, 15))

        self.btn_importar = ctk.CTkButton(
            action_frame, text="✅ Importar datos",
            font=obtener_fuente("button"),
            height=42,
            fg_color=COLORS["success"],
            hover_color="#388E3C",
            state="disabled",
            command=self._importar_datos
        )
        self.btn_importar.pack(side="right", padx=5)

        self.btn_limpiar = ctk.CTkButton(
            action_frame, text="🗑️ Limpiar",
            font=obtener_fuente("button"),
            height=42,
            fg_color=COLORS["error"],
            hover_color="#C62828",
            command=self._limpiar
        )
        self.btn_limpiar.pack(side="right", padx=5)

    def _toggle_nuevo_hotel(self):
        """Muestra/oculta los campos de nuevo hotel."""
        if self.check_nuevo.get():
            self.frame_nuevo_hotel.pack(fill="x", after=self.check_nuevo.get.__self__
                                         if hasattr(self.check_nuevo.get, '__self__') else None)
            # Insertar después del checkbox
            try:
                self.frame_nuevo_hotel.pack(fill="x")
            except Exception:
                pass
            self.input_hotel.entry.configure(state="normal")
        else:
            self.frame_nuevo_hotel.pack_forget()

    def _seleccionar_archivos(self):
        """Abre diálogo para seleccionar archivos Excel."""
        archivos = filedialog.askopenfilenames(
            title="Seleccionar archivos Excel (formato tabular)",
            filetypes=[("Archivos Excel", "*.xlsx *.xls"), ("Todos", "*.*")]
        )
        if archivos:
            self.archivos_seleccionados = list(archivos)
            self._mostrar_archivos()
            self._procesar_archivos()

    def _seleccionar_carpeta(self):
        """Abre diálogo para seleccionar carpeta con archivos Excel."""
        carpeta = filedialog.askdirectory(title="Seleccionar carpeta con archivos Excel")
        if carpeta:
            archivos = []
            for f in os.listdir(carpeta):
                if f.lower().endswith(('.xlsx', '.xls')) and not f.startswith('~'):
                    archivos.append(os.path.join(carpeta, f))
            if archivos:
                self.archivos_seleccionados = archivos
                self._mostrar_archivos()
                self._procesar_archivos()
            else:
                mostrar_advertencia(self, "Sin archivos",
                                    "No se encontraron archivos Excel en la carpeta seleccionada.")

    def _mostrar_archivos(self):
        """Muestra los archivos seleccionados en la UI."""
        nombres = [os.path.basename(f) for f in self.archivos_seleccionados]
        if len(nombres) > 5:
            texto = ", ".join(nombres[:5]) + f" y {len(nombres) - 5} más..."
        else:
            texto = ", ".join(nombres)
        self.label_archivos.configure(
            text=f"📁 {len(nombres)} archivo(s): {texto}",
            text_color=COLORS["text_primary"]
        )

    def _detectar_encabezados(self, hoja) -> dict:
        """Detecta automáticamente la posición de las columnas leyendo los encabezados de fila 1.
        Retorna un dict {campo_interno: letra_columna}."""
        mapeo = {}
        # Escanear columnas A-Z en la fila 1
        for col_idx in range(26):
            letra = chr(ord('A') + col_idx)
            try:
                celda = hoja[f"{letra}1"]
                valor = celda.value
                if valor is None:
                    continue
                texto = str(valor).strip().lower()
                # Quitar acentos comunes para matching
                texto_limpio = texto.replace("á", "a").replace("é", "e").replace("í", "i")\
                                     .replace("ó", "o").replace("ú", "u").replace("ñ", "n")

                # Buscar en aliases
                if texto in EXCEL_V2_HEADER_ALIASES:
                    campo = EXCEL_V2_HEADER_ALIASES[texto]
                    if campo not in mapeo:
                        mapeo[campo] = letra
                elif texto_limpio in EXCEL_V2_HEADER_ALIASES:
                    campo = EXCEL_V2_HEADER_ALIASES[texto_limpio]
                    if campo not in mapeo:
                        mapeo[campo] = letra
            except Exception:
                continue

        return mapeo

    def _procesar_archivos(self):
        """Procesa los archivos Excel seleccionados en un hilo secundario."""
        self.datos_preview = []

        self.barra_progreso.actualizar(0, "Procesando archivos...")
        self._set_botones_estado("disabled")

        archivos = list(self.archivos_seleccionados)

        def tarea():
            datos_preview = []
            errores = []
            total_hojas = 0
            mapeo_columnas = {}

            for idx, archivo in enumerate(archivos):
                try:
                    wb = _abrir_workbook(archivo)
                    nombre_archivo = os.path.basename(archivo)

                    for hoja_nombre in wb.sheetnames:
                        hoja = wb[hoja_nombre]
                        total_hojas += 1

                        mapeo_detectado = self._detectar_encabezados(hoja)

                        if not mapeo_detectado or len(mapeo_detectado) < 3:
                            mapeo_detectado = dict(EXCEL_V2_HUESPED_COLS)
                            log_info(f"Usando mapeo por defecto para {nombre_archivo}/{hoja_nombre}")
                        else:
                            log_info(f"Encabezados detectados en {nombre_archivo}/{hoja_nombre}: "
                                     f"{list(mapeo_detectado.keys())}")

                        mapeo_columnas = mapeo_detectado

                        huespedes = self._leer_huespedes(hoja, mapeo_detectado, nombre_archivo, hoja_nombre)
                        datos_preview.extend(huespedes)

                    wb.close()

                except Exception as e:
                    error_msg = f"Error en '{nombre_archivo}': {str(e)}"
                    errores.append(error_msg)
                    log_error(error_msg, e)

                progreso = (idx + 1) / len(archivos)
                self.after(0, lambda p=progreso, i=idx: self.barra_progreso.actualizar(
                    p, f"Procesando {i + 1}/{len(archivos)} archivos..."
                ))

            self.after(0, lambda: self._procesar_archivos_completado(
                datos_preview, errores, total_hojas, mapeo_columnas
            ))

        threading.Thread(target=tarea, daemon=True).start()

    def _set_botones_estado(self, estado: str):
        """Habilita o deshabilita los botones de acción."""
        try:
            for widget in self.winfo_children():
                self._set_botones_recursivo(widget, estado)
        except Exception:
            pass

    def _set_botones_recursivo(self, widget, estado: str):
        """Recursivamente establece el estado de botones CTkButton."""
        try:
            if isinstance(widget, ctk.CTkButton):
                widget.configure(state=estado)
            for child in widget.winfo_children():
                self._set_botones_recursivo(child, estado)
        except Exception:
            pass

    def _procesar_archivos_completado(self, datos_preview, errores, total_hojas, mapeo_columnas):
        """Callback en el hilo principal con los resultados del procesamiento."""
        self.datos_preview = datos_preview
        self.mapeo_columnas = mapeo_columnas

        if self.mapeo_columnas:
            cols_detectadas = [f"{k}={v}" for k, v in sorted(self.mapeo_columnas.items(),
                                                              key=lambda x: x[1])]
            self.label_columnas.configure(
                text=f"🔍 Columnas detectadas: {', '.join(cols_detectadas)}"
            )

        self.barra_progreso.completar(
            f"Procesado: {len(self.archivos_seleccionados)} archivos, "
            f"{total_hojas} hojas, {len(self.datos_preview)} huéspedes encontrados"
        )

        self.tabla_huesped.cargar_datos([
            (formato_fecha(h.get("fecha_entrada")),
             str(h.get("habitacion", "")),
             h.get("apellido_nombre", ""),
             str(h.get("edad", "")),
             h.get("nacionalidad", ""),
             h.get("profesion", ""),
             h.get("procedencia", ""),
             h.get("domicilio", ""),
             h.get("destino", ""),
             h.get("dni_pasaporte", ""),
             formato_fecha(h.get("fecha_salida")),
             h.get("movilidad", ""),
             h.get("telefono", ""))
            for h in self.datos_preview
        ])

        self.label_conteo.configure(
            text=f"{len(self.datos_preview)} huéspedes detectados"
        )

        if errores:
            self.label_errores.configure(text="⚠ " + " | ".join(errores[:3]))
        else:
            self.label_errores.configure(text="")

        self._set_botones_estado("normal")
        if self.datos_preview:
            self.btn_importar.configure(state="normal")
        else:
            self.btn_importar.configure(state="disabled")

    def _valor_celda(self, hoja, columna: str, fila: int):
        """Obtiene el valor de una celda específica."""
        try:
            celda = hoja[f"{columna}{fila}"]
            valor = celda.value
            if isinstance(valor, str) and valor.strip() == "":
                return None
            return valor
        except (KeyError, IndexError, AttributeError):
            return None
        except Exception:
            return None

    def _fila_tiene_datos(self, hoja, fila: int, mapeo: dict) -> bool:
        """Verifica si una fila tiene datos en al menos una columna mapeada."""
        for col in mapeo.values():
            valor = self._valor_celda(hoja, col, fila)
            if valor is not None and str(valor).strip() != "":
                return True
        return False

    def _detectar_fila_inicio(self, hoja, mapeo: dict) -> int:
        """Detecta la fila donde comienzan los datos reales (después de encabezados)."""
        # Palabras clave de encabezados que NO son datos
        encabezados = {
            "fecha", "habitacion", "habitación", "nombre", "apellido",
            "nombre y apellido", "apellido y nombre", "edad", "nacionalidad",
            "profesion", "profesión", "procede", "procedencia", "domicilio",
            "destino", "doc", "documento", "dni", "salida", "movilidad",
            "telefono", "teléfono", "entrada", "ocupacion", "ocupación",
        }

        columna_nombre = mapeo.get("apellido_nombre", "C")

        for fila in range(1, 20):
            valor = self._valor_celda(hoja, columna_nombre, fila)
            if valor is not None:
                texto = str(valor).strip().lower()
                if texto and texto not in encabezados and len(texto) > 1:
                    return fila

        return EXCEL_V2_HUESPED_START_ROW

    def _obtener_max_fila(self, hoja) -> int:
        """Obtiene la última fila con datos en la hoja."""
        if hasattr(hoja, 'max_row') and hoja.max_row:
            return hoja.max_row
        if hasattr(hoja, '_sheet') and hasattr(hoja._sheet, 'nrows'):
            return hoja._sheet.nrows
        return 10000

    def _leer_huespedes(self, hoja, mapeo: dict, nombre_archivo: str, hoja_nombre: str) -> list:
        """Lee los datos de huéspedes usando el mapeo de columnas detectado."""
        huespedes = []

        fila = self._detectar_fila_inicio(hoja, mapeo)
        max_fila = self._obtener_max_fila(hoja)
        filas_vacias_consecutivas = 0
        MAX_FILAS_VACIAS = 15

        while fila <= max_fila + MAX_FILAS_VACIAS:
            if not self._fila_tiene_datos(hoja, fila, mapeo):
                filas_vacias_consecutivas += 1
                if filas_vacias_consecutivas >= MAX_FILAS_VACIAS:
                    break
                fila += 1
                continue

            filas_vacias_consecutivas = 0

            # Leer nombre - campo clave
            col_nombre = mapeo.get("apellido_nombre", "C")
            apellido = self._valor_celda(hoja, col_nombre, fila)

            # Si no hay nombre, intentar con DNI
            if not apellido or str(apellido).strip() == "":
                col_dni = mapeo.get("dni_pasaporte", "J")
                dni_val = self._valor_celda(hoja, col_dni, fila)
                if not dni_val or str(dni_val).strip() == "":
                    fila += 1
                    continue

            try:
                # Leer fecha de entrada
                fe_raw = self._valor_celda(hoja, mapeo.get("fecha_entrada", "A"), fila) if "fecha_entrada" in mapeo else None
                _, _, fecha_entrada = validar_fecha(fe_raw, permite_vacio=True)

                # Leer fecha de salida
                fs_raw = self._valor_celda(hoja, mapeo.get("fecha_salida", "K"), fila) if "fecha_salida" in mapeo else None
                _, _, fecha_salida = validar_fecha(fs_raw, permite_vacio=True)

                # Leer edad
                edad_raw = self._valor_celda(hoja, mapeo.get("edad", "D"), fila) if "edad" in mapeo else None
                _, _, edad = validar_edad(edad_raw)

                # Leer habitación
                hab_raw = self._valor_celda(hoja, mapeo.get("habitacion", "B"), fila) if "habitacion" in mapeo else None
                _, _, habitacion = validar_habitacion(hab_raw)

                # Leer teléfono
                tel_raw = self._valor_celda(hoja, mapeo.get("telefono", "M"), fila) if "telefono" in mapeo else None
                _, _, telefono = validar_telefono(tel_raw)

                # Leer DNI
                dni_raw = self._valor_celda(hoja, mapeo.get("dni_pasaporte", "J"), fila) if "dni_pasaporte" in mapeo else None
                dni_str = sanitizar_texto(str(dni_raw)) if dni_raw else ""
                # Limpiar .0 de DNIs numéricos
                if dni_str.endswith('.0'):
                    dni_str = dni_str[:-2]

                huesped = {
                    "archivo": f"{nombre_archivo}/{hoja_nombre}",
                    "fecha_entrada": fecha_entrada,
                    "habitacion": habitacion,
                    "apellido_nombre": sanitizar_texto(str(apellido)) if apellido else "",
                    "edad": edad,
                    "nacionalidad": sanitizar_texto(
                        str(self._valor_celda(hoja, mapeo.get("nacionalidad", "E"), fila) or ""))
                        if "nacionalidad" in mapeo else "",
                    "profesion": sanitizar_texto(
                        str(self._valor_celda(hoja, mapeo.get("profesion", "F"), fila) or ""))
                        if "profesion" in mapeo else "",
                    "procedencia": sanitizar_texto(
                        str(self._valor_celda(hoja, mapeo.get("procedencia", "G"), fila) or ""))
                        if "procedencia" in mapeo else "",
                    "domicilio": sanitizar_texto(
                        str(self._valor_celda(hoja, mapeo.get("domicilio", "H"), fila) or ""))
                        if "domicilio" in mapeo else "",
                    "destino": sanitizar_texto(
                        str(self._valor_celda(hoja, mapeo.get("destino", "I"), fila) or ""))
                        if "destino" in mapeo else "",
                    "dni_pasaporte": dni_str,
                    "fecha_salida": fecha_salida,
                    "movilidad": sanitizar_texto(
                        str(self._valor_celda(hoja, mapeo.get("movilidad", "L"), fila) or ""))
                        if "movilidad" in mapeo else "",
                    "telefono": telefono,
                }
                huespedes.append(normalizar_huesped_geografia(huesped))

            except Exception as e:
                log_error(f"Error leyendo huésped en fila {fila} de {nombre_archivo}", e)

            fila += 1

        return huespedes

    def _importar_datos(self):
        """Importa los datos procesados a la base de datos en un hilo secundario."""
        if not self.datos_preview:
            mostrar_advertencia(self, "Sin datos", "No hay datos para importar.")
            return

        hotel_nombre = self.input_hotel.get()
        if not hotel_nombre:
            mostrar_advertencia(self, "Hotel requerido",
                                "Debe seleccionar o registrar un hotel antes de importar.")
            return

        if not confirmar(self, "Confirmar importación",
                         f"Se importarán {len(self.datos_preview)} registros\n"
                         f"al hotel: {hotel_nombre}\n\n¿Desea continuar?"):
            return

        self.btn_importar.configure(state="disabled", text="Importando...")
        self.btn_limpiar.configure(state="disabled")
        self.barra_progreso.actualizar(0, "Importando datos a la base de datos...")

        datos = list(self.datos_preview)
        archivos = list(self.archivos_seleccionados)
        usuario_id = self.usuario["id"]
        es_nuevo = self.check_nuevo.get()
        nro_orden = sanitizar_texto(self.input_nro_orden.get()) if es_nuevo else ""
        direccion = sanitizar_texto(self.input_direccion.get()) if es_nuevo else ""
        ciudad = sanitizar_texto(self.input_ciudad.get()) if es_nuevo else ""

        def tarea():
            importados = 0
            errores = 0
            duplicados = 0
            error_general = None

            try:
                conn = db.obtener_conexion()
                if not conn:
                    self.after(0, lambda: mostrar_error(self, "Error de conexión",
                                  "No se pudo conectar a la base de datos."))
                    return

                cursor = conn.cursor()

                # Obtener o crear hotel
                if es_nuevo:
                    cursor.execute("""
                        INSERT INTO hoteles (nombre, nro_orden, direccion, ciudad_localidad, usuario_registro_id)
                        VALUES (%s, %s, %s, %s, %s) RETURNING id
                    """, (
                        sanitizar_texto(hotel_nombre),
                        nro_orden,
                        direccion,
                        ciudad,
                        usuario_id
                    ))
                    hotel_id = cursor.fetchone()[0]
                else:
                    cursor.execute(
                        "SELECT id FROM hoteles WHERE LOWER(nombre) = LOWER(%s)", (hotel_nombre,)
                    )
                    resultado = cursor.fetchone()
                    if resultado:
                        hotel_id = resultado[0]
                    else:
                        cursor.execute("""
                            INSERT INTO hoteles (nombre, usuario_registro_id)
                            VALUES (%s, %s) RETURNING id
                        """, (sanitizar_texto(hotel_nombre), usuario_id))
                        hotel_id = cursor.fetchone()[0]

                for i, huesped in enumerate(datos):
                    try:
                        if self._es_duplicado(cursor, hotel_id, huesped):
                            duplicados += 1
                            continue

                        cursor.execute("""
                            INSERT INTO huespedes (
                                hotel_id, nacionalidad, procedencia, apellido_nombre,
                                dni_pasaporte, edad, profesion,
                                fecha_entrada, fecha_salida,
                                habitacion, domicilio, destino, movilidad, telefono,
                                origen_carga, usuario_carga_id
                            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'excel_v2', %s)
                        """, (
                            hotel_id,
                            huesped.get("nacionalidad", ""),
                            huesped.get("procedencia", ""),
                            huesped.get("apellido_nombre", ""),
                            huesped.get("dni_pasaporte", ""),
                            huesped.get("edad"),
                            huesped.get("profesion", ""),
                            huesped.get("fecha_entrada"),
                            huesped.get("fecha_salida"),
                            huesped.get("habitacion", ""),
                            huesped.get("domicilio", ""),
                            huesped.get("destino", ""),
                            huesped.get("movilidad", ""),
                            huesped.get("telefono", ""),
                            usuario_id
                        ))
                        importados += 1

                    except Exception as e:
                        errores += 1
                        log_error(f"Error importando: {huesped.get('apellido_nombre', '?')}", e)

                    if (i + 1) % 10 == 0 or i == len(datos) - 1:
                        progreso = (i + 1) / len(datos)
                        self.after(0, lambda p=progreso, n=i+1: self.barra_progreso.actualizar(
                            p, f"Importando {n}/{len(datos)}..."
                        ))

                for archivo in archivos:
                    cursor.execute("""
                        INSERT INTO importaciones_log (
                            archivo_nombre, fecha_importacion, usuario_id,
                            registros_importados, registros_error, registros_duplicados,
                            estado, detalle
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        os.path.basename(archivo),
                        datetime.now(),
                        usuario_id,
                        importados,
                        errores,
                        duplicados,
                        "completado" if errores == 0 else "parcial",
                        "Formato tabular V2"
                    ))

                conn.commit()
                cursor.close()
                db.liberar_conexion(conn)

                try:
                    conn_aud = db.obtener_conexion()
                    if conn_aud:
                        auditoria = Auditoria(conn_aud)
                        auditoria.registrar(
                            usuario_id,
                            "importar_excel_v2",
                            "huespedes",
                            detalle=f"Formato tabular - Importados: {importados}, "
                                    f"Errores: {errores}, Duplicados: {duplicados}"
                        )
                        db.liberar_conexion(conn_aud)
                except Exception:
                    pass

            except Exception as e:
                log_error("Error general en importación V2", e)
                error_general = str(e)

            self.after(0, lambda: self._importar_completado(importados, errores, duplicados, error_general))

        threading.Thread(target=tarea, daemon=True).start()

    def _importar_completado(self, importados, errores, duplicados, error_general):
        """Callback en el hilo principal con los resultados de la importación."""
        self.btn_importar.configure(state="normal", text="✅ Importar datos")
        self.btn_limpiar.configure(state="normal")

        if error_general:
            mostrar_error(self, "Error de importación",
                          f"Ocurrió un error durante la importación:\n{error_general}")
            return

        self.barra_progreso.completar(
            f"Importación completada: {importados} importados, "
            f"{duplicados} duplicados, {errores} errores"
        )

        mensaje = (f"Importación completada:\n\n"
                   f"✅ Importados: {importados}\n"
                   f"⚠️ Duplicados omitidos: {duplicados}\n"
                   f"❌ Errores: {errores}")

        if errores == 0:
            mostrar_exito(self, "Importación exitosa", mensaje)
        else:
            mostrar_advertencia(self, "Importación parcial", mensaje)

        log_info(f"Importación Excel V2: {importados} importados, "
                 f"{duplicados} duplicados, {errores} errores")

        # Refrescar lista de hoteles para el combo
        self._cargar_hoteles()
        nombres_hoteles = [h["nombre"] for h in self.hoteles] if self.hoteles else []
        self.input_hotel.entry.configure(values=[""] + nombres_hoteles)

    def _obtener_o_crear_hotel(self, cursor, hotel_nombre: str) -> int:
        """Obtiene el ID de un hotel existente o lo crea si es nuevo."""
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
            return cursor.fetchone()[0]
        else:
            cursor.execute(
                "SELECT id FROM hoteles WHERE LOWER(nombre) = LOWER(%s)", (hotel_nombre,)
            )
            resultado = cursor.fetchone()
            if resultado:
                return resultado[0]
            # Crear si no existe
            cursor.execute("""
                INSERT INTO hoteles (nombre, usuario_registro_id)
                VALUES (%s, %s) RETURNING id
            """, (sanitizar_texto(hotel_nombre), self.usuario["id"]))
            return cursor.fetchone()[0]

    def _es_duplicado(self, cursor, hotel_id: int, huesped: dict) -> bool:
        """Verifica si un huésped ya existe (mismo DNI + hotel + fecha entrada)."""
        dni = huesped.get("dni_pasaporte", "")
        fecha_entrada = huesped.get("fecha_entrada")

        if not dni or not fecha_entrada:
            return False

        cursor.execute("""
            SELECT id FROM huespedes
            WHERE hotel_id = %s AND dni_pasaporte = %s AND fecha_entrada = %s
        """, (hotel_id, dni, fecha_entrada))

        return cursor.fetchone() is not None

    def _limpiar(self):
        """Limpia todos los datos y resetea la interfaz."""
        self.archivos_seleccionados = []
        self.datos_preview = []
        self.mapeo_columnas = {}
        self.tabla_huesped.limpiar()
        self.label_archivos.configure(
            text="No se han seleccionado archivos",
            text_color=COLORS["text_secondary"]
        )
        self.label_conteo.configure(text="")
        self.label_errores.configure(text="")
        self.label_columnas.configure(text="")
        self.barra_progreso.actualizar(0, "Esperando datos...")
        self.btn_importar.configure(state="disabled")
