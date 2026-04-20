"""Export module for syncing with choraufstellung."""

import csv
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional

from ..data.database import Database
from ..domain.repository import SingerRepository, EventRepository, AvailabilityRepository
from ..config import get_data_dir


def get_sync_dir() -> Path:
    """Get the sync directory.
    
    Returns:
        Path: The sync directory inside app data dir.
    """
    data_dir = get_data_dir()
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


def export_singers_json(db: Database, output_path: Path = None) -> Path:
    """Export singers for choraufstellung sync as JSON.
    
    Creates singers.json with fields: singer_id, name, voice_group, affinity
    
    Args:
        db: Database instance.
        output_path: Optional output path. If None, uses default sync dir.
    
    Returns:
        Path: Path to the exported file.
    """
    if output_path is None:
        output_path = get_sync_dir() / "singers.json"
    
    singer_repo = SingerRepository(db)
    singers = singer_repo.get_all()
    
    data = []
    for singer in singers:
        data.append({
            "singer_id": singer.id,
            "name": singer.short_name or singer.full_name or "",
            "voice_group": singer.voice_group or "",
            "affinity": singer.affinity_uuid or ""
        })
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    return output_path


def export_events_json(db: Database, output_path: Path = None) -> Path:
    """Export events as JSON for choraufstellung.
    
    Args:
        db: Database instance.
        output_path: Optional output path. If None, uses default sync dir.
    
    Returns:
        Path: Path to the exported file.
    """
    if output_path is None:
        output_path = get_sync_dir() / "termine.json"
    
    event_repo = EventRepository(db)
    events = event_repo.get_all()
    
    data = []
    for event in events:
        data.append({
            "event_id": event.id,
            "name": event.name,
            "date": event.date,
            "event_type": event.event_type,
            "description": event.description or ""
        })
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    return output_path


def export_availability_json(db: Database, output_path: Path = None) -> Path:
    """Export availability matrix as JSON for choraufstellung.
    
    Matrix format: For each event, a list of singers with their status.
    
    Args:
        db: Database instance.
        output_path: Optional output path. If None, uses default sync dir.
    
    Returns:
        Path: Path to the exported file.
    """
    if output_path is None:
        output_path = get_sync_dir() / "verfuegbarkeit.json"
    
    singer_repo = SingerRepository(db)
    event_repo = EventRepository(db)
    avail_repo = AvailabilityRepository(db)
    
    singers = singer_repo.get_all()
    events = event_repo.get_all()
    
    matrix = []
    for event in events:
        event_availability = {
            "event_id": event.id,
            "event_name": event.name,
            "date": event.date,
            "event_type": event.event_type,
            "availability": []
        }
        
        for singer in singers:
            avail = avail_repo.get_by_ids(singer.id, event.id)
            status = avail.status if avail else "unknown"
            event_availability["availability"].append({
                "singer_id": singer.id,
                "name": singer.short_name or singer.full_name or "",
                "voice_group": singer.voice_group or "",
                "status": status
            })
        
        matrix.append(event_availability)
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(matrix, f, ensure_ascii=False, indent=2)
    
    return output_path


def export_singers_csv(db: Database, output_path: Path = None) -> Path:
    """Export singers as CSV for choraufstellung fallback.
    
    CSV format compatible with choraufstellung import.
    
    Args:
        db: Database instance.
        output_path: Optional output path.
    
    Returns:
        Path: Path to the exported file.
    """
    if output_path is None:
        output_path = get_sync_dir() / "singers_export.csv"
    
    singer_repo = SingerRepository(db)
    singers = singer_repo.get_all()
    
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["singer_id", "name", "voice_group", "affinity"])
        
        for singer in singers:
            writer.writerow([
                singer.id,
                singer.short_name or singer.full_name or "",
                singer.voice_group or "",
                singer.affinity_uuid or ""
            ])
    
    return output_path


def export_all_sync(db: Database) -> Dict[str, Path]:
    """Export all sync files (singers, events, availability).
    
    Args:
        db: Database instance.
    
    Returns:
        dict: Mapping of export type to file path.
    """
    sync_dir = get_sync_dir()
    
    result = {}
    
    result["singers"] = export_singers_json(db, sync_dir / "singers.json")
    result["termine"] = export_events_json(db, sync_dir / "termine.json")
    result["verfuegbarkeit"] = export_availability_json(db, sync_dir / "verfuegbarkeit.json")
    result["csv_fallback"] = export_singers_csv(db, sync_dir / "singers_export.csv")
    
    return result
