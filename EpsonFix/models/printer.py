from sqlalchemy import Column, Integer, String, DateTime, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from database.db_manager import Base


class PrinterProfile(Base):
    __tablename__ = "printer_profiles"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)        # "Epson L3210 Recepción"
    model = Column(String(50))                           # "L3210"
    series = Column(String(30))                        # "EcoTank"
    connection = Column(String(20), default="USB")     # "USB" | "WiFi" | "Network"
    ip_address = Column(String(45))
    system_name = Column(String(200))                  # Nombre en win32print
    driver_version = Column(String(20))
    added_at = Column(DateTime, default=datetime.utcnow)
    last_seen = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)

    errors = relationship("ErrorEvent", back_populates="printer", cascade="all, delete-orphan")
    sessions = relationship("RepairSession", back_populates="printer", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Printer {self.name} ({self.model})>"

    @property
    def display_series(self):
        series_map = {
            "EcoTank": "EcoTank (L-Series)",
            "WorkForce": "WorkForce (WF)",
            "Expression": "Expression (XP)",
            "SureColor": "SureColor (SC)",
        }
        return series_map.get(self.series, self.series or "Desconocida")
