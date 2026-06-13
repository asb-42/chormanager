# Plan: M-3 — Aufteilung `chormanager/ui/dialogs.py`

> Erstellt am 2026-06-13 nach Abschluss von M-2.
> Schließt an [`plans/2026-06-12_m2_choraufstellung_refactor.md`](2026-06-12_m2_choraufstellung_refactor.md) an.

## 🎯 Ziel

`chormanager/ui/dialogs.py` (1824 LOC, 12 Klassen, 60 Methoden) ist nach
M-1/M-2 der größte zusammenhängende Codeblock in der Codebase. Wir
extrahieren logische Cluster in eigene Module, ohne das Public-API
(`from chormanager.ui.dialogs import X`) zu brechen.

## 🏗️ Aktueller Zustand (12 Klassen, 1824 LOC)

| Klasse                       | Z.    | LOC  | Verantwortlichkeit                                  | Qt-Komponenten |
|------------------------------|-------|------|-----------------------------------------------------|----------------|
| `AvailabilityDelegate`       | 52    | 26   | QStyledItemDelegate für Availability-Dropdown       | ComboBox       |
| `AvailabilityDialog`         | 79    | 57   | "Singer X: ja/nein?"-Mini-Dialog                    | QDialog       |
| `EventDialog`                | 137   | 117  | Create/Edit-Event-Form                              | Form          |
| `EventListDialog`            | 255   | 127  | Event-Picker + Live-Availability                    | List+Form     |
| `EventAvailabilityDialog`    | 383   | **591** ⚠️ | **Größter Dialog**: Tabelle mit 24-Spalten-Dropdown + 3 Export-Buttons | TableWidget |
| `ConfigDialog`               | 975   | 130  | Edit app.yaml-Settings                              | Form          |
| `SelbstdarstellungDialog`    | 1105  | 79   | Rich-Text-Editor + DB-Save                          | TextEdit      |
| `SingerSelectionDialog`      | 1184  | **250** | Multi-Select-Singer mit Filtern                   | Table+Form    |
| `DropZone`                   | 1435  | 41   | Drag&Drop-Widget für Backup-Dateien                 | QFrame        |
| `BackupRestoreDialog`        | 1477  | 156  | Backup/Restore-Workflow                            | Custom        |
| `NewFormationDialog`         | 1633  | 78   | Project+Event-Picker                                | Form          |
| `RepertoireDialog`           | 1713  | 111  | Repertoire-CRUD                                     | Form          |

### Bestehende Tests (sehr gute Coverage bereits vorhanden)

| Test-Datei                                       | Klassen                       | LOC  |
|--------------------------------------------------|-------------------------------|------|
| `tests/unit/test_phase2_dialogs.py`              | BackupRestore, Config, Selbst |  597 |
| `tests/unit/test_phase3_dialogs.py`              | SingerSelection, NewForm, Rep |  536 |
| `tests/unit/test_phase4_event_availability.py`   | EventAvailability             |  469 |
| **Summe**                                                                              | **~1600 LOC** |

→ **Diese Tests sind bereits eine ausführbare Spezifikation des
Ist-Verhaltens.** Wir dürfen sie nicht brechen.

## 🏗️ Vorgeschlagene neue Modulstruktur

```
chormanager/ui/dialogs/                     ← neuer Package-Ordner
├── __init__.py                             ← Re-Exports (Back-Compat)
├── _availability.py                        ← AvailabilityDelegate + AvailabilityDialog
├── _event.py                               ← EventDialog + EventListDialog
├── _event_availability.py                  ← EventAvailabilityDialog (allein)
├── _config.py                              ← ConfigDialog
├── _selbstdarstellung.py                   ← SelbstdarstellungDialog
├── _singer_selection.py                    ← SingerSelectionDialog
├── _backup_restore.py                      ← DropZone + BackupRestoreDialog
├── _new_formation.py                       ← NewFormationDialog
└── _repertoire.py                          ← RepertoireDialog
```

`dialogs.py` (alt) wird zu `dialogs/__init__.py` mit Re-Exporten.

### Wichtige Design-Entscheidungen

