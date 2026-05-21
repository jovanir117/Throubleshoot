from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
import unicodedata
import re


@dataclass
class Diagnosis:
    error_code: str
    category: str
    title: str
    description: str
    confidence: int          # 0-100
    severity: str            # "critical" | "warning" | "info"
    solution_ids: list[int]  # IDs de soluciones recomendadas (ordenadas)
    probable_causes: list[str]


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
    "no imprime": "head_clog",
    "rayas": "head_clog",
    "rayas horizontales": "head_clog",
    "colores incorrectos": "head_clog",
    "papel atorado": "paper",
    "atasco": "paper",
    "no reconoce cartucho": "ink",
    "cartucho": "ink",
    "luz parpadeando": "waste_ink",
    "almohadilla": "waste_ink",
    "sin conexion": "connectivity",
    "offline": "connectivity",
    "no aparece": "driver",
    "driver": "driver",
    "controlador": "driver",
    "usb no detecta": "connectivity",
    "wifi": "connectivity",
    "no conecta": "connectivity",
    "almacenamiento": "system",
    "disco lleno": "system",
    "lento": "system",
    "computadora lenta": "system",
}

EXTRA_CODES = {
    "head_clog": {"category": "head_clog", "title": "Cabezal de impresión obstruido", "severity": "warning"},
    "connectivity": {"category": "connectivity", "title": "Problema de conexión", "severity": "warning"},
    "driver": {"category": "driver", "title": "Problema de controlador", "severity": "warning"},
    "paper": {"category": "paper", "title": "Atasco o error de papel", "severity": "warning"},
    "ink": {"category": "ink", "title": "Cartucho no reconocido", "severity": "warning"},
    "waste_ink": {"category": "waste_ink", "title": "Almohadilla de tinta llena", "severity": "critical"},
    "hardware": {"category": "hardware", "title": "Error de hardware interno", "severity": "critical"},
    "system": {"category": "system", "title": "Problema del sistema operativo/equipo", "severity": "warning"},
}

CAUSE_MAP: dict[str, list[str]] = {
    "waste_ink": [
        "Contador de almohadilla llegó al límite interno de seguridad.",
        "Acumulación real de tinta residual por ciclos de limpieza frecuentes.",
        "Firmware bloqueó impresión para evitar derrames internos.",
    ],
    "paper": [
        "Fragmentos de papel o cuerpos extraños en el trayecto.",
        "Rodillos sucios/desgastados o mala alineación del papel.",
        "Atasco previo mal retirado dejó residuos.",
    ],
    "head_clog": [
        "Boquillas obstruidas por tinta seca o uso intermitente prolongado.",
        "Aire en líneas de tinta tras recarga o baja tinta.",
        "Calibración pendiente después de limpiezas repetidas.",
    ],
    "ink": [
        "Contactos del cartucho o del carriage sucios/oxidados.",
        "Cartucho incompatible, defectuoso o mal asentado.",
        "Chip de cartucho no leído correctamente por firmware.",
    ],
    "connectivity": [
        "Servicio Print Spooler detenido o cola de impresión corrupta.",
        "Pérdida de red WiFi/USB inestable o puertos en conflicto.",
        "Configuración de impresora fuera de línea en el sistema.",
    ],
    "driver": [
        "Controlador incorrecto, corrupto o desactualizado.",
        "Migraciones de Windows dejaron entradas huérfanas.",
        "Instalación parcial sin utilidades completas del fabricante.",
    ],
    "hardware": [
        "Fallo de sensor interno o sobretemperatura del cabezal.",
        "Motor/ventilador/rodillo con desgaste mecánico.",
        "Error persistente de placa lógica o alimentación.",
    ],
    "system": [
        "Almacenamiento bajo (disco casi lleno) afectando spooler, temporales y drivers.",
        "Servicios de impresión inestables por saturación de recursos del sistema.",
        "Errores del SO por actualizaciones incompletas o archivos temporales corruptos.",
    ],
}


