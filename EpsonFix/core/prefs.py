from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

_PREFS_PATH = Path(__file__).parent.parent / "data" / "prefs.json"
_log = logging.getLogger(__name__)

_DEFAULTS: dict[str, Any] = {
    "skipped_version": None,
    "last_update_check": None,
    "usb_backend_downloaded": False,
}


def _load() -> dict:
    try:
        if _PREFS_PATH.exists():
            return {**_DEFAULTS, **json.loads(_PREFS_PATH.read_text(encoding="utf-8"))}
    except Exception as exc:
        _log.warning("prefs load failed: %s", exc)
    return dict(_DEFAULTS)


def _save(data: dict) -> None:
    try:
        _PREFS_PATH.parent.mkdir(exist_ok=True)
        _PREFS_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except Exception as exc:
        _log.warning("prefs save failed: %s", exc)


def get(key: str) -> Any:
    return _load().get(key, _DEFAULTS.get(key))


def set(key: str, value: Any) -> None:
    data = _load()
    data[key] = value
    _save(data)
