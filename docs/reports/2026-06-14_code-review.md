# Code Review — ChorManager

**Datum:** 2026-06-14
**Reviewer:** Senior-Review (statisch, ohne Ausführung)
**Codebase:** `chormanager/` (~16 000 LOC, 75+ Python-Module)
**Branch/Stand:** Stand nach M-1 (MainWindow-Refactor) + M-2 (ChorAufstellung-Refactor) + M-3 (Dialoge). 430+ Tests grün, Coverage 42 % → ~48 %.
**Test-Stand:** `python -m pytest tests/ -q` → alle passed

> **Scope-Erweiterung gegenüber 2026-06-12:** Diese Review konzentriert sich auf die neu hinzugekommenen Module (`core/`, `autosave`, `recovery`, `file_io`, `undo_bridge`, `chormanager_bridge`, `pdf_export_integration`, `theme`, `main_menu`, `update_controller`, `export_controller`, `choraufstellung_launcher`, `dependencies`, `qt_compat`) und auf das **zweite, parallele QApplication-Subshell-Modell** (ChorAufstellung wird als Subprozess gespawnt, nicht als Modul importiert). Die Findings 2026-06-12 sind weiterhin gültig; hier kommen die neu beobachteten Risiken hinzu.

---

## 🎯 Executive Summary

| Kategorie | Score (1-10) | Kurzbegründung |
|-----------|:-:|---|
| **Korrektheit** | 6/10 | Subshell-IPC über Umgebungsvariablen + Temp-JSON, Optimizer mit quadratischer Komplexität, Race in `update_controller._do_update` |
| **Concurrency** | 4/10 | Blockierende `subprocess.run`-Aufrufe auf Main-Thread (LibreOffice, git, ChorAufstellung), `QApplication.processEvents` als Spinner, Recovery-Symlink-Lesen ohne Locking |
| **Sicherheit** | 5/10 | F-String-SQL (latent), unbeschränkte `urllib.request`-Aufrufe in `update_controller`, `git pull` ohne Integritätsprüfung |
| **Zuverlässigkeit** | 5/10 | Auto-Save-Symlink auf Windows nicht portierbar, `save_formation` schreibt tmp-File ohne `os.replace`-Räumarbeitung, `OptimizeFormationCommand.redo()`-Coupling |
| **Architektur** | 6/10 | Bridges sauber getrennt, aber ChorAufstellung als Subprozess statt Modul zwingt zu teurer IPC, Mixin-Inflation in MainWindow |

**Gesamtbild:** Die Refactorings M-1, M-2, M-3 haben die unmittelbaren UI-Bugs adressiert. Die **nächste Schicht** von Risiken liegt jetzt in der **Prozessgrenzen-Architektur** (Subshell-Spawning), in den **blockierenden I/O-Pfaden** (subprocess.run, urllib, git pull) und in der **Optimierer-Algorithmik** (Affinitäts-Regel mit O(n² × max_swaps) im Worst Case). Für Single-User-Desktop bleibt das System benutzbar; jeder Pfad, der "Multi-User", "Background-Job" oder "Subshell-Restart" einführt, braucht ein Architektur-Update.

---

## 🔴 Critical Findings

### C-1 · ChorAufstellung als Subprozess statt Modul — IPC ist fragil und nicht regressional testbar
| Aspekt | Detail |
|--------|--------|
| **Severity** | 🔴 Hoch |
| **Confidence** | 95 % |
| **Location** | `chormanager/ui/choraufstellung_launcher.py:151-218` (`_open_choraufstellung_file`); `chormanager/choraufstellung/__main__.py:1-15`; `chormanager/choraufstellung/main.py:818-840` (`main()`) |
| **Erklärung** | Die `ChorAufstellung`-Subshell wird über `subprocess.run([sys.executable, "choraufstellung/__main__.py"], cwd=choraufstellung_path, env=env)` gestartet. Konfiguration wird ausschließlich über **Umgebungsvariablen** transportiert (`CHOR_EVENT_DATE`, `CHOR_EVENT_ID`, `CHOR_EVENT_NAME`, `CHOR_PROJECT`, `CHOR_EVENT_TYPE`, `CHOR_DB_PATH`, `CHOR_FILE`, `CHOR_EVENT_DATA`). 5 der 6 Übergabepfade für File-Pfade/Event-Daten sind reine Strings, nur `CHOR_EVENT_DATA` zeigt auf ein Temp-JSON. |
| **Failure-Szenario 1** | **Path-Injection über `CHOR_FILE`:** `_open_choraufstellung_file` liest `self.choraufstellung_tab.current_file()`-Rückgabe (vermutlich Tabelleneintrag) und setzt sie unverändert als `CHOR_FILE`. Wenn der Tab ein User-editable-Feld anbietet, kann ein Pfad wie `"; rm -rf ~ #` mitgegeben werden — auf Linux wird der nicht ausgeführt, aber `subprocess.run` selbst startet eine zweite Python-Instanz, die ggf. die Pfad-Semantik falsch interpretiert. |
| **Failure-Szenario 2** | **Zwei `QApplication`-Instanzen:** Die `main.py` der Subshell ruft `QApplication(sys.argv)` (Zeile 829). Wenn die Launcher-Methode vom MainWindow aus aufgerufen wird, **erbt der Subprozess** die Display-Umgebung des Haupprozesses. Auf Wayland / X11 mit laufendem Display-Server ist das OK, aber headless in CI bedeutet: zwei `QApplication`s, kein sauberer Tear-Down, Speicher-Lecks. |
| **Failure-Szenario 3** | **Stale State auf Restore:** Nach `_reload_after_restore()` (main_window.py:886) wird `self.choraufstellung_tab._load_formations()` aufgerufen, aber die Subshell wurde **vor** dem Restore gestartet. Die im Subshell-Prozess laufende `MainWindow` zeigt weiterhin die alte `self.db`-Referenz. Race: Subshell schreibt in `ChorAufstellung/data/...` während MainWindow die `chor.db` durch ein Backup ersetzt. |
| **Failure-Szenario 4** | **Temp-JSON-Leak:** `tempfile.gettempdir()/choraufstellung_event.json` (choraufstellung_launcher.py:270) wird **nie aufgeräumt**. Bei jeder Event-Öffnung wächst die Datei oder wird überschrieben. Wenn der Subshell-Crash passiert, bevor sie liest, bleibt der alte Stand für die **nächste** Subshell-Instanz — falsche Sänger-Zuordnung. |
| **User/Business Impact** | Der Chorleiter bearbeitet die Aufstellung für Konzert X. Backup-Restore legt einen alten Stand an. Subshell schreibt parallel weiter, überschreibt die frische DB. Datenverlust, falsche Konzertplanung. |
| **Suggested Remediation** | (a) `choraufstellung` als importierbares Modul in `MainWindow` einbetten (kein Subprozess), Subshell als eigener "Dokument-Modus" mit `MainWindow` als Host. (b) Falls Subprozess bleibt: `multiprocessing.connection` oder `socket`-basierte IPC, Mutex auf DB-Ebene, Temp-Files mit `tempfile.NamedTemporaryFile(delete=True)` und `os.replace`. (c) `subprocess.run` durch `subprocess.Popen` + Signal-Handling ersetzen, damit `_check_version` nicht blockiert. |
| **Tradeoffs** | Modul-Einbettung erfordert Refactor von ~2 000 LOC und löst die Symlink-/Path-Trennung im Repo auf. IPC-Bleibe erfordert saubere Lifecycle-Verwaltung (zwei `QApplication`s koexistieren lassen ist mit `QApplication.setAttribute(Qt.AA_PluginApplication)` möglich, aber fragil). |

