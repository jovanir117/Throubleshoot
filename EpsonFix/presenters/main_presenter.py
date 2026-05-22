from __future__ import annotations

from datetime import datetime
import logging
import threading
import tkinter

from sqlalchemy.exc import SQLAlchemyError

from core.diagnosis_engine import DiagnosisEngine
from core.printer_detector import list_printers
from core.system_health import get_system_health_report
from database.db_manager import get_session, remove_current_session
from models.error_event import ErrorEvent
from models.printer import PrinterProfile
from models.solution import RepairSession, Solution


class MainPresenter:
    def __init__(self):
        self.view = None
        self.db = get_session()
        self.engine = DiagnosisEngine(self.db)
        self._selected_printer: PrinterProfile | None = None
        self._is_scanning = False
        self._scan_lock = threading.Lock()
        self._spooler_console = None

    def attach_view(self, view):
        self.view = view
        self.refresh()

    def close(self):
        self.db.close()
        remove_current_session()

    def refresh(self):
        if not self.view:
            return
        with self._scan_lock:
            if self._is_scanning:
                return
            self._is_scanning = True

        def bg_scan():
            session = get_session()
            try:
                sessions = (
                    session.query(RepairSession)
                    .order_by(RepairSession.started_at.desc())
                    .limit(8)
                    .all()
                )

                spooler_active = True
                try:
                    import win32print
                    win32print.EnumPrinters(win32print.PRINTER_ENUM_LOCAL, None, 2)
                except Exception as exc:
                    logging.getLogger(__name__).warning("Spooler status probe failed: %s", str(exc)[:300])
                    spooler_active = False

                health = get_system_health_report()
                db_printers = session.query(PrinterProfile).filter_by(is_active=True).all()

                try:
                    detected = {p.system_name: p.status_code for p in list_printers()}
                except Exception as exc:
                    logging.getLogger(__name__).warning("Printer list scan failed: %s", str(exc)[:300])
                    detected = {}

                status_map = {p.system_name: detected.get(p.system_name, 8) for p in db_printers}

                if self._view_alive():
                    for repair_session in sessions:
                        session.expunge(repair_session)
                    for printer in db_printers:
                        session.expunge(printer)
                    self.view.after(
                        0,
                        lambda: self._update_ui_after_scan(
                            db_printers,
                            status_map,
                            health,
                            spooler_active,
                            sessions,
                        ),
                    )
            except Exception as exc:
                import sys
                print(f"Error en escaneo en segundo plano: {exc}", file=sys.stderr)
            finally:
                session.close()
                remove_current_session()
                with self._scan_lock:
                    self._is_scanning = False

        threading.Thread(target=bg_scan, daemon=True).start()

    def _update_ui_after_scan(self, printers, status_map, health, spooler_active, sessions):
        if not self._view_alive():
            return
        self.view.render_recent_history(sessions)
        self.view.render_printers(printers, status_map)
        self.view.update_system_health(
            health.disk_free_pct,
            health.summary,
            spooler_active,
        )

    def on_add_printer(self):
        from views.add_printer_dialog import AddPrinterDialog
        AddPrinterDialog(self.view, on_save=self._save_printer)

    def on_diagnose_printer(self, printer: PrinterProfile):
        self._selected_printer = printer
        self._open_diagnosis_dialog(printer)

    def on_view_history(self, printer: PrinterProfile):
        from views.history_view import HistoryView
        HistoryView(self.view, printer=printer, db=self.db)

    def on_quick_diagnose(self, error_code: str):
        if not self._selected_printer:
            printers = self.db.query(PrinterProfile).filter_by(is_active=True).limit(1).all()
            if not printers:
                self.view.show_info("Sin impresoras", "Agrega una impresora primero.")
                return
            self._selected_printer = printers[0]
        self._run_diagnosis(error_code, self._selected_printer)

    def on_symptom_diagnose(self, symptom: str):
        if not self._selected_printer:
            printers = self.db.query(PrinterProfile).filter_by(is_active=True).limit(1).all()
            if not printers:
                self.view.show_info("Sin impresoras", "Agrega una impresora primero.")
                return
            self._selected_printer = printers[0]
        self._run_diagnosis(symptom, self._selected_printer)

    def on_restart_spooler(self):
        if self._spooler_console and self._view_alive():
            try:
                if self._spooler_console.winfo_exists():
                    self._spooler_console.lift()
                    return
            except tkinter.TclError:
                pass

        from core.step_actions import execute_action
        from views.console_view import ConsoleView

        self._spooler_console = ConsoleView(self.view, title="Reiniciar Spooler de Windows")

        def on_close():
            self._spooler_console = None
            self.refresh()

        self._spooler_console.bind(
            "<Destroy>",
            lambda e: self._after_view(100, on_close) if e.widget == self._spooler_console else None,
        )
        self._spooler_console.run_generator(execute_action("spooler_restart"))

    def on_wizard_complete(self, printer, solution, outcome, steps_completed, notes):
        repair_session = RepairSession(
            printer_id=printer.id,
            solution_id=solution.id,
            error_code=solution.error_code,
            started_at=datetime.utcnow(),
            completed_at=datetime.utcnow(),
            outcome=outcome,
            steps_completed=steps_completed,
            notes=notes,
        )
        try:
            self.db.add(repair_session)
            if outcome == "fixed":
                solution.success_count += 1
            solution.attempt_count += 1
            self.db.commit()
        except SQLAlchemyError as exc:
            self.db.rollback()
            self.view.show_error(f"No se pudo guardar la reparacion: {exc}")
            return

        msg = {"fixed": "Problema resuelto.", "partial": "Solucion parcial.", "failed": "No funciono esta vez."}.get(outcome, "")
        self.view.show_info("Resultado", msg)
        self.refresh()

    def _open_diagnosis_dialog(self, printer: PrinterProfile):
        from views.diagnosis_dialog import DiagnosisDialog
        DiagnosisDialog(self.view, printer=printer, on_diagnose=self._run_diagnosis)

    def _run_diagnosis(self, user_input: str, printer: PrinterProfile):
        health = get_system_health_report()
        diagnosis = self.engine.diagnose_smart(user_input)
        if not diagnosis:
            self.view.show_info(
                "Sin resultado",
                f"No encontre solucion para '{user_input}'.\nRevisa el codigo de error o describe el problema.\n\n"
                f"{health.summary}",
            )
            return

        event = ErrorEvent(
            printer_id=printer.id,
            error_code=diagnosis.error_code,
            category=diagnosis.category,
            description=diagnosis.description,
        )
        try:
            self.db.add(event)
            self.db.commit()
        except SQLAlchemyError as exc:
            self.db.rollback()
            self.view.show_error(f"No se pudo registrar el diagnostico: {exc}")
            return

        if diagnosis.category in ("connectivity", "driver", "system"):
            from tkinter import messagebox
            from core.auto_fix import run_auto_fix_gen
            from views.console_view import ConsoleView

            console = ConsoleView(self.view, title=f"Auto-Fix: {diagnosis.title}")

            def on_console_close():
                self.refresh()
                if not self._view_alive():
                    return
                if not messagebox.askyesno(
                    "Problema resuelto?",
                    "Se soluciono el problema con la reparacion automatica?\n\n"
                    "Si seleccionas 'No', se iniciara el asistente paso a paso.",
                ):
                    solution = self._get_best_solution(diagnosis, printer)
                    if solution:
                        self.view.show_wizard(solution, printer)
                    else:
                        self.view.show_info("Sin pasos detallados", "No hay pasos manuales detallados para esta categoria.")

            console.bind("<Destroy>", lambda e: self._after_view(100, on_console_close) if e.widget == console else None)
            console.run_generator(run_auto_fix_gen(diagnosis.category))
            return

        solution = self._get_best_solution(diagnosis, printer)
        if not solution:
            self.view.show_info(
                diagnosis.title,
                f"{diagnosis.description}\n\n"
                f"Causas raiz probables:\n- " + "\n- ".join(diagnosis.probable_causes) +
                "\n\nNo hay pasos detallados en la base de conocimiento.\n\n"
                f"{health.summary}\n"
                + "\n".join(f"- {r}" for r in health.recommendations),
            )
            return

        self.view.show_wizard(solution, printer)

    def _get_best_solution(self, diagnosis, printer: PrinterProfile) -> Solution | None:
        solutions = (
            self.db.query(Solution)
            .filter(Solution.error_code == diagnosis.category)
            .all()
        )
        applicable = [s for s in solutions if s.applies_to(printer.series or "ALL")]
        if not applicable:
            applicable = solutions
        applicable.sort(key=lambda s: s.success_rate, reverse=True)
        return applicable[0] if applicable else None

    def _save_printer(self, data: dict):
        try:
            printer = PrinterProfile(**data)
            self.db.add(printer)
            self.db.commit()
            self.refresh()
        except SQLAlchemyError as exc:
            self.db.rollback()
            self.view.show_error(f"No se pudo guardar la impresora: {exc}")

    def on_edit_printer(self, printer: PrinterProfile):
        from views.edit_printer_dialog import EditPrinterDialog
        EditPrinterDialog(self.view, printer=printer, on_save=self._update_printer)

    def _update_printer(self, printer_id: int, data: dict):
        db_printer = self.db.query(PrinterProfile).filter_by(id=printer_id).first()
        if not db_printer:
            return
        try:
            for key, value in data.items():
                setattr(db_printer, key, value)
            self.db.commit()
            self.refresh()
        except SQLAlchemyError as exc:
            self.db.rollback()
            self.view.show_error(f"No se pudo actualizar la impresora: {exc}")

    def on_delete_printer(self, printer: PrinterProfile):
        from tkinter import messagebox

        if not messagebox.askyesno("Confirmar eliminacion", f"Estas seguro de que deseas eliminar la impresora '{printer.name}'?"):
            return
        db_printer = self.db.query(PrinterProfile).filter_by(id=printer.id).first()
        if not db_printer:
            return
        try:
            db_printer.is_active = False
            self.db.commit()
            self.refresh()
        except SQLAlchemyError as exc:
            self.db.rollback()
            self.view.show_error(f"No se pudo eliminar la impresora: {exc}")

    def check_for_updates(self, force: bool = False):
        """Run in background thread. Shows update UI if newer version exists on GitHub."""
        from config import APP_VERSION
        from core.updater import check_for_updates

        def _bg():
            info = check_for_updates(APP_VERSION, force=force)
            if info and self._view_alive():
                self.view.after(0, lambda: self.view.show_update_available(info))

        import threading
        threading.Thread(target=_bg, daemon=True).start()

    def on_about(self):
        from views.about_dialog import AboutDialog
        AboutDialog(self.view, presenter=self)

    def _view_alive(self) -> bool:
        try:
            return bool(self.view and self.view.winfo_exists())
        except tkinter.TclError:
            return False

    def _after_view(self, delay_ms: int, callback):
        if not self._view_alive():
            return None
        try:
            return self.view.after(delay_ms, callback)
        except tkinter.TclError:
            return None
