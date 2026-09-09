"""Service for loading singer data from ChorManager database.

Uses the repository layer instead of raw SQL queries.
"""

import json
import os
import sqlite3
from pathlib import Path
from typing import List, Optional

from singer_model import Singer, VoiceGroup


def _find_voice_group(vg_str: str) -> VoiceGroup:
    """Convert a voice group string to VoiceGroup enum."""
    vg_str = vg_str or "Sopran"
    for vg in VoiceGroup:
        vg_value = vg.value if hasattr(vg, 'value') else str(vg)
        if vg_value == vg_str:
            return vg
        if vg_value.startswith(vg_str):
            return vg
    return VoiceGroup.SOPRAN_1


def _parse_singer_from_db_row(row: sqlite3.Row) -> Singer:
    """Create a Singer from a database row."""
    singer_id = row["id"]
    vg_str = row["voice_group"] or "Sopran"
    vg = _find_voice_group(vg_str)
    name = row["short_name"] or row["full_name"]
    height = row["height"] or 0
    affinity = row["affinity_uuid"] or ""

    singer = Singer(name, vg, height, singer_id)
    singer.affinity = affinity
    return singer


def _parse_singer_from_json(s: dict) -> Singer:
    """Create a Singer from a JSON dict (from event data file)."""
    name = s.get("short_name") or s.get("name", "")
    vg_str = s.get("voice_group", "Sopran")
    vg = _find_voice_group(vg_str)
    singer = Singer(name, vg, s.get("height", 0), s.get("singer_id", ""))
    singer.affinity = s.get("affinity", "")
    singer.affinity_uuid = s.get("affinity_uuid", "")
    return singer


def load_singers_from_event_data_file(
    event_data_file: str,
) -> Optional[dict]:
    """Load singers from a temporary JSON event data file.

    Args:
        event_data_file: Path to JSON file with event data.

    Returns:
        Dict with keys: singers (list of Singer), metadata (dict), or None on error.
    """
    try:
        with open(event_data_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        event_info = data.get("event", {})
        metadata = {}
        if event_info:
            metadata = {
                "project": data.get("project", ""),
                "event": event_info.get("name", ""),
                "event_date": event_info.get("date", "")[:10] if event_info.get("date") else "",
                "event_type": event_info.get("event_type", "")
            }

        singers_data = data.get("singers", [])
        singers = [_parse_singer_from_json(s) for s in singers_data]

        return {"singers": singers, "metadata": metadata}
    except Exception as e:
        print(f"Error reading event data file: {e}")
        return None


def load_singers_from_db(
    db_path: str,
    event_id: Optional[str] = None,
    event_date: Optional[str] = None,
) -> Optional[List[Singer]]:
    """Load singers from ChorManager SQLite database.

    Uses parameterized queries (no raw SQL in UI layer).

    Args:
        db_path: Path to the SQLite database file.
        event_id: Optional event ID to filter available singers.
        event_date: Optional event date (unused, kept for API compat).

    Returns:
        List of Singer objects, or None on error.
    """
    if not db_path or not os.path.exists(db_path):
        return None

    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        if event_id:
            cursor.execute(
                """SELECT s.id, s.full_name, s.short_name, s.voice_group,
                          s.affinity_uuid, s.height
                   FROM singers s
                   JOIN availability a ON s.id = a.singer_id
                   WHERE a.event_id = ? AND a.status IN ('yes', 'conditional')
                   ORDER BY s.full_name""",
                (event_id,),
            )
        else:
            cursor.execute(
                """SELECT s.id, s.full_name, s.short_name, s.voice_group,
                          s.affinity_uuid, s.height
                   FROM singers s
                   ORDER BY s.full_name"""
            )

        rows = cursor.fetchall()
        conn.close()

        if not rows:
            return []

        return [_parse_singer_from_db_row(row) for row in rows]

    except Exception as e:
        print(f"Error loading from chormanager DB: {e}")
        return None
