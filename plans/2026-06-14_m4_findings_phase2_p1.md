# Plan: M-4 — Findings Phase 2 (P1, Should-Fix)

**Datum:** 2026-06-14
**Bezug:** `docs/reports/2026-06-14_code-review.md` und `2026-06-14_m4_findings.md`
**Scope:** P1-Cluster E (Architektur), F (Optimizer), G (Subprocess-Async), H (Error-Handling), I (Test-Coverage)

> **Hinweis:** Diese Datei dokumentiert die P1-Phase. Für Sprint-Reihenfolge, Aufwand-Schätzung, Akzeptanz-Gates siehe Hauptdatei.

---

## 🟠 Phase 2 — Should-Fix vor nächstem Feature (P1)

### Cluster E: Architektur (C-1, C-6, A-1, A-5)

#### 🔍 C1-SUBPLAN-A · Eigenes Sub-Plan: Subshell-IPC-Architektur evaluieren
- **Prio:** P1 · **Aufwand:** XL (3-5 Tage) — siehe Sub-Plan
- **Sub-Plan-Datei:** `plans/2026-06-14_subplan_subshell_ipc.md` (zu erstellen)
- **Warum Sub-Plan?** Architektur-Entscheidung: (a) Modul-Einbettung, (b) IPC mit `multiprocessing.connection`, (c) Status quo + Cleanup.
- **Akzeptanz:** (1) Entscheidung dokumentiert. (2) Temp-JSON-Leak behoben. (3) Backup-Restore-Race behoben. (4) Tests für den gewählten Ansatz.
- **Subtasks:**
  - [ ] **C1-SUBPLAN-A.0** Sub-Plan erstellen.
  - [ ] **C1-SUBPLAN-A.1** Architektur-Spike: ChorAufstellung als importierbares Modul.
  - [ ] **C1-SUBPLAN-A.2** Falls Modul-Einbettung: `choraufstellung/__main__.py` deprecated, direkter Import in `chormanager/ui/choraufstellung_launcher.py`.
  - [ ] **C1-SUBPLAN-A.3** Temp-JSON `tempfile.NamedTemporaryFile(delete=True, suffix='.json')` statt hartcodiertem Pfad.
  - [ ] **C1-SUBPLAN-A.4** `self._host.file = None` als initialen Zustand im Subshell.
  - [ ] **C1-SUBPLAN-A.5** Integration-Test: zwei `MainWindow`s in einem Prozess.

#### 🔍 C6-SUBPLAN-A · Eigenes Sub-Plan: Pro-Tab-Database-Connection-Pool
- **Prio:** P1 · **Aufwand:** L (2 Tage) — siehe Sub-Plan
- **Sub-Plan-Datei:** `plans/2026-06-14_subplan_db_connection_pool.md` (zu erstellen)
- **Warum Sub-Plan?** Connection-Pool-Topologie: (a) Pool pro Tab, (b) ein Pool mit n Slots, (c) Write-Lock via `BEGIN IMMEDIATE`. Test-Strategie muss Concurrency abdecken.
- **Akzeptanz:** (1) Jeder Tab hat eigene Connection. (2) Schreib-Concurrency-Test grün. (3) `_reload_after_restore` race-frei.
- **Subtasks:**
  - [ ] **C6-SUBPLAN-A.0** Sub-Plan erstellen.
  - [ ] **C6-SUBPLAN-A.1** `Database.connect_pool(max_connections=10)` mit `sqlite3.connect(check_same_thread=False)`.
  - [ ] **C6-SUBPLAN-A.2** Tabs als `Database`-Consumer: `tab.db_pool = self.db.connect_pool()`.
  - [ ] **C6-SUBPLAN-A.3** Repos via `with self.db.connection() as conn:`.
  - [ ] **C6-SUBPLAN-A.4** `refresh_tab_repositories` ruft `tab.db_pool = self.db.connect_pool()` **vor** dem ersten Tab-Refresh.
  - [ ] **C6-SUBPLAN-A.5** Concurrency-Test `tests/integration/test_db_concurrent_writes.py` mit `threading.Thread`.

