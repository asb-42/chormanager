# TDD RED: Unit tests for the Response-Matrix Aggregator
#
# The aggregator is pure-Python: it takes singers, events, and
# availabilities, and produces a structured matrix grouped by voice
# group with subtotals — independent of any rendering (PDF/ODT) and
# of Qt. This file defines the contract; tests fail until the
# implementation in chormanager/core/response_matrix.py is written.
import os
from datetime import date

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from chormanager.core.response_matrix import (
    build_response_matrix,
    ResponseMatrix,
    EventColumn,
    SingerRow,
    GroupBlock,
    ResponseCell,
    VOICE_GROUP_ORDER,
)


# --- Helpers ---------------------------------------------------------------
def _singer(id_, short_name, voice_group, full_name=""):
    """Build a minimal Singer-like object for testing.

    Singer is a dataclass with many fields, so we use a SimpleNamespace
    instead of constructing a real Singer.
    """
    from types import SimpleNamespace

    return SimpleNamespace(
        id=id_,
        short_name=short_name,
        full_name=full_name or short_name,
        voice_group=voice_group,
    )


def _event(id_, date_, event_type="", name=""):
    from types import SimpleNamespace

    return SimpleNamespace(
        id=id_,
        date=date_,
        event_type=event_type or None,
        name=name or id_,
        project_id="p1",
    )


def _avail(singer_id, event_id, status):
    from types import SimpleNamespace

    return SimpleNamespace(
        id=f"a-{singer_id}-{event_id}",
        singer_id=singer_id,
        event_id=event_id,
        status=status,
    )


# --- 1. Empty inputs -------------------------------------------------------
def test_empty_inputs_yields_empty_matrix():
    matrix = build_response_matrix(
        singers=[],
        events=[],
        availabilities=[],
    )
    assert isinstance(matrix, ResponseMatrix)
    assert matrix.title == ""
    assert matrix.columns == []
    assert matrix.groups == []
    assert matrix.totals == []  # row totals per event


# --- 2. Title is propagated -------------------------------------------------
def test_title_is_stored():
    matrix = build_response_matrix([], [], [], title="Konzert Hoffmann OKO")
    assert matrix.title == "Konzert Hoffmann OKO"


# --- 3. Columns are derived from events ------------------------------------
def test_columns_are_built_from_events_in_date_order():
    events = [
        _event("e1", "2026-05-15T18:00:00", "Probe"),
        _event("e2", "2026-05-10T18:00:00", "Probe"),
        _event("e3", "2026-06-01T20:00:00", "Konzert"),
    ]
    matrix = build_response_matrix([], events, [])
    # Should be sorted ascending by date
    assert [c.event_id for c in matrix.columns] == ["e2", "e1", "e3"]
    # Labels: "TT.MM." with optional event_type suffix
    assert matrix.columns[0].label == "10.05. Probe"
    assert matrix.columns[1].label == "15.05. Probe"
    assert matrix.columns[2].label == "01.06. Konzert"


def test_columns_omit_type_when_event_type_is_empty():
    events = [_event("e1", "2026-05-15T18:00:00", event_type=None)]
    matrix = build_response_matrix([], events, [])
    assert matrix.columns[0].label == "15.05."


# --- 4. Singers are grouped by voice_group in canonical order --------------
def test_singers_grouped_by_voice_group_in_canonical_order():
    singers = [
        _singer("s_bass1", "Karl", "Bass 1"),
        _singer("s_alt1", "Anna", "Alt 1"),
        _singer("s_sop1", "Eva", "Sopran 1"),
        _singer("s_ten1", "Anton", "Tenor 1"),
        _singer("s_unk",  "N.N.",  "Unknown"),
    ]
    matrix = build_response_matrix(singers, [], [])
    # Unknown voice groups are appended at the end
    assert [g.voice_group for g in matrix.groups] == [
        "Sopran 1", "Alt 1", "Tenor 1", "Bass 1", "Unknown",
    ]


# --- 5. Singers are sorted alphabetically within their group ---------------
def test_singers_sorted_alphabetically_within_group_by_short_name():
    singers = [
        _singer("s1", "Zoe",  "Sopran 1"),
        _singer("s2", "Anna", "Sopran 1"),
        _singer("s3", "Mia",  "Sopran 1"),
        _singer("s4", "Ben",  "Bass 1"),
        _singer("s5", "Adam", "Bass 1"),
    ]
    matrix = build_response_matrix(singers, [], [])
    assert [r.name for r in matrix.groups[0].rows] == ["Anna", "Mia", "Zoe"]
    assert [r.name for r in matrix.groups[1].rows] == ["Adam", "Ben"]


# --- 6. Cells are populated from availabilities -----------------------------
def test_cell_status_x_when_yes():
    events = [_event("e1", "2026-05-15T18:00:00")]
    singers = [_singer("s1", "Anna", "Sopran 1")]
    avs = [_avail("s1", "e1", "yes")]
    matrix = build_response_matrix(singers, events, avs)
    cell = matrix.groups[0].rows[0].cells[0]
    assert cell.status == "yes"
    assert cell.label == "X"


def test_cell_status_dash_when_no():
    events = [_event("e1", "2026-05-15T18:00:00")]
    singers = [_singer("s1", "Anna", "Sopran 1")]
    avs = [_avail("s1", "e1", "no")]
    matrix = build_response_matrix(singers, events, avs)
    cell = matrix.groups[0].rows[0].cells[0]
    assert cell.status == "no"
    assert cell.label == "-"