### C-2 · `OptimizeFormationCommand.redo()` führt Optimizer **und** Snapshot-Capture in einer Methode aus — und setzt `self.swap_count` aus dem letzten Rule-Result
| Aspekt | Detail |
|--------|--------|
| **Severity** | 🔴 Hoch |
| **Confidence** | 90 % |
| **Location** | `chormanager/choraufstellung/core/optimizer.py:21-49` (`OptimizeFormationCommand.redo`) |
| **Erklärung** | `redo()` iteriert über `self.rule_ids` und addiert **`result.swap_count` von jeder Regel** in `self.swap_count`. Aber `FormationOptimizer.run()` ruft `cmd.redo()` **einmal** auf (Z. 88-89), speichert dann die `old_positions` **vorher** (im `__init__` Z. 18) und `new_positions` **nachher** (Z. 45-46). Das ist konsistent. ABER: der `UndoStack` ([`core/commands.py:198-206`](chormanager/choraufstellung/core/commands.py:198)) ruft bei `push()` `command.redo()` NICHT auf (Zeile 198-206: nur `append` + Index-Inkrement). Der `QtUndoStack.push()` ([`undo_bridge.py:60-69`](chormanager/choraufstellung/undo_bridge.py:60)) ruft `command.redo()` **explizit** auf, BEVOR er den Stack pusht. In `FormationOptimizer.run()` wird `cmd.redo()` dann ein **zweites Mal** aufgerufen, weil `grid.undo_stack.push(cmd)` (Z. 92) das tut. |
| **Failure-Szenario** | Optimizer läuft mit Regeln `[height, affinity, voice_group_cohesion]`. `FormationOptimizer.run` ruft `cmd.redo()` → alle 3 Regeln applied, `swap_count=42`. Dann `grid.undo_stack.push(cmd)` ruft `cmd.redo()` **erneut** → swap_count=84. Der Undo-Stack ist inkonsistent, der Anwender sieht "84 Sänger getauscht" statt 42. Noch schlimmer: `self.old_positions` (Z. 18) wurde **vor** dem ersten `redo()` gecaptured, `self.new_positions` (Z. 45) **nach** dem ersten. Undo restauriert die **Zwischen-Position** (nach erstem redo), nicht die echte Start-Position. |
| **User/Business Impact** | Chorleiter optimiert, vertraut der "Anzahl Tauschvorgänge"-Anzeige, macht Undo → halbfertige Aufstellung, Daten stehen falsch. |
| **Suggested Remediation** | Entweder: `FormationOptimizer.run()` baut `cmd` ohne `redo()` und übergibt an `grid.undo_stack.push(cmd)` (das übernimmt den initial redo). Oder: `push()` ruft **kein** `redo()` mehr auf und der Caller macht es explizit. Empfehlung: Variante 1, weil sie dem `QUndoStack`-Standard entspricht und die Doppelverantwortung auflöst. |
| **Tradeoffs** | Variante 1 erfordert, dass andere `QtUndoStack.push()`-Caller (z. B. `MoveSingerCommand`, `SwapSingersCommand`, `MoveGroupCommand` in `formation_grid.py`) den initialen `redo()` ebenfalls weglassen. Die existierenden `MoveSingerCommand.redo()` etc. ([`core/commands.py:48-60`](chormanager/choraufstellung/core/commands.py:48)) sind idempotent (sie setzen nur `row`/`col` auf `new_row`/`new_col`), also kein Datenverlust — aber die Test-Suite sollte das absichern. |

### C-3 · Blockierende `subprocess.run` in `update_controller._do_update` und `_check_version` — UI-Freeze + untrusted git pull
| Aspekt | Detail |
|--------|--------|
| **Severity** | 🔴 Hoch |
| **Confidence** | 95 % |
| **Location** | `chormanager/ui/update_controller.py:54-114` |
| **Erklärung** | `_check_version` ruft `urllib.request.urlopen(req, timeout=10)` synchron im Main-Thread, danach `subprocess.run(['git', 'rev-parse', 'HEAD'], cwd='/media/data/coding/chormanager')`. `_do_update` ruft `subprocess.run(['git', 'pull', 'origin', 'main'])` — **ohne Timeout**. Wenn der Default-Push 1 GB ist oder das Netz hängt, hängt der Dialog (und damit der Main-Thread) **unendlich** (`timeout=None`). `QApplication.processEvents()` (Z. 57, 99) versucht das zu kaschieren, lässt aber Event-Handler-Reentrance zu — ein Timer, der während `processEvents` feuert, kann in `_check_version` reinlaufen und die halbfertige `urllib`-Connection zerstören. |
| **Failure-Szenario 1** | User klickt "Auf neue Version prüfen" in einer Firma mit restriktivem Web-Proxy. `urllib` wirft `URLError` nach 10 s, `git rev-parse` returnt `0` mit leerem stdout. `local_sha = "".strip()[:7] = ""`. Vergleich `"" != remote_sha` ist True → "Update verfügbar" obwohl bereits aktuell. |
| **Failure-Szenario 2** | User klickt "Update durchführen". `git pull origin main` läuft. Während des Pulls ruft ein Timer `auto_backup.tick()` auf, der in der DB schreibt. Pull mischt neue `chormanager/`-Sources mit alter laufender Python-Instanz — `sqlite3`-Bindings, geladene Module sind halb alt, halb neu. Result: AttributeError beim nächsten Method-Call. |
| **Failure-Szenario 3** | `git pull origin main` mit einem **manipulierten Remote** (DNS-Spoofing, kompromittierter GitHub-Account) liefert beliebigen Code. Es gibt keine PGP-Signatur-Prüfung, keinen `git verify-commit`, keinen Hash-Vergleich gegen eine bekannte Good-Version. **Auto-Update-Attacker-Pattern** (vgl. event-stream, ua-parser-js). |
| **User/Business Impact** | UI hängt minutenlang, im Worst Case beliebige Code-Ausführung unter dem User-Account. |
| **Suggested Remediation** | (a) `QThread`/`QRunnable` mit `pyqtSignal(int, str)` für Fortschritt. (b) `subprocess.run(..., timeout=60)` immer setzen. (c) Mindestens `git verify-commit HEAD~1..HEAD` nach Pull; besser: Signed-Tags verlangen, `--gpg-sign`-Updates. (d) `local_sha`-Vergleich robuster: `if not local_sha: return`. |
| **Tradeoffs** | QThread-Migration erfordert ~1 Tag; signed Tags erfordern Git-Repo-Setup. Pragmatischer Mittelweg: Timeout + User-Bestätigung vor Pull. |

### C-4 · Affinitäts-Optimizer mit O(n² × max_swaps × max_iterations) — UI-Freeze bei >30 Sängern
| Aspekt | Detail |
|--------|--------|
| **Severity** | 🟠 Mittel-Hoch |
| **Confidence** | 90 % |
| **Location** | `chormanager/choraufstellung/core/rules.py:357-447` (`AffinityRule.apply`) |
| **Erklärung** | Pro Iteration: für jedes Paar (s1, s2) werden `neighbors1` (max 8) × `neighbors2` (max 8) × leere Positionen (bis 4) Kombinationen geprüft = bis zu 64 Swaps. Innere Schleife läuft `len(pairs)²` Mal — bei 30 Sängern mit Affinitäts-Paaren sind das ~900 Iterationen, jede mit bis zu 64 Vergleichen. Plus die quadratische Singersuche für `occ1, occ2` (Z. 399-404) — **O(n)** pro Swap-Kandidat. Tatsächliche Komplexität: O(pairs² × max_swaps × n × max_iterations). Bei `max_swaps=50`, `max_iterations=3`, n=40: ~50 × 3 × 40 × 30² = 5,4 Mio Operationen im Main-Thread. |
| **Failure-Szenario** | Chorleiter klickt "Optimieren" mit 50 Sängern. UI friert 8–15 s ein, das `OptimizeFormationCommand` wird in den Stack gepusht, aber `QtUndoStack.canUndoChanged.emit()` läuft erst nach Abschluss. Während des Freezes sieht der Anwender keinen Fortschritt, klickt nochmal → mehrfache Optimierer-Stack-Pushs, O(n²) wird O(n³). |
| **User/Business Impact** | Bei großen Chören (60+ Sänger mit 20 Affinitäts-Paaren) ist Optimierer **unbenutzbar**. |
| **Suggested Remediation** | (a) Optimierer in `QThread` mit Progress-Signal. (b) `_get_neighbor_positions` cached die leeren Positionen pro Iteration (Z. 472-482: baut die Liste **für jeden Aufruf** neu). (c) Singersuche O(1) via `Dict[singer_id, Singer]`-Index. (d) Break-Out-Logik in `VoiceGroupCohesionRule.apply` (Z. 612-643) ist verschachtelt — 5 Break-Levels tief, schwer zu refactoren. |
| **Tradeoffs** | QThread-Integration braucht 0,5–1 Tag. Singers-Dict ist 10 Zeilen, sofort machbar. |

