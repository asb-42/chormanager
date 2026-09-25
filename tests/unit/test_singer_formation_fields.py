"""Phase 1 (M0): formation fields on the shared domain Singer.

Plan ref: docs/plans/2026-06-11_choraufstellung-migration.md, Phase 1
(Singer model unify). The domain Singer gains transient formation
fields (row/col/affinity) plus from_formation_dict(), so the web
backend (M1) can use ONE model. The fields are transient: the
SingerRepository must keep ignoring them (no schema change).
"""
from chormanager.domain.models import Singer


def test_formation_fields_default_to_unplaced():
    s = Singer()
    assert s.row == -1
    assert s.col == -1
    assert s.affinity == ""


def test_from_formation_dict_full_mapping():
    s = Singer.from_formation_dict(
        {
            "name": "Anna",
            "voice_group": "Sopran 1",
            "height": 170,
            "singer_id": "abc-123",
            "row": 2,
            "col": 3,
            "affinity": "partner-9",
            "affinity_uuid": "fallback-uuid",
            "external_id": "ext-1",
        }
    )
    assert s.short_name == "Anna"
    assert s.full_name == "Anna"
    assert s.voice_group == "Sopran 1"
    assert s.height == 170
    assert s.id == "abc-123"
    assert s.row == 2
    assert s.col == 3
    # "affinity" (partner id) wins over "affinity_uuid" fallback.
    assert s.affinity == "partner-9"
    assert s.affinity_uuid == "partner-9"


def test_from_formation_dict_affinity_uuid_fallback():
    s = Singer.from_formation_dict(
        {"name": "Bo", "voice_group": "Bass 2", "affinity_uuid": "u-1"}
    )
    assert s.affinity == "u-1"
    assert s.affinity_uuid == "u-1"


def test_from_formation_dict_missing_id_generates_uuid():
    s = Singer.from_formation_dict({"name": "Cy", "voice_group": "Alt 1"})
    assert s.id, "missing singer_id must yield a generated id"
    assert s.row == -1
    assert s.col == -1


def test_repository_ignores_transient_formation_fields():
    # No I/O: guards the SQL layer against schema leakage.
    from chormanager.domain.repositories.singer import SingerRepository

    assert "row" not in SingerRepository._SINGER_COLS
    assert "col" not in SingerRepository._SINGER_COLS
    assert "affinity" not in SingerRepository._SINGER_COLS


def test_to_formation_singer_still_unplaced_by_default():
    # to_formation_singer() builds a fresh formation singer; the
    # transient domain fields must not leak into it.
    s = Singer(full_name="Anna Muster", voice_group="Sopran 1", id="x-1")
    s.row = 4
    s.col = 5
    formation = s.to_formation_singer()
    assert formation.row == -1
    assert formation.col == -1
    assert formation.name == "Anna Muster"
