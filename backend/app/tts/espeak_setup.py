from __future__ import annotations

import os
import subprocess
from pathlib import Path


def get_espeak_data_path() -> str | None:
    """Best-effort discovery of espeak-ng data directory on Windows.

    Piper needs access to espeak-ng-data (e.g. phontab) for phonemization.
    If ESPEAK_DATA_PATH is set, we use that.
    Otherwise we try to locate it from common install locations.

    Returns a path to the directory containing 'phontab', or None.
    """

    env = os.getenv("ESPEAK_DATA_PATH")
    if env and (Path(env) / "phontab").exists():
        return env

    candidates = [
        # Common eSpeak NG install
        r"C:\Program Files\eSpeak NG\espeak-ng-data",
        r"C:\Program Files (x86)\eSpeak NG\espeak-ng-data",
        # Sometimes installed as share\espeak-ng-data
        r"C:\Program Files\eSpeak NG\share\espeak-ng-data",
        r"C:\Program Files (x86)\eSpeak NG\share\espeak-ng-data",
        # Legacy eSpeak
        r"C:\Program Files\eSpeak\espeak-data",
        r"C:\Program Files (x86)\eSpeak\espeak-data",
    ]

    for p in candidates:
        if (Path(p) / "phontab").exists():
            return p

    return None


def ensure_espeak_data_env():
    """Set ESPEAK_DATA_PATH if we can auto-detect it."""

    if os.getenv("ESPEAK_DATA_PATH"):
        return

    found = get_espeak_data_path()
    if found:
        os.environ["ESPEAK_DATA_PATH"] = found


def debug_espeak():
    """Optional helper to print espeak-ng version for debugging."""
    try:
        subprocess.run(["espeak-ng", "--version"], check=False, capture_output=True)
    except Exception:
        pass
