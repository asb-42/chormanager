"""
ChorManager Database Access Module

This module provides read-only access to the ChorManager database
for integration with Choraufstellung.

Usage:
    from chormanager_db import ChorManagerDB
    
    db = ChorManagerDB("/path/to/chor.db")
    
    # Get available singers for a project
    singers = db.get_available_singers(project_name="Hoffmann OKO (2026)")
    
    # Get singers for a specific event
    singers = db.get_event_singers(event_date="2026-05-15")
    
    # Get all singers
    all_singers = db.get_all_singers()
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
    
    def get_available_singers(self, project_name: str, event_date: str = None) -> List[Tuple[str, str, str, str]]:
        """Get singers available for a project and event.
        
        Args:
            project_name: Name of the project.
            event_date: Date in YYYY-MM-DD format (optional).
            
        Returns:
            List of (short_name, voice_group, status, singer_id) tuples.
        """
        if event_date:
            query = """
                SELECT s.short_name, s.voice_group, a.status, s.id as singer_id
                FROM singers s
                JOIN availability a ON s.id = a.singer_id
                JOIN events e ON a.event_id = e.id
                JOIN projects p ON e.project_id = p.id
                WHERE p.name = ? AND e.date LIKE ? || '%'
                AND a.status IN ('yes', 'conditional')
                ORDER BY s.voice_group, s.short_name
            """
            results = self._execute(query, (project_name, event_date))
        else:
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
    
    def get_event_singers(self, event_date: str) -> List[Tuple[str, str, str]]:
        """Get singers for a specific event.
        
        Args:
            event_date: Date in YYYY-MM-DD format.
            
        Returns:
            List of (short_name, voice_group, status) tuples.
        """
        query = """
            SELECT s.short_name, s.voice_group, a.status
            FROM singers s
            JOIN availability a ON s.id = a.singer_id
            JOIN events e ON a.event_id = e.id
            WHERE e.date LIKE ? || '%'
            ORDER BY s.voice_group, s.short_name
        """
        results = self._execute(query, (event_date,))
        return [(r['short_name'], r['voice_group'], r['status']) for r in results]
    
    def get_all_singers(self) -> List[Tuple[str, str]]:
        """Get all singers.
        
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


def get_available_singers(project_name: str, event_date: str = None, db_path: str = "~/.local/share/chormanager/chor.db") -> List[Tuple[str, str, str, str]]:
    """Convenience function to get available singers.
    
    Args:
        project_name: Name of the project.
        event_date: Date in YYYY-MM-DD format (optional).
        db_path: Path to the database.
        
    Returns:
        List of (short_name, voice_group, status, singer_id) tuples.
    """
    with ChorManagerDB(db_path) as db:
        return db.get_available_singers(project_name, event_date)


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