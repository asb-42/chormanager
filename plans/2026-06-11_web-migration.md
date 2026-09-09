# ChorManager Web Migration Plan

**Date:** 2026-06-11
**Status:** Proposed
**Scope:** Full migration from PyQt6 desktop application to web-based technology stack

---

## Executive Summary

Migrating ChorManager from a PyQt6 desktop app to a web application is a **significant undertaking** requiring approximately **8-14 weeks** for a single experienced developer, or **4-7 weeks** for a two-person team. The total estimated effort is **400-700 hours**.

The hardest part is not the backend or standard CRUD UI — it's the **interactive formation grid** (`choraufstellung`) which relies heavily on desktop-specific features: custom painting, absolute positioning, drag-and-drop with mime data, rubber-band selection, and undo/redo stacks. This component alone represents ~30-40% of the total migration effort.

| Component | Desktop (Current) | Web (Target) | Migration Effort |
|-----------|-------------------|--------------|:---:|
| Database | SQLite | PostgreSQL (or SQLite via Litestream) | Low |
| Backend API | None (direct DB) | FastAPI + SQLAlchemy | Medium |
| Domain models | Python dataclasses | Shared Python (backend) | Low |
| CRUD UI (tables, forms, dialogs) | PyQt6 widgets | React/Vue components | Medium |
| Formation grid (drag-and-drop) | QWidget + QDrag + QUndoStack | HTML5 Canvas/SVG + JS DnD | **High** |
| PDF export | ReportLab (desktop) | ReportLab (backend) or jsPDF | Low |
| CSV/LibreOffice export | Desktop file dialog | Browser download | Low |
| Theme switching | Inline stylesheets | CSS variables / Tailwind | Low |
| Authentication | None (local app) | Optional (JWT/session) | Medium |

---

## Current Architecture Analysis

### What Exists Today

```
chormanager/
├── data/database.py          # SQLite connection + schema (242 lines)
├── domain/
│   ├── models.py             # 6 dataclasses: Singer, Event, Project, etc. (324 lines)
│   └── repository.py         # 6 repository classes (655 lines)
├── core/export_service.py    # CSV, LibreOffice export (135 lines)
├── history/service.py        # Undo/redo commands (194 lines)
├── backup/service.py         # File backup (172 lines)
├── export/                   # ZIP backup, sync, portability (469 lines)
├── config.py                 # YAML config, state management (205 lines)
├── ui/                       # PyQt6 UI layer (~6,500 lines total)
│   ├── main_window.py        # 2,925 lines — the god-class
│   ├── dialogs.py            # 1,824 lines — all dialogs
│   ├── views/                # Tab views (~2,000 lines)
│   └── export_dialog.py      # Export format selection
└── choraufstellung/          # Formation editor plugin (~5,500 lines)
    ├── core/                 # Grid engine, optimizer, rules, commands
    ├── ui/                   # Grid widget, pool widget, dialogs
    ├── storage.py            # JSON persistence
    └── pdf_export.py         # PDF generation
```

### Key Technical Dependencies

| Dependency | Usage | Web Equivalent |
|------------|-------|----------------|
| `PyQt6` | All UI | React, Vue, or Svelte |
| `sqlite3` | Database | PostgreSQL, MySQL, or SQLite (via Litestream/SQLite Cloud) |
| `PyYAML` | Config files | JSON config or environment variables |
| `ReportLab` | PDF generation | Same (backend) or jsPDF (client) |
| `PyQt6.QtGui.QDrag` | Drag-and-drop | HTML5 Drag and Drop API |
| `PyQt6.QRubberBand` | Selection rectangles | Canvas/SVG selection or library |
| `PyQt6.QUndoStack` | Undo/redo | Custom JS undo manager |
| `subprocess` | LibreOffice conversion | Backend API or pandoc |
| `pathlib` / `os` | File I/O | Server-side file system or object storage |

### What Transfers Easily to Web

The **entire domain layer** transfers almost unchanged:

