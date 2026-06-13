# M-3 Schritt 1: Re-export wrapper for backward compatibility.
# The 12 dialog classes will be incrementally moved into sub-modules
# (_event.py, _config.py, ...) in M-3 Schritte 2-12. The package-level
# re-exports below keep  working.
"""Dialogs for event management."""


from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QLineEdit,
    QComboBox,
    QDateTimeEdit,
    QTextEdit,
    QPushButton,
    QDialogButtonBox,
    QTableWidget,
    QTableWidgetItem,
    QRadioButton,
    QButtonGroup,
    QLabel,
    QScrollArea,
    QWidget,
    QGroupBox,
    QStyledItemDelegate,
    QSizePolicy,
    QMessageBox,
    QFileDialog,
    QFrame,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QDragEnterEvent, QDropEvent
from PyQt6.QtCore import QDateTime, Qt

from ...domain.repository import (
    SingerRepository,
    AvailabilityRepository,
    EventRepository,
    ProjectRepository,
    RepertoireRepository,
)
from ...config import load_voice_groups

# M-3 Schritt 2: Re-exports for back-compat
from ._availability import (
    AvailabilityDelegate,
    AvailabilityDialog,
    AVAILABILITY_STATUS,
)

# M-3 Schritt 3: Re-exports for back-compat
from ._event import (
    EventDialog,
    EventListDialog,
)

# M-3 Schritt 4: Re-exports for back-compat
from ._event_availability import (
    EventAvailabilityDialog,
)

# M-3 Schritt 5: Re-exports for back-compat
from ._config import (
    ConfigDialog,
)

# M-3 Schritt 6: Re-exports for back-compat
from ._selbstdarstellung import (
    SelbstdarstellungDialog,
)

# M-3 Schritte 7+8: Re-exports for back-compat
from ._singer_selection import (
    SingerSelectionDialog,
)
from ._backup_restore import (
    DropZone,
    BackupRestoreDialog,
)


# M-3 Schritt 9: Re-exports for back-compat
from ._new_formation import (
    NewFormationDialog,
)

# M-3 Schritt 10: Re-exports for back-compat
from ._repertoire import (
    RepertoireDialog,
)
