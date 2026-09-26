# Web-Migration ChorManager — Analyse, Tech-Stack-Empfehlung & Phasenplan

**Stand:** 2026-09-25 · **Autor:** OpenCode (Muse Spark) · **Quelle:** Live-Codeanalyse von `main` @ `c9acebf`
**Vorgänger:** `docs/plans/2026-06-11_web-migration.md` (wird hier aktualisiert / korrigiert, nicht ersetzt)
**Ablage:** `docs/plans/` (am 2026-09-25 von `plans/` hierher verschoben; siehe §7 zur Verzeichnisstruktur-Bereinigung).
**MS4 erreicht am 2026-09-27 (Branch `web-migration`):** Docker-Compose-Release verifiziert (Write-Kette + PDF/ODT durch nginx→api→MariaDB), Web-Benutzerhandbuch + CHANGELOG nachgezogen, danach Merge nach `main`.

---

## 0. Git-Status: kein Update nötig

```text
origin  git@github.com:asb-42/chormanager.git (fetch/push)
main    c9acebf [origin/main] Merge PR #7: release v0.1
git fetch origin --prune  →  main == origin/main, kein Diff
```

Am 2026-09-25 wurde `git fetch origin --prune` ausgeführt. Lokales `main` ist identisch mit `origin/main` — **kein Pull, kein Merge erforderlich**. Alle Zahlen unten beziehen sich auf diesen Stand.

---

## 1. Ist-Analyse: was migriert werden müsste

### 1.1 Größenordnung (gemessen, nicht geschätzt)

| Kennzahl | Wert (gemessen 2026-09-25) |
|---|---|
| Produktions-Dateien (`chormanager/**/*.py`) | **103** |
| Produktions-LOC | **23.856** |
| Test-Dateien (`tests/**/*.py`) | **122** |
| Test-LOC | **22.705** |
| Größte Dateien | `ui/main_window.py` 990 · `ui/export_controller.py` 919 · `ui/dialogs/_task_wizard.py` 861 · `choraufstellung/main.py` 839 · `choraufstellung/widgets/formation_grid.py` 825 · `choraufstellung/ui/grid_widget.py` 778 (totes Duplikat) · `choraufstellung/core/rules.py` 710 |
| Sprache / Laufzeit | Python `>=3.9` (`pyproject.toml`), Desktop Linux Mint/Ubuntu (`run.sh`) |
| GUI-Abhängigkeiten | `PyQt6>=6.5.0,<6.8.0` (Produktion), `PyQt5>=5.15.0` (nur Dual-Bind-Dialog-Tests + Fallbacks in `draggable_list.py`), `PyYAML`, `reportlab>=4.0` |
| Test-Stack | `pytest`, `pytest-qt`, `pytest-cov`, `hypothesis`; Headless via `QT_QPA_PLATFORM=offscreen` |

Qt-Anteil (via `grep PyQt6|PyQt5`, Limit 100 erreicht): ca. **60+ Dateien / 65–75 % des Produktionscodes** sind Qt-gebunden und müssen für Web neu implementiert werden. Ca. **25–30 Dateien sind Qt-frei** und direkt wiederverwendbar (s. §1.3).

### 1.2 Funktionsumfang (aus `README.md` + Code verifiziert)

| Bereich | Desktop-Umsetzung | Tabellen / Formate |
|---|---|---|
| Aufgaben-Wizard (Startansicht) | `ui/views/tasks_view.py`, `ui/dialogs/_task_wizard.py` (861 LOC), `domain/taskflow/` (Qt-frei) | Vorbedingungs-Graph, keine eigene Tabelle |
| Sänger-Stammdaten | `ui/views/singers_tab.py` (378), `ui/forms/singer_dialog.py`, Suche/Filter/Sortierung, Undo/Redo, Auto-Backup | `singers` |
| Projekte & Termine | `views/projects_tab.py` (397), `views/events_tab.py` (445), Projekt-Filter + Header-Anzeige | `projects`, `events` |
| Verfügbarkeit (6 Status: yes/no/none/conditional/unknown/maybe) | `dialogs/_event_availability.py` (637), `dialogs/_event.py`, Matrix-Ansicht | `availability` |
| Besetzung / Repertoire / Selbstdarstellung | `views/besetzung_tab.py`, `views/repertoire_tab.py`, `dialogs/_selbstdarstellung.py` | `besetzung`, `repertoire`, `selbstdarstellung` |
| Theming Hell/Dunkel | `ui/theme_manager.py` (484), QSS-Sheets | `config/app.yaml`, `voice_groups.yaml/json` |
| Exporte | `ui/export_controller.py` (919!), `core/response_render_pdf.py`, `response_render_odt.py`, `export/sync.py` (191) | CSV, PDF (reportlab), LibreOffice Writer/Calc, JSON-Sync |
| Backup / History | `backup/service.py` (217, ZIP + `sqliteConnection.backup`), `history/service.py` (194, Qt-freies Command-Protokoll) | `~/.local/share/chormanager/chor.db`, portabler Modus |
| Update-Check | `ui/update_controller.py`, `subprocess_runner.py` (TLS-Trust-Annahme, siehe Benutzerhandbuch „Problemlösung“) | GitHub Releases |
| Choraufstellung-Integration | `ui/choraufstellung_launcher.py` (414), `views/choraufstellung_tab.py` (404), `CHOR_EVENT_DATA`-JSON via ENV, SQLite-Fallback — **einweg** (kein Write-Back) | Temp-JSON `{singer_id, full_name, short_name, voice_group, height, affinity_uuid}` + Metadaten |

