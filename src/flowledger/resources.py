"""Locate bundled resource files in both source and PyInstaller-frozen runs."""
from __future__ import annotations

import sys
from pathlib import Path


def resource_path(name: str) -> Path:
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent)) / name
    return Path(__file__).resolve().parents[2] / name
