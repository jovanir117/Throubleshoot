from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
import json
from pathlib import Path


@dataclass
class Diagnosis:
    error_code: str
    category: str
    title: str
    description: str
    confidence: int          # 0-100
    severity: str            # "critical" | "warning" | "info"
    solution_ids: list[int]  # IDs de soluciones recomendadas (ordenadas)


ERROR_CODE_MAP: dict[str, dict] = {
    # Waste ink / contador
    "0x97": {"category": "waste_ink",   "title": "Almohadilla de tinta llena",         "severity": "critical"},
    "0x41": {"category": "waste_ink",   "title": "Error EEPROM / contador saturado",   "severity": "critical"},
    "0x98": {"category": "waste_ink",   "title": "Advertencia de tinta residual",      "severity": "warning"},
    # Paper
    "0x10": {"category": "paper",       "title": "Atasco o error de papel",            "severity": "warning"},
    "0x0a": {"category": "paper",       "title": "Atasco de carro de impresión",       "severity": "warning"},
    # Print head
    "0x09": {"category": "head_clog",   "title": "Error en ciclo de limpieza",         "severity": "warning"},
    "0x27": {"category": "hardware",    "title": "Error de temperatura del cabezal",   "severity": "critical"},
    # Ink / cartridge
    "0x0b": {"category": "ink",         "title": "Cartucho no reconocido",             "severity": "warning"},
    "0x19": {"category": "hardware",    "title": "Error de sensor de temperatura",     "severity": "critical"},
    "0x2a": {"category": "hardware",    "title": "Error de rodillo de tinta",          "severity": "critical"},
    "0x31": {"category": "hardware",    "title": "Error de ventilador de enfriamiento","severity": "critical"},
}

SYMPTOM_MAP: dict[str, str] = {
    "no imprime":            "0x09",
    "rayas":                 "head_clog",
    "rayas horizontales":    "head_clog",
    "colores incorrectos":   "head_clog",
    "papel atorado":         "0x10",
    "atasco":                "0x10",
    "no reconoce cartucho":  "0x0b",
    "cartucho":              "0x0b",
    "luz parpadeando":       "0x97",
    "almohadilla":           "0x97",
    "sin conexion":          "connectivity",
    "sin conexion":          "connectivity",
    "offline":               "connectivity",
    "no aparece":            "driver",
    "driver":                "driver",
    "controlador":           "driver",
}

EXTRA_CODES = {
    "head_clog":     {"category": "head_clog",    "title": "Cabezal de impresión obstruido", "severity": "warning"},
    "connectivity":  {"category": "connectivity", "title": "Problema de conexión",           "severity": "warning"},
    "driver":        {"category": "driver",       "title": "Problema de controlador",        "severity": "warning"},
}


class DiagnosisEngine:
    def __init__(self, db_session):
        self.db = db_session

    def diagnose_by_code(self, code: str) -> Optional[Diagnosis]:
        code = code.strip().lower()
        info = ERROR_CODE_MAP.get(code) or EXTRA_CODES.get(code)
        if not info:
            return None
        solution_ids = self._get_solution_ids(info["category"])
        return Diagnosis(
            error_code=code,
            category=info["category"],
            title=info["title"],
            description=self._build_description(info["category"]),
            confidence=95,
            severity=info["severity"],
            solution_ids=solution_ids,
        )

    def diagnose_by_symptom(self, symptom_text: str) -> Optional[Diagnosis]:
        symptom_lower = symptom_text.lower()
        matched_code = None
        for keyword, code in SYMPTOM_MAP.items():
            if keyword in symptom_lower:
                matched_code = code
                break
        if not matched_code:
            return None
        return self.diagnose_by_code(matched_code)

    def diagnose_smart(self, user_input: str) -> Optional[Diagnosis]:
        """Intenta código directo primero, luego síntoma."""
        stripped = user_input.strip()
        if stripped.startswith("0x") or stripped.startswith("0X"):
            result = self.diagnose_by_code(stripped.lower())
            if result:
                return result
        return self.diagnose_by_symptom(user_input)

    def _get_solution_ids(self, category: str) -> list[int]:
        from models.solution import Solution
        solutions = (
            self.db.query(Solution)
            .filter(Solution.error_code.like(f"%{category}%"))
            .order_by(Solution.success_count.desc())
            .limit(3)
            .all()
        )
        return [s.id for s in solutions]

    def _build_description(self, category: str) -> str:
        desc_map = {
            "waste_ink":    "La almohadilla de tinta residual está llena. Epson bloquea la impresora para evitar derrames. Necesita reset del contador.",
            "paper":        "Hay un atasco o problema con la alimentación del papel. El carro o los rodillos están bloqueados.",
            "head_clog":    "El cabezal de impresión está obstruido. Las boquillas tienen tinta seca que bloquea la salida.",
            "hardware":     "Error de hardware interno. Sensor o componente mecánico con fallo. Puede requerir servicio técnico.",
            "ink":          "Un cartucho no es reconocido. Puede ser por contactos sucios, chip dañado, o cartucho incompatible.",
            "connectivity": "La impresora no aparece en el sistema o perdió la conexión. Puede ser driver, cable, WiFi, o spooler.",
            "driver":       "Problema con el controlador de impresión en Windows.",
        }
        return desc_map.get(category, "Error detectado. Sigue los pasos para resolverlo.")
