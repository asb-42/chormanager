# Plan: M-4 — Anhang B: Sub-Plan-Übersicht

**Datum:** 2026-06-14
**Bezug:** `docs/reports/2026-06-14_code-review.md` und `2026-06-14_m4_findings.md`
**Scope:** 5 Sub-Pläne, die vor dem jeweiligen Cluster-Start erstellt werden müssen.

> **Konvention:** Jeder Sub-Plan bekommt eine eigene Datei: `plans/2026-06-14_subplan_<topic>.md`. Diese Anhang-Datei listet die Tradeoffs, Architektur-Entscheidungen und Subtasks, die im jeweiligen Sub-Plan detailliert werden.

---

## 🔍 1. `plans/2026-06-14_subplan_update_controller.md` (C3-SUBPLAN-A)

**Bezugs-Findings:** C-3 (blockierender git pull), M-3 (processEvents), M-1 (Subprocess-Async für 7 Pfade)
**Geschätzter Aufwand:** M (1 Tag)

### Architektur-Entscheidung: QThread vs QRunnable vs asyncio

| Variante | Vorteile | Nachteile |
|---|---|---|
| **QThread** (gewählt) | Native Qt-Integration, einfaches Signal/Slot | Komplexeres Lifecycle-Management, separater Event-Loop |
| **QRunnable + QThreadPool** | Wiederverwendbar, weniger Boilerplate | Komplexeres Progress-Reporting, kein direkter Signal-Connect ohne Wrapper |
| **asyncio + qasync** | Modern Python-Idiom | PyQt6-Kompatibilität unklar, zusätzliche Dependency |

**Empfehlung:** QThread mit dediziertem `UpdateWorker(QObject, moveToThread)`, gesteuert von QThread.

### Drei Sub-Bereiche

**(a) QThread-Migration:** `urllib.request` + `git rev-parse` in Worker-Thread, Result via `pyqtSignal(dict)`.
**(b) Timeout-Ergänzung:** `subprocess.run(..., timeout=60)` immer, auch für `_do_update`.
**(c) Signaturprüfung:** `git verify-commit HEAD` mit `--pretty=format:%G?` — nur `G`/`U`/`X`/`Y` als gültig akzeptieren.

### Tradeoffs

- **QThread-Migration:** + sauberer, + Signal-basiert, - 30-50 Zeilen Boilerplate. Tradeoff: ein Tag Refactor für 1 Tag Test-Coverage.
- **Signaturprüfung:** ++ Sicherheit (verhindert RCE via kompromittiertes Remote), -- User muss GPG-Key haben, -- Educational-Overhead für Maintainer. Tradeoff: 1 Tag Setup, deutlich höhere Sicherheit.
- **Timeout=60s:** ++ Robustheit, - Bei langsamer Disk bricht Pull ab. Tradeoff: 1 Zeile, kaum Nachteil.

### Detaillierte Subtasks (im Sub-Plan)

1. `QApplication.processEvents()` durch `setOverrideCursor(Qt.WaitCursor)` ersetzen
2. `UpdateCheckWorker(QObject, moveToThread)` mit `pyqtSignal(dict)` für Result
3. `UpdateWorker` für `git pull` mit `timeout=60`, Signal-basiert
4. `git verify-commit HEAD` mit Signatur-Status-Check (`G`/`U`/`X`/`Y` = OK)
5. Auto-Update erzwingt App-Neustart (User-Bestätigung)
6. Test `tests/unit/test_update_controller.py` mit gemocktem `subprocess.run`

---

## 🔍 2. `plans/2026-06-14_subplan_subshell_ipc.md` (C1-SUBPLAN-A)

**Bezugs-Findings:** C-1 (Subshell-Spawn fragil), M-7 (Pfad-Validation)
**Geschätzter Aufwand:** XL (3-5 Tage)

### Architektur-Entscheidung: Drei Varianten

| Variante | Vorteile | Nachteile |
|---|---|---|
| **Modul-Einbettung** | Eine QApplication, kein IPC, einfaches State-Management | Memory-Footprint höher, Tests schwerer, ChorAufstellung muss als Library umgebaut werden |
| **`multiprocessing.connection`** | Echte Prozess-Trennung, sauberer Lifecycle | Komplexer, zwei QApplication-Probleme bleiben |
| **Status quo + Cleanup** | Geringster Aufwand, keine Architektur-Änderung | Risiken bleiben (Race, Leak), nur gemildert |

**Empfehlung:** **Modul-Einbettung** mit `QApplication.setAttribute(Qt.AA_PluginApplication)` (erlaubt mehrere QApplication-Instanzen im selben Prozess). ChorAufstellung wird in MainWindow eingebettet als Modus-Toggle (`self.choraufstellung_view`).

