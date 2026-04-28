import tempfile
import os
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class TestAffinityBidirectional:
    def test_create_singer_with_affinity_sets_partner(self):
        from chormanager.data.database import Database
        from chormanager.domain.repository import SingerRepository

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, 'test.db')
            db = Database(db_path)
            db.connect()
            db.create_tables()

            repo = SingerRepository(db)

            singer_a = repo.create(full_name='Singer A')
            singer_b = repo.create(full_name='Singer B')

            assert singer_a.affinity_uuid is None
            assert singer_b.affinity_uuid is None

            repo.update(singer_a.id, affinity_uuid=singer_b.id)

            updated_a = repo.get_by_id(singer_a.id)
            updated_b = repo.get_by_id(singer_b.id)

            assert updated_a.affinity_uuid == singer_b.id
            assert updated_b.affinity_uuid == singer_a.id

            db.close()

    def test_change_affinity_clears_old_partner(self):
        from chormanager.data.database import Database
        from chormanager.domain.repository import SingerRepository

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, 'test.db')
            db = Database(db_path)
            db.connect()
            db.create_tables()

            repo = SingerRepository(db)

            singer_a = repo.create(full_name='Singer A')
            singer_b = repo.create(full_name='Singer B')
            singer_c = repo.create(full_name='Singer C')

            repo.update(singer_a.id, affinity_uuid=singer_b.id)
            updated_b = repo.get_by_id(singer_b.id)
            assert updated_b.affinity_uuid == singer_a.id

            repo.update(singer_a.id, affinity_uuid=singer_c.id)

            updated_a = repo.get_by_id(singer_a.id)
            updated_b = repo.get_by_id(singer_b.id)
            updated_c = repo.get_by_id(singer_c.id)

            assert updated_a.affinity_uuid == singer_c.id
            assert updated_b.affinity_uuid is None
            assert updated_c.affinity_uuid == singer_a.id

            db.close()

    def test_clear_affinity_clears_partner(self):
        from chormanager.data.database import Database
        from chormanager.domain.repository import SingerRepository

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, 'test.db')
            db = Database(db_path)
            db.connect()
            db.create_tables()

            repo = SingerRepository(db)

            singer_a = repo.create(full_name='Singer A')
            singer_b = repo.create(full_name='Singer B')

            repo.update(singer_a.id, affinity_uuid=singer_b.id)

            assert repo.get_by_id(singer_b.id).affinity_uuid == singer_a.id

            repo.update(singer_a.id, affinity_uuid=None)

            updated_a = repo.get_by_id(singer_a.id)
            updated_b = repo.get_by_id(singer_b.id)

            assert updated_a.affinity_uuid is None
            assert updated_b.affinity_uuid is None

            db.close()

    def test_bidirectional_already_set_does_nothing(self):
        from chormanager.data.database import Database
        from chormanager.domain.repository import SingerRepository

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, 'test.db')
            db = Database(db_path)
            db.connect()
            db.create_tables()

            repo = SingerRepository(db)

            singer_a = repo.create(full_name='Singer A')
            singer_b = repo.create(full_name='Singer B')

            repo.update(singer_a.id, affinity_uuid=singer_b.id)
            repo.update(singer_b.id, affinity_uuid=singer_a.id)

            updated_a = repo.get_by_id(singer_a.id)
            updated_b = repo.get_by_id(singer_b.id)

            assert updated_a.affinity_uuid == singer_b.id
            assert updated_b.affinity_uuid == singer_a.id

            repo.update(singer_a.id, affinity_uuid=singer_b.id)

            updated_a = repo.get_by_id(singer_a.id)
            updated_b = repo.get_by_id(singer_b.id)

            assert updated_a.affinity_uuid == singer_b.id
            assert updated_b.affinity_uuid == singer_a.id

            db.close()