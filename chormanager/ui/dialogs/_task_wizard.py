""":class:`TaskWizard` — guided, dependency-aware task execution.

The wizard renders a :class:`chormanager.domain.taskflow.TaskDefinition`
as a Qt :class:`QWizard`: an intro page lists all steps with their
current status, followed by one interactive page per *open* step.
Each step page delegates the actual work to an **executor** — a plain
callable ``executor(context) -> entity | None`` — so tests can inject
fakes and the wizard itself stays free of data logic.

Default executors (``build_default_executors``) reuse the existing
ChorManager dialogs (ProjectDialog, EventDialog, SingerSelectionDialog,
EventAvailabilityDialog, SingerDialog) plus two small pick dialogs
(:class:`EventPickDialog`, :class:`BesetzungPickDialog`) defined here.

On acceptance the wizard emits ``task_completed(task_id, context)``;
the MainWindow decides what to launch next (e.g. the Choraufstellung
editor for the ``aufstellung_planen`` task).
"""
from __future__ import annotations

from typing import Any, Callable, Dict, Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
    QWizard,
    QWizardPage,
)

from ...domain.repository import (
    BesetzungRepository,
    EventRepository,
    ProjectRepository,
    SingerRepository,
)
from ...domain.taskflow import (
    StepStatus,
    TaskContext,
    TaskDefinition,
    TaskStep,
    evaluate_task,
    resolve_besetzung,
    resolve_besetzung_for_event,
    resolve_event,
    resolve_project,
)
from ..theme_manager import accent_color
from . import (
    EventAvailabilityDialog,
    EventDialog,
    SingerSelectionDialog,
)

#: Executor signature: receives the context, returns the created or
#: picked entity (truthy = step completed), or None on cancel.
Executor = Callable[[TaskContext], Any]

#: Friendlier button labels for action steps whose title is long.
_BUTTON_OVERRIDES = {
    "verfuegbarkeit_erfassen": "Rückmeldungen öffnen",
    "aufstellung_oeffnen": "Aufstellung öffnen",
    "mitglied_anlegen": "Mitglied anlegen",
    "besetzung_pruefen": "Besetzung wählen \u2026",
}

#: Step-id -> TaskContext attribute the wizard pins automatically when
#: an executor returns a non-boolean entity.
_PIN_TARGETS = {
    "projekt_waehlen": "project",
    "termin_waehlen": "event",
    "termin_anlegen": "event",
    "besetzung_waehlen": "besetzung",
    "besetzung_pruefen": "besetzung",
}

#: Step-id -> resolver for auto-detected entities shown on confirm
#: pages ("bereits erledigt: <entity>").
_DETECTED_RESOLVERS = {
    "projekt_waehlen": resolve_project,
    "termin_waehlen": resolve_event,
    "besetzung_waehlen": resolve_besetzung,
    "besetzung_pruefen": resolve_besetzung_for_event,
}


# ----------------------------------------------------------------------
# pick dialogs (small helpers used by the default executors)
# ----------------------------------------------------------------------

def _format_event(event: Any) -> str:
    """Human-readable combo entry for an event."""
    date_part = (event.date or "")[:10]
    return f"{date_part} \u2013 {event.name}"


