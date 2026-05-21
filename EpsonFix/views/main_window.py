import customtkinter as ctk
from tkinter import messagebox
from config import COLORS, FONTS, WINDOW_W, WINDOW_H, PADDING, CARD_W
from views.components.printer_card import PrinterCard
from views.wizard_view import WizardView


class MainWindow(ctk.CTk):
    def __init__(self, presenter):
        super().__init__()
        self.presenter = presenter
        self.title("EpsonFix")
        self.geometry(f"{WINDOW_W}x{WINDOW_H}")
        self.minsize(800, 560)
        self.configure(fg_color=COLORS["bg_primary"])
        self._build()

    def _build(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._build_topbar()
        self._build_main_area()
        self._build_sidebar()

    def _build_topbar(self):
        bar = ctk.CTkFrame(self, fg_color=COLORS["bg_card"], corner_radius=0, height=56)
        bar.grid(row=0, column=0, columnspan=2, sticky="ew")
        bar.grid_columnconfigure(1, weight=1)
        bar.grid_propagate(False)

        ctk.CTkLabel(
            bar,
            text="🖨  EpsonFix",
            font=FONTS["title"],
            text_color=COLORS["brand"],
        ).grid(row=0, column=0, padx=PADDING, pady=10, sticky="w")

        ctk.CTkLabel(
            bar,
            text="Soluciones inteligentes para impresoras Epson",
            font=FONTS["body"],
            text_color=COLORS["text_secondary"],
        ).grid(row=0, column=1, padx=8, sticky="w")

        ctk.CTkButton(
            bar,
            text="+ Agregar impresora",
            font=FONTS["body"],
            fg_color=COLORS["brand"],
            hover_color=COLORS["brand_light"],
            corner_radius=6,
            command=self.presenter.on_add_printer,
            width=160,
        ).grid(row=0, column=2, padx=PADDING, pady=10)

    def _build_main_area(self):
        self.main_frame = ctk.CTkScrollableFrame(
            self,
            fg_color="transparent",
            scrollbar_fg_color=COLORS["bg_card"],
        )
        self.main_frame.grid(row=1, column=0, sticky="nsew", padx=PADDING, pady=PADDING)
        self.main_frame.grid_columnconfigure(0, weight=1)

        self._section_label(self.main_frame, "Mis impresoras", row=0)
        self.cards_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.cards_frame.grid(row=1, column=0, sticky="ew")

        self._section_label(self.main_frame, "Últimas reparaciones", row=2)
        self.history_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.history_frame.grid(row=3, column=0, sticky="ew")

    def _build_sidebar(self):
        sidebar = ctk.CTkFrame(
            self,
            fg_color=COLORS["bg_card"],
            corner_radius=0,
            width=220,
            border_width=1,
            border_color=COLORS["border"],
        )
        sidebar.grid(row=1, column=1, sticky="nsew")
        sidebar.grid_propagate(False)

        ctk.CTkLabel(
            sidebar,
            text="Errores frecuentes",
            font=FONTS["heading"],
            text_color=COLORS["text_primary"],
        ).pack(anchor="w", padx=16, pady=(16, 8))

        quick_errors = [
            ("0x97", "Almohadilla llena"),
            ("0x10", "Atasco de papel"),
            ("Rayas", "Cabezal sucio"),
            ("Sin conexión", "Offline"),
            ("Cartucho", "No reconocido"),
            ("Driver", "Controlador"),
        ]

        for code, label in quick_errors:
            btn = ctk.CTkButton(
                sidebar,
                text=f"{code}  —  {label}",
                font=FONTS["small"],
                fg_color="transparent",
                hover_color=COLORS["border"],
                text_color=COLORS["text_secondary"],
                anchor="w",
                corner_radius=4,
                command=lambda c=code: self.presenter.on_quick_diagnose(c),
            )
            btn.pack(fill="x", padx=8, pady=2)

        ctk.CTkFrame(sidebar, height=1, fg_color=COLORS["border"]).pack(
            fill="x", padx=16, pady=12
        )

        ctk.CTkLabel(
            sidebar,
            text="Diagnóstico por síntoma",
            font=("Segoe UI", 11, "bold"),
            text_color=COLORS["text_secondary"],
        ).pack(anchor="w", padx=16, pady=(0, 6))

        self.symptom_entry = ctk.CTkEntry(
            sidebar,
            placeholder_text='Ej: "no imprime", "rayas"',
            font=FONTS["small"],
            fg_color=COLORS["bg_primary"],
            border_color=COLORS["border"],
            corner_radius=6,
        )
        self.symptom_entry.pack(fill="x", padx=16, pady=(0, 6))
        self.symptom_entry.bind("<Return>", lambda e: self._on_symptom_search())

        ctk.CTkButton(
            sidebar,
            text="Buscar solución",
            font=FONTS["small"],
            fg_color=COLORS["brand"],
            hover_color=COLORS["brand_light"],
            corner_radius=6,
            command=self._on_symptom_search,
        ).pack(fill="x", padx=16)

    def _section_label(self, parent, text: str, row: int):
        ctk.CTkLabel(
            parent,
            text=text,
            font=FONTS["heading"],
            text_color=COLORS["text_primary"],
            anchor="w",
        ).grid(row=row, column=0, sticky="w", pady=(12, 6))

    def _on_symptom_search(self):
        symptom = self.symptom_entry.get().strip()
        if symptom:
            self.presenter.on_symptom_diagnose(symptom)

    # ── Métodos llamados por el presenter ──────────────────────────────────

    def render_printers(self, printers: list, status_map: dict):
        for w in self.cards_frame.winfo_children():
            w.destroy()

        if not printers:
            ctk.CTkLabel(
                self.cards_frame,
                text="No hay impresoras. Agrega una con '+ Agregar impresora'.",
                font=FONTS["body"],
                text_color=COLORS["text_secondary"],
            ).grid(row=0, column=0, pady=40)
            return

        for i, printer in enumerate(printers):
            printer.status_code = status_map.get(printer.system_name, 0)
            card = PrinterCard(
                self.cards_frame,
                printer=printer,
                on_diagnose=self.presenter.on_diagnose_printer,
                on_history=self.presenter.on_view_history,
            )
            col = i % 3
            row = i // 3
            card.grid(row=row, column=col, padx=8, pady=8, sticky="nsew")

        for c in range(3):
            self.cards_frame.grid_columnconfigure(c, weight=1)

    def render_recent_history(self, sessions: list):
        for w in self.history_frame.winfo_children():
            w.destroy()

        if not sessions:
            ctk.CTkLabel(
                self.history_frame,
                text="Sin reparaciones registradas aún.",
                font=FONTS["body"],
                text_color=COLORS["text_secondary"],
            ).grid(row=0, column=0, pady=8)
            return

        for i, session in enumerate(sessions):
            outcome_colors = {
                "fixed": COLORS["success"],
                "partial": COLORS["warning"],
                "failed": COLORS["error"],
            }
            color = outcome_colors.get(session.outcome, COLORS["text_secondary"])
            outcome_text = {"fixed": "✓ Resuelto", "partial": "⚠ Parcial", "failed": "✗ Falló"}.get(
                session.outcome, session.outcome
            )

            row_frame = ctk.CTkFrame(self.history_frame, fg_color="transparent")
            row_frame.grid(row=i, column=0, sticky="ew", pady=2)
            row_frame.grid_columnconfigure(2, weight=1)

            ctk.CTkLabel(
                row_frame,
                text=outcome_text,
                font=FONTS["small"],
                text_color=color,
                width=90,
            ).grid(row=0, column=0, padx=(0, 12))

            printer_name = session.printer.name if session.printer else "—"
            ctk.CTkLabel(
                row_frame,
                text=f"{printer_name}  ·  {session.error_code or '—'}",
                font=FONTS["small"],
                text_color=COLORS["text_primary"],
            ).grid(row=0, column=1, padx=(0, 12))

            date_str = session.started_at.strftime("%d/%m/%Y %H:%M") if session.started_at else ""
            ctk.CTkLabel(
                row_frame,
                text=date_str,
                font=FONTS["small"],
                text_color=COLORS["text_secondary"],
            ).grid(row=0, column=2, sticky="e")

    def show_wizard(self, solution, printer):
        WizardView(
            self,
            solution=solution,
            printer=printer,
            on_complete=self.presenter.on_wizard_complete,
        )

    def show_error(self, message: str):
        messagebox.showerror("Error", message)

    def show_info(self, title: str, message: str):
        messagebox.showinfo(title, message)
