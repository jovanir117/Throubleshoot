import customtkinter as ctk
from tkinter import messagebox

from config import COLORS, FONTS, CORNER_RADIUS
from core.printer_detector import list_printers, _detect_series, _extract_model
from core.validation import clean_text, validate_ip, validate_model, validate_printer_system_name


class EditPrinterDialog(ctk.CTkToplevel):
    def __init__(self, parent, printer, on_save):
        super().__init__(parent)
        self.printer = printer
        self.on_save = on_save
        self.title("Editar impresora - EpsonFix")
        self.geometry("500x480")
        self.resizable(False, False)
        self.configure(fg_color=COLORS["bg_primary"])
        self.grab_set()

        self._detected: list = list_printers()
        self._build()
        self._load_printer_data()

    def _build(self):
        self.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            self, text="Editar impresora",
            font=FONTS["title"], text_color=COLORS["text_primary"]
        ).grid(row=0, column=0, pady=(20, 4))

        ctk.CTkLabel(
            self, text="Modifica los datos de la impresora seleccionada",
            font=FONTS["body"], text_color=COLORS["text_secondary"]
        ).grid(row=1, column=0, pady=(0, 16))

        form = ctk.CTkFrame(self, fg_color=COLORS["bg_card"], corner_radius=CORNER_RADIUS)
        form.grid(row=2, column=0, sticky="ew", padx=24)
        form.grid_columnconfigure(1, weight=1)

        fields = [
            ("Nombre personalizado *", "entry", "name", "Ej: Epson de Recepcion"),
            ("Impresora del sistema", "combo", "system_name", None),
            ("Modelo", "entry", "model", "Ej: L3210, WF-2850"),
            ("Serie", "combo", "series", None),
            ("Conexion", "combo", "connection", None),
            ("IP (si aplica)", "entry", "ip_address", "Solo si es de red/WiFi"),
        ]

        self._widgets = {}

        for i, (label, wtype, key, placeholder) in enumerate(fields):
            ctk.CTkLabel(
                form, text=label, font=FONTS["body"], text_color=COLORS["text_secondary"]
            ).grid(row=i, column=0, sticky="w", padx=16, pady=(10, 0))

            if wtype == "entry":
                w = ctk.CTkEntry(
                    form, placeholder_text=placeholder or "",
                    font=FONTS["body"], fg_color=COLORS["bg_primary"],
                    border_color=COLORS["border"], corner_radius=6,
                )
            else:
                options = self._get_combo_options(key)
                w = ctk.CTkComboBox(
                    form, values=options, font=FONTS["body"],
                    fg_color=COLORS["bg_primary"], border_color=COLORS["border"],
                    corner_radius=6, dropdown_fg_color=COLORS["bg_card"],
                )
                if options:
                    w.set(options[0])

            w.grid(row=i, column=1, sticky="ew", padx=(8, 16), pady=(10, 0))
            self._widgets[key] = w

        sys_combo = self._widgets.get("system_name")
        if sys_combo:
            sys_combo.configure(command=self._on_printer_selected)

        ctk.CTkButton(
            self, text="Guardar cambios",
            font=FONTS["body"], fg_color=COLORS["brand"],
            hover_color=COLORS["brand_light"], corner_radius=CORNER_RADIUS,
            command=self._save,
        ).grid(row=3, column=0, pady=20, ipadx=20)

    def _get_combo_options(self, key: str) -> list[str]:
        if key == "system_name":
            detected_names = [p.system_name for p in self._detected]
            current_sys = self.printer.system_name
            if current_sys and current_sys not in detected_names:
                detected_names.insert(0, current_sys)
            return detected_names if detected_names else ["(No detectadas automaticamente)"]
        if key == "series":
            return ["EcoTank", "WorkForce", "Expression", "SureColor", "Otra"]
        if key == "connection":
            return ["USB", "WiFi", "Red (Ethernet)"]
        return []

    def _load_printer_data(self):
        self._widgets["name"].insert(0, self.printer.name or "")

        if self.printer.system_name:
            self._widgets["system_name"].set(self.printer.system_name)
        else:
            self._widgets["system_name"].set("(No detectadas automaticamente)")

        if self.printer.model:
            self._widgets["model"].insert(0, self.printer.model)

        self._widgets["series"].set(self.printer.series or "EcoTank")
        self._widgets["connection"].set(self.printer.connection or "USB")

        if self.printer.ip_address:
            self._widgets["ip_address"].insert(0, self.printer.ip_address)

    def _on_printer_selected(self, system_name: str):
        match = next((p for p in self._detected if p.system_name == system_name), None)
        if not match:
            return
        if match.model:
            self._widgets["model"].delete(0, "end")
            self._widgets["model"].insert(0, match.model)
        if match.series:
            self._widgets["series"].set(match.series)
        if match.connection:
            self._widgets["connection"].set(match.connection)

    def _save(self):
        try:
            name = clean_text(self._widgets["name"].get(), 100)
            if not name:
                raise ValueError("Nombre requerido.")
            model_raw = validate_model(self._widgets["model"].get())
            ip_address = validate_ip(self._widgets["ip_address"].get())
            system_name_raw = self._widgets["system_name"].get()
            system_name = (
                None
                if system_name_raw == "(No detectadas automaticamente)"
                else validate_printer_system_name(system_name_raw)
            )
        except ValueError as exc:
            self._widgets["name"].configure(border_color=COLORS["error"])
            messagebox.showerror("Datos invalidos", str(exc))
            return

        series = self._widgets["series"].get()
        if not series or series == "Otra":
            series = _detect_series(model_raw) if model_raw else None

        data = {
            "name": name,
            "system_name": system_name,
            "model": model_raw or (system_name and _extract_model(system_name)),
            "series": series,
            "connection": self._widgets["connection"].get(),
            "ip_address": ip_address,
        }
        self.on_save(self.printer.id, data)
        self.destroy()
