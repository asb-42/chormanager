"""ChorManager-Bridge for ChorAufstellung (M-2 Schritt 10).

The bridge encapsulates the two ways ChorAufstellung can be seeded
with singers from the parent ChorManager app:

* **Temp JSON file** (preferred): the launcher writes
  ``CHOR_EVENT_DATA=/tmp/chor_event_<id>.json`` with a payload of
  ``{event: {...}, project: ..., singers: [...]}``.
* **SQLite DB** (fallback): the bridge opens the ChorManager DB and
  runs the ``availability`` + ``singers`` join filtered by ``event_id``.

The host (MainWindow) is mutated by the bridge — it sets
``host.singers``, ``host.pool.singers``, ``host._is_modified`` and
``host._loaded_metadata``.  The bridge **does not** import
:class:`MainWindow`; it relies on duck typing so the same class can
be reused by tests, by the ChorManager launcher, and by future
command-line tooling.

Public surface
--------------
* ``ChorManagerBridge(host)``
* ``ChorManagerBridge.load_from_env()``
* ``ChorManagerBridge.load_from_json(path)``
* ``ChorManagerBridge.load_from_db(path, event_id)``
"""
from __future__ import annotations

import json
import os
import sqlite3
from typing import TYPE_CHECKING, Any, List, Optional

if TYPE_CHECKING:  # pragma: no cover
    pass


# VoiceGroup enum is imported lazily so the module can be loaded
# under the test runner without a Qt event loop.
_VoiceGroup: Any = None
_Singer: Any = None


def _resolve_domain_types() -> None:
    """Lazy lookup of :class:`VoiceGroup` + :class:`Singer` (cached)."""
    global _VoiceGroup, _Singer
    if _VoiceGroup is None or _Singer is None:
        from singer_model import Singer, VoiceGroup  # type: ignore
        _VoiceGroup = VoiceGroup
        _Singer = Singer


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _find_voice_group(vg_to_enum: dict, vg_str: Optional[str]) -> Any:
    """Resolve a string (e.g. ``"Sopran 1"``) to a :class:`VoiceGroup` enum.

    Falls back to a prefix match and finally to ``VoiceGroup.SOPRAN_1``
    so a malformed or missing voice group never crashes the loader.
    """
    VoiceGroup = _VoiceGroup
    vg_str = vg_str or "Sopran"
    if vg_str in vg_to_enum:
        return vg_to_enum[vg_str]
    for vg_name, vg in vg_to_enum.items():
        if vg_name.startswith(vg_str):
            return vg
    return VoiceGroup.SOPRAN_1


def _build_voice_group_map() -> dict:
    """Return ``{voice_group.value: VoiceGroup}`` for the current enum."""
    VoiceGroup = _VoiceGroup
    out: dict = {}
    for vg in VoiceGroup:
        out[vg.value if hasattr(vg, "value") else str(vg)] = vg
    return out


# ---------------------------------------------------------------------------
# the bridge
# ---------------------------------------------------------------------------