#### 🔍 A1-SUBPLAN-A · Eigenes Sub-Plan: Mixin-Inflation auflösen
- **Prio:** P1 · **Aufwand:** L (2-3 Tage) — siehe Sub-Plan
- **Sub-Plan-Datei:** `plans/2026-06-14_subplan_mixin_refactor.md` (zu erstellen)
- **Warum Sub-Plan?** Mixin-Architektur durch Komposition ersetzen: `ExportController`, `UpdateController`, `TabRouter` als QObject-Members. Diamond-Problem-Resolution.
- **Akzeptanz:** (1) MainWindow-Klasse < 200 LOC. (2) Controller-Klassen eigenständig testbar. (3) Keine Mixin-MRO-Konflikte.
- **Subtasks:**
  - [ ] **A1-SUBPLAN-A.0** Sub-Plan erstellen.
  - [ ] **A1-SUBPLAN-A.1** `ExportController(QObject)` mit Signal `export_finished = pyqtSignal(str)`.
  - [ ] **A1-SUBPLAN-A.2** Methoden aus `ExportCoreMixin`, `ExportJsonSyncMixin`, `ExportTabSpecificMixin` in `ExportController` verschieben.
  - [ ] **A1-SUBPLAN-A.3** `UpdateController(QObject)` analog.
  - [ ] **A1-SUBPLAN-A.4** `TabRouter` analog.
  - [ ] **A1-SUBPLAN-A.5** MainWindow-Klasse schrumpft auf < 200 LOC.

#### A5-FIX-A · `load_formation_data` Duplikation entfernen
- **Prio:** P1 · **Aufwand:** S (0,3 Tag) · **Abhängigkeiten:** M5-FIX-A
- **Akzeptanz:** (1) `main.py:_load_formation_data` (Z. 790-815) gelöscht. (2) `RecoveryController` und `file_io.open` rufen beide `self._host.file_io.load_formation_data(self._host, data)`.
- **Subtasks:**
  - [ ] **A5-FIX-A.1** ComboBox-Sync-Logik aus `_load_formation_data` in `chormanager/choraufstellung/file_io.py` verschieben.
  - [ ] **A5-FIX-A.2** `_load_formation_data` löschen, alle Caller umstellen.
  - [ ] **A5-FIX-A.3** Test `test_load_formation_data_single_path.py`.

### Cluster F: Optimizer (C-4, R-6)

#### 🔍 C4-SUBPLAN-A · Eigenes Sub-Plan: `AffinityRule` Performance + QThread-Migration
- **Prio:** P1 · **Aufwand:** L (2 Tage) — siehe Sub-Plan
- **Sub-Plan-Datei:** `plans/2026-06-14_subplan_optimizer_perf.md` (zu erstellen)
- **Warum Sub-Plan?** Optimierer ist hot path. Performance-Refactor + Threading-Architektur gekoppelt.
- **Akzeptanz:** (1) 50 Sänger mit 20 Affinitäts-Paaren < 1 s. (2) Optimierer in QThread. (3) Progress-Signal. (4) Singersuche O(1) via Dict-Index.
- **Subtasks:**
  - [ ] **C4-SUBPLAN-A.0** Sub-Plan erstellen.
  - [ ] **C4-SUBPLAN-A.1** `_get_neighbor_positions` (Z. 459-483): leere Positionen außerhalb der Schleife.
  - [ ] **C4-SUBPLAN-A.2** `Singers`-Dict-Index: `self._singer_by_id = {s.singer_id: s for s in singers}`.
  - [ ] **C4-SUBPLAN-A.3** `OptimizerWorker(QThread)` mit `pyqtSignal(int)` für Progress.
  - [ ] **C4-SUBPLAN-A.4** UI: Progress-Dialog mit `QProgressBar`.
  - [ ] **C4-SUBPLAN-A.5** Test T-2 `test_affinity_perf.py` mit `@pytest.mark.timeout(2)`.
  - [ ] **C4-SUBPLAN-A.6** Bench-Skript `bench/optimizer_bench.py`.

#### R6-FIX-A · `chormanager_bridge._refresh_pool` `placed_singer_ids` synchronisieren
- **Prio:** P1 · **Aufwand:** XS (0,1 Tag) · **Abhängigkeiten:** —
- **Akzeptanz:** (1) Nach Bridge-Load sind `pool.placed_singer_ids` mit `grid.get_placed_singer_ids()` synchron.
- **Subtasks:**
  - [ ] **R6-FIX-A.1** In `chormanager/choraufstellung/chormanager_bridge.py:253-257` `self._host.pool.placed_singer_ids = self._host.grid.get_placed_singer_ids()`.
  - [ ] **R6-FIX-A.2** Test schreiben.

### Cluster G: Subprocess-Async (M-1, M-3, M-7)

