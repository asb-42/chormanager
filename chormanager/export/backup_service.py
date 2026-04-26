# FILE: chormanager/export/backup_service.py
import zipfile
import shutil
import os
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Tuple, Optional
import json


class BackupFile:
    def __init__(self, source: Path, archive_name: str):
        self.source = source
        self.archive_name = archive_name
        self.mtime = source.stat().st_mtime

    def __repr__(self):
        return f'<BackupFile {self.archive_name} mtime={self.mtime}>'


class BackupService:
    # Dateien, die ins Backup gehören (Pfade relativ zum App-Root)
    BACKUP_FILES = [
        'data/chor.db',
        'data/state.json',
        'config/app.yaml',
        'config/fields.yaml',
        'config/voice_groups.json',
        'config/voice_groups.yaml',
    ]

    # Verzeichnisse, die rekursiv ins Backup gehören
    BACKUP_DIRS = [
        'chormanager/choraufstellung/data',
    ]

    def __init__(self, app_root: Path):
        self.app_root = Path(app_root).expanduser().resolve()

    def _resolve_path(self, rel_path: str) -> Path:
        return self.app_root / rel_path

    def list_backup_files(self) -> List[BackupFile]:
        files = []
        for rel_path in self.BACKUP_FILES:
            p = self._resolve_path(rel_path)
            if p.exists():
                files.append(BackupFile(p, rel_path))
            # else: silently skip missing files (optional config etc.)

        for rel_dir in self.BACKUP_DIRS:
            dir_path = self._resolve_path(rel_dir)
            if dir_path.exists() and dir_path.is_dir():
                for root, _, filenames in os.walk(dir_path):
                    for fname in filenames:
                        fpath = Path(root) / fname
                        archive_name = str(fpath.relative_to(self.app_root))
                        files.append(BackupFile(fpath, archive_name))
        return files

    def create_backup(self, output_path: str) -> str:
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        files = self.list_backup_files()

        with zipfile.ZipFile(output_file, 'w', zipfile.ZIP_DEFLATED) as zf:
            for bf in files:
                zf.write(bf.source, bf.archive_name)

            manifest = {
                'version': '1.0',
                'created_at': datetime.now().isoformat(),
                'app': 'ChorManager',
                'files': [{'name': bf.archive_name, 'mtime': bf.mtime} for bf in files],
            }
            zf.writestr('manifest.json', json.dumps(manifest, indent=2))

        return str(output_file)

    def validate_backup(self, archive_path: str) -> Tuple[bool, str]:
        try:
            with zipfile.ZipFile(archive_path, 'r') as zf:
                result = zf.testzip()
                if result is not None:
                    return False, f'Fehlerhafte Datei im Archiv: {result}'
                return True, 'Archiv ist gültig'
        except zipfile.BadZipFile:
            return False, 'Keine gültige ZIP-Datei'
        except Exception as e:
            return False, f'Fehler beim Lesen: {e}'

    def analyze_restore(self, archive_path: str) -> Dict[str, Dict]:
        changes = {'newer': [], 'older': [], 'same': [], 'new': []}
        local_mtimes = {}

        with zipfile.ZipFile(archive_path, 'r') as zf:
            for member in zf.namelist():
                if member == 'manifest.json' or member.endswith('/'):
                    continue

                archive_mtime = None
                info = zf.getinfo(member)
                if info.date_time:
                    archive_dt = datetime(*info.date_time)
                    archive_mtime = archive_dt.timestamp()

                local_path = self._resolve_path(member)
                local_mtime = local_path.stat().st_mtime if local_path.exists() else None

                entry = {
                    'archive_name': member,
                    'archive_mtime': archive_mtime,
                    'archive_mtime_str': datetime.fromtimestamp(archive_mtime).strftime('%Y-%m-%d %H:%M') if archive_mtime else 'unbekannt',
                    'local_path': str(local_path),
                    'local_mtime': local_mtime,
                    'local_mtime_str': datetime.fromtimestamp(local_mtime).strftime('%Y-%m-%d %H:%M') if local_mtime else 'nicht vorhanden',
                }

                if local_mtime is None:
                    changes['new'].append(entry)
                elif archive_mtime is None:
                    changes['newer'].append(entry)
                elif archive_mtime > local_mtime:
                    changes['newer'].append(entry)
                elif archive_mtime < local_mtime:
                    changes['older'].append(entry)
                else:
                    changes['same'].append(entry)

                local_mtimes[member] = local_mtime

        return changes

    def restore_backup(self, archive_path: str) -> List[str]:
        restored = []
        with zipfile.ZipFile(archive_path, 'r') as zf:
            for member in zf.namelist():
                if member == 'manifest.json' or member.endswith('/'):
                    continue

                target_path = self._resolve_path(member)
                target_path.parent.mkdir(parents=True, exist_ok=True)

                with zf.open(member) as source:
                    with open(target_path, 'wb') as dest:
                        shutil.copyfileobj(source, dest)
                restored.append(member)

        return restored

    def get_backup_size(self, archive_path: str) -> int:
        return Path(archive_path).stat().st_size