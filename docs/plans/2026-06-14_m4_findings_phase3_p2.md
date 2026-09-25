# Plan: M-4 — Findings Phase 3 (P2, Nice-to-Have)

**Datum:** 2026-06-14
**Bezug:** `docs/reports/2026-06-14_code-review.md` und `2026-06-14_m4_findings.md`
**Scope:** P2-Cluster J (Cleanup), K (Repository/SQL), L (UI-Polish), M (Robustheit), N (Security), O (Mutation-Tests)

> **Hinweis:** Diese Datei dokumentiert die P2-Phase. Für Sprint-Reihenfolge, Aufwand-Schätzung, Akzeptanz-Gates siehe Hauptdatei.

---

## 🟢 Phase 3 — Nice-to-Have (P2)

### Cluster J: Cleanup (A-2, A-3, A-4, m-2, m-10, Dead-Code)

#### A2-FIX-A · Tote PyQt5-Fallbacks entfernen
- **Prio:** P2 · **Aufwand:** S (0,5 Tag) · **Abhängigkeiten:** —
- **Akzeptanz:** (1) Kein `try/except ImportError` für PyQt5. (2) `qt_compat.exec_qt()`, `FallbackSinger`, `FallbackOptimizerDialog` entfernt oder als deprecated markiert.
- **Subtasks:**
  - [ ] **A2-FIX-A.1** Audit: welche Module importieren `qt_compat.exec_qt` oder `FallbackSinger`?
  - [ ] **A2-FIX-A.2** Direkte PyQt6-Imports statt qt_compat.
  - [ ] **A2-FIX-A.3** `qt_compat.py` löschen oder auf reine Qt-Aliase reduzieren.
  - [ ] **A2-FIX-A.4** `requirements.txt` bereinigen (PyQt5 raus).
  - [ ] **A2-FIX-A.5** Test grün.

#### A3-FIX-A · Modul-globale Lazy-Caches refactoren
- **Prio:** P2 · **Aufwand:** S (0,3 Tag) · **Abhängigkeiten:** —
- **Akzeptanz:** (1) `VoiceGroup`-Cache in `singer_model.py` (Singleton), nicht in `chormanager_bridge`.
- **Subtasks:**
  - [ ] **A3-FIX-A.1** Cache aus `chormanager/choraufstellung/chormanager_bridge.py:39-46` in `singer_model.py` verschieben.
  - [ ] **A3-FIX-A.2** Test schreiben.

#### DEADCODE-FIX-A · `_menu_legenda` und andere tote Methoden
- **Prio:** P2 · **Aufwand:** XS (0,1 Tag) · **Abhängigkeiten:** —
- **Akzeptanz:** (1) Keine leeren Methoden in `main.py`.
- **Subtasks:**
  - [ ] **DEADCODE-FIX-A.1** `chormanager/choraufstellung/main.py:761-769` `_menu_legenda` löschen.
  - [ ] **DEADCODE-FIX-A.2** `get_primary_rules`, `get_refinement_rules` in `chormanager/choraufstellung/core/rules.py:664-665` prüfen.

### Cluster K: Repository & SQL (m-6, m-7)

#### m6-FIX-A · `EventRepository.set_active` mit `BEGIN IMMEDIATE`
- **Prio:** P2 · **Aufwand:** XS (0,2 Tag) · **Abhängigkeiten:** C6-SUBPLAN-A
- **Akzeptanz:** (1) Zwei aufeinanderfolgende `set_active`-Aufrufe in Transaktion wickeln. (2) Maximal ein aktives Projekt.
- **Subtasks:**
  - [ ] **m6-FIX-A.1** `with self.db.transaction():` um `chormanager/domain/repository.py:418-422`.
  - [ ] **m6-FIX-A.2** Test schreiben.

#### m7-FIX-A · `AvailabilityRepository.update` `INSERT OR IGNORE` + expliziter UPDATE
- **Prio:** P2 · **Aufwand:** S (0,3 Tag) · **Abhängigkeiten:** —
- **Akzeptanz:** (1) Keine Geister-Zeilen mit zufälliger UUID.
- **Subtasks:**
  - [ ] **m7-FIX-A.1** `INSERT OR IGNORE` + separate `UPDATE` in `chormanager/domain/repository.py:344-349`.
  - [ ] **m7-FIX-A.2** Test schreiben.

### Cluster L: UI-Polish (CC-3, CC-4, m-3, m-5)

#### CC3-FIX-A · Auto-Arrange in Worker-Thread
- **Prio:** P2 · **Aufwand:** M (1 Tag) · **Abhängigkeiten:** C4-SUBPLAN-A (Worker-Pattern)
- **Akzeptanz:** (1) `auto_arrange_*` läuft in Worker-Thread. (2) Progress-Signal.
- **Subtasks:**
  - [ ] **CC3-FIX-A.1** `ArrangeWorker(QThread)`.
  - [ ] **CC3-FIX-A.2** 5 Methoden in `chormanager/choraufstellung/widgets/formation_grid.py:427-558` migrieren.
  - [ ] **CC3-FIX-A.3** Test schreiben.