- `domain/models.py` — Python dataclasses, no PyQt dependency
- `domain/repository.py` — SQLAlchemy can replace raw SQLite with minimal changes
- `core/export_service.py` — Pure Python, no UI dependency
- `history/service.py` — Pure Python command pattern (the command classes, not the Qt integration)
- `backup/service.py` — Pure Python file operations
- `config.py` — Pure Python YAML/JSON handling
- `choraufstellung/core/` — Grid engine, optimizer, rules are pure Python math

**~2,500 lines of pure business logic transfer directly.**

### What Must Be Rewritten

- `ui/main_window.py` (2,925 lines) — entire UI
- `ui/dialogs.py` (1,824 lines) — all dialogs
- `ui/views/` (~2,000 lines) — all tab views
- `choraufstellung/ui/` (~1,800 lines) — formation grid, pool widget
- `choraufstellung/main.py` (2,180 lines) — standalone app (partially reusable)

**~10,700 lines of UI code must be rewritten.**

---

## Target Architecture

### Option A: Monolith (Recommended for this project)

```
┌─────────────────────────────────────────────────────────────┐
│                        Browser                               │
│  ┌───────────────────────────────────────────────────────┐   │
│  │  React/Vue SPA                                        │   │
│  │                                                       │   │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌──────────┐   │   │
│  │  │Projects │ │Singers  │ │Events   │ │Formation │   │   │
│  │  │  View   │ │  View   │ │  View   │ │  Editor  │   │   │
│  │  └────┬────┘ └────┬────┘ └────┬────┘ └────┬─────┘   │   │
│  │       │           │           │            │          │   │
│  │       └───────────┴───────────┴────────────┘          │   │
│  │                       │                               │   │
│  │              REST API calls                           │   │
│  └───────────────────────┼───────────────────────────────┘   │
└──────────────────────────┼──────────────────────────────────┘
                           │ HTTP/JSON
┌──────────────────────────┼──────────────────────────────────┐
│  FastAPI Backend         │                                   │
│  ┌───────────────────────┴───────────────────────────────┐  │
│  │  API Routes                                           │  │
│  │  /api/singers    /api/events    /api/formations       │  │
│  │  /api/projects   /api/availability  /api/export       │  │
│  └───────────────────────┬───────────────────────────────┘  │
│                          │                                   │
│  ┌───────────────────────┴───────────────────────────────┐  │
│  │  Domain Layer (REUSED from desktop app)                │  │
│  │  models.py  repository.py  export_service.py          │  │
│  └───────────────────────┬───────────────────────────────┘  │
│                          │                                   │
│  ┌───────────────────────┴───────────────────────────────┐  │
│  │  Database: PostgreSQL (or SQLite via Litestream)       │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### Option B: Server-Side Rendering (Simpler, less interactive)

Use Django with Django REST Framework and htmx or Alpine.js. The formation grid would be less interactive but simpler to implement. Not recommended for this project because the formation editor requires rich interactivity.

### Option C: Electron/Tauri (Desktop wrapper around web code)

Package the web app as a desktop app using Tauri (Rust-based, smaller than Electron). This preserves the desktop experience while using web technologies internally. Good if you want both desktop and web from one codebase.

**Recommendation:** Option A (monolith) for maximum flexibility, or Option C (Tauri) if desktop distribution is still needed.

---

## Phase 1: Backend API

**Goal:** Create a REST API that exposes all current functionality.
**Effort:** ~2-3 weeks (~80-120 hours)
**Risk:** Low — the domain layer transfers directly

### 1.1 Technology Stack

| Component | Choice | Rationale |
|-----------|--------|-----------|
| Framework | **FastAPI** | Async, auto-generated OpenAPI docs, Python ecosystem |
| ORM | **SQLAlchemy 2.0** | Mature, maps well from current repository pattern |
| Database | **PostgreSQL** | Production-ready, JSON support for flexible fields |
| Migrations | **Alembic** | Standard SQLAlchemy migration tool |
| Auth | **None initially** | Desktop app has no auth; add later if needed |

### 1.2 API Design

```
# Projects
GET    /api/projects                 # List all
GET    /api/projects/{id}            # Get one
POST   /api/projects                 # Create
PUT    /api/projects/{id}            # Update
DELETE /api/projects/{id}            # Delete

