"""Import script to import singers from CSV with UUIDs from JSON."""

import json
import csv
import sqlite3
import sys
from pathlib import Path

def load_uuid_mapping(json_path):
    """Load UUID mapping from JSON file."""
    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)
    
    # Use singer_id as key to handle duplicate names
    mapping = {}
    for placed in data.get("placed", []):
        singer = placed.get("singer", {})
        name = singer.get("name", "")
        singer_id = singer.get("singer_id", "")
        if singer_id and name:
            # Store as dict with name and voice_group
            mapping[singer_id] = {
                "name": name,
                "voice_group": singer.get("voice_group", "")
            }
    
    return mapping

def load_voice_groups(json_path):
    """Load valid voice groups from JSON."""
    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)
    
    groups = set()
    for vg in data.get("voice_groups", []):
        name = vg.get("id", "")  # Use "id" instead of "name"
        if name:
            groups.add(name)
    
    return groups

def import_singers(csv_path, json_uuid_path, json_vg_path, db_path):
    """Import singers from CSV with UUIDs from JSON."""
    
    # Load UUID mapping
    uuid_mapping = load_uuid_mapping(json_uuid_path)
    print(f"Loaded {len(uuid_mapping)} UUID mappings")
    
    # Load valid voice groups
    voice_groups = load_voice_groups(json_vg_path)
    print(f"Loaded {len(voice_groups)} valid voice groups")
    
    # Connect to database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check existing singers
    cursor.execute("SELECT COUNT(*) FROM singers")
    existing = cursor.fetchone()[0]
    print(f"Existing singers in database: {existing}")
    
    # Read CSV
    imported = 0
    skipped = 0
    
    with open(csv_path, encoding="utf-8") as f:
        reader = csv.reader(f)
        # Don't skip header - first row is data (no header in CSV)
        
        for row in reader:
            if len(row) < 2:
                continue
            
            short_name = row[0].strip()
            csv_voice_group = row[1].strip()
            
            # Validate voice group
            if csv_voice_group not in voice_groups:
                print(f"Warning: Invalid voice group '{csv_voice_group}' for {short_name}")
                # Still try to import without voice_group
                csv_voice_group = None
            
            # Find singer by name and voice_group from JSON
            singer_match = None
            for uid, info in uuid_mapping.items():
                if info["name"] == short_name and info["voice_group"] == row[1].strip():
                    singer_match = (uid, info)
                    break
            
            if not singer_match:
                print(f"Warning: No match found for {short_name} ({csv_voice_group})")
                skipped += 1
                continue
            
            cursor.execute(
                "SELECT id FROM singers WHERE short_name = ? AND voice_group = ?",
                (short_name, csv_voice_group)
            )
            if cursor.fetchone():
                print(f"Skipping {short_name} - already exists")
                skipped += 1
                continue
            
            import uuid
            singer_id = str(uuid.uuid4())
            
            # Insert singer
            import datetime
            now = datetime.datetime.now().isoformat()
            
            try:
                cursor.execute("""
                    INSERT INTO singers (id, short_name, voice_group, full_name, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (singer_id, short_name, csv_voice_group, short_name, now, now))
                imported += 1
            except Exception as e:
                print(f"Error importing {short_name}: {e}")
                skipped += 1
    
    conn.commit()
    
    # Verify count
    cursor.execute("SELECT COUNT(*) FROM singers")
    total = cursor.fetchone()[0]
    
    conn.close()
    
    print(f"\nImport complete:")
    print(f"  Imported: {imported}")
    print(f"  Skipped: {skipped}")
    print(f"  Total in database: {total}")
    
    return imported, skipped, total

if __name__ == "__main__":
    base_path = Path("/media/data/coding/chormanager")
    
    csv_path = "/media/data/coding/choraufstellung/Inputs/Export.csv"
    json_uuid_path = "/media/data/coding/choraufstellung/Outputs/jugendchor-5.json"
    json_vg_path = base_path / "voice_groups.json"
    # Use default data directory
    db_path = Path.home() / ".local/share/chormanager/chor.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    
    if not db_path.exists():
        print(f"Error: Database not found at {db_path}")
        sys.exit(1)
    
    # Ensure autocommit is enabled
    conn = sqlite3.connect(str(db_path), isolation_level=None)
    conn.close()
    
    import_singers(csv_path, json_uuid_path, json_vg_path, str(db_path))
