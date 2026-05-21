from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
import subprocess


@dataclass
class DetectedPrinter:
    system_name: str
    driver: str = ""
    status_code: int = 0
    is_online: bool = True
    model: Optional[str] = None
    series: Optional[str] = None
    connection: str = "USB"
    ip_address: Optional[str] = None


SERIES_PATTERNS = {
    "EcoTank": ["L110", "L120", "L210", "L310", "L380", "L395", "L3110", "L3150", "L3210",
                "L3250", "L4150", "L4160", "L5190", "L6170", "L6190", "L8180"],
    "WorkForce": ["WF-", "WF2", "WF3", "WF4", "WF5", "WF7", "WF-C"],
    "Expression": ["XP-", "XP2", "XP3", "XP4", "XP6", "XP8"],
    "SureColor": ["SC-", "P400", "P600", "P800", "F130", "F500"],
}


def _detect_series(model: str) -> str:
    model_upper = model.upper()
    for series, patterns in SERIES_PATTERNS.items():
        if any(p.upper() in model_upper for p in patterns):
            return series
    return "Expression"  # default


def _extract_model(printer_name: str) -> Optional[str]:
    """Extrae modelo de nombre del sistema (e.g. 'EPSON L3210 Series' → 'L3210')."""
    import re
    name_upper = printer_name.upper()
    patterns = [
        r"L\d{3,4}",     # EcoTank: L3210, L4260
        r"WF-?\w+",      # WorkForce: WF-2850
        r"XP-?\w+",      # Expression: XP-440
        r"SC-?\w+",      # SureColor
        r"ET-\w+",       # EcoTank US naming
        r"EP-\w+",       # Japonés
    ]
    for p in patterns:
        m = re.search(p, name_upper)
        if m:
            return m.group(0)
    return None


def list_printers() -> list[DetectedPrinter]:
    """Detecta impresoras en Windows. Usa win32print con fallback a WMIC."""
    results: list[DetectedPrinter] = []

    try:
        results = _detect_win32print()
    except Exception:
        pass

    if not results:
        results = _detect_wmic()

    for p in results:
        if p.model:
            p.series = _detect_series(p.model)
        if _is_network_printer(p.system_name):
            p.connection = "WiFi/Network"

    return results


def _detect_win32print() -> list[DetectedPrinter]:
    import win32print
    printers = []
    flags = win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS
    for info in win32print.EnumPrinters(flags, None, 2):
        name = info["pPrinterName"]
        driver = info.get("pDriverName", "")
        status = info.get("Status", 0)
        if "epson" not in name.lower() and "epson" not in driver.lower():
            continue
        model = _extract_model(name)
        printers.append(DetectedPrinter(
            system_name=name,
            driver=driver,
            status_code=status,
            is_online=(status == 0),
            model=model,
        ))
    return printers


def _detect_wmic() -> list[DetectedPrinter]:
    result = subprocess.run(
        ["wmic", "printer", "get", "Name,DriverName,PrinterStatus", "/format:csv"],
        capture_output=True, text=True, timeout=10
    )
    printers = []
    for line in result.stdout.splitlines()[2:]:
        parts = line.strip().split(",")
        if len(parts) < 4:
            continue
        _, driver, name, status_str = parts[0], parts[1], parts[2], parts[3]
        if "epson" not in name.lower() and "epson" not in driver.lower():
            continue
        model = _extract_model(name)
        try:
            status = int(status_str)
        except ValueError:
            status = 0
        printers.append(DetectedPrinter(
            system_name=name,
            driver=driver,
            status_code=status,
            is_online=(status in (3, 0)),
            model=model,
        ))
    return printers


def _is_network_printer(name: str) -> bool:
    return name.startswith("\\\\") or "network" in name.lower() or "wifi" in name.lower()


def get_printer_status_label(status_code: int) -> tuple[str, str]:
    """Devuelve (label, color) para mostrar en UI."""
    status_map = {
        0:  ("En línea", "#2ECC71"),
        1:  ("En pausa", "#F39C12"),
        2:  ("Error", "#E74C3C"),
        3:  ("Eliminando", "#95A5A6"),
        4:  ("Sin papel", "#E74C3C"),
        5:  ("Sin tinta", "#E74C3C"),
        6:  ("Cubierta abierta", "#E74C3C"),
        7:  ("Atasco de papel", "#E74C3C"),
        8:  ("Fuera de línea", "#95A5A6"),
        9:  ("Modo de ahorro", "#3498DB"),
        10: ("Imprimiendo", "#3498DB"),
        11: ("Calentando", "#F39C12"),
    }
    return status_map.get(status_code, ("Desconocido", "#95A5A6"))