# Singers
GET    /api/singers                  # List all (with filters)
GET    /api/singers/{id}             # Get one
POST   /api/singers                  # Create
PUT    /api/singers/{id}             # Update
DELETE /api/singers/{id}             # Delete
GET    /api/singers/search?q=        # Search

# Events
GET    /api/events                   # List all (with filters)
GET    /api/events/{id}              # Get one
POST   /api/events                   # Create
PUT    /api/events/{id}              # Update
DELETE /api/events/{id}              # Delete

# Availability
GET    /api/events/{id}/availability           # Get all availability
PUT    /api/events/{id}/availability/{singer_id}  # Update status

# Besetzung (Lineups)
GET    /api/besetzungen              # List all
GET    /api/besetzungen/{id}         # Get one
POST   /api/besetzungen              # Create
PUT    /api/besetzungen/{id}         # Update
DELETE /api/besetzungen/{id}         # Delete

# Repertoire
GET    /api/repertoire               # List all
GET    /api/repertoire/{id}          # Get one
POST   /api/repertoire               # Create
PUT    /api/repertoire/{id}          # Update
DELETE /api/repertoire/{id}          # Delete

# Formations (Choraufstellung)
GET    /api/formations               # List all saved formations
GET    /api/formations/{id}          # Get one
POST   /api/formations               # Save formation
PUT    /api/formations/{id}          # Update formation
DELETE /api/formations/{id}          # Delete formation

# Export
POST   /api/export/csv               # Export to CSV
POST   /api/export/pdf               # Export to PDF
POST   /api/export/libreoffice       # Export to LibreOffice format

# Configuration
GET    /api/config/voice-groups      # Get voice groups
GET    /api/config/fields            # Get field definitions
GET    /api/config/app               # Get app config
```

### 1.3 Migration from Current Repository Pattern

The current `repository.py` uses raw SQL via `sqlite3`. SQLAlchemy replaces this cleanly:

```python
# Current (repository.py)
class SingerRepository:
    def get_all(self) -> List[Singer]:
        cols = self._cols(self._SINGER_COLS)
        result = self.db.execute(f"SELECT {cols} FROM singers ORDER BY full_name")
        return [Singer(**dict(row)) for row in result.fetchall()]

# Target (SQLAlchemy)
class SingerRepository:
    def get_all(self) -> List[Singer]:
        return self.db.query(SingerModel).order_by(SingerModel.full_name).all()