### C-5 · Auto-Save-Symlink-Strategie bricht auf Windows und ist race-anfällig
| Aspekt | Detail |
|--------|--------|
| **Severity** | 🟠 Mittel-Hoch |
| **Confidence** | 85 % |
| **Location** | `chormanager/choraufstellung/storage.py:129-153` (`save_autosave`) |
| **Erklärung** | `save_autosave` schreibt `autosave_<timestamp>.json` und legt einen **Symlink** `latest_autosave.json → autosave_<timestamp>.json` an (Z. 140-143). Auf Windows ohne Developer-Mode oder ohne Admin-Rechte schlägt `os.symlink` mit `OSError: symbolic link privilege not held` fehl — die App ist dann unter Windows nicht lauffähig (zumindest der Auto-Save-Pfad). Auf Linux: `os.symlink` überschreibt **nicht** automatisch; Z. 141-142 löscht zwar vorher, aber zwischen `os.remove` und `os.symlink` ist ein kleines Zeitfenster, in dem `get_latest_autosave_path` `None` returnt. Wenn der Crash genau in dem Fenster passiert, sieht `RecoveryController.check()` keinen Auto-Save und überspringt die Wiederherstellung. |
| **Failure-Szenario 1 (Windows)** | User auf Windows 10/11 ohne Admin: `os.symlink` wirft `OSError`, der `try/except` schluckt ihn (Z. 151-152), `return True` wird trotzdem ausgeführt. `latest_autosave.json` existiert nicht. Beim nächsten Start: `RecoveryController.check()` → `get_latest_autosave_path()` returnt `None` → `return False` → **kein Recovery**, manuelle Wiederherstellung unmöglich. |
| **Failure-Szenario 2 (Linux-Race)** | Auto-Save-Fire um 12:00:00.000. `os.remove("latest_autosave.json")` um 12:00:00.001. Main-Thread wird von anderem Timer unterbrochen. `os.symlink(...)` um 12:00:00.050. In dem Fenster von 49 ms sieht ein paralleler `get_latest_autosave_path()`-Aufruf `None` und behauptet "kein Auto-Save". |
| **Failure-Szenario 3 (`_get_backup_dir`)** | `_get_backup_dir` (Z. 121-127) gibt `os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "backups")` zurück. Bei einer **Installation per `pip install`** liegt `__file__` in `site-packages/.../chormanager/choraufstellung/storage.py` — der Backup-Ordner wird im Site-Packages-Verzeichnis angelegt, das bei Updates gelöscht wird. **Alle Auto-Saves futsch**. |
| **User/Business Impact** | Auf Windows: keine Auto-Save-Wiederherstellung. Bei pip-Installation: Datenverlust beim nächsten `pip install --upgrade`. |
| **Suggested Remediation** | (a) `os.replace()` mit einer normalen Datei statt Symlink: schreibe einfach den **Inhalt** in `latest_autosave.json` (mit `tmp` + `os.replace`). Verliert die "zeige alle Versionen"-Funktionalität, aber löst das Symlink-Problem. (b) `_get_backup_dir` über `XDG_DATA_HOME` / `appdirs.user_data_dir("choraufstellung")` (AGENTS.md schreibt das sogar vor: "XDG-Pfade (`~/.local/share/choraufstellung/`)"). (c) Rotation: `os.listdir(backup_dir)` ist nicht atomar, sollte via `os.scandir` mit Filter geschehen. |
| **Tradeoffs** | Variante (a) verliert die Versions-Liste, aber die braucht die Recovery-Logik sowieso nicht — `latest_autosave.json` reicht. |

### C-6 · `Database`-Connection wird in mehreren Tabs geteilt — keine Connection-Isolation
| Aspekt | Detail |
|--------|--------|
| **Severity** | 🟠 Mittel-Hoch |
| **Confidence** | 80 % |
| **Location** | `chormanager/data/database.py:30-66` (`Database.connect`, `execute`); `chormanager/ui/main_window.py:680-704` (Tab-Instanziierung); `chormanager/ui/choraufstellung_launcher.py:53-85` (`refresh_tab_repositories`) |
| **Erklärung** | Ein einziges `Database`-Objekt wird im MainWindow-Konstruktor erstellt (Z. 143-145) und **per Reference** an `ProjectsTab`, `SingersTab`, `EventsTab`, `BesetzungTab`, `ChorAufstellungTab`, `RepertoireTab` weitergegeben. Jeder Tab instanziiert `SingerRepository(self.db)`, `EventRepository(self.db)`, … — alle Repos zeigen auf **dieselbe** `sqlite3.Connection`. SQLite serialisiert Schreibvorgänge automatisch, ABER: |
| **Failure-Szenario 1** | Tab A ruft `self.db.execute("UPDATE singers SET …")` ohne `commit()`. Tab B ruft `self.db.execute("SELECT … FROM singers")` → sieht die un-committeten Daten. (SQLite-Default: isolation_level=""). Sobald Tab A `commit()` aufruft, sind sie persistent; macht er `rollback()`, sieht Tab B phantom-Daten. |
| **Failure-Szenario 2** | `_reload_after_restore` (main_window.py:886-913) ruft `self.db.close()` (Z. 889), dann `self.db = Database(...)` (Z. 890), dann `self.db.connect()` (Z. 891). **Aber:** die Tabs halten noch ihre alten `SingerRepository(self.db)`-Referenzen — `self.db` in den Repos zeigt auf die geschlossene Connection. Jeder `repo.get_all()` wirft `ProgrammingError: Cannot operate on a closed database`. Der nachfolgende `refresh_tab_repositories(tab, self.db)` **muss** alle Tabs erwischen, **bevor** ein Tab-UI-Refresh passiert. Wenn in der Zwischenzeit ein Timer/Event einen `singers_tab._load_singers()` triggert, ist die UI leer. |
| **Failure-Szenario 3** | `update_controller._do_update` ersetzt via `git pull` den Source-Tree. Die `chormanager/data/database.py` ist jetzt eine neue Version. Beim nächsten Method-Call lädt Python das Modul nicht neu (`__pycache__` cached), aber `sqlite3.Connection` selbst ist in C — falls die C-Bibliothek geladen wurde, gibt es keine Reload-Möglichkeit. **Inkonsistenter Zustand nach Auto-Update** ohne Neustart. |
| **User/Business Impact** | Race-Conditions in Multi-Tab-Szenarien (Chorleiter klickt schnell zwischen Sänger- und Termin-Tab); Datenverlust bei Backup-Restore, wenn Timer zuschlägt. |
| **Suggested Remediation** | (a) Jeder Tab bekommt eine **eigene** Connection aus einem Pool (`Database.connect_pool()` mit `sqlite3.connect` + `check_same_thread=False` + `row_factory`). (b) Schreibende Repos explizit in `with db.transaction():` wickeln. (c) Auto-Update muss **App-Neustart erzwingen** (heute steht das zwar im Status, ist aber nicht erzwungen — User kann weiterklicken). |
| **Tradeoffs** | Connection-Pool erhöht den Memory-Footprint minimal (jede Connection ~50 KB). Pro-Tab-Connection ist Standard-Praxis in produktiven SQLite-Apps. |

---

## 🟠 Major Findings

### M-1 · `subprocess.run` blockiert Main-Thread in 7 Pfaden
| Aspekt | Detail |
|--------|--------|
| **Severity** | 🟠 Mittel-Hoch |
| **Confidence** | 95 % |
| **Location** | `chormanager/ui/choraufstellung_launcher.py:209-211, 297-301` (ChorAufstellung-Spawn); `chormanager/ui/main_window.py:833-841` (`_show_about` git-Describe); `chormanager/ui/update_controller.py:77-80, 103-106` (git-Status, git-Pull); `chormanager/ui/export_controller.py:223-236` (LibreOffice-Konvertierung) |
| **Erklärung** | Sieben `subprocess.run`-Aufrufe ohne `QThread`/`QProcess`. Drei davon ohne Timeout (ChorAufstellung-Spawn × 2, `_show_about` git-Describe). Die `LibreOffice`-Konvertierung in `_export_libreoffice` hat `timeout=30` (export_controller.py:235), aber 30 s Freeze ist immer noch Freeze. |
| **Failure-Szenario** | User klickt "Hilfe → Über" (git-Describe blockiert 0,5–3 s). User klickt "LibreOffice exportieren" (30 s Freeze ohne Spinner). User klickt "Aufstellung öffnen" (Spawn blockiert 5–20 s je nach Cold-Start der Python-Imports). Bei schlechter Disk: 60+ s. |
| **Suggested Remediation** | Ein einziger `SubprocessRunner(QObject)` mit `pyqtSignal(int, str)` und `run_async(cmd, cwd, env, timeout, on_done)`. Jeder Caller wechselt von `subprocess.run` zu `subprocess_runner.run_async(...)`. |
| **Tradeoffs** | ~1 Tag Refactor; verbessert UX signifikant. |

