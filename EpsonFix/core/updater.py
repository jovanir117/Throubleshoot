from __future__ import annotations

import logging
import os
import subprocess
import sys
import tempfile
import urllib.request
import json
from dataclasses import dataclass
from typing import Optional, Callable

log = logging.getLogger(__name__)

GITHUB_REPO = "jovanir117/Throubleshoot"
ASSET_NAME = "EpsonFix.exe"
API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"


@dataclass
class UpdateInfo:
    current: str
    latest: str
    update_type: str        # "patch" | "minor" | "major"
    release_notes: str
    download_url: str
    tag_name: str

    @property
    def is_silent(self) -> bool:
        return self.update_type == "patch"


def check_for_updates(current_version: str, force: bool = False) -> Optional[UpdateInfo]:
    """
    Query GitHub Releases for a newer version.
    Returns None if up-to-date, skipped, or on network error.
    Pass force=True to ignore skip_version (used by manual "Check updates" button).
    """
    from core import prefs
    from datetime import datetime, timezone

    if not force:
        skipped = prefs.get("skipped_version")
        if skipped and _classify_update(current_version, skipped) == "none":
            return None

    prefs.set("last_update_check", datetime.now(timezone.utc).isoformat())
    try:
        req = urllib.request.Request(
            API_URL,
            headers={"Accept": "application/vnd.github+json", "User-Agent": "EpsonFix-Updater/1.0"},
        )
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode())
    except Exception as exc:
        log.warning("Update check failed: %s", exc)
        return None

    tag = data.get("tag_name", "")
    latest = tag.lstrip("v")
    if not latest:
        return None

    update_type = _classify_update(current_version, latest)
    if update_type == "none":
        return None

    download_url = ""
    for asset in data.get("assets", []):
        if asset.get("name") == ASSET_NAME:
            download_url = asset.get("browser_download_url", "")
            break

    if not download_url:
        log.warning("Release %s found but no %s asset", latest, ASSET_NAME)
        return None

    notes = (data.get("body") or "").strip() or "Sin notas de versión."
    return UpdateInfo(
        current=current_version,
        latest=latest,
        update_type=update_type,
        release_notes=notes,
        download_url=download_url,
        tag_name=tag,
    )


def download_update(info: UpdateInfo, progress_cb: Optional[Callable[[int, int], None]] = None) -> str:
    """Download new EXE to temp. Returns path. Raises on failure."""
    dest = os.path.join(tempfile.gettempdir(), f"EpsonFix_{info.latest}.exe")

    def _report(block_count, block_size, total_size):
        if progress_cb and total_size > 0:
            downloaded = min(block_count * block_size, total_size)
            progress_cb(downloaded, total_size)

    urllib.request.urlretrieve(info.download_url, dest, reporthook=_report)
    return dest


def apply_update(new_exe_path: str) -> None:
    """
    Replace running EXE via detached PowerShell helper, then exit.
    No-op when running as a plain Python script.
    """
    if not getattr(sys, "frozen", False):
        log.info("apply_update skipped — not running as EXE bundle")
        return

    current_exe = os.path.normpath(sys.executable)
    new_exe = os.path.normpath(new_exe_path)
    pid = os.getpid()

    ps = f"""
$ErrorActionPreference = 'Stop'
try {{
    $proc = Get-Process -Id {pid} -ErrorAction SilentlyContinue
    if ($proc) {{ $proc.WaitForExit(30000) }}
    Start-Sleep -Milliseconds 800
    Copy-Item -Force -LiteralPath '{new_exe}' -Destination '{current_exe}'
    Start-Process -FilePath '{current_exe}'
}} catch {{
}} finally {{
    Remove-Item -Force -LiteralPath '{new_exe}' -ErrorAction SilentlyContinue
}}
"""
    script_path = os.path.join(tempfile.gettempdir(), "epsonfix_patch.ps1")
    with open(script_path, "w", encoding="utf-8") as f:
        f.write(ps)

    subprocess.Popen(
        ["powershell", "-NoProfile", "-WindowStyle", "Hidden",
         "-ExecutionPolicy", "Bypass", "-File", script_path],
        creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP,
    )
    sys.exit(0)


def _parse_version(v: str) -> tuple[int, int, int]:
    parts = v.lstrip("v").split(".")
    try:
        major = int(parts[0]) if len(parts) > 0 else 0
        minor = int(parts[1]) if len(parts) > 1 else 0
        patch = int(parts[2]) if len(parts) > 2 else 0
        return major, minor, patch
    except (ValueError, IndexError):
        return 0, 0, 0


def _classify_update(current: str, latest: str) -> str:
    c = _parse_version(current)
    l = _parse_version(latest)
    if l <= c:
        return "none"
    if l[0] > c[0]:
        return "major"
    if l[1] > c[1]:
        return "minor"
    return "patch"
