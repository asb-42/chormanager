import json
import os
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime


def _get_data_dir() -> str:
    """Returns data directory in program folder."""
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")


class FormationStorage:
    """Handle saving and loading of choir formations to/from JSON files"""
    
    def __init__(self, filepath: Optional[str] = None):
        self.filepath = filepath
    
    def save_formation(self, singers: List, rows: int, cols: int, 
                       filepath: Optional[str] = None,
                       placed_singers: List[Tuple] = None,
                       staggered: bool = False,
                       voicing_config: List[str] = None,
                       metadata: Dict[str, Any] = None) -> bool:
        """Save formation data to JSON file"""
        target_path = filepath or self.filepath
        if not target_path:
            raise ValueError("No filepath specified")
        
        try:
            placed_ids = set()
            placed_data = []
            if placed_singers:
                for singer, row, col in placed_singers:
                    placed_ids.add(singer.singer_id)
                    placed_data.append({
                        "singer": singer.to_dict(),
                        "row": row,
                        "col": col
                    })
            
            singers_data = []
            for singer in singers:
                if singer.singer_id not in placed_ids:
                    singers_data.append(singer.to_dict())
            
            data = {
                "version": "1.0",
                "saved_at": datetime.now().isoformat(),
                "rows": rows,
                "cols": cols,
                "staggered": staggered,
                "voicing_config": voicing_config or [],
                "singers": singers_data,
                "placed": placed_data,
                "metadata": metadata or {}
            }
            
            directory = os.path.dirname(target_path)
            if directory and not os.path.exists(directory):
                os.makedirs(directory)

            # R-5 Fix: tmp-Cleanup bei Crash zwischen open() und os.replace().
            # Sonst bleibt eine korrupte .tmp-Datei liegen.
            temp_path = target_path + ".tmp"
            try:
                with open(temp_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                os.replace(temp_path, target_path)
            except Exception:
                if os.path.exists(temp_path):
                    try:
                        os.remove(temp_path)
                    except OSError:
                        pass
                raise
            return True
        except Exception as e:
            print(f"Error saving formation: {e}")
            return False
    
    def load_formation(self, filepath: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Load formation data from JSON file"""
        target_path = filepath or self.filepath
        if not target_path:
            raise ValueError("No filepath specified")
            
        if not os.path.exists(target_path):
            print(f"File not found: {target_path}")
            return None
            
        try:
            with open(target_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            from singer_model import Singer
            
            all_singers = []
            placed_list = []
            
            for placed in data.get("placed", []):
                singer_data = placed.get("singer", {})
                sid = singer_data.get("singer_id", "")
                row = placed.get("row", 0)
                col = placed.get("col", 0)
                
                if sid:
                    singer = Singer.from_dict(singer_data)
                    singer.row = row
                    singer.col = col
                    all_singers.append(singer)
                    placed_list.append((singer, row, col))
            
            for singer_data in data.get("singers", []):
                singer = Singer.from_dict(singer_data)
                if singer.row < 0 and singer.col < 0:
                    all_singers.append(singer)
            
            return {
                "rows": data.get("rows", 3),
                "cols": data.get("cols", 4),
                "staggered": data.get("staggered", False),
                "voicing_config": data.get("voicing_config", []),
                "singers": all_singers,
                "placed": placed_list
            }
        except Exception as e:
            print(f"Error loading formation: {e}")
            return None

    # --- AUTOSAVE: Backup-Funktionalität ---
    def _get_backup_dir(self) -> str:
        """Erstellt Backup-Verzeichnis und gibt Pfad zurück."""
        data_dir = _get_data_dir()
        backup_dir = os.path.join(data_dir, "backups")
        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir, exist_ok=True)
        return backup_dir

    def save_autosave(self, data: dict, max_keep: int = 5) -> bool:
        """Speichert Auto-Save mit Zeitstempel und Rotation.

        C-5 Fix: Schreibt den Auto-Save als atomaren File (tmp + os.replace)
        statt als Symlink. Funktioniert auf Windows (kein Admin nötig) und
        ist race-frei. ``get_latest_autosave_path`` ermittelt den neuesten
        ``autosave_<timestamp>.json``-File via ``os.listdir`` + mtime.
        """
        try:
            backup_dir = self._get_backup_dir()
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"autosave_{timestamp}.json"
            filepath = os.path.join(backup_dir, filename)

            # Atomic write: tmp + os.replace (POSIX/Windows-kompatibel)
            tmp_path = filepath + ".tmp"
            with open(tmp_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            os.replace(tmp_path, filepath)

            self._rotate_backups(backup_dir, max_keep)

            return True
        except IOError as e:
            print(f"Auto-save IO error: {e}")
            return False
        except Exception as e:
            print(f"Auto-save error: {e}")
            return False

    def _rotate_backups(self, backup_dir: str, max_keep: int):
        """Löscht älteste Backups, falls mehr als max_keep vorhanden."""
        try:
            autosave_files = [
                f for f in os.listdir(backup_dir) 
                if f.startswith("autosave_") and f.endswith(".json")
            ]
            autosave_files.sort()
            
            while len(autosave_files) > max_keep:
                oldest = autosave_files.pop(0)
                oldest_path = os.path.join(backup_dir, oldest)
                if os.path.exists(oldest_path):
                    os.remove(oldest_path)
        except OSError as e:
            print(f"Backup rotation error: {e}")

    def get_latest_autosave_path(self) -> Optional[str]:
        """Gibt Pfad zum neuesten Auto-Save zurück.

        C-5 Fix: Liest die ``autosave_<timestamp>.json``-Files direkt
        und returnt den mit der jüngsten mtime. Funktioniert ohne
        Symlink und damit auch auf Windows.
        """
        try:
            backup_dir = self._get_backup_dir()
            candidates = [
                f for f in os.listdir(backup_dir)
                if f.startswith("autosave_") and f.endswith(".json")
            ]
            if not candidates:
                return None
            candidates.sort(
                key=lambda f: os.path.getmtime(os.path.join(backup_dir, f)),
                reverse=True,
            )
            return os.path.join(backup_dir, candidates[0])
        except OSError:
            return None

    def get_latest_autosave_mtime(self) -> Optional[float]:
        """Gibt mtime des neuesten Auto-Save zurück."""
        path = self.get_latest_autosave_path()
        if path and os.path.exists(path):
            return os.path.getmtime(path)
        return None

    def delete_latest_autosave(self) -> bool:
        """Löscht den neuesten Auto-Save.

        C-5 Fix: Löscht den jüngsten ``autosave_<timestamp>.json``-File
        statt einen (ehemaligen) Symlink.
        """
        try:
            latest = self.get_latest_autosave_path()
            if latest and os.path.exists(latest):
                os.remove(latest)
            return True
        except OSError as e:
            print(f"Error deleting latest autosave: {e}")
            return False