DB-Schema (`chormanager/data/database.py`, `ConnectionPool` mit WAL + `busy_timeout=5000`): 7 Tabellen — `singers`, `events`, `projects`, `selbstdarstellung`, `availability`, `besetzung`, `repertoire`.

### 1.3 Was direkt wiederverwendbar ist (Qt-frei, ohne Änderung als Backend-Service)

- `choraufstellung/core/` komplett: `rules.py` (711, 8 Arrangement-Regeln + `RULE_REGISTRY`), `grid_engine.py` (132, Geometrie), `arrangement.py` (355, funktionale Alt-API), `commands.py` (268, `UndoStack` + Move/Swap/Group-Commands), `optimizer.py` (103, nur `TYPE_CHECKING`-Qt-Import).
- `domain/` (13 Dateien inkl. `taskflow/`), `data/database.py` (366), `core/` (Response-Matrix + PDF/ODT-Renderer), `backup/service.py`, `history/service.py`, `export/sync.py`, `config.py` (376), `choraufstellung/{singer_model,storage,file_io,config}.py` (JSON-Serialisierung, atomar via `tmp+os.replace`).
- Summe: **ca. 2.500–3.500 LOC reine Business-Logik** (deckt sich mit Vorgängerplan §82: „~2.500 lines transfer directly“).

### 1.4 Was neu gebaut werden muss (Qt-gebunden)

- Komplette `ui/` (35 Dateien): `MainWindow` (~990), `TabRouter` (533), alle 7 Views, 10 Dialoge, Delegates, Icons, `ThemeManager`, `ExportController` (919).
- Komplettes `choraufstellung/widgets/` + `main.py`/`file_io`-Dialoganteile/`pdf_export*`/`theme.ThemeApplier` (QSS) / `undo_bridge.QtUndoStack` (dünner Signal-Adapter).
- Doppelimplementierung `choraufstellung/ui/` (778 + 496 LOC) vs. `choraufstellung/widgets/`: **beide leben und sind divergiert** (Entscheid 2026-09-26, Branch `web-migration`). `widgets/formation_grid.py` (825) wird von `main.py` produktiv genutzt und gilt als **Verhaltens-Spec für den React-Editor**; `ui/grid_widget.py` + `ui/pool_widget.py` hängen am Paket-Interface (`__init__.py`-Reexporte) und an 2 Tests. Keine Löschung in M0 — beide werden ohnehin durch das Frontend ersetzt.

---

## 2. Deep Dive: Choraufstellung-Raster (der Kostentreiber, 30–40 % des Aufwands)

Referenzdateien: `choraufstellung/widgets/formation_grid.py:59-825`, `singer_tile.py:178-288`, `singer_pool.py:1-457`, `draggable_list.py:1-133`, `core/grid_engine.py`, `core/commands.py`.

### 2.1 Entscheidende Erkenntnis: kein `QGraphicsView`, sondern absolute `QWidget`-Geometrie

Das Raster ist ein plain `QWidget` (`setAcceptDrops(True)`) mit absolut positionierten Kindern:

- Hintergrundzellen: `QFrame` (`Shape.Panel`, `Shadow.Sunken`, `setGeometry(x,y,125,75)`).
- Sänger-Kacheln: `SingerTile(QFrame)`, `setFixedSize(120,60)`, `move(x,y)`, `show()`, `installEventFilter`.
- Position: `x = MARGIN_LEFT(80) + col*130 (+OFFSET 65 wenn staggered && row%2==1)`, `y = MARGIN_TOP(20) + row*80`.
- `refresh_grid()` löscht alle Tiles (`deleteLater`), baut Zellen + Tiles neu, cached Row-Labels (kein `findChildren`-Walk).

**Folge für Web:** Das lässt sich 1:1 auf **DOM mit absoluter Positionierung + CSS-Transforms** abbilden — kein Canvas-Zwang. `GridConfig`/`pixel_pos()` aus `grid_engine.py` ist direkt nach TypeScript portierbar.

### 2.2 Interaktions-Inventar (alles muss im Web nachgebaut werden)

