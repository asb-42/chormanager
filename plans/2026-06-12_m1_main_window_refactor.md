# Plan: M-1 — Aufteilung `chormanager/ui/main_window.py`

**Datum:** 2026-06-12
**Status:** Plan (kein Code-Change)
**Voraussetzung:** M-4 Schritt 1 ✅, Q-1 ✅ (auf `main` als `ba1e58b`/`1e2b5ef`)
**Risiko-Klasse:** 🟠 Hoch (God-Class-Refactor, mehrere hundert Zeilen Code werden verschoben)

---

## 🎯 Ziel

Die Datei [`chormanager/ui/main_window.py`](chormanager/ui/main_window.py:1) (3 104 LOC, 71 Methoden, 3 Klassen) so aufteilen, dass:

1. **Jede Klasse eine einzige Verantwortlichkeit** hat (Single Responsibility).
2. **main_window.py ≤ 750 Zeilen** wird (AGENTS.md-Anforderung).
3. **Keine Verhaltensänderung** in Schritt 1 (rein mechanische Extraktion).
4. **Test-Suite bleibt grün** nach jedem Sub-Schritt.

---

## 📋 Bestandsaufnahme

### Klassen (3) und Methoden (71)

| Klasse | Zeile | LOC | Verantwortlichkeit |
|---|---:|---:|---|
| `SingerDialog` | 84-297 | 213 | Form-Dialog zum Sänger bearbeiten (QDialog, `_setup_ui`, `_populate_from_singer`, `get_data`) |
| `MainWindow` | 300-2973 | 2 673 | **Alles andere** — Menu/Toolbar/Tabs/Exports/Update/About/… |
| `VersionCheckDialog` | 2975-3063 | 88 | Versions-Check-Dialog (QDialog + GitHub-Abfrage) |

Plus Hilfsfunktion `refresh_tab_repositories` (Zeile 3071-3103, 32 LOC).

### Verantwortlichkeits-Cluster in `MainWindow`

| Cluster | Methoden | LOC ca. | Vorschlag: Neue Datei |
|---|---:|---:|---|
| **A. UI-Setup (Window-Lifecycle)** | `__init__`, `_setup_ui`, `_create_info_bar`, `_create_menu_bar`, `_create_tool_bar`, `_create_central_widget`, `_create_status_bar`, `_switch_view` | ~620 | **bleibt in `MainWindow`** |
| **B. Tab-Selection & Context-Toolbar** | `_emit_selection`, `_on_selection_changed` (1275-1282 + 969-976 Doppel!), `_update_context_toolbar`, `_update_info_labels`, `_on_project_changed`, `_on_event_selected`, `_on_besetzung_changed`, `_on_tab_changed` | ~250 | **`chormanager/ui/tab_router.py`** |
| **C. Such-/Filter-Handler** | `_on_search_text_changed`, `_on_filter_changed`, `_refresh_tabs` | ~30 | **bleibt in `MainWindow`** (eng mit Toolbar) |
| **D. Singer-Aktionen** | `_add_singer`, `_edit_singer`, `_delete_singer` | ~10 | **bleibt in `MainWindow`** (dünne Wrapper) |
| **E. Event-Aktionen** | `_new_event`, `_edit_event`, `_delete_event`, `_duplicate_event`, `_manage_availability`, `_list_events` | ~50 | **bleibt in `MainWindow`** |
| **F. Project-Aktionen** | `_new_projekt`, `_edit_project`, `_delete_project`, `_duplicate_project`, `_save_projekt`, `_open_projekt` | ~30 | **bleibt in `MainWindow`** |
| **G. ChorAufstellung-Spawning** | `_open_choraufstellung`, `_open_choraufstellung_file`, `_open_choraufstellung_for_event`, `refresh_tab_repositories` | ~120 | **`chormanager/ui/choraufstellung_launcher.py`** |
| **H. Undo/Redo** | `_undo`, `_redo` | ~15 | **bleibt in `MainWindow`** |
| **I. Theming** | `_set_light_theme`, `_set_dark_theme` | 425 | **`chormanager/ui/theme_manager.py`** |
| **J. Dialog-Show** | `_show_config`, `_show_about`, `_show_selbstdarstellung`, `_open_backup_restore`, `_reload_after_restore` | ~100 | **bleibt in `MainWindow`** |
| **K. Export — Core** | `_export_csv`, `_export_pdf`, `_export_libreoffice`, `_export_response_matrix`, `_export_tab_generic`, `_get_export_config_for_current_tab` | ~430 | **`chormanager/ui/export_controller.py`** |
| **L. Export — JSON-Sync** | `_export_singers_json`, `_export_events_json`, `_export_availability_json`, `_export_singers_csv`, `_export_all_sync` | ~120 | **`chormanager/ui/export_controller.py`** (Teil von K) |
| **M. Export — tab-spezifisch** | `_export_besetzung`, `_export_termine`, `_export_aufstellung`, `_export_project_libreoffice`, `_export_project_csv`, `_export_tab`, `_export_tab_csv` | ~280 | **`chormanager/ui/export_controller.py`** (Teil von K) |
| **N. Versions-Check & Update** | `_check_version`, `VersionCheckDialog`, `_do_update` | ~180 | **`chormanager/ui/update_controller.py`** |
| **O. Sonstiges** | `_get_data_dir`, `closeEvent` | ~15 | **bleibt in `MainWindow`** |
| **P. Inner Class** | `SingerDialog` | 213 | **`chormanager/ui/dialogs/singer_dialog.py`** (eigene Datei, analog zu `views/`) |