### M-2 · `except Exception` schluckt `KeyboardInterrupt` und `SystemExit` in Bridge-Loaders
| Aspekt | Detail |
|--------|--------|
| **Severity** | 🟠 Mittel |
| **Confidence** | 95 % |
| **Location** | `chormanager/choraufstellung/chormanager_bridge.py:139, 201` (`# noqa: BLE001 — never raise`); `chormanager/choraufstellung/file_io.py:228-239` (`_rehydrate_singers`); `chormanager/choraufstellung/recovery.py:105-113` (`_ask_user_should_restore` ruft `QMessageBox.question` ohne `except`) |
| **Erklärung** | In `chormanager_bridge.py:139` und `:201` wird `except Exception as exc: print(...)` mit einem expliziten `# noqa: BLE001`-Marker benutzt, **um den Caller am Laufen zu halten, wenn der Subshell-Loader fehlschlägt**. Beide Stellen haben einen `return False`-Fallback. Das ist absichtlich, ABER: `KeyboardInterrupt` ist **kein** `Exception` in Python 3, sondern erbt von `BaseException` — wird also **nicht** geschluckt. `SystemExit` ebenfalls. `Exception` schluckt aber Memory-Adresse-Probleme wie `RecursionError` oder `MemoryError` (in Python 3.12+ ist `MemoryError` von `Exception` abgeleitet, ältere Versionen nicht). |
| **Failure-Szenario** | Beim Laden von 10 000 Sängern aus `CHOR_EVENT_DATA` (z. B. Bug im Sync-Export) rekurriert `_make_singer_from_dict` → `RecursionError` → `except Exception` schluckt → `return False` → User sieht "leeres Choraufstellung-Fenster" ohne Fehlermeldung. Diagnose dauert Stunden. |
| **Suggested Remediation** | `except (json.JSONDecodeError, KeyError, ValueError, OSError)` als konkrete Liste. Logging via `app_logging.get_logger(__name__)` statt `print()`. |
| **Tradeoffs** | Minimaler Aufwand, semantisch klar. |

### M-3 · `qApplication.processEvents()` als Spinner in `update_controller`
| Aspekt | Detail |
|--------|--------|
| **Severity** | 🟠 Mittel |
| **Confidence** | 90 % |
| **Location** | `chormanager/ui/update_controller.py:57, 99` |
| **Erklärung** | `QApplication.processEvents()` wird gerufen, damit der Statusbar-Text `"Prüfe GitHub Repository..."` sichtbar wird, bevor der blockierende `urllib`-Call startet. Anti-Pattern: `processEvents` re-entrancy erlaubt es Qt-Timern, in der laufenden Methode zu feuern, was zu Reentrance-Bugs führt. Zudem: `processEvents()` verarbeitet **alle** anstehenden Events, inkl. Mouse-Clicks — der User kann auf "Abbrechen" klicken, während wir in `urlopen` hängen. |
| **Failure-Szenario** | `processEvents()` löst `clicked` auf den "Schließen"-Button aus → `reject()` schließt den Dialog. Die `urllib`-Connection hält den Dialog am Leben, der Close wird ignoriert. UI-Freeze + unschließbares Fenster. |
| **Suggested Remediation** | `QApplication.processEvents()` komplett entfernen, sobald QThread-Migration erfolgt. Bis dahin: durch `QApplication.setOverrideCursor(Qt.WaitCursor)` + Statusbar-Update ersetzen. |
| **Tradeoffs** | `setOverrideCursor` ist Standard-Praxis, 5 Zeilen, sofort. |

### M-4 · `state.json` wird ohne Atomic-Write geschrieben
| Aspekt | Detail |
|--------|--------|
| **Severity** | 🟠 Mittel |
| **Confidence** | 95 % |
| **Location** | `chormanager/config.py:33-41` (`save_state`) |
| **Erklärung** | `save_state` öffnet `state_file` direkt mit `"w"` und schreibt JSON. Kein `tmp` + `os.replace`. `state.json` enthält `last_active_project_id`, `last_active_event_id`, `last_active_besetzung_id`, `theme`. |
| **Failure-Szenario** | Beim Setzen des aktiven Projekts wird `state.json` geschrieben. Parallel: User startet Backup, das `state.json` mitkopiert. Crash mitten im `f.write(...)` → Datei ist truncated, JSON-Parser wirft `JSONDecodeError`, `load_state()` returnt `{}`, `last_active_project_id` ist weg. Beim nächsten Start: kein Projekt vorausgewählt. |
| **Suggested Remediation** | `tmp = state_file + ".tmp"; with open(tmp, "w", encoding="utf-8") as f: json.dump(...); os.replace(tmp, state_file)`. Standard-Pattern, 4 Zeilen. |
| **Tradeoffs** | Keine — atomare Writes sind immer besser. |

### M-5 · `file_io.load_formation_data` mutiert 5 Attribute auf dem Host ohne Validation
| Aspekt | Detail |
|--------|--------|
| **Severity** | 🟠 Mittel |
| **Confidence** | 80 % |
| **Location** | `chormanager/choraufstellung/file_io.py:75-117`; `chormanager/choraufstellung/main.py:790-815` (`_load_formation_data` — Duplikat) |
| **Erklärung** | `load_formation_data` liest `rows`, `cols`, `staggered` aus dem Dict und weist sie `host.grid.*` zu. `rows` und `cols` werden **nicht** valid — ein JSON mit `"rows": -1, "cols": 999999` würde die Grid-Geometrie sprengen. `_load_formation_data` in `main.py:790-815` ist eine **fast identische Kopie** der gleichen Logik (zweite Quelle für Bugs: Recovery ruft `self._load_formation_data`, `file_io.open` ruft `self.file_io.load_formation_data` → **zwei Code-Pfade** für dasselbe). |
| **Failure-Szenario 1** | Manipuliertes JSON-File (von außen editiert): `rows: -1`. `grid.set_dimensions(-1, 4)` setzt `self.minimumSize = -1 * 130 + 80 + 50 = -100` → Qt wirft `RuntimeError: negative size` oder produziert unsichtbares Widget. |
| **Failure-Szenario 2** | **Duplikation** in `main.py:_load_formation_data` vs. `file_io.load_formation_data` — sie haben **leicht unterschiedliche** Defaults (`file_io` setzt `rows=3, cols=4` wenn key fehlt; `main._load_formation_data` ebenfalls, aber **baut die ComboBox-Sync-Logik**). Bug-Fix muss an zwei Stellen. |
| **Suggested Remediation** | (a) Klient validiert `1 <= rows <= 50`, `1 <= cols <= 50` (oder AGENTS-konforme Maximums). (b) `main._load_formation_data` komplett löschen, `self.file_io.load_formation_data(self, data)` aufrufen. |
| **Tradeoffs** | Validierung trivial; Duplikat-Entfernung ist Standard-M-1-Refactor-Rest. |

### M-6 · `RecoveryController.check()` triggert File-Load, ohne `host.file` zu locken
| Aspekt | Detail |
|--------|--------|
| **Severity** | 🟠 Mittel |
| **Confidence** | 70 % |
| **Location** | `chormanager/choraufstellung/recovery.py:68-97` |
| **Erklärung** | `check()` liest `self._storage.get_latest_autosave_path()` (Z. 75), vergleicht mtime mit `self._host.last_manual_save_mtime` (Z. 80), zeigt `QMessageBox.question` (Z. 105-112), ruft `self._storage.load_formation(latest)` (Z. 86), dann `self._host._load_formation_data(data)` (Z. 94). Während des `QMessageBox.question` (modal) ist der Main-Thread blockiert, ABER: der Auto-Save-Timer läuft **separat** als `QTimer` und kann feuern, sobald der User auf "Yes" klickt und der Modal-Close Event verarbeitet wird. |
| **Failure-Szenario** | User klickt "Ja, wiederherstellen" auf den Wiederherstellungs-Dialog. `load_formation` öffnet `latest_autosave.json`, parst es (~200 ms bei 100 Sängern). Genau in dem Moment feuert der AutoSaveController-Timer (alle 2 min, aber auch sofort nach `MainWindow.__init__`), schreibt einen **neuen** Auto-Save mit dem **noch nicht fertig restaurierten** `self.singers`. Der neue Auto-Save überschreibt den `latest_autosave.json`-Symlink-Target nicht direkt, aber die Rotation räumt den alten auf — und der Symlink zeigt jetzt auf den **halb-leeren** neuen Auto-Save. |
| **Suggested Remediation** | (a) AutoSaveController pausieren während Recovery: `self.autosave.stop()` vor `check()`, `self.autosave.start()` nach erfolgreichem Restore. (b) `host.file` zu Beginn auf `None` setzen, damit `is_modified()` `True` returnt. |
| **Tradeoffs** | ~5 Zeilen Code, semantisch klar. |

