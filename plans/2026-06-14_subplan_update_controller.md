# Sub-Plan: Update-Controller — Timeout, Async, Signaturpruefung (C-3)

| Feld | Wert |
|------|------|
| **Quelle** | `docs/reports/2026-06-14_code-review.md` — **C-3** (Subprocess-Spawn ohne UI-Feedback / blockierender `subprocess.run`) |
| **Bezug** | `plans/2026-06-14_m4_findings.md` — Cluster B / C3-SUBPLAN-A |
| **Status** | 📝 **Vorbereitet** (Sprint 1.7) — Implementierung in Sprint 2 |
| **Owner** | TBD |
| **Prio** | P0 (Block-Release) |
| **Aufwand** | M (1,0 Personentag) |
| **Risiko** | Niedrig (isolierter Controller, gutes Mock-Substrat) |

## 🎯 Ziel

Die `VersionCheckDialog`-Pipeline in `chormanager/ui/update_controller.py`
darf den UI-Thread **nicht mehr** fuer beliebig lange blockieren. Statt
`subprocess.run(...)` + `QApplication.processEvents()`-Workarounds:

1. **Asynchroner Check** via `QThread`-Worker.
2. **Begrenzter `git pull`** via `subprocess.run(..., timeout=60)` + klares
   Fehler-Handling.
3. **Kryptografische Pruefung** des heruntergeladenen Commits (`git verify-commit`).
4. **Erzwungener App-Neustart** nach erfolgreichem Update.

## 🏗️ Architektur-Entscheidung

### Variante A — QThread-Worker (gewählt ✅)

- `UpdateCheckWorker(QThread)` mit `pyqtSignal(dict) finished` fuer HTTP-Lookup.
- `UpdatePullWorker(QThread)` mit `pyqtSignal(bool) finished` fuer `git pull`.
- Vorteile:
  - Native Qt-Integration, kein `asyncio`-Loop noetig.
  - Saubere Lifecycle-Kontrolle (`worker.deleteLater()`).
  - Leicht testbar via `pytest-qt` mit `qtbot.waitSignal(...)`.
- Nachteile:
  - Mehr Boilerplate als `QRunnable` + `QThreadPool`.
  - Signal-Disconnects bei Tear-Down beachten (Memory-Leak-Risiko).

### Variante B — `QRunnable` + `QThreadPool` (abgelehnt ❌)

- Vorteile: Weniger Code.
- Nachteile: Keine nativen Qt-Signale, Signal-Mapping via `QObject.metaObject`
  komplexer. Schlechtere Test-Story.

### Variante C — `asyncio` in separatem Thread (abgelehnt ❌)

- Vorteile: Saubere Coroutine-Semantik fuer `urllib.request` + `asyncio.create_subprocess_exec`.
- Nachteile: Volle `asyncio`-Integration in PyQt6 nicht trivial (`qasync`-Bruecke
  noetig). Verlaesst das etablierte Qt-Pattern der Codebase.

## 📋 Akzeptanzkriterien

| # | Kriterium | Verifikation |
|---|-----------|--------------|
| A1 | `processEvents()`-Loops vollstaendig entfernt aus `update_controller.py` | grep + py_compile |
| A2 | Check laeuft in `QThread`; UI bleibt interaktiv (Drag&Drop bleibt nutzbar) | manueller Test |
| A3 | `git pull` hat hartes `timeout=60s` | `subprocess.run(..., timeout=60)` |
| A4 | Nach erfolgreichem `git pull` wird `git verify-commit HEAD` ausgefuehrt; bei Mismatch Rollback-Hinweis im Statusbar | Test T-4 |
| A5 | Bei Update-Erfolg: Dialog fordert User zum Neustart auf; bei Abbruch bleibt App offen | manueller Test |
| A6 | Test `tests/unit/test_update_controller.py` mit `monkeypatch.setattr(subprocess, "run", ...)` | pytest gruen |
| A7 | `_check_version()` laesst sich ohne GitHub-Netzwerk testen | `monkeypatch.setattr(urllib.request, "urlopen", ...)` |

## 🧩 Modul-Schnitt (Soll)

```
chormanager/ui/update_controller.py
├── UpdateCheckWorker(QThread)
│   ├── run(): urllib.request.urlopen(timeout=10) → emit finished(dict)
│   └── finished = pyqtSignal(dict)
├── UpdatePullWorker(QThread)
│   ├── run(): subprocess.run(["git", "pull"], timeout=60) → emit finished(bool)
│   ├── run() (Schritt 2): subprocess.run(["git", "verify-commit", "HEAD"], timeout=10)
│   └── finished = pyqtSignal(bool)
├── VersionCheckDialog(QDialog)
│   ├── _check_version(): startet UpdateCheckWorker, connect auf finished
│   └── _do_update(): startet UpdatePullWorker, connect auf finished
```

## 🔧 Implementation-Details

### 1. `processEvents` ersetzen (C3-SUBPLAN-A.1)