class ChorManagerBridge:
    """Encapsulates "load singers from ChorManager" for ChorAufstellung."""

    #: Default location of the ChorManager SQLite database
    DEFAULT_DB_PATH: str = os.path.expanduser(
        "~/.local/share/chormanager/chor.db"
    )

    def __init__(self, host: Any) -> None:
        """Store the host (``MainWindow`` or duck-typed equivalent)."""
        _resolve_domain_types()
        self._host = host

    # ------------------------------------------------------------------
    # public API
    # ------------------------------------------------------------------

    def load_from_env(self) -> bool:
        """Auto-dispatch: try JSON file first, then fall back to DB.

        Honours the following env vars:

        * ``CHOR_EVENT_DATA`` — path to a temp JSON file
        * ``CHOR_DB_PATH``    — path to the ChorManager SQLite DB
          (defaults to :attr:`DEFAULT_DB_PATH`)
        * ``CHOR_EVENT_ID``   — optional filter for the DB query
        """
        # Preferred path: temp JSON file
        json_path = os.environ.get("CHOR_EVENT_DATA", "")
        if json_path and os.path.exists(json_path):
            if self.load_from_json(json_path):
                return True
            # JSON exists but failed to parse — fall through to DB
            # (the original main.py did the same).

        # Fallback: SQLite DB
        db_path = os.environ.get("CHOR_DB_PATH", self.DEFAULT_DB_PATH)
        event_id = (
            getattr(self._host, "event_id", None)
            or os.environ.get("CHOR_EVENT_ID", "")
        )
        return self.load_from_db(db_path, event_id=event_id)

    def load_from_json(self, path: str) -> bool:
        """Read ``path`` (a temp JSON file) and seed the host.

        Returns ``True`` on success, ``False`` on any failure
        (missing file, invalid JSON, empty payload).
        """
        if not path or not os.path.exists(path):
            return False
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as exc:  # noqa: BLE001 — never raise
            print(f"Error reading event data file: {exc}")
            return False

        event_info = data.get("event", {}) or {}
        if event_info:
            self._host._loaded_metadata = {
                "project": data.get("project", ""),
                "event": event_info.get("name", ""),
                "event_date": (event_info.get("date", "") or "")[:10],
                "event_type": event_info.get("event_type", ""),
            }

        singers_data = data.get("singers", []) or []
        if not singers_data:
            return False

        self._host.singers = []
        for s in singers_data:
            singer = self._make_singer_from_dict(s)
            self._host.singers.append(singer)

        self._refresh_pool()
        return True

    def load_from_db(self, db_path: str, event_id: str = "") -> bool:
        """Open the ChorManager SQLite DB and seed the host.

        When ``event_id`` is non-empty, only singers with
        ``availability.status IN ('yes', 'conditional')`` are loaded.
        Returns ``True`` on success, ``False`` when the DB is missing
        or unreadable.
        """
        if not db_path or not os.path.exists(db_path):
            return False
        try:
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            if event_id:
                cur.execute(
                    """
                    SELECT s.id, s.full_name, s.short_name, s.voice_group,
                           s.affinity_uuid, s.height
                    FROM singers s
                    JOIN availability a ON s.id = a.singer_id
                    WHERE a.event_id = ? AND a.status IN ('yes', 'conditional')
                    ORDER BY s.full_name
                    """,
                    (event_id,),
                )
            else:
                cur.execute(
                    """
                    SELECT s.id, s.full_name, s.short_name, s.voice_group,
                           s.affinity_uuid, s.height
                    FROM singers s
                    ORDER BY s.full_name
                    """
                )
            rows = cur.fetchall()
            conn.close()
        except Exception as exc:  # noqa: BLE001 — never raise
            print(f"Error loading from chormanager: {exc}")
            return False

        if not rows:
            return False

        vg_to_enum = _build_voice_group_map()
        self._host.singers = []
        for row in rows:
            vg = _find_voice_group(vg_to_enum, row["voice_group"])
            singer = _Singer(
                row["short_name"] or row["full_name"],
                vg,
                row["height"] or 0,
                row["id"],
            )
            singer.affinity = row["affinity_uuid"] or ""
            self._host.singers.append(singer)

        self._refresh_pool()
        return True

    # ------------------------------------------------------------------
    # private helpers
    # ------------------------------------------------------------------

    def _make_singer_from_dict(self, payload: dict) -> Any:
        """Build a :class:`Singer` from a temp-JSON singer entry."""
        VoiceGroup = _VoiceGroup
        Singer = _Singer
        name = payload.get("short_name") or payload.get("name", "")
        vg_str = payload.get("voice_group", "Sopran")
        vg = next(
            (
                v for v in VoiceGroup
                if hasattr(v, "value") and v.value == vg_str
            ),
            None,
        )
        if not vg:
            vg = VoiceGroup.SOPRAN_1
        singer = Singer(
            name,
            vg,
            payload.get("height", 0),
            payload.get("singer_id", ""),
        )
        singer.affinity = payload.get("affinity", "")
        singer.affinity_uuid = payload.get("affinity_uuid", "")
        return singer

    def _refresh_pool(self) -> None:
        """Push the new singer list into the pool and clear the modified flag."""
        self._host.pool.singers = self._host.singers
        self._host.pool.update_singers(self._host.singers, set())
        self._host._is_modified = False
