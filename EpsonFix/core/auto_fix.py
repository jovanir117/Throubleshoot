from __future__ import annotations
from dataclasses import dataclass
import platform
import subprocess


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
            details="Las reparaciones automáticas solo están habilitadas en Windows.",
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


def _run_connectivity_fix() -> AutoFixResult:
    commands = [
        'powershell -Command "Stop-Service spooler -ErrorAction SilentlyContinue"',
        'powershell -Command "Remove-Item -Path $env:windir\\System32\\spool\\PRINTERS\\* -Force -ErrorAction SilentlyContinue"',
        'powershell -Command "Start-Service spooler"',
    ]
    output = _run_commands(commands)
    return AutoFixResult(
        applied=True,
        title="Auto-fix de conectividad aplicado",
        details="Se reinició Print Spooler y se limpió la cola de impresión.\n\n" + output,
    )


def _run_driver_fix() -> AutoFixResult:
    commands = [
        'powershell -Command "Get-Printer | Out-Null"',
        'powershell -Command "pnputil /enum-drivers | Out-Null"',
    ]
    output = _run_commands(commands)
    return AutoFixResult(
        applied=True,
        title="Verificación automática de driver ejecutada",
        details=(
            "Se validó subsistema de impresión. Si persiste, usar wizard para reinstalación limpia del driver Epson.\n\n"
            + output
        ),
    )


def _run_system_fix() -> AutoFixResult:
    commands = [
        'powershell -Command "cleanmgr /AUTOCLEAN"',
        'powershell -Command "Stop-Service spooler -ErrorAction SilentlyContinue; Start-Service spooler"',
    ]
    output = _run_commands(commands)
    return AutoFixResult(
        applied=True,
        title="Auto-fix de sistema aplicado",
        details="Se ejecutó limpieza básica y reinicio de servicios de impresión.\n\n" + output,
    )


def _run_commands(commands: list[str]) -> str:
    logs: list[str] = []
    for cmd in commands:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        logs.append(f"$ {cmd}\nexit={result.returncode}")
        if result.stdout.strip():
            logs.append(result.stdout.strip()[:500])
        if result.stderr.strip():
            logs.append(result.stderr.strip()[:500])
    return "\n".join(logs)
