# 🤖 Coding Agent Instructions: Choraufstellung App

## 🧪 TDD-Workflow (NON-NEGOTIABLE)
1. **RED:** Schreibe zuerst failing test(s) in `tests/unit/`, `tests/integration/` oder `tests/ui/`.
2. **GREEN:** Implementiere minimalen Code, um Tests grün zu machen.
3. **REFACTOR:** Bereinige Code, extrahiere Funktionen, füge Type Hints/Docstrings hinzu. Tests bleiben grün.
4. **KEIN Feature ohne Tests.** Neue Logik ohne zugehörige Tests wird abgelehnt.
5. **Test-Pyramide:** ~70% Unit (`core/`), ~25% Integration (`storage/`, `config/`), ~5% UI (`pytest-qt`).
6. **Headless Execution:** `QT_QPA_PLATFORM=offscreen` für lokale/CI-Läufe. Kein Display-Server nötig.

## 📝 Code-Generierungsstandards
- **Type Hints:** `typing` Modul für alle Signaturen (`def run(grid: FormationGrid, rules: list[str]) -> bool:`).
- **Docstrings:** Public APIs müssen Zweck, Parameter, Return und Exceptions dokumentieren.
- **Error Handling:** `try/except` mit spezifischen Exceptions. Fallback-Werte. Niemals `except: pass`.
- **Keine Platzhalter:** `# ... hier Logik` oder `TODO` in produktivem Code verboten. Vollständig lauffähig.
- **API-Kompatibilität:** Bestehende Signaturen nicht brechen. Wraps/Adapter nutzen, falls Refactor nötig.

## 🔒 Safety & Integration Guards
- ✅ `python -m py_compile src/main.py` muss fehlerfrei durchlaufen.
- ✅ `python -m pytest tests/ -q` muss grün bleiben (0 failed).
- ❌ Keine Änderung an `src/core/` ohne entsprechende Unit-Tests.
- ❌ UI-Änderungen dürfen Drag & Drop, Rubber-Band, Theming oder Layout nicht brechen.
- ❌ Keine `QApplication`-Mocking, wo reine Python-Logik ausreicht.
- 🔄 Atomic Saves & Rollback bei I/O-Fehlern. Statusbar/Logs bei Recovery.

## 📤 Erwartetes AI-Output-Format

✅ ARCHITEKTUR-HINWEIS: [1-2 Sätze, warum dieser Ansatz gewählt wurde]

