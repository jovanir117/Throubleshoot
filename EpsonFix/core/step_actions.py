import subprocess
import time
from typing import Generator

from core.validation import validate_printer_system_name


POWERSHELL = ["powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command"]


def execute_action(action_key: str, printer_name: str | None = None) -> Generator[str, None, bool]:
    if action_key == "spooler_restart":
        return (yield from _spooler_restart())
    if action_key == "spooler_clear_queue":
        return (yield from _spooler_clear_queue())
    if action_key == "open_preferences":
        return (yield from _open_preferences(printer_name))
    if action_key == "open_queue":
        return (yield from _open_queue(printer_name))
    if action_key == "print_test":
        return (yield from _print_test(printer_name))

    yield f"ERROR: Accion desconocida '{action_key}'."
    return False


def _spooler_restart() -> Generator[str, None, bool]:
    yield "Iniciando reinicio del servicio de cola de impresion (Spooler)..."
    if not _is_admin():
        yield "ERROR: Esta accion requiere ejecutar EpsonFix como Administrador."
        yield "Cierra la app y abre run_epsonfix_admin.bat, o inicia la terminal como Administrador."
        return False
    time.sleep(0.4)

    yield "Deteniendo servicio 'spooler'..."
    r1 = _run_ps("Stop-Service spooler -Force -ErrorAction SilentlyContinue")
    if r1.returncode != 0:
        yield f"Advertencia al detener spooler: {r1.stderr.strip() or 'Acceso denegado (requiere Admin)'}"
    else:
        yield "Servicio detenido con exito."

    time.sleep(0.4)
    yield "Iniciando servicio 'spooler'..."
    r2 = _run_ps("Start-Service spooler")
    if r2.returncode != 0:
        yield f"ERROR al iniciar spooler: {r2.stderr.strip() or 'Acceso denegado'}"
        return False

    yield "Servicio 'spooler' iniciado y funcionando."
    return True


def _spooler_clear_queue() -> Generator[str, None, bool]:
    yield "Iniciando limpieza de cola del spooler..."
    if not _is_admin():
        yield "ERROR: Esta accion requiere ejecutar EpsonFix como Administrador."
        yield "Cierra la app y abre run_epsonfix_admin.bat, o inicia la terminal como Administrador."
        return False
    time.sleep(0.4)

    yield "Deteniendo cola de impresion (Spooler)..."
    stop_result = _run_ps("Stop-Service spooler -Force -ErrorAction SilentlyContinue")
    if stop_result.returncode != 0:
        yield f"Advertencia al detener spooler: {stop_result.stderr.strip() or 'Acceso denegado'}"

    yield "Vaciando archivos de impresion pendientes (.shd / .spl)..."
    clear_result = _clear_spooler_files()
    if clear_result.returncode != 0:
        yield f"ERROR al limpiar spooler: {clear_result.stderr.strip() or clear_result.stdout.strip()}"
        _run_ps("Start-Service spooler")
        return False
    yield "Carpeta PRINTERS limpiada con exito."

    time.sleep(0.4)
    yield "Reiniciando servicio de impresion..."
    r2 = _run_ps("Start-Service spooler")
    if r2.returncode != 0:
        yield f"ERROR al arrancar Spooler: {r2.stderr.strip()}"
        return False

    yield "Cola de impresion limpiada correctamente."
    return True


def _open_preferences(printer_name: str | None) -> Generator[str, None, bool]:
    safe_name = _safe_printer_name(printer_name)
    if not safe_name:
        yield "ERROR: Nombre de impresora invalido o no definido."
        return False

    yield f"Abriendo Preferencias de Impresion para '{safe_name}'..."
    time.sleep(0.3)
    subprocess.Popen(["rundll32.exe", "printui.dll,PrintUIEntry", "/e", "/n", safe_name])
    yield "Comando de preferencias ejecutado en segundo plano."
    return True


def _open_queue(printer_name: str | None) -> Generator[str, None, bool]:
    safe_name = _safe_printer_name(printer_name)
    if not safe_name:
        yield "ERROR: Nombre de impresora invalido o no definido."
        return False

    yield f"Abriendo cola de trabajos de '{safe_name}'..."
    time.sleep(0.3)
    subprocess.Popen(["rundll32.exe", "printui.dll,PrintUIEntry", "/o", "/n", safe_name])
    yield "Cola de trabajos abierta."
    return True


def _print_test(printer_name: str | None) -> Generator[str, None, bool]:
    safe_name = _safe_printer_name(printer_name)
    if not safe_name:
        yield "ERROR: Nombre de impresora invalido o no definido."
        return False

    yield f"Enviando comando de pagina de prueba a '{safe_name}'..."
    time.sleep(0.4)
    r = subprocess.run(
        ["rundll32.exe", "printui.dll,PrintUIEntry", "/k", "/n", safe_name],
        capture_output=True,
        text=True,
        timeout=20,
    )
    if r.returncode != 0:
        yield f"ERROR al imprimir pagina de prueba: {r.stderr.strip() or 'Acceso denegado o impresora no responde'}"
        return False

    yield "Pagina de prueba solicitada correctamente."
    return True


def _run_ps(script: str, timeout: int = 30) -> subprocess.CompletedProcess[str]:
    return subprocess.run(POWERSHELL + [script], capture_output=True, text=True, timeout=timeout)


def _clear_spooler_files() -> subprocess.CompletedProcess[str]:
    script = r"""
$spool = Join-Path $env:windir 'System32\spool\PRINTERS'
$resolved = [System.IO.Path]::GetFullPath($spool)
$expected = [System.IO.Path]::GetFullPath((Join-Path $env:windir 'System32\spool\PRINTERS'))
if ($resolved -ne $expected) { throw "Ruta spooler inesperada: $resolved" }
if (Test-Path -LiteralPath $resolved) {
  Get-ChildItem -LiteralPath $resolved -File -Force |
    Where-Object { $_.Extension -in '.spl','.shd','.tmp' } |
    Remove-Item -Force -ErrorAction Stop
}
"""
    return _run_ps(script, timeout=30)


def _safe_printer_name(printer_name: str | None) -> str | None:
    try:
        return validate_printer_system_name(printer_name)
    except ValueError:
        return None


def _is_admin() -> bool:
    try:
        import ctypes
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False