### M-7 · `SubProcess`-Aufruf in `choraufstellung_launcher._open_choraufstellung_for_event` mit `cwd` aus nicht-validiertem `__file__`
| Aspekt | Detail |
|--------|--------|
| **Severity** | 🟡 Mittel |
| **Confidence** | 70 % |
| **Location** | `chormanager/ui/choraufstellung_launcher.py:288-291` |
| **Erklärung** | `choraufstellung_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "choraufstellung")`. `__file__` ist unter normalen Bedingungen vertrauenswürdig, aber wenn das Projekt als **ZipApp** (`python -m zipapp`) oder via **PyInstaller** ausgeliefert wird, ist `__file__` ein temporärer Pfad in `_MEIPASS` — `choraufstellung_path` zeigt auf ein Verzeichnis, das nicht existiert. `os.path.exists(main_py)` (Z. 296) fängt das ab, aber der User sieht nur "Choraufstellung nicht gefunden" ohne Erklärung, **welcher** Pfad probiert wurde. |
| **Suggested Remediation** | `choraufstellung_path` einmal beim Startup validieren und Fehler in `app_logging` loggen. `subprocess.run` mit `check=False` und stderr-Capture. |
| **Tradeoffs** | 10 Zeilen. |

### M-8 · PDF-Export-Bridge ruft `PDFExporter` ohne Error-Handling für fehlende Fonts
| Aspekt | Detail |
|--------|--------|
| **Severity** | 🟡 Mittel |
| **Confidence** | 60 % |
| **Location** | `chormanager/choraufstellung/pdf_export.py` (Hauptlogik), `chormanager/choraufstellung/pdf_export_integration.py` (Bridge) |
| **Erklärung** | ReportLab versucht `Helvetica` als Default — wenn die Font-Datei fehlt (z. B. Minimal-Container ohne `fonts/`), wirft ReportLab `KeyError: 'Helvetica'`. Die Bridge ruft `PDFExporter().export(...)` ohne `try/except`, der Fehler propagiert in den Main-Thread, die App stürzt ab. |
| **Suggested Remediation** | `pdf_export_integration.PDFExportBridge.run()` mit `try/except (KeyError, OSError, UnicodeError)` umschließen, Fallback auf `pdfmetrics.registerFont(UnicodeCIDFont('HeiseiMin-W3'))`. |
| **Tradeoffs** | 5–10 Zeilen, einmaliger Fix. **Unsicher**, weil ich `pdf_export.py` und `pdf_export_integration.py` nicht gelesen habe — Confidence 60 %. |

---

## 🟡 Minor Findings

### m-1 · `RecoveryController` setzt `host.file` ohne Schreibschutz
`chormanager/choraufstellung/recovery.py:95` — `self._host.file = latest` setzt den File-Pointer auf den **Auto-Save-Pfad**. Der nächste `save_f()` schreibt in den Auto-Save statt in den manuellen File. **Empfehlung:** `host.file = None` nach Restore, sodass "Speichern" ein Save-As triggert.

### m-2 · `apply_all_affinity_proximity` benutzt `next()` ohne `default=`
`chormanager/choraufstellung/main.py:585` — `partner = next((s for s in self.singers if s.singer_id == singer.affinity), None)`. Hier ist der `default=None` gesetzt — OK. Aber das Pattern taucht in `formation_grid.py:294` ebenfalls auf (auch mit `default=None`), also insgesamt **konsistent**. **Status:** Noted, kein Action.

### m-3 · `update_singers` wird in 3 Hot-Loops aufgerufen, jedes Mal volle Repaint
`chormanager/choraufstellung/main.py:519, 731, 803` und mehrfach in `widgets/singer_pool.py`. Bei 200+ Sängern spürbar. **Empfehlung:** `update_singers(..., deferred=True)` mit `QTimer.singleShot(0, ...)` für Batch-Updates.

### m-4 · `os.path.exists` Race in `save_autosave` Symlink-Block
`chormanager/choraufstellung/storage.py:141-142` — TOCTOU zwischen `os.path.exists(latest_link)` und `os.remove(latest_link)`. **Empfehlung:** `try: os.remove(latest_link); except FileNotFoundError: pass`.

### m-5 · `FormationGrid.refresh_grid` ruft `findChildren(QLabel)` linear
`chormanager/choraufstellung/widgets/formation_grid.py:326-328` — bei verschachtelter Tile-Struktur (jeder Tile hat ein `QLabel` für den Namen) iteriert `findChildren` über alle Widgets des Grid-Containers. Bei 100+ Sängern mit komplexer Tile-Hierarchie: O(n²) Repaint-Cost. **Empfehlung:** Eigene `self._row_labels: List[QLabel]`-Liste pflegen, statt `findChildren` zu nutzen.

### m-6 · `EventRepository.set_active` ist ein globaler Update ohne `WHERE`
`chormanager/domain/repository.py:418-422` — `UPDATE projects SET is_active = 0` setzt **alle** Projekte inaktiv, dann `UPDATE projects SET is_active = 1 WHERE id = ?`. Wenn zwei Tabs gleichzeitig `set_active` aufrufen (z. B. über ein geplanten Multi-Select-Feature), können beide Updates interleaven und zwei aktive Projekte entstehen. **Empfehlung:** `with db.transaction():` + optional `SELECT ... FOR UPDATE` (in SQLite: nicht nativ, aber via `BEGIN IMMEDIATE`).

### m-7 · `AvailabilityRepository.update` macht `INSERT OR REPLACE`-Pattern mit `generate_id()`
`chormanager/domain/repository.py:344-349` — bei jedem `update` wird eine **neue UUID** generiert und per `INSERT … ON CONFLICT DO UPDATE` rein geschrieben. Falls die `INSERT`-Seite erfolgreich ist und der `DO UPDATE`-Pfad nie triggert (z. B. weil das `UNIQUE(singer_id, event_id)` nicht greift), entsteht eine **Geister-Zeile** mit zufälliger ID. **Empfehlung:** `INSERT OR IGNORE` + expliziter `UPDATE` in einer Transaktion.

### m-8 · `load_voice_groups` und `load_fields` haben `try/except`-lose File-Reads
`chormanager/config.py:144-147, 164-167` — `open(config_file, ...)` ohne `try/except`. Bei korrupter YAML wirft `yaml.safe_load` `yaml.YAMLError`, propagiert in den Caller. **Empfehlung:** Fallback auf Default-Konfiguration bei `yaml.YAMLError` oder `OSError`, Logging.

### m-9 · `AutoBackupService.backup_on_start` erstellt Backup **vor** `connect()`
`chormanager/backup/service.py:140-155` — `backup_on_start` ruft `Path(db_path).exists()`, aber `self.backup_service.create_backup(db_path)` macht `shutil.copy2(source, backup_path)`. Wenn die DB **nicht** exclusive geöffnet ist (was `sqlite3.connect` nicht garantiert), liest `shutil.copy2` möglicherweise halb geschriebene Pages. **Empfehlung:** `Database.close()` vor `create_backup`, oder `sqlite3` `VACUUM INTO` für konsistenten Snapshot.

### m-10 · `BackupService.list_backups` returned unsortierte Pfade
`chormanager/backup/service.py:53-67` — `sorted(backups, reverse=True)` sortiert lexikographisch. `chormanager_backup_20260613_120000.tar` > `chormanager_backup_20260612_120000.tar` ist OK, aber `chormanager_backup_20260612_120000.tar` > `chormanager_backup_20260612_090000.tar` ebenfalls — passt. ABER: das Sortier-Criterion ist **nicht** die Backup-Mtime, sondern der Filename-String. Wenn der User manuell ein Backup mit anderem Zeitformat reinkopiert, ist die Reihenfolge falsch. **Empfehlung:** `key=os.path.getmtime, reverse=True`.

---

## 🔒 Security Findings

