# ChorManager API Reference

## Repository Layer

All repositories follow the same pattern:
- Constructor takes `Database` instance
- Methods return dataclass instances or lists thereof
- Timestamps (`created_at`, `updated_at`) set automatically

### SingerRepository

#### `create(**kwargs) -> Singer`
Create a new singer.

**Parameters:**
- `**kwargs`: Singer fields (full_name, short_name, voice_group, height, etc.)

**Returns:**
- `Singer`: Created singer instance

**Example:**
```python
repo = SingerRepository(db)
singer = repo.create(
    full_name="Max Mustermann",
    short_name="Max",
    voice_group="Tenor 1",
    height=180,
    email="max@example.com"
)
```

#### `get_by_id(singer_id: str) -> Optional[Singer]`
Get singer by ID.

#### `get_all() -> List[Singer]`
Get all singers ordered by `full_name`.

#### `get_by_voice_group(voice_group: str) -> List[Singer]`
Filter singers by voice group.

#### `get_active() -> List[Singer]`
Get singers where `left_year IS NULL`.

#### `update(singer_id: str, **kwargs) -> Optional[Singer]`
Update singer. Handles bidirectional affinity sync.

**Special handling:**
- If `affinity_uuid` changes, automatically updates partner's affinity.
- `height` field can be updated for Choraufstellung grid placement.

#### `delete(singer_id: str) -> bool`
Delete singer. Returns True if deleted.

#### `search(query: str) -> List[Singer]`
Search by `full_name`, `short_name`, or `email`.

---

### EventRepository

#### `create(**kwargs) -> Event`
Create a new event.

**Parameters:**
- `**kwargs`: Event fields (name, date, event_type, location, project_id)

**Example:**
```python
repo = EventRepository(db)
event = repo.create(
    name="Frühjahrskonzert",
    date="2026-05-15",
    event_type="Konzert",
    project_id="uuid-of-project"
)
```

#### `get_by_id(event_id: str) -> Optional[Event]`

#### `get_all() -> List[Event]`
Get all events ordered by `date DESC`.

#### `get_upcoming() -> List[Event]`
Get events where `date >= NOW()`.

#### `update(event_id: str, **kwargs) -> Optional[Event]`

#### `delete(event_id: str) -> bool`

---

### AvailabilityRepository

#### `create(**kwargs) -> Availability`
Create availability entry.

#### `get_by_ids(singer_id: str, event_id: str) -> Optional[Availability]`
Get by composite key.

#### `get_by_event(event_id: str) -> List[Availability]`
Get all availability for an event.

#### `get_by_singer(singer_id: str) -> List[Availability]`
Get all availability for a singer.

#### `update(singer_id: str, event_id: str, status: str) -> Optional[Availability]`
Upsert availability. Uses `INSERT ... ON CONFLICT DO UPDATE`.

**Status values:**
- `yes`: Available (Zusage)
- `no`: Not available (Absage)
- `none`: No response (offen)
- `conditional`: Conditional (Vorbehalt)
- `unknown`: Unknown (weiß nicht)
- `maybe`: Maybe (vielleicht)

#### `delete(singer_id: str, event_id: str) -> bool`

---

### ProjectRepository

#### `create(**kwargs) -> Project`
Create a new project.

**Example:**
```python
repo = ProjectRepository(db)
project = repo.create(
    name="Hoffmann OKO 2026",
    spielzeit="2025/26",
    description="Großes Chorprojekt"
)
```

#### `get_by_id(project_id: str) -> Optional[Project]`

#### `get_all() -> List[Project]`
Get all projects ordered by `name`.

#### `get_active() -> Optional[Project]`
Get project where `is_active = 1`.

#### `set_active(project_id: str) -> None`
Set project as active (unsets all others).

#### `update(project_id: str, **kwargs) -> Optional[Project]`

#### `delete(project_id: str) -> bool`

---

### BesetzungRepository

#### `create(name: str, project_id: str, singer_ids: List[str]) -> Besetzung`
Create a new lineup.

**Example:**
```python
repo = BesetzungRepository(db)
lineup = repo.create(
    name="Premiere A",
    project_id="uuid-of-project",
    singer_ids=["uuid1", "uuid2", "uuid3"]
)
```

#### `get_by_id(besetzung_id: str) -> Optional[Besetzung]`

#### `get_all() -> List[Besetzung]`
Get all lineups ordered by `updated_at DESC`.

#### `get_by_project(project_id: str) -> List[Besetzung]`
Get lineups for a specific project.

#### `update(besetzung_id: str, **kwargs) -> Optional[Besetzung]`
Update lineup. Automatically JSON-encodes `singer_ids` if list.

#### `delete(besetzung_id: str) -> bool`

#### `set_active(project_id: str) -> None`
Set most recent lineup as active for project.

---

### RepertoireRepository

#### `create(composer: str, title: str, ..., project_id: str) -> Repertoire`
Create a new repertoire entry.