```

The current `Database` class (242 lines) is replaced by SQLAlchemy's `Session`. The `create_tables()` method (schema DDL) is replaced by Alembic migrations.

### 1.4 Files to Create

```
backend/
├── main.py                 # FastAPI app entry point
├── database.py             # SQLAlchemy engine, session
├── models/                 # SQLAlchemy ORM models
│   ├── singer.py
│   ├── event.py
│   ├── project.py
│   ├── availability.py
│   ├── besetzung.py
│   └── repertoire.py
├── repositories/           # Data access layer
│   ├── singer_repository.py
│   ├── event_repository.py
│   └── ...
├── routes/                 # API route handlers
│   ├── singers.py
│   ├── events.py
│   ├── projects.py
│   ├── availability.py
│   ├── formations.py
│   └── export.py
├── services/               # Business logic (REUSED from desktop)
│   ├── export_service.py   # From core/export_service.py
│   ├── backup_service.py   # From backup/service.py
│   └── history_service.py  # From history/service.py
├── schemas/                # Pydantic request/response models
│   ├── singer.py
│   ├── event.py
│   └── ...
├── config.py               # App configuration
└── migrations/             # Alembic migrations
```

### Files Reused Directly (no changes needed)

| Desktop File | Web File | Notes |
|--------------|----------|-------|
| `domain/models.py` | `backend/services/models.py` | Dataclasses, no PyQt dependency |
| `core/export_service.py` | `backend/services/export_service.py` | Pure Python CSV/HTML export |
| `history/service.py` | `backend/services/history_service.py` | Command pattern, pure Python |
| `backup/service.py` | `backend/services/backup_service.py` | File operations |
| `export/sync.py` | `backend/services/sync.py` | JSON/CSV export |
| `config.py` | `backend/config.py` | YAML loading |

---

## Phase 2: Frontend — Core UI Framework

**Goal:** Set up the frontend framework and implement standard CRUD views.
**Effort:** ~2-3 weeks (~60-80 hours)
**Risk:** Medium — requires frontend expertise

### 2.1 Technology Stack

| Component | Choice | Rationale |
|-----------|--------|-----------|
| Framework | **React** (or Vue 3) | Largest ecosystem, component-based |
| State Management | **Zustand** (React) or **Pinia** (Vue) | Lightweight, simple |
| UI Library | **shadcn/ui** or **Ant Design** | Pre-built table, form, dialog components |
| Styling | **Tailwind CSS** | Utility-first, supports dark mode |
| Data Fetching | **TanStack Query** (React Query) | Caching, optimistic updates |
| Forms | **React Hook Form** + **Zod** | Validation, type-safe |
| PDF Download | **jsPDF** (client) or backend endpoint | For client-side PDF generation |

### 2.2 Core Layout

```tsx
// App.tsx — Main layout matching current sidebar navigation
function App() {
  return (
    <div className="flex h-screen">
      <Sidebar />          {/* Projects, Singers, Besetzung, Events, Formation, Repertoire */}
      <div className="flex-1 flex flex-col">
        <InfoBar />        {/* Active project/event/besetzung display */}
        <ContextToolbar /> {/* Dynamic actions based on current view */}
        <main className="flex-1 overflow-auto">
          <Routes>
            <Route path="/projects" element={<ProjectsView />} />
            <Route path="/singers" element={<SingersView />} />
            <Route path="/besetzung" element={<BesetzungView />} />
            <Route path="/events" element={<EventsView />} />
            <Route path="/formation" element={<FormationView />} />
            <Route path="/repertoire" element={<RepertoireView />} />
          </Routes>
        </main>
      </div>
    </div>
  );
}
```

### 2.3 Standard CRUD Views

Each view follows the same pattern (direct translation from current PyQt6 tabs):

| Desktop (PyQt6) | Web (React) | Notes |
|-----------------|-------------|-------|
| `QTableWidget` | `<DataTable />` from shadcn/ui | Sorting, filtering, pagination |
| `QLineEdit` search | `<Input />` with debounced onChange | Same behavior |
| `QComboBox` filter | `<Select />` | Same behavior |
| `QDialog` | `<Dialog />` from shadcn/ui | Modal overlay |
| `QFormLayout` | `<Form />` with validation | React Hook Form |
| `QPushButton` | `<Button />` | Click handlers |
| `QMessageBox` | `<Alert />` or toast notifications | Feedback |

### 2.4 Effort per View

| View | Desktop Lines | Web Estimated | Notes |
|------|-------------:|---------------:|-------|
| Projects | 405 | ~200 lines | Table + dialog + search |
| Singers | 390 | ~250 lines | Table + dialog + filters + age computation |
| Events | 425 | ~250 lines | Table + dialog + project filter |
| Besetzung | 286 | ~200 lines | Table + singer selection dialog |
| Repertoire | 217 | ~150 lines | Table + dialog |
| Info bar | ~80 | ~50 lines | Simple display component |
| Context toolbar | ~270 | ~100 lines | Dynamic action bar |
| Sidebar + routing | ~150 | ~80 lines | Navigation |
| **Total CRUD** | **~2,223** | **~1,280** | |

---

## Phase 3: Formation Editor (The Hard Part)

**Goal:** Recreate the interactive choir formation grid in the browser.
**Effort:** ~3-5 weeks (~100-160 hours)
**Risk:** **High** — most complex component, requires deep frontend expertise

### 3.1 Why This Is Hard

The current formation editor uses desktop-specific features that have no direct web equivalent:

| Desktop Feature | Implementation | Web Equivalent |
|-----------------|----------------|----------------|
| **Grid rendering** | `QWidget` child positioning with `setGeometry()` | HTML5 Canvas, SVG, or CSS Grid |
| **Singer tiles** | `SingerTile(QFrame)` with `setStyleSheet()` | React components with CSS |
| **Drag and drop** | `QDrag` + `QMimeData` + `drag.exec()` | HTML5 Drag and Drop API or `react-dnd` |
| **Rubber band selection** | `QRubberBand` on `QWidget` | Canvas selection rectangle (custom) |
| **Multi-select** | `Ctrl+Click` toggling `selected_ids` set | Same (click handler + state) |
| **Group drag** | Drag multiple selected tiles together | Same (track delta, apply to all) |
| **Undo/redo** | `QUndoStack` + `QUndoCommand` subclasses | Custom undo manager (e.g., `immutable.js`) |
| **Context menu** | `QMenu` on right-click | `<ContextMenu />` component |
| **Drop target** | `dropEvent` on `FormationGrid` | `onDrop` handler on container |
| **Grid cells** | `QFrame` with `setFrameShape()` | CSS borders/backgrounds |
| **Staggered layout** | Manual x-offset calculation | Same math, CSS transforms |
| **Pulse animation** | `QTimer` + stylesheet toggle | CSS `@keyframes` animation |

### 3.2 Recommended Approach: Canvas vs SVG vs DOM

| Approach | Pros | Cons | Recommendation |
|----------|------|------|:---:|
| **HTML5 Canvas** | Fast rendering, full control | No DOM events on elements, harder text rendering | |
| **SVG** | DOM-based, events on elements, scalable | Performance with many elements | |
| **CSS Grid + DOM** | Native events, accessible, easy styling | Absolute positioning harder, layout limits | **Recommended** |
| **Hybrid (DOM + Canvas overlay)** | Best of both | Complexity | |

**Recommendation:** Use **DOM-based approach** with CSS transforms for positioning. Each singer tile is a React component positioned absolutely within a container. This gives native event handling, accessibility, and easy styling.

### 3.3 Component Architecture

```
formation-editor/
├── FormationEditor.tsx          # Main container
├── FormationGrid.tsx            # Grid with cells and positioned tiles
├── SingerTile.tsx               # Individual singer card (draggable)
├── SingerPool.tsx               # Unplaced singers list (drag source)
├── GridControls.tsx             # Rows/cols inputs, stagger toggle
├── SearchBar.tsx                # Singer search with highlight
├── Legend.tsx                   # Voice group color legend
├── context-menu.tsx             # Right-click context menu
├── hooks/
│   ├── useDragAndDrop.ts        # DnD logic
│   ├── useSelection.ts          # Multi-select + rubber band
│   ├── useUndoRedo.ts           # Undo/redo stack
│   └── useFormation.ts          # Formation state management
├── utils/
│   ├── grid-math.ts             # Coordinate calculations (from grid_engine.py)
│   ├── optimizer.ts             # Optimizer rules (from optimizer.py + rules.py)
│   └── auto-arrange.ts          # Arrangement algorithms
└── types/
    └── singer.ts                # TypeScript types