- Zeige klar, wo Code ergänzt wird (# --- NEW: ...).
- Liefere vollständige, kopierfertige Dateien.
- Erkläre Designentscheidungen kurz im Kommentar.
- Respektiere bestehende Imports, Signale/Slots, Klassenstruktur.

## Pre-Flight Checklist (AI prüft vor Ausgabe)

- Tests geschrieben & rot?
- src/core/ frei von Qt-Imports?
- Type Hints & Docstrings vorhanden?
- Error Handling & Fallbacks implementiert?
- py_compile + pytest würden lokal durchlaufen?
- Keine Platzhalter, kein "TODO", keine Globalen?
- Undo/Redo via QUndoCommand für State-Changes?
- Atomic I/O bei Dateien?

# DOX framework

- DOX is highly performant AGENTS.md hierarchy installed here
- Agent must follow DOX instructions across any edits

## Core Contract

- AGENTS.md files are binding work contracts for their subtrees
- Work products, source materials, instructions, records, assets, and durable docs must stay understandable from the nearest applicable AGENTS.md plus every parent AGENTS.md above it

## Read Before Editing

1. Read the root AGENTS.md
2. Identify every file or folder you expect to touch
3. Walk from the repository root to each target path
4. Read every AGENTS.md found along each route
5. If a parent AGENTS.md lists a child AGENTS.md whose scope contains the path, read that child and continue from there
6. Use the nearest AGENTS.md as the local contract and parent docs for repo-wide rules
7. If docs conflict, the closer doc controls local work details, but no child doc may weaken DOX

Do not rely on memory. Re-read the applicable DOX chain in the current session before editing.

## Update After Editing

Every meaningful change requires a DOX pass before the task is done.

Update the closest owning AGENTS.md when a change affects:

- purpose, scope, ownership, or responsibilities
- durable structure, contracts, workflows, or operating rules
- required inputs, outputs, permissions, constraints, side effects, or artifacts
- user preferences about behavior, communication, process, organization, or quality
- AGENTS.md creation, deletion, move, rename, or index contents

Update parent docs when parent-level structure, ownership, workflow, or child index changes. Update child docs when parent changes alter local rules. Remove stale or contradictory text immediately. Small edits that do not change behavior or contracts may leave docs unchanged, but the DOX pass still must happen.

## Hierarchy

- Root AGENTS.md is the DOX rail: project-wide instructions, global preferences, durable workflow rules, and the top-level Child DOX Index
- Child AGENTS.md files own domain-specific instructions and their own Child DOX Index
- Each parent explains what its direct children cover and what stays owned by the parent
- The closer a doc is to the work, the more specific and practical it must be

## Child Doc Shape

- Create a child AGENTS.md when a folder becomes a durable boundary with its own purpose, rules, responsibilities, workflow, materials, or quality standards
- Work Guidance must reflect the current standards of the project or user instructions; if there are no specific standards or instructions yet, leave it empty
- Verification must reflect an existing check; if no verification framework exists yet, leave it empty and update it when one exists

Default section order:
- Purpose
- Ownership
- Local Contracts
- Work Guidance
- Verification
- Child DOX Index

## Style

- Keep docs concise, current, and operational
- Document stable contracts, not diary entries
- Put broad rules in parent docs and concrete details in child docs
- Prefer direct bullets with explicit names
- Do not duplicate rules across many files unless each scope needs a local version
- Delete stale notes instead of explaining history
- Trim obvious statements, repeated rules, misplaced detail, and warnings for risks that no longer exist

## Closeout

1. Re-check changed paths against the DOX chain
2. Update nearest owning docs and any affected parents or children
3. Refresh every affected Child DOX Index
4. Remove stale or contradictory text
5. Run existing verification when relevant
6. Report any docs intentionally left unchanged and why

## User Preferences

When the user requests a durable behavior change, record it here or in the relevant child AGENTS.md

## Child DOX Index

Each entry points to a child ``AGENTS.md`` that owns the local
contract for a durable sub-tree. When a child changes its
contract, update both the child and this index.

| Child | Owns | Local AGENTS.md |
|---|---|---|
| ``chormanager/`` | The main ChorManager package (UI + business + data). Owns all sub-packages below. | (this file) |
| ``chormanager/choraufstellung/`` | The ChorAufstellung subshell / library. Runs both as a stand-alone process (``__main__.py``) and embedded inside ChorManager (planned, see C-1 sub-plan). | [chormanager/choraufstellung/AGENTS.md](chormanager/choraufstellung/AGENTS.md) |
| ``chormanager/choraufstellung/core/`` | Pure-Python arrangement rules + optimizer. No Qt imports allowed. | [chormanager/choraufstellung/core/AGENTS.md](chormanager/choraufstellung/core/AGENTS.md) |
| ``chormanager/choraufstellung/ui/`` | Qt widgets (FormationGrid, SingerPool, dialogs). | [chormanager/choraufstellung/ui/AGENTS.md](chormanager/choraufstellung/ui/AGENTS.md) |
| ``chormanager/choraufstellung/widgets/`` | Legacy widgets (drag/drop, context-menu). | [chormanager/choraufstellung/widgets/AGENTS.md](chormanager/choraufstellung/widgets/AGENTS.md) |
| ``chormanager/data/`` | SQLite layer with ``ConnectionPool`` (C-6). | [chormanager/data/AGENTS.md](chormanager/data/AGENTS.md) |
| ``chormanager/domain/`` | Domain models + repositories (Singer, Event, Project, ...). | [chormanager/domain/AGENTS.md](chormanager/domain/AGENTS.md) |
| ``chormanager/ui/`` | ChorManager's Qt MainWindow + controllers + dialogs. | [chormanager/ui/AGENTS.md](chormanager/ui/AGENTS.md) |
| ``chormanager/backup/`` | Backup service. | [chormanager/backup/AGENTS.md](chormanager/backup/AGENTS.md) |
| ``chormanager/export/`` | Export modules (CSV, JSON, sync). | [chormanager/export/AGENTS.md](chormanager/export/AGENTS.md) |
| ``chormanager/history/`` | Undo/Redo history service. | [chormanager/history/AGENTS.md](chormanager/history/AGENTS.md) |
| ``tests/`` | All test files. | [tests/AGENTS.md](tests/AGENTS.md) |
| ``plans/`` | Plan documents (M-4, sub-plans, retrospective). | [plans/AGENTS.md](plans/AGENTS.md) |
| ``docs/`` | User-facing documentation (Benutzerhandbuch) + code-review reports. | [docs/AGENTS.md](docs/AGENTS.md) |

### Sub-trees without a local AGENTS.md

These directories are simple grouping utilities with no
distinct contracts of their own. They follow the parent doc.

* ``chormanager/backup/service.py`` → see [chormanager/backup/AGENTS.md](chormanager/backup/AGENTS.md)
* ``chormanager/core/`` (empty wrapper) → see [chormanager/AGENTS.md](AGENTS.md) (this file)
* ``chormanager/history/service.py`` → see [chormanager/history/AGENTS.md](chormanager/history/AGENTS.md)
* ``chormanager/tools/`` (CLI scripts) → no AGENTS.md (out of refactor scope)
