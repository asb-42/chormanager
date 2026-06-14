# Sub-Plan: Subshell-IPC-Architektur (C-1)

| Feld | Wert |
|------|------|
| **Quelle** | `docs/reports/2026-06-14_code-review.md` — **C-1** (Subshell-Spawn blockiert Main-Thread, Temp-JSON-Leak) |
| **Bezug** | `plans/2026-06-14_m4_findings.md` — Sprint 2 / Cluster E / C1-SUBPLAN-A |
| **Status** | 📝 **Vorbereitet** (Sprint 2.5) — Spike-Phase Sprint 3 |
| **Prio** | P1 |
| **Aufwand** | XL (3-5 Personentage, ueber 2 Sprints) |
| **Risiko** | Hoch (Architektur-Wechsel) |

## 🎯 Ziel

Die ChorAufstellung-Subshell-Architektur so umbauen, dass:

1. **Kein blockierender `subprocess.run` mit Endlos-Wait** mehr im Main-Thread laeuft.
2. **Keine Temp-JSON-Leaks** durch vergessene Dateien in `/tmp`.
3. **Backup-Restore-Race** zwischen ChorManager und ChorAufstellung eliminiert.
4. **Eine klare Topologie** fuer Tests (zwei MainWindows in einem Prozess).

## 🏗️ Architektur-Optionen

### Variante A — Modul-Einbettung (empfohlen ✅)

```
chormanager (Hauptprozess)
  ├── MainWindow (ChorManager)
  └── choraufstellung_tab (importiert choraufstellung direkt)
       └── MainWindow (ChorAufstellung) als eingebettetes Widget
```

**Vorteile:**
- Kein Subshell-Overhead, keine Temp-Files
- Direkter Funktionsaufruf statt IPC
- Tests trivial: zwei MainWindow-Instanzen im gleichen Prozess
- Drag-and-Drop zwischen Tabs trivial
- `host._is_modified` synchron ohne Race

**Nachteile:**
- Beide Apps muessen gleiche Python-Version / Qt-Version nutzen
- ChorAufstellung laeuft als MDI/Sub-Widget statt eigenstaendiger Prozess
- Kein Cross-Process-Update (gut, wollen wir nicht)

### Variante B — `multiprocessing.connection` (abgelehnt ❌)

**Vorteile:** Saubere Trennung der Prozesse.
**Nachteile:** Komplexe IPC-Protokoll-Schicht, schwer testbar, gleiche Race-Probleme.

### Variante C — Status quo + Cleanup (abgelehnt ❌)

**Vorteile:** Kein Architektur-Wechsel.
**Nachteile:** Behebt nur Symptome (Temp-Leak), nicht die Ursache (blockierende Subshell).

## 📋 Akzeptanzkriterien

| # | Kriterium | Verifikation |
|---|-----------|--------------|
| A1 | ChorAufstellung laeuft als importiertes Modul im Hauptprozess | manueller Test |
| A2 | Keine `subprocess.run([sys.executable, "__main__.py"])` mehr | `grep` |
| A3 | Temp-JSON-Dateien werden in `tempfile.TemporaryDirectory()` erzeugt und automatisch aufgeraeumt | Test |
| A4 | `_reload_after_restore` funktioniert ohne Crash auch wenn ChorAufstellung-Tab offen | Integration-Test |
| A5 | Zwei `MainWindow`-Instanzen in einem Test-Prozess funktionieren | Test T-3 |
| A6 | Drag-and-Drop zwischen ChorManager- und ChorAufstellung-Widgets bleibt erhalten | manueller Test |

## 🧩 Implementation-Skizze

### Phase 1 — Spike (0,5 d)

```python
# Minimaler Spike: ChorAufstellung-MainWindow direkt importieren
from chormanager.choraufstellung.main import MainWindow as ChorAufMainWindow
# In choraufstellung_tab:
self.inner_window = ChorAufMainWindow(
    chormanager_mode=True, project_name=..., event_date=..., ...
)
self.layout.addWidget(self.inner_window)
```

Akzeptanz: Lade-Test mit echtem DB-Sample.

### Phase 2 — Datenmodell (1 d)

- `host.singers` als zentrale Source-of-Truth.
- `ChorAufstellungLauncher` wird zu `ChorAufstellungTab` (kein Spawn mehr).
- Bridge-Klassen bleiben, nur Aufruf-Kontext aendert sich.

### Phase 3 — Temp-Cleanup (0,5 d)

```python
with tempfile.TemporaryDirectory(prefix="chor_") as tmp:
    json_path = os.path.join(tmp, "event.json")
    # ... schreibe JSON
    bridge.load_from_json(json_path)
# tmp wird automatisch aufgeraeumt
```

### Phase 4 — Tests (1 d)

- `tests/integration/test_two_mainwindows.py`
- `tests/integration/test_choraufstellung_no_subprocess.py`
- `tests/integration/test_tempfile_cleanup.py`

## 🛡️ Risk-Assessment

| Risiko | Wahrscheinlichkeit | Impact | Mitigation |
|--------|-------------------|--------|------------|
| Qt-Event-Loop-Konflikte zwischen 2 MainWindows | Mittel | Hoch | Phase 1 Spike + gruendliche Tests |
| Tests brechen, weil sie Subshell erwarten | Niedrig | Mittel | `conftest.py` mit `qtbot` Fixture bleibt kompatibel |
| Drag-Drop bricht zwischen Tabs | Niedrig | Mittel | Akzeptanzkriterium A6 mit manuellem Test |
| ChorAufstellung-Bridge setzt globale Annahmen voraus (env vars) | Hoch | Mittel | env vars als Konstruktor-Args |

## 📅 Sprint-Einordnung

- **Vorbereitung** (Sprint 2.5, dieses Dokument): ✅ abgeschlossen
- **Spike-Phase** (Sprint 3): Variante A validieren
- **Implementation** (Sprint 4 oder spaeter): Phasen 1-4

## 🔗 Verweise

- Code-Review: `docs/reports/2026-06-14_code-review.md` — C-1
- Haupt-Plan: `plans/2026-06-14_m4_findings.md` — Sprint 2
- Sub-Plan-Index: `plans/2026-06-14_m4_anhang_b_subplans.md`
- Original-Datei: `chormanager/ui/choraufstellung_launcher.py:151-218, 221-308`

---

**Erstellt:** 2026-06-14 — Sprint 2.5