| Feature | Desktop-Mechanik | Web-Äquivalent (s. §3.3) |
|---|---|---|
| Pool → Grid Drag | `DraggableTableWidget.startDrag`, MIME `singer:<id>` / `singer:<prim>:group:<ids>`, `QDrag.exec(CopyAction)` | dnd-kit `useDraggable` + JSON-Payload statt MIME-String |
| Tile → Grid Move/Swap | `SingerTile.mouseMoveEvent` (Start-Distanz via `manhattanLength`), `drag.setPixmap(grab())`, Drop parst `mimeData().text()`, `row=(y-20)/80`, `col=(x-80-offset)/130`, Swap mit Bewohner | dnd-kit `useDroppable` pro Zelle + `closestCenter`-Kollision; Swap-Logik aus `dropEvent()` portieren |
| Gruppen-Drag (Mehrfachselektion) | Delta-Check aller `group_ids`, `QMessageBox.warning("Rand erreicht")` bei Overflow | dnd-kit Multi-Drag (eigener Sensor) + Vorab-Validierung via `can_place()` |
| Rubber-Band-Selektion | `QRubberBand(Rectangle)` auf leerem `mousePress`, `rect.intersects(tile.geometry())` | Maus-Overlay-`<div>` + `getBoundingClientRect`-Schnitt; Touch: Zwei-Finger oder Long-Press-Modus |
| Undo/Redo | `core/commands.UndoStack` (rein Python!) + `undo_bridge.QtUndoStack`-Signalschicht; Befehle: Move/Swap/Group/Optimize | `UndoStack` nach TS portieren (Callbacks statt `refresh_fn`), Ctrl+Z / Ctrl+Shift+Z, serverseitig persistiert |
| Kontextmenü | `QMenu`: Rückgängig/Wiederholen, `apply_affinity_proximity`, Positionen tauschen, Bearbeiten/Nähe/Entfernen | Custom Context-Menu (Radix/Shadcn), gleiche Aktionen via REST |
| Suche-Puls (`highlight_singer`) | Singleton-`QTimer` 200 ms, 5× Pulse `#FFD700/#FF8C00` | CSS-Animation + `scrollIntoView` |
| Optimizer-Dialog | `priority1_combo` (Makro) + `priority2/3` (Refinement), `RULE_REGISTRY` | Gleicher Dialog als Form; Regeln laufen serverseitig (Python wiederverwenden), Ergebnis als Diff-Preview |
| Druck/PDF | `QPainter/QPrinter` + reportlab | Server-PDF (reportlab behalten) + Client-Print-CSS |
| Theming | `ThemeApplier` (QSS) + `voice_group_color()` theme-aware | CSS-Variablen + Tailwind `dark:`-Klasse, Farben aus `voice_groups.yaml` |

Leistung: Bei typischen Chören (40–120 Kacheln) reicht DOM problemlos. Erst ab >300 Kacheln wäre Canvas (`Konva`) schneller — aktuell nicht nötig.

---

## 3. Tech-Stack-Empfehlung

### 3.1 Empfehlung: FastAPI-Backend + React/TypeScript-Frontend (Monolith-Deployment)

Diese Empfehlung **bestätigt** den Vorgängerplan (Option A Monolith) und präzisiert ihn auf Basis der Live-Analyse (§2.1: DOM statt Canvas).

```text
Backend      FastAPI 0.110+ · SQLAlchemy 2.0 · Pydantic v2 · Alembic · PyTest · Python 3.11/3.12 via .venv
DB           MariaDB/MySQL InnoDB utf8mb4 (Produktion, wird bereits betrieben) · SQLite (Dev/Test, Bestand weiter nutzbar)
Auth         Single-User + Token zum Start; Rollen-/Rechtemodell (Chorleiter/Vorstand/Sänger) als Architektur-Reserve, s. §5.8
PDF/Export   reportlab (behalten, server-seitig) · LibreOffice-Export via odfpy/unoconv-Endpoint
Frontend     TypeScript 5 · React 18 · Vite · Tailwind CSS · shadcn/ui (Radix) · TanStack Query · Zustand · React Hook Form + Zod
DnD          @dnd-kit/core + @dnd-kit/sortable (Formation Editor, s. §3.3)
Tabellen     TanStack Table (Sänger/Verfügbarkeit/Besetzung)
PDF-Preview  <iframe>/PDF.js auf Backend-Endpoint
Deployment   Docker Compose (api + db + static-frontend via nginx), server-seitig, Browser als primärer Client
Tests        Backend: pytest (Bestand) · Frontend: Vitest + Testing Library + Playwright (1–2 Smoke-Flows)
Branch       Eigener Migrations-Branch, Qt-`main` bleibt bis MS4 voll benutzbar, s. §5.9
```

**Warum genau dieser Stack:**