### Tradeoffs

- **Modul-Einbettung:** + Eine QApplication, + Sauberer State, + Einfachere Tests, - 2 Tage Refactor, - ChorAufstellung muss von Standalone-App zu Library-Modus umgebaut werden.
- **Temp-JSON-Fix (Teil-C-1.3):** ++ Schnell, + Sofort umsetzbar, - Wirkt nur Symptom, nicht Ursache.

### Detaillierte Subtasks (im Sub-Plan)

1. Architektur-Spike: ChorAufstellung als importierbares Modul testen
2. `choraufstellung/__main__.py` deprecated, `main.py` als Library-Entry
3. Subshell-Spawn-Code in `chormanager/ui/choraufstellung_launcher.py` durch direkten Import ersetzen
4. `tempfile.NamedTemporaryFile(delete=True, suffix='.json')` statt hartcodiertem Pfad
5. `self._host.file = None` als initialen Zustand
6. Integration-Test: zwei `MainWindow`s in einem Prozess

### Offene Architektur-Fragen (vor Sub-Plan-Start zu klären)

- Kann ChorAufstellung wirklich als Library laufen, oder gibt es Qt-Spezifika, die eine zweite `QApplication` zwingend brauchen?
- Soll die Modus-Toggle im Menü sichtbar sein, oder nur via Env-Var steuerbar?
- Backup-Restore-Race: braucht es ein explizites Mutex-Protokoll, oder reicht DB-Lock?

---

## 🔍 3. `plans/2026-06-14_subplan_db_connection_pool.md` (C6-SUBPLAN-A)

**Bezugs-Findings:** C-6 (Connection-Sharing), m-6 (set_active ohne Transaktion), m-7 (INSERT OR REPLACE Pattern)
**Geschätzter Aufwand:** L (2 Tage)

### Architektur-Entscheidung: Drei Topologien

| Topologie | Vorteile | Nachteile |
|---|---|---|
| **Pool pro Tab** | Maximale Isolation, kein Cross-Tab-Conflict | Höherer Memory-Footprint, mehr File-Handles |
| **Ein Pool mit n Slots** | Kontrolliert, begrenzter Footprint | Slot-Mangel kann zum Block führen |
| **Write-Lock via `BEGIN IMMEDIATE`** | Einfachste Implementierung | Writes serialisiert, evtl. Performance-Issue |

**Empfehlung:** **Pool pro Tab** mit `max_connections=10` (6 Tabs + Reserve). Schreibzugriffe gehen via `with self.db.connection() as conn:` mit `BEGIN IMMEDIATE`.

### Tradeoffs

- **Pool pro Tab:** + Maximale Isolation, + Parallel-Reads, - 6 Connections ~ 300 KB RAM. Tradeoff: 300 KB für saubere Concurrency.
- **Write-Lock:** ++ Einfach, - Bottleneck bei vielen Schreibvorgängen. Tradeoff: minimaler Aufwand, schlechte Concurrency.

### Detaillierte Subtasks (im Sub-Plan)

1. `Database.connect_pool(max_connections=10)` mit `sqlite3.connect(check_same_thread=False)`
2. Tabs als `Database`-Consumer: `tab.db_pool = self.db.connect_pool()`
3. Repos via `with self.db.connection() as conn:`
4. `refresh_tab_repositories` ruft `tab.db_pool = self.db.connect_pool()` **vor** dem ersten Tab-Refresh
5. Concurrency-Test `tests/integration/test_db_concurrent_writes.py` mit `threading.Thread`

### Offene Architektur-Fragen (vor Sub-Plan-Start zu klären)

- Brauchen wir Read-Replica-Trennung? (Wahrscheinlich nicht für Single-User)
- Soll `Database` ein Thread-Local-Pool sein, oder global?
- Was passiert mit WAL-Mode bei mehreren Connections?

---

## 🔍 4. `plans/2026-06-14_subplan_optimizer_perf.md` (C4-SUBPLAN-A)

**Bezugs-Findings:** C-4 (AffinityRule O(n²)), R-1 (Bounds-Check), R-2 (Sanity-Check)
**Geschätzter Aufwand:** L (2 Tage)

### Architektur-Entscheidung: In-Place vs Approximativ

| Variante | Vorteile | Nachteile |
|---|---|---|
| **In-Place Optimierung** (gewählt) | Exakte Lösung, keine Quality-Loss | Längere Laufzeit bei großen Chören |
| **Approximative Optimierung** (Simulated Annealing) | Skaliert besser, schneller | Quality-Loss, schwerer zu debuggen |
| **Hybrid: In-Place mit frühen Abbruch** | Guter Tradeoff | Komplexer zu implementieren |

