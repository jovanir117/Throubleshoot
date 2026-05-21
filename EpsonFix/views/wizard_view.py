import customtkinter as ctk
from config import COLORS, FONTS, CORNER_RADIUS, PADDING
from views.components.progress_stepper import ProgressStepper


class WizardView(ctk.CTkToplevel):
    """Ventana wizard paso a paso para resolver un error."""

    def __init__(self, parent, solution, printer, on_complete):
        super().__init__(parent)
        self.solution = solution
        self.printer = printer
        self.on_complete = on_complete
        self.steps = solution.steps
        self.current_step_idx = 0

        self.title(f"EpsonFix — {solution.title}")
        self.geometry("720x560")
        self.resizable(False, False)
        self.configure(fg_color=COLORS["bg_primary"])
        self.grab_set()

        self._build()
        self._show_step(0)

    def _build(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=0)   # stepper: fixed height

        # Header
        header = ctk.CTkFrame(self, fg_color=COLORS["bg_card"], corner_radius=0)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            header,
            text="🖨  EpsonFix",
            font=FONTS["heading"],
            text_color=COLORS["brand"],
        ).grid(row=0, column=0, padx=PADDING, pady=12, sticky="w")

        ctk.CTkLabel(
            header,
            text=f"{self.printer.name}  ·  {self.solution.title}",
            font=FONTS["body"],
            text_color=COLORS["text_secondary"],
        ).grid(row=0, column=1, padx=PADDING, sticky="w")

        # Stepper
        self.stepper = ProgressStepper(self, total_steps=len(self.steps), current_step=0)
        self.stepper.grid(row=1, column=0, pady=(20, 0))

        # Step content card
        self.content_card = ctk.CTkFrame(
            self,
            fg_color=COLORS["bg_card"],
            corner_radius=CORNER_RADIUS,
            border_width=1,
            border_color=COLORS["border"],
        )
        self.content_card.grid(row=2, column=0, sticky="nsew", padx=PADDING, pady=12)
        self.content_card.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(2, weight=1)

        # Step number
        self.step_num_lbl = ctk.CTkLabel(
            self.content_card,
            text="1",
            font=FONTS["step_num"],
            text_color=COLORS["brand"],
            width=56,
        )
        self.step_num_lbl.grid(row=0, column=0, rowspan=3, padx=(20, 12), pady=20, sticky="n")

        # Step title
        self.step_title_lbl = ctk.CTkLabel(
            self.content_card,
            text="",
            font=FONTS["heading"],
            text_color=COLORS["text_primary"],
            anchor="w",
            wraplength=540,
        )
        self.step_title_lbl.grid(row=0, column=1, sticky="w", padx=(0, 20), pady=(20, 4))

        # Step description
        self.step_desc_lbl = ctk.CTkLabel(
            self.content_card,
            text="",
            font=FONTS["body"],
            text_color=COLORS["text_secondary"],
            anchor="nw",
            justify="left",
            wraplength=540,
        )
        self.step_desc_lbl.grid(row=1, column=1, sticky="w", padx=(0, 20), pady=(0, 8))

        # Tip
        self.tip_frame = ctk.CTkFrame(
            self.content_card,
            fg_color=COLORS["accent"],
            corner_radius=6,
        )
        self.tip_lbl = ctk.CTkLabel(
            self.tip_frame,
            text="",
            font=FONTS["small"],
            text_color=COLORS["info"],
            anchor="w",
            wraplength=510,
            justify="left",
        )
        self.tip_lbl.grid(row=0, column=0, padx=12, pady=8, sticky="w")

        # Verification question
        self.verify_lbl = ctk.CTkLabel(
            self.content_card,
            text="",
            font=("Segoe UI", 12, "bold"),
            text_color=COLORS["warning"],
            anchor="w",
            wraplength=540,
        )

        # Footer buttons
        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.grid(row=3, column=0, sticky="ew", padx=PADDING, pady=(0, PADDING))
        footer.grid_columnconfigure(1, weight=1)

        self.problem_btn = ctk.CTkButton(
            footer,
            text="⚠ Tengo un problema",
            font=FONTS["body"],
            fg_color="transparent",
            border_width=1,
            border_color=COLORS["warning"],
            text_color=COLORS["warning"],
            hover_color=COLORS["accent"],
            corner_radius=CORNER_RADIUS,
            command=self._on_problem,
            width=180,
        )
        self.problem_btn.grid(row=0, column=0, sticky="w")

        self.back_btn = ctk.CTkButton(
            footer,
            text="◀ Anterior",
            font=FONTS["body"],
            fg_color=COLORS["bg_card"],
            hover_color=COLORS["border"],
            corner_radius=CORNER_RADIUS,
            command=self._prev_step,
            width=120,
        )
        self.back_btn.grid(row=0, column=2, padx=(0, 8))

        self.next_btn = ctk.CTkButton(
            footer,
            text="Sí, continuar ▶",
            font=FONTS["body"],
            fg_color=COLORS["brand"],
            hover_color=COLORS["brand_light"],
            corner_radius=CORNER_RADIUS,
            command=self._next_step,
            width=160,
        )
        self.next_btn.grid(row=0, column=3)

    def _show_step(self, idx: int):
        step = self.steps[idx]
        self.stepper.set_step(idx)
        self.step_num_lbl.configure(text=str(idx + 1))
        self.step_title_lbl.configure(text=step.title)
        self.step_desc_lbl.configure(text=step.description)

        if step.tip:
            self.tip_lbl.configure(text=f"💡 {step.tip}")
            self.tip_frame.grid(row=2, column=1, sticky="ew", padx=(0, 20), pady=(0, 8))
        else:
            self.tip_frame.grid_remove()

        if step.verification_question:
            self.verify_lbl.configure(text=f"¿ {step.verification_question}")
            self.verify_lbl.grid(row=3, column=1, sticky="w", padx=(0, 20), pady=(0, 12))
        else:
            self.verify_lbl.grid_remove()

        is_first = (idx == 0)
        is_last = (idx == len(self.steps) - 1)
        self.back_btn.configure(state="disabled" if is_first else "normal")
        self.next_btn.configure(text="¡Listo! Terminar ✓" if is_last else "Sí, continuar ▶")

    def _next_step(self):
        if self.current_step_idx < len(self.steps) - 1:
            self.current_step_idx += 1
            self._show_step(self.current_step_idx)
        else:
            self._finish("fixed")

    def _prev_step(self):
        if self.current_step_idx > 0:
            self.current_step_idx -= 1
            self._show_step(self.current_step_idx)

    def _on_problem(self):
        # Muestra diálogo con tip extra o sugiere otra solución
        dialog = ctk.CTkInputDialog(
            text="Describe brevemente el problema con este paso:",
            title="¿Qué ocurrió?",
        )
        result = dialog.get_input()
        if result:
            self._finish("partial", notes=result)

    def _finish(self, outcome: str, notes: str = ""):
        self.on_complete(
            printer=self.printer,
            solution=self.solution,
            outcome=outcome,
            steps_completed=self.current_step_idx + 1,
            notes=notes,
        )
        self.destroy()
