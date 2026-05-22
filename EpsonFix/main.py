"""EpsonFix — Soluciones inteligentes para impresoras Epson."""
import sys
import logging
import traceback
import threading
from pathlib import Path
import customtkinter as ctk

from database.db_manager import init_db, seed_knowledge_base
from presenters.main_presenter import MainPresenter
from views.main_window import MainWindow

# Configurar directorio y archivo de logs
LOG_DIR = Path(__file__).parent / "data"
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / "app.log"

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.ERROR,
    format="%(asctime)s - %(levelname)s - %(message)s",
    encoding="utf-8"
)


def show_crash_dialog(exctype, value, tb):
    tb_text = "".join(traceback.format_exception(exctype, value, tb))
    logging.error(f"Unhandled exception:\n{tb_text}")

    try:
        from config import COLORS, FONTS
        
        # Crear ventana de error independiente
        crash_win = ctk.CTk()
        crash_win.title("Error Crítico — EpsonFix")
        crash_win.geometry("600x450")
        crash_win.minsize(500, 400)
        crash_win.configure(fg_color=COLORS["bg_primary"])
        
        # Centrar ventana en pantalla
        crash_win.update_idletasks()
        w = crash_win.winfo_width()
        h = crash_win.winfo_height()
        extra_w = (crash_win.winfo_screenwidth() - w) // 2
        extra_h = (crash_win.winfo_screenheight() - h) // 2
        crash_win.geometry(f"+{extra_w}+{extra_h}")

        # Título
        ctk.CTkLabel(
            crash_win,
            text="🚨 Se ha producido un error inesperado",
            font=("Segoe UI", 16, "bold"),
            text_color=COLORS["error"]
        ).pack(pady=(20, 10))

        ctk.CTkLabel(
            crash_win,
            text="EpsonFix experimentó una falla crítica y debe cerrarse. Reporta este error.",
            font=FONTS["body"],
            text_color=COLORS["text_secondary"]
        ).pack(padx=20, pady=(0, 15))

        # Caja de texto monospacio para el Traceback
        txt = ctk.CTkTextbox(
            crash_win,
            fg_color=COLORS["bg_card"],
            text_color=COLORS["text_primary"],
            font=FONTS["mono"],
            border_color=COLORS["border"],
            border_width=1
        )
        txt.pack(fill="both", expand=True, padx=20, pady=10)
        txt.insert("0.0", tb_text)
        txt.configure(state="disabled")

        # Botones de reporte y cierre
        btn_frame = ctk.CTkFrame(crash_win, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=15)

        def copy_traceback():
            crash_win.clipboard_clear()
            crash_win.clipboard_append(tb_text)
            copy_btn.configure(text="¡Copiado! ✓", fg_color=COLORS["success"])
            crash_win.after(2000, lambda: copy_btn.configure(text="Copiar reporte", fg_color=COLORS["accent"]))

        copy_btn = ctk.CTkButton(
            btn_frame,
            text="Copiar reporte",
            font=FONTS["body"],
            fg_color=COLORS["accent"],
            hover_color=COLORS["border"],
            command=copy_traceback
        )
        copy_btn.pack(side="left", padx=(0, 10))

        exit_btn = ctk.CTkButton(
            btn_frame,
            text="Cerrar aplicación",
            font=FONTS["body"],
            fg_color=COLORS["brand"],
            hover_color=COLORS["brand_light"],
            command=sys.exit
        )
        exit_btn.pack(side="right")

        crash_win.mainloop()
    except Exception as dialog_err:
        try:
            from tkinter import messagebox
            messagebox.showerror(
                "Error Crítico",
                f"EpsonFix no pudo iniciarse debido a un error crítico:\n\n{value}\n\nDetalles guardados en 'data/app.log'"
            )
        except Exception:
            pass
        sys.exit(1)


def thread_excepthook(args):
    show_crash_dialog(args.exc_type, args.exc_value, args.exc_traceback)


sys.excepthook = show_crash_dialog
threading.excepthook = thread_excepthook


def _start_update_check(app, presenter):
    """Fires 5 s after startup — checks GitHub for updates without blocking UI."""
    def _run():
        import time
        time.sleep(5)
        presenter.check_for_updates()
    threading.Thread(target=_run, daemon=True).start()


def main():
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("dark-blue")

    init_db()
    seed_knowledge_base()

    presenter = MainPresenter()
    app = MainWindow(presenter)
    presenter.attach_view(app)
    app.after(5000, lambda: _start_update_check(app, presenter))
    app.mainloop()


if __name__ == "__main__":
    main()