1. **Package statt 1-zu-1-Splits.** Die Klassen sind zu klein für
   eigene Top-Level-Module. Ein `dialogs/`-Package gruppiert sie
   logisch unter `chormanager/ui/dialogs/`.

2. **Keine `core/`-Trennung.** M-2 hat das für `choraufstellung/main.py`
   gemacht. Bei `dialogs.py` ist die Logik so eng an Qt-Widgets
   gekoppelt, dass eine Trennung in `core/` + `ui/` keinen echten
   Test-Vorteil bringt (Tests brauchen ohnehin `qtbot`).

3. **Atomic I/O bleibt im Dialog.** Die 3 Stellen, die Datei-IO machen
   (`BackupRestoreDialog._on_backup`, `EventAvailabilityDialog._export_*`),
   bleiben im Dialog-Modul — Extrahieren in eine `BackupService`-Bridge
   wäre M-4-Overhead für minimalen Gewinn.

4. **Keine Mixins.** Die 12 Klassen sind zu verschieden (DB-Connections,
   Form-Fields, Widget-Hierarchien). Mixins würden die Komplexität
   erhöhen, ohne Tests zu vereinfachen.

## 🪜 Extraktions-Reihenfolge (kleinster Eingriff zuerst)

### Schritt 1: `chormanager/ui/dialogs/`-Package-Skelett (🟢 Niedrig)
**Ziel:** `dialogs.py` → `dialogs/__init__.py` (Pure-Re-Export, keine Logik-Änderung).

**TDD:**
- `test_dialogs_package_exists`: import `chormanager.ui.dialogs` muss weiter funktionieren
- `test_all_12_classes_still_importable`: alle 12 Klassennamen auflisten + importieren
- `test_legacy_import_path_still_works`: `from chormanager.ui.dialogs import EventDialog` (alt) und `from chormanager.ui.dialogs.event_availability import EventAvailabilityDialog` (neu) funktionieren beide

**Durchführung:**
1. `mkdir chormanager/ui/dialogs/`
2. `dialogs.py` kopieren → `dialogs/__init__.py` (mit `# Re-export wrapper` docstring)
3. `dialogs.py` löschen
4. Tests laufen lassen → müssen grün bleiben

**Verifikation:** `pytest tests/unit/test_phase{2,3,4}_*_dialogs.py -q` grün, py_compile OK.

### Schritt 2: `dialogs/_availability.py` (🟢 Niedrig)
**Ziel:** Die zwei kleinsten Klassen (56 LOC) als Test-Balloon.

**Inhalt:** `AvailabilityDelegate` (Z. 52-77) + `AvailabilityDialog` (Z. 79-135)

**TDD:**
- `test_availability_delegate_lives_in_module`
- `test_availability_dialog_lives_in_module`
- `test_re_exports_from_package_init`

**Im Package-Init:** `from ._availability import AvailabilityDelegate, AvailabilityDialog`

**Verifikation:** 3 neue Tests grün, alte Tests grün.

### Schritt 3: `dialogs/_event.py` (🟢 Niedrig)
**Ziel:** Die zwei mittleren Event-Dialoge (~244 LOC).

**Inhalt:** `EventDialog` (Z. 137-253) + `EventListDialog` (Z. 255-381)

**TDD:**
- `test_event_dialog_lives_in_module`
- `test_event_list_dialog_lives_in_module`
- `test_re_exports_from_package_init`

### Schritt 4: `dialogs/_event_availability.py` (🔴 Hoch — der größte Brocken)
**Ziel:** `EventAvailabilityDialog` (591 LOC) in eigenes Modul.

**Inhalt:** Die ganze Klasse + die zugehörigen Helper.

**Sub-Risiko:** Klasse hat `_load_availability`, `_save_availability_on_change`,
`accept`, `_export_pdf`, `_export_availability` → 5 Verantwortlichkeiten.
Eventuell lohnt sich ein **inner split** in EventAvailabilityDialog
+ _export_pdf (PDF-Bridge) + _export_availability (CSV/HTML).