```

### 3.4 Key Implementation Details

#### Singer Tile (DOM-based)

```tsx
// SingerTile.tsx
function SingerTile({ singer, position, isSelected, onRemove, onEdit }) {
  const color = getVoiceGroupColor(singer.voiceGroup);
  
  return (
    <div
      className={`absolute w-[120px] h-[60px] rounded border cursor-move
        ${isSelected ? 'border-4 border-blue-600' : 'border border-gray-400'}`}
      style={{
        backgroundColor: color,
        left: position.col * CELL_WIDTH + MARGIN_LEFT,
        top: position.row * CELL_HEIGHT + MARGIN_TOP,
      }}
      draggable
      onDragStart={handleDragStart}
    >
      <span className="font-bold text-xs">{singer.name}</span>
      <span className="text-[8pt]">{singer.voiceGroup}</span>
      {singer.height > 0 && <span className="text-[7pt]">{singer.height} cm</span>}
    </div>
  );
}
```

#### Drag and Drop

```tsx
// useDragAndDrop.ts
function useDragAndDrop(gridRef, singers, onDrop) {
  const handleDrop = useCallback((e: DragEvent) => {
    e.preventDefault();
    const sid = e.dataTransfer.getData('text/plain');
    const rect = gridRef.current.getBoundingClientRect();
    const row = Math.floor((e.clientY - rect.top - MARGIN_TOP) / CELL_HEIGHT);
    const col = Math.floor((e.clientX - rect.left - MARGIN_LEFT) / CELL_WIDTH);
    onDrop(sid, row, col);
  }, [onDrop]);
  
  return { handleDrop };
}
```

#### Undo/Redo

```ts
// useUndoRedo.ts
function useUndoRedo() {
  const [undoStack, setUndoStack] = useState<Command[]>([]);
  const [redoStack, setRedoStack] = useState<Command[]>([]);
  
  const execute = (command: Command) => {
    command.execute();
    setUndoStack(prev => [...prev, command]);
    setRedoStack([]);  // Clear redo on new action
  };
  
  const undo = () => {
    const cmd = undoStack[undoStack.length - 1];
    if (cmd) {
      cmd.undo();
      setUndoStack(prev => prev.slice(0, -1));
      setRedoStack(prev => [...prev, cmd]);
    }
  };
  
  const redo = () => {
    const cmd = redoStack[redoStack.length - 1];
    if (cmd) {
      cmd.redo();
      setRedoStack(prev => prev.slice(0, -1));
      setUndoStack(prev => [...prev, cmd]);
    }
  };
  
  return { execute, undo, redo, canUndo: undoStack.length > 0, canRedo: redoStack.length > 0 };
}
```

#### Optimizer (port from Python to TypeScript)

The optimizer logic (`choraufstellung/core/optimizer.py` + `rules.py`) is ~760 lines of pure Python math. It can be ported to TypeScript with a 1:1 translation:

```typescript
// utils/optimizer.ts
export function runOptimizer(
  singers: Singer[],
  gridRows: number,
  gridCols: number,
  ruleIds: string[]
): void {
  // Direct port of optimizer.py:FormationOptimizer.run()
  // Same algorithm, different syntax
}
```

### 3.5 Effort Breakdown for Formation Editor

| Component | Desktop Lines | Web Estimated | Hours |
|-----------|-------------:|---------------:|------:|
| FormationGrid rendering | 300 | ~150 | 16 |
| SingerTile component | 120 | ~80 | 8 |
| SingerPool (table + DnD) | 463 | ~200 | 20 |
| Drag and drop system | 200 | ~150 | 24 |
| Multi-select + rubber band | 150 | ~120 | 16 |
| Undo/redo | 205 | ~80 | 12 |
| Auto-arrange algorithms | 300 | ~150 | 16 |
| Optimizer (port from Python) | 760 | ~400 | 32 |
| Context menus | 100 | ~50 | 4 |
| Search + highlight pulse | 80 | ~40 | 4 |
| Grid controls (rows/cols) | 50 | ~30 | 4 |
| Legend | 30 | ~20 | 2 |
| **Total Formation Editor** | **~2,758** | **~1,470** | **~158** |

---

## Phase 4: Export & PDF

**Goal:** Implement PDF, CSV, and LibreOffice export in the web version.
**Effort:** ~1 week (~20-30 hours)
**Risk:** Low

### 4.1 PDF Export

**Option A: Server-side (recommended)**
Keep ReportLab on the backend. Create an API endpoint that generates PDF and returns it as a download.

```python
# backend/routes/export.py
@router.post("/export/pdf")
async def export_pdf(request: PDFExportRequest):
    pdf_bytes = generate_pdf(request.formation_id, request.settings)
    return Response(content=pdf_bytes, media_type="application/pdf",
                    headers={"Content-Disposition": "attachment; filename=formation.pdf"})