1. **Maximale Backend-Wiederverwendung.** `domain/`, `choraufstellung/core/`, `data/`, `export/`, `backup/` sind Qt-frei und wandern fast unverändert hinter FastAPI-Router — das ist der größte Hebel (ca. 3k LOC geschenkt). Django wäre schwerer, weil das bestehende SQLAlchemy-nahe Repository-Pattern und die Pydantic-ähnlichen Dataclasses (`Singer.to_dict/from_dict`) natürlicher auf FastAPI abbilden.
2. **React + dnd-kit ist die einzige Kombination, die alle Raster-Interaktionen (§2.2) abdeckt** — inkl. Touch, Tastatur-Accessibility und Gruppen-Drag. HTMX/Alpine (im Vorgängerplan als „nicht empfohlen“ markiert) bleiben für CRUD denkbar, scheitern aber am Formation Editor. Vue 3 + `vuedraggable` wäre gleichwertig, hat aber kleineres DnD-Ökosystem als dnd-kit.
3. **reportlab bleibt server-seitig** — der Vorgängerplan (Option A Server-side) ist korrekt; Client-PDF (jsPDF) würde Drucktreue verlieren.
4. **MariaDB statt SQLite-Datei**, sobald mehr als ein Gerät zugreift (der eigentliche Web-Mehrwert) — und MariaDB statt PostgreSQL, weil sie **bereits betrieben wird** (s. §5.6). Für Single-User-Start reicht SQLite weiter — kein harter Cutover nötig. SQL portabel halten (keine PG-spezifischen Typen), damit ein späterer Wechsel möglich bleibt.
5. **PWA/Offline nur optional:** Der Nutzen ist unbewiesen — daher kein Kernbestandteil, sondern optionale Erweiterung M6 (§5.7), nur bei echtem Bedarf.

### 3.2 Ausdrücklich nicht empfohlen (mit Begründung)

| Alternative | Urteil | Begründung |
|---|---|---|
| Django + HTMX/Alpine als Full-Frontend | Abgelehnt für Formation Editor | CRUD 30 % schneller, aber Rubber-Band, Gruppen-Drag, Swap-Preview und Undo sind in HTMX nicht sauber baubar. Allenfalls als Admin-CRUD neben React-Editor — erhöht aber Stack-Komplexität ohne Not. |
| Canvas-first (`Konva`/`Fabric`) für das Raster | Abgelehnt als Startpunkt | Raster ist kein Freiform-Canvas, sondern feste Geometrie (§2.1). Canvas verliert Accessibility (Screenreader, Tastatur), Text-Selektion und einfaches Theming. Erst bei >300 Kacheln als Optimierung nachrüsten. |
| `react-beautiful-dnd` | Veraltet | Keine Wartung mehr; keine Mehrfach-Drag-Unterstützung. dnd-kit bzw. Atlassian `pragmatic-drag-and-drop` sind die Nachfolger. |
| Tauri/Electron als „schneller Weg“ (2–3 Wochen lt. Vorgängerplan §762) | **Widersprochen — grob unterschätzt** | Tauri spart nur Installer/Deployment, nicht den UI-Rewrite: 15–18k LOC Qt-Code müssen trotzdem in Web-Tech neu gebaut werden. Realistisch eher 8–12 Wochen auch mit Tauri, wenn identische Funktionalität gefordert ist. Tauri lohnt nur, wenn explizit **Offline-Desktop ohne Server** gefordert bleibt. |
| Next.js-Fullstack statt getrenntem FastAPI | Neutral, nicht empfohlen | Würde Python-Bestand (`rules.py`, Repositories) in TS erzwingen — verschenkt den größten Wiederverwendungshebel. Allenfalls für reines Frontend-Hosting (statt Vite-static) denkbar. |

### 3.3 Formation Editor im Detail (Pflichtenheft für die kritischste Komponente)

