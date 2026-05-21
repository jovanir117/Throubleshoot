import customtkinter as ctk
from config import COLORS, FONTS


class ProgressStepper(ctk.CTkFrame):
    """Barra de progreso tipo stepper: ●──●──○──○──○"""

    def __init__(self, parent, total_steps: int, current_step: int = 0, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)
        self.total = total_steps
        self.current = current_step
        self._build()

    def _build(self):
        for widget in self.winfo_children():
            widget.destroy()

        for i in range(self.total):
            col = i * 2
            is_done = i < self.current
            is_active = i == self.current

            if is_active:
                color = COLORS["brand"]
                symbol = "●"
            elif is_done:
                color = COLORS["success"]
                symbol = "✓"
            else:
                color = COLORS["text_secondary"]
                symbol = "○"

            ctk.CTkLabel(
                self,
                text=symbol,
                font=("Segoe UI", 16),
                text_color=color,
            ).grid(row=0, column=col, padx=2)

            if i < self.total - 1:
                line_color = COLORS["success"] if is_done else COLORS["border"]
                ctk.CTkLabel(
                    self,
                    text="────",
                    font=FONTS["small"],
                    text_color=line_color,
                ).grid(row=0, column=col + 1)

    def set_step(self, step: int):
        self.current = step
        self._build()
