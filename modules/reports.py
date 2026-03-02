"""
S.C.A.H. - Módulo de Reportes
Generación de reportes en Excel y PDF, exportación de datos
"""

import customtkinter as ctk
from datetime import datetime
from tkinter import filedialog

from database.connection import db
from ui.themes import COLORS, obtener_fuente
from ui.dialogs import mostrar_exito, mostrar_error, mostrar_advertencia
from utils.formatters import formato_nombre_archivo, formato_fecha
from utils.logger import log_info, log_error, Auditoria


def exportar_a_excel(datos: list, archivo: str, titulo: str = "Datos"):
    """
    Exporta una lista de diccionarios a un archivo Excel .xlsx.
    Compatible con el import desde search.py.
    
    Args:
        datos: Lista de dicts con los datos
        archivo: Ruta del archivo de salida
        titulo: Título de la hoja
    """
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = titulo[:31]  # Máximo 31 caracteres en nombre de hoja

    if not datos:
        ws["A1"] = "Sin datos para exportar"
        wb.save(archivo)
        return

    # Estilos
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="1565C0", end_color="1565C0", fill_type="solid")
    header_align = Alignment(horizontal="center", vertical="center", wrap_text=True)
    thin_border = Border(
        left=Side(style="thin"), right=Side(style="thin"),
        top=Side(style="thin"), bottom=Side(style="thin")
    )
    alt_fill = PatternFill(start_color="E3F2FD", end_color="E3F2FD", fill_type="solid")

    # Título del reporte
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=len(datos[0]))
    title_cell = ws.cell(row=1, column=1, value=f"S.C.A.H. - {titulo}")
    title_cell.font = Font(name="Calibri", size=14, bold=True, color="1565C0")
    title_cell.alignment = Alignment(horizontal="center", vertical="center")

    # Fecha de generación
    ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=len(datos[0]))
    date_cell = ws.cell(row=2, column=1,
                        value=f"Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    date_cell.font = Font(name="Calibri", size=9, italic=True, color="666666")
    date_cell.alignment = Alignment(horizontal="center")

    # Mapping de columnas para nombres legibles
    column_names = {
        "id": "ID",
        "apellido_nombre": "Nombre y Apellido",
        "dni_pasaporte": "DNI/Pasaporte",
        "nacionalidad": "Nacionalidad",
        "procedencia": "Procedencia",
        "profesion_ocupacion": "Profesión",
        "edad": "Edad",
        "fecha_nacimiento": "Fecha Nac.",
        "fecha_entrada": "Entrada",
        "fecha_salida": "Salida",
        "hotel": "Hotel",
        "nombre": "Nombre",
        "hotel_nombre": "Hotel",
        "ciudad_localidad": "Ciudad",
        "direccion": "Dirección",
        "nro_orden": "Nro. Orden",
        "total": "Total",
        "username": "Usuario",
        "rol": "Rol",
        "ultimo_acceso": "Último Acceso",
        "fecha_registro": "Fecha Registro",
        "habitacion": "Habitación",
        "domicilio": "Domicilio",
        "destino": "Destino",
        "movilidad": "Movilidad",
        "telefono": "Teléfono",
    }

    # Headers
    columnas = list(datos[0].keys())
    for col_idx, col in enumerate(columnas, 1):
        cell = ws.cell(row=4, column=col_idx, value=column_names.get(col, col.title()))
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_align
        cell.border = thin_border

    # Datos
    for row_idx, fila in enumerate(datos, 5):
        for col_idx, col in enumerate(columnas, 1):
            valor = fila.get(col, "")
            # Formatear fechas
            if hasattr(valor, 'strftime'):
                valor = valor.strftime("%d/%m/%Y")
            elif valor is None:
                valor = ""

            cell = ws.cell(row=row_idx, column=col_idx, value=valor)
            cell.border = thin_border
            cell.font = Font(name="Calibri", size=10)

            if (row_idx - 5) % 2 == 1:
                cell.fill = alt_fill

    # Ajustar anchos
    for col_idx, col in enumerate(columnas, 1):
        max_len = len(column_names.get(col, col))
        for fila in datos[:100]:
            val = str(fila.get(col, ""))
            if len(val) > max_len:
                max_len = len(val)
        ws.column_dimensions[openpyxl.utils.get_column_letter(col_idx)].width = min(max_len + 4, 40)

    # Fila de totales
    total_row = len(datos) + 5
    ws.cell(row=total_row, column=1, value=f"Total de registros: {len(datos)}")
    ws.cell(row=total_row, column=1).font = Font(name="Calibri", size=10, bold=True)

    wb.save(archivo)
    log_info(f"Excel exportado: {archivo} ({len(datos)} registros)")


def generar_pdf(datos: list, archivo: str, titulo: str = "Reporte",
                columnas_mostrar: list = None):
    """
    Genera un reporte PDF con los datos proporcionados.
    
    Args:
        datos: Lista de dicts con los datos
        archivo: Ruta del archivo PDF
        titulo: Título del reporte
        columnas_mostrar: Lista de keys a incluir (None = todas)
    """
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib import colors
    from reportlab.lib.units import mm
    from reportlab.platypus import (SimpleDocTemplate, Table, TableStyle,
                                     Paragraph, Spacer)
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

    doc = SimpleDocTemplate(
        archivo, pagesize=landscape(A4),
        leftMargin=15*mm, rightMargin=15*mm,
        topMargin=15*mm, bottomMargin=15*mm
    )

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name="TituloReporte",
        parent=styles["Title"],
        fontSize=16,
        textColor=colors.HexColor("#1565C0"),
        spaceAfter=5
    ))
    styles.add(ParagraphStyle(
        name="SubTitulo",
        parent=styles["Normal"],
        fontSize=9,
        textColor=colors.HexColor("#666666"),
        spaceAfter=15
    ))
    styles.add(ParagraphStyle(
        name="CellText",
        parent=styles["Normal"],
        fontSize=7,
        leading=9
    ))

    elements = []

    # Encabezado
    elements.append(Paragraph(f"S.C.A.H. - {titulo}", styles["TituloReporte"]))
    elements.append(Paragraph(
        f"Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')} | "
        f"Total registros: {len(datos)}",
        styles["SubTitulo"]
    ))

    if not datos:
        elements.append(Paragraph("No hay datos para mostrar", styles["Normal"]))
        doc.build(elements)
        return

    # Mapping de nombres
    column_names = {
        "apellido_nombre": "Nombre",
        "dni_pasaporte": "DNI/Pasap.",
        "nacionalidad": "Nacionalidad",
        "procedencia": "Procedencia",
        "profesion_ocupacion": "Profesión",
        "edad": "Edad",
        "fecha_entrada": "Entrada",
        "fecha_salida": "Salida",
        "hotel": "Hotel",
        "nombre": "Nombre",
        "hotel_nombre": "Hotel",
        "ciudad_localidad": "Ciudad",
        "habitacion": "Habitación",
        "domicilio": "Domicilio",
        "destino": "Destino",
        "movilidad": "Movilidad",
        "telefono": "Teléfono",
    }

    # Determinar columnas
    if columnas_mostrar:
        cols = [c for c in columnas_mostrar if c in datos[0]]
    else:
        cols = list(datos[0].keys())
        # Omitir ID si hay más columnas
        if len(cols) > 1 and "id" in cols:
            cols.remove("id")

    # Headers
    headers = [column_names.get(c, c.title()) for c in cols]

    # Datos de tabla
    table_data = [headers]
    for fila in datos:
        row = []
        for c in cols:
            val = fila.get(c, "")
            if hasattr(val, 'strftime'):
                val = val.strftime("%d/%m/%Y")
            elif val is None:
                val = ""
            # Truncar textos largos
            val = str(val)
            if len(val) > 30:
                val = val[:27] + "..."
            row.append(Paragraph(val, styles["CellText"]))
        table_data.append(row)

    # Calcular anchos proporcionales
    available_width = landscape(A4)[0] - 30*mm
    col_width = available_width / len(cols)
    col_widths = [col_width] * len(cols)

    table = Table(table_data, colWidths=col_widths, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1565C0")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 8),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1),
         [colors.white, colors.HexColor("#E3F2FD")]),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CCCCCC")),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))

    elements.append(table)
    doc.build(elements)
    log_info(f"PDF generado: {archivo} ({len(datos)} registros)")