- **Layout:** Container-`<div>` relativ positioniert, Kacheln absolut (`left/top` aus `pixelPos()`-Port), Stagger-Offset via `margin-left`. Zellgröße 130×80 (Desktop-Konstanten übernehmen, responsiv skalieren via CSS-`transform: scale()`).
- **DnD:** `@dnd-kit/core` mit eigenem `PointerSensor` (Aktivierungs-Distanz = Desktop-`startDragDistance`-Äquivalent), `CollisionDetection: closestCenter` + eigene `canPlace`-Guard. Gruppen-Drag: selektierte IDs als `active.data.current.groupIds`, Delta-Validierung vor Commit (Desktop-`MoveGroupCommand`-Semantik).
- **Selektion:** Click (Single), Ctrl/Cmd-Click (Toggle), Shift-Click (Rechteck-Bereich), leere Fläche + Ziehen = Rubber-Band-`<div>` mit Schnitt-Test. `selection_changed`-Event → Zustand-Store.
- **Undo:** TS-Port von `core/commands.py` (`UndoStack`, max. 100 Einträge wie Desktop-`history/service.py`), synchronisiert mit Backend-Transaktionen (optimistic UI + Rollback).
- **Optimizer:** Regeln laufen **serverseitig** (Python-`RULE_REGISTRY` unverändert), Frontend zeigt `swap_count`/`cost`/`elapsed_ms` + Vorher/Nachher-Diff; „Übernehmen“ pusht einen `OptimizeFormationCommand` auf den Undo-Stack.
- **Persistenz:** `PUT /api/formations/{id}/placements` (Bulk), Autosave-Debounce 2 s + Rotation (Desktop-`autosave.py`-Semantik: max. 5 Snapshots), Recovery-Dialog bei neuerem Snapshot.
- **Primärgerät Desktop/Notebook:** DnD, Rubber-Band und Tastaturkürzel werden für Maus/Trackpad optimiert und dort abgenommen. Touch/Tablet/Handy: Kacheln ansehen und einfache Aktionen sollen funktionieren (progressive Erweiterung), aber **kein Mobile-First-Redesign** — das Raster bleibt eine Desktop-Komponente (§5.1).

### 3.4 Architektur-Reserven (eingeplant, NICHT implementiert)

Eigner-Vorgabe 2026-09-26: Die App läuft überwiegend server-seitig (Browser als primärer Client). Spätere Sänger-Selbstbedienung (eigene Stammdaten-Teile pflegen, Verfügbarkeiten per Webseite/App eintragen) wird architektonisch vorbereitet, gehört aber **nicht** zum Migrationsumfang:

- **Rollenmodell** in Schema + Auth von Anfang an vorsehen (`chorleiter`, `vorstand`, `saenger`), inkl. Scoped Permissions (Sänger sieht/schreibt nur eigene Datensätze: `PUT /api/me/availability/{event_id}` idempotent, Unique-Constraint `(singer_id, event_id)` für Concurrent-Writes).
- **Formation-Planung bleibt Single-Editor** (§5.2): kein Kollaborations-Protokoll, einfacher Versions-Check (`If-Match`/Revision) genügt.
- **Kein Code für das Sänger-Portal in M0–M5** — nur: keine Designentscheidung treffen, die es später blockiert (z. B. kein Singleton-User, keine clientseitigen Admin-Geheimnisse, keine nicht-mandantenfähigen Session-Annahmen).

---

## 4. Aufwands-Schätzung (korrigiert gegenüber Vorgängerplan)

Der Vorgängerplan widerspricht sich selbst: Executive Summary „400–700 h / 8–14 Wo“ vs. Summentabelle „320–480 h / 10–15 Wo“ (vgl. Subanalyse §3). Auf Basis der **gemessenen** 23,8k LOC (davon ~15–18k Qt-gebunden) gilt:

| Phase | Umfang | Aufwand (1 erfahrener Dev) | Risiko |
|---|---|---|---|
| **M0 Vorbereitung** | Desktop-Bugs fixen, **Duplikat-Entscheid 2026-09-26: keine Qt-Löschung, `widgets/` = Verhaltens-Spec für React-Editor (§1.4)**, Choraufstellung-Plan Phase 1–2 (Singer-Modell unifizieren, Embed), **Verzeichnisstruktur-Bereinigung (§7)**, ERD + API-Kontrakte (OpenAPI), E2E-Basis | 1–2 Wochen · 35–50 h | Niedrig |
| **M1 Backend-API** | FastAPI-Skeleton, Auth-Token, Router für singers/events/projects/availability/besetzung/repertoire/formations/export/config, Alembic-Migrationen aus `database.py`-Schema, `domain/`+`choraufstellung/core/` als Services verdrahten | 2–3 Wochen · 80–120 h | Niedrig |
| **M2 Frontend-CRUD** | App-Shell + Router + Theming (Hell/Dunkel), 6 CRUD-Tabs (Sänger/Projekte/Termine/Verfügbarkeit/Besetzung/Repertoire), Aufgaben-Wizard als Multi-Step-Form, TanStack-Table + Filter/Suche/Sortierung | 2–3 Wochen · 60–80 h | Mittel |
| **M3 Formation Editor** | §3.3 vollständig: Grid, DnD, Rubber-Band, Kontextmenü, Undo, Suche-Puls, Optimizer-Anbindung, Autosave/Recovery | 3–5 Wochen · 100–160 h | **Hoch** |
| **M4 Export/PDF/Backup** | reportlab-Endpoints (PDF-Qualitätskriterien §5.3: Zentrierung, S/W-Tauglichkeit, Schriften, Kopf), CSV/LibreOffice, JSON-Sync, Backup/Restore-UI, Update-Check-Ersatz | 1 Woche · 20–30 h | Niedrig |
| **M5 Rollen-Reserve + Deployment** | Rollenmodell als Schema/Auth-Reserve (§3.4, ohne Portal-UI), MariaDB-Schema-Migration via Alembic, Docker Compose (api + db + static-frontend), Playwright-Smoke, Doku (Benutzerhandbuch nachziehen) | 1–2 Wochen · 30–50 h | Mittel |
| **M6 (optional, nur bei Bedarf)** | PWA/Offline: Service-Worker-Cache + queued Mutations | 1 Woche · 20–40 h | Mittel |
| **Test/Puffer** | Ausbau pytest + Vitest + Playwright, Accessibility-Audit, Performance (300-Kacheln-Probe) | durchgehend · 40–60 h | — |
| **Gesamt (Kern M0–M5)** | | **10–15 Wochen (1 Dev) · 365–550 h; 6–8 Wochen (2 Devs)** | Kritischer Pfad: M1 → M3 |

