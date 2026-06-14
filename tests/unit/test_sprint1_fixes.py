"""Sprint 1 Regression-Tests (P0-Cluster).

Tests for the fixes applied in Sprint 1.5 (R1/R2/R4/R5) and Sprint 1.6 (S1).
All tests are headless (no Qt display required).

Naming convention: test_<finding-id>_<short-description>
"""
from __future__ import annotations

import sqlite3
import tempfile
import os
import pytest

from chormanager.data.database import Database
from chormanager.domain.repository import (
    SingerRepository,
    EventRepository,
    ProjectRepository,
    AvailabilityRepository,
    _whitelist_kwargs,
)


# ============================================================================
# S-1: SQL-Whitelist (Sprint 1.6)
# ============================================================================

class TestSQLWhitelistHelper:
    """Tests for the module-level _whitelist_kwargs helper (S-1)."""

    def test_whitelist_accepts_known_columns(self):
        result = _whitelist_kwargs(
            {"id": "1", "name": "Foo"},
            allowed=["id", "name"],
        )
        assert result == {"id": "1", "name": "Foo"}

    def test_whitelist_raises_on_unknown_column(self):
        with pytest.raises(ValueError) as exc_info:
            _whitelist_kwargs(
                {"id": "1", "is_admin": 1},
                allowed=["id", "name"],
            )
        assert "is_admin" in str(exc_info.value)
        assert "Allowed" in str(exc_info.value)

    def test_whitelist_preserves_order(self):
        kwargs = {"z": 1, "a": 2, "m": 3}
        allowed = ["z", "a", "m"]
        result = _whitelist_kwargs(kwargs, allowed)
        assert list(result.keys()) == ["z", "a", "m"]


class TestSingerRepositorySQLInjection:
    """S-1 Fix: SingerRepository rejects unknown columns on create/update."""

    @pytest.fixture
    def db(self):
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        d = Database(db_path=path)
        d.connect()
        d.create_tables()
        yield d
        d.close()
        os.unlink(path)

    def test_create_rejects_unknown_columns(self, db):
        repo = SingerRepository(db)
        with pytest.raises(ValueError) as exc_info:
            repo.create(
                full_name="Hacker",
                voice_group="Sopran 1",
                is_admin=1,           # ← injection attempt
                password="secret",    # ← injection attempt
            )
        assert "is_admin" in str(exc_info.value)
        assert "password" in str(exc_info.value)

    def test_create_accepts_valid_columns(self, db):
        repo = SingerRepository(db)
        singer = repo.create(
            full_name="Real Singer",
            voice_group="Sopran 1",
            email="real@example.com",
        )
        assert singer.full_name == "Real Singer"
        assert singer.voice_group == "Sopran 1"
        assert singer.email == "real@example.com"

    def test_update_rejects_unknown_columns(self, db):
        repo = SingerRepository(db)
        singer = repo.create(full_name="X", voice_group="Sopran 1")
        with pytest.raises(ValueError):
            repo.update(singer.id, is_admin=1, full_name="Y")


class TestEventRepositorySQLInjection:
    """S-1 Fix: EventRepository rejects unknown columns."""

    @pytest.fixture
    def db(self):
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        d = Database(db_path=path)
        d.connect()
        d.create_tables()
        yield d
        d.close()
        os.unlink(path)

    def test_create_rejects_unknown_columns(self, db):
        repo = EventRepository(db)
        with pytest.raises(ValueError):
            repo.create(
                name="Concert",
                date="2026-12-24",
                event_type="Weihnachtskonzert",
                evil_col="x",  # should fail
            )

    def test_create_accepts_valid_columns(self, db):
        repo = EventRepository(db)
        event = repo.create(
            name="Konzert",
            date="2026-12-24",
            event_type="Weihnachtskonzert",
        )
        assert event.name == "Konzert"


class TestProjectRepositorySQLInjection:
    """S-1 Fix: ProjectRepository rejects unknown columns."""

    @pytest.fixture
    def db(self):
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        d = Database(db_path=path)
        d.connect()
        d.create_tables()
        yield d
        d.close()
        os.unlink(path)

    def test_create_rejects_unknown_columns(self, db):
        repo = ProjectRepository(db)
        with pytest.raises(ValueError):
            repo.create(
                name="X",
                injected_col="x",  # should be rejected
            )

    def test_update_rejects_unknown_columns(self, db):
        repo = ProjectRepository(db)
        project = repo.create(name="P")
        with pytest.raises(ValueError):
            repo.update(project.id, evil=1)