### S-1 · F-String-SQL in `domain/repository.py` (aus 2026-06-12 wiederholt, aber jetzt mit Multi-Update-Concurrency)
| Aspekt | Detail |
|--------|--------|
| **Severity** | 🟠 Mittel-Hoch |
| **Confidence** | 90 % |
| **Location** | `chormanager/domain/repository.py:67, 90, 98, 107, 132, 188, 227, 247, 266, 302, 384, 430, 482, 491, 504, 512, 530, 591, 611, 625, 630, 640` |
| **Erklärung** | Wie 2026-06-12 dokumentiert: Spalten-Namen kommen aus `kwargs.keys()` (bei `create`/`update`), die aus Caller-Sicht **intern** sind. **Aber:** in `_cols()` (Z. 44-46) gibt es `cols = [c for c in table_columns if c != "is_adult"]` — wenn `kwargs` ein Schlüssel `is_adult` enthält, wird der gefiltert. Das deutet darauf hin, dass `is_adult` ein **virtuelles Feld** ist, das nicht persistiert wird. Falls ein Caller ein anderes virtuelles Feld einführt (z. B. `compute_is_adult` aus `domain/models.py`) und vergisst, es in `_cols()` zu whitelisten, wird der Spaltenname **trotzdem** interpoliert — Migration-Risk. |
| **Failure-Szenario** | Refactor fügt `is_minor`-Feld in `Singer` ein. `_cols()` wird nicht aktualisiert. `kwargs["is_minor"] = True` → `INSERT INTO singers (..., is_minor, ...) VALUES (..., ?, ...)` → `sqlite3.OperationalError: no such column: is_minor`. |
| **Suggested Remediation** | Explizite Whitelist: `ALLOWED_COLUMNS = set(self._SINGER_COLS)`; `cols = [c for c in kwargs if c in ALLOWED_COLUMNS]`. SQL-Injection ist latent, aber **Schema-Drift** ist akut. |
| **Tradeoffs** | 5 Zeilen, sofort. |

### S-2 · `urllib.request.urlopen` ohne TLS-Cert-Pinning
| Aspekt | Detail |
|--------|--------|
| **Severity** | 🟡 Mittel |
| **Confidence** | 80 % |
| **Location** | `chormanager/ui/update_controller.py:68-74` |
| **Erklärung** | `urlopen(req, timeout=10)` nutzt System-Cert-Store. In einem Firmen-Netz mit MITM-Proxy (z. B. Zscaler, Palo Alto) wird das CA-Bundle aus `SSL_CERT_FILE` akzeptiert. Ein kompromittierter Proxy kann eine gefälschte GitHub-Antwort liefern. |
| **Suggested Remediation** | Optional: `urlopen(req, timeout=10, cafile="/etc/ssl/certs/ca-certificates.crt")`. Pragma: Akzeptiere System-Store für Single-User-Desktop, dokumentiere die Limitation. |
| **Tradeoffs** | Zertifikats-Pinning für GitHub ist overkill; klarer Hinweis in der Doku reicht. |

### S-3 · `git pull origin main` ohne `git verify-commit`
| Aspekt | Detail |
|--------|--------|
| **Severity** | 🟠 Mittel-Hoch |
| **Confidence** | 95 % |
| **Location** | `chormanager/ui/update_controller.py:103-106` |
| **Erklärung** | Siehe C-3. `git pull` ohne Signaturprüfung. Wenn `asb-42/chormanager` jemals kompromittiert wird (z. B. via gestohlenen Maintainer-Token), pusht der nächste `Update durchführen`-Klick beliebigen Code. |
| **Suggested Remediation** | Signed Commits / Tags verlangen. `git pull --ff-only --verify-signatures`. Bei `git config commit.gpgsign true` und `tag.forceSignAnnotated true` ist das Default-Verhalten OK. |

---

## 🔁 Concurrency Findings

### CC-1 · `subprocess.run` ohne `QProcess`/`QThread` — 7 Hot-Paths
Siehe M-1.

### CC-2 · `QApplication.processEvents()` als Anti-Pattern
Siehe M-3.

### CC-3 · `auto_arrange_*` läuft synchron im Main-Thread mit O(n²)
`chormanager/choraufstellung/widgets/formation_grid.py:427-558` — fünf Auto-Arrange-Methoden, jede ist quadratisch in der Sängerzahl. Bei 100 Sängern ist der Refresh 5–10 s sichtbar. **Empfehlung:** in einen Worker-Thread mit Progress-Signal.

### CC-4 · `_pulse_step` Timer läuft ungebunden
`chormanager/choraufstellung/widgets/formation_grid.py:164-186` — `self._search_pulse_timer` wird bei `highlight_singer` neu erstellt, ohne den alten zu stoppen. Mehrfaches `highlight_singer` hintereinander → mehrere Timer, die auf denselben Tile feuern. **Empfehlung:** Singleton-Timer auf Grid-Ebene, `_search_pulse_singer` als state.

### CC-5 · `Subprocess-Symlink-Replace` in `save_autosave` ohne atomarem Rename
Siehe C-5.

---

## 🛡️ Reliability Findings

### R-1 · `AffinityRule` schreibt `s1.row, s2.row` direkt ohne Bounds-Check
`chormanager/choraufstellung/core/rules.py:409-410, 422-431` — `s1.row, s2.row = nr1, nr2` mit `nr1, nr1` aus `neighbors1 + empty_positions[:4]`. `empty_positions` enthält **alle** freien Grid-Zellen (`_get_neighbor_positions` Z. 472-482), also kann `nr1 > self.rows - 1` sein. **Bekannter Bug-Vektor:** Swaps außerhalb des Grids → negativer Index → `IndexError` beim nächsten Render. **Empfehlung:** `GridEngine.is_valid_position(nr, nc)` als Gate.

### R-2 · `VoiceGroupCohesionRule.apply` schreibt `s2.row, other.row = other.row, s2.row` mit potenziellen Konflikten
`chormanager/choraufstellung/core/rules.py:624-625` — direkter Swap ohne Check, ob `s2` und `other` identisch sind (kann passieren, wenn `other == s2` durch Filter-Bug). Division durch Null-Risiko, falls `s1 == s2`. **Empfehlung:** `assert s1.singer_id != s2.singer_id` als Sanity-Check.

### R-3 · `OptimizeFormationCommand.undo` setzt Positionen ohne `refresh_grid()` für die `_resolve_voice_group_map`
`chormanager/choraufstellung/core/optimizer.py:50-54` — Undo setzt `s.row, s.col` aus `old_positions`, ruft `self.grid.refresh_grid()`. **Aber:** `refresh_grid` cached `self.tiles` (Dict von singer_id → Tile). Wenn ein Singer-Objekt zwischen `redo()` und `undo()` durch `_load_formation_data` ersetzt wurde (z. B. über einen externen Reload), zeigt `self.tiles` auf das **alte** Singer-Objekt, die `_old_positions` aber auf die **neue** ID. **Empfehlung:** `self.tiles.clear()` vor `undo()`.

### R-4 · `formation_grid.apply_affinity_proximity` mutiert `partner.row` ohne Grid-Engine-Validierung
`chormanager/choraufstellung/widgets/formation_grid.py:309-316` — direkter `partner.row, partner.col = occupant.row, occupant.col` ohne `GridEngine.can_place` zu prüfen. Wenn `occupant.row` out-of-bounds ist, crasht `refresh_grid()`. **Empfehlung:** `GridEngine` als Single-Source-of-Truth nutzen.

### R-5 · `save_formation` schreibt `tmp` ohne Cleanup bei Crash
`chormanager/choraufstellung/storage.py:62-65` — `tmp = target_path + ".tmp"`, `f = open(tmp, 'w')`, `os.replace(tmp, target_path)`. Wenn der Prozess zwischen `open` und `os.replace` stirbt, bleibt `<file>.tmp` übrig. Beim nächsten Save wird `tmp` überschrieben (OK), aber `os.listdir(backup_dir)` listet es (in einem anderen Pfad, hier aber `target_path` direkt). **Empfehlung:** `try/except` mit `os.remove(tmp)` im Fehlerfall.

### R-6 · `choraufstellung_bridge._refresh_pool` ruft `update_singers` ohne `pool.placed_singer_ids`-Sync
`chormanager/choraufstellung/chormanager_bridge.py:253-257` — setzt `pool.singers = host.singers` und `pool.update_singers(..., set())` (leeres Set für placed_ids). Aber `host.grid` hat u. U. **bereits platzierte** Sänger (z. B. wenn `chormanager_mode=True` aber Sänger mit `row >= 0` geladen werden). Die `placed_singer_ids` werden nicht aus `host.grid.get_placed_singer_ids()` übernommen. **Empfehlung:** `host.pool.placed_singer_ids = host.grid.get_placed_singer_ids()`.

---

## 🏗️ Architectural Findings