Ohne Multi-User-Anspruch (Single-User-Web als 1:1-Ersatz) entfallen ca. 20–30 h aus M5 → **ca. 340–520 h**. M6 kommt nur bei nachgewiesenem Bedarf hinzu. Die alte „Tauri 2–3 Wochen“-Aussage ist gestrichen (§3.2).

### Meilensteine (Demo-fähig)

- **MS1 (nach M1):** API + OpenAPI-Docs, CRUD via Swagger, Optimizer-Regeln per `curl` aufrufbar.
- **MS2 (nach M2):** Alle CRUD-Tabs klickbar, Wizard durchgängig, Desktop parallel nutzbar (gleiche SQLite-Datei im Dev-Modus).
- **MS3 (nach M3):** Formation Editor paritätisch (Akzeptanz: Pool→Grid, Swap, Gruppen-Drag, Rubber-Band, Undo, Optimizer-Diff — je 1 Playwright-Test; Abnahme an Notebook mit Maus/Trackpad).
- **MS4 (nach M4+M5):** Docker-Compose-Release, Benutzerhandbuch aktualisiert, Desktop als Fallback noch lauffähig — erst hier Merge des Migrations-Branch nach `main` (§5.9).
- **MS0 (vor M1):** Migrations-Branch angelegt, Desktop-CI auf `main` grün, API-Kontrakt + MariaDB-Entscheidung festgezurrt.

---

## 5. Risiken & Entscheidungen (Eigner-Vorgaben 2026-09-26 eingearbeitet)

1. **Primärgerät Notebook/Desktop (kein Mobile-First):** Die App wird per Browser an Notebook/Desktop-PC mit Maus/Trackpad bedient — alle DnD- und Rubber-Band-Interaktionen werden dort abgenommen. Dass sie sich zusätzlich auf Handy/Tablet brauchbar bedienen lässt, ist erfreulich, aber **kein Design-Ziel**: kein Mobile-First-Layout, keine Touch-Neukonzeption des Rasters in M3 (nur Basistauglichkeit, keine Abnahme auf Touch).
   **Schärfung 2026-09-27 (Klick-Test):** 1:1-Port ist kein Ziel, das Web bekommt ein eigenes Benutzungskonzept (statt Menüleiste: Navigation + kontextuelle Werkzeugleisten). Handy-Scope: Dirigenten-Workflows (Editor, Matrix-Pflege) bleiben Desktop-optimiert; Handy-Nutzung = Lesen + Sänger-Selbstbedienung (Verfügbarkeit, Portal). Responsive-Basis (wrappende Nav, scrollende Tabellen) ist drin; Editor-Touch bleibt Später.
