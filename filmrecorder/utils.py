from __future__ import annotations

import os
import re
import sys
from pathlib import Path


def resource_path(relative: str | Path) -> Path:
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[1]))
    return base / Path(relative)


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
