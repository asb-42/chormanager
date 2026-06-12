"""ChorAufstellung subshell helpers.

Extracted from chormanager.ui.main_window as part of M-1 (God-Class
refactor, see plans/2026-06-12_m1_main_window_refactor.md step 3).

This module hosts helpers that bridge between the ChorManager main
window and the standalone ``chormanager/choraufstellung/`` subshell
(formation editor). Step 3 moves the module-level
``refresh_tab_repositories`` helper here; later steps (6) will move
the subprocess-spawning code that opens the subshell.

The function is kept byte-for-byte identical to the previous
implementation; only the location changed. A re-export at the
original location
(``chormanager.ui.main_window.refresh_tab_repositories``) is
preserved for backward compatibility with the unit test that
imports it.
"""
from __future__ import annotations


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
