from __future__ import annotations

import threading
import customtkinter as ctk
from typing import Callable, TYPE_CHECKING

from config import COLORS, FONTS, CORNER_RADIUS

if TYPE_CHECKING:
    from core.updater import UpdateInfo


_TYPE_LABELS = {
    "patch": ("Corrección de errores", COLORS.get("success", "#2ECC71")),
    "minor": ("Nueva versión",         "#3498DB"),
    "major": ("Actualización mayor",   "#F39C12"),
}


class UpdateDialog(ctk.CTkToplevel):
    """Modal for minor/major updates with release notes and progress bar."""

    def __init__(self, parent, info: "UpdateInfo", on_install: Callable, on_skip: Callable):
        super().__init__(parent)
        self._info = info
        self._on_install = on_install
        self._on_skip = on_skip
        self._downloading = False

        type_label, type_color = _TYPE_LABELS.get(info.update_type, ("Actualización", "#3498DB"))
        self.title(f"EpsonFix — {type_label} disponible")
        self.geometry("520x450")
        self.resizable(False, False)
        self.configure(fg_color=COLORS["bg_primary"])
        self.grab_set()
        self._build(type_label, type_color)

    def _build(self, type_label: str, type_color: str):
        self.grid_columnconfigure(0, weight=1)

        badge = ctk.CTkFrame(self, fg_color=type_color, corner_radius=6)
        badge.grid(row=0, column=0, pady=(20, 0), padx=24, sticky="w")
        ctk.CTkLabel(
            badge, text=f"  {type_label.upper()}  ",
            font=("Segoe UI", 10, "bold"), text_color="#FFFFFF",
        ).pack(padx=4, pady=2)

        ctk.CTkLabel(
            self,
            text=f"v{self._info.current}  →  v{self._info.latest}",
            font=FONTS["title"], text_color=COLORS["text_primary"],
        ).grid(row=1, column=0, pady=(8, 0))

        if self._info.update_type == "major":
            ctk.CTkLabel(
                self,
                text="⚠  Actualización mayor — puede incluir cambios importantes.",
                font=FONTS["small"], text_color=COLORS["warning"],
            ).grid(row=2, column=0, pady=(4, 0))
        else:
            ctk.CTkLabel(self, text="", font=FONTS["small"]).grid(row=2, column=0)

        ctk.CTkLabel(
            self, text="Notas de versión:",
            font=FONTS["body"], text_color=COLORS["text_secondary"],
        ).grid(row=3, column=0, sticky="w", padx=24, pady=(12, 2))

        notes_box = ctk.CTkTextbox(
            self, height=130,
            fg_color=COLORS["bg_card"], text_color=COLORS["text_primary"],
            font=FONTS["small"], border_color=COLORS["border"],
            border_width=1, corner_radius=CORNER_RADIUS,
        )
        notes_box.grid(row=4, column=0, sticky="ew", padx=24)
        notes_box.insert("0.0", self._info.release_notes)
        notes_box.configure(state="disabled")

        self._progress = ctk.CTkProgressBar(
            self, fg_color=COLORS["bg_card"], progress_color=COLORS["success"],
        )
        self._progress.grid(row=5, column=0, sticky="ew", padx=24, pady=(12, 0))
        self._progress.set(0)
        self._progress.grid_remove()

        self._status_label = ctk.CTkLabel(
            self, text="", font=FONTS["small"], text_color=COLORS["text_secondary"],
        )
        self._status_label.grid(row=6, column=0)

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.grid(row=7, column=0, pady=16)

        ctk.CTkButton(
            btn_frame, text="Omitir versión",
            font=FONTS["body"], fg_color=COLORS["accent"],
            hover_color=COLORS["border"], corner_radius=CORNER_RADIUS,
            command=self._skip_version, width=130,
        ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            btn_frame, text="Ahora no",
            font=FONTS["body"], fg_color="transparent",
            hover_color=COLORS["border"], corner_radius=CORNER_RADIUS,
            border_width=1, border_color=COLORS["border"],
            command=self._skip, width=100,
        ).pack(side="left", padx=(0, 8))

        install_text = "Instalar y reiniciar" if self._info.update_type != "major" else "Confirmar e instalar"
        self._install_btn = ctk.CTkButton(
            btn_frame, text=install_text,
            font=FONTS["body"], fg_color=COLORS["brand"],
            hover_color=COLORS["brand_light"], corner_radius=CORNER_RADIUS,
            command=self._start_install, width=180,
        )
        self._install_btn.pack(side="left")

    def _skip_version(self):
        from core import prefs
        prefs.set("skipped_version", self._info.latest)
        self._on_skip()
        self.destroy()

    def _skip(self):
        self._on_skip()
        self.destroy()

    def _start_install(self):
        if self._downloading:
            return
        self._downloading = True
        self._install_btn.configure(state="disabled", text="Descargando...")
        self._progress.grid()
        threading.Thread(target=self._download_and_apply, daemon=True).start()

    def _download_and_apply(self):
        from core.updater import download_update, apply_update

        def progress(downloaded: int, total: int):
            ratio = downloaded / total if total > 0 else 0
            mb_dl = downloaded / 1_048_576
            mb_total = total / 1_048_576
            self.after(0, lambda: self._progress.set(ratio))
            self.after(0, lambda: self._status_label.configure(
                text=f"Descargando... {mb_dl:.1f} / {mb_total:.1f} MB"
            ))

        try:
            path = download_update(self._info, progress_cb=progress)
            self.after(0, lambda: self._status_label.configure(
                text="Aplicando actualización y reiniciando..."
            ))
            self.after(200, lambda: apply_update(path))
        except Exception as exc:
            self.after(0, lambda: self._on_download_error(str(exc)))

    def _on_download_error(self, msg: str):
        self._downloading = False
        self._progress.grid_remove()
        self._install_btn.configure(state="normal", text="Reintentar")
        self._status_label.configure(text=f"Error: {msg[:80]}", text_color=COLORS["error"])


