"""ChorManager :mod:`chormanager.ui.dialogs` — Qt dialogs (M-3 refactored).

This package replaces the original 1 825 LOC ``chormanager/ui/dialogs.py``
module. The 12 dialog classes have been split into dedicated sub-modules
(``_availability.py``, ``_event.py``, …).  For backward compatibility, the
public ``from chormanager.ui.dialogs import <Class>`` import path is
preserved by the re-exports below.

Class → Sub-module Map
======================

================================  ======================================
Public class                      Sub-module
================================  ======================================
``AvailabilityDelegate``          ``chormanager.ui.dialogs._availability``
``AvailabilityDialog``            ``chormanager.ui.dialogs._availability``
``AVAILABILITY_STATUS`` (const)   ``chormanager.ui.dialogs._availability``
``EventDialog``                   ``chormanager.ui.dialogs._event``
``EventListDialog``               ``chormanager.ui.dialogs._event``
``EventAvailabilityDialog``       ``chormanager.ui.dialogs._event_availability``
``ConfigDialog``                  ``chormanager.ui.dialogs._config``
``SelbstdarstellungDialog``       ``chormanager.ui.dialogs._selbstdarstellung``
``SingerSelectionDialog``         ``chormanager.ui.dialogs._singer_selection``
``DropZone``                      ``chormanager.ui.dialogs._backup_restore``
``BackupRestoreDialog``           ``chormanager.ui.dialogs._backup_restore``
``NewFormationDialog``            ``chormanager.ui.dialogs._new_formation``
``RepertoireDialog``              ``chormanager.ui.dialogs._repertoire``
================================  ======================================

The sub-modules are private (leading underscore) and should not be imported
directly by application code — they are an internal implementation detail of
this package.  Tests, however, may import from the sub-modules when they need
to patch a specific dependency.
"""

# Re-exports for backward compatibility.  Each block corresponds to one
# M-3 extraction step; the order below matches the order in the M-3 plan
# (``plans/2026-06-13_m3_dialogs_refactor.md``).
from ._availability import (
    AVAILABILITY_STATUS,
    AvailabilityDelegate,
    AvailabilityDialog,
)
from ._backup_restore import (
    BackupRestoreDialog,
    DropZone,
)
from ._config import (
    ConfigDialog,
)
from ._event import (
    EventDialog,
    EventListDialog,
)
from ._event_availability import (
    EventAvailabilityDialog,
)
from ._new_formation import (
    NewFormationDialog,
)
from ._repertoire import (
    RepertoireDialog,
)
from ._selbstdarstellung import (
    SelbstdarstellungDialog,
)
from ._singer_selection import (
    SingerSelectionDialog,
)

__all__ = [
    # _availability
    "AvailabilityDelegate",
    "AvailabilityDialog",
    "AVAILABILITY_STATUS",
    # _event
    "EventDialog",
    "EventListDialog",
    # _event_availability
    "EventAvailabilityDialog",
    # _config
    "ConfigDialog",
    # _selbstdarstellung
    "SelbstdarstellungDialog",
    # _singer_selection
    "SingerSelectionDialog",
    # _backup_restore
    "DropZone",
    "BackupRestoreDialog",
    # _new_formation
    "NewFormationDialog",
    # _repertoire
    "RepertoireDialog",
]