**Entscheidung für M-3:** Erst nur Modul-Split, **kein** Klassen-Split.
Begründung: Bestehende `test_phase4_*`-Tests (469 LOC) sind die Spezifikation
und decken alle 5 Methoden ab. Klassen-Split wäre M-4-Overhead.

**TDD:**
- `test_event_availability_dialog_lives_in_module`
- `test_re_exports_from_package_init`

### Schritt 5: `dialogs/_config.py` (🟢 Niedrig)
**Ziel:** `ConfigDialog` (130 LOC) + Utility-Funktionen.

**TDD:** analog zu Schritt 2.

### Schritt 6: `dialogs/_selbstdarstellung.py` (🟢 Niedrig)
**Ziel:** `SelbstdarstellungDialog` (79 LOC).

**TDD:** analog.

### Schritt 7: `dialogs/_singer_selection.py` (🟡 Mittel)
**Ziel:** `SingerSelectionDialog` (250 LOC). Hat Filter-Logik + Export.

**Sub-Risiko:** Export-Funktion könnte später in `_export_singers_bridge.py`
extrahiert werden — M-4.

**TDD:** analog + 1 Test, der die Filter-Pipeline festhält.

### Schritt 8: `dialogs/_backup_restore.py` (🟡 Mittel)
**Ziel:** `DropZone` (41 LOC) + `BackupRestoreDialog` (156 LOC).

**Sub-Risiko:** Drag&Drop-Logik in `DropZone` ist eng mit
`BackupRestoreDialog._on_file_dropped` verzahnt. Beide zusammen
extrahiert ist ok.

**TDD:** analog.

### Schritt 9: `dialogs/_new_formation.py` (🟢 Niedrig)
**Ziel:** `NewFormationDialog` (78 LOC).

**TDD:** analog.

### Schritt 10: `dialogs/_repertoire.py` (🟢 Niedrig)
**Ziel:** `RepertoireDialog` (111 LOC).

**TDD:** analog.

### Schritt 11: `dialogs/__init__.py` aufräumen (🟢 Niedrig)
**Ziel:** Konsolidierte Re-Exports mit Docstring-Map, die jeden
Klassennamen seinem Sub-Modul zuordnet (analog zu M-2 Schritt 14).

**TDD:**
- `test_init_docstring_lists_all_modules`
- `test_init_exports_exactly_12_classes`

### Schritt 12: Finale `chormanager/ui/dialogs/`-Validierung (🟢 Niedrig)
**Ziel:** Letzte Konsistenz-Checks.

**Checkliste:**
- ✅ Kein Code mehr in `__init__.py` außer Re-Exports + Docstring
- ✅ Alle 12 Klassen haben Type-Hints auf den public-Methoden
- ✅ `py_compile` + `pytest` durchlaufen
- ✅ Keine zirkulären Imports zwischen Sub-Modulen
- ✅ Backward-Compat: `from chormanager.ui.dialogs import X` für alle X

**Verifikation:** `pytest tests/unit/test_phase{2,3,4}_*.py -q` grün, **1600+** Tests.

## ⚖️ Risiko-Assessment

### Risiko 1: `__init__.py` Re-Export-Side-Effects (Mittel)
**Problem:** Manche Sub-Module importieren beim Laden (z.B.
`BackupRestoreDialog` importiert `chormanager.export.backup_service`).
Wenn `__init__.py` alle 12 Module imported, könnte das langsamer sein.

**Mitigation:** Lazy-Loading via `__getattr__` (PEP 562) im `__init__.py`?
Oder akzeptieren, dass 12 Module-Imports ~50ms kosten?

**Entscheidung:** **Akzeptieren** — 50ms ist unter dem menschlichen
Threshold und der Test-Runner cached eh. PEP 562 wäre über-engineered.

### Risiko 2: Test-Patching bricht (Mittel)
**Problem:** Bestehende Tests patchen Klassen via
`monkeypatch.setattr("chormanager.ui.dialogs.EventDialog", _Fake)`.
Wenn `EventDialog` jetzt aus `chormanager.ui.dialogs._event` re-exportiert
wird, kann das Patchen am Original-Modul oder am Re-Export erfolgen.

