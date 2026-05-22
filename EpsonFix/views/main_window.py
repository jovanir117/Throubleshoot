import customtkinter as ctk
from tkinter import messagebox
from config import COLORS, FONTS, WINDOW_W, WINDOW_H, PADDING, CARD_W
from views.components.printer_card import PrinterCard
from views.wizard_view import WizardView


class MainWindow(ctk.CTk):
    def __init__(self, presenter):
        super().__init__()
        self.presenter = presenter
        self._refresh_after_id = None
        self.title("EpsonFix — Suite de Diagnóstico Profesional")
        self.geometry(f"{WINDOW_W}x{WINDOW_H}")
        self.minsize(900, 600)
        self.configure(fg_color=COLORS["bg_primary"])

        # Cargar icono de ventana
        try:
            from pathlib import Path
            icon_path = Path(__file__).parent.parent / "assets" / "icons" / "app_icon.ico"
            if icon_path.exists():
                self.iconbitmap(str(icon_path))
        except Exception:
            pass

        self._build()
        
        # Iniciar bucle de refresco periódico de segundo plano
        self._start_periodic_refresh()

        # Atajos de teclado
        self.bind("<F5>", lambda e: self._on_f5_press())
        self.bind("<Control-n>", lambda e: self._on_ctrln_press())
        self.bind("<Control-N>", lambda e: self._on_ctrln_press())
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)  # row 1 = update banner slot

        self._build_topbar()
        # Banner slot: row=1, collapsed by default
        self._banner_slot = ctk.CTkFrame(self, fg_color="transparent", height=0)
        self._banner_slot.grid(row=1, column=0, columnspan=2, sticky="ew")
        self._banner_slot.grid_propagate(False)
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
            text="Acerca de",
            font=FONTS["body"],
            fg_color=COLORS["accent"],
            hover_color=COLORS["border"],
            corner_radius=6,
            command=self.presenter.on_about,
            width=100,
        ).grid(row=0, column=2, padx=(8, 0), pady=10)

        ctk.CTkButton(
            bar,
            text="+ Agregar impresora",
            font=FONTS["body"],
            fg_color=COLORS["brand"],
            hover_color=COLORS["brand_light"],
            corner_radius=6,
            command=self.presenter.on_add_printer,
            width=160,
        ).grid(row=0, column=3, padx=PADDING, pady=10)

    def _build_main_area(self):
        self.main_frame = ctk.CTkScrollableFrame(
            self,
            fg_color="transparent",
            scrollbar_fg_color=COLORS["bg_card"],
        )
        self.main_frame.grid(row=2, column=0, sticky="nsew", padx=PADDING, pady=PADDING)
        self.main_frame.grid_columnconfigure(0, weight=1)

        self._section_label(self.main_frame, "Mis impresoras", row=0)
        self.cards_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.cards_frame.grid(row=1, column=0, sticky="ew")

        self._section_label(self.main_frame, "Últimas reparaciones", row=2)
        self.history_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.history_frame.grid(row=3, column=0, sticky="ew")

    def _build_sidebar(self):
        self.sidebar = ctk.CTkFrame(
            self,
            fg_color=COLORS["bg_card"],
            corner_radius=0,
            width=240,
            border_width=1,
            border_color=COLORS["border"],
        )
        self.sidebar.grid(row=2, column=1, sticky="nsew")
        self.sidebar.grid_propagate(False)

        ctk.CTkLabel(
            self.sidebar,
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
                self.sidebar,
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

        ctk.CTkFrame(self.sidebar, height=1, fg_color=COLORS["border"]).pack(
            fill="x", padx=16, pady=12
        )

        ctk.CTkLabel(
            self.sidebar,
            text="Diagnóstico por síntoma",
            font=("Segoe UI", 11, "bold"),
            text_color=COLORS["text_secondary"],
        ).pack(anchor="w", padx=16, pady=(0, 6))

        self.symptom_entry = ctk.CTkEntry(
            self.sidebar,
            placeholder_text='Ej: "no imprime", "rayas"',
            font=FONTS["small"],
            fg_color=COLORS["bg_primary"],
            border_color=COLORS["border"],
            corner_radius=6,
        )
        self.symptom_entry.pack(fill="x", padx=16, pady=(0, 6))
        self.symptom_entry.bind("<Return>", lambda e: self._on_symptom_search())

        ctk.CTkButton(
            self.sidebar,
            text="Buscar solución",
            font=FONTS["small"],
            fg_color=COLORS["brand"],
            hover_color=COLORS["brand_light"],
            corner_radius=6,
            command=self._on_symptom_search,
        ).pack(fill="x", padx=16)

        # ── SECCIÓN DE SALUD DEL SISTEMA ──
        ctk.CTkFrame(self.sidebar, height=1, fg_color=COLORS["border"]).pack(
            fill="x", padx=16, pady=12
        )

        ctk.CTkLabel(
            self.sidebar,
            text="Salud del Sistema",
            font=FONTS["heading"],
            text_color=COLORS["text_primary"],
        ).pack(anchor="w", padx=16, pady=(0, 6))

        # Fila del Spooler
        spooler_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        spooler_frame.pack(fill="x", padx=16, pady=4)
        
        self.spooler_lbl = ctk.CTkLabel(
            spooler_frame,
            text="Spooler: Escaneando...",
            font=FONTS["small"],
            text_color=COLORS["text_secondary"],
        )
        self.spooler_lbl.pack(side="left")

        self.spooler_btn = ctk.CTkButton(
            spooler_frame,
            text="Reiniciar",
            font=("Segoe UI", 9, "bold"),
            fg_color=COLORS["accent"],
            hover_color=COLORS["border"],
            corner_radius=4,
            width=65,
            height=20,
            command=self._on_restart_spooler_click,
        )
        self.spooler_btn.pack(side="right")

        # Fila de Almacenamiento
        disk_lbl_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        disk_lbl_frame.pack(fill="x", padx=16, pady=(8, 2))
        
        ctk.CTkLabel(
            disk_lbl_frame,
            text="Disco C:",
            font=FONTS["small"],
            text_color=COLORS["text_secondary"],
        ).pack(side="left")

        self.disk_val_lbl = ctk.CTkLabel(
            disk_lbl_frame,
            text="--%",
            font=FONTS["small"],
            text_color=COLORS["text_primary"],
        )
        self.disk_val_lbl.pack(side="right")

        self.disk_progress = ctk.CTkProgressBar(
            self.sidebar,
            height=6,
            corner_radius=3,
            fg_color=COLORS["border"],
            progress_color=COLORS["success"],
        )
        self.disk_progress.pack(fill="x", padx=16, pady=2)
        self.disk_progress.set(0.0)

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

    def _on_restart_spooler_click(self):
        self.presenter.on_restart_spooler()

    def _start_periodic_refresh(self):
        """Dispara la actualización y programa el siguiente ciclo."""
        self.presenter.refresh()
        # Refrescar cada 6 segundos para mantener un monitoreo en tiempo real
        self._refresh_after_id = self.after(6000, self._start_periodic_refresh)

    # ── Métodos llamados por el presenter ──────────────────────────────────

    def update_system_health(self, disk_free_pct: float, disk_summary: str, spooler_active: bool):
        # Actualizar etiqueta de spooler
        if spooler_active:
            self.spooler_lbl.configure(text="Spooler: Activo ●", text_color=COLORS["success"])
        else:
            self.spooler_lbl.configure(text="Spooler: Inactivo ●", text_color=COLORS["error"])

        # Actualizar barra de disco (usar porcentaje de espacio ocupado)
        usage_pct = 100.0 - disk_free_pct
        self.disk_val_lbl.configure(text=f"{usage_pct:.1f}% Usado")
        self.disk_progress.set(usage_pct / 100.0)

        # Colorear barra según espacio libre
        if disk_free_pct < 5.0:
            self.disk_progress.configure(progress_color=COLORS["error"])
        elif disk_free_pct < 15.0:
            self.disk_progress.configure(progress_color=COLORS["warning"])
        else:
            self.disk_progress.configure(progress_color=COLORS["success"])

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
            printer.status_code = status_map.get(printer.system_name, 8)
            card = PrinterCard(
                self.cards_frame,
                printer=printer,
                on_diagnose=self.presenter.on_diagnose_printer,
                on_history=self.presenter.on_view_history,
                on_edit=self.presenter.on_edit_printer,
                on_delete=self.presenter.on_delete_printer,
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

    def show_update_available(self, info) -> None:
        """Called from presenter after bg update check. Safe to call from any thread via after()."""
        from views.update_dialog import UpdateDialog, UpdateBanner

        def _install():
            pass  # download/apply handled inside dialog/banner

        def _skip():
            pass

        if info.is_silent:
            # Patch: show inline banner
            for child in self._banner_slot.winfo_children():
                child.destroy()
            self._banner_slot.configure(height=36)
            banner = UpdateBanner(
                self._banner_slot, info=info,
                on_install=_install,
                on_dismiss=lambda: self._banner_slot.configure(height=0),
            )
            banner.pack(fill="x", padx=8, pady=2)
        else:
            # Minor / major: modal dialog
            UpdateDialog(self, info=info, on_install=_install, on_skip=_skip)

    def show_error(self, message: str):
        messagebox.showerror("Error", message)

    def show_info(self, title: str, message: str):
        messagebox.showinfo(title, message)

    def _on_f5_press(self):
        self.presenter.refresh()

    def _on_ctrln_press(self):
        self.presenter.on_add_printer()

    def _on_close(self):
        if self._refresh_after_id is not None:
            self.after_cancel(self._refresh_after_id)
            self._refresh_after_id = None
        close = getattr(self.presenter, "close", None)
        if close:
            close()
        self.destroy()