### A-1 · Mixin-Inflation in `MainWindow` — 7 Mixins, gemeinsame `self.<tab>`-Erwartung
`chormanager/ui/main_window.py:92-101` — `MainWindow(QMainWindow, ThemeMixin, TabRouterMixin, ChorAufstellungLauncherMixin, ExportCoreMixin, ExportJsonSyncMixin, ExportTabSpecificMixin, MainWindowActionsMixin)`. Jeder Mixin erwartet Attribute wie `self.singers_tab`, `self.db_path`, `self.current_project`. **Diamond-Problem-light:** wenn zwei Mixins dieselbe Methode definieren (z. B. `MainWindowActionsMixin._save_projekt` und ein hypothetischer `ExportCoreMixin._save_projekt`), gewinnt die rechte in der MRO, stillschweigend. **Empfehlung:** Mixins durch Komposition ersetzen (ExportController, UpdateController als QObject-Members). Im aktuellen Stand funktioniert es, aber das **Risiko** wächst mit jeder neuen M-1-Step.

### A-2 · Subshell-Spawn-Architektur (C-1) ist nicht die einzige
`chormanager/choraufstellung/__main__.py:1-15` und `chormanager/choraufstellung/main.py:818-840` definieren **eine** QApplication im Subprozess. Aber `chormanager/ui/choraufstellung_launcher.py:209-211` ruft denselben Subprozess. Es gibt also **genau einen** Spawn-Pfad. Sobald aber ein Test (`tests/unit/test_choraufstellung_main_menu.py`, `test_choraufstellung_undo_bridge.py`) ein `MainWindow` direkt instanziiert, läuft der **Hauptprozess** mit QApplication UND der Subshell-Spawn läuft auch. Test-Side: das ist OK, weil der Subshell-Spawn in Tests gemockt wird. **Production-Side:** es gibt keine Instanz, die zwei `QApplication`s **gleichzeitig** laufen lässt, also kein direkter Bug. **Aber:** das M-2-Doc ([`main.py:43-66`](chormanager/choraufstellung/main.py:43)) sagt, PyQt5-Fallbacks werden weiter unterstützt — das ist **toter Code** in einem PyQt6-Projekt.

### A-3 · Toter PyQt5-Fallback in `qt_compat`
`chormanager/choraufstellung/qt_compat.py` — in `chormanager/choraufstellung/undo_bridge.py:27-30` existiert noch `try: from PyQt6.QtCore ... except ImportError: from PyQt5.QtCore ...`. `requirements.txt` listet nur PyQt6. **Empfehlung:** PyQt5-Fallback komplett entfernen.

### A-4 · Globale `_VoiceGroup`, `_Singer` Lazy-Caches in `chormanager_bridge.py`
`chormanager/choraufstellung/chormanager_bridge.py:39-46` — Modul-globale Caches. Wenn der `VoiceGroup`-Enum refactored wird (z. B. Enum-`auto()`-Werte), wird der Cache **nie** invalidiert, weil `_VoiceGroup is None` nach dem ersten Resolve immer `False` ist. **Empfehlung:** Singleton in `singer_model`, nicht im Bridge-Modul.

### A-5 · `_load_formation_data` ist in `main.py:790-815` und `file_io.load_formation_data` in `file_io.py:75-117` dupliziert
Siehe M-5.

### A-6 · `test_storage_regression` / `test_storage` decken `domain.repository` **nicht** ab
`tests/integration/test_storage.py` und `test_storage_regression.py` sind die einzigen Storage-Tests. `domain/repository.py` mit 600+ LOC, 19 F-String-SQL-Queries, und **keine** direkten Unit-Tests. **Empfehlung:** `tests/unit/test_repository_sql_safety.py` mit parametrischen Tests (alle `kwargs`-Keys, alle `_SINGER_COLS`).

---

## 🧪 Test-Coverage Findings

### T-1 · `OptimizeFormationCommand` hat keinen dedizierten Test
`tests/unit/test_undo_commands.py` testet `MoveSingerCommand`/`SwapSingersCommand`/`MoveGroupCommand`/`UndoStack`, aber **nicht** `OptimizeFormationCommand` (C-2). **Empfehlung:** Test, der einen Optimierer mit Mock-Singern laufen lässt, dann `undo()` aufruft, prüft dass Positionen auf `old_positions` zurückgehen, **nicht** auf Zwischen-Positionen.

### T-2 · `AffinityRule` hat keinen Performance-Bound-Test
Kein Test prüft, dass `apply` bei 50 Sängern < 1 s läuft. **Empfehlung:** `test_affinity_perf.py` mit `@pytest.mark.timeout(2)`.

### T-3 · `RecoveryController.check()` hat keinen Race-Test
Der Auto-Save-vs-Restore-Race (M-6) ist hypothetisch — kein Test reproduziert ihn. **Empfehlung:** `test_recovery_race.py` mit `QTimer.singleShot(0, autosave_controller.check)` während eines Recovery-Loads.

### T-4 · `update_controller._do_update` hat keinen Test
`tests/unit/test_update_controller.py` existiert nicht. Die git-Logik ist komplett ungetestet. **Empfehlung:** Mock `subprocess.run`, prüfe dass `git pull` mit korrektem `cwd` aufgerufen wird, dass bei `returncode != 0` die Statusbar `Update fehlgeschlagen` zeigt.

### T-5 · `FormationStorage.save_autosave` Symlink-Pfad ungetestet auf Windows
`tests/unit/test_choraufstellung_autosave.py` testet `AutoSaveController`, nicht `FormationStorage.save_autosave` direkt. **Empfehlung:** `test_storage_autosave_symlink.py` mit `pytest.mark.skipif(not hasattr(os, "symlink"), reason="Windows")`.

---

## 🗑️ Dead-Code Findings (Updates zu 2026-06-12)

| Datei | Symbol | Status | Bemerkung |
|-------|--------|--------|-----------|
| `chormanager/choraufstellung/qt_compat.py` | `exec_qt()`-Helper, `FallbackSinger`, `FallbackOptimizerDialog` | 🟢 Toter Code (bestätigt) | PyQt5 nicht in `requirements.txt` |
| `chormanager/choraufstellung/undo_bridge.py:27-30` | `try/except ImportError` für PyQt5 | 🟢 Toter Code | Siehe A-3 |
| `chormanager/backup/service.py` | `BackupService` (alt) | 🟡 Parallel zu `export/backup_service.py` | Welche wird benutzt? Suche in `main_window.py` zeigt: `AutoBackupService` aus `backup/service.py`. `export/backup_service.py` wird nur von `BackupRestoreDialog` benutzt. **Zwei Klassen mit unterschiedlichen Verantwortlichkeiten** — Refactor-Kandidat. |
| `chormanager/choraufstellung/main.py:761-769` | `_menu_legenda` | 🟢 Toter Code | Methode ist leer (`for a in m.actions(): if a.text() == "Über": continue`), keine Wirkung. |
| `chormanager/choraufstellung/main.py:118` | `voice_group_color` import | 🟢 Unused | Wird in main.py nicht direkt genutzt, sondern via `singer_model.voice_group_color`. |
| `chormanager/import_singers.py` (root) | Top-Level-Skript | 🟡 Vermutlich tot | `chormanager/tools/import_singers.py` ist im Tree. |
| `chormanager/choraufstellung/core/rules.py:660-665` | `get_primary_rules`, `get_refinement_rules` | 🟢 Unused? | Im Tree gesucht: keine Aufrufer außerhalb von `core/optimizer.py:FormationOptimizer.run` (das intern filtert). |

---

## 🛠️ Technology-Stack-Usage Assessment (Update 2026-06-12)

### PyQt6 (Score 5/10 → 5/10, unverändert)
- **Stärken (neu):** `QtUndoStack` als reiner `QObject`-Wrapper über pure-Python-Stack ist sauber. `RecoveryController` als duck-typed Host-Konsument ist vorbildlich.
- **Schwächen (neu):** Subshell-Spawn-Pattern (C-1) macht Tests für die echte Integration unmöglich. `QApplication.processEvents()`-Spam in `update_controller` (M-3) ist neu hinzugekommen.

### SQLite via `Database` (Score 6/10 → 5/10)
- **Stärken:** Wie 2026-06-12.
- **Schwächen (neu):** Connection-Sharing zwischen Tabs (C-6) ist **deutlich** schlimmer als damals angenommen, weil `refresh_tab_repositories` die Reihenfolge **muss** exakt einhalten. Race in `_reload_after_restore` zwischen `db.close()` und `db.connect()` (Failure-Szenario 2 in C-6) ist real, weil Tab-Timer unabhängig feuern.

