"""Pytest bootstrap: make `backend/` importable so `config` and `apps` resolve.

Kept deliberately minimal — shared fixtures belong to the app-level `tests/` packages.
"""

import sys
from pathlib import Path

BACKEND_ROOT: Path = Path(__file__).resolve().parent

if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))