#### CC4-FIX-A · Singleton-Search-Pulse-Timer
- **Prio:** P2 · **Aufwand:** XS (0,2 Tag) · **Abhängigkeiten:** —
- **Akzeptanz:** (1) Ein Timer pro Grid, nicht pro `highlight_singer`-Call.
- **Subtasks:**
  - [ ] **CC4-FIX-A.1** In `chormanager/choraufstellung/widgets/formation_grid.py:160-162` `self._search_pulse_timer` als Init-Attribut, in `highlight_singer` prüfen `if self._search_pulse_timer: self._search_pulse_timer.stop()`.
  - [ ] **CC4-FIX-A.2** Test schreiben.

#### m3-FIX-A · `update_singers` Batch-Update
- **Prio:** P2 · **Aufwand:** S (0,5 Tag) · **Abhängigkeiten:** —
- **Akzeptanz:** (1) `update_singers(..., deferred=True)` mit `QTimer.singleShot(0, ...)`. (2) Mehrere Calls in einem Frame → ein Repaint.
- **Subtasks:**
  - [ ] **m3-FIX-A.1** Helper in `SingerPool`.
  - [ ] **m3-FIX-A.2** Test schreiben.

#### m5-FIX-A · `FormationGrid.refresh_grid` Tile-Cache statt `findChildren`
- **Prio:** P2 · **Aufwand:** XS (0,2 Tag) · **Abhängigkeiten:** —
- **Akzeptanz:** (1) `self._row_labels: List[QLabel]` als Member. (2) `findChildren(QLabel)` ersetzt.
- **Subtasks:**
  - [ ] **m5-FIX-A.1** In `chormanager/choraufstellung/widgets/formation_grid.py:326-328` eigene Liste.
  - [ ] **m5-FIX-A.2** Test schreiben.

### Cluster M: Robustheit (m-4, m-10)

#### m4-FIX-A · Symlink-Replace-Race in `save_autosave`
- **Prio:** P2 · **Aufwand:** XS (0,1 Tag) · **Abhängigkeiten:** C5-FIX-A (Symlink wird sowieso entfernt)
- **Akzeptanz:** (1) `try/except FileNotFoundError` um `os.remove(latest_link)`.
- **Subtasks:**
  - [ ] **m4-FIX-A.1** Siehe C5-FIX-A.1 (entfällt durch C5-FIX-A).

#### m10-FIX-A · `BackupService.list_backups` `key=os.path.getmtime`
- **Prio:** P2 · **Aufwand:** XS (0,1 Tag) · **Abhängigkeiten:** —
- **Akzeptanz:** (1) Sortierung nach mtime, nicht nach Filename.
- **Subtasks:**
  - [ ] **m10-FIX-A.1** In `chormanager/backup/service.py:67` `key=os.path.getmtime, reverse=True`.
  - [ ] **m10-FIX-A.2** Test schreiben.

### Cluster N: Security (S-2)

#### S2-FIX-A · TLS-Cert-Hinweis in Doku
- **Prio:** P2 · **Aufwand:** XS (0,1 Tag) · **Abhängigkeiten:** —
- **Akzeptanz:** (1) Hinweis in `docs/benutzerhandbuch.md` über MITM-Proxy-Limitation.
- **Subtasks:**
  - [ ] **S2-FIX-A.1** Doku-Sektion ergänzen.

### Cluster O: Mutation-Tests & Property-Based

#### HYPOTHESIS-FIX-A · Property-Based-Tests für `AffinityCostFunction`
- **Prio:** P2 · **Aufwand:** M (1 Tag) · **Abhängigkeiten:** C4-SUBPLAN-A
- **Akzeptanz:** (1) `hypothesis` für `compute_cost` mit zufälligen Sänger-Listen. (2) Invariante: `compute_cost(pairs) >= 0`.
- **Subtasks:**
  - [ ] **HYPOTHESIS-FIX-A.1** `hypothesis` zu `requirements.txt` hinzufügen.
  - [ ] **HYPOTHESIS-FIX-A.2** Test in `tests/unit/test_affinity_properties.py`.

#### MUTMUT-FIX-A · Mutation-Tests für `core/optimizer.py`
- **Prio:** P2 · **Aufwand:** M (1 Tag) · **Abhängigkeiten:** C2-FIX-A, T1-FIX-A
- **Akzeptanz:** (1) `mutmut run` überlebt > 80 % der Mutationen.
- **Subtasks:**
  - [ ] **MUTMUT-FIX-A.1** `mutmut` konfigurieren.
  - [ ] **MUTMUT-FIX-A.2** Mutation-Run, gefundene Survivors fixen.

---

## 📊 P2-Aufwand-Schätzung (Detail)

| Cluster | Anzahl | Aufwand |
|---|---:|---:|
| J (Cleanup) | 3 | ~0,9 Tage |
| K (Repository/SQL) | 2 | ~0,5 Tage |
| L (UI-Polish) | 4 | ~2 Tage |
| M (Robustheit) | 2 | ~0,2 Tage |
| N (Security) | 1 | ~0,1 Tage |
| O (Mutation-Tests) | 2 | ~2 Tage |
| **Σ P2** | **19** | **~12 Tage** |