def test_cell_status_conditional_label():
    events = [_event("e1", "2026-05-15T18:00:00")]
    singers = [_singer("s1", "Anna", "Sopran 1")]
    avs = [_avail("s1", "e1", "conditional")]
    matrix = build_response_matrix(singers, events, avs)
    cell = matrix.groups[0].rows[0].cells[0]
    assert cell.status == "conditional"
    assert cell.label == "X?"


def test_cell_empty_when_no_availability_record():
    events = [_event("e1", "2026-05-15T18:00:00")]
    singers = [_singer("s1", "Anna", "Sopran 1")]
    matrix = build_response_matrix(singers, events, [])
    cell = matrix.groups[0].rows[0].cells[0]
    assert cell.status == "none"
    assert cell.label == ""


def test_unknown_status_maps_to_question_mark():
    events = [_event("e1", "2026-05-15T18:00:00")]
    singers = [_singer("s1", "Anna", "Sopran 1")]
    avs = [_avail("s1", "e1", "unknown_status")]
    matrix = build_response_matrix(singers, events, avs)
    cell = matrix.groups[0].rows[0].cells[0]
    assert cell.status == "unknown_status"
    assert cell.label == "?"


# --- 7. Subtotal counts only "yes" per group per event ---------------------
def test_subtotal_counts_yes_only():
    events = [_event("e1", "2026-05-15T18:00:00"), _event("e2", "2026-05-16T18:00:00")]
    singers = [
        _singer("s1", "Anna", "Sopran 1"),
        _singer("s2", "Bea",  "Sopran 1"),
        _singer("s3", "Cea",  "Sopran 1"),
    ]
    avs = [
        _avail("s1", "e1", "yes"),
        _avail("s2", "e1", "yes"),
        # s3 has no record for e1
        _avail("s1", "e2", "conditional"),  # X? does NOT count as yes
        _avail("s2", "e2", "no"),
        _avail("s3", "e2", "yes"),
    ]
    matrix = build_response_matrix(singers, events, avs)
    sop_group = matrix.groups[0]
    assert sop_group.subtotal == [2, 1]  # e1: 2 yes, e2: 1 yes


# --- 8. Grand totals across groups per event -------------------------------
def test_grand_totals_sum_yes_per_event_across_all_groups():
    events = [_event("e1", "2026-05-15T18:00:00")]
    singers = [
        _singer("s1", "A", "Sopran 1"),
        _singer("s2", "B", "Alt 1"),
    ]
    avs = [
        _avail("s1", "e1", "yes"),
        _avail("s2", "e1", "yes"),
    ]
    matrix = build_response_matrix(singers, events, avs)
    assert matrix.totals == [2]


def test_grand_totals_omit_empty_voice_groups():
    events = [_event("e1", "2026-05-15T18:00:00")]
    singers = [
        _singer("s1", "A", "Sopran 1"),
        # no Alt, no Tenor, no Bass singers
    ]
    avs = [_avail("s1", "e1", "yes")]
    matrix = build_response_matrix(singers, events, avs)
    # Only the non-empty group should be present
    assert [g.voice_group for g in matrix.groups] == ["Sopran 1"]


# --- 9. Singer filter (active Besetzung) ------------------------------------
def test_singer_filter_excludes_non_besetzung_singers():
    events = [_event("e1", "2026-05-15T18:00:00")]
    singers = [
        _singer("s1", "A", "Sopran 1"),
        _singer("s2", "B", "Sopran 1"),
    ]
    matrix = build_response_matrix(
        singers, events, [],
        singer_filter_ids={"s1"},  # only Anna is in the active Besetzung
    )
    assert len(matrix.groups) == 1
    assert len(matrix.groups[0].rows) == 1
    assert matrix.groups[0].rows[0].singer_id == "s1"


# --- 10. VOICE_GROUP_ORDER constant is canonical ----------------------------
def test_voice_group_order_constant_is_canonical():
    assert VOICE_GROUP_ORDER == [
        "Sopran 1", "Sopran 2",
        "Alt 1", "Alt 2",
        "Tenor 1", "Tenor 2",
        "Bass 1", "Bass 2",
    ]


# --- 11. Date label formatting ---------------------------------------------
def test_event_label_uses_tt_mm_format():
    events = [_event("e1", "2026-05-15T18:00:00", event_type="GP")]
    matrix = build_response_matrix([], events, [])
    assert matrix.columns[0].label == "15.05. GP"


def test_event_label_with_short_date():
    """A bare '2026-05-15' should still work."""
    events = [_event("e1", "2026-05-15", event_type=None)]
    matrix = build_response_matrix([], events, [])
    assert matrix.columns[0].label == "15.05."


def test_event_label_with_unparseable_date_keeps_raw_string():
    events = [_event("eXYZ", "not-a-date", event_type=None)]
    matrix = build_response_matrix([], events, [])
    # Unparseable dates are kept as-is (more informative than falling
    # back to the event id)
    assert matrix.columns[0].label == "not-a-date"


# --- 12. Event with no date produces an empty label ------------------------
def test_event_with_missing_date_has_empty_label():
    events = [_event("e1", "", event_type="Probe")]
    matrix = build_response_matrix([], events, [])
    # The date part is empty; the suffix may still be present
    assert matrix.columns[0].label == " Probe".strip() or matrix.columns[0].label == "Probe"