#### M1-FIX-A · `SubprocessRunner(QObject)` für 7 Hot-Paths
- **Prio:** P1 · **Aufwand:** M (1,5 Tage) · **Abhängigkeiten:** C3-SUBPLAN-A
- **Akzeptanz:** (1) Ein einziger `SubprocessRunner` mit `run_async(cmd, cwd, env, timeout, on_done)`. (2) Alle 7 `subprocess.run`-Aufrufe migriert. (3) Progress-Signal. (4) Kein UI-Freeze.
- **Subtasks:**
  - [ ] **M1-FIX-A.1** `SubprocessRunner(QObject)` in `chormanager/ui/subprocess_runner.py`.
  - [ ] **M1-FIX-A.2** `run_async(cmd, *, cwd=None, env=None, timeout=None, on_stdout=None, on_stderr=None, on_done=None)`.
  - [ ] **M1-FIX-A.3** Intern `QProcess` (Qt-nativ).
  - [ ] **M1-FIX-A.4** Migration `chormanager/ui/choraufstellung_launcher.py:209-211, 297-301`.
  - [ ] **M1-FIX-A.5** Migration `chormanager/ui/main_window.py:833-841` (`_show_about` git-Describe).
  - [ ] **M1-FIX-A.6** Migration `chormanager/ui/update_controller.py:77-80, 103-106` (Doppel-Coverage mit C3-SUBPLAN-A).
  - [ ] **M1-FIX-A.7** Migration `chormanager/ui/export_controller.py:223-236` (LibreOffice).
  - [ ] **M1-FIX-A.8** Test `tests/unit/test_subprocess_runner.py` mit Mock-QProcess.

#### M3-FIX-A · `QApplication.processEvents()` eliminieren
- **Prio:** P1 · **Aufwand:** XS (0,1 Tag) · **Abhängigkeiten:** C3-SUBPLAN-A
- **Akzeptanz:** (1) Kein `processEvents()` in `update_controller.py`. (2) `setOverrideCursor(Qt.WaitCursor)`.
- **Subtasks:**
  - [ ] **M3-FIX-A.1** Siehe C3-SUBPLAN-A.1.

#### M7-FIX-A · Subprocess-Pfad-Validation in `choraufstellung_launcher`
- **Prio:** P1 · **Aufwand:** XS (0,2 Tag) · **Abhängigkeiten:** —
- **Akzeptanz:** (1) Startup-Validierung von `choraufstellung_path`. (2) Logging bei nicht-existentem Pfad.
- **Subtasks:**
  - [ ] **M7-FIX-A.1** `validate_choraufstellung_path()` Helper.
  - [ ] **M7-FIX-A.2** In `app_logging` loggen.
  - [ ] **M7-FIX-A.3** Test schreiben.

### Cluster H: Error-Handling (M-2, M-5, m-8, m-9)

#### M2-FIX-A · Konkrete Exceptions in `chormanager_bridge`
- **Prio:** P1 · **Aufwand:** XS (0,1 Tag) · **Abhängigkeiten:** —
- **Akzeptanz:** (1) `except Exception` durch `except (json.JSONDecodeError, KeyError, ValueError, OSError, sqlite3.Error)`. (2) Logging statt `print`.
- **Subtasks:**
  - [ ] **M2-FIX-A.1** `chormanager/choraufstellung/chormanager_bridge.py:139, 201` konkretisieren.
  - [ ] **M2-FIX-A.2** `print` durch `app_logging.get_logger(__name__).warning(...)`.
  - [ ] **M2-FIX-A.3** Test schreiben.

#### M5-FIX-A · `load_formation_data` Validierung
- **Prio:** P1 · **Aufwand:** S (0,3 Tag) · **Abhängigkeiten:** A5-FIX-A
- **Akzeptanz:** (1) `rows`, `cols` auf `1 <= value <= 50` validiert. (2) `ValueError` bei out-of-bounds. (3) Caller fängt ValueError.
- **Subtasks:**
  - [ ] **M5-FIX-A.1** `_validate_dimensions(rows, cols)` Helper.
  - [ ] **M5-FIX-A.2** In `chormanager/choraufstellung/file_io.py:82-99` validieren.
  - [ ] **M5-FIX-A.3** Test schreiben.

