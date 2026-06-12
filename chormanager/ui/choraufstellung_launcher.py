"""ChorAufstellung subshell helpers.

Extracted from chormanager.ui.main_window as part of M-1 (God-Class
refactor, see ``plans/2026-06-12_m1_main_window_refactor.md``).

This module hosts two related pieces:

1. ``refresh_tab_repositories`` — a module-level helper that rebinds
   the repositories on a tab to a new ``Database`` instance. Was
   added in M-1 step 3.

2. ``ChorAufstellungLauncherMixin`` — a Mixin that contributes the
   four "open choraufstellung" entry points to the main window:

     * ``_open_choraufstellung``                 → thin wrapper, opens
                                                   with no file.
     * ``_open_choraufstellung_selected_or_new`` → opens the selected
                                                   row's file, or
                                                   falls back to a
                                                   fresh editor.
     * ``_open_choraufstellung_file``            → spawns the subshell
                                                   subprocess with the
                                                   right env vars.
     * ``_open_choraufstellung_for_event``       → builds a temp JSON
                                                   with the available
                                                   singers for an
                                                   event and hands it
                                                   to the subshell.
     * ``_edit_formation``                       → thin wrapper around
                                                   ``self.choraufstellung_tab._edit_formation()``.

   All five were moved here in M-1 step 6 (cluster G in the plan).

The methods are kept byte-for-byte identical to the previous
implementation; only the location changed.

Backward compatibility
----------------------
The module-level ``refresh_tab_repositories`` is re-exported from
``chormanager.ui.main_window`` so the existing test that imports it
continues to work. The Mixin methods are *inherited* (not imported)
so no re-export is needed for them.
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from datetime import datetime


def refresh_tab_repositories(tab, new_db):
    """Rebind every known repository on a tab to a new Database instance.

    Called from MainWindow._reload_after_restore() after a backup has
    been restored. Idempotent: re-creates every repository listed below
    on the given tab and re-points its ``db`` attribute.

    The repository list MUST be kept in sync with the attributes that
    the tab classes initialise in their constructors.
    """
    from ..domain.repository import (
        SingerRepository,
        EventRepository,
        ProjectRepository,
        BesetzungRepository,
        AvailabilityRepository,
        RepertoireRepository,
    )

    if hasattr(tab, 'db'):
        tab.db = new_db
    if hasattr(tab, 'singer_repo'):
        tab.singer_repo = SingerRepository(new_db)
    if hasattr(tab, 'event_repo'):
        tab.event_repo = EventRepository(new_db)
    if hasattr(tab, 'project_repo'):
        tab.project_repo = ProjectRepository(new_db)
    if hasattr(tab, 'besetzung_repo'):
        tab.besetzung_repo = BesetzungRepository(new_db)
    if hasattr(tab, 'avail_repo'):
        tab.avail_repo = AvailabilityRepository(new_db)
    if hasattr(tab, 'repertoire_repo'):
        tab.repertoire_repo = RepertoireRepository(new_db)


class ChorAufstellungLauncherMixin:
    """Mixin that provides the ChorAufstellung-spawning methods.

    Any widget that needs them must inherit from this mixin AND from
    a QWidget-derived class so that ``self.<tab>`` and
    ``self.<label>`` resolve to real Qt attributes.

    The Mixin expects the following attributes on the host (provided
    by ``MainWindow`` in production):

      * ``self.db_path``           (str) — path to the SQLite DB
      * ``self.db``                (Database) — the DB instance
      * ``self.current_project``   (Project | None) — active project
      * ``self.current_event``     (Event | None) — active event
      * ``self.content_stack``     (QStackedWidget) — main tab switch
      * ``self.projects_tab``      (ProjectsTab) — projects view
      * ``self.events_tab``        (EventsTab) — events view
      * ``self.choraufstellung_tab`` (ChorAufstellungTab) — formation
                                                  table
    """

    # ------------------------------------------------------------------
    # Thin wrappers (used by other Mixin methods and by tests)
    # ------------------------------------------------------------------

    def _edit_formation(self):
        self.choraufstellung_tab._edit_formation()

    # ------------------------------------------------------------------
    # Public-ish entry points
    # ------------------------------------------------------------------

    def _open_choraufstellung(self):
        """Open Choraufstellung app with current project/event data."""
        self._open_choraufstellung_file(None)

    def _open_choraufstellung_selected_or_new(self):
        """Open the currently selected formation file, or a fresh
        editor if no row is selected.

        Used by the main-menu 'Aufstellung → In Aufstellung öffnen…'
        entry point (bug-fix 2026-06-12). The previous wiring called
        ``_open_choraufstellung`` directly which always passed
        ``None`` (no CHOR_FILE) and therefore showed an empty grid
        when the user wanted to reopen a saved formation. Now the
        menu action uses the same logic as the context-toolbar /
        right-click 'Bearbeiten' actions: open the selected file if
        one is selected, otherwise fall back to a fresh editor.
        """
        tab = getattr(self, "choraufstellung_tab", None)
        if tab is not None and tab.table.currentRow() >= 0:
            # Delegate to the wrapper used by the context-toolbar /
            # right-click 'Bearbeiten' (it sets CHOR_FILE).
            self._edit_formation()
        else:
            # No selection: original behaviour (fresh editor with
            # current project/event context).
            self._open_choraufstellung()

    # ------------------------------------------------------------------
    # Subprocess spawners
    # ------------------------------------------------------------------

    def _open_choraufstellung_file(self, filepath: str = None):
        """Open ChorAufstellung app, optionally with a specific file."""
        from PyQt6.QtCore import Qt
        from PyQt6.QtWidgets import QMessageBox

        choraufstellung_path = (
            os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            + "/choraufstellung"
        )

        if not os.path.exists(choraufstellung_path):
            QMessageBox.warning(
                self,
                "Fehler",
                f"Choraufstellung nicht gefunden unter:\n choraufstellung_path",
            )
            return

        project = (
            self.projects_tab.current_project if hasattr(self, "projects_tab") else None
        )

        event = None
        event_id = None
        current_row = (
            self.events_tab.table.currentRow() if hasattr(self, "events_tab") else -1
        )

        if current_row >= 0:
            item = self.events_tab.table.item(current_row, 0)
            event_id = item.data(Qt.ItemDataRole.UserRole) if item else None
            if event_id:
                event = self.events_tab.event_repo.get_by_id(event_id)

        vars_to_pass = []
        if project:
            vars_to_pass.append(f"CHOR_PROJECT={project.name}")
        if event:
            vars_to_pass.append(f"CHOR_EVENT_DATE={event.date[:10]}")
            vars_to_pass.append(f"CHOR_EVENT_NAME={event.name}")
            vars_to_pass.append(f"CHOR_EVENT_ID={event.id}")
            vars_to_pass.append(f"CHOR_EVENT_TYPE={event.event_type}")
        if filepath:
            vars_to_pass.append(f"CHOR_FILE={filepath}")

        env = os.environ.copy()
        for var in vars_to_pass:
            key, value = var.split("=", 1)
            env[key] = value

        db_path = self.db_path or os.path.expanduser(
            "~/.local/share/chormanager/chor.db"
        )
        env["CHOR_DB_PATH"] = db_path

        try:
            main_py = os.path.join(choraufstellung_path, "__main__.py")
            if os.path.exists(main_py):
                subprocess.run(
                    [sys.executable, main_py], cwd=choraufstellung_path, env=env
                )
                self.choraufstellung_tab._load_formations()
        except Exception as e:
            QMessageBox.warning(
                self,
                "Fehler",
                f"Choraufstellung konnte nicht gestartet werden:\n{str(e)}",
            )

    def _open_choraufstellung_for_event(self, event):
        """Open ChorAufstellung with event data via temp file."""
        import json

        from PyQt6.QtWidgets import QMessageBox

        from ..domain.repository import AvailabilityRepository, SingerRepository

        self.content_stack.setCurrentIndex(4)

        # 1. Get project
        project = getattr(self, "current_project", None) or (
            self.projects_tab.current_project if hasattr(self, "projects_tab") else None
        )

        # 2. Get repositories
        singer_repo = SingerRepository(self.db)
        avail_repo = AvailabilityRepository(self.db)

        # 3. Get available singers (status=yes or conditional)
        singers = singer_repo.get_all()
        available_singers = []

        for singer in singers:
            avail = avail_repo.get_by_ids(singer.id, event.id)
            if avail and avail.status in ("yes", "conditional"):
                available_singers.append({
                    "singer_id": singer.id,
                    "name": singer.full_name,
                    "short_name": singer.short_name or "",
                    "voice_group": singer.voice_group,
                    "height": singer.height or 0,
                    "affinity": singer.affinity_uuid or ""
                })

        # 3. Prepare data
        data = {
            "project": project.name if project else "",
            "event": {
                "id": event.id,
                "name": event.name,
                "date": event.date,
                "event_type": event.event_type
            },
            "singers": available_singers,
            "created_at": datetime.now().isoformat()
        }

        # 4. Write to temp JSON file
        temp_dir = tempfile.gettempdir()
        temp_file = os.path.join(temp_dir, "choraufstellung_event.json")

        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        # 5. Pass via environment
        env = os.environ.copy()
        env["CHOR_EVENT_DATA"] = temp_file
        env["CHOR_PROJECT"] = data.get("project", "")

        # 6. Also set legacy env vars for compatibility
        if event:
            env["CHOR_EVENT_DATE"] = event.date[:10]
            env["CHOR_EVENT_NAME"] = event.name
            env["CHOR_EVENT_ID"] = event.id
            env["CHOR_EVENT_TYPE"] = event.event_type

        # 7. Get data directory for ChorAufstellung
        choraufstellung_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "..", "choraufstellung"
        )

        # 8. Start ChorAufstellung
        try:
            main_py = os.path.join(choraufstellung_path, "__main__.py")
            if os.path.exists(main_py):
                subprocess.run(
                    [sys.executable, main_py],
                    cwd=choraufstellung_path,
                    env=env
                )
                self.choraufstellung_tab._load_formations()
        except Exception as e:
            QMessageBox.warning(
                self,
                "Fehler",
                f"Choraufstellung konnte nicht gestartet werden:\n{str(e)}"
            )