**Vorher** (`update_controller.py`):
```python
QApplication.processEvents()
```

**Nachher**:
```python
QApplication.setOverrideCursor(Qt.WaitCursor)
try:
    worker.start()
finally:
    QApplication.restoreOverrideCursor()
```

### 2. Worker-Basis (C3-SUBPLAN-A.2 + A.3)

```python
from PyQt6.QtCore import QThread, pyqtSignal

class UpdateCheckWorker(QThread):
    finished = pyqtSignal(dict)

    def __init__(self, url: str, timeout: int = 10, parent=None):
        super().__init__(parent)
        self._url = url
        self._timeout = timeout

    def run(self) -> None:
        import urllib.request
        try:
            with urllib.request.urlopen(self._url, timeout=self._timeout) as r:
                payload = json.loads(r.read().decode("utf-8"))
            self.finished.emit({"ok": True, "payload": payload})
        except Exception as exc:
            self.finished.emit({"ok": False, "error": str(exc)})


class UpdatePullWorker(QThread):
    finished = pyqtSignal(bool, str)  # ok, error_msg

    def __init__(self, timeout: int = 60, parent=None):
        super().__init__(parent)
        self._timeout = timeout

    def run(self) -> None:
        import subprocess
        try:
            pull = subprocess.run(
                ["git", "pull", "--ff-only"],
                capture_output=True, text=True, timeout=self._timeout, check=False,
            )
            if pull.returncode != 0:
                self.finished.emit(False, f"git pull failed: {pull.stderr}")
                return
            # Signatur verifizieren
            verify = subprocess.run(
                ["git", "verify-commit", "HEAD"],
                capture_output=True, text=True, timeout=10, check=False,
            )
            if verify.returncode != 0:
                self.finished.emit(False, f"verify-commit failed: {verify.stderr}")
                return
            self.finished.emit(True, "")
        except subprocess.TimeoutExpired:
            self.finished.emit(False, "timeout")
        except Exception as exc:
            self.finished.emit(False, str(exc))
```

### 3. Lifecycle (Memory-Leak-Praevention)

```python
def _on_check_finished(self, result: dict) -> None:
    worker = self.sender()
    if isinstance(worker, QThread):
        worker.quit()
        worker.wait(2000)
        worker.deleteLater()
    # ... result verarbeiten
```

## 🧪 Test-Plan (T-4, `tests/unit/test_update_controller.py`)

| Test | Setup | Assertion |
|------|-------|-----------|
| `test_check_success_emits_ok` | monkeypatch `urllib.request.urlopen` mit `MagicMock` | `finished` Signal `{"ok": True, ...}` |
| `test_check_timeout_emits_error` | `urlopen` raises `socket.timeout` | `{"ok": False, "error": ...}` |
| `test_pull_success` | monkeypatch `subprocess.run` returns `CompletedProcess(0, "")` | `finished(True, "")` |
| `test_pull_verify_fails` | pull ok, verify-commit exit 1 | `finished(False, "verify-commit failed: ...")` |
| `test_pull_timeout` | `subprocess.run` raises `TimeoutExpired` | `finished(False, "timeout")` |
| `test_processEvents_removed` | statische Quellcode-Analyse: kein `processEvents` mehr in `update_controller.py` | AST- oder Regex-Check |

## 🛡️ Risk-Assessment

| Risiko | Wahrscheinlichkeit | Impact | Mitigation |
|--------|-------------------|--------|------------|
| `QThread`-Memory-Leak (Worker nicht `deleteLater`) | Mittel | Niedrig | Lifecycle-Helper aus Punkt 3 |
| `git verify-commit` nicht im PATH / GPG-Key fehlt | Hoch | Mittel | Klare Fehlermeldung, KEIN erzwungener Rollback (User manuell) |
| `git pull --ff-only` schlaegt bei abweichendem Branch fehl | Niedrig | Niedrig | Hinweis-Dialog mit "force update" als zukuenftige P2-Erweiterung |
| `setOverrideCursor` nicht wiederhergestellt bei Worker-Exception | Niedrig | Niedrig | try/finally um `worker.start()` |

## 📅 Sprint-Einordnung

- **Vorbereitung** (dieses Dokument, Sprint 1.7): ✅ abgeschlossen.
- **Implementierung** (Sprint 2, Prio P0): C3-SUBPLAN-A.1 bis A.7.
- **Review & Polish** (Sprint 2, Ende): A.5 + A.7 manueller Test mit echtem GitHub.

## 🔗 Verweise

- Code-Review: `docs/reports/2026-06-14_code-review.md` — C-3
- Haupt-Plan: `plans/2026-06-14_m4_findings.md` — Cluster B
- Sub-Plan-Index: `plans/2026-06-14_m4_anhang_b_subplans.md`
- Original-Datei: `chormanager/ui/update_controller.py:1-114`
- Test-Datei (Soll): `tests/unit/test_update_controller.py` (neu)

---

**Erstellt:** 2026-06-14 — Sprint 1.7