#### m8-FIX-A · YAML-Fallback in `config.py`
- **Prio:** P1 · **Aufwand:** XS (0,2 Tag) · **Abhängigkeiten:** —
- **Akzeptanz:** (1) `yaml.YAMLError` und `OSError` in `load_voice_groups`/`load_fields`/`load_app_config` abgefangen. (2) Fallback auf Default-Dict.
- **Subtasks:**
  - [ ] **m8-FIX-A.1** `try/except` um `yaml.safe_load` in `chormanager/config.py:144, 164, 181`.
  - [ ] **m8-FIX-A.2** Default-Werte definieren.
  - [ ] **m8-FIX-A.3** Test schreiben.

#### m9-FIX-A · `backup_on_start` konsistenter Snapshot
- **Prio:** P1 · **Aufwand:** S (0,5 Tag) · **Abhängigkeiten:** —
- **Akzeptanz:** (1) Backup via `sqlite3.Connection.backup()`. (2) `db_path` exclusive gelockt während Backup.
- **Subtasks:**
  - [ ] **m9-FIX-A.1** `BackupService.create_backup` auf `sqlite3.connect(source_db_path).backup(backup_conn)`.
  - [ ] **m9-FIX-A.2** Test schreiben mit parallelem Write.

### Cluster I: Test-Coverage (T-1 bis T-5)

#### T1-FIX-A · Test für `OptimizeFormationCommand` Doppel-Redo
- **Prio:** P1 · **Aufwand:** S (0,3 Tag) · **Abhängigkeiten:** C2-FIX-A
- **Akzeptanz:** (1) `swap_count` nach `push()` == `swap_count` nach `run()`. (2) `undo()` restauriert `old_positions`, nicht Zwischen-Position.
- **Subtasks:**
  - [ ] **T1-FIX-A.1** Test `tests/unit/test_optimizer_double_redo.py`.

#### T2-FIX-A · Performance-Bound-Test für `AffinityRule`
- **Prio:** P1 · **Aufwand:** S (0,2 Tag) · **Abhängigkeiten:** C4-SUBPLAN-A
- **Akzeptanz:** (1) 50 Sänger mit 20 Affinitäten < 1 s. (2) `@pytest.mark.timeout(2)`.
- **Subtasks:**
  - [ ] **T2-FIX-A.1** Test `tests/unit/test_affinity_perf.py`.

#### T3-FIX-A · Race-Test für `RecoveryController`
- **Prio:** P1 · **Aufwand:** S (0,3 Tag) · **Abhängigkeiten:** M6-FIX-A
- **Akzeptanz:** (1) Reproduziert Auto-Save-Während-Recovery. (2) Kein Datenverlust.
- **Subtasks:**
  - [ ] **T3-FIX-A.1** Test `tests/unit/test_recovery_race.py`.

#### T4-FIX-A · Test für `update_controller._do_update`
- **Prio:** P1 · **Aufwand:** S (0,3 Tag) · **Abhängigkeiten:** C3-SUBPLAN-A
- **Akzeptanz:** (1) `subprocess.run` mit korrektem `cwd`. (2) Bei `returncode != 0`: Statusbar-Fehler. (3) Timeout eingehalten.
- **Subtasks:**
  - [ ] **T4-FIX-A.1** Test `tests/unit/test_update_controller.py`.

#### T5-FIX-A · Test für `FormationStorage.save_autosave` ohne Symlink
- **Prio:** P1 · **Aufwand:** XS (0,2 Tag) · **Abhängigkeiten:** C5-FIX-A
- **Akzeptanz:** (1) `os.symlink` wird nicht aufgerufen. (2) Funktioniert auf Windows.
- **Subtasks:**
  - [ ] **T5-FIX-A.1** Test `tests/unit/test_storage_autosave_no_symlink.py`.

---

## 📊 P1-Aufwand-Schätzung (Detail)

| Cluster | Anzahl | Aufwand |
|---|---:|---:|
| E (Architektur) | 4 (3 Sub-Pläne + 1 FIX) | ~7 Tage (mit Sub-Plänen) |
| F (Optimizer) | 2 (1 Sub-Plan + 1 FIX) | ~2 Tage |
| G (Subprocess-Async) | 3 | ~2 Tage |
| H (Error-Handling) | 4 | ~1,2 Tage |
| I (Test-Coverage) | 5 | ~1,3 Tage |
| **Σ P1** | **14** | **~13,5 Tage** |

> **Sub-Plan-Wert:** C1 + C4 + C6 = ~7-9 Tage. Die restlichen P1-FIXes sind ~5-6 Tage.
