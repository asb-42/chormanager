# ChorManager - Technical Documentation

## 1. Technology Stack

### Core Technologies
- **Python 3.8+**: Primary programming language
- **PyQt6**: GUI framework (Qt 6 bindings for Python)
- **SQLite 3**: Embedded relational database
- **PyYAML**: Configuration file parsing
- **reportlab**: PDF generation and export

### Development Tools
- **pytest**: Testing framework with pytest-qt for UI tests
- **hypothesis**: Property-based testing
- **ruff**: Python linter and formatter

### External Integrations
- **LibreOffice**: Export to Writer (.odt) and Calc (.ods)
- **Choraufstellung App**: Integrated choir arrangement tool (separate module in `choraufstellung/`)

---

## 2. Architecture Overview

```
chormanager/
├── config/                  # YAML configuration files
│   ├── voice_groups.yaml   # Voice group definitions
│   ├── fields.yaml        # Dynamic singer fields
│   └── app.yaml           # Application settings
├── data/                   # Database layer
│   └── database.py        # SQLite connection & schema
├── domain/                 # Business logic
│   ├── models.py          # Dataclasses (Singer, Event, Project, etc.)
│   └── repository.py      # Data access layer (CRUD operations)
├── ui/                     # PyQt6 UI components
│   ├── main_window.py     # Application shell
│   ├── dialogs.py        # All dialog windows
│   ├── export_dialog.py   # Export configuration dialog
│   └── views/            # Tab views
│       ├── singers_tab.py
│       ├── events_tab.py
│       ├── projects_tab.py
│       ├── repertoire_tab.py
│       ├── besetzung_tab.py
│       └── choraufstellung_tab.py
├── export/                 # Export services
│   ├── backup_service.py  # Backup creation/restoration
│   ├── portability.py     # Data portability (ZIP export/import)
│   └── chormanager_db.py # Direct DB access for Choraufstellung
├── backup/                 # Backup management
│   └── service.py
├── history/                # Undo/Redo system
│   └── service.py
├── choraufstellung/        # Integrated arrangement app
│   ├── main.py
│   ├── optimizer.py       # Grid placement algorithm
│   └── ui/               # Arrangement UI components
└── tests/
    ├── unit/              # Unit tests (mocked DB)
    ├── integration/        # Integration tests
    └── gui/               # UI tests (pytest-qt)
```

### Architectural Principles
1. **No global state**: Dependency injection via constructors
2. **Core vs UI separation**: `domain/` contains pure Python (no Qt imports)
3. **QUndoCommand pattern**: All state changes use undo/redo commands
4. **TDD workflow**: Tests written before implementation (RED-GREEN-REFACTOR)

---

## 3. Database Schema

### Tables

#### **singers**
| Column | Type | Description |
|--------|------|-------------|
| id | TEXT PK | UUID primary key |
| full_name | TEXT NOT NULL | Singer's full name |
| short_name | TEXT | Short name/nickname |
| birth_date | TEXT | ISO format date |
| voice_group | TEXT | Voice group (e.g., "Sopran 1") |
| email | TEXT | Email address |
| phone | TEXT | Phone number |
| street | TEXT | Street address |
| postal_code | TEXT | Postal code |
| city | TEXT | City |
| gender | TEXT | Gender |
| guardian1 | TEXT | First guardian name |
| guardian1_phone | TEXT | First guardian phone |
| guardian2 | TEXT | Second guardian name |
| guardian2_phone | TEXT | Second guardian phone |
| social_contacts | TEXT | JSON-encoded social media contacts |
| joined_year | INTEGER | Year joined |
| joined_month | INTEGER | Month joined |
| left_year | INTEGER | Year left (NULL if active) |
| left_month | INTEGER | Month left |
| affinity_uuid | TEXT FK | UUID of affinity partner singer |
| created_at | TEXT NOT NULL | ISO timestamp |
| updated_at | TEXT NOT NULL | ISO timestamp |

#### **events**
| Column | Type | Description |
|--------|------|-------------|
| id | TEXT PK | UUID primary key |
| name | TEXT NOT NULL | Event name |
| date | TEXT NOT NULL | ISO format date |
| event_type | TEXT NOT NULL | Type: GP, OP, SOFA, Probe, Konzert, Auftritt |
| location | TEXT | Event location |
| description | TEXT | Event description |
| project_id | TEXT FK | References projects(id) ON DELETE SET NULL |
| created_at | TEXT NOT NULL | ISO timestamp |
| updated_at | TEXT NOT NULL | ISO timestamp |