---

## 🏗️ Vorgeschlagene neue Modulstruktur

```
chormanager/ui/
├── main_window.py                  (~ 700 LOC)  ← nur Window-Lifecycle + Delegation
├── main_window_actions.py          (~ 200 LOC)  ← Singer/Event/Project/Dialog-Wrapper
├── tab_router.py                   (~ 250 LOC)  ← Selection + Context-Toolbar
├── theme_manager.py                (~ 430 LOC)  ← Theming (Light/Dark)
├── export_controller.py            (~ 850 LOC)  ← alle 15+ Export-Methoden
├── update_controller.py            (~ 180 LOC)  ← VersionCheckDialog + Git-Pull
├── choraufstellung_launcher.py     (~ 120 LOC)  ← Subshell-Spawning
└── dialogs/
    └── singer_dialog.py            (~ 213 LOC)  ← extrahiert aus main_window.py
```

**Netto-Effekt:** 3 104 LOC → 1 × ~700 + 7 × ~250 = ~2 450 LOC verteilt, kleinste Datei 120 LOC, größte 850 LOC.

---

## 🪜 Extraktions-Reihenfolge (kleinster Eingriff zuerst)

> **Grundprinzip:** Jeder Schritt ist ein eigener Commit. Nach jedem Schritt: `python -m py_compile` + `python -m pytest tests/ -q` muss grün bleiben. Verhalten ändert sich nicht.

| Schritt | Extraktion | LOC raus | Risiko | Commit-Strategie |
|---:|---|---:|:-:|---|
| **1** | `SingerDialog` → `dialogs/singer_dialog.py` | 213 | 🟢 Niedrig | 1 Commit, Smoke-Test `SingerDialog` per bestehendem GUI-Test |
| **2** | `VersionCheckDialog` → `update_controller.py` (Klasse + 2 Methoden) | 88 + 80 | 🟢 Niedrig | 1 Commit |
| **3** | `refresh_tab_repositories` → `choraufstellung_launcher.py` (Modul-Level-Funktion, kein Klassen-Bezug) | 32 | 🟢 Niedrig | 1 Commit |
| **4** | `_set_light_theme` + `_set_dark_theme` → `theme_manager.py` | 425 | 🟡 Mittel (StyleSheets evtl. mit Side-Effects) | 1 Commit, manueller Smoke-Test "Theme wechseln" |
| **5** | Tab-Routing (`_emit_selection` + Context-Toolbar) → `tab_router.py` | 250 | 🟡 Mittel (Phase-6-Bug lebt hier!) | 1 Commit, Phase-6-Tests müssen weiter grün sein |
| **6** | ChorAufstellung-Spawning → `choraufstellung_launcher.py` | 120 | 🟡 Mittel (subprocess-Aufrufe) | 1 Commit |
| **7** | Export-Controller → `export_controller.py` | ~850 | 🟠 Hoch (viele Methoden, viele Tests betroffen) | **2-3 Commits** (Core / JSON-Sync / Tab-spezifisch) |
| **8** | Singer/Event/Project-Aktions-Wrapper → `main_window_actions.py` | ~200 | 🟢 Niedrig | 1 Commit |

