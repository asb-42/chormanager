# Code Review — ChorManager

**Datum:** 2026-06-12
**Reviewer:** Senior-Review (statisch, ohne Ausführung)
**Codebase:** `chormanager/` (13 129 LOC, 41 Python-Module)
**Branch/Stand:** Stand nach Phase 1-6 (163 Tests grün, Coverage 28 % → 42 %)
**Test-Stand:** `python -m pytest tests/ -q` → 386 passed

---

## 🎯 Executive Summary

| Kategorie | Score (1-10) | Kurzbegründung |
|-----------|:-:|---|
| **Code-Qualität** | 5/10 | Funktional korrekt, aber zwei God-Classes (3 104 + 2 180 LOC) und breite `except:`-Klauseln. |
| **Wartbarkeit** | 4/10 | Refactor-Bedarf: `main_window.py`, `dialogs.py`, `choraufstellung/main.py`. Kein globales State-Management, aber Layer-Trennung schwach. |
| **Robustheit** | 5/10 | `except:` an 11 Stellen, fehlende Transaktionen für Multi-Table-Operationen, keine Connection-Pool-Isolation. |
| **Architektur** | 5/10 | Repository-Pattern sauber, UI-Wiring chaotisch. Tests gut strukturiert, aber nur 42 % Coverage. |

**Gesamtbild:** Solide funktionale App, die ihre Hauptaufgabe (Chorverwaltung) erfüllt. Die Hauptprobleme sind **Größe und Kopplung** der UI-Klassen sowie **konventionelle Sicherheits-/Robustheits-Defizite** (SQL-Style, Exception-Handling). Für den produktiven Einsatz in einem Verein/Verband braucht es 2-3 Refactoring-Sprints.

---

## 🔴 Major Findings

### M-1 · God-Class `chormanager/ui/main_window.py` (3 104 LOC)
| Aspekt | Detail |
|--------|--------|
| **Severity** | 🔴 Hoch |
| **Location** | `chormanager/ui/main_window.py:300-2973` |
| **Erklärung** | Die `MainWindow`-Klasse macht Menübau, Toolbar, Tab-Switching, Selection-Routing, Context-Toolbar, **15 Export-Pfade** (CSV, PDF, ODT, JSON, LibreOffice, Synchronisation, …), Versions-Check, Auto-Update (`subprocess.run("git pull")`), Backup-Restore-Wiring, Theming, About-Dialog und _ChorAufstellung_-Subprozess-Spawning. |
| **Risiko** | Jede UI-Änderung berührt diese eine Datei. Reviewer können Änderungen kaum atomar prüfen. Der Phase-6-Bug (`_emit_selection` ignorierte die Tabellen-Row) wäre in einer schlankeren Klasse nicht passiert. |
| **Fix** | Aufteilen in `MainWindow` (nur Window-Lifecycle, Menü, Toolbar) + `ExportController` (alle `_*_export*`-Methoden) + `UpdateController` (Version-Check, Git-Pull). Jeder Controller bekommt eigene Tests. |

### M-2 · God-Class `chormanager/choraufstellung/main.py` (2 180 LOC)
| Aspekt | Detail |
|--------|--------|
| **Severity** | 🔴 Hoch |
| **Location** | `chormanager/choraufstellung/main.py` |
| **Erklärung** | Das Submodul "ChorAufstellung" (Sitzordnung-Editor) enthält 2 180 LOC in einer Datei — Menü, Toolbar, Drag-and-Drop, Auto-Save-Timer, Optimizer-Aufruf, Undo-Stack, Print-Preview. PyQt5/PyQt6-Cross-Kompatibilität ist über `try/except` aktiv. |
| **Risiko** | Diese Datei ist **nicht** durch `chormanager/ui/main_window.py` abgedeckt (eigene Subshell via `subprocess.run`). Eine Änderung hier ist nie regressionstestbar aus der Hauptapp heraus. |
| **Fix** | Genau wie M-1: pro Verantwortlichkeit eine Klasse + Signale als Schnittstelle. Den Auto-Save-Timer und die Undo-Logik in eigene Module extrahieren. |