#### **projects**
| Column | Type | Description |
|--------|------|-------------|
| id | TEXT PK | UUID primary key |
| name | TEXT NOT NULL | Project name |
| description | TEXT | Project description |
| is_active | INTEGER | 1 if active, 0 otherwise |
| spielzeit | TEXT | Season (e.g., "2025/26") |
| created_at | TEXT NOT NULL | ISO timestamp |
| updated_at | TEXT NOT NULL | ISO timestamp |

#### **availability**
| Column | Type | Description |
|--------|------|-------------|
| id | TEXT PK | UUID primary key |
| singer_id | TEXT FK | References singers(id) ON DELETE CASCADE |
| event_id | TEXT FK | References events(id) ON DELETE CASCADE |
| status | TEXT NOT NULL | yes/no/none/conditional/unknown/maybe |
| created_at | TEXT NOT NULL | ISO timestamp |
| updated_at | TEXT NOT NULL | ISO timestamp |
| UNIQUE(singer_id, event_id) | | Composite unique constraint |

#### **besetzung** (Lineups)
| Column | Type | Description |
|--------|------|-------------|
| id | TEXT PK | UUID primary key |
| name | TEXT NOT NULL | Lineup name |
| project_id | TEXT FK | References projects(id) ON DELETE SET NULL |
| singer_ids | TEXT | JSON array of singer UUIDs |
| created_at | TEXT NOT NULL | ISO timestamp |
| updated_at | TEXT NOT NULL | ISO timestamp |

#### **repertoire**
| Column | Type | Description |
|--------|------|-------------|
| id | TEXT PK | UUID primary key |
| composer | TEXT | Composer name |
| title | TEXT NOT NULL | Piece title |
| dates | TEXT | Composer life dates |
| country | TEXT | Composer country |
| publisher | TEXT | Publisher name |
| arrangement | TEXT | Arrangement type |
| location | TEXT | Sheet music location |
| project_id | TEXT FK | References projects(id) ON DELETE SET NULL |
| created_at | TEXT NOT NULL | ISO timestamp |
| updated_at | TEXT NOT NULL | ISO timestamp |

#### **selbstdarstellung** (Marketing)
| Column | Type | Description |
|--------|------|-------------|
| id | TEXT PK | UUID primary key |
| content | TEXT | Marketing text content |
| updated_at | TEXT NOT NULL | ISO timestamp |

### Relationships
```
projects (1) ──→ (n) events
projects (1) ──→ (n) besetzung
projects (1) ──→ (n) repertoire
events (1) ──→ (n) availability
singers (1) ──→ (n) availability
singers (1) ──→ (0..1) singers (affinity_uuid self-reference)
```

---

## 4. Data Processing Pipeline

