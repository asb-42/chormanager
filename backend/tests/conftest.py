"""Pytest bootstrap for the backend tier (mirrors tests/conftest.py)."""
import sys
from pathlib import Path

_backend_dir = str(Path(__file__).parent.parent)
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)