### M-3 · F-String-SQL mit Spalten-Interpolation
| Aspekt | Detail |
|--------|--------|
| **Severity** | 🟠 Mittel-Hoch |
| **Location** | `chormanager/domain/repository.py:67,78,90,97,106,131,188,227,266,301,384,430,492,505,514,532,612,624,630,641` |
| **Erklärung** | 19 Queries benutzen f-Strings zur Spalten- und Placeholder-Interpolation, z. B. `f"SELECT {cols} FROM singers WHERE id = ?"`. Werte werden korrekt als Parameter übergeben, aber Spaltennamen kommen aus Modul-Konstanten (`_SINGER_COLS`, `_EVENT_COLS`, …). |
| **Risiko** | **Heute** nicht ausnutzbar, weil alle Spalten aus internen Tupel-Konstanten stammen. Aber das Pattern ist eine **tickende Zeitbombe**: Sobald ein Entwickler einen Spaltennamen aus User-Input interpoliert, ist SQL-Injection möglich. Statische Tools (`bandit`, `sqlfluff`) flaggen die ganze Datei. |
| **Fix** | Spaltenliste explizit whitelisten und mit `", ".join(SAFE_COLS)` zusammensetzen, oder ein `QueryBuilder` einführen, der nur vordefinierte Templates akzeptiert. `bandit -r chormanager/domain/` in CI einbinden. |

### M-4 · Ungefangene `except:`-Klauseln
| Aspekt | Detail |
|--------|--------|
| **Severity** | 🟠 Mittel-Hoch |
| **Location** | 11 Stellen: `chormanager/ui/views/choraufstellung_tab.py:187,245`; `chormanager/ui/views/events_tab.py:215`; `chormanager/ui/main_window.py:2826,2910,2938`; `chormanager/choraufstellung/main.py:1216`; `chormanager/choraufstellung/ui/grid_widget.py:27,36`; `chormanager/choraufstellung/dependencies.py:70,87,100` |
| **Erklärung** | `except:` ohne Exception-Spec fängt **alles** ein, inklusive `KeyboardInterrupt`, `SystemExit`, `MemoryError`. Real-World-Bug: `except: pass` in `choraufstellung/main.py:1216` schluckt Fehler, die für Auto-Save-Diagnose kritisch sind. |
| **Risiko** | Maskiert echte Bugs (DB-Connection weg, Disk-Full, Race-Conditions), macht Debugging zum Albtraum. |
| **Fix** | Jede `except:` ersetzen durch konkrete Exception: `except (OSError, KeyError, ValueError) as e:` + Log via `app_logging.get_logger(__name__)`. Linter: `ruff` mit `BLE001` (blind-except) aktivieren. |

### M-5 · Subprocess-Spawns ohne UI-Feedback
| Aspekt | Detail |
|--------|--------|
| **Severity** | 🟠 Mittel |
| **Location** | `chormanager/ui/main_window.py:1470, 1659, 2327, 2332, 2428, 3026, 3052` |
| **Erklärung** | `subprocess.run(...)` blockiert den Main-Thread (z. B. `git log`, `git pull`, `libreoffice --convert-to`). Bei langsamer Disk hängt die UI minutenlang. `_check_version` (3007-3043) und `_do_update` (3045-3063) blockieren den Main-Thread mit Netzwerk-IO. |
| **Risiko** | UI-Freezes, ANR-ähnliches Verhalten, keine Cancel-Möglichkeit für `git pull`. |
| **Fix** | Langlaufende Subprocesses in `QThread` / `QProcess` auslagern. Git-Update in eigenen Worker, Fortschritt via `pyqtSignal(int)` an Statusbar. |

### M-6 · Keine expliziten Transaktionen für Multi-Table-Operationen
| Aspekt | Detail |
|--------|--------|
| **Severity** | 🟡 Mittel |
| **Location** | `chormanager/data/database.py:209-225` (`transaction()` ist implementiert), aber Aufrufer nutzen es nicht konsistent. |
| **Erklärung** | `_reload_after_restore` (main_window.py:2454-2481) ruft eine Sequenz von Repo-Operationen ohne `with db.transaction():`. Wenn eine Operation mitten in der Sequenz fehlschlägt, ist die DB inkonsistent. |
| **Risiko** | Datenkorruption bei Backup-Restore oder bei Multi-Table-Imports. |
| **Fix** | Alle Repo-`update`/`delete`-Aufrufer, die mehrere Tabellen berühren, in `with db.transaction():` wickeln. Static-Check via `assert` in `Database.execute`. |

### M-7 · Mix aus `os.path` und `pathlib`
| Aspekt | Detail |
|--------|--------|
| **Severity** | 🟡 Mittel |
| **Location** | `chormanager/ui/views/choraufstellung_tab.py:34-41, 158, 173, 273, 294, 308, 334` benutzt `os.path`; fast alle anderen Module `pathlib.Path`. |
| **Risiko** | Code-Review-Friktion, doppelte Mental-Models, Pfad-Bugs bei Windows-Ports (falls je nötig). |
| **Fix** | `os.path` → `pathlib.Path` migrieren. Konsistenz schlägt Bevorzugung. |

