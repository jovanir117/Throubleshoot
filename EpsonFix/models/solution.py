from sqlalchemy import Column, Integer, String, Boolean, Text, ForeignKey, DateTime, Index
from sqlalchemy.orm import relationship
from datetime import datetime
from database.db_manager import Base


class Solution(Base):
    __tablename__ = "solutions"

    id = Column(Integer, primary_key=True)
    error_code = Column(String(20), nullable=False)
    title = Column(String(150), nullable=False)
    difficulty = Column(String(10), default="easy")    # "easy" | "medium" | "hard"
    estimated_minutes = Column(Integer, default=5)
    requires_admin = Column(Boolean, default=False)
    applicable_series = Column(String(100))            # "EcoTank,WorkForce" o "ALL"
    success_count = Column(Integer, default=0)
    attempt_count = Column(Integer, default=0)

    steps = relationship("SolutionStep", back_populates="solution",
                         order_by="SolutionStep.order", cascade="all, delete-orphan")
    sessions = relationship("RepairSession", back_populates="solution")

    @property
    def success_rate(self):
        if self.attempt_count == 0:
            return 0.0
        return round(self.success_count / self.attempt_count * 100, 1)

    def applies_to(self, series: str) -> bool:
        if not self.applicable_series or self.applicable_series == "ALL":
            return True
        return series in self.applicable_series.split(",")


Index("ix_solutions_error_code", Solution.error_code)


class SolutionStep(Base):
    __tablename__ = "solution_steps"

    id = Column(Integer, primary_key=True)
    solution_id = Column(Integer, ForeignKey("solutions.id"), nullable=False)
    order = Column(Integer, nullable=False)
    title = Column(String(150), nullable=False)
    description = Column(Text, nullable=False)
    image_path = Column(String(300))
    tip = Column(Text)                                 # Tip extra si el paso es confuso
    verification_question = Column(Text)               # "¿Apareció el menú de mantenimiento?"
    action_key = Column(String(50))                    # Identificador de la acción de sistema asociada
    action_label = Column(String(100))                 # Texto para el botón de acción

    solution = relationship("Solution", back_populates="steps")


class RepairSession(Base):
    __tablename__ = "repair_sessions"

    id = Column(Integer, primary_key=True)
    printer_id = Column(Integer, ForeignKey("printer_profiles.id"), nullable=False)
    solution_id = Column(Integer, ForeignKey("solutions.id"))
    error_code = Column(String(20))
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
    outcome = Column(String(20))                       # "fixed" | "partial" | "failed" | "skipped"
    steps_completed = Column(Integer, default=0)
    notes = Column(Text)

    printer = relationship("PrinterProfile", back_populates="sessions")
    solution = relationship("Solution", back_populates="sessions")
    error_event = relationship("ErrorEvent", back_populates="session",
                               foreign_keys="ErrorEvent.session_id")


Index("ix_repair_sessions_printer_started", RepairSession.printer_id, RepairSession.started_at)
Index("ix_repair_sessions_error_code", RepairSession.error_code)
