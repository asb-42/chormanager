#!/usr/bin/env python3
"""ChorManager - Chorverwaltungsanwendung für Chorleiter.

Usage:
    chormanager                    # Start with default database
    chormanager --db <path>         # Start with specific database
    chormanager --help             # Show this help
"""

import sys
import argparse
from pathlib import Path

from PyQt6.QtWidgets import QApplication

from chormanager.app_logging import setup_logging
from chormanager.ui.main_window import MainWindow


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="ChorManager - Chorverwaltungsanwendung"
    )
    parser.add_argument(
        "--db", "-d",
        help="Path to database file",
        default=None
    )
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging()
    
    db_path = args.db
    
    if db_path is None:
        from chormanager.config import get_data_dir
        data_dir = get_data_dir()
        data_dir.mkdir(parents=True, exist_ok=True)
        
        from chormanager.config import load_app_config
        config = load_app_config()
        db_path = str(data_dir / config.get("database", {}).get("filename", "chor.db"))
    
    app = QApplication(sys.argv)
    
    app.setApplicationName("ChorManager")
    app.setOrganizationName("ChorManager")
    
    window = MainWindow(db_path=db_path)
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
