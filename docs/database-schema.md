# ChorManager Database Schema Reference

## Connection Details

- **Type**: SQLite 3
- **Location**: `~/.local/share/chormanager/chor.db` (default)
- **Foreign Keys**: Enabled (`PRAGMA foreign_keys = ON`)
- **Row Factory**: `sqlite3.Row` (dict-like access)

---

## Table Definitions

### singers
Stores choir member data.

```sql
CREATE TABLE singers (
    id TEXT PRIMARY KEY,                     -- UUID
    full_name TEXT NOT NULL,                  -- Required
    short_name TEXT,                           -- Optional nickname
    birth_date TEXT,                            -- YYYY-MM-DD
    voice_group TEXT,                           -- e.g., "Sopran 1"
    height INTEGER,                              -- Height in cm (for Choraufstellung)
    email TEXT,                                 -- Email address
    phone TEXT,                                 -- Phone number
    street TEXT,                                -- Street address
    postal_code TEXT,                           -- Postal code
    city TEXT,                                  -- City
    gender TEXT,                                -- Gender
    guardian1 TEXT,                             -- First guardian name
    guardian1_phone TEXT,                       -- First guardian phone
    guardian2 TEXT,                             -- Second guardian name
    guardian2_phone TEXT,                       -- Second guardian phone
    social_contacts TEXT,                        -- JSON: {"facebook": "...", ...}
    joined_year INTEGER,                         -- Year joined
    joined_month INTEGER,                        -- Month joined
    left_year INTEGER,                          -- NULL if active
    left_month INTEGER,                         -- Month left
    affinity_uuid TEXT,                          -- FK to singers(id)
    created_at TEXT NOT NULL,                    -- ISO timestamp
    updated_at TEXT NOT NULL                     -- ISO timestamp
)
```

**Indexes:**
- PRIMARY KEY on `id`
- Foreign key: `affinity_uuid` references `singers(id)` (no cascade)

**Migrations:**
- `street`, `postal_code`, `city` added via ALTER TABLE
- `guardian1`, `guardian1_phone`, `guardian2`, `guardian2_phone` added via ALTER TABLE
- `is_adult` column was removed (logic computed from `birth_date`)
- `height` added via ALTER TABLE (for Choraufstellung grid placement)

---

### events
Stores rehearsals, concerts, and other events.

```sql
CREATE TABLE events (
    id TEXT PRIMARY KEY,                        -- UUID
    name TEXT NOT NULL,                           -- Event name
    date TEXT NOT NULL,                           -- YYYY-MM-DD
    event_type TEXT NOT NULL,                     -- GP/OP/SOFA/Probe/Konzert/Auftritt
    location TEXT,                                -- Location
    description TEXT,                             -- Description
    project_id TEXT REFERENCES projects(id) ON DELETE SET NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
)
```

**Indexes:**
- PRIMARY KEY on `id`
- Foreign key: `project_id` → `projects(id)` with SET NULL on delete

---

### projects
Stores concert projects (e.g., "Hoffmann OKO 2026").

```sql
CREATE TABLE projects (
    id TEXT PRIMARY KEY,                        -- UUID
    name TEXT NOT NULL,                           -- Project name
    description TEXT,                             -- Description
    is_active INTEGER DEFAULT 0,                  -- 1 if active
    spielzeit TEXT,                               -- Season (e.g., "2025/26")
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
)
```

**Indexes:**
- PRIMARY KEY on `id`
- Index on `is_active` (implicit via WHERE clause)

---

### availability
Stores singer availability for events.

```sql
CREATE TABLE availability (
    id TEXT PRIMARY KEY,                        -- UUID
    singer_id TEXT NOT NULL REFERENCES singers(id) ON DELETE CASCADE,
    event_id TEXT NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    status TEXT NOT NULL,                         -- yes/no/none/conditional/unknown/maybe
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(singer_id, event_id)                  -- Composite unique constraint
)
```

**Indexes:**
- PRIMARY KEY on `id`
- UNIQUE constraint on (`singer_id`, `event_id`)
- Foreign keys with CASCADE delete

**Upsert Pattern:**
```sql
INSERT INTO availability (id, singer_id, event_id, status, created_at, updated_at)
VALUES (?, ?, ?, ?, ?, ?)
ON CONFLICT(singer_id, event_id) DO UPDATE SET status = ?, updated_at = ?
```

---

### besetzung
Stores singer lineups/castings for projects.

```sql
CREATE TABLE besetzung (
    id TEXT PRIMARY KEY,                        -- UUID
    name TEXT NOT NULL,                           -- Lineup name
    project_id TEXT REFERENCES projects(id) ON DELETE SET NULL,
    singer_ids TEXT NOT NULL,                     -- JSON array: ["uuid1", "uuid2", ...]
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
)
```