2. **Keine gleichzeitige Formation-Planung (Wahrscheinlichkeit quasi null):** Zwei Chorleiter, die gleichzeitig dieselbe Aufstellung bearbeiten, sind kein Design-Ziel — Single-Editor-Semantik mit Revisions-Check genügt, kein CRDT/OT, keine WebSockets für das Raster. **Getrennt davon:** Das Backend muss später Concurrent-Writes vieler Sänger entgegennehmen können (Verfügbarkeits-Zusagen, Stammdaten-Teile) — das wird über idempotente Pro-Sänger-Endpoints + Unique-Constraints gelöst (§3.4), betrifft die Formation-Planung aber **nicht**.
3. **Keine Maßstabstreue — dafür PDF-Qualität:** Das Raster ist auch in Qt weder maßstabsgetreu noch bemaßt, und das bleibt so (kein Design-Ziel). **Viel wichtiger** ist die Qualität der PDF-Version — Abnahmekriterien in M4: Sänger-Kurznamen sauber horizontal + vertikal in den Raster-Kacheln zentriert, Stimmgruppen-Farben auch im S/W-Druck unterscheidbar (Muster/Symbole als Rückfallebene prüfen), Schriften eingebettet, Kopf mit Projekt/Termin/Datum, keine abgeschnittenen Kacheln am Seitenrand. Referenz-PDFs Desktop-vs-Web in M4 vergleichen.
4. **Farbschema leicht änderbar, Format egal:** Ob YAML oder JSON ist vollkommen gleichgültig — Anforderung ist nur, dass Stimmgruppen-Farben (hell/dunkel) einfach konfigurier- und änderbar sind. Korrektur 2026-09-27: `voice_groups.yaml` (Gruppenliste) und `voice_groups.json` (Theme-Farben) sind **kein Inhalts-Duplikat**, nur eine Namens-Kollision; sie haben verschiedene Leser (`config.load_voice_groups` vs. `choraufstellung/config`). Zusammenführung in eine DB-Tabelle mit Admin-Pflege bleibt M1; Desktop- und Web-Farben dürfen nicht divergieren.
5. **Python 3.11/3.12 via .venv:** Die 3.9-Bindung diente historisch nur der lokalen Qt-Lauffähigkeit auf Ubuntu/Mint. Das Backend zielt auf **3.11+** (im Migrations-Branch, eigene `.venv`); der Kompat-Test `test_py39_compat.py` gilt weiter nur für den Qt-Desktop-Branch.
6. **MariaDB/MySQL server-seitig: ja, ohne gravierende Nachteile.** Antwort auf Eigner-Frage 1: SQLAlchemy + Alembic abstrahieren den Dialekt; bei dieser Größenordnung (ein Chor, 7 Tabellen, keine GIS-/Array-/Vektor-Workloads) hat MariaDB gegenüber PostgreSQL keine praxisrelevanten Nachteile. Zu beachten: Engine **InnoDB**, Charset **utf8mb4** (für `utf8mb4_unicode_ci`-Kollation), `DATETIME` statt `TIMESTAMP` für Veranstaltungszeiten (kein 2038-/TZ-Problem), JSON-Spalten sparsam einsetzen (MariaDB-Longtext-Alias beachten), `RETURNING` erst ab 10.5 — im Zweifel letzte IDs via `lastrowid` lesen. Keine PG-spezifischen Typen (`ARRAY`, `CITEXT`, `JSONB`) verwenden, dann bleibt ein späterer Wechsel zu PostgreSQL ein reiner Config-Vorgang. **Entscheidung: MariaDB** (bereits betrieben — Betriebswissen schlägt theoretische PG-Vorteile).
7. **PWA/Offline nur optional (M6):** Aufwand derzeit nicht gerechtfertigt — kein Kernbestandteil, nur bei nachgewiesenem Bedarf (z. B. netzlose Konzertsäle mit Tablet-Einsatz). Architektur versperrt den Weg nicht (API bereits offline-freundlich: Bulk-Endpoints, Revisionen).
8. **Sänger-Portal als Architektur-Reserve:** Stammdaten-Selbstpflege und Verfügbarkeits-Eintrag per Webseite/App werden mitgedacht (§3.4: Rollen, Scopes, idempotente Endpoints), aber **nicht implementiert** — kein Portal-UI, keine Sänger-Accounts-Verwaltung in M0–M5.
9. **Branch-Isolation:** Die gesamte Migration entwickelt sich in einem **eigenen Branch** (`web-migration`); der Qt-`main` bleibt bis zum Abschluss **vollständig benutzbar** (CI grün, Releases möglich). Hotfixes auf `main` werden per Cherry-Pick in den Migrations-Branch übernommen, nicht umgekehrt. Merge nach `main` erst bei MS4 (Docker-Release + abgenommene Parität).

---

## 6. Empfehlung / Next Steps

1. **M0 starten** (1–2 Wochen): Migrations-Branch `web-migration` anlegen, Duplikat-UI löschen, Singer-Modell unifizieren, Verzeichnisstruktur-Bereinigung (§7), OpenAPI-Kontrakt + MariaDB-Entscheidung festzurren. Kein Web-Code vor MS1-Vertrag.
2. **Stack wie in §3.1 beschließen** (FastAPI + React + dnd-kit + MariaDB + Docker Compose, Python 3.11/3.12). Kein Spagat mit HTMX/Canvas/Tauri, kein Mobile-First, keine Maßstabs-Neukonzeption.
3. **Formation Editor als Prototyp vorziehen** (M3-Risiko-Spike, 2–3 Tage): 1 Grid + 20 Kacheln + dnd-kit + Rubber-Band als Wegwerf-Prototype an Notebook mit Maus/Trackpad — killt das größte Risiko vor dem Full-Commit.
4. **Desktop und Web parallel betreiben** bis MS4 (gleiche JSON-/SQLite-Formate, Einweg-Bridge wiederverwenden); Merge erst bei MS4, `main` bleibt bis dahin voll benutzbar (§5.9).

---

## 7. Verzeichnisstruktur-Bereinigung (Voraussetzung in M0)