class DiagnosisEngine:
    def __init__(self, db_session):
        self.db = db_session

    def diagnose_by_code(self, code: str) -> Optional[Diagnosis]:
        normalized_code = self._normalize(code)
        info = ERROR_CODE_MAP.get(normalized_code) or EXTRA_CODES.get(normalized_code)
        if not info:
            return None
        category = info["category"]
        solution_ids = self._get_solution_ids(category)
        return Diagnosis(
            error_code=normalized_code,
            category=category,
            title=info["title"],
            description=self._build_description(category),
            confidence=96 if normalized_code.startswith("0x") else 90,
            severity=info["severity"],
            solution_ids=solution_ids,
            probable_causes=CAUSE_MAP.get(category, ["Causa no determinada con precisión."]),
        )

    def diagnose_by_symptom(self, symptom_text: str) -> Optional[Diagnosis]:
        normalized_symptom = self._normalize(symptom_text)
        matched_code, confidence = self._match_symptom(normalized_symptom)
        if not matched_code:
            return None
        diagnosis = self.diagnose_by_code(matched_code)
        if diagnosis:
            diagnosis.confidence = min(diagnosis.confidence, confidence)
        return diagnosis

    def diagnose_smart(self, user_input: str) -> Optional[Diagnosis]:
        """Intenta código directo primero, luego síntoma con matching tolerante."""
        normalized_input = self._normalize(user_input)
        if re.fullmatch(r"0x[0-9a-f]{1,2}", normalized_input):
            result = self.diagnose_by_code(normalized_input)
            if result:
                return result

        direct = self.diagnose_by_code(normalized_input)
        if direct:
            return direct

        return self.diagnose_by_symptom(user_input)

    def _match_symptom(self, symptom: str) -> tuple[Optional[str], int]:
        best_code: Optional[str] = None
        best_score = 0
        tokens = set(symptom.split())
        for keyword, code in SYMPTOM_MAP.items():
            normalized_keyword = self._normalize(keyword)
            if normalized_keyword in symptom:
                score = len(normalized_keyword)
            else:
                key_tokens = set(normalized_keyword.split())
                overlap = len(tokens & key_tokens)
                score = overlap * 3
            if score > best_score:
                best_score = score
                best_code = code

        if not best_code:
            return None, 0

        confidence = max(65, min(90, 55 + best_score))
        return best_code, confidence

    def _get_solution_ids(self, category: str) -> list[int]:
        from models.solution import Solution

        solutions = (
            self.db.query(Solution)
            .filter(Solution.error_code == category)
            .order_by(Solution.success_count.desc(), Solution.attempt_count.desc(), Solution.id.asc())
            .limit(5)
            .all()
        )
        return [s.id for s in solutions]

    def _build_description(self, category: str) -> str:
        desc_map = {
            "waste_ink": "La almohadilla de tinta residual alcanzó su límite. El bloqueo protege el equipo de derrames; se requiere mantenimiento y reinicio del contador.",
            "paper": "Existe obstrucción en la ruta de papel o falla de alimentación. Es clave retirar residuos y validar rodillos para evitar reincidencia.",
            "head_clog": "El cabezal presenta obstrucción en boquillas, normalmente por tinta seca o flujo irregular. Requiere limpieza controlada y verificación de patrón.",
            "hardware": "Se detecta un fallo interno de hardware (sensor/mecánico/electrónico). Si persiste tras reinicio eléctrico, requiere inspección técnica.",
            "ink": "El cartucho no se reconoce por contacto, compatibilidad o chip. Deben limpiarse contactos y validar cartucho correcto.",
            "connectivity": "La impresora perdió comunicación con el sistema (spooler, USB, red o estado offline).",
            "driver": "El controlador está ausente, corrupto o desactualizado. Se recomienda reinstalación limpia del driver oficial.",
            "system": "El problema puede originarse en el sistema anfitrión (almacenamiento/servicios), no solo en la impresora.",
        }
        return desc_map.get(category, "Error detectado. Sigue los pasos para resolverlo.")

    def _normalize(self, value: str) -> str:
        normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
        normalized = normalized.lower().strip()
        normalized = re.sub(r"\s+", " ", normalized)
        return normalized
