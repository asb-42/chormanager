"""Database engine wiring (SQLite now, MariaDB via env later).

The URL comes from ``CHORMANAGER_DATABASE_URL`` (SQLAlchemy form,
e.g. ``sqlite:////path/chor.db`` or ``mysql+pymysql://...``) and
falls back to the desktop database at ``<repo>/data/chor.db``.
Only portable column types are used (see ``tables.py``) so the
same code runs on SQLite and MariaDB/MySQL (Analyse §5.6).
"""
import os
from functools import lru_cache
from pathlib import Path
from typing import Iterator, List, Optional

from sqlalchemy import create_engine
from sqlalchemy.engine import Connection, Engine


def default_db_path() -> str:
    """Fall back to the desktop database next to this repo."""
    return str(Path(__file__).resolve().parents[2] / "data" / "chor.db")


def resolve_db_url(explicit: Optional[str] = None) -> str:
    """Resolve the SQLAlchemy database URL.

    Args:
        explicit: URL override (tests); otherwise the
            ``CHORMANAGER_DATABASE_URL`` env var, otherwise the
            desktop fallback.

    Returns:
        SQLAlchemy database URL string.
    """
    url = explicit or os.environ.get("CHORMANAGER_DATABASE_URL")
    if url:
        return url
    return f"sqlite:///{default_db_path()}"


@lru_cache(maxsize=8)
def get_engine(db_url: Optional[str] = None) -> Engine:
    """Return a cached engine per URL (``cache_clear`` in tests)."""
    engine = create_engine(resolve_db_url(db_url), future=True)
    _TRACKED_ENGINES.append(engine)
    return engine


_TRACKED_ENGINES: List[Engine] = []


def dispose_engines() -> None:
    """Close all pooled connections (needed before restoring the
    DB file; engines stay usable and reconnect lazily)."""
    for engine in _TRACKED_ENGINES:
        engine.dispose()


def get_db() -> Iterator[Connection]:
    """FastAPI dependency: one connection per request."""
    engine = get_engine()
    with engine.connect() as conn:
        yield conn