Der Altbestand hat eine historisch gewachsene, chaotische Ablagestruktur, die bei der Migration sinnvoll aufgelöst werden muss — sonst werden Pfadfehler und Namens­kollisionen in Backend und Frontend übernommen. Befund am 2026-09-25 (Repo-Root `chormanager/` = Paket `chormanager/`):

| Befund | Konkret | Maßnahme bei der Migration |
|---|---|---|
| Repo-Root und Python-Paket heißen identisch (`chormanager/chormanager/...`) | Import-Pfade, Suchen und Doku (z. B. `choraufstellung/...` vs. `chormanager/choraufstellung/...`) sind mehrdeutig; hartcodierte Pfade wie `/media/data/coding/chormanager/workdir` in `chormanager/ui/dialogs/_event_availability.py:406,439` funktionieren nur auf einem Rechner | Monorepo-Layout mit eindeutigen Top-Level-Namen: `backend/` (FastAPI, aus heutigem `chormanager/`-Paket extrahiert), `frontend/` (React), `docs/` (bleibt). Keine Pfad-Hardcodes mehr — alles über ENV/XDG-Konfiguration |
| Drei `workdir/`-Verzeichnisse | `./workdir/` (Export-Ablage, genutzt), `chormanager/workdir/` (leer, Code schrieb je nach Aufrufer hierhin), `chormanager/choraufstellung/workdir/` (1 PDF, ungetrackt) — plus absolut hartcodierter `/media/...`-Pfad in `_event_availability.py` | **Erledigt 2026-09-27 (Branch `web-migration`):** Single Source `config.get_workdir()` (Repo-Root + `workdir`), 8 Call-Sites umgestellt, Hardcode entfernt, Guard-Tests (`test_workdir_single_source.py`); Exporte im Web als Download-Endpoints statt Dateisystem-Ablage |
| Zwei `data/`-Bedeutungen + Plugin-Daten | `./data/` (Laufzeit: `chor.db`, `backups/`, `logs/`, JSON-Sync) vs. `chormanager/data/` (**Code**: `database.py`) vs. `chormanager/choraufstellung/data/` (Formations-JSONs + `backups/`) | Trennung Code vs. Laufzeitdaten: Code-Paket umbenennen (`chormanager/data/` → `backend/.../persistence/` bzw. `storage/`), Laufzeitdaten unter einen konfigurierbaren Daten-Root (`XDG_DATA_HOME/chormanager/`), Formations-JSONs in DB-Tabelle `formations` migrieren statt Dateisammlung |
| `config/` vs. `config.py` vs. `config.py` | `./config/*.yaml/json` (Laufzeit-Konfig) kollidiert namentlich mit `chormanager/config.py` (Code) und `chormanager/choraufstellung/config.py` (Plugin-Code); zusätzlich `voice_groups.yaml` (Gruppen) **und** `voice_groups.json` (Theme-Farben) mit irreführend ähnlichem Namen (kein Inhalts-Duplikat, Stand 2026-09-27) | Eindeutige Namen: `backend/config/` (Code) vs. `./config/` → `backend/settings/`-Defaults + ENV-Overrides; beide Dateien in M1 in DB-Tabellen (`voice_groups`, Theme-Farben) überführen |
| Beispieldaten im Repo (`data/*.json`, `workdir/*.pdf/.odt`) | Echte Chor-Daten (Zusagen-Listen, Exporte) liegen versioniert im Repo | Vor Migration entfernen und ggf. anonymisierte Fixtures nach `backend/tests/fixtures/` überführen; `.gitignore` für Laufzeitdaten härten |

**Erledigt im Zuge dieses Auftrags (Desktop-Bestand):** `plans/` → `docs/plans/` verschoben (28 Dateien via `git mv`, Historie erhalten), Referenzen in Code-Kommentaren (`chormanager/ui/*`, `chormanager/choraufstellung/*`, `tests/unit/*`) und Plan-Querverweisen auf `docs/plans/` aktualisiert, Root-`AGENTS.md`-Index und `docs/AGENTS.md` (neuer Child-Eintrag `docs/plans/`) nachgezogen.

**Akzeptanz für M0:** `find . -maxdepth 2 -type d` zeigt keine doppelten Bedeutungen mehr; kein absoluter Pfad unter `/media/` im Code (`grep -rn "/media/" backend/ frontend/` leer); `git status` sauber; Desktop-Tests grün.

*Geprüft gegen: `README.md`, `pyproject.toml`, `requirements.txt`, `chormanager/data/database.py`, `chormanager/choraufstellung/widgets/formation_grid.py`, `chormanager/choraufstellung/core/rules.py`, `docs/plans/2026-06-11_web-migration.md`, `docs/plans/2026-06-11_choraufstellung-migration.md`, `docs/technical-documentation.md`.*