**Empfehlung:** **Hybrid-Ansatz** — In-Place-Algorithmus beibehalten, aber mit `max_iterations` und `max_swaps` Cap, plus QThread-Wrapper für UI-Responsiveness.

### Tradeoffs

- **QThread-Migration:** + UI responsive, + Progress-Bar, - Worker-Thread-Komplexität. Tradeoff: 0,5 Tag für deutlich bessere UX.
- **Singers-Dict-Index:** + O(1) Lookups statt O(n), + Trivial (5 Zeilen), - Dict-Memory. Tradeoff: 10 Zeilen, sofort machbar.
- **Neighbor-Cache:** + 30% Speedup, - 1 Helper-Methode. Tradeoff: 15 Zeilen, signifikante Verbesserung.

### Detaillierte Subtasks (im Sub-Plan)

1. `_get_neighbor_positions`: leere Positionen außerhalb der Schleife berechnen
2. `Singers`-Dict-Index: `self._singer_by_id = {s.singer_id: s for s in singers}`
3. `OptimizerWorker(QThread)` mit `pyqtSignal(int)` für Progress
4. UI: Progress-Dialog mit `QProgressBar`
5. Test T-2 `test_affinity_perf.py` mit `@pytest.mark.timeout(2)`
6. Bench-Skript `bench/optimizer_bench.py` für Regressions-Check

### Performance-Targets

| Sänger-Zahl | Affinitäts-Paare | Aktuell | Ziel |
|---:|---:|---:|---:|
| 30 | 5 | ~2 s | < 0,5 s |
| 50 | 20 | ~10 s | < 1 s |
| 100 | 40 | ~60 s | < 5 s |

---

## 🔍 5. `plans/2026-06-14_subplan_mixin_refactor.md` (A1-SUBPLAN-A)

**Bezugs-Findings:** A-1 (Mixin-Inflation), A-2 (PyQt5-Totcode), A-3 (Lazy-Caches)
**Geschätzter Aufwand:** L (2-3 Tage)

### Architektur-Entscheidung: Mixin → Komposition vs Mixin → Split

| Variante | Vorteile | Nachteile |
|---|---|---|
| **Mixin → Komposition** (gewählt) | Diamond-Problem gelöst, klarere Lifecycle, bessere Test-Isolation | 3 Refactor-Sprints, viele Touchpoints |
| **Mixin → Split (mehrere Klassen)** | Einfacher Refactor, weniger Aufwand | Verbleibt im Mixin-Antipattern |

**Empfehlung:** **Mixin → Komposition** mit `ExportController`, `UpdateController`, `TabRouter` als QObject-Members. MainWindow-Klasse schrumpft auf < 200 LOC.

### Tradeoffs

- **Komposition:** + Saubere Architektur, + Diamond-Problem gelöst, + Test-Isolation, - 2-3 Tage Refactor, - Viele Tests müssen umgeschrieben werden. Tradeoff: 3 Tage für signifikante Qualitätsverbesserung.
- **Nur Mixin-Split:** + Schneller, - Verbleibt bei MRO-Problemen. Tradeoff: 1 Tag, halbe Lösung.

### Detaillierte Subtasks (im Sub-Plan)

1. `ExportController(QObject)` mit Signal `export_finished = pyqtSignal(str)`
2. Methoden aus `ExportCoreMixin`, `ExportJsonSyncMixin`, `ExportTabSpecificMixin` in `ExportController` verschieben
3. `UpdateController(QObject)` analog
4. `TabRouter` analog
5. MainWindow-Klasse schrumpft auf < 200 LOC (von aktuell ~925 LOC)

### Migrations-Strategie

- **Phase 1:** Neue Controller-Klassen erstellen, parallel zu Mixins (1 Tag)
- **Phase 2:** MainWindow-Methoden auf Controller umleiten, Mixin-Methoden als Deprecation-Wrapper (0,5 Tag)
- **Phase 3:** Mixins löschen, MainWindow aufräumen (0,5 Tag)
- **Phase 4:** Tests anpassen, Coverage-Check (0,5-1 Tag)

---

## 📊 Übersicht der 5 Sub-Pläne

| Sub-Plan | Datei | Aufwand | Prio | Abhängigkeiten |
|---|---|---|---|---|
| C3 (Update) | `2026-06-14_subplan_update_controller.md` | M (1 d) | P0 | — |
| C1 (Subshell) | `2026-06-14_subplan_subshell_ipc.md` | XL (3-5 d) | P1 | PO/Lead-Approval |
| C6 (DB-Pool) | `2026-06-14_subplan_db_connection_pool.md` | L (2 d) | P1 | — |
| C4 (Optimizer) | `2026-06-14_subplan_optimizer_perf.md` | L (2 d) | P1 | — |
| A1 (Mixin) | `2026-06-14_subplan_mixin_refactor.md` | L (2-3 d) | P1 | — |