**Parameters:**
- `composer`: Composer name
- `title`: Piece title (required)
- `dates`: Composer life dates (optional)
- `country`: Composer country (optional)
- `publisher`: Publisher name (optional)
- `arrangement`: Arrangement type (optional)
- `location`: Sheet music location (optional)
- `project_id`: Associated project UUID (optional)

**Example:**
```python
repo = RepertoireRepository(db)
piece = repo.create(
    composer="Mozart",
    title="Requiem d-Moll",
    dates="1756-1791",
    country="Österreich",
    arrangement="Gemischter Chor",
    project_id="uuid-of-project"
)
```

#### `get_by_id(repertoire_id: str) -> Optional[Repertoire]`

#### `get_all() -> List[Repertoire]`
Get all entries ordered by `title ASC`.

#### `get_by_project_id(project_id: str) -> List[Repertoire]`
Get all repertoire pieces linked to a project.

#### `update(repertoire_id: str, **kwargs) -> Optional[Repertoire]`

#### `delete(repertoire_id: str) -> bool`

---

## Database Layer

### Database Class

#### `__init__(db_path: Optional[str] = None)`
Initialize database connection.

**Parameters:**
- `db_path`: Path to .db file. If None, uses config from `app.yaml`.

#### `connect() -> None`
Establish SQLite connection. Enables foreign key constraints.

#### `get_connection() -> sqlite3.Connection`
Get active connection. Raises `RuntimeError` if not connected.

#### `execute(query: str, params: tuple = ()) -> sqlite3.Cursor`
Execute SQL query with optional parameters.

#### `commit() -> None`
Commit current transaction.

#### `rollback() -> None`
Rollback current transaction.

#### `create_tables() -> None`
Create all tables if not exist. Also runs migrations.

#### `transaction()`
Context manager for atomic operations.

**Example:**
```python
with db.transaction():
    # Multiple operations here
    # Automatically commits or rollbacks
    pass
```

#### `generate_id() -> str`
Generate UUID4 string.

---

## Model Layer

All models are `@dataclass` decorated classes with:
- Automatic `created_at`/`updated_at` timestamps in `__post_init__`
- `to_dict()` method for serialization
- `from_dict(cls, data: dict)` classmethod for deserialization

### Common Fields
- `id`: UUID primary key
- `created_at`: ISO format timestamp
- `updated_at`: ISO format timestamp

### Singer Model Additional Methods

#### `is_adult() -> bool`
Check if singer is 18+ years based on `birth_date`.

#### `age() -> Optional[int]`
Calculate age in years. Returns None if no `birth_date`.

#### `compute_is_adult() -> int`
Compute `is_adult` from `birth_date`. Returns 1 (adult) or 0 (minor).

#### `joined_display() -> str`
Format as "MM/YYYY" or empty string.

#### `left_display() -> str`
Format as "MM/YYYY" or empty string.

#### `social_contacts_dict() -> dict`
Parse `social_contacts` JSON string to dict.

#### `height` property
Height in centimeters. Used for Choraufstellung auto-arrange by height feature.

---

## Configuration

### Loading Config
```python
from chormanager.config import load_app_config, get_data_dir

config = load_app_config()
data_dir = get_data_dir()
```

### Voice Groups
Voice groups are now configured in `config/voice_groups.json` with theme-aware colors:

```json
{
  "themes": {
    "light": {
      "text": "#1A1A1A",
      "colors": [
        {"id": "Sopran 1", "color": "#E5C84B"},
        ...
      ]
    },
    "dark": {
      "text": "#F0F0F0",
      "colors": [...]
    }
  }
}
```

### Dynamic Fields
```yaml
# config/fields.yaml
- name: "height"
  type: "integer"
  label: "Größe (cm)"
- name: "instrument"
  type: "text"
  label: "Instrument"
...
```

---

## Export Services

### ExportService (`export/__init__.py`)

#### `export_to_csv(data: List[dict], fields: List[str]) -> str`
Export to CSV with semicolon delimiter.

#### `export_to_libreoffice_writer(data: List[dict], fields: List[str]) -> bytes`
Export to LibreOffice Writer (.odt).

#### `export_to_libreoffice_calc(data: List[dict], fields: List[str]) -> bytes`
Export to LibreOffice Calc (.ods).

#### `get_export_data(items: List[Any], fields: List[str]) -> List[dict]`
Convert model instances to exportable dictionaries.

---

## Error Handling

### Common Exceptions
- `RuntimeError`: Database not connected
- `sqlite3.OperationalError`: SQL syntax or constraint violation
- `json.JSONDecodeError`: Invalid JSON in fields

### Atomic Operations
All write operations use `try/except` with rollback:
```python
try:
    # Execute operations
    db.commit()
except Exception:
    db.rollback()
    raise
```

### File I/O
All file writes use atomic pattern:
- Write to temporary file
- Use `os.replace()` to atomically move

---

**API Version**: 1.1
**Last Updated**: 2026-05-07
