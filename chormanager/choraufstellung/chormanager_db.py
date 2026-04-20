"""
ChorManager Database Access Module (Extended)

This module provides read-only access to the ChorManager database
for integration with ChorAufstellung.

Enhanced with:
- singer_id in all singer queries
- affinity_uuid for partner relationships

Usage:
    from chormanager_db import ChorManagerDB
    
    db = ChorManagerDB("/path/to/chor.db")
    
    # Get available singers for a project (now includes singer_id)
    singers = db.get_available_singers(project_name="Hoffmann OKO (2026)")
    # Returns: List[Tuple[str, str, str, str]] = (short_name, voice_group, status, singer_id)
    
    # Get singers for a specific event
    singers = db.get_event_singers(event_date="2026-05-15")
    
    # Get affinity relationships
    affinities = db.get_all_singer_affinities()
    
    # Get all singers with their IDs
    all_singers = db.get_all_singers_with_id()
"""

import sqlite3
from typing import List, Dict, Optional, Tuple
from pathlib import Path


class ChorManagerDB:
    """Read-only access to ChorManager database."""
    
    def __init__(self, db_path: str = "~/.local/share/chormanager/chor.db"):
        """Initialize database connection.
        
        Args:
            db_path: Path to the ChorManager database file.
        """
        self.db_path = Path(db_path).expanduser()
        self._conn = None
    
    def connect(self) -> None:
        """Connect to database in read-only mode."""
        uri = f"file:{self.db_path}?mode=ro"
        self._conn = sqlite3.connect(uri, uri=True)
        self._conn.row_factory = sqlite3.Row
    
    def close(self) -> None:
        """Close database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None
    
    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
    
    def _execute(self, query: str, params: tuple = ()) -> List[Dict]:
        """Execute a query and return results as list of dicts."""
        if not self._conn:
            self.connect()
        
        cursor = self._conn.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]
    
    def get_available_singers(self, project_name: str) -> List[Tuple[str, str, str, str]]:
        """Get singers available for a project.
        
        Args:
            project_name: Name of the project.
            
        Returns:
            List of (short_name, voice_group, status, singer_id) tuples.
        """
        query = """
            SELECT s.short_name, s.voice_group, a.status, s.id as singer_id
            FROM singers s
            JOIN availability a ON s.id = a.singer_id
            JOIN events e ON a.event_id = e.id
            JOIN projects p ON e.project_id = p.id
            WHERE p.name = ? AND a.status IN ('yes', 'conditional')
            ORDER BY s.voice_group, s.short_name
        """
        results = self._execute(query, (project_name,))
        return [(r['short_name'], r['voice_group'], r['status'], r['singer_id']) for r in results]
    
    def get_event_singers(self, event_date: str) -> List[Tuple[str, str, str, str]]:
        """Get singers for a specific event.
        
        Args:
            event_date: Date in YYYY-MM-DD format.
            
        Returns:
            List of (short_name, voice_group, status, singer_id) tuples.
        """
        query = """
            SELECT s.short_name, s.voice_group, a.status, s.id as singer_id
            FROM singers s
            JOIN availability a ON s.id = a.singer_id
            JOIN events e ON a.event_id = e.id
            WHERE e.date LIKE ? || '%'
            ORDER BY s.voice_group, s.short_name
        """
        results = self._execute(query, (event_date,))
        return [(r['short_name'], r['voice_group'], r['status'], r['singer_id']) for r in results]
    
    def get_all_singers(self) -> List[Tuple[str, str]]:
        """Get all singers (short_name, voice_group).
        
        Returns:
            List of (short_name, voice_group) tuples.
        """
        query = """
            SELECT short_name, voice_group
            FROM singers
            WHERE full_name IS NOT NULL AND full_name != ''
            ORDER BY voice_group, short_name
        """
        results = self._execute(query)
        return [(r['short_name'], r['voice_group']) for r in results]
    
    def get_all_singers_with_id(self) -> List[Tuple[str, str, str]]:
        """Get all singers with their IDs.
        
        Returns:
            List of (short_name, voice_group, singer_id) tuples.
        """
        query = """
            SELECT short_name, voice_group, id as singer_id
            FROM singers
            WHERE full_name IS NOT NULL AND full_name != ''
            ORDER BY voice_group, short_name
        """
        results = self._execute(query)
        return [(r['short_name'], r['voice_group'], r['singer_id']) for r in results]
    
    def get_singer_by_id(self, singer_id: str) -> Optional[Dict]:
        """Get singer details by ID.
        
        Args:
            singer_id: The singer ID.
            
        Returns:
            Dictionary with singer details or None if not found.
        """
        query = """
            SELECT id, full_name, short_name, voice_group, affinity_uuid
            FROM singers
            WHERE id = ?
        """
        results = self._execute(query, (singer_id,))
        return results[0] if results else None
    
    def get_singer_by_name(self, short_name: str) -> Optional[Dict]:
        """Get singer details by short name.
        
        Args:
            short_name: The short name of the singer.
            
        Returns:
            Dictionary with singer details or None if not found.
        """
        query = """
            SELECT id, full_name, short_name, voice_group, affinity_uuid
            FROM singers
            WHERE short_name = ?
        """
        results = self._execute(query, (short_name,))
        return results[0] if results else None
    
    def get_all_singer_affinities(self) -> Dict[str, str]:
        """Get all singer affinity relationships.
        
        Returns:
            Dictionary mapping singer_id -> affinity_uuid
        """
        query = """
            SELECT id, affinity_uuid
            FROM singers
            WHERE affinity_uuid IS NOT NULL AND affinity_uuid != ''
        """
        results = self._execute(query)
        return {r['id']: r['affinity_uuid'] for r in results}
    
    def get_singer_affinity(self, singer_id: str) -> Optional[str]:
        """Get the affinity UUID for a specific singer.
        
        Args:
            singer_id: The singer ID.
            
        Returns:
            The affinity UUID or None if not set.
        """
        singer = self.get_singer_by_id(singer_id)
        return singer['affinity_uuid'] if singer else None
    
    def set_singer_affinity(self, singer_id: str, affinity_singer_id: str) -> bool:
        """Set affinity between two singers.
        
        Note: This requires write access to the database.
        
        Args:
            singer_id: The singer ID.
            affinity_singer_id: The ID of the singer to set as affinity partner.
            
        Returns:
            True if successful, False otherwise.
        """
        if not self._conn:
            self.connect()
        
        try:
            self._conn.execute(
                "UPDATE singers SET affinity_uuid = ?, updated_at = datetime('now') WHERE id = ?",
                (affinity_singer_id, singer_id)
            )
            self._conn.commit()
            return True
        except sqlite3.Error:
            return False
    
    def get_projects(self) -> List[str]:
        """Get all project names.
        
        Returns:
            List of project names.
        """
        query = "SELECT name FROM projects ORDER BY name"
        results = self._execute(query)
        return [r['name'] for r in results]
    
    def get_events(self, project_name: Optional[str] = None) -> List[Dict]:
        """Get events, optionally filtered by project.
        
        Args:
            project_name: Optional project name to filter by.
            
        Returns:
            List of event dictionaries.
        """
        if project_name:
            query = """
                SELECT e.id, e.name, e.date, e.event_type, p.name as project_name
                FROM events e
                JOIN projects p ON e.project_id = p.id
                WHERE p.name = ?
                ORDER BY e.date
            """
            return self._execute(query, (project_name,))
        else:
            query = """
                SELECT e.id, e.name, e.date, e.event_type, p.name as project_name
                FROM events e
                LEFT JOIN projects p ON e.project_id = p.id
                ORDER BY e.date
            """
            return self._execute(query)
    
    def get_event_availability_summary(self, event_id: str) -> Dict:
        """Get availability summary for an event.
        
        Args:
            event_id: The event ID.
            
        Returns:
            Dictionary with counts by status.
        """
        query = """
            SELECT status, COUNT(*) as count
            FROM availability
            WHERE event_id = ?
            GROUP BY status
        """
        results = self._execute(query, (event_id,))
        summary = {}
        for r in results:
            summary[r['status']] = r['count']
        return summary


def get_available_singers(project_name: str, db_path: str = "~/.local/share/chormanager/chor.db") -> List[Tuple[str, str, str, str]]:
    """Convenience function to get available singers.
    
    Args:
        project_name: Name of the project.
        db_path: Path to the database.
        
    Returns:
        List of (short_name, voice_group, status, singer_id) tuples.
    """
    with ChorManagerDB(db_path) as db:
        return db.get_available_singers(project_name)


if __name__ == "__main__":
    import sys
    
    db_path = sys.argv[1] if len(sys.argv) > 1 else "~/.local/share/chormanager/chor.db"
    
    print(f"Opening: {db_path}")
    
    with ChorManagerDB(db_path) as db:
        print("\nProjects:")
        for name in db.get_projects():
            print(f"  - {name}")
        
        print("\nEvents:")
        for event in db.get_events():
            print(f"  - {event['date'][:10]} {event['name']} ({event['project_name']})")
        
        print("\nSingers with IDs:")
        for short_name, vg, sid in db.get_all_singers_with_id():
            print(f"  - {short_name} ({vg}): {sid}")
        
        print("\nAffinities:")
        affinities = db.get_all_singer_affinities()
        for sid, affinity in affinities.items():
            print(f"  - {sid} -> {affinity}")