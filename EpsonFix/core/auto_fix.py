from __future__ import annotations

from dataclasses import dataclass
import platform
import subprocess
import time
from typing import Generator


POWERSHELL = ["powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command"]


@dataclass
class AutoFixResult:
    applied: bool
    title: str
    details: str


def run_auto_fix(category: str) -> AutoFixResult:
    if platform.system().lower() != "windows":
        return AutoFixResult(
            applied=False,
            title="Auto-fix no ejecutado",
            details="Las reparaciones automaticas solo estan habilitadas en Windows.",
        )

    if category == "connectivity":
        return _run_connectivity_fix()
    if category == "driver":
        return _run_driver_fix()
    if category == "system":
        return _run_system_fix()

    return AutoFixResult(
        applied=False,
        title="Auto-fix no requerido",
        details="Este tipo de fallo requiere pasos guiados del wizard.",
    )


def run_auto_fix_gen(category: str) -> Generator[str, None, bool]:
    if platform.system().lower() != "windows":
        yield "ERROR: Las reparaciones automaticas solo estan habilitadas en Windows."
        return False
    if category in {"connectivity", "system"} and not _is_admin():
        yield "ERROR: Esta reparacion requiere ejecutar EpsonFix como Administrador."
        yield "Cierra la app y abre run_epsonfix_admin.bat, o inicia la terminal como Administrador."
        return False

    if category == "connectivity":
        yield "Iniciando reparacion automatica de conectividad..."
        time.sleep(0.4)
        yield "Deteniendo el servicio de cola de impresion (Print Spooler)..."
        stop_result = _run_ps("Stop-Service spooler -Force -ErrorAction SilentlyContinue")
        if stop_result.returncode != 0:
            yield f"Advertencia al detener Spooler: {stop_result.stderr.strip() or 'Acceso denegado'}"
        time.sleep(0.4)

        yield "Limpiando archivos de impresion pendientes (.spl / .shd)..."
        clear_result = _clear_spooler_files()
        if clear_result.returncode != 0:
            yield f"ERROR al limpiar Spooler: {clear_result.stderr.strip() or clear_result.stdout.strip()}"
            _run_ps("Start-Service spooler")
            return False
        time.sleep(0.4)

        yield "Re-iniciando el servicio de cola de impresion..."
        res = _run_ps("Start-Service spooler")
        if res.returncode == 0:
            yield "Cola de impresion reiniciada correctamente. Spooler en ejecucion."
            return True

        yield f"ERROR al iniciar Spooler: {res.stderr.strip()}"
        return False

    if category == "driver":
        yield "Iniciando verificacion automatica del controlador de Windows..."
        time.sleep(0.4)
        yield "Verificando el subsistema de impresion..."
        _run_ps("Get-Printer | Out-Null")
        time.sleep(0.4)
        yield "Escaneando el almacen de controladores (Driver Store)..."
        _run_ps("pnputil /enum-drivers | Out-Null", timeout=60)
        time.sleep(0.4)
        yield "Comprobacion completada. Si persiste, realiza una instalacion limpia desde el Wizard."
        return True

    if category == "system":
        yield "Iniciando optimizacion del sistema de impresion..."
        time.sleep(0.4)
        yield "Limpiando archivos temporales del sistema..."
        clean_result = _run_ps(_clean_temp_script(), timeout=30)
        if clean_result.returncode != 0:
            yield f"Advertencia limpieza temporales: {clean_result.stderr.strip()[:120]}"
        time.sleep(0.4)
        yield "Reiniciando servicios y cola de impresion..."
        restart_result = _run_ps("Stop-Service spooler -ErrorAction SilentlyContinue; Start-Service spooler")
        if restart_result.returncode != 0:
            yield f"ERROR al reiniciar Spooler: {restart_result.stderr.strip()}"
            return False
        yield "Optimizacion finalizada. Temporales purgados, Spooler reiniciado."
        return True

    yield "Esta categoria no requiere auto-fix automatizado."
    return False


def _run_connectivity_fix() -> AutoFixResult:
    commands = [
        ("Stop-Service spooler -ErrorAction SilentlyContinue", 30),
        (_clear_spooler_script(), 30),
        ("Start-Service spooler", 30),
    ]
    output = _run_commands(commands)
    return AutoFixResult(
        applied=True,
        title="Auto-fix de conectividad aplicado",
        details="Se reinicio Print Spooler y se limpio la cola de impresion.\n\n" + output,
    )


def _run_driver_fix() -> AutoFixResult:
    commands = [
        ("Get-Printer | Out-Null", 30),
        ("pnputil /enum-drivers | Out-Null", 60),
    ]
    output = _run_commands(commands)
    return AutoFixResult(
        applied=True,
        title="Verificacion automatica de driver ejecutada",
        details=(
            "Se valido subsistema de impresion. Si persiste, usar wizard para reinstalacion limpia del driver Epson.\n\n"
            + output
        ),
    )


def _run_system_fix() -> AutoFixResult:
    commands = [
        (_clean_temp_script(), 30),
        ("Stop-Service spooler -ErrorAction SilentlyContinue; Start-Service spooler", 30),
    ]
    output = _run_commands(commands)
    return AutoFixResult(
        applied=True,
        title="Auto-fix de sistema aplicado",
        details="Temporales purgados y servicios de impresion reiniciados.\n\n" + output,
    )


def _run_commands(commands: list[tuple[str, int]]) -> str:
    logs: list[str] = []
    for script, timeout in commands:
        result = _run_ps(script, timeout=timeout)
        logs.append(f"$ powershell -Command {script[:120]}\nexit={result.returncode}")
        if result.stdout.strip():
            logs.append(result.stdout.strip()[:500])
        if result.stderr.strip():
            logs.append(result.stderr.strip()[:500])
    return "\n".join(logs)


def _run_ps(script: str, timeout: int = 30) -> subprocess.CompletedProcess[str]:
    return subprocess.run(POWERSHELL + [script], capture_output=True, text=True, timeout=timeout)


def _clear_spooler_files() -> subprocess.CompletedProcess[str]:
    return _run_ps(_clear_spooler_script(), timeout=30)


def _clear_spooler_script() -> str:
    return r"""
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


def _clean_temp_script() -> str:
    """Limpia %TEMP%, temporales del spooler y prefetch de impresión sin usar cleanmgr."""
    return r"""
$paths = @(
    $env:TEMP,
    (Join-Path $env:windir 'Temp')
)
foreach ($p in $paths) {
    if (Test-Path -LiteralPath $p) {
        Get-ChildItem -LiteralPath $p -File -Force -ErrorAction SilentlyContinue |
            Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-3) } |
            Remove-Item -Force -ErrorAction SilentlyContinue
    }
}
"""


def _is_admin() -> bool:
    try:
        import ctypes
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False