**Geschätzter Aufwand:** 8-10 Commits, jeweils 5-30 min, dazwischen User-Pause.

> **Status (2026-06-12):** Alle 8 Schritte **abgeschlossen** + Cleanup-Commit.
> Commits: `89a101e` (Schritt 1) … `2f32d0d` (Schritt 8) + `06e6328` (Cleanup duplicate `_on_selection_changed`).
> Test-Suite: 518 passed, 4 skipped, 0 failed.
> `chormanager/ui/main_window.py`: 3 105 → 924 LOC (-70%).
> Nächster Schritt: M-2 (siehe `plans/2026-06-12_m2_choraufstellung_refactor.md`).

---

## ⚠️ Risiken & Mitigationen

### Risiko 1: Zirkuläre Imports
`MainWindow` braucht `TabRouter`, `ExportController` etc. Diese brauchen zurück Referenzen auf das Window (für `self.content_stack`, `self.db`).
**Mitigation:** Dependency Injection. Controller bekommen `main_window: "MainWindow"` als Konstruktor-Parameter, nutzen es nur schwach typisiert (oder über Protocol).

### Risiko 2: `self.db_path`, `self.db` werden von vielen Methoden benutzt
**Mitigation:** Diese Attribute bleiben in `MainWindow`. Controller bekommen `db` als Property-Zugriff auf `main_window.db`.

### Risiko 3: Phase-6-Bug wieder einführen
`_emit_selection` ist exakt die Stelle, die in Phase 6 schon mal kaputt war.
**Mitigation:** Schritt 5 hat **zwingend** das `test_phase6_project_toolbar_fix.py` als Regression-Test, das nach jedem Commit mitläuft.

### Risiko 4: Tests an internal API
`tests/unit/test_phase5_tabs.py` testet Tabs direkt. `tests/gui/test_main_window.py` testet das Window. Beide bleiben unverändert, weil die **externe API stabil** bleibt.
**Mitigation:** Refactorings sind rein interne Umstrukturierung; kein Aufrufer ändert sich.

### Risiko 5: `SingerDialog` ist in `main_window.py` definiert, aber `from chormanager.ui.main_window import SingerDialog` wird vermutlich woanders genutzt
**Mitigation:** Re-Export in `main_window.py`:
```python
# Backward-compat re-export
from .dialogs.singer_dialog import SingerDialog  # noqa: F401
```

---

## ✅ Erfolgs-Kriterien

1. `main_window.py` ≤ 750 Zeilen.
2. Alle 408+ Tests grün nach jedem Schritt.
3. Keine Verhaltensänderung (manueller Smoke-Test der App: Menü, Toolbar, Tab-Wechsel, Theme-Wechsel, je 1 Export pro Pfad, Backup-Restore-Dialog öffnen).
4. `grep -c "^    def " chormanager/ui/main_window.py` < 25.
5. Keine neuen zirkulären Imports (`python -c "import chormanager.ui.main_window"` OK).

---

## 🚫 Was dieser Plan NICHT macht

- Kein Umbau der Subshell `choraufstellung/main.py` (das ist ein **separater** Riesen-Refactor, würde ich auf M-2 verschieben).
- Keine Änderung an `dialogs.py` (M-3, R-3 — ebenfalls separat).
- Keine Verhaltensänderungen (kein Bug-Fix, kein Feature).

---

## 📅 Nächste Schritte (nach User-Freigabe dieses Plans)

1. **Diskussion:** Welcher der 8 Schritte zuerst? Mein Vorschlag: **Schritt 1** (`SingerDialog` extrahieren) — risikoärmster Einstieg.
2. Pro Schritt: User-Pause zwischen Commits, bis Smoke-Test OK.
3. Nach allen 8 Schritten: **großer Smoke-Test** der gesamten App.

---

## 🔗 Bezug zum Code-Review

- **M-1** (God-Class `main_window.py`) aus [`docs/reports/2026-06-12_code-review.md`](../docs/reports/2026-06-12_code-review.md:1)
- **R-1** (Refactoring Opportunity #1) aus demselben Report
- **AGENTS.md** §1: "`main.py` ≤ 750 Zeilen. Auslagerung in `core/` oder `ui/` erzwingen."