```

**Option B: Client-side**
Use `jsPDF` or `pdfmake` in the browser. Simpler but limited formatting.

### 4.2 CSV/LibreOffice Export

Same as PDF — generate on backend, return as download. The current `ExportService` transfers directly.

### 4.3 Availability Export

The `EventAvailabilityDialog._export_pdf` and `_export_availability` methods (lines 704-972 of `dialogs.py`) translate to a backend endpoint. The ReportLab code can be reused almost verbatim.

---

## Phase 5: Deployment & Infrastructure

**Goal:** Deploy the web application.
**Effort:** ~1 week (~20-30 hours)
**Risk:** Low

### 5.1 Deployment Options

| Option | Complexity | Cost | Best For |
|--------|:---:|:---:|----------|
| **Docker Compose** | Low | Free (self-hosted) | Small teams, local network |
| **Fly.io** | Low | ~$5-20/month | Small deployment, easy setup |
| **Railway** | Low | ~$5-20/month | Similar to Fly.io |
| **AWS ECS/Fargate** | Medium | Variable | Scalable deployment |
| **Kubernetes** | High | Variable | Large scale |

**Recommendation:** Docker Compose for initial deployment. The app is a single PostgreSQL instance + a Python API + a static React build.

### 5.2 Docker Compose Setup

```yaml
# docker-compose.yml
version: '3.8'
services:
  db:
    image: postgres:16
    environment:
      POSTGRES_DB: chormanager
      POSTGRES_USER: chormanager
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - pgdata:/var/lib/postgresql/data
  
  api:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql://chormanager:${DB_PASSWORD}@db:5432/chormanager
    depends_on:
      - db
  
  web:
    build: ./frontend
    ports:
      - "3000:80"
    depends_on:
      - api