**Empfohlene Reihenfolge der Sub-Plan-Erstellung:**

1. **C3-SUBPLAN-A** zuerst (P0, kleinster Aufwand, löst Sicherheits-Risiko)
2. **C6-SUBPLAN-A** als Nächstes (P1, löst Race-Conditions)
3. **C4-SUBPLAN-A** (P1, Performance)
4. **A1-SUBPLAN-A** (P1, Architektur)
5. **C1-SUBPLAN-A** zuletzt (P1, größter Aufwand, braucht PO-Approval)

> **Wichtig:** Sub-Pläne sollten **vor** dem jeweiligen Cluster-Start erstellt und mit PO/Lead abgestimmt werden. Sie enthalten Architektur-Entscheidungen, die nicht im laufenden Sprint revidiert werden sollten.

---

## 📊 Implementations-Status (Stand: Sprint 4, 2026-06-14)

| Sub-Plan | Geplant | Implementiert | Quick-Wins separat erledigt |
|---|---|---|---|
| **C3 (Update-Controller)** | QThread-Wrapper für `_check_version`, `git verify-commit` | ❌ Nicht implementiert | ✅ M-1 (SubprocessRunner QObject in `chormanager/ui/subprocess_runner.py`) — bereit als Baustein. M-3 (`processEvents` entfernen) offen. |
| **C1 (Subshell-IPC)** | Modul-Einbettung der ChorAufstellung | ❌ Nicht implementiert | ✅ M-7 (Pfad-Validation in `chormanager/ui/choraufstellung_launcher.py`). M-1 (Launcher-Tests grün). |
| **C6 (DB-Connection-Pool)** | Pool pro Tab + `BEGIN IMMEDIATE` | ❌ Nicht implementiert | ✅ m-6 (Transaktion in `ProjectRepository.set_active`). ✅ m-7 (INSERT OR IGNORE in `AvailabilityRepository.update`). |
| **C4 (Optimizer-Perf)** | QThread + Dict-Index | ❌ Nicht implementiert | ✅ R-1 (AffinityRule Bounds-Check via GridEngine). ✅ R-2 (Sanity-Asserts). ✅ Property-Tests (HYPOTHESIS-FIX-A) entdeckten Latent-Bug (`compute_cost` returnt `inf` für unplatzierte Sänger). |
| **A1 (Mixin-Refactor)** | Mixin → QObject-Komposition | 🟡 **Scoped angefangen**: `TabSignals(QObject)` + `TabDescriptor` als Kompositions-Bausteine. Doc-Update in `main_window.py` mit Migrations-Strategie. | ✅ A-2 (PyQt5-Fallbacks entfernt). ✅ A-3 (VoiceGroup-Cache nach `singer_model.py`). |

### Empfohlene nächste Schritte (Reihenfolge)

1. **C-6** als erstes umsetzen (P1, 2 d, kleinster XL-Sub-Plan nach C-3).
2. **C-4** Dict-Index (10-Zeilen-Quick-Win) + QThread-Wrapper (1 d).
3. **C-3** QThread-Wrapper für `_check_version` (0,5 d, da `SubprocessRunner` bereits da).
4. **A-1** Mixin → Komposition für `ExportController` (1 d).
5. **C-1** Subshell-IPC — größter Scope (XL), braucht PO-Approval.

### Beweis-Dokumente

* Sprint 2: `chormanager/ui/subprocess_runner.py` (M-1, 195 LOC) — Baustein für C-3
* Sprint 3: `chormanager/backup/service.py:_sqlite_backup` (m-9) — Alternative zu C-6-Pattern
* Sprint 3: `chormanager/domain/repository.py:ProjectRepository.set_active` (m-6) — `db.transaction()`-Wrapper
* Sprint 4: `chormanager/ui/tab_signals.py:TabSignals` (A-1 first step) — Kompositions-Baustein
* Sprint 4: `tests/unit/test_optimizer_guards.py` (MUTMUT-FIX-A) — Regression-Tests für Optimizer-Guards

### Akzeptanz

Diese 5 Sub-Pläne sind **vorbereitet** (Phase 1 abgeschlossen), aber **nicht vollständig implementiert** (Phase 2 offen). Die Quick-Wins, die im Rahmen der jeweiligen Sub-Pläne identifiziert wurden, sind separat in Sprint 1–4 fertig geworden. Der zukünftige Maintainer sollte mit **C-6** (kleinster XL-Task) starten, dann **C-4** und **C-3** in einem Sprint kombinieren.