### M-8 · Modal-Dialoge in `QApplication.processEvents`-Loops
| Aspekt | Detail |
|--------|--------|
| **Severity** | 🟡 Mittel |
| **Location** | `chormanager/ui/main_window.py:3009, 3048` |
| **Erklärung** | `QApplication.processEvents()` in Hot-Loops ist ein Anti-Pattern, das Event-Handler-Reentrance und Race-Conditions verursacht. |
| **Risiko** | Sporadische Hänger bei `_check_version`/`_do_update`. |
| **Fix** | Subprocess-Aufrufe in `QThread` verlagern, nicht im Main-Thread pollen. |

---

## 🗑️ Dead-Code Findings

| Datei | Symbol | Grund | Confidence |
|-------|--------|-------|:-:|
| `chormanager/app_logging.py:60` | `get_logger` | Wird nirgends importiert (Logger werden ad-hoc via `logging.getLogger` geholt). | 95 % |
| `chormanager/config.py:172` | `get_voice_group_choices` | Heißt intern `voice_group_choices`, aber Aufrufer benutzen `load_voice_groups()` direkt. | 90 % |
| `chormanager/config.py:182` | `get_field_by_name` | Keine Aufrufer im gesamten `chormanager/`-Tree. | 95 % |
| `chormanager/config.py:198` | `get_required_fields` | Keine Aufrufer; UI filtert manuell. | 95 % |
| `chormanager/backup/service.py:172` | `BackupService`-Klasse | Existiert parallel zu `chormanager/export/backup_service.py:21`. Welche wird benutzt? | 80 % |
| `chormanager/choraufstellung/qt_compat.py` | `exec_qt()`-Helper | PyQt5 wird in `requirements.txt` nicht mehr unterstützt, aber der `try/except`-Pfad existiert. | 70 % |
| `import_singers.py` (Projekt-Root) | Skript | Wird vermutlich durch `chormanager/tools/import_singers.py` ersetzt. | 60 % |

**Hinweis:** Die Repository-Methoden (`create`, `get_by_id`, …) hatten im AST-Scan refcount=0, was aber eine **False-Positive** des Skripts ist (Method-Calls werden als `Attribute`, nicht als `Name` gezählt). Diese Methoden sind in Gebrauch.

---

## 🛠️ Technology-Stack-Usage Assessment

### PyQt6 (Score 5/10)
- **Stärken:** Saubere Signal/Slot-Trennung (45 `pyqtSignal`/`pyqtSlot` Deklarationen). `pyqtSignal(Qt.UserRole)` für ID-Storage in Tabellen-Cells ist idiomatisch.
- **Schwächen:**
  - **15+ Export-Methoden** in `main_window.py`, die alle mit `subprocess.run` arbeiten, blockieren die UI (M-5).
  - **`os.path.exists` + `time.sleep`-Polling** in mindestens 3 Modulen (Subprocess-Status).
  - **PyQt5-Fallback** in `choraufstellung/qt_compat.py` — keine Notwendigkeit, da `requirements.txt` nur PyQt6 listet. Toter Code, der Verwirrung stiftet.
  - **Modal-Dialoge blockieren Tests** — aufwendiges Mocking via `patch.object(QMessageBox, "exec", ...)` in Phase 2-3 nötig.
  - **Zwei voneinander unabhängige QApplication-Starts** (`chormanager/__main__.py:55` und `chormanager/choraufstellung/main.py:2181`). Subprozess statt modularem Aufruf — schwere Test-Last.

### SQLite via `Database`-Wrapper (Score 6/10)
- **Stärken:** Klares `row_factory = sqlite3.Row`, `transaction()`-Context-Manager vorhanden, Foreign-Keys aktiviert.
- **Schwächen:**
  - **F-String-SQL** an 19 Stellen (M-3).
  - **`Database.execute` ist nicht thread-safe** — `Database` lebt im MainWindow-Scope, kein Connection-Pool. Mehrere Tabs teilen sich eine Connection.
  - **Migrations-Strategie unklar:** `create_tables()` legt fehlende Tabellen an, aber Schema-Änderungen (z. B. neue Spalte) werden nicht gehandhabt. Kein `PRAGMA user_version`.
  - **`os.replace` für Atomic-Writes** fehlt beim State-File (`config.py:38`).