class ReportsModule(ctk.CTkFrame):
    """Módulo para generación y descarga de reportes."""

    def __init__(self, parent, usuario: dict):
        super().__init__(parent, fg_color="transparent")
        self.usuario = usuario
        self._crear_ui()

    def _crear_ui(self):
        """Crea la interfaz de reportes."""
        # Header
        header_card = ctk.CTkFrame(self, fg_color=COLORS["bg_card"], corner_radius=10)
        header_card.pack(fill="x", pady=(0, 15))

        header_inner = ctk.CTkFrame(header_card, fg_color="transparent")
        header_inner.pack(fill="x", padx=20, pady=15)

        ctk.CTkLabel(
            header_inner, text="📄 Generación de Reportes",
            font=obtener_fuente("heading")
        ).pack(side="left")

        # Tipos de reportes
        tipos_card = ctk.CTkFrame(self, fg_color=COLORS["bg_card"], corner_radius=10)
        tipos_card.pack(fill="both", expand=True)

        tipos_inner = ctk.CTkFrame(tipos_card, fg_color="transparent")
        tipos_inner.pack(fill="both", expand=True, padx=20, pady=20)

        reportes = [
            {
                "icon": "📋",
                "titulo": "Listado General de Huéspedes",
                "desc": "Exporta todos los huéspedes registrados con sus datos completos.",
                "command": self._reporte_general
            },
            {
                "icon": "🏨",
                "titulo": "Huéspedes por Hotel",
                "desc": "Genera un reporte agrupado por hotel con todos sus huéspedes.",
                "command": self._reporte_por_hotel
            },
            {
                "icon": "📅",
                "titulo": "Huéspedes por Rango de Fechas",
                "desc": "Filtra huéspedes por fecha de entrada en un período específico.",
                "command": self._reporte_por_fechas
            },
            {
                "icon": "📊",
                "titulo": "Reporte Estadístico",
                "desc": "Resumen con totales por nacionalidad, profesión y procedencia.",
                "command": self._reporte_estadistico
            },
            {
                "icon": "📥",
                "titulo": "Historial de Importaciones",
                "desc": "Registro de todas las importaciones Excel realizadas.",
                "command": self._reporte_importaciones
            },
            {
                "icon": "📝",
                "titulo": "Auditoría del Sistema",
                "desc": "Registro de acciones realizadas por los usuarios.",
                "command": self._reporte_auditoria
            },
        ]

        for i, rep in enumerate(reportes):
            card = ctk.CTkFrame(tipos_inner, fg_color="gray20", corner_radius=8)
            card.pack(fill="x", pady=5)

            left = ctk.CTkFrame(card, fg_color="transparent")
            left.pack(side="left", fill="x", expand=True, padx=15, pady=12)

            ctk.CTkLabel(
                left, text=f"{rep['icon']}  {rep['titulo']}",
                font=obtener_fuente("subtitulo"), anchor="w"
            ).pack(anchor="w")

            ctk.CTkLabel(
                left, text=rep["desc"],
                font=obtener_fuente("small"),
                text_color=COLORS["text_secondary"], anchor="w"
            ).pack(anchor="w")

            btn_frame = ctk.CTkFrame(card, fg_color="transparent")
            btn_frame.pack(side="right", padx=15)

            ctk.CTkButton(
                btn_frame, text="📊 Excel",
                font=obtener_fuente("small_bold"),
                height=32, width=90,
                fg_color="#2E7D32", hover_color="#1B5E20",
                command=lambda cmd=rep["command"]: cmd("excel")
            ).pack(side="left", padx=3, pady=5)

            ctk.CTkButton(
                btn_frame, text="📄 PDF",
                font=obtener_fuente("small_bold"),
                height=32, width=90,
                fg_color="#C62828", hover_color="#B71C1C",
                command=lambda cmd=rep["command"]: cmd("pdf")
            ).pack(side="left", padx=3, pady=5)

    def _obtener_ruta_guardado(self, formato: str, nombre_base: str) -> str:
        """Abre diálogo para seleccionar ruta de guardado."""
        ext = ".xlsx" if formato == "excel" else ".pdf"
        tipo_label = "Excel" if formato == "excel" else "PDF"

        archivo = filedialog.asksaveasfilename(
            title=f"Guardar reporte como {tipo_label}",
            defaultextension=ext,
            initialfile=formato_nombre_archivo(nombre_base) + ext,
            filetypes=[(tipo_label, f"*{ext}")]
        )
        return archivo

    def _exportar(self, datos: list, formato: str, nombre: str, titulo: str,
                   columnas: list = None):
        """Exporta datos según el formato seleccionado."""
        if not datos:
            mostrar_advertencia(self, "Sin datos", "No hay datos para exportar")
            return

        archivo = self._obtener_ruta_guardado(formato, nombre)
        if not archivo:
            return

        try:
            if formato == "excel":
                exportar_a_excel(datos, archivo, titulo)
            else:
                generar_pdf(datos, archivo, titulo, columnas)

            mostrar_exito(self, "Exportado",
                         f"Reporte generado correctamente:\n{archivo}")

            Auditoria.registrar(
                self.usuario["id"], "reporte_generado",
                f"Reporte '{titulo}' en {formato.upper()}: {len(datos)} registros"
            )

        except Exception as e:
            log_error(f"Error al generar reporte {formato}", e)
            mostrar_error(self, "Error", f"Error al generar reporte: {str(e)}")

    def _reporte_general(self, formato: str):
        """Genera reporte general de todos los huéspedes."""
        try:
            datos = db.ejecutar_query("""
                SELECT hu.apellido_nombre, hu.dni_pasaporte, hu.nacionalidad,
                       hu.procedencia, hu.profesion_ocupacion, hu.edad,
                       hu.fecha_entrada, hu.fecha_salida, h.nombre as hotel,
                       h.ciudad_localidad, hu.habitacion, hu.domicilio,
                       hu.destino, hu.movilidad, hu.telefono
                FROM huespedes hu
                LEFT JOIN hoteles h ON hu.hotel_id = h.id
                ORDER BY hu.apellido_nombre
            """, fetch=True)

            self._exportar(
                [dict(d) for d in datos] if datos else [],
                formato, "listado_general", "Listado General de Huéspedes",
                ["apellido_nombre", "dni_pasaporte", "nacionalidad",
                 "procedencia", "profesion_ocupacion", "edad",
                 "fecha_entrada", "fecha_salida", "hotel", "ciudad_localidad",
                 "habitacion", "domicilio", "destino", "movilidad", "telefono"]
            )
        except Exception as e:
            log_error("Error en reporte general", e)
            mostrar_error(self, "Error", str(e))

    def _reporte_por_hotel(self, formato: str):
        """Genera reporte de huéspedes agrupado por hotel."""
        try:
            datos = db.ejecutar_query("""
                SELECT h.nombre as hotel, h.ciudad_localidad,
                       hu.apellido_nombre, hu.dni_pasaporte, hu.nacionalidad,
                       hu.profesion_ocupacion, hu.edad,
                       hu.fecha_entrada, hu.fecha_salida,
                       hu.habitacion, hu.telefono
                FROM huespedes hu
                JOIN hoteles h ON hu.hotel_id = h.id
                ORDER BY h.nombre, hu.apellido_nombre
            """, fetch=True)

            self._exportar(
                [dict(d) for d in datos] if datos else [],
                formato, "huespedes_por_hotel", "Huéspedes por Hotel",
                ["hotel", "ciudad_localidad", "apellido_nombre",
                 "dni_pasaporte", "nacionalidad", "fecha_entrada", "fecha_salida",
                 "habitacion", "telefono"]
            )
        except Exception as e:
            log_error("Error en reporte por hotel", e)
            mostrar_error(self, "Error", str(e))

    def _reporte_por_fechas(self, formato: str):
        """Genera reporte filtrado por rango de fechas."""
        # Ventana para seleccionar fechas
        ventana = ctk.CTkToplevel(self)
        ventana.title("Seleccionar Rango de Fechas")
        ventana.geometry("400x250")
        ventana.resizable(False, False)
        ventana.grab_set()
        ventana.transient(self)

        ventana.update_idletasks()
        x = (ventana.winfo_screenwidth() // 2) - 200
        y = (ventana.winfo_screenheight() // 2) - 125
        ventana.geometry(f"400x250+{x}+{y}")

        frame = ctk.CTkFrame(ventana, fg_color="transparent")
        frame.pack(fill="both", expand=True, padx=25, pady=20)

        ctk.CTkLabel(
            frame, text="📅 Seleccionar Período",
            font=obtener_fuente("subtitulo")
        ).pack(anchor="w", pady=(0, 15))

        dates_frame = ctk.CTkFrame(frame, fg_color="transparent")
        dates_frame.pack(fill="x")
        dates_frame.grid_columnconfigure((0, 1), weight=1)

        ctk.CTkLabel(dates_frame, text="Desde:",
                     font=obtener_fuente("small_bold")).grid(row=0, column=0, sticky="w", padx=5)
        entry_desde = ctk.CTkEntry(dates_frame, placeholder_text="DD/MM/AAAA", height=36)
        entry_desde.grid(row=1, column=0, sticky="ew", padx=5, pady=5)

        ctk.CTkLabel(dates_frame, text="Hasta:",
                     font=obtener_fuente("small_bold")).grid(row=0, column=1, sticky="w", padx=5)
        entry_hasta = ctk.CTkEntry(dates_frame, placeholder_text="DD/MM/AAAA", height=36)
        entry_hasta.grid(row=1, column=1, sticky="ew", padx=5, pady=5)

        def generar():
            desde_str = entry_desde.get().strip()
            hasta_str = entry_hasta.get().strip()

            if not desde_str or not hasta_str:
                mostrar_advertencia(ventana, "Aviso",
                                   "Ingrese ambas fechas (desde y hasta)")
                return

            try:
                desde = datetime.strptime(desde_str, "%d/%m/%Y").date()
                hasta = datetime.strptime(hasta_str, "%d/%m/%Y").date()
            except ValueError:
                mostrar_error(ventana, "Error",
                             "Formato de fecha inválido. Use DD/MM/AAAA")
                return

            if desde > hasta:
                mostrar_error(ventana, "Error",
                             "La fecha 'Desde' debe ser anterior a 'Hasta'")
                return

            try:
                datos = db.ejecutar_query("""
                    SELECT hu.apellido_nombre, hu.dni_pasaporte, hu.nacionalidad,
                           hu.procedencia, hu.profesion_ocupacion, hu.edad,
                           hu.fecha_entrada, hu.fecha_salida, h.nombre as hotel,
                           hu.habitacion, hu.telefono
                    FROM huespedes hu
                    LEFT JOIN hoteles h ON hu.hotel_id = h.id
                    WHERE hu.fecha_entrada BETWEEN %s AND %s
                    ORDER BY hu.fecha_entrada, hu.apellido_nombre
                """, (desde, hasta), fetch=True)

                ventana.destroy()
                self._exportar(
                    [dict(d) for d in datos] if datos else [],
                    formato, f"huespedes_{desde_str.replace('/', '')}_a_{hasta_str.replace('/', '')}",
                    f"Huéspedes del {desde_str} al {hasta_str}"
                )
            except Exception as e:
                log_error("Error en reporte por fechas", e)
                mostrar_error(ventana, "Error", str(e))

        btn_frame = ctk.CTkFrame(frame, fg_color="transparent")
        btn_frame.pack(fill="x", pady=(20, 0))

        ctk.CTkButton(
            btn_frame, text="Generar", height=40,
            fg_color=COLORS["success"], hover_color="#388E3C",
            command=generar
        ).pack(side="right", padx=5)

        ctk.CTkButton(
            btn_frame, text="Cancelar", height=40,
            fg_color="gray30", command=ventana.destroy
        ).pack(side="right", padx=5)

    def _reporte_estadistico(self, formato: str):
        """Genera reporte estadístico con resúmenes."""
        try:
            # Nacionalidades
            nac_datos = db.ejecutar_query("""
                SELECT nacionalidad as concepto, COUNT(*) as total
                FROM huespedes
                WHERE nacionalidad IS NOT NULL AND nacionalidad != ''
                GROUP BY nacionalidad ORDER BY total DESC
            """, fetch=True)

            # Profesiones
            prof_datos = db.ejecutar_query("""
                SELECT profesion_ocupacion as concepto, COUNT(*) as total
                FROM huespedes
                WHERE profesion_ocupacion IS NOT NULL AND profesion_ocupacion != ''
                GROUP BY profesion_ocupacion ORDER BY total DESC
            """, fetch=True)

            # Procedencia
            proc_datos = db.ejecutar_query("""
                SELECT procedencia as concepto, COUNT(*) as total
                FROM huespedes
                WHERE procedencia IS NOT NULL AND procedencia != ''
                GROUP BY procedencia ORDER BY total DESC
            """, fetch=True)

            # Combinar en Excel con hojas separadas
            if formato == "excel":
                archivo = self._obtener_ruta_guardado("excel", "reporte_estadistico")
                if not archivo:
                    return

                import openpyxl
                from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

                wb = openpyxl.Workbook()

                def crear_hoja(wb, nombre, datos_hoja, titulo_hoja):
                    ws = wb.create_sheet(title=nombre[:31])

                    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
                    header_fill = PatternFill(start_color="1565C0", end_color="1565C0",
                                              fill_type="solid")

                    ws.cell(row=1, column=1, value=titulo_hoja).font = Font(
                        name="Calibri", size=14, bold=True, color="1565C0")

                    ws.cell(row=3, column=1, value="Concepto").font = header_font
                    ws.cell(row=3, column=1).fill = header_fill
                    ws.cell(row=3, column=2, value="Cantidad").font = header_font
                    ws.cell(row=3, column=2).fill = header_fill

                    if datos_hoja:
                        for i, d in enumerate(datos_hoja, 4):
                            ws.cell(row=i, column=1, value=d.get("concepto", ""))
                            ws.cell(row=i, column=2, value=d.get("total", 0))

                    ws.column_dimensions["A"].width = 35
                    ws.column_dimensions["B"].width = 15

                crear_hoja(wb, "Nacionalidades", nac_datos or [], "Distribución por Nacionalidad")
                crear_hoja(wb, "Profesiones", prof_datos or [], "Distribución por Profesión")
                crear_hoja(wb, "Procedencias", proc_datos or [], "Distribución por Procedencia")

                # Eliminar hoja default
                if "Sheet" in wb.sheetnames:
                    del wb["Sheet"]

                wb.save(archivo)
                mostrar_exito(self, "Exportado",
                             f"Reporte estadístico generado:\n{archivo}")
            else:
                # Para PDF, combinar todo en una tabla
                datos_combinados = []
                if nac_datos:
                    for d in nac_datos[:10]:
                        datos_combinados.append({
                            "categoria": "Nacionalidad",
                            "concepto": d["concepto"],
                            "total": d["total"]
                        })
                if prof_datos:
                    for d in prof_datos[:10]:
                        datos_combinados.append({
                            "categoria": "Profesión",
                            "concepto": d["concepto"],
                            "total": d["total"]
                        })
                if proc_datos:
                    for d in proc_datos[:10]:
                        datos_combinados.append({
                            "categoria": "Procedencia",
                            "concepto": d["concepto"],
                            "total": d["total"]
                        })

                self._exportar(
                    datos_combinados, formato,
                    "reporte_estadistico", "Reporte Estadístico",
                    ["categoria", "concepto", "total"]
                )

        except Exception as e:
            log_error("Error en reporte estadístico", e)
            mostrar_error(self, "Error", str(e))

    def _reporte_importaciones(self, formato: str):
        """Genera reporte del historial de importaciones."""
        try:
            datos = db.ejecutar_query("""
                SELECT il.nombre_archivo, il.registros_importados,
                       il.registros_duplicados, il.registros_error,
                       il.fecha_importacion,
                       u.username as usuario
                FROM importaciones_log il
                LEFT JOIN usuarios u ON il.usuario_id = u.id
                ORDER BY il.fecha_importacion DESC
            """, fetch=True)

            self._exportar(
                [dict(d) for d in datos] if datos else [],
                formato, "historial_importaciones",
                "Historial de Importaciones"
            )
        except Exception as e:
            log_error("Error en reporte importaciones", e)
            mostrar_error(self, "Error", str(e))

    def _reporte_auditoria(self, formato: str):
        """Genera reporte de auditoría del sistema."""
        try:
            datos = db.ejecutar_query("""
                SELECT a.fecha, u.username, a.accion, a.detalle
                FROM auditoria a
                LEFT JOIN usuarios u ON a.usuario_id = u.id
                ORDER BY a.fecha DESC
                LIMIT 500
            """, fetch=True)

            self._exportar(
                [dict(d) for d in datos] if datos else [],
                formato, "auditoria_sistema",
                "Auditoría del Sistema"
            )
        except Exception as e:
            log_error("Error en reporte auditoría", e)
            mostrar_error(self, "Error", str(e))
