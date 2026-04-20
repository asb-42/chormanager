"""Data portability service for ChorManager."""

import zipfile
import shutil
import os
from pathlib import Path
from datetime import datetime
from typing import Optional


class PortabilityService:
    """Service for portable data export/import."""
    
    def __init__(self, data_dir: str):
        """Initialize portability service.
        
        Args:
            data_dir: Base data directory.
        """
        self.data_dir = Path(data_dir).expanduser()
    
    def export_data(self, output_path: str) -> str:
        """Export all data to a ZIP archive.
        
        Args:
            output_path: Path to output ZIP file.
            
        Returns:
            str: Path to created archive.
        """
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with zipfile.ZipFile(output_file, "w", zipfile.ZIP_DEFLATED) as zf:
            for root, _, files in os.walk(self.data_dir):
                root_path = Path(root)
                rel_root = root_path.relative_to(self.data_dir)
                
                for file in files:
                    file_path = root_path / file
                    if rel_root == Path("."):
                        arcname = f"data/{file}"
                    else:
                        arcname = f"{rel_root.name}/{file}"
                    zf.write(file_path, arcname)
            
            manifest = {
                "version": "1.0",
                "exported_at": datetime.now().isoformat(),
                "app": "ChorManager"
            }
            import json
            zf.writestr("manifest.json", json.dumps(manifest, indent=2))
        
        return str(output_file)
    
    def import_data(self, archive_path: str, target_dir: Optional[str] = None) -> str:
        """Import data from a ZIP archive.
        
        Args:
            archive_path: Path to ZIP archive.
            target_dir: Target directory. If None, uses data_dir.
            
        Returns:
            str: Path to target directory.
        """
        target = Path(target_dir) if target_dir else self.data_dir
        
        with zipfile.ZipFile(archive_path, "r") as zf:
            for member in zf.namelist():
                if member == "manifest.json":
                    continue
                
                target_path = target / member
                target_path.parent.mkdir(parents=True, exist_ok=True)
                
                if not member.endswith("/"):
                    with zf.open(member) as source:
                        with open(target_path, "wb") as dest:
                            shutil.copyfileobj(source, dest)
        
        return str(target)
    
    def get_export_size(self, archive_path: str) -> int:
        """Get size of archive in bytes.
        
        Args:
            archive_path: Path to archive.
            
        Returns:
            int: Size in bytes.
        """
        return Path(archive_path).stat().st_size