**Mitigation:** Re-Exports im `__init__.py` tun **nichts** außer
`from ._event import EventDialog`. Dadurch sind `monkeypatch.setattr`
am Original-Modul (`chormanager.ui.dialogs._event.EventDialog`) und am
Re-Export (`chormanager.ui.dialogs.EventDialog`) **gleich wirksam**, weil
Python den Re-Export-Name dynamisch auflöst (PEP 3134 / import system).

**Verifikation:** Tests müssen nach jedem Schritt grün bleiben.

### Risiko 3: ChorAufstellung-Launcher (Niedrig)
**Problem:** Der Subshell-Launcher importiert vielleicht direkt
`chormanager.ui.dialogs.X` — funktioniert das nach dem Package-Split?

**Mitigation:** Re-Exports in `__init__.py` decken das ab.

**Verifikation:** `python -m chormanager.choraufstellung` muss starten (manueller Test, nicht in CI).

## ✅ Erfolgs-Kriterien

| Kriterium                                      | Ziel                | Messung              |
|------------------------------------------------|---------------------|----------------------|
| `dialogs.py` LOC                               | 0 (gelöscht)        | `ls chormanager/ui/dialogs.py` |
| `dialogs/`-Package LOC                         | ~2000 (1800+Doc+Re-Exports) | `find chormanager/ui/dialogs -name "*.py" \| xargs wc -l` |
| Anzahl Sub-Module                              | 11 (1 Init + 10 Klassen-Dateien) | `ls chormanager/ui/dialogs/*.py` |
| Größtes Sub-Modul                               | <650 LOC            | `wc -l`               |
| Tests grün                                     | 1600+               | `pytest tests/unit/test_phase{2,3,4}_*` |
| Neue Modul-Shape-Tests                         | ~30                 | `pytest tests/unit/test_dialogs_package` |
| Backward-Compat                                | 100%                | `grep -r "from chormanager.ui.dialogs import" chormanager/ tests/` |
| py_compile                                     | OK                  | `python -m py_compile ...` |

## 🚫 Was dieser Plan NICHT macht

- **Kein Klassen-Split** für `EventAvailabilityDialog` (M-4-Kandidat)
- **Kein Bridge-Pattern** für die Backup/PDF/CSV-Exports (M-4)
- **Keine Umbenennung** der 12 Klassen
- **Keine API-Änderung** an irgendeiner public-Methode
- **Kein `chormanager/ui/forms/`-Subpackage** (das existiert bereits
  für `singer_dialog.py` und bleibt unangetastet)

## 📅 Reihenfolge der Commits

```
[plan]      plans/2026-06-13_m3_dialogs_refactor.md          (dieses Dokument)
[1]  refactor: dialogs/ package-skelett (Pure-Re-Export)
[2]  refactor: dialogs/_availability.py
[3]  refactor: dialogs/_event.py
[4]  refactor: dialogs/_event_availability.py
[5]  refactor: dialogs/_config.py
[6]  refactor: dialogs/_selbstdarstellung.py
[7]  refactor: dialogs/_singer_selection.py
[8]  refactor: dialogs/_backup_restore.py
[9]  refactor: dialogs/_new_formation.py
[10] refactor: dialogs/_repertoire.py
[11] refactor: dialogs/__init__.py aufräumen
[12] docs: finale Validierung
```

Jeder Commit = 1 Schritt + ~3 neue Module-Shape-Tests.

## 🔗 Bezug zum Code-Review

Aus [`docs/reports/2026-06-12_code-review.md`](../docs/reports/2026-06-12_code-review.md)
(sofern vorhanden): `dialogs.py` war als **High-Priority-Refactoring-Target**
markiert — zu groß, zu viele Verantwortlichkeiten, keine Test-Granularität.

M-3 ist die direkte Antwort darauf.

## 🚀 Nächste Schritte (nach User-Freigabe dieses Plans)

1. Schritt 1 ausführen (Package-Skelett) — minimal-invasiv
2. Bei jedem Schritt: pytest + py_compile
3. Nach Schritt 4 (`_event_availability.py`): Smoke-Test der App manuell
4. Nach Schritt 12: M-3 ist abgeschlossen → M-4 / M-Struct planen
