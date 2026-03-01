"""
S.C.A.H. - Configuración de temas visuales
Paleta de colores y estilos para la interfaz
"""

import customtkinter as ctk

# ============================================================
# COLORES DEL TEMA
# ============================================================
COLORS = {
    # Primarios
    "primary": "#1E88E5",
    "primary_hover": "#1565C0",
    "primary_dark": "#1565C0",
    "primary_light": "#42A5F5",

    # Secundarios
    "secondary": "#26A69A",
    "secondary_hover": "#00897B",

    # Sidebar
    "sidebar_bg": "#1A1A2E",
    "sidebar_text": "#E0E0E0",
    "sidebar_active": "#16213E",
    "sidebar_hover": "#0F3460",

    # Fondo
    "bg_dark": "#0F0F23",
    "bg_medium": "#1A1A2E",
    "bg_light": "#16213E",
    "bg_card": "#1E1E3A",

    # Texto
    "text_primary": "#FFFFFF",
    "text_secondary": "#B0B0B0",
    "text_muted": "#707070",

    # Estado
    "success": "#4CAF50",
    "success_light": "#81C784",
    "warning": "#FF9800",
    "warning_light": "#FFB74D",
    "error": "#F44336",
    "error_light": "#E57373",
    "info": "#2196F3",

    # Tabla
    "table_header": "#1A237E",
    "table_row_even": "#1E1E3A",
    "table_row_odd": "#16213E",
    "table_selected": "#1565C0",

    # Bordes
    "border": "#333355",
    "border_light": "#444466",

    # Inputs
    "input_bg": "#16213E",
    "input_border": "#333355",
    "input_focus": "#1E88E5",
}

# ============================================================
# FUENTES
# ============================================================
FONTS = {
    "titulo": ("Segoe UI", 24, "bold"),
    "subtitulo": ("Segoe UI", 18, "bold"),
    "heading": ("Segoe UI", 16, "bold"),
    "body": ("Segoe UI", 14),
    "body_bold": ("Segoe UI", 14, "bold"),
    "small": ("Segoe UI", 12),
    "small_bold": ("Segoe UI", 12, "bold"),
    "tiny": ("Segoe UI", 10),
    "mono": ("Consolas", 13),
    "sidebar": ("Segoe UI", 14),
    "sidebar_bold": ("Segoe UI", 14, "bold"),
    "button": ("Segoe UI", 14, "bold"),
    "table_header": ("Segoe UI", 12, "bold"),
    "table_body": ("Segoe UI", 12),
}


def aplicar_tema():
    """Aplica el tema oscuro de CustomTkinter."""
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")


def obtener_fuente(nombre: str) -> ctk.CTkFont:
    """Retorna un objeto CTkFont a partir del nombre del estilo."""
    if nombre in FONTS:
        f = FONTS[nombre]
        weight = "bold" if len(f) > 2 and f[2] == "bold" else "normal"
        return ctk.CTkFont(family=f[0], size=f[1], weight=weight)
    return ctk.CTkFont(family="Segoe UI", size=14)
