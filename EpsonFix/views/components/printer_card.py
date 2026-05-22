import customtkinter as ctk
from config import COLORS, FONTS, CARD_W, CARD_H, CORNER_RADIUS
from core.printer_detector import get_printer_status_label


class PrinterCard(ctk.CTkFrame):
    """Card cuadrada por impresora en el dashboard principal."""

    def __init__(self, parent, printer, on_diagnose, on_history, on_edit, on_delete, **kwargs):
        super().__init__(
            parent,
            width=CARD_W,
            height=CARD_H,
            corner_radius=CORNER_RADIUS,
            fg_color=COLORS["bg_card"],
            border_width=1,
            border_color=COLORS["border"],
            **kwargs,
        )
        self.printer = printer
        self.on_diagnose = on_diagnose
        self.on_history = on_history
        self.on_edit = on_edit
        self.on_delete = on_delete
        self._build()
        self._bind_hover()

    def _build(self):
        self.grid_propagate(False)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        # Header: icono + nombre
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=14, pady=(14, 4))
        header.grid_columnconfigure(1, weight=1)

        icon_lbl = ctk.CTkLabel(header, text="🖨", font=("Segoe UI Emoji", 22))
        icon_lbl.grid(row=0, column=0, padx=(0, 8))

        name_lbl = ctk.CTkLabel(
            header,
            text=self.printer.name,
            font=FONTS["heading"],
            text_color=COLORS["text_primary"],
            anchor="w",
        )
        name_lbl.grid(row=0, column=1, sticky="w")

        edit_btn = ctk.CTkButton(
            header,
            text="✏️",
            font=("Segoe UI Emoji", 11),
            fg_color="transparent",
            hover_color=COLORS["border"],
            text_color=COLORS["text_secondary"],
            width=24,
            height=24,
            corner_radius=4,
            command=self._on_edit_click,
        )
        edit_btn.grid(row=0, column=2, padx=2)

        delete_btn = ctk.CTkButton(
            header,
            text="🗑️",
            font=("Segoe UI Emoji", 11),
            fg_color="transparent",
            hover_color=COLORS["border"],
            text_color=COLORS["text_secondary"],
            width=24,
            height=24,
            corner_radius=4,
            command=self._on_delete_click,
        )
        delete_btn.grid(row=0, column=3, padx=(2, 0))

        # Modelo / serie
        model_text = f"{self.printer.model or 'Desconocido'} · {self.printer.series or 'Epson'}"
        model_lbl = ctk.CTkLabel(
            self,
            text=model_text,
            font=FONTS["small"],
            text_color=COLORS["text_secondary"],
            anchor="w",
        )
        model_lbl.grid(row=1, column=0, sticky="w", padx=14, pady=(0, 6))

        # Estado
        status_label, status_color = get_printer_status_label(
            getattr(self.printer, "status_code", 0)
        )
        status_frame = ctk.CTkFrame(self, fg_color="transparent")
        status_frame.grid(row=2, column=0, sticky="w", padx=14)

        dot = ctk.CTkLabel(
            status_frame,
            text="●",
            font=FONTS["small"],
            text_color=status_color,
        )
        dot.grid(row=0, column=0, padx=(0, 4))

        status_lbl = ctk.CTkLabel(
            status_frame,
            text=status_label,
            font=FONTS["small"],
            text_color=status_color,
        )
        status_lbl.grid(row=0, column=1)

        # Botones
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.grid(row=3, column=0, sticky="ew", padx=14, pady=(8, 14))
        btn_frame.grid_columnconfigure((0, 1), weight=1)

        is_error = getattr(self.printer, "status_code", 0) not in (0, 3, 9, 10)
        btn_color = COLORS["brand"] if is_error else COLORS["accent"]
        btn_text = "RESOLVER ▶" if is_error else "Diagnosticar"

        diag_btn = ctk.CTkButton(
            btn_frame,
            text=btn_text,
            font=FONTS["body"],
            fg_color=btn_color,
            hover_color=COLORS["brand_light"],
            corner_radius=CORNER_RADIUS,
            command=lambda: self.on_diagnose(self.printer),
        )
        diag_btn.grid(row=0, column=0, sticky="ew", padx=(0, 4))

        hist_btn = ctk.CTkButton(
            btn_frame,
            text="Historial",
            font=FONTS["body"],
            fg_color=COLORS["bg_primary"],
            hover_color=COLORS["border"],
            corner_radius=CORNER_RADIUS,
            command=lambda: self.on_history(self.printer),
        )
        hist_btn.grid(row=0, column=1, sticky="ew", padx=(4, 0))

    def _bind_hover(self):
        def on_enter(e):
            self.configure(fg_color=COLORS["bg_card_hover"])

        def on_leave(e):
            self.configure(fg_color=COLORS["bg_card"])

        def bind_recursive(widget):
            widget.bind("<Enter>", on_enter)
            widget.bind("<Leave>", on_leave)
            for child in widget.winfo_children():
                bind_recursive(child)

        bind_recursive(self)

    def _on_edit_click(self):
        if self.on_edit:
            self.on_edit(self.printer)

    def _on_delete_click(self):
        if self.on_delete:
            self.on_delete(self.printer)
