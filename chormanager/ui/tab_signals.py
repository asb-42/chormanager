"""A1-SUBPLAN-A — TabSignals(QObject): composition-friendly tab event bus.

The legacy ``TabRouterMixin`` (``chormanager/ui/tab_router.py``) ties
all tab-routing logic to the ``MainWindow`` instance via ``self``
lookups. This module introduces a **signals-only** QObject that new
code can connect to without instantiating a MainWindow, plus a small
``TabDescriptor`` dataclass so the tab→name mapping is testable in
isolation.

The mixin remains the production entry point for backwards
compatibility. ``TabSignals`` is the first step of the A1
migration: once new code starts emitting via ``TabSignals``, the
mixin can be removed without breaking callers.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from PyQt6.QtCore import QObject, pyqtSignal


# Tab indices, kept stable because they are referenced in main.py.
TAB_PROJECTS = 0
TAB_SINGERS = 1
TAB_BESETZUNG = 2
TAB_EVENTS = 3
TAB_AUFSTELLUNG = 4
TAB_REPERTOIRE = 5


@dataclass(frozen=True)
class TabDescriptor:
    """Lightweight description of a tab for menus / toolbars / tests."""
    index: int
    name: str
    short_label: str


DEFAULT_TABS: List[TabDescriptor] = [
    TabDescriptor(TAB_PROJECTS, "Projekte", "Pr"),
    TabDescriptor(TAB_SINGERS, "Sänger", "Sä"),
    TabDescriptor(TAB_BESETZUNG, "Besetzungen", "Be"),
    TabDescriptor(TAB_EVENTS, "Termine", "Te"),
    TabDescriptor(TAB_AUFSTELLUNG, "Aufstellung", "Au"),
    TabDescriptor(TAB_REPERTOIRE, "Repertoire", "Re"),
]


class TabSignals(QObject):
    """Pure signals object for tab events.

    Decouples "what happens when a tab changes" from the QWidget
    that hosts the tabs.  New controllers can subscribe to these
    signals without depending on the full MainWindow.
    """

    #: Emitted whenever the user selects a row in a tab's table.
    selection_changed = pyqtSignal(int, object)  # (tab_index, selection)

    #: Emitted when the active tab changes.
    tab_changed = pyqtSignal(int)  # new tab_index

    #: Emitted when a project becomes active.
    project_changed = pyqtSignal(object)  # Project or None

    #: Emitted when a singer is selected (for context toolbar).
    singer_changed = pyqtSignal(object)  # Singer or None

    #: Emitted when a besetzung becomes active.
    besetzung_changed = pyqtSignal(object)

    #: Emitted when an event is selected.
    event_selected = pyqtSignal(object)


def get_tab_descriptor(index: int) -> Optional[TabDescriptor]:
    """Return the descriptor for ``index`` (or None if out of range)."""
    for tab in DEFAULT_TABS:
        if tab.index == index:
            return tab
    return None