**Indexes:**
- PRIMARY KEY on `id`
- Foreign key: `project_id` → `projects(id)` with SET NULL on delete

**Note:** `singer_ids` is stored as JSON array string.

---

### repertoire
Stores musical pieces with optional project link.

```sql
CREATE TABLE repertoire (
    id TEXT PRIMARY KEY,                        -- UUID
    composer TEXT,                                -- Composer name
    title TEXT NOT NULL,                           -- Piece title
    dates TEXT,                                   -- Composer life dates (e.g., "1756-1791")
    country TEXT,                                 -- Composer country
    publisher TEXT,                                -- Publisher
    arrangement TEXT,                             -- Arrangement type
    location TEXT,                                -- Sheet music location
    project_id TEXT REFERENCES projects(id) ON DELETE SET NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
)
```

**Indexes:**
- PRIMARY KEY on `id`
- Foreign key: `project_id` → `projects(id)` with SET NULL on delete

**Migration:** Column `program` was renamed to `project_id` via `ALTER TABLE repertoire RENAME COLUMN program TO project_id`.

---

### selbstdarstellung
Stores marketing texts for choir presentation.

```sql
CREATE TABLE selbstdarstellung (
    id TEXT PRIMARY KEY,                        -- UUID
    content TEXT,                                  -- Marketing text content
    updated_at TEXT NOT NULL
)
```

---

## Relationships Diagram

```
projects (1) ──→ (n) events
projects (1) ──→ (n) besetzung
projects (1) ──→ (n) repertoire
events (1) ──→ (n) availability
singers (1) ──→ (n) availability
singers (1) ──→ (0..1) singers (affinity_uuid self-reference)
```

---

## Data Types

### Text Fields
- Stored as `TEXT` in SQLite
- Empty strings stored as `""` (not NULL)
- JSON fields: `social_contacts`, `singer_ids`

### Integer Fields
- `joined_year`, `joined_month`, `left_year`, `left_month`: NULL if not set
- `height`: Height in centimeters (NULL if not set)
- `is_active`: 0 (inactive) or 1 (active)

### Timestamps
- Format: ISO 8601 (`YYYY-MM-DDTHH:MM:SS.ssssss`)
- Set automatically via `datetime.now().isoformat()`
- `created_at`: Set once on creation
- `updated_at`: Updated on every modification

---

## Query Patterns

### Get All with Ordering
```sql
SELECT * FROM singers ORDER BY full_name
SELECT * FROM events ORDER BY date DESC
SELECT * FROM projects ORDER BY name
SELECT * FROM repertoire ORDER BY title ASC
SELECT * FROM besetzung ORDER BY updated_at DESC
```

### Filter by Foreign Key
```sql
SELECT * FROM events WHERE project_id = ?
SELECT * FROM besetzung WHERE project_id = ?
SELECT * FROM repertoire WHERE project_id = ?
SELECT * FROM singers WHERE voice_group = ?
```

### Search with LIKE
```sql
SELECT * FROM singers 
WHERE full_name LIKE ? OR short_name LIKE ? OR email LIKE ?
ORDER BY full_name
-- Pattern: "%query%"
```

### Upsert (Insert or Update)
```sql
INSERT INTO availability (id, singer_id, event_id, status, created_at, updated_at)
VALUES (?, ?, ?, ?, ?, ?)
ON CONFLICT(singer_id, event_id) DO UPDATE SET status = ?, updated_at = ?
```

### Check Existence
```sql
SELECT 1 FROM availability WHERE singer_id = ? AND event_id = ?
```

---

## Database Migrations

Migrations run automatically in `Database.create_tables()`:

```python
# Rename column (SQLite 3.25+)
try:
    conn.execute("ALTER TABLE repertoire RENAME COLUMN program TO project_id")
except sqlite3.OperationalError:
    pass  # Column doesn't exist or already renamed

# Add new columns
for col, typ in [("street", "TEXT"), ("postal_code", "TEXT"), ...]:
    try:
        conn.execute(f"ALTER TABLE singers ADD COLUMN {col} {typ}")
    except sqlite3.OperationalError:
        pass  # Column already exists
```

---

## Backup & Restore

### Automatic Backup
- Triggered on app start and before critical saves
- Location: `~/.local/share/chormanager/backups/`
- Format: ZIP archive containing `chor.db`, `config/`, `choraufstellung/data/`

### Manual Backup
```python
from chormanager.backup.service import BackupService
service = BackupService(db)
service.create_backup()
```

### Restore
```python
service.restore_backup("/path/to/backup.zip")
```

---

**Schema Version**: 1.1
**Last Updated**: 2026-05-07
**Corresponding Code Version**: 0.5
