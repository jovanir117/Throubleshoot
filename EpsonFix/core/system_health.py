from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import shutil


@dataclass
class SystemHealthReport:
    disk_total_gb: float
    disk_used_gb: float
    disk_free_gb: float
    disk_free_pct: float
    level: str  # "ok" | "warning" | "critical"
    summary: str
    recommendations: list[str]


def get_system_health_report() -> SystemHealthReport:
    usage = shutil.disk_usage(Path.home().anchor or "/")
    total_gb = _bytes_to_gb(usage.total)
    used_gb = _bytes_to_gb(usage.used)
    free_gb = _bytes_to_gb(usage.free)
    free_pct = round((usage.free / usage.total) * 100, 1) if usage.total else 0.0

    if free_pct < 5:
        level = "critical"
    elif free_pct < 15:
        level = "warning"
    else:
        level = "ok"

    summary = (
        f"Estado de almacenamiento: {level.upper()} "
        f"(libre {free_gb:.1f} GB / {total_gb:.1f} GB, {free_pct:.1f}%)."
    )

    recommendations = [
        "Mantén al menos 15% de espacio libre para evitar fallos de spooler y temporales.",
        "Limpia cola de impresión y archivos temporales si hay trabajos atascados.",
        "Evita instalar drivers en unidades casi llenas para prevenir corrupción.",
    ]
    if level != "ok":
        recommendations.insert(0, "Libera espacio en disco antes de repetir el diagnóstico o reinstalar driver.")

    return SystemHealthReport(
        disk_total_gb=total_gb,
        disk_used_gb=used_gb,
        disk_free_gb=free_gb,
        disk_free_pct=free_pct,
        level=level,
        summary=summary,
        recommendations=recommendations,
    )


def _bytes_to_gb(value: int) -> float:
    return value / (1024 ** 3)