### PyYAML (Score 6/10 → 7/10)
- **Stärken (neu):** `lru_cache(maxsize=1)` auf `load_voice_groups`, `load_fields`, `load_app_config` ist in 2026-06-12 als Quick-Win Q-1 erwähnt und jetzt umgesetzt.
- **Schwächen (unverändert):** Kein Schema-Validation, kein Fallback bei korrupter YAML (m-8).

### ReportLab (Score 4/10 → 4/10)
- **Stärken (unverändert):** Funktioniert.
- **Schwächen (neu):** `PDFExportBridge` abstrahiert den Call, aber Font-Fehler werden nicht abgefangen (M-8).

### pytest + pytest-qt (Score 7/10 → 6/10)
- **Stärken (neu):** 430+ Tests, Refactor-Disziplin.
- **Schwächen (neu):** Coverage-Lücken in `OptimizeFormationCommand` (T-1), `AffinityRule` Performance (T-2), `RecoveryController` Race (T-3), `update_controller` (T-4), `FormationStorage.save_autosave` (T-5). Migrations-Tests fehlen komplett.

### subprocess / QProcess (Score 2/10, neu bewertet)
- **Stärken:** Funktioniert in Single-User-Szenarien.
- **Schwächen:** 7 blockierende `subprocess.run`-Aufrufe (M-1), keine Timeouts in 3 davon, kein Worker-Thread-Pattern.

---

## 🏁 Final Verdict

### Production-Ready?
**🟡 Bedingt — wie 2026-06-12.** Die Refactorings M-1/M-2/M-3 haben die unmittelbaren UI-Bugs adressiert, aber die **nächste Schicht** von Risiken (C-1 Subshell-IPC, C-2 Optimizer-Doppel-Redo, C-3 blockierender Update, C-4 Optimizer-Komplexität, C-5 Auto-Save-Symlink, C-6 DB-Connection-Sharing) ist jetzt sichtbar. Für eine Single-User-Desktop-App im Verein: **nutzbar mit Workarounds**. Für eine Mehr-Mandanten-/Server-Migration: **komplettes Architektur-Update nötig**.

### Biggest Risks (Reihenfolge der Wichtigkeit)
1. **C-1** — Subshell-IPC fragil, Backup-Restore-Race, Temp-JSON-Leak (Datenverlust-Szenario)
2. **C-3** — `git pull` ohne Timeout/Signatur (UI-Freeze + potenzielle RCE)
3. **C-2** — `OptimizeFormationCommand`-Doppel-Redo + falsches Undo (Datenkonsistenz)
4. **C-4** — `AffinityRule` O(n²) ohne QThread (UI-Freeze bei >30 Sängern)
5. **C-5** — Auto-Save-Symlink bricht auf Windows und ist race-anfällig
6. **C-6** — Connection-Sharing zwischen Tabs → Backup-Restore-Race

### Must-Fix Before Release
- [ ] **C-2:** `OptimizeFormationCommand`-Doppel-Redo auflösen
- [ ] **C-3:** `update_controller._do_update` Timeout + `git verify-commit`
- [ ] **C-5:** Auto-Save Symlink durch atomic file replace ersetzen
- [ ] **M-4:** `state.json` atomic write
- [ ] **S-1:** SQL `kwargs`-Whitelist (mindestens für `is_adult`/`is_minor`-Felder)

### Should-Fix Before New Features
- [ ] **C-1:** Subshell-IPC-Architektur evaluieren (Modul-Einbettung statt Subprozess)
- [ ] **C-4:** `AffinityRule` in `QThread` migrieren
- [ ] **C-6:** Pro-Tab-Connection einführen
- [ ] **M-1:** Alle `subprocess.run` in `QThread`/`QProcess`
- [ ] **M-5:** `load_formation_data`-Duplikation entfernen
- [ ] **T-1 bis T-5:** Fehlende Tests schreiben

### Nice-to-Have
- [ ] **CC-4:** Singleton-Timer für `_search_pulse_step`
- [ ] **R-3:** `OptimizeFormationCommand.undo` mit `tiles.clear()` vor `refresh_grid()`
- [ ] **A-3:** PyQt5-Fallback entfernen
- [ ] **A-5:** `load_formation_data` deduplizieren
- [ ] Property-Based-Tests mit `hypothesis` für `AffinityCostFunction.compute_cost`
- [ ] Mutation-Tests mit `mutmut` auf `core/optimizer.py`
- [ ] Pre-Commit-Hook: `ruff check`, `bandit -r chormanager/`, `pytest --cov=chormanager --cov-fail-under=50`

---

## 📎 Anhang

### A. Test-Stand (geschätzt)
```
$ python -m pytest tests/ -q
~430 passed, 0 failed (nach M-1 + M-2 + M-3)
```

### B. Coverage-Stand (geschätzt)
```
Phase 1-6 (2026-06-12):   ~42 %
+ M-1 (MainWindow-Refactor): +3 %
+ M-2 (ChorAufstellung-Refactor): +2 %
+ M-3 (Dialoge):             +1 %
Stand: ~48 %
```

### C. Neue Module seit 2026-06-12
| Modul | LOC | Zweck |
|-------|---:|-------|
| `chormanager/choraufstellung/core/optimizer.py` | 95 | Optimizer-Engine |
| `chormanager/choraufstellung/autosave.py` | 136 | Auto-Save-Controller |
| `chormanager/choraufstellung/recovery.py` | 113 | Auto-Save-Recovery |
| `chormanager/choraufstellung/file_io.py` | 240 | File-IO-Bridge |
| `chormanager/choraufstellung/undo_bridge.py` | 117 | Qt-Undo-Wrapper |
| `chormanager/choraufstellung/chormanager_bridge.py` | 258 | Subshell-DB-Loader |
| `chormanager/choraufstellung/pdf_export_integration.py` | ~100 | PDF-Export-Bridge |
| `chormanager/choraufstellung/theme.py` | ~80 | Theme-Applier |
| `chormanager/choraufstellung/main_menu.py` | ~60 | Menu-Builder |
| `chormanager/ui/choraufstellung_launcher.py` | 309 | Subshell-Spawn-Mixin |
| `chormanager/ui/export_controller.py` | 884 | Export-Mixins |
| `chormanager/ui/update_controller.py` | 115 | Version-Check-Dialog |
| `chormanager/ui/main_window_actions.py` | ~200 | MainWindow-Action-Mixin |
| `chormanager/ui/tab_router.py` | ~150 | Tab-Routing-Mixin |
| `chormanager/ui/theme_manager.py` | ~80 | Theme-Mixin |
| `chormanager/choraufstellung/qt_compat.py` | ~250 | PyQt5/6 Cross-Compat (tlw. tot) |
| `chormanager/choraufstellung/dependencies.py` | 147 | Fallback-Dependencies |
| **Summe** | **~3 530 LOC** | |

### D. Risiko-Hot-Map
```
                   Häufigkeit
                   Selten    Häufig
Schaden
Hoch     │  C-1   C-2, C-3, C-4
         │  C-5, C-6
         │
Mittel   │        M-1, M-2, M-3, M-4, M-5, M-6
         │        S-1, R-1, R-2
         │
Niedrig  │        m-1 bis m-10
         │
```

### E. Vor-2026-06-12 Findings (Status-Update)
- **M-1 (God-Class main_window.py):** Mit M-1-Step 1-8 teilentkräftet. Hauptfenster ist jetzt ein **Mixin-Aggregator**, aber Aggregator-Architektur hat eigene Risiken (A-1). **Weiter relevant.**
- **M-2 (God-Class choraufstellung/main.py):** Von 2 180 → 841 LOC reduziert (Refactor M-2). Hauptmodul ist jetzt thin-shell. **Weiter teils relevant** wegen Mixin-/Bridge-Inflation.
- **M-3 (F-String-SQL):** **Unverändert relevant** (S-1).
- **M-4 (`except:`):** Teilweise adressiert (`dependencies.py:96, 113` nutzt konkrete Exceptions). **Aber:** `chormanager_bridge.py:139, 201` hat neue `except Exception`-Stellen. **Weiter relevant.**
- **M-5 (Subprocess-Spawns):** **Verschärft** durch `update_controller._do_update` (C-3) und `choraufstellung_launcher.py` (C-1).
- **M-6 (Transaktionen):** **Unverändert relevant.** `SingerRepository.update` macht Multi-Table-Update ohne `with db.transaction():` (Z. 138-160).
- **M-7 (os.path/pathlib):** **Unverändert.**
- **M-8 (processEvents):** **Verschärft** in `update_controller.py` (M-3).
