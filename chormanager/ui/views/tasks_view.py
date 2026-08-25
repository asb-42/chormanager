"""Aufgaben view: friendly, task-based landing page for ChorManager.

Presents the four core tasks from :mod:`chormanager.domain.taskflow`
as cards in everyday German. Each card shows a live checklist of its
prerequisites and a prominent start button; clicking emits
``task_started(task_id)`` for the MainWindow to open the wizard.

The heavy lifting (dependency evaluation) lives in the Qt-free
taskflow package; this module is presentation only.
"""
from __future__ import annotations

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from ...config import get_theme
from ...data.database import Database
from ...domain.taskflow import (
    StepStatus,
    TaskContext,
    TaskDefinition,
    evaluate_task,
    get_all_tasks,
)

_STATUS_DONE = "\u2713"   # ✓
_STATUS_OPEN = "\u25CB"   # ○

# Per-theme card styling. IMPORTANT: this app themes via a window-wide
# stylesheet only and never installs a dark QPalette, so palette()
# roles resolve to the *light* system palette. Cards therefore carry
# explicit colors per theme. Labels inside the card must be
# transparent, otherwise the global "QWidget { background-color }"
# rule paints dark boxes over the card surface.
_CARD_THEMES = {
    "light": {
        "surface": "#ffffff",
        "border": "#d0d7de",
        "title": "#2c3e50",
        "muted": "#555555",
    },
    "dark": {
        "surface": "#2d2d2d",
        "border": "#404040",
        "title": "#ffffff",
        "muted": "#b0b0b0",
    },
}


def card_stylesheet(theme: str) -> str:
    """Return the TaskCard QSS for ``theme`` (``"light"``/``"dark"``).

    Unknown themes fall back to ``"light"``.
    """
    colors = _CARD_THEMES.get(theme, _CARD_THEMES["light"])
    return f"""
            QFrame#taskCard {{
                background-color: {colors["surface"]};
                border: 1px solid {colors["border"]};
                border-radius: 8px;
            }}
            QFrame#taskCard QLabel {{
                background: transparent;
                color: {colors["muted"]};
            }}
            QFrame#taskCard QLabel#cardTitle {{
                font-size: 13pt;
                font-weight: bold;
                color: {colors["title"]};
            }}
            """


class TaskCard(QFrame):
    """One clickable card representing a single task definition."""

    started = pyqtSignal(object)

    def __init__(self, task: TaskDefinition, parent=None):
        super().__init__(parent)
        self.task = task
        self.setObjectName("taskCard")
        self.apply_theme("light")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(6)

        self.title_label = QLabel(task.title)
        self.title_label.setObjectName("cardTitle")
        self.title_label.setWordWrap(True)
        layout.addWidget(self.title_label)

        self.subtitle_label = QLabel(task.subtitle)
        self.subtitle_label.setWordWrap(True)
        layout.addWidget(self.subtitle_label)

        self.checklist_label = QLabel("")
        self.checklist_label.setWordWrap(True)
        layout.addWidget(self.checklist_label)

        bottom_row = QHBoxLayout()
        self.progress_label = QLabel("")
        bottom_row.addWidget(self.progress_label)
        bottom_row.addStretch()

        self.start_button = QPushButton("Jetzt starten")
        self.start_button.setMinimumHeight(34)
        self.start_button.clicked.connect(lambda: self.started.emit(self.task))
        bottom_row.addWidget(self.start_button)
        layout.addLayout(bottom_row)

    def apply_theme(self, theme: str) -> None:
        """Apply the card stylesheet for ``theme``."""
        self.setStyleSheet(card_stylesheet(theme))

    def update_status(self, context: TaskContext) -> None:
        """Re-evaluate the checklist against ``context``."""
        rows = evaluate_task(self.task, context)
        done, total = 0, len(rows)
        marks = []
        for step, status in rows:
            mark = _STATUS_DONE if status is StepStatus.DONE else _STATUS_OPEN
            marks.append(f"{mark} {step.title}")
            if status is StepStatus.DONE:
                done += 1

        self.checklist_label.setText("   \u00b7   ".join(marks))
        self.progress_label.setText(
            f"{done} von {total} Schritten erledigt"
        )
        self.start_button.setToolTip(
            "Führt Sie durch die fehlenden Schritte."
            if done < total
            else "Alle Vorbedingungen sind erfüllt."
        )


class TasksView(QWidget):
    """Landing page listing all catalog tasks as cards."""

    task_started = pyqtSignal(str)

    def __init__(self, db: Database, parent=None):
        super().__init__(parent)
        self.db = db
        self.cards: list[TaskCard] = []
        self._setup_ui()
        self.refresh()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(10)

        header = QLabel("Was möchten Sie tun?")
        header.setObjectName("pageTitle")
        header.setStyleSheet("font-size: 15pt; font-weight: bold;")
        layout.addWidget(header)

        intro = QLabel(
            "Wählen Sie eine Aufgabe aus – Sie werden Schritt für Schritt "
            "durchgeführt. Fehlende Vorbedingungen werden automatisch "
            "erkannt und gleich mit erledigt."
        )
        intro.setWordWrap(True)
        # No hardcoded text color: the theme stylesheet decides.
        self.intro_label = intro
        layout.addWidget(intro)

        body = QWidget()
        self._cards_layout = QVBoxLayout(body)
        self._cards_layout.setSpacing(12)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidget(body)
        layout.addWidget(scroll, 1)

        for task in get_all_tasks():
            card = TaskCard(task)
            card.started.connect(self._emit_task_started)
            self._cards_layout.addWidget(card)
            self.cards.append(card)
        self._cards_layout.addStretch(1)

    def _emit_task_started(self, task: TaskDefinition) -> None:
        """Re-emit a card click as ``task_started`` with the task id."""
        self.task_started.emit(task.id)

    def refresh(self) -> None:
        """Update card theming and checklists from the current state."""
        try:
            theme = get_theme()
        except Exception:
            theme = "light"
        context = TaskContext(db=self.db)
        for card in self.cards:
            card.apply_theme(theme)
            card.update_status(context)

    def showEvent(self, event) -> None:  # noqa: N802 (Qt naming)
        """Refresh automatically whenever the view becomes visible."""
        super().showEvent(event)
        self.refresh()

    def changeEvent(self, event) -> None:  # noqa: N802 (Qt naming)
        """Re-evaluate cards when the theme (stylesheet) changes."""
        super().changeEvent(event)
        from PyQt6.QtCore import QEvent

        if event.type() == QEvent.Type.StyleChange:
            self.refresh()
