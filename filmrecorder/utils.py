from __future__ import annotations

import os
import re
import sys
from pathlib import Path


def resource_path(relative: str | Path) -> Path:
    """Resolve bundled resources in source, PyInstaller one-dir, or one-file layouts.

    PyInstaller 6 normally places one-dir support files below ``_internal``.
    We also ship selected resources beside the executable on Windows. Searching
    each supported layout makes web/assets resilient to packaging changes.
    """
    rel = Path(relative)
    candidates: list[Path] = []
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        candidates.append(Path(meipass) / rel)
    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).resolve().parent
        candidates.extend([exe_dir / rel, exe_dir / "_internal" / rel])
    candidates.extend([Path(__file__).resolve().parents[1] / rel, Path.cwd() / rel])
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0] if candidates else Path(__file__).resolve().parents[1] / rel


def safe_filename_component(value: str, fallback: str) -> str:
    value = (value or "").strip()
    if not value:
        value = fallback
    value = re.sub(r"[^A-Za-z0-9._-]+", "_", value)
    return value.strip("._") or fallback


def format_duration(seconds: float, milliseconds: bool = False) -> str:
    seconds = max(0.0, float(seconds))
    whole = int(seconds)
    hours = whole // 3600
    minutes = (whole % 3600) // 60
    secs = whole % 60
    if milliseconds:
        ms = int((seconds - whole) * 1000.0)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}.{ms:03d}"
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def advance_take_number(current: int, completed: int, maximum: int = 99999) -> int:
    """Return the next slate take after a successful finalization.

    If the operator changed the slate while the completed take was being
    finalized, preserve that newer value instead of overwriting it.
    """
    current = int(current)
    completed = int(completed)
    maximum = max(1, int(maximum))
    if current == completed:
        return min(maximum, completed + 1)
    return current


def app_data_dir() -> Path:
    if sys.platform.startswith("win"):
        root = Path(os.environ.get("LOCALAPPDATA", Path.home()))
        path = root / "FilmSetRecorder"
    elif sys.platform == "darwin":
        path = Path.home() / "Library" / "Application Support" / "FilmSetRecorder"
    else:
        path = Path.home() / ".local" / "share" / "FilmSetRecorder"
    path.mkdir(parents=True, exist_ok=True)
    return path
