import customtkinter as ctk
from config import COLORS, FONTS, CORNER_RADIUS, PADDING
from models.solution import RepairSession


class HistoryView(ctk.CTkToplevel):
    def __init__(self, parent, printer, db):
        super().__init__(parent)
        self.printer = printer
        self.db = db
        self.title(f"Historial — {printer.name}")
        self.geometry("640x480")
        self.configure(fg_color=COLORS["bg_primary"])
        self.grab_set()
        self._build()

    def _build(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(
            self,
            text=f"Historial de reparaciones · {self.printer.name}",
            font=FONTS["heading"],
            text_color=COLORS["text_primary"],
        ).grid(row=0, column=0, sticky="w", padx=PADDING, pady=(16, 8))

        sessions = (
            self.db.query(RepairSession)
            .filter_by(printer_id=self.printer.id)
            .order_by(RepairSession.started_at.desc())
            .all()
        )

        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll.grid(row=1, column=0, sticky="nsew", padx=PADDING, pady=(0, PADDING))
        scroll.grid_columnconfigure(0, weight=1)

        if not sessions:
            ctk.CTkLabel(
                scroll,
                text="Sin reparaciones registradas para esta impresora.",
                font=FONTS["body"],
                text_color=COLORS["text_secondary"],
            ).pack(pady=40)
            return

        outcome_map = {
            "fixed":   ("✓ Resuelto",  COLORS["success"]),
            "partial": ("⚠ Parcial",   COLORS["warning"]),
            "failed":  ("✗ Falló",     COLORS["error"]),
            "skipped": ("— Omitido",   COLORS["text_secondary"]),
        }

        for i, session in enumerate(sessions):
            label, color = outcome_map.get(session.outcome, ("?", COLORS["text_secondary"]))
            card = ctk.CTkFrame(
                scroll,
                fg_color=COLORS["bg_card"],
                corner_radius=CORNER_RADIUS,
                border_width=1,
                border_color=COLORS["border"],
            )
            card.grid(row=i, column=0, sticky="ew", pady=4)
            card.grid_columnconfigure(1, weight=1)

            ctk.CTkLabel(
                card, text=label, font=FONTS["body"], text_color=color, width=90
            ).grid(row=0, column=0, padx=12, pady=10)

            sol_title = session.solution.title if session.solution else session.error_code or "—"
            ctk.CTkLabel(
                card, text=sol_title, font=FONTS["body"],
                text_color=COLORS["text_primary"], anchor="w",
            ).grid(row=0, column=1, sticky="w")

            date_str = session.started_at.strftime("%d/%m/%Y %H:%M") if session.started_at else ""
            steps_str = f"{session.steps_completed} paso(s)" if session.steps_completed else ""
            ctk.CTkLabel(
                card,
                text=f"{date_str}  ·  {steps_str}",
                font=FONTS["small"],
                text_color=COLORS["text_secondary"],
            ).grid(row=0, column=2, padx=12)