class TestAvailabilityRepositorySQLInjection:
    """S-1 Fix: AvailabilityRepository rejects unknown columns."""

    @pytest.fixture
    def db(self):
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        d = Database(db_path=path)
        d.connect()
        d.create_tables()
        yield d
        d.close()
        os.unlink(path)

    def test_create_rejects_unknown_columns(self, db):
        # Need a singer and an event first to satisfy FKs (not enforced without PRAGMA)
        sr = SingerRepository(db)
        er = EventRepository(db)
        singer = sr.create(full_name="S", voice_group="Sopran 1")
        event = er.create(name="E", date="2026-12-24", event_type="X")

        ar = AvailabilityRepository(db)
        with pytest.raises(ValueError):
            ar.create(
                singer_id=singer.id,
                event_id=event.id,
                status="yes",
                evil_col="x",  # should be rejected
            )


# ============================================================================
# R-1: AffinityRule Bounds-Check via GridEngine (Sprint 1.5)
# ============================================================================

class TestAffinityRuleBoundsCheck:
    """R-1 Fix: AffinityRule uses GridEngine.is_valid_position as a gate."""

    def test_apply_with_grid_engine_runs(self):
        from chormanager.choraufstellung.core.rules import (
            AffinityRule,
            SingerRef,
        )
        from chormanager.choraufstellung.core.grid_engine import (
            GridEngine,
            GridConfig,
        )

        # 4 singers in 2x4 grid
        singers = [
            SingerRef(
                singer_id=str(i),
                name=f"S{i}",
                voice_group="Sopran 1",
                height=170,
                row=0,
                col=i,
            )
            for i in range(4)
        ]
        ge = GridEngine(GridConfig(rows=2, cols=4, staggered=False))
        rule = AffinityRule()
        result = rule.apply(
            singers,
            rows=2,
            cols=4,
            staggered=False,
            grid_engine=ge,
        )
        assert result.success

    def test_apply_without_grid_engine_still_works_fallback(self):
        """Default-Aufruf ohne grid_engine-Argument funktioniert (Fallback)."""
        from chormanager.choraufstellung.core.rules import (
            AffinityRule,
            SingerRef,
        )

        singers = [
            SingerRef(
                singer_id=str(i),
                name=f"S{i}",
                voice_group="Sopran 1",
                height=170,
                row=0,
                col=i,
            )
            for i in range(4)
        ]
        rule = AffinityRule()
        result = rule.apply(singers, rows=2, cols=4, staggered=False)
        assert result.success

    def test_grid_engine_rejects_out_of_bounds(self):
        """is_valid_position lehnt Out-of-bounds-Positionen ab."""
        from chormanager.choraufstellung.core.grid_engine import (
            GridEngine,
            GridConfig,
        )

        ge = GridEngine(GridConfig(rows=2, cols=4, staggered=False))
        assert ge.is_valid_position(0, 0) is True
        assert ge.is_valid_position(1, 3) is True
        assert ge.is_valid_position(-1, 0) is False
        assert ge.is_valid_position(2, 0) is False
        assert ge.is_valid_position(0, 4) is False
        assert ge.is_valid_position(0, -1) is False


# ============================================================================
# R-2: VoiceGroupCohesionRule Sanity-Asserts (Sprint 1.5)
# ============================================================================

class TestVoiceGroupCohesionRuleSanityAsserts:
    """R-2 Fix: VoiceGroupCohesionRule enthaelt Sanity-Asserts."""

    def test_apply_with_different_singers_works(self):
        from chormanager.choraufstellung.core.rules import (
            VoiceGroupCohesionRule,
            SingerRef,
        )

        singers = [
            SingerRef(
                singer_id="1",
                name="A",
                voice_group="Sopran 1",
                height=170,
                row=0,
                col=0,
            ),
            SingerRef(
                singer_id="2",
                name="B",
                voice_group="Sopran 1",
                height=170,
                row=0,
                col=2,
            ),
        ]
        rule = VoiceGroupCohesionRule()
        result = rule.apply(singers, rows=2, cols=4, staggered=False)
        assert result.success

    def test_apply_with_three_voice_group_members(self):
        from chormanager.choraufstellung.core.rules import (
            VoiceGroupCohesionRule,
            SingerRef,
        )

        singers = [
            SingerRef(
                singer_id=str(i),
                name=f"S{i}",
                voice_group="Alt 1",
                height=170,
                row=i % 2,
                col=i,
            )
            for i in range(3)
        ]
        rule = VoiceGroupCohesionRule()
        result = rule.apply(singers, rows=2, cols=4, staggered=False)
        assert result.success
