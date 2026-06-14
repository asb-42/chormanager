# AGENTS.md — chormanager/data/

## Purpose
The **SQLite layer**: ``Database`` (single-connection, legacy) and
``ConnectionPool`` (multi-connection, C-6). Owns the connection
plumbing; repositories in ``chormanager/domain/`` use the
connection primitives exposed here.

## Ownership
This folder is the **only** place that should call
``sqlite3.connect``. Repositories receive a connection via the
pool's ``with pool.connection() as conn:`` block and never
connect directly.

## Local Contracts

* **ConnectionPool + Database** are siblings. ``Database`` is the
  legacy single-connection entry point (kept for tests that
  need a deterministic single-connection setup). ``ConnectionPool``
  is the production entry point.
* **WAL + busy_timeout.** Every pooled connection runs in WAL
  mode with ``busy_timeout=5000``. New code must not toggle
  these off; they are the basis of the C-6 sub-plan.
* **commit() on context exit.** The pool commits any pending
  transaction when ``connection()`` returns the conn to the idle
  list. Callers must therefore wrap their work in a single
  ``with pool.connection() as c:`` block, not in a function that
  spans multiple acquires.
* **No schema knowledge.** Schema creation lives in
  ``Database.create_tables``. The pool is connection-only; it
  does **not** know about the singers / events / projects tables.

## Work Guidance

* When adding a new connection-related primitive (e.g. an
  in-memory ``:memory:`` pool for tests), add it as a method
  on ``ConnectionPool``, not as a free function.
* The pool is used by tabs via ``ensure_tab_pool`` /
  ``reset_tab_pool`` (see
  ``chormanager/ui/choraufstellung_launcher.py``). New tabs
  must use these helpers, not call ``connect_pool`` directly.

## Verification

```bash
QT_QPA_PLATFORM=offscreen python3 -m pytest \
    tests/unit/test_database.py \
    tests/unit/test_database_connection_pool.py \
    tests/unit/test_db_concurrent_writes.py \
    tests/unit/test_reload_after_restore.py \
    -q
```

## Child DOX Index

*(This folder is a leaf in the DOX tree. No children.)*
