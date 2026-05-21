"""EpsonFix — Soluciones inteligentes para impresoras Epson."""
import customtkinter as ctk
from database.db_manager import init_db, seed_knowledge_base
from presenters.main_presenter import MainPresenter
from views.main_window import MainWindow


def main():
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("dark-blue")

    init_db()
    seed_knowledge_base()

    presenter = MainPresenter()
    app = MainWindow(presenter)
    presenter.attach_view(app)
    app.mainloop()


if __name__ == "__main__":
    main()