### Singer Management
1. **Input**: User enters singer data via SingerDialog
2. **Validation**: Required field check (full_name)
3. **Processing**:
   - Generate UUID via `Database.generate_id()`
   - Set `created_at` and `updated_at` timestamps
   - Compute `is_adult` from `birth_date` if not provided
   - Handle affinity bidirectional sync (update partner's affinity_uuid)
4. **Storage**: INSERT into singers table via `SingerRepository.create()`
5. **Output**: Singer object returned, table refreshed

### Event Availability Processing
1. **Input**: User selects status via EventAvailabilityDialog (radio buttons)
2. **Processing**:
   - Check if availability record exists for (singer_id, event_id)
   - If exists: UPDATE status
   - If not exists: INSERT new record
   - Uses UPSERT pattern: `INSERT ... ON CONFLICT DO UPDATE`
3. **Storage**: availability table via `AvailabilityRepository.update()`
4. **Output**: Updated availability record, summary table refreshed

### Export Pipeline
1. **Input**: User selects fields and format (CSV/PDF/ODT/ODS)
2. **Data Fetch**: Repository.get_all() or filtered query
3. **Processing**:
   - **CSV**: Direct CSV writer
   - **PDF**: reportlab canvas, format table
   - **LibreOffice**: Use `odfpy` or `uno` API to generate ODT/ODS
4. **Output**: File written to user-selected path

### Choraufstellung Integration Pipeline
1. **Trigger**: User selects "Choraufstellung → In Choraufstellung öffnen..."
2. **Data Export**: 
   - Query singers with availability status "yes" or "conditional"
   - Get current event data (project_id, date, name)
3. **Environment Variables**:
   - `CHOR_PROJECT_ID`: Current project ID
   - `CHOR_EVENT_ID`: Current event ID
   - `CHOR_DB_PATH`: Database path (read-only access)
4. **Launch**: Start Choraufstellung app with environment variables
5. **Data Flow**: One-way (ChorManager → Choraufstellung), no write-back

---

## 5. Key Functions and Methods

### Database Layer (`data/database.py`)

#### `Database` class
- `__init__(db_path: Optional[str])`: Initialize with optional custom path
- `connect()`: Establish SQLite connection, enable foreign keys
- `get_connection() -> sqlite3.Connection`: Get active connection
- `execute(query: str, params: tuple) -> Cursor`: Execute SQL query
- `commit()`: Commit transaction
- `rollback()`: Rollback transaction
- `create_tables()`: Create all tables if not exist, run migrations
- `generate_id() -> str`: Generate UUID4 string
- `transaction()`: Context manager for atomic operations

### Domain Models (`domain/models.py`)

#### `Singer` dataclass
- `is_adult() -> bool`: Check if singer ≥18 years
- `age() -> Optional[int]`: Calculate age in years
- `compute_is_adult() -> int`: Compute is_adult from birth_date
- `joined_display() -> str`: Format joined date as "MM/YYYY"
- `left_display() -> str`: Format left date as "MM/YYYY"
- `social_contacts_dict() -> dict`: Parse social_contacts JSON
- `to_dict() -> dict`: Convert to dictionary
- `from_dict(data: dict) -> Singer`: Create from dictionary

#### `Event` dataclass
- `is_past() -> bool`: Check if event date is in the past
- `to_dict() -> dict`: Convert to dictionary
- `from_dict(data: dict) -> Event`: Create from dictionary

#### `Project` dataclass
- `to_dict() -> dict`: Convert to dictionary
- `from_dict(data: dict) -> Project`: Create from dictionary

#### `Availability` dataclass
- `to_dict() -> dict`: Convert to dictionary
- `from_dict(data: dict) -> Availability`: Create from dictionary

#### `Besetzung` dataclass
- `get_singer_ids() -> list`: Parse singer_ids JSON array
- `set_singer_ids(ids: list)`: Set singer_ids from list
- `to_dict() -> dict`: Convert to dictionary
- `from_dict(data: dict) -> Besetzung`: Create from dictionary

#### `Repertoire` dataclass
- `to_dict() -> dict`: Convert to dictionary
- `from_dict(data: dict) -> Repertoire`: Create from dictionary

### Repository Layer (`domain/repository.py`)

#### `SingerRepository`
- `create(**kwargs) -> Singer`: Create new singer
- `get_by_id(singer_id: str) -> Optional[Singer]`: Get by ID
- `get_all() -> List[Singer]`: Get all singers ordered by name
- `get_by_voice_group(voice_group: str) -> List[Singer]`: Filter by voice group
- `get_active() -> List[Singer]`: Get active singers (left_year IS NULL)
- `update(singer_id: str, **kwargs) -> Optional[Singer]`: Update singer, handles affinity sync
- `delete(singer_id: str) -> bool`: Delete singer
- `search(query: str) -> List[Singer]`: Search by name/email

#### `EventRepository`
- `create(**kwargs) -> Event`: Create new event
- `get_by_id(event_id: str) -> Optional[Event]`: Get by ID
- `get_all() -> List[Event]`: Get all events ordered by date DESC
- `get_upcoming() -> List[Event]`: Get future events
- `update(event_id: str, **kwargs) -> Optional[Event]`: Update event
- `delete(event_id: str) -> bool`: Delete event

#### `AvailabilityRepository`
- `create(**kwargs) -> Availability`: Create availability entry
- `get_by_ids(singer_id: str, event_id: str) -> Optional[Availability]`: Get by composite key
- `get_by_event(event_id: str) -> List[Availability]`: Get all for event
- `get_by_singer(singer_id: str) -> List[Availability]`: Get all for singer
- `update(singer_id: str, event_id: str, status: str) -> Optional[Availability]`: Upsert availability
- `delete(singer_id: str, event_id: str) -> bool`: Delete availability

#### `ProjectRepository`
- `create(**kwargs) -> Project`: Create new project
- `get_by_id(project_id: str) -> Optional[Project]`: Get by ID
- `get_all() -> List[Project]`: Get all projects ordered by name
- `get_active() -> Optional[Project]`: Get currently active project
- `set_active(project_id: str)`: Set project as active (unsets others)
- `update(project_id: str, **kwargs) -> Optional[Project]`: Update project
- `delete(project_id: str) -> bool`: Delete project

#### `BesetzungRepository`
- `create(name: str, project_id: str, singer_ids: List[str]) -> Besetzung`: Create lineup
- `get_by_id(besetzung_id: str) -> Optional[Besetzung]`: Get by ID
- `get_all() -> List[Besetzung]`: Get all lineups ordered by updated_at DESC
- `get_by_project(project_id: str) -> List[Besetzung]`: Get lineups for project
- `update(besetzung_id: str, **kwargs) -> Optional[Besetzung]`: Update lineup
- `delete(besetzung_id: str) -> bool`: Delete lineup
- `set_active(project_id: str)`: Set active lineup for project

#### `RepertoireRepository`
- `create(composer: str, title: str, ..., project_id: str) -> Repertoire`: Create repertoire entry
- `get_by_id(repertoire_id: str) -> Optional[Repertoire]`: Get by ID
- `get_all() -> List[Repertoire]`: Get all entries ordered by title ASC
- `get_by_project_id(project_id: str) -> List[Repertoire]`: Get entries linked to project
- `update(repertoire_id: str, **kwargs) -> Optional[Repertoire]`: Update entry
- `delete(repertoire_id: str) -> bool`: Delete entry

---

## 6. UI Components and Outputs

### Main Window (`ui/main_window.py`)
- **Menu Bar**: File, Edit (Undo/Redo), Extras (Settings, Backup, Export), Choraufstellung, Help
- **Tab Widget**: Projects, Singers, Lineups, Events, Arrangement
- **Status Bar**: Shows active project, active lineup, last backup time

### Tab Views

#### ProjectsTab (`views/projects_tab.py`)
- **Table columns**: Season, Name, Description, Active, Event Count
- **Toolbar**: Search, Sort by Name/Season, Sort order
- **Context menu**: Edit, Duplicate
- **ProjectDialog**: Name, Season, Description (200px height), linked Repertoire pieces table

#### SingersTab (`views/singers_tab.py`)
- **Table columns**: Name, Short name, Voice group, Age, Status, etc.
- **Toolbar**: Search, Voice group filter, Status filter (Active/Minor/U16), Sort options
- **Context menu**: Add, Edit, Delete, Set affinity
- **SingerSelectionDialog**: Checkbox table for lineup creation

#### EventsTab (`views/events_tab.py`)
- **Table columns**: Date, Name, Type, Project, Location
- **EventAvailabilityDialog**: Radio buttons for availability status, summary by voice group
- **Export**: PDF, CSV, LibreOffice formats

#### RepertoireTab (`views/repertoire_tab.py`)
- **Table columns**: Composer, Title, Dates, Country, Publisher, Arrangement, Location, Program
- **Toolbar**: Sort by Composer/Country/Location, Sort order, Search
- **RepertoireDialog**: Composer, Title, Dates, Country, Publisher, Arrangement, Location, Program (dropdown)

#### BesetzungTab (`views/besetzung_tab.py`)
- **Table columns**: Name, Project, Singer count, Updated
- **Context menu**: Edit, Rename, Set active, Delete
- **Choraufstellung integration**: Open lineup in arrangement app

#### ChoraufstellungTab (`views/choraufstellung_tab.py`)
- **Table columns**: Filename, Size, Project, Event, Type, Saved date
- **Context menu**: Edit, Duplicate
- **Integration**: Launch Choraufstellung app with selected JSON

### Export Outputs

#### CSV Export
- Delimiter: Semicolon (;)
- Encoding: UTF-8 with BOM
- Format: Flat table with selected fields

#### PDF Export (`reportlab`)
- Page size: A4
- Font: Helvetica, 10pt
- Headers: Bold, 12pt
- Tables: Grid lines, alternating row colors

#### LibreOffice Export
- **Writer (.odt)**: Formatted text document with headers and tables
- **Calc (.ods)**: Spreadsheet with auto-sized columns

#### JSON Sync Export
- Format: `{"singers": [...], "event": {...}, "project": {...}}`
- Purpose: Data exchange with Choraufstellung app
- Location: `choraufstellung/data/` directory

### Backup Outputs
- **Format**: ZIP archive
- **Contents**: 
  - `chor.db` (SQLite database)
  - `config/` directory (YAML files)
  - `choraufstellung/data/` (JSON files)
- **Location**: `~/.local/share/chormanager/backups/` or custom path
- **Naming**: `chormanager_backup_YYYY-MM-DD.zip`

---

## 7. Configuration Files

### `config/app.yaml`
```yaml
database:
  filename: "chor.db"
data_dir: "~/.local/share/chormanager"
backup:
  auto_backup: true
  max_backups: 10
logging:
  level: "INFO"
  max_bytes: 1048576
  backup_count: 5
theme:
  mode: "light"  # or "dark"
```

### `config/voice_groups.yaml`
```yaml
- name: "Sopran 1"
  order: 1
- name: "Sopran 2"
  order: 2
- name: "Alt 1"
  order: 3
...
```

### `config/fields.yaml`
Dynamic fields for singer data (extendable without code changes).

---

## 8. Testing Strategy

### Test Pyramid
- **70% Unit Tests** (`tests/unit/`): Pure Python logic, mocked database
- **25% Integration Tests** (`tests/integration/`): Real database, file I/O
- **5% UI Tests** (`tests/gui/`): pytest-qt for critical flows

### Running Tests
```bash
# All tests (headless)
QT_QPA_PLATFORM=offscreen python3 -m pytest tests/unit/ -v

# Specific test file
python3 -m pytest tests/unit/test_database.py -v

# With coverage
python3 -m pytest --cov=chormanager tests/unit/
```

### Test Fixtures (`conftest.py`)
- `mock_db`: In-memory SQLite database
- `mock_qapp`: QApplication instance for UI tests
- `sample_singers`: Pre-populated singer data
- `empty_undo_stack`: Fresh QUndoStack

---

## 9. Data Storage Paths

### Default Locations (XDG Base Directory Specification)
- **Database**: `~/.local/share/chormanager/chor.db`
- **Backups**: `~/.local/share/chormanager/backups/`
- **Logs**: `~/.local/share/chormanager/logs/`
- **Config**: `{project}/config/` (project-local)

### Portable Mode (USB Stick)
1. Open Settings dialog (Extras → Einstellungen)
2. Set "Datenpfad" to USB stick folder
3. All data stored in that single directory

---

## 10. Undo/Redo System

### Implementation
- **Pattern**: Command Pattern via `QUndoCommand`
- **Stack**: `QUndoStack` in `MainWindow`
- **Commands**: Custom subclasses in `history/service.py`

### Available Commands
- `AddSingerCommand`: Undo/Redo singer creation
- `DeleteSingerCommand`: Undo/Redo singer deletion
- `UpdateSingerCommand`: Undo/Redo singer updates
- `AddEventCommand`: Undo/Redo event creation
- `DeleteEventCommand`: Undo/Redo event deletion
- `AddProjectCommand`: Undo/Redo project creation
- And more for all CRUD operations...

### Usage
- **Undo**: Ctrl+Z or Edit → Undo
- **Redo**: Ctrl+Shift+Z or Edit → Redo
- **Stack size**: Unlimited (memory permitting)

---

## 11. Performance Considerations

### Database
- **Indexes**: SQLite automatically creates indexes for PRIMARY KEY and UNIQUE constraints
- **Foreign keys**: Enabled via `PRAGMA foreign_keys = ON`
- **Transactions**: Atomic commits via context manager

### UI
- **Lazy loading**: Tables populated on tab switch
- **Thumbnail cache**: Not implemented (not needed for current scale)
- **Search**: Client-side filtering (sufficient for <10k records)

### Scalability
- **Tested up to**: 500 singers, 100 events, 200 repertoire pieces
- **Bottleneck**: Availability matrix rendering (O(singers × events))
- **Optimization**: Pagination planned for future releases

---

## 12. Security Notes

### Data Privacy
- **Local only**: No network access, all data stored locally
- **No encryption**: Database not encrypted (plan for portable mode)
- **File permissions**: SQLite file created with default umask

### Backup Security
- **ZIP only**: No cloud upload (user responsibility)
- **No password**: Backup ZIP not password-protected
- **Sanitization**: User input sanitized before SQL queries (parameterized queries)

---

**Documentation Version**: 1.0  
**Last Updated**: 2026-04-30  
**Corresponding Code Version**: 0.4