class EventPickDialog(QDialog):
    """Pick an existing event or create a new one inline."""

    def __init__(self, db, project=None, parent=None):
        super().__init__(parent)
        self.db = db
        self.project = project
        self.event_repo = EventRepository(db)
        self.setWindowTitle("Termin auswählen")
        self.setMinimumWidth(420)

        layout = QVBoxLayout(self)
        hint = (
            "Welcher Termin ist gemeint? "
            "Oder legen Sie einen neuen an."
        )
        layout.addWidget(QLabel(hint))

        self.combo = QComboBox()
        layout.addWidget(self.combo)

        self.error_label = QLabel("")
        self.error_label.setStyleSheet(f"color: {accent_color('error')};")
        layout.addWidget(self.error_label)

        buttons = QHBoxLayout()
        new_button = QPushButton("Neuen Termin anlegen \u2026")
        new_button.clicked.connect(self._create_new_event)
        buttons.addWidget(new_button)
        buttons.addStretch()

        ok_button = QPushButton("Übernehmen")
        ok_button.setDefault(True)
        ok_button.clicked.connect(self._on_accept)
        cancel_button = QPushButton("Abbrechen")
        cancel_button.clicked.connect(self.reject)
        buttons.addWidget(ok_button)
        buttons.addWidget(cancel_button)
        layout.addLayout(buttons)

        self._load_events()

    def _events(self):
        events = self.event_repo.get_all()
        if self.project is not None:
            events = [
                e for e in events if e.project_id == self.project.id
            ]
        return sorted(events, key=lambda e: e.date or "", reverse=True)

    def _load_events(self) -> None:
        self.combo.clear()
        for event in self._events():
            self.combo.addItem(_format_event(event), event)
        if self.combo.count() > 0:
            self.combo.setCurrentIndex(0)

    def _create_new_event(self) -> None:
        """Open the existing EventDialog and add the created event."""
        prefilled = self.project.id if self.project else None
        dialog = EventDialog(
            db=self.db, parent=self, prefilled_project_id=prefilled
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        data = {k: v for k, v in dialog.get_data().items() if v is not None}
        if not data.get("name"):
            return
        event = self.event_repo.create(**data)
        self.combo.addItem(_format_event(event), event)
        self.combo.setCurrentIndex(self.combo.count() - 1)

    def _on_accept(self) -> None:
        if self.combo.currentData() is None:
            # Non-modal feedback keeps this path testable headless.
            self.error_label.setText(
                "Bitte zuerst einen Termin ausw\u00e4hlen oder anlegen."
            )
            return
        self.accept()

    def get_event(self):
        """Return the selected (or freshly created) event."""
        return self.combo.currentData()


class ProjectPickDialog(QDialog):
    """Pick an existing project or create a new one inline.

    Mirrors :class:`EventPickDialog`/:class:`BesetzungPickDialog` so
    the wizard's project step works for users whose project exists
    but is not currently the active one.
    """

    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.project_repo = ProjectRepository(db)
        self.setWindowTitle("Projekt auswählen")
        self.setMinimumWidth(420)

        layout = QVBoxLayout(self)
        layout.addWidget(
            QLabel("Für welches Projekt wird geplant? "
                   "Oder legen Sie ein neues an.")
        )

        self.combo = QComboBox()
        layout.addWidget(self.combo)

        self.error_label = QLabel("")
        self.error_label.setStyleSheet("color: #b00020;")
        layout.addWidget(self.error_label)

        buttons = QHBoxLayout()
        new_button = QPushButton("Neues Projekt anlegen \u2026")
        new_button.clicked.connect(self._create_new_project)
        buttons.addWidget(new_button)
        buttons.addStretch()

        ok_button = QPushButton("Übernehmen")
        ok_button.setDefault(True)
        ok_button.clicked.connect(self._on_accept)
        cancel_button = QPushButton("Abbrechen")
        cancel_button.clicked.connect(self.reject)
        buttons.addWidget(ok_button)
        buttons.addWidget(cancel_button)
        layout.addLayout(buttons)

        self._load_projects()

    def _load_projects(self) -> None:
        self.combo.clear()
        for project in self.project_repo.get_all():
            label = project.name or project.id
            if project.spielzeit:
                label = f"{label} ({project.spielzeit})"
            self.combo.addItem(label, project)
        if self.combo.count() > 0:
            self.combo.setCurrentIndex(0)

    def _create_new_project(self) -> None:
        """Open the existing ProjectDialog and add the new project."""
        from ..views.projects_tab import ProjectDialog

        dialog = ProjectDialog(self.db, parent=self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        data = dialog.get_data()
        if not data.get("name"):
            return
        project = self.project_repo.create(**data)
        self.combo.addItem(project.name, project)
        self.combo.setCurrentIndex(self.combo.count() - 1)

    def _on_accept(self) -> None:
        if self.combo.currentData() is None:
            self.error_label.setText(
                "Bitte zuerst ein Projekt ausw\u00e4hlen oder anlegen."
            )
            return
        self.accept()

    def get_project(self):
        """Return the selected (or freshly created) project."""
        return self.combo.currentData()


def _sync_active_project(db, project, parent) -> None:
    """Make ``project`` the UI's active project (both sources).

    Updates the config key (info bar, tab filters) via
    ``projects_tab.set_current_project`` when a MainWindow is
    reachable, and keeps the legacy ``projects.is_active`` flag in
    sync. Regression guard for the "Keines vs. bereits vorhanden"
    divergence.
    """
    main_window = parent.window() if parent is not None else None
    projects_tab = getattr(main_window, "projects_tab", None)
    if projects_tab is not None:
        projects_tab.set_current_project(project)
    else:
        from ...config import set_last_active_project_id

        set_last_active_project_id(project.id)
    ProjectRepository(db).set_active(project.id)


class BesetzungPickDialog(QDialog):
    """Pick an existing besetzung or assemble a new one inline."""

    def __init__(self, db, project=None, parent=None):
        super().__init__(parent)
        self.db = db
        self.project = project
        self.besetzung_repo = BesetzungRepository(db)
        self.setWindowTitle("Besetzung auswählen")
        self.setMinimumWidth(420)

        layout = QVBoxLayout(self)
        layout.addWidget(
            QLabel(
                "Welche Sängergruppe soll verwendet werden? "
                "Bestehende Besetzungen können übernommen werden."
            )
        )

        self.combo = QComboBox()
        layout.addWidget(self.combo)

        self.error_label = QLabel("")
        self.error_label.setStyleSheet(f"color: {accent_color('error')};")
        layout.addWidget(self.error_label)

        buttons = QHBoxLayout()
        new_button = QPushButton("Neue Besetzung zusammenstellen \u2026")
        new_button.clicked.connect(self._create_new_besetzung)
        buttons.addWidget(new_button)
        buttons.addStretch()

        ok_button = QPushButton("Übernehmen")
        ok_button.setDefault(True)
        ok_button.clicked.connect(self._on_accept)
        cancel_button = QPushButton("Abbrechen")
        cancel_button.clicked.connect(self.reject)
        buttons.addWidget(ok_button)
        buttons.addWidget(cancel_button)
        layout.addLayout(buttons)

        self._load_besetzungen()

    def _besetzungen(self):
        if self.project is not None:
            return self.besetzung_repo.get_by_project(self.project.id)
        return self.besetzung_repo.get_all()

    def _load_besetzungen(self) -> None:
        self.combo.clear()
        for besetzung in self._besetzungen():
            count = len(besetzung.get_singer_ids())
            self.combo.addItem(
                f"{besetzung.name} ({count} Sänger)", besetzung
            )
        if self.combo.count() > 0:
            self.combo.setCurrentIndex(0)

    def _create_new_besetzung(self) -> None:
        """Ask for a name, let the user pick singers, store it."""
        from PyQt6.QtWidgets import QInputDialog

        name, ok = QInputDialog.getText(
            self, "Neue Besetzung", "Name der Besetzung:"
        )
        if not ok or not name.strip():
            return

        dialog = SingerSelectionDialog(
            self.db, besetzung_name=name.strip(), parent=self
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        singer_ids = dialog.get_selected_ids()
        if not singer_ids:
            self.error_label.setText(
                "Bitte mindestens einen S\u00e4nger ausw\u00e4hlen."
            )
            return

        project_id = self.project.id if self.project else None
        if project_id is None:
            self.error_label.setText(
                "Daf\u00fcr wird zuerst ein Projekt ben\u00f6tigt."
            )
            return
        besetzung = self.besetzung_repo.create(
            name.strip(), project_id, singer_ids
        )
        self.combo.addItem(f"{besetzung.name}", besetzung)
        self.combo.setCurrentIndex(self.combo.count() - 1)

    def _on_accept(self) -> None:
        if self.combo.currentData() is None:
            self.error_label.setText(
                "Bitte zuerst eine Besetzung ausw\u00e4hlen oder anlegen."
            )
            return
        self.accept()

    def get_besetzung(self):
        """Return the selected (or freshly created) besetzung."""
        return self.combo.currentData()


# ----------------------------------------------------------------------
# default executors
# ----------------------------------------------------------------------

def build_default_executors(
    db, parent: Optional[QWidget] = None
) -> Dict[str, Executor]:
    """Build the production executor map for all catalog step ids.

    Every executor reuses an existing ChorManager dialog and pins its
    result into the shared :class:`TaskContext`.
    """
    def do_project(context: TaskContext):
        # Pick an existing project or create one; then make it the
        # UI's active project (config + info bar + DB flag in sync).
        dialog = ProjectPickDialog(db, parent=parent)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return None
        project = dialog.get_project()
        if project is None:
            return None
        _sync_active_project(db, project, parent)
        return project

    def do_termin(context: TaskContext):
        dialog = EventPickDialog(db, context.project, parent=parent)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return None
        return dialog.get_event()

    def do_besetzung(context: TaskContext):
        dialog = BesetzungPickDialog(db, context.project, parent=parent)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return None
        besetzung = dialog.get_besetzung()
        if besetzung is not None:
            from ...config import set_last_active_besetzung_id

            set_last_active_besetzung_id(besetzung.id)
        return besetzung

    def do_besetzung_pruefen(context: TaskContext):
        """Confirm/choose the besetzung matching the pinned termin."""
        event = context.event
        if event is None:
            return None
        if not event.project_id:
            QMessageBox.information(
                parent,
                "Termin ohne Projekt",
                "Der Termin gehört zu keinem Projekt. Im nächsten "
                "Schritt werden alle aktiven Sänger angezeigt.",
            )
            return True
        project = ProjectRepository(db).get_by_id(event.project_id)
        dialog = BesetzungPickDialog(db, project, parent=parent)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return None
        besetzung = dialog.get_besetzung()
        if besetzung is not None:
            from ...config import set_last_active_besetzung_id

            set_last_active_besetzung_id(besetzung.id)
        return besetzung

    def do_verfuegbarkeit(context: TaskContext):
        from ...config import get_last_active_besetzung_id
        from ...domain.taskflow import resolve_event

        event = resolve_event(context)
        if event is None:
            QMessageBox.information(
                parent,
                "Kein Termin",
                "Bitte zuerst einen Termin festlegen.",
            )
            return None

        # Mirror events_tab: filter the dialog to the besetzung that
        # was pinned/confirmed earlier in the wizard (fallback: the
        # last active besetzung), so only the right singers appear.
        besetzung = context.besetzung
        if besetzung is None and context.db is not None:
            from ...domain.repository import BesetzungRepository

            saved_id = get_last_active_besetzung_id()
            if saved_id:
                besetzung = BesetzungRepository(context.db).get_by_id(
                    saved_id
                )

        besetzung_ids = None
        besetzung_name = None
        besetzung_count = 0
        if besetzung is not None:
            besetzung_ids = besetzung.get_singer_ids()
            besetzung_name = besetzung.name
            besetzung_count = len(besetzung_ids)

        dialog = EventAvailabilityDialog(
            db,
            event,
            parent,
            besetzung_ids=besetzung_ids,
            besetzung_name=besetzung_name,
            besetzung_count=besetzung_count,
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return None
        return True

    def do_mitglied(context: TaskContext):
        from ..forms.singer_dialog import SingerDialog

        dialog = SingerDialog(parent=parent, db=db)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return None
        data = {
            k: v for k, v in dialog.get_data().items() if v is not None
        }
        singer = SingerRepository(db).create(**data)
        return singer

    def do_aufstellung_oeffnen(context: TaskContext):
        # The actual editor launch happens in MainWindow's
        # task_completed handler; this only completes the wizard.
        return True

    def do_termin_neu(context: TaskContext):
        """Create a NEW termin via the existing EventDialog."""
        prefilled = context.project.id if context.project else None
        dialog = EventDialog(
            db=db, parent=parent, prefilled_project_id=prefilled
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return None
        data = {
            k: v for k, v in dialog.get_data().items() if v is not None
        }
        if not data.get("name"):
            return None
        return EventRepository(db).create(**data)

    return {
        "projekt_waehlen": do_project,
        "termin_waehlen": do_termin,
        "termin_anlegen": do_termin_neu,
        "besetzung_waehlen": do_besetzung,
        "besetzung_pruefen": do_besetzung_pruefen,
        "verfuegbarkeit_erfassen": do_verfuegbarkeit,
        "mitglied_anlegen": do_mitglied,
        "aufstellung_oeffnen": do_aufstellung_oeffnen,
    }


# ----------------------------------------------------------------------
# wizard pages
# ----------------------------------------------------------------------

class _IntroPage(QWizardPage):
    """Non-interactive overview listing every step and its status."""

    def __init__(self, task: TaskDefinition, context: TaskContext,
                 parent=None):
        super().__init__(parent)
        self.setTitle(task.title)
        layout = QVBoxLayout(self)

        subtitle = QLabel(task.subtitle)
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)

        lines = [""]
        for step, status in evaluate_task(task, context):
            mark = "\u2713" if status is StepStatus.DONE else "\u25cb"
            suffix = " (bereits vorhanden)" if mark == "\u2713" else ""
            lines.append(f"{mark} {step.title}{suffix}")
        lines.append("")
        lines.append(
            "Die Schritte werden nun nacheinander abgefragt. Bereits "
            "vorhandene Vorbedingungen bestätigen Sie mit einem Klick "
            "– oder wählen etwas anderes."
        )

        self.summary_label = QLabel("\n".join(lines))
        self.summary_label.setWordWrap(True)
        layout.addWidget(self.summary_label)
        layout.addStretch()


class _StepPage(QWizardPage):
    """Interactive page for one step.

    Two modes:

    * **Open step** – a single action button runs the executor.
    * **Satisfied step** – shows *what* was auto-detected and requires
      an explicit confirmation ("Diese Auswahl verwenden") or offers
      "Anderes auswählen …" (runs the executor). Nothing is ever
      silently pre-checked.
    """

    def __init__(self, wizard_host: "TaskWizard", step: TaskStep,
                 parent=None):
        super().__init__(parent)
        self._host = wizard_host
        self.step = step
        self._executed = False

        self.setTitle(step.title)
        layout = QVBoxLayout(self)

        description = QLabel(step.description)
        description.setWordWrap(True)
        layout.addWidget(description)

        self.detected_label = QLabel("")
        self.detected_label.setWordWrap(True)
        self.detected_label.setStyleSheet(
            f"color: {accent_color('success')};"
        )
        layout.addWidget(self.detected_label)

        self.status_label = QLabel("")
        self.status_label.setWordWrap(True)
        self.status_label.setStyleSheet(
            f"color: {accent_color('success')};"
        )
        layout.addWidget(self.status_label)

        row = QHBoxLayout()
        self.use_button = QPushButton("Diese Auswahl verwenden")
        self.use_button.clicked.connect(self.confirm_detected)
        row.addWidget(self.use_button)

        self.action_button = QPushButton(
            _BUTTON_OVERRIDES.get(step.id, "Jetzt erledigen \u2026")
        )
        self.action_button.clicked.connect(self.run_executor)
        row.addWidget(self.action_button)
        row.addStretch()
        layout.addLayout(row)
        layout.addStretch()

        self._refresh_mode()

    # ------------------------------------------------------------------
    # mode handling
    # ------------------------------------------------------------------

    def _is_satisfied(self) -> bool:
        return self.step.is_done(self._host.context)

    def _detected_entity(self):
        resolver = _DETECTED_RESOLVERS.get(self.step.id)
        if resolver is None:
            return None
        try:
            return resolver(self._host.context)
        except Exception:
            return None

    def _detected_text(self) -> str:
        entity = self._detected_entity()
        if entity is None:
            return "\u2713 Bereits vorhanden."
        name = getattr(entity, "name", None) or str(entity)
        return f"\u2713 Bereits vorhanden: {name}"

    def _refresh_mode(self) -> None:
        if self._executed:
            self.status_label.setText("\u2713 Erledigt.")
            return
        if self._is_satisfied():
            self.detected_label.setText(self._detected_text())
            self.use_button.setVisible(True)
            self.action_button.setText(
                _BUTTON_OVERRIDES.get(self.step.id,
                                      "Anderes ausw\u00e4hlen \u2026")
            )
        else:
            self.detected_label.setText("")
            self.use_button.setVisible(False)
            self.action_button.setText(
                _BUTTON_OVERRIDES.get(self.step.id,
                                      "Jetzt erledigen \u2026")
            )

    def initializePage(self) -> None:  # noqa: N802 (Qt naming)
        """Refresh the detected-state right before showing."""
        self._refresh_mode()

    # ------------------------------------------------------------------
    # actions
    # ------------------------------------------------------------------

    def confirm_detected(self) -> None:
        """Accept the auto-detected entity and complete the step."""
        if self._executed:
            return
        target = _PIN_TARGETS.get(self.step.id)
        if target is not None:
            entity = self._detected_entity()
            if entity is not None:
                setattr(self._host.context, target, entity)
        self._executed = True
        self.use_button.setVisible(False)
        self.action_button.setVisible(False)
        self.detected_label.setText("")
        self.status_label.setText("\u2713 Erledigt.")
        self.completeChanged.emit()

    def run_executor(self) -> None:
        """Invoke the step's executor, pin its result, record success."""
        executor = self._host._executors.get(self.step.id)
        if executor is None:
            self.status_label.setStyleSheet(
                f"color: {accent_color('error')};"
            )
            self.status_label.setText(
                "Interner Fehler: kein Ablauf hinterlegt."
            )
            return
        result = executor(self._host.context)
        if result:
            target = _PIN_TARGETS.get(self.step.id)
            if target is not None and not isinstance(result, bool):
                setattr(self._host.context, target, result)
            self._executed = True
            self.use_button.setVisible(False)
            self.status_label.setText("\u2713 Erledigt.")
            self.completeChanged.emit()

    def isComplete(self) -> bool:  # noqa: N802 (Qt naming)
        # Deliberately NOT satisfied-check based: an auto-detected
        # prerequisite stays incomplete until the user confirms or
        # replaces it (no silent pre-checking).
        return self._executed


# ----------------------------------------------------------------------
# the wizard itself
# ----------------------------------------------------------------------

class TaskWizard(QWizard):
    """Step-by-step wizard for one :class:`TaskDefinition`.

    Emits ``task_completed(task_id, context)`` when accepted.
    """

    task_completed = pyqtSignal(str, object)

    def __init__(
        self,
        db,
        task: TaskDefinition,
        parent=None,
        executors: Optional[Dict[str, Executor]] = None,
        context: Optional[TaskContext] = None,
    ):
        super().__init__(parent)
        self.db = db
        self.task = task
        self.context = context if context is not None else TaskContext(db=db)
        self._executors: Dict[str, Executor] = (
            executors
            if executors is not None
            else build_default_executors(db, self)
        )
        self.step_pages: Dict[str, _StepPage] = {}

        self.setWindowTitle(f"Aufgabe: {task.title}")
        self.setWizardStyle(QWizard.WizardStyle.ClassicStyle)
        self.setOption(QWizard.WizardOption.NoBackButtonOnStartPage, True)
        self.setButtonText(
            QWizard.WizardButton.FinishButton, "Fertig"
        )
        self.setButtonText(
            QWizard.WizardButton.CancelButton, "Abbrechen"
        )

        intro = _IntroPage(task, self.context)
        self.intro_label = intro.summary_label
        self.addPage(intro)

        # Every step gets a page: open steps show an action button,
        # satisfied steps become confirm pages. Nothing is skipped.
        for step in task.steps:
            page = _StepPage(self, step)
            self.step_pages[step.id] = page
            self.addPage(page)

    def page_count(self) -> int:
        """Number of wizard pages (intro + open steps)."""
        return len(self.pageIds())

    def done(self, result: int) -> None:  # noqa: N802 (Qt naming)
        """Emit ``task_completed`` once before closing on accept."""
        if result == QDialog.DialogCode.Accepted:
            self.task_completed.emit(self.task.id, self.context)
        super().done(result)
