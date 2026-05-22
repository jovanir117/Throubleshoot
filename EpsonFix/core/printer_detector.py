from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
import csv
import logging
import subprocess
import re


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
    is_usb_hardware: bool = False
    jobs_count: int = 0
    port_name: str = ""


SERIES_PATTERNS = {
    "EcoTank": ["L110", "L120", "L210", "L310", "L380", "L395", "L3110", "L3150", "L3210",
                "L3250", "L4150", "L4160", "L5190", "L6170", "L6190", "L8180", "L4260", "L5290"],
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


def _decode_win32_status(status_mask: int) -> int:
    """Decodifica la máscara de bits de estado de win32print a nuestro código interno."""
    # 0: En línea, 1: En pausa, 2: Error, 3: Eliminando, 4: Sin papel, 5: Sin tinta
    # 6: Cubierta abierta, 7: Atasco de papel, 8: Fuera de línea, 9: Modo de ahorro, 10: Imprimiendo, 11: Calentando
    if status_mask & 0x00000008:   # PRINTER_STATUS_PAPER_JAM
        return 7
    if status_mask & 0x00000010:   # PRINTER_STATUS_PAPER_OUT
        return 4
    if status_mask & 0x00000080:   # PRINTER_STATUS_OFFLINE
        return 8
    if status_mask & 0x00000020:   # PRINTER_STATUS_USER_INTERVENTION
        return 2
    if status_mask & 0x00000001:   # PRINTER_STATUS_PAUSED
        return 1
    if status_mask & 0x00400000:   # PRINTER_STATUS_DOOR_OPEN
        return 6
    if status_mask & (0x00020000 | 0x00040000):  # TONER_LOW / NO_TONER
        return 5
    if status_mask & 0x00000400:   # PRINTER_STATUS_PRINTING
        return 10
    if status_mask & 0x00010000:   # PRINTER_STATUS_WARMING_UP
        return 11
    if status_mask & 0x01000000:   # PRINTER_STATUS_POWER_SAVE
        return 9
    if status_mask & 0x00000002:   # PRINTER_STATUS_ERROR
        return 2
    if status_mask & 0x00000004:   # PRINTER_STATUS_PENDING_DELETION
        return 3
    return 0


def _get_usb_backend():
    """
    Resuelve el backend libusb. Orden de preferencia:
    1. Paquete 'libusb' de PyPI (incluye DLL pre-compilada para Windows)
    2. libusb en PATH / system
    3. Descarga automática del paquete si falta (solo en modo script, no EXE)
    """
    import usb.backend.libusb1 as _lib1

    # Intento 1: paquete libusb de PyPI
    try:
        import libusb
        backend = _lib1.get_backend(find_library=lambda _: libusb.dll._name)
        if backend:
            return backend
    except Exception:
        pass

    # Intento 2: sistema / PATH
    backend = _lib1.get_backend()
    if backend:
        return backend

    # Intento 3: auto-instalar paquete 'libusb' vía pip (solo modo script)
    import sys
    if not getattr(sys, "frozen", False):
        try:
            import subprocess as _sp
            _sp.run(
                [sys.executable, "-m", "pip", "install", "libusb", "--quiet"],
                capture_output=True, timeout=60,
            )
            import importlib
            libusb = importlib.import_module("libusb")
            backend = _lib1.get_backend(find_library=lambda _: libusb.dll._name)
            if backend:
                from core import prefs
                prefs.set("usb_backend_downloaded", True)
                return backend
        except Exception:
            pass

    return None


def _detect_usb_raw() -> list[DetectedPrinter]:
    """Escaneo USB de bajo nivel para Epson (VID 0x04b8). Auto-descarga libusb si falta."""
    printers = []
    try:
        import usb.core
        import usb.util
        backend = _get_usb_backend()
        if backend is None:
            return printers
        devices = usb.core.find(find_all=True, idVendor=0x04b8, backend=backend)
        for dev in devices:
            try:
                product = usb.util.get_string(dev, dev.iProduct) or "Epson USB Device"
                serial = usb.util.get_string(dev, dev.iSerialNumber) or ""
            except Exception as exc:
                _log_detector_warning("usb_descriptor", exc)
                product = "Epson USB Device"
                serial = ""
            model = _extract_model(product) or product
            printers.append(DetectedPrinter(
                system_name=f"Epson USB Hardware (S/N: {serial})" if serial else product,
                driver="Ninguno (Solo hardware)",
                status_code=0, is_online=True,
                model=model, connection="USB", is_usb_hardware=True,
            ))
    except Exception as exc:
        _log_detector_warning("usb_raw", exc)
    return printers


def _detect_wmi() -> list[DetectedPrinter]:
    """Consulta utilizando la biblioteca WMI nativa para obtener detalles extendidos de impresoras."""
    printers = []
    try:
        import wmi
        c = wmi.WMI()
        for p in c.Win32_Printer():
            name = p.Name
            driver = p.DriverName or ""
            if "epson" not in name.lower() and "epson" not in driver.lower():
                continue

            model = _extract_model(name)
            status = p.PrinterStatus or 0
            status_code = 0
            is_online = True

            # Decodificar usando estados de error detectados por WMI
            if p.DetectedErrorState:
                err = p.DetectedErrorState
                if err == 3: status_code = 11  # Calentando / papel bajo
                elif err == 4: status_code = 4  # Sin papel
                elif err == 7: status_code = 6  # Cubierta abierta
                elif err == 8: status_code = 7  # Atasco
                elif err == 9: status_code = 8  # Fuera de línea
                elif err == 10: status_code = 2 # Error crítico
            elif status == 7:
                status_code = 8
                is_online = False
            elif p.WorkOffline or getattr(p, "ExtendedPrinterStatus", 0) == 8:
                status_code = 8
                is_online = False
            elif status == 4:
                status_code = 10

            jobs = p.JobCountSinceLastReset or 0
            printers.append(DetectedPrinter(
                system_name=name,
                driver=driver,
                status_code=status_code,
                is_online=is_online,
                model=model,
                port_name=p.PortName or "",
                jobs_count=jobs
            ))
    except Exception as exc:
        _log_detector_warning("wmi", exc)
    return printers


def _detect_win32print() -> list[DetectedPrinter]:
    import win32print
    printers = []
    flags = win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS
    for info in win32print.EnumPrinters(flags, None, 2):
        name = info["pPrinterName"]
        driver = info.get("pDriverName", "")
        status_mask = info.get("Status", 0)
        jobs = info.get("cJobs", 0)
        port = info.get("pPortName", "")

        if "epson" not in name.lower() and "epson" not in driver.lower():
            continue

        model = _extract_model(name)
        status_code = _decode_win32_status(status_mask)
        printers.append(DetectedPrinter(
            system_name=name,
            driver=driver,
            status_code=status_code,
            is_online=(status_code in (0, 9, 10, 11)),
            model=model,
            port_name=port,
            jobs_count=jobs
        ))
    return printers


def _detect_wmic() -> list[DetectedPrinter]:
    """Fallback con PowerShell Get-Printer (wmic deprecated en Windows 11 24H2)."""
    import json as _json
    printers = []
    try:
        script = (
            "Get-Printer | Where-Object { $_.Name -match 'epson' -or $_.DriverName -match 'epson' } | "
            "Select-Object Name,DriverName,PrinterStatus | ConvertTo-Json -Compress"
        )
        result = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
            capture_output=True, text=True, timeout=15
        )
        if result.returncode != 0 or not result.stdout.strip():
            return printers
        data = _json.loads(result.stdout.strip())
        if isinstance(data, dict):
            data = [data]
        for item in data:
            name = item.get("Name") or ""
            driver = item.get("DriverName") or ""
            status = item.get("PrinterStatus") or 0
            if not name:
                continue
            model = _extract_model(name)
            printers.append(DetectedPrinter(
                system_name=name,
                driver=driver,
                status_code=(8 if status == 7 else 0),
                is_online=(status in (3, 0)),
                model=model,
            ))
    except Exception as exc:
        _log_detector_warning("ps_get_printer", exc)
    return printers


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


