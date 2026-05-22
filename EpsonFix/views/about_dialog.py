import customtkinter as ctk
from config import COLORS, FONTS, CORNER_RADIUS, APP_VERSION


class AboutDialog(ctk.CTkToplevel):
    def __init__(self, parent, presenter=None):
        super().__init__(parent)
        self._presenter = presenter
        self.title("Acerca de EpsonFix")
        self.geometry("460x440")
        self.resizable(False, False)
        self.configure(fg_color=COLORS["bg_primary"])
        self.grab_set()

        self.update_idletasks()
        w = self.winfo_width()
        h = self.winfo_height()
        self.geometry(f"+{(self.winfo_screenwidth()-w)//2}+{(self.winfo_screenheight()-h)//2}")
        self._build()

    def _build(self):
        self.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(self, text="🖨", font=("Segoe UI Emoji", 56)).grid(row=0, column=0, pady=(25, 5))

        ctk.CTkLabel(
            self, text="EpsonFix Premium",
            font=("Segoe UI", 20, "bold"), text_color=COLORS["brand"],
        ).grid(row=1, column=0, pady=2)

        ctk.CTkLabel(
            self, text=f"Versión {APP_VERSION}",
            font=FONTS["body"], text_color=COLORS["text_secondary"],
        ).grid(row=2, column=0, pady=(0, 12))

        info_frame = ctk.CTkFrame(
            self, fg_color=COLORS["bg_card"],
            corner_radius=CORNER_RADIUS, border_width=1, border_color=COLORS["border"],
        )
        info_frame.grid(row=3, column=0, sticky="ew", padx=24, pady=4)
        info_frame.grid_columnconfigure(0, weight=1)

        desc = (
            "Suite integral de diagnóstico y mantenimiento para impresoras Epson.\n\n"
            "• Detección de hardware vía pyusb y WMI\n"
            "• Reparaciones automáticas integradas (Auto-Fix)\n"
            "• Asistente guiado por base de conocimiento local\n"
            "• Historial detallado y telemetría de fallas\n"
            "• Actualizaciones automáticas desde GitHub Releases"
        )
        ctk.CTkLabel(
            info_frame, text=desc, font=FONTS["small"], text_color=COLORS["text_primary"],
            justify="left", wraplength=380,
        ).grid(row=0, column=0, padx=16, pady=14, sticky="w")

        ctk.CTkLabel(
            self, text="Desarrollado con ❤️ para el soporte mundial de impresión",
            font=FONTS["small"], text_color=COLORS["text_secondary"],
        ).grid(row=4, column=0, pady=(10, 6))

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.grid(row=5, column=0, pady=(0, 20))

        if self._presenter:
            self._update_btn = ctk.CTkButton(
                btn_frame, text="Buscar actualizaciones",
                font=FONTS["body"], fg_color=COLORS["accent"],
                hover_color=COLORS["border"], corner_radius=CORNER_RADIUS,
                command=self._check_updates, width=180,
            )
            self._update_btn.pack(side="left", padx=(0, 10))

        ctk.CTkButton(
            btn_frame, text="Cerrar",
            font=FONTS["body"], fg_color=COLORS["brand"],
            hover_color=COLORS["brand_light"], corner_radius=CORNER_RADIUS,
            command=self.destroy, width=100,
        ).pack(side="left")

    def _check_updates(self):
        self._update_btn.configure(state="disabled", text="Buscando...")
        import threading
        threading.Thread(target=self._run_check, daemon=True).start()

    def _run_check(self):
        from config import APP_VERSION
        from core.updater import check_for_updates
        info = check_for_updates(APP_VERSION, force=True)
        self.after(0, lambda: self._on_check_done(info))

    def _on_check_done(self, info):
        if not self.winfo_exists():
            return
        if info:
            self._update_btn.configure(
                state="normal", text=f"v{info.latest} disponible!",
                fg_color=COLORS["success"],
            )
            if self._presenter and hasattr(self._presenter, "view"):
                view = self._presenter.view
                if view:
                    view.after(0, lambda: view.show_update_available(info))
        else:
            self._update_btn.configure(state="normal", text="✓ Al día", fg_color=COLORS["success"])
            self.after(3000, lambda: self._update_btn.configure(
                text="Buscar actualizaciones", fg_color=COLORS["accent"],
                state="normal",
            ) if self.winfo_exists() else None)
