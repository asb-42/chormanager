# Sub-Plan: Pro-Tab-Database-Connection-Pool (C-6)

| Feld | Wert |
|------|------|
| **Quelle** | `docs/reports/2026-06-14_code-review.md` — **C-6** (Geteilte SQLite-Connection) |
| **Bezug** | `plans/2026-06-14_m4_findings.md` — Sprint 2 / Cluster E / C6-SUBPLAN-A |
| **Status** | 📝 **Vorbereitet** (Sprint 2.7) — Implementation Sprint 3 |
| **Prio** | P1 |
| **Aufwand** | L (2 Personentage) |
| **Risiko** | Hoch (Concurrency ist schwer) |

## 🎯 Ziel

Jeder Tab bekommt eine **eigene SQLite-Connection** mit garantierter Write-Serialisierung. Damit:

1. Keine "Recursive use of cursors not allowed"-Errors mehr.
2. `_reload_after_restore` ist race-frei.
3. Schreib-Concurrency-Test ist gruen.
4. Write-Lock via `BEGIN IMMEDIATE` (SQLite-Standard fuer sicheres Schreiben).

## 🏗️ Architektur

### Variante A — Pro-Tab-Connection mit Write-Lock (empfohlen ✅)

```
MainWindow
   ├── Database (zentraler Path, WAL-Mode)
   ├── db_pool = self.db.connect_pool(max_connections=N_tabs)
   ├── tab1: SingerRepository(db=self.db_pool.connection())
   ├── tab2: SingerRepository(db=self.db_pool.connection())
   └── ...
```

**Schreib-Serialisierung:** `db_pool.write_lock` (Python `threading.Lock`).

**SQLite-Einstellungen:**
- `journal_mode=WAL` (Multi-Reader + Single-Writer)
- `busy_timeout=5000` (5s warten statt sofort fehlschlagen)
- `check_same_thread=False` (fuer Cross-Thread-Nutzung)

**Vorteile:**
- Standard SQLite-Pattern
- Testbar mit `threading.Thread`
- Keine externe Dependency

**Nachteile:**
- Mehr Code als Single-Connection
- Schreib-Concurrency auf 1 beschränkt (OK fuer unsere Last)

### Variante B — `sqlite3pool` aus PyPI (abgelehnt ❌)

- Vorteile: Fertig.
- Nachteile: Neue Dependency, nicht im Standard-Stack.

### Variante C — `BEGIN IMMEDIATE` ohne Pool (abgelehnt ❌)

- Vorteile: Minimaler Code.
- Nachteile: Nicht thread-safe pro Connection.

## 📋 Akzeptanzkriterien

| # | Kriterium | Verifikation |
|---|-----------|--------------|
| A1 | Jeder Tab hat eigene `sqlite3.Connection` | `inspect` |
| A2 | Concurrency-Test `tests/integration/test_db_concurrent_writes.py` gruen | pytest |
| A3 | `_reload_after_restore` ohne Race | manueller Test + Test T-1 |
| A4 | WAL-Mode aktiv | `PRAGMA journal_mode` |
| A5 | `busy_timeout=5000` gesetzt | Test |

## 🧩 Implementation-Skizze

### Phase 1 — `Database.connect_pool()` (0,5 d)

```python
class Database:
    def connect_pool(self, max_connections: int = 10) -> "DatabasePool":
        """Return a new pool with own connections for thread-safe access."""
        return DatabasePool(self.db_path, max_connections=max_connections)


class DatabasePool:
    def __init__(self, db_path, max_connections=10):
        self._path = db_path
        self._max = max_connections
        self._lock = threading.Lock()
        self._pool = queue.Queue(maxsize=max_connections)
        for _ in range(max_connections):
            conn = sqlite3.connect(db_path, check_same_thread=False, timeout=5.0)
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA busy_timeout=5000")
            conn.row_factory = sqlite3.Row
            self._pool.put(conn)
    
    @contextmanager
    def connection(self):
        conn = self._pool.get()
        try:
            yield conn
        finally:
            self._pool.put(conn)
    
    def write_lock(self) -> threading.Lock:
        return self._lock
```

### Phase 2 — Repository-Migration (0,5 d)

```python
class SingerRepository:
    def __init__(self, db):
        self.db = db  # Kann Database ODER DatabasePool sein

    def create(self, **kwargs):
        with self.db.connection() as conn:
            cur = conn.execute(...)
            conn.commit()
```

### Phase 3 — Tab-Integration (0,5 d)

```python
# In MainWindow:
self.db_pool = self.db.connect_pool()
self.singer_repo = SingerRepository(self.db_pool)
# In jedem Tab beim Refresh:
refresh_tab_repositories(tab, self.db_pool)
```

### Phase 4 — Tests (0,5 d)

```python
# tests/integration/test_db_concurrent_writes.py
def test_concurrent_writes_serialized():
    db = Database(":memory:")
    db_pool = db.connect_pool(max_connections=4)
    results = []
    def writer(sid):
        with db_pool.connection() as conn:
            conn.execute("INSERT INTO singers(id, full_name) VALUES (?, ?)", (sid, f"Name-{sid}"))
            conn.commit()
        results.append(sid)
    
    threads = [threading.Thread(target=writer, args=(i,)) for i in range(20)]
    for t in threads: t.start()
    for t in threads: t.join()
    
    assert len(results) == 20
    cur = db.execute("SELECT COUNT(*) FROM singers")
    assert cur.fetchone()[0] == 20
```

## 🛡️ Risk-Assessment

| Risiko | Wahrscheinlichkeit | Impact | Mitigation |
|--------|-------------------|--------|------------|
| Dead-Lock bei Lock-Order | Niedrig | Hoch | Single-Lock-Pattern (Write-Lock) |
| Connection-Leak bei Exception | Mittel | Mittel | `@contextmanager` garantiert Return |
| In-Memory-DB nicht Multi-Connection-faehig | Niedrig | Niedrig | Test mit File-DB |
| WAL-Mode erzeugt `.wal`-File (Backup-Risiko) | Niedrig | Niedrig | Backup-Service inkludiert `.wal` |

## 📅 Sprint-Einordnung

- **Vorbereitung** (Sprint 2.7, dieses Dokument): ✅
- **Implementation** (Sprint 3, parallel zu A-1 Refactor)

## 🔗 Verweise

- Code-Review: `docs/reports/2026-06-14_code-review.md` — C-6
- Haupt-Plan: `plans/2026-06-14_m4_findings.md` — Sprint 2
- Sub-Plan-Index: `plans/2026-06-14_m4_anhang_b_subplans.md`
- Original-Datei: `chormanager/data/database.py:1-243`
- Test-Datei (Soll): `tests/integration/test_db_concurrent_writes.py` (neu)

---

**Erstellt:** 2026-06-14 — Sprint 2.7