def list_printers() -> list[DetectedPrinter]:
    """
    Obtiene la lista de impresoras Epson instaladas o conectadas en el sistema.
    Combina los resultados de win32print, WMI y escaneo USB directo.
    """
    printers_dict = {}

    # 1. Intentar con win32print (es el más confiable para el estado del spooler)
    try:
        for p in _detect_win32print():
            printers_dict[p.system_name] = p
    except Exception as exc:
        _log_detector_warning("win32print", exc)

    # 2. Intentar con WMI (aporta detalles extendidos y DetectedErrorState)
    try:
        for p in _detect_wmi():
            if p.system_name in printers_dict:
                # Combinar datos
                existing = printers_dict[p.system_name]
                if p.status_code != 0:
                    existing.status_code = p.status_code
                if p.jobs_count > 0:
                    existing.jobs_count = p.jobs_count
                if p.port_name:
                    existing.port_name = p.port_name
            else:
                printers_dict[p.system_name] = p
    except Exception as exc:
        _log_detector_warning("wmi_merge", exc)

    # 3. Si no hay nada hasta ahora, usar wmic como fallback de emergencia
    if not printers_dict:
        try:
            for p in _detect_wmic():
                printers_dict[p.system_name] = p
        except Exception as exc:
            _log_detector_warning("wmic", exc)

    # 4. Escaneo USB raw de bajo nivel (para impresoras sin driver instalado o no reconocidas por el spooler)
    try:
        usb_printers = _detect_usb_raw()
        for p in usb_printers:
            # Si ya existe una con nombre similar, no duplicar
            # Pero si no existe en el spooler, agregarla
            already_exists = False
            for existing_name in printers_dict:
                if p.model and p.model.upper() in existing_name.upper():
                    already_exists = True
                    break
            if not already_exists:
                printers_dict[p.system_name] = p
    except Exception as exc:
        _log_detector_warning("usb_merge", exc)

    # Post-procesamiento: setear serie correcta si falta
    for p in printers_dict.values():
        if not p.series:
            p.series = _detect_series(p.model or p.system_name)

    return list(printers_dict.values())


def _log_detector_warning(source: str, exc: Exception) -> None:
    logging.getLogger(__name__).warning("Printer detector %s failed: %s", source, str(exc)[:300])