### PyYAML (Score 6/10)
- **Stärken:** `yaml.safe_load` korrekt verwendet, `lru_cache` fehlt (Performance-Bug — wird bei jedem `load_voice_groups()` neu geparst).
- **Schwächen:** Kein Schema-Validation. `app.yaml`, `fields.yaml`, `voice_groups.yaml` sind stillschweigend required, kein Fallback bei `FileNotFoundError`.

### ReportLab (Score 4/10)
- **Stärken:** PDF-Generierung funktional in `chormanager/ui/main_window.py:1540-1607` und `chormanager/ui/dialogs.py:704-870`.
- **Schwächen:**
  - **`from reportlab.platypus import …`** wird in zwei Methoden dynamisch importiert — sollte Top-Level-Import sein.
  - **PDF-Templates inline**, keine Trennung zwischen Layout und Daten. Nicht testbar ohne `ReportLab`-Rendering.
  - **LibreOffice-Conversion** über `subprocess.run("libreoffice", "--convert-to", "pdf", …)` — blockiert Main-Thread (M-5).

### pytest + pytest-qt (Score 7/10)
- **Stärken:** 386 Tests grün, headless via `QT_QPA_PLATFORM=offscreen`. TDD-Disziplin sichtbar. Phase 1-6 legten 163 Tests ab.
- **Schwächen:**
  - **Coverage 42 %** — vor allem UI- und Subprozess-Pfade ungetestet.
  - **Keine Property-Based-Tests** (z. B. `hypothesis` für `compute_is_adult`).
  - **Keine Mutation-Tests** (z. B. `mutmut`/`cosmic-ray`) — der Phase-6-Bug wäre ohne ausdrücklichen Test nicht aufgefallen.
  - **In `tests/gui/`** sind nur 2 Dateien (Events, MainWindow-Smoke). Sollte komplett in `tests/unit/` migriert werden, da Headless.

---

## 🏗️ Refactoring Opportunities (Top 10)

| # | Opportunity | Impact | Aufwand | Priorität |
|:-:|-------------|:-:|:-:|:-:|
| **R-1** | `main_window.py` (3 104 LOC) aufteilen: Window-Lifecycle + Export-Controller + Update-Controller. | 🔴 Hoch | 2-3 Tage | **P0** |
| **R-2** | `choraufstellung/main.py` (2 180 LOC) aufteilen: Window + Undo-Stack + Optimizer-Bridge. | 🔴 Hoch | 2 Tage | **P0** |
| **R-3** | `dialogs.py` (1 824 LOC) aufteilen: Eine Dateie pro Dialog-Klasse (analog zu `views/`). | 🟠 Mittel | 1 Tag | **P1** |
| **R-4** | F-String-SQL durch `QueryBuilder` ersetzen (M-3). | 🟠 Mittel-Hoch | 1 Tag | **P1** |
| **R-5** | Alle `except:` durch konkrete Exceptions ersetzen (M-4). | 🟡 Mittel | 0,5 Tag | **P1** |
| **R-6** | Subprocess-Calls in `QThread`/`QProcess` migrieren (M-5, M-8). | 🟠 Mittel | 1-2 Tage | **P1** |
| **R-7** | `lru_cache` auf `load_voice_groups()`, `load_fields()`, `load_app_config()` — die werden bei jeder UI-Initialisierung geparst. | 🟡 Mittel | 0,1 Tag | **P2** |
| **R-8** | `os.path` → `pathlib.Path` in `choraufstellung_tab.py` (M-7). | 🟢 Niedrig | 0,2 Tag | **P3** |
| **R-9** | Dead Code entfernen (siehe Tabelle oben). | 🟢 Niedrig | 0,1 Tag | **P3** |
| **R-10** | `lru_cache` auf `Settings.get_config` + Schema-Validation mit `pydantic` (oder zumindest `voluptuous`) für YAML-Configs. | 🟡 Mittel | 0,5 Tag | **P2** |

---

## ⚡ Quick Wins (< 30 min)

