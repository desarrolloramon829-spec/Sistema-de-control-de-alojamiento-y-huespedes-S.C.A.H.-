"""
S.C.A.H. - Diálogos reutilizables
Ventanas de confirmación, error, información, etc.
"""

import customtkinter as ctk
from ui.themes import COLORS, obtener_fuente


class DialogoMensaje(ctk.CTkToplevel):
    """Diálogo genérico para mostrar mensajes."""

    def __init__(self, parent, titulo: str, mensaje: str,
                 tipo: str = "info", botones: list = None):
        super().__init__(parent)

        self.resultado = None

        self.title(titulo)
        self.geometry("420x220")
        self.resizable(False, False)
        self.grab_set()
        self.transient(parent)

        # Centrar
        self.update_idletasks()
        x = (self.winfo_screenwidth() // 2) - 210
        y = (self.winfo_screenheight() // 2) - 110
        self.geometry(f"420x220+{x}+{y}")

        # Icono según tipo
        iconos = {
            "info": "ℹ️",
            "success": "✅",
            "warning": "⚠️",
            "error": "❌",
            "question": "❓"
        }
        colores = {
            "info": COLORS["info"],
            "success": COLORS["success"],
            "warning": COLORS["warning"],
            "error": COLORS["error"],
            "question": COLORS["primary"]
        }

        # Contenido
        frame = ctk.CTkFrame(self, fg_color="transparent")
        frame.pack(fill="both", expand=True, padx=20, pady=20)

        # Icono y mensaje
        top_frame = ctk.CTkFrame(frame, fg_color="transparent")
        top_frame.pack(fill="both", expand=True)

        ctk.CTkLabel(
            top_frame,
            text=iconos.get(tipo, "ℹ️"),
            font=ctk.CTkFont(size=40)
        ).pack(pady=(0, 10))

        ctk.CTkLabel(
            top_frame,
            text=mensaje,
            font=obtener_fuente("body"),
            wraplength=360,
            justify="center"
        ).pack()

        # Botones
        btn_frame = ctk.CTkFrame(frame, fg_color="transparent")
        btn_frame.pack(fill="x", pady=(15, 0))

        if botones is None:
            botones = [("Aceptar", "primary")]

        for texto, color_key in botones:
            color = colores.get(color_key, COLORS.get(color_key, COLORS["primary"]))
            ctk.CTkButton(
                btn_frame,
                text=texto,
                font=obtener_fuente("button"),
                fg_color=color,
                width=120,
                height=36,
                command=lambda t=texto: self._click(t)
            ).pack(side="right", padx=5)

        self.bind("<Return>", lambda e: self._click(botones[0][0] if botones else "Aceptar"))
        self.bind("<Escape>", lambda e: self._click("Cancelar"))

    def _click(self, texto):
        self.resultado = texto
        self.grab_release()
        self.destroy()


def mostrar_info(parent, titulo: str, mensaje: str):
    """Muestra un diálogo informativo."""
    dialogo = DialogoMensaje(parent, titulo, mensaje, "info")
    parent.wait_window(dialogo)
    return dialogo.resultado


def mostrar_exito(parent, titulo: str, mensaje: str):
    """Muestra un diálogo de éxito."""
    dialogo = DialogoMensaje(parent, titulo, mensaje, "success")
    parent.wait_window(dialogo)
    return dialogo.resultado


def mostrar_error(parent, titulo: str, mensaje: str):
    """Muestra un diálogo de error."""
    dialogo = DialogoMensaje(parent, titulo, mensaje, "error")
    parent.wait_window(dialogo)
    return dialogo.resultado


def mostrar_advertencia(parent, titulo: str, mensaje: str):
    """Muestra un diálogo de advertencia."""
    dialogo = DialogoMensaje(parent, titulo, mensaje, "warning")
    parent.wait_window(dialogo)
    return dialogo.resultado


def confirmar(parent, titulo: str, mensaje: str) -> bool:
    """Muestra un diálogo de confirmación. Retorna True si acepta."""
    dialogo = DialogoMensaje(
        parent, titulo, mensaje, "question",
        botones=[("Cancelar", "error"), ("Aceptar", "primary")]
    )
    parent.wait_window(dialogo)
    return dialogo.resultado == "Aceptar"


def confirmar_eliminar(parent, elemento: str) -> bool:
    """Diálogo de confirmación para eliminar un elemento."""
    return confirmar(
        parent,
        "Confirmar eliminación",
        f"¿Está seguro que desea eliminar {elemento}?\n\nEsta acción no se puede deshacer."
    )
