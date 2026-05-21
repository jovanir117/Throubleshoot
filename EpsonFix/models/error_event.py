from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from database.db_manager import Base


class ErrorEvent(Base):
    __tablename__ = "error_events"

    id = Column(Integer, primary_key=True)
    printer_id = Column(Integer, ForeignKey("printer_profiles.id"), nullable=False)
    error_code = Column(String(20), nullable=False)   # "0x97", "paper_jam", "head_clog"
    category = Column(String(30))                      # "waste_ink", "paper", "quality"
    description = Column(Text)
    occurred_at = Column(DateTime, default=datetime.utcnow)
    resolved = Column(Boolean, default=False)
    resolved_at = Column(DateTime)
    session_id = Column(Integer, ForeignKey("repair_sessions.id"))

    printer = relationship("PrinterProfile", back_populates="errors")
    session = relationship("RepairSession", back_populates="error_event", foreign_keys=[session_id])