class UpdateBanner(ctk.CTkFrame):
    """Inline green banner for silent patch installs."""

    def __init__(self, parent, info: "UpdateInfo", on_install: Callable, on_dismiss: Callable):
        super().__init__(parent, fg_color=COLORS.get("success", "#2ECC71"), corner_radius=6, height=32)
        self._info = info
        self._on_install = on_install
        self._on_dismiss = on_dismiss
        self._downloading = False
        self.grid_propagate(False)
        self._build()

    def _build(self):
        self.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            self,
            text=f"✓  Corrección v{self._info.latest} disponible",
            font=FONTS["small"], text_color="#FFFFFF",
        ).grid(row=0, column=0, padx=(10, 6), pady=4)

        self._status = ctk.CTkLabel(self, text="", font=FONTS["small"], text_color="#FFFFFF")
        self._status.grid(row=0, column=1, sticky="w")

        ctk.CTkButton(
            self, text="Instalar",
            font=FONTS["small"], fg_color="#27AE60", hover_color="#1E8449",
            corner_radius=4, height=22, width=70,
            command=self._install,
        ).grid(row=0, column=2, padx=4)

        ctk.CTkButton(
            self, text="✕",
            font=FONTS["small"], fg_color="transparent", hover_color="#1E8449",
            corner_radius=4, height=22, width=28,
            command=self._dismiss,
        ).grid(row=0, column=3, padx=(0, 6))

    def _install(self):
        if self._downloading:
            return
        self._downloading = True
        self._status.configure(text="Descargando...")
        threading.Thread(target=self._download_and_apply, daemon=True).start()

    def _download_and_apply(self):
        from core.updater import download_update, apply_update
        try:
            path = download_update(self._info)
            self.after(0, lambda: self._status.configure(text="Aplicando..."))
            self.after(400, lambda: apply_update(path))
        except Exception as exc:
            self.after(0, lambda: self._status.configure(text=f"Error: {str(exc)[:40]}"))
            self._downloading = False

    def _dismiss(self):
        self._on_dismiss()
        self.destroy()
