# Sub-Plan: AffinityRule Performance + QThread-Migration (C-4)

| Feld | Wert |
|------|------|
| **Quelle** | `docs/reports/2026-06-14_code-review.md` — **C-4** (Optimizer blockiert UI-Thread) |
| **Bezug** | `plans/2026-06-14_m4_findings.md` — Sprint 2 / Cluster F / C4-SUBPLAN-A |
| **Status** | 📝 **Vorbereitet** (Sprint 2.6) — Implementation Sprint 3 |
| **Prio** | P1 |
| **Aufwand** | L (2 Personentage) |
| **Risiko** | Mittel (Hot-Path-Refactor + Threading) |

## 🎯 Ziel

`AffinityRule` und `FormationOptimizer` so umbauen, dass:

1. **50 Saenger mit 20 Affinitaets-Paaren < 1 Sekunde** Laufzeit.
2. **UI-Thread bleibt interaktiv** waehrend Optimierung.
3. **Progress-Signal** fuer UI (z. B. `QProgressBar`).
4. **Singersuche O(1)** via Dict-Index statt O(n) Listen-Scan.
5. **Bestehende API** (Rule-Interface) bleibt rueckwaertskompatibel.

## 🏗️ Architektur

### Variante A — `QThread`-Worker + Dict-Index (empfohlen ✅)

```
MainWindow (UI-Thread)
   ├── OptimizerDialog (UI)
   │    └── Start-Button
   └── OptimizerWorker(QThread)
        ├── run(): FormationOptimizer.run() in worker
        ├── progress = pyqtSignal(int, int)  # (iteration, max_iterations)
        ├── finished = pyqtSignal(object)    # OptimizeFormationCommand
        └── error = pyqtSignal(str)
```

**Optimierungen:**
1. `self._singer_by_id = {s.singer_id: s for s in singers}` einmal zu Beginn.
2. `_get_neighbor_positions` cached leere Positionen ausserhalb der inneren Loop.
3. Hot-Path-Methode `AffinityRule._try_swap` ohne `occ1`/`occ2`-Listen-Iteration.

**Vorteile:**
- Saubere Qt-Integration
- Testbar mit `qtbot.waitSignal(...)`
- Hot-Path messbar besser

**Nachteile:**
- Mehr Boilerplate als synchroner Aufruf
- Race-Bedingungen bei UI-Updates vermeiden (alle UI-Updates via Signal)

### Variante B — Caching-only (ohne Threading) (abgelehnt ❌)

- Vorteile: Einfacher.
- Nachteile: UI-Block bei grossen Formationen bleibt.

### Variante C — `numpy`-basiertes Backend (abgelehnt ❌)

- Vorteile: Schneller.
- Nachteile: Massive Refactor, `SingerRef`-Datenklasse passt nicht zu Vektorisierung.

## 📋 Akzeptanzkriterien

| # | Kriterium | Verifikation |
|---|-----------|--------------|
| A1 | 50 Saenger, 20 Affinitaets-Paare: < 1 s Wandzeit | Test T-2 mit `@pytest.mark.timeout(2)` |
| A2 | UI bleibt interaktiv waehrend Optimierung (Drag&Drop moeglich) | manueller Test mit `qtbot.waitSignal` |
| A3 | `OptimizerWorker` emittiert Progress-Signal mindestens 1x pro Iteration | Test |
| A4 | Dict-Index ersetzt alle O(n) Singersuchen in `_try_swap` | Code-Review + `grep` |
| A5 | `Aff`inityRule.apply` API unveraendert | `test_arrangement_rules.py` gruen |

## 🧩 Implementation-Skizze

### Phase 1 — Hot-Path-Mikro-Optimierungen (0,5 d)

```python
class AffinityRule(ArrangementRule):
    def apply(self, singers, rows, cols, ...):
        # NEU: O(1) Index
        singer_by_id = {s.singer_id: s for s in singers}
        # NEU: leere Positionen cachen
        empty_positions = self._compute_empty_positions(singers, rows, cols)
        # ... bestehende Logik, aber mit Index
```

### Phase 2 — Worker-Klasse (0,5 d)

```python
class OptimizerWorker(QThread):
    progress = pyqtSignal(int, int)
    finished = pyqtSignal(object)
    error = pyqtSignal(str)

    def __init__(self, grid, rule_ids, parent=None):
        super().__init__(parent)
        self._grid = grid
        self._rule_ids = rule_ids

    def run(self):
        try:
            cmd = FormationOptimizer.run(self._grid, self._rule_ids)
            self.finished.emit(cmd)
        except Exception as exc:
            self.error.emit(str(exc))
```

### Phase 3 — UI-Integration (0,5 d)

```python
# In MainWindow.run_optimizer():
self.optimizer_worker = OptimizerWorker(self.grid, rule_ids)
self.optimizer_worker.finished.connect(self._on_optimizer_finished)
self.optimizer_worker.error.connect(self._on_optimizer_error)
self.progress_dialog = QProgressDialog("Optimierung...", "Abbrechen", 0, 100, self)
self.optimizer_worker.progress.connect(self.progress_dialog.setValue)
self.optimizer_worker.start()
```

### Phase 4 — Tests + Bench (0,5 d)

- `tests/unit/test_affinity_perf.py` mit `@pytest.mark.timeout(2)`.
- `bench/optimizer_bench.py` fuer manuelle Messung.

## 🛡️ Risk-Assessment

| Risiko | Wahrscheinlichkeit | Impact | Mitigation |
|--------|-------------------|--------|------------|
| Threading-Race bei UI-Updates | Mittel | Mittel | `QMetaObject.invokeMethod` oder nur-Signal-Updates |
| `QThread.deleteLater()`-Lifecycle-Leak | Niedrig | Niedrig | Connect `finished` → `worker.deleteLater` |
| Dict-Index vergroessert Memory-Footprint | Niedrig | Niedrig | 50 Saenger ~ 50 Eintraege, irrelevant |
| Backward-Compat bricht (Rule-Signatur) | Niedrig | Mittel | Akzeptanzkriterium A5 |

## 📅 Sprint-Einordnung

- **Vorbereitung** (Sprint 2.6, dieses Dokument): ✅
- **Implementation** (Sprint 3 oder Sprint 4, je nach Sprint-Plaetzen)

## 🔗 Verweise

- Code-Review: `docs/reports/2026-06-14_code-review.md` — C-4
- Haupt-Plan: `plans/2026-06-14_m4_findings.md` — Sprint 2
- Sub-Plan-Index: `plans/2026-06-14_m4_anhang_b_subplans.md`
- Original-Datei: `chormanager/choraufstellung/core/rules.py:351-495` (AffinityRule)

---

**Erstellt:** 2026-06-14 — Sprint 2.6
