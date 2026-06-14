"""TDD RED: Regression tests for m6-FIX-A and m7-FIX-A — repository cleanup.

m6-FIX-A: ``ProjectRepository.set_active`` must wrap both UPDATEs in a
single ``db.transaction()`` so that two concurrent calls cannot leave
the database in a state where no project is active or two projects are
active.

m7-FIX-A: ``AvailabilityRepository.update`` must not use
``ON CONFLICT ... DO UPDATE`` (which creates a "ghost" row with a
freshly generated id when the original key is missing). Instead, the
method must first ``INSERT OR IGNORE`` and then run a separate
``UPDATE`` that uses the existing row's id.
"""
from __future__ import annotations

import sqlite3

import pytest


# ---------------------------------------------------------------------------
# m6-FIX-A: ProjectRepository.set_active transactional
# ---------------------------------------------------------------------------


def _make_db():
    """Create a fresh in-memory ``Database`` with the required tables."""
    from chormanager.data.database import Database
    db = Database(db_path=":memory:")
    db.connect()
    db.create_tables()
    return db


def _insert_project(db, project_id: str) -> None:
    now = "2026-01-01T00:00:00"
    db.execute(
        "INSERT INTO projects (id, name, is_active, created_at, updated_at) "
        "VALUES (?, ?, 0, ?, ?)",
        (project_id, f"P{project_id}", now, now),
    )
    db.commit()


def test_set_active_uses_transaction():
    from chormanager.domain.repository import ProjectRepository

    db = _make_db()
    _insert_project(db, "p1")
    _insert_project(db, "p2")
    _insert_project(db, "p3")
    repo = ProjectRepository(db)

    # Spy: record whether the transaction context manager was entered.
    tx_used = {"enter": 0, "exit": 0}

    real_tx = db.transaction

    @staticmethod  # type: ignore[arg-type]
    def _patched_tx(self):  # noqa: ARG001
        from contextlib import contextmanager

        @contextmanager
        def _cm():
            tx_used["enter"] += 1
            try:
                yield
            finally:
                tx_used["exit"] += 1
        return _cm()

    # Patch the *bound* method on the db instance
    from contextlib import contextmanager

    @contextmanager
    def spy_cm():
        tx_used["enter"] += 1
        try:
            yield
        finally:
            tx_used["exit"] += 1

    db.transaction = lambda: spy_cm()  # type: ignore[assignment]
    repo.set_active("p2")

    assert tx_used["enter"] == 1, "set_active did not wrap in db.transaction()"
    assert tx_used["exit"] == 1, "set_active did not properly exit the transaction"

    # Only p2 must be active.
    cur = db.execute("SELECT id FROM projects WHERE is_active = 1")
    rows = [r[0] if isinstance(r, tuple) else r["id"] for r in cur.fetchall()]
    assert rows == ["p2"]


def test_set_active_atomic_under_interleaved_calls():
    """Serial interleaving of set_active(p1) and set_active(p2) must result
    in exactly one active project, never zero, never two. We use a lock
    to serialize (the multi-threaded test belongs to C6-SUBPLAN-A)."""
    from chormanager.domain.repository import ProjectRepository

    db = _make_db()
    _insert_project(db, "p1")
    _insert_project(db, "p2")
    repo = ProjectRepository(db)

    # Interleave 20 calls in random order, all in the same thread.
    import random
    random.seed(42)
    sequence = ["p1" if random.random() < 0.5 else "p2" for _ in range(20)]
    for pid in sequence:
        repo.set_active(pid)

    # Exactly one active.
    cur = db.execute("SELECT COUNT(*) FROM projects WHERE is_active = 1")
    n = cur.fetchone()[0]
    assert n == 1
    # The last call's target must be the active one.
    cur = db.execute("SELECT id FROM projects WHERE is_active = 1")
    rows = [r[0] if isinstance(r, tuple) else r["id"] for r in cur.fetchall()]
    assert rows == [sequence[-1]]


# ---------------------------------------------------------------------------
# m7-FIX-A: AvailabilityRepository.update explicit INSERT OR IGNORE + UPDATE
# ---------------------------------------------------------------------------


def _make_avail_db():
    db = _make_db()
    now = "2026-01-01T00:00:00"
    # singer
    db.execute(
        "INSERT INTO singers (id, full_name, created_at, updated_at) "
        "VALUES (?, ?, ?, ?)",
        ("s1", "Max Mustermann", now, now),
    )
    # event (date and event_type are NOT NULL)
    db.execute(
        "INSERT INTO events (id, name, date, event_type, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        ("e1", "Weihnachtskonzert", "2026-12-24", "konzert", now, now),
    )
    db.commit()
    return db


def test_availability_update_uses_separate_update_statement():
    """The implementation must not rely on ``ON CONFLICT ... DO UPDATE``
    alone. It must run a separate ``UPDATE`` so the ``id`` column stays
    stable (no fresh UUID per call)."""
    from chormanager.domain.repository import AvailabilityRepository

    db = _make_avail_db()
    repo = AvailabilityRepository(db)

    # First call: creates the row.
    a1 = repo.update("s1", "e1", "yes")
    assert a1 is not None
    first_id = a1.id
    # Second call: must UPDATE the SAME row (not insert a new one).
    a2 = repo.update("s1", "e1", "no")
    assert a2 is not None
    assert a2.id == first_id, (
        "Second call created a new row with a new id; "
        "AvailabilityRepository.update must reuse the existing id."
    )

    # Exactly one row in the table.
    cur = db.execute(
        "SELECT COUNT(*) FROM availability WHERE singer_id='s1' AND event_id='e1'"
    )
    assert cur.fetchone()[0] == 1


def test_availability_update_changes_status():
    from chormanager.domain.repository import AvailabilityRepository

    db = _make_avail_db()
    repo = AvailabilityRepository(db)
    repo.update("s1", "e1", "yes")
    a = repo.update("s1", "e1", "no")
    assert a is not None
    assert a.status == "no"
