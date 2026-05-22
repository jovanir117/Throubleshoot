import queue
import threading

import customtkinter as ctk

from config import COLORS, FONTS, CORNER_RADIUS


class ConsoleView(ctk.CTkToplevel):
    def __init__(self, parent, title="Consola de Reparacion"):
        super().__init__(parent)
        self.title(title)
        self.geometry("620x420")
        self.resizable(False, False)
        self.configure(fg_color="#0F0F1A")
        self._cancel_event = threading.Event()
        self._running = False

        self.transient(parent)
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        self._build()

    def _build(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        header = ctk.CTkFrame(self, fg_color=COLORS["bg_card"], corner_radius=0, height=44)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_columnconfigure(0, weight=1)
        header.grid_propagate(False)

        ctk.CTkLabel(
            header,
            text="EJECUTOR DE DIAGNOSTICO Y REPARACION",
            font=("Segoe UI", 11, "bold"),
            text_color=COLORS["brand_light"],
        ).grid(row=0, column=0, padx=14, pady=10, sticky="w")

        self.textbox = ctk.CTkTextbox(
            self,
            fg_color="#0A0A16",
            text_color="#39FF14",
            font=("Consolas", 11),
            border_width=1,
            border_color=COLORS["border"],
            corner_radius=CORNER_RADIUS,
        )
        self.textbox.grid(row=1, column=0, sticky="nsew", padx=16, pady=16)
        self.textbox.configure(state="disabled")

        self.footer = ctk.CTkFrame(self, fg_color="transparent")
        self.footer.grid(row=2, column=0, sticky="ew", padx=16, pady=(0, 16))
        self.footer.grid_columnconfigure(0, weight=1)

        self.status_lbl = ctk.CTkLabel(
            self.footer,
            text="Ejecutando procesos...",
            font=FONTS["body"],
            text_color=COLORS["warning"],
            anchor="w",
        )
        self.status_lbl.grid(row=0, column=0, sticky="w")

        self.copy_btn = ctk.CTkButton(
            self.footer,
            text="Copiar log",
            font=FONTS["body"],
            fg_color=COLORS["accent"],
            hover_color=COLORS["border"],
            corner_radius=CORNER_RADIUS,
            command=self.copy_to_clipboard,
            width=100,
        )
        self.copy_btn.grid(row=0, column=1, padx=(0, 8))

        self.close_btn = ctk.CTkButton(
            self.footer,
            text="Cerrar",
            font=FONTS["body"],
            fg_color=COLORS["accent"],
            hover_color=COLORS["border"],
            corner_radius=CORNER_RADIUS,
            command=self._on_close,
            width=100,
            state="disabled",
        )
        self.close_btn.grid(row=0, column=2)

    def write_line(self, text: str):
        if not self.winfo_exists():
            return
        self.textbox.configure(state="normal")
        self.textbox.insert("end", f"> {text}\n")
        self.textbox.see("end")
        self.textbox.configure(state="disabled")

    def run_generator(self, generator):
        self._running = True
        events: queue.Queue[tuple[str, object]] = queue.Queue()

        def worker():
            try:
                while True:
                    if self._cancel_event.is_set():
                        events.put(("finish", False))
                        return
                    line = next(generator)
                    if isinstance(line, str):
                        events.put(("line", line))
                    else:
                        events.put(("finish", bool(line)))
                        return
            except StopIteration as e:
                success = e.value if e.value is not None else True
                events.put(("finish", bool(success)))
            except Exception as ex:
                events.put(("line", f"EXCEPCION CRITICA: {ex}"))
                events.put(("finish", False))

        def drain():
            if not self.winfo_exists():
                return
            finished = False
            while True:
                try:
                    event_type, payload = events.get_nowait()
                except queue.Empty:
                    break
                if event_type == "line":
                    self.write_line(str(payload))
                elif event_type == "finish":
                    self._finish(bool(payload))
                    finished = True
            if not finished and self.winfo_exists():
                self.after(100, drain)

        threading.Thread(target=worker, daemon=True).start()
        self.after(100, drain)

    def _finish(self, success: bool):
        self._running = False
        if success:
            self.status_lbl.configure(text="Proceso finalizado con exito.", text_color=COLORS["success"])
            self.write_line("PROCESO TERMINADO. Listo para operar.")
        else:
            self.status_lbl.configure(text="El proceso finalizo con fallas.", text_color=COLORS["error"])
            self.write_line("PROCESO DETENIDO. Revisa los mensajes de error superiores.")

        self.close_btn.configure(state="normal")

    def copy_to_clipboard(self):
        if not self.winfo_exists():
            return
        log_content = self.textbox.get("1.0", "end-1c")
        self.clipboard_clear()
        self.clipboard_append(log_content)
        self.copy_btn.configure(text="Copiado", fg_color=COLORS["success"])
        self.after(2000, self._restore_copy_button)

    def _restore_copy_button(self):
        if self.winfo_exists():
            self.copy_btn.configure(text="Copiar log", fg_color=COLORS["accent"])

    def _on_close(self):
        if self._running:
            self._cancel_event.set()
            self.close_btn.configure(state="disabled")
            self.status_lbl.configure(text="Cancelando al terminar el paso actual...", text_color=COLORS["warning"])
            return
        self.destroy()
