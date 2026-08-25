"""Catalog of end-user tasks shown on the Aufgaben view.

The catalog is declarative: every task gets a friendly German title,
a one-liner subtitle and an ordered step chain built from the shared
check predicates in :mod:`.checker`. Steps without a ``check`` are
actions executed by the wizard (they open existing dialogs).
"""
from __future__ import annotations

from typing import Dict, List

from .checker import (
    check_availability,
    check_besetzung,
    check_project,
    check_termin,
)
from .models import TaskDefinition, TaskStep

#: Stable task identifiers, in display order.
TASK_IDS = (
    "aufstellung_planen",
    "termin_anlegen",
    "verfuegbarkeit_erfassen",
    "mitglied_aufnehmen",
)


def _aufstellung_planen() -> TaskDefinition:
    """Build the full 'plan a formation' dependency chain."""
    return TaskDefinition(
        id="aufstellung_planen",
        title="Eine Aufstellung für einen Auftritt planen",
        subtitle=(
            "Führt Sie Schritt für Schritt zum Sitzplan: Projekt, Termin, "
            "Besetzung, Zusagen – und öffnet dann die Aufstellung."
        ),
        icon_name="view-grid",
        steps=[
            TaskStep(
                id="projekt_waehlen",
                title="Projekt auswählen oder anlegen",
                description=(
                    "Ein Projekt fasst alles zu einer Produktion zusammen "
                    "(z. B. \u201eHoffmann OKO 2026\u201c)."
                ),
                check=check_project,
            ),
            TaskStep(
                id="termin_waehlen",
                title="Termin für den Auftritt festlegen",
                description=(
                    "Wählen Sie das Konzert bzw. den Auftritt aus, für den "
                    "geplant wird – oder legen Sie ihn neu an."
                ),
                check=check_termin,
            ),
            TaskStep(
                id="besetzung_waehlen",
                title="Besetzung zusammenstellen",
                description=(
                    "Welche Sänger gehören zum Programm? Bestehende "
                    "Besetzungen können übernommen werden."
                ),
                check=check_besetzung,
            ),
            TaskStep(
                id="verfuegbarkeit_erfassen",
                title="Zusagen und Absagen erfassen",
                description=(
                    "Markieren Sie pro Sänger, ob er beim Termin dabei ist. "
                    "Mindestens eine Zusage ist nötig."
                ),
                check=check_availability,
            ),
            TaskStep(
                id="aufstellung_oeffnen",
                title="Aufstellung erstellen",
                description=(
                    "Die Sänger mit Zusagen werden in den Sitzplan übernommen "
                    "– dort können Sie platzieren und drucken."
                ),
            ),
        ],
    )


def _termin_anlegen() -> TaskDefinition:
    """Build the 'create an event' chain."""
    return TaskDefinition(
        id="termin_anlegen",
        title="Einen neuen Termin eintragen",
        subtitle=(
            "Probe, Konzert oder Auftritt in den Kalender aufnehmen."
        ),
        icon_name="x-office-calendar",
        steps=[
            TaskStep(
                id="projekt_waehlen",
                title="Projekt auswählen oder anlegen",
                description=(
                    "Jeder Termin gehört zu einem Projekt "
                    "(z. B. der aktuellen Spielzeit)."
                ),
                check=check_project,
            ),
            TaskStep(
                id="termin_anlegen",
                title="Termin anlegen",
                description=(
                    "Name, Datum und Typ des Termins eingeben – fertig."
                ),
            ),
        ],
    )


def _verfuegbarkeit_erfassen() -> TaskDefinition:
    """Build the 'record availability' chain."""
    return TaskDefinition(
        id="verfuegbarkeit_erfassen",
        title="Zusagen und Absagen für einen Termin erfassen",
        subtitle=(
            "Pro Sänger markieren, ob er zu einem Termin kommen kann."
        ),
        icon_name="view-calendar",
        steps=[
            TaskStep(
                id="termin_waehlen",
                title="Termin auswählen",
                description=(
                    "Wählen Sie den Termin aus, für den Rückmeldungen "
                    "erfasst werden sollen."
                ),
                check=check_termin,
            ),
            TaskStep(
                id="verfuegbarkeit_erfassen",
                title="Rückmeldungen eintragen",
                description=(
                    "Setzen Sie pro Sänger den Status: Zusage, Absage, "
                    "unter Vorbehalt usw. Es wird automatisch gespeichert."
                ),
            ),
        ],
    )


def _mitglied_aufnehmen() -> TaskDefinition:
    """Build the 'add a choir member' chain."""
    return TaskDefinition(
        id="mitglied_aufnehmen",
        title="Ein Chormitglied aufnehmen",
        subtitle=(
            "Name und Stimmgruppe eines neuen Sängers/iner neuen Sängerin "
            "eintragen."
        ),
        icon_name="list-add-user",
        steps=[
            TaskStep(
                id="mitglied_anlegen",
                title="Mitglied anlegen",
                description=(
                    "Mindestens Name und Stimmgruppe angeben; alles andere "
                    "kann später ergänzt werden."
                ),
            ),
        ],
    )


_BUILDERS = {
    "aufstellung_planen": _aufstellung_planen,
    "termin_anlegen": _termin_anlegen,
    "verfuegbarkeit_erfassen": _verfuegbarkeit_erfassen,
    "mitglied_aufnehmen": _mitglied_aufnehmen,
}


def get_task(task_id: str) -> TaskDefinition:
    """Return the task definition for ``task_id``.

    Raises:
        KeyError: If ``task_id`` is not part of the catalog.
    """
    try:
        builder = _BUILDERS[task_id]
    except KeyError as exc:
        raise KeyError(f"Unbekannte Aufgabe: {task_id!r}") from exc
    return builder()


def get_all_tasks() -> List[TaskDefinition]:
    """Return all catalog tasks in display order."""
    return [get_task(task_id) for task_id in TASK_IDS]


# Kept importable for tests that patch individual builders.
_CATALOG: Dict[str, TaskDefinition] = {}
