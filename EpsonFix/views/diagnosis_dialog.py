import customtkinter as ctk
from config import COLORS, FONTS, CORNER_RADIUS


QUICK_SYMPTOMS = [
    ("No imprime nada",          "no imprime"),
    ("Rayas en la impresión",    "rayas"),
    ("Atasco de papel",          "papel atorado"),
    ("Luz de error parpadeando", "luz parpadeando"),
    ("No aparece en Windows",    "sin conexión"),
    ("Cartucho con error",       "no reconoce cartucho"),
    ("Colores incorrectos",      "colores incorrectos"),
]


class DiagnosisDialog(ctk.CTkToplevel):
    """Diálogo para elegir síntoma o ingresar código de error."""

    def __init__(self, parent, printer, on_diagnose):
        super().__init__(parent)
        self.printer = printer
        self.on_diagnose = on_diagnose

        self.title(f"Diagnosticar — {printer.name}")
        self.geometry("520x500")
        self.resizable(False, False)
        self.configure(fg_color=COLORS["bg_primary"])
        self.grab_set()
        self._build()

    def _build(self):
        self.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            self,
            text=f"¿Qué problema tiene\n{self.printer.name}?",
            font=FONTS["title"],
            text_color=COLORS["text_primary"],
            justify="center",
        ).grid(row=0, column=0, pady=(20, 6))

        ctk.CTkLabel(
            self,
            text="Selecciona un síntoma o escribe el código de error",
            font=FONTS["body"],
            text_color=COLORS["text_secondary"],
        ).grid(row=1, column=0, pady=(0, 16))

        # Grid de síntomas 2 columnas
        sym_frame = ctk.CTkFrame(self, fg_color="transparent")
        sym_frame.grid(row=2, column=0, sticky="ew", padx=24)
        sym_frame.grid_columnconfigure((0, 1), weight=1)

        for i, (label, code) in enumerate(QUICK_SYMPTOMS):
            btn = ctk.CTkButton(
                sym_frame,
                text=label,
                font=FONTS["body"],
                fg_color=COLORS["bg_card"],
                hover_color=COLORS["border"],
                text_color=COLORS["text_primary"],
                border_width=1,
                border_color=COLORS["border"],
                corner_radius=CORNER_RADIUS,
                height=44,
                command=lambda c=code: self._select(c),
            )
            btn.grid(row=i // 2, column=i % 2, padx=4, pady=4, sticky="ew")

        ctk.CTkLabel(
            self,
            text="O ingresa código de error directamente:",
            font=FONTS["small"],
            text_color=COLORS["text_secondary"],
        ).grid(row=3, column=0, pady=(16, 4))

        code_frame = ctk.CTkFrame(self, fg_color="transparent")
        code_frame.grid(row=4, column=0, padx=24, sticky="ew")
        code_frame.grid_columnconfigure(0, weight=1)

        self.code_entry = ctk.CTkEntry(
            code_frame,
            placeholder_text="Ej: 0x97, 0x10",
            font=FONTS["body"],
            fg_color=COLORS["bg_primary"],
            border_color=COLORS["border"],
            corner_radius=6,
            height=40,
        )
        self.code_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self.code_entry.bind("<Return>", lambda e: self._select(self.code_entry.get()))

        ctk.CTkButton(
            code_frame,
            text="Buscar",
            font=FONTS["body"],
            fg_color=COLORS["brand"],
            hover_color=COLORS["brand_light"],
            corner_radius=6,
            width=80,
            height=40,
            command=lambda: self._select(self.code_entry.get()),
        ).grid(row=0, column=1)

    def _select(self, code_or_symptom: str):
        val = code_or_symptom.strip()
        if val:
            self.destroy()
            self.on_diagnose(val, self.printer)