| # | Quick Win | Geschätzter Aufwand |
|:-:|----------|:-:|
| **Q-1** | `lru_cache` auf `load_voice_groups()`, `load_fields()`, `load_app_config()` setzen. | 5 min |
| **Q-2** | Dead Code entfernen: `get_logger`, `get_field_by_name`, `get_required_fields`, `get_voice_group_choices`. | 5 min |
| **Q-3** | `requirements.txt` bereinigen: PyQt5-Verweise löschen, da nicht mehr genutzt. | 5 min |
| **Q-4** | `coverage-badge` ins README einfügen (Phase 1-6: 42 %). | 5 min |
| **Q-5** | `pytest --cov=chormanager --cov-fail-under=50` als Pre-Commit-Hook (Quality-Gate). | 10 min |
| **Q-6** | `import_singers.py` (Projekt-Root) löschen, wenn `chormanager/tools/import_singers.py` aktiv ist. | 2 min |
| **Q-7** | `docs/reports/`-Verzeichnis anlegen und diese Review committen. | 2 min |
| **Q-8** | `pre-commit`-Config mit `ruff` (Linting), `black` (Format), `mypy --strict` (Typing) initialisieren. | 15 min |
| **Q-9** | `.editorconfig` hinzufügen (UTF-8, LF, 4-Space-Indent). | 5 min |
| **Q-10** | `CHANGELOG.md` anlegen + Phase-1-6-Commits eintragen. | 15 min |

---

## 🏁 Final Verdict

### Production-Ready?
**🟡 Bedingt.** Für eine Single-User-Desktop-App im Verein ist der Code **nutzbar**, aber **nicht** für eine Mehr-Benutzer- oder Multi-Instance-Server-Umgebung. Die fehlenden Transaktionen und die `except:`-Klauseln würden in einem Mehrmandanten-Szenario zu Datenverlust führen.

### Biggest Risks (Reihenfolge der Wichtigkeit)
1. **Datenkorruption bei Backup-Restore** (M-6) — kein Transaktionsschutz, ein Crash mitten in der Restore-Sequenz macht die DB unbrauchbar.
2. **UI-Hänger** durch blockierende Subprocess-Aufrufe (M-5, M-8) — Benutzer klickt "Backup jetzt", UI hängt 30 s ohne Feedback.
3. **SQL-Injection-Risiko** durch F-String-Pattern (M-3) — heute latent, morgen akut.
4. **Unwartbarkeit** durch God-Classes (M-1, M-2) — Phase 6 hat gezeigt, dass UI-Bugs sich in 3 000+ LOC verstecken.

### Must-Fix Before Release
- [x] Tests grün (✅ 386 passed)
- [ ] M-4: Alle `except:` ersetzen
- [ ] M-3: F-String-SQL absichern
- [ ] Q-1: `lru_cache` auf YAML-Loads
- [ ] R-1 oder R-2: Mindestens **eine** God-Class aufteilen

### Should-Fix Before New Features
- [ ] M-5/M-8: Subprocess-Async
- [ ] R-3: `dialogs.py` splitten
- [ ] M-6: Transaktionen für Multi-Table-Operationen
- [ ] Coverage auf 60 % treiben (kritische Pfade: `main_window.py`, `choraufstellung/main.py`)

### Nice-to-Have
- [ ] Property-Based-Tests mit `hypothesis`
- [ ] Mutation-Tests mit `mutmut`
- [ ] CI-Pipeline mit `pytest`, `ruff`, `mypy`, `bandit`, `coverage`
- [ ] Internationalisierung (Strings sind aktuell hardcoded deutsch)

---

## 📎 Anhang

### A. Test-Stand
```
$ python -m pytest tests/ -q
386 passed, 0 failed
```

### B. Coverage (vor / nach Phasen)
```
Start (vor Phase 1):    ~28 %
Nach Phase 1-6:         ~42 %
Delta:                  +14 pp
P0-Module (≥ 90 %):     ExportService, BackupService, PortabilityService, EventAvailabilityDialog
P1-Module (≥ 50 %):     dialogs.py (69 %), besetzung_tab (56 %), projects_tab (78 %)
```

### C. LOC-Verteilung (Top 10)
| Datei | LOC |
|-------|---:|
| `chormanager/ui/main_window.py` | 3 104 |
| `chormanager/choraufstellung/main.py` | 2 180 |
| `chormanager/ui/dialogs.py` | 1 824 |
| `chormanager/domain/repository.py` | 655 |
| `chormanager/choraufstellung/optimizer_rules.py` | 407 |
| `chormanager/choraufstellung/chormanager_db.py` | 327 |
| `chormanager/domain/models.py` | 324 |
| `chormanager/core/response_matrix.py` | 276 |
| `chormanager/choraufstellung/pdf_export.py` | 257 |
| `chormanager/data/database.py` | 242 |

**Gesamt:** 13 129 LOC Python in `chormanager/`.

### D. Methodik
- Statische Analyse via `grep`, `wc -l`, AST-Walk (Dead-Code-Detection).
- Phasen-1-6-Tests als funktionale Verifikation.
- Keine Runtime-Profiling- oder Security-Audit-Tools (`bandit`, `semgrep`) eingesetzt — diese wären der nächste Schritt.