volumes:
  pgdata:
```

### 5.3 Data Migration

Migrate existing SQLite data to PostgreSQL:

```python
# migration script
import sqlite3
import psycopg2

# Read from SQLite
sqlite_conn = sqlite3.connect("data/chor.db")
# Write to PostgreSQL
pg_conn = psycopg2.connect("postgresql://...")
# Transfer tables: singers, events, projects, availability, besetzung, repertoire
```

---

## Effort Summary

### By Phase

| Phase | Description | Hours | Weeks (1 dev) | Weeks (2 devs) |
|-------|-------------|------:|:---:|:---:|
| 1 | Backend API (FastAPI + SQLAlchemy) | 80-120 | 2-3 | 1-2 |
| 2 | Frontend Core (CRUD views) | 60-80 | 2-3 | 1-2 |
| 3 | Formation Editor (grid + DnD) | 100-160 | 3-5 | 2-3 |
| 4 | Export (PDF, CSV) | 20-30 | 1 | 0.5 |
| 5 | Deployment | 20-30 | 1 | 0.5 |
| — | Testing & Polish | 40-60 | 1-2 | 1 |
| — | **Total** | **320-480** | **10-15** | **6-9** |

### By Component

| Component | Current Lines | Web Lines (est.) | Transfer Ratio |
|-----------|-------------:|------------------:|:---:|
| Domain models | 324 | ~300 | 90% (reuse) |
| Repository layer | 655 | ~400 | 60% (SQLAlchemy rewrite) |
| Business logic services | 500 | ~450 | 90% (reuse) |
| Config | 205 | ~150 | 70% (reuse) |
| Database schema/migrations | 242 | ~300 | 0% (new Alembic migrations) |
| CRUD UI (all views) | 2,223 | ~1,280 | 0% (rewrite) |
| Formation editor | 2,758 | ~1,470 | 0% (rewrite) |
| Dialogs | 1,824 | ~800 | 0% (rewrite) |
| Main window/layout | 2,925 | ~400 | 0% (rewrite) |
| PDF generation | 257 | ~200 | 80% (reuse on backend) |
| Export services | 469 | ~400 | 85% (reuse) |
| Backup services | 325 | ~300 | 90% (reuse) |
| **Total** | **~20,700** | **~6,450** | **~40% reuse** |

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Formation grid DnD complexity | High — could take 2x estimated time | Start with simplified version; add features incrementally |
| Loss of desktop-specific UX | Medium — drag-and-drop feels different in browser | Use library like `@dnd-kit/core` for polished DnD |
| PDF formatting differences | Low — ReportLab on backend produces identical output | Test PDF output against current desktop PDFs |
| Data migration errors | Medium — corrupting existing data | Write comprehensive migration tests; keep SQLite backup |
| Performance with large choirs | Low — web apps handle 100s of items easily | Add pagination if needed; formation grid is the bottleneck |
| Browser compatibility | Low — modern browsers support all needed APIs | Test on Chrome, Firefox, Safari; use autoprefixer |

---

## Recommended Migration Strategy

### Phase 0: Preparation (1 week)

Before starting the migration:

1. **Fix critical bugs** from the code review (hardcoded paths, Project model duplicate, etc.)
2. **Complete Phase 1-2 of the Choraufstellung plugin migration** (unify Singer model, embed as widget) — this cleans up the codebase and makes the domain layer easier to port
3. **Write integration tests** for all repository methods — these become the API test suite
4. **Document the database schema** — create an ERD diagram

### Incremental Migration (Recommended)

Don't rewrite everything at once. Migrate incrementally:

1. **Start with the backend API** — expose existing functionality via REST endpoints
2. **Build a simple web UI for one view** (e.g., Singers) — prove the architecture works
3. **Add views incrementally** — one tab at a time
4. **Build the formation editor last** — it's the hardest and most独立 component
5. **Run desktop and web in parallel** during migration — same database, both work

This approach:
- Delivers value early (API + one view working in ~3 weeks)
- Reduces risk (can stop at any point and have a partially-working web app)
- Allows testing against the desktop app (same data, compare behavior)

---

## Alternative: Don't Migrate — Hybrid Approach

Before committing to a full migration, consider whether a **hybrid approach** might be sufficient:

| Need | Solution |
|------|----------|
| Remote access | Tauri (webview in desktop app) or SSH + X11 forwarding |
| Multi-user access | Keep desktop app, add sync via API (already partially implemented in `export/sync.py`) |
| Mobile access | Build a thin mobile app that reads the same SQLite database |
| Cross-platform | Tauri builds for Linux, macOS, Windows from same codebase |

The current app already has export/sync functionality (`export/sync.py`) that could be extended into a lightweight API without rewriting the entire UI.

---

## Decision Framework

| If you need... | Then... |
|----------------|---------|
| Same app, multiple machines | **Tauri** (desktop wrapper) — ~2-3 weeks |
| Multi-user real-time collaboration | **Full web migration** — ~10-15 weeks |
| Mobile companion app | **REST API + mobile app** — ~4-6 weeks |
| Just remote access | **SSH + X11** or **Apache Guacamole** — ~1 day |
| Simpler deployment | **Docker + current app** — ~1 week |

---

## Conclusion

A full web migration is feasible but substantial (~400-700 hours). The domain layer (~2,500 lines) transfers cleanly. The CRUD UI (~2,200 lines) is a straightforward rewrite. The formation editor (~2,758 lines) is the critical path — it requires deep frontend expertise and careful implementation of drag-and-drop, selection, and undo/redo.

**If the primary goal is multi-user access**, consider a hybrid approach: build a REST API backend and a thin web UI for the CRUD views, while keeping the formation editor as a desktop component (or Tauri webview). This reduces the migration effort by ~40% while delivering the most value.

**If the primary goal is eliminating desktop deployment**, Tauri is the fastest path (~2-3 weeks) and preserves all existing functionality.
