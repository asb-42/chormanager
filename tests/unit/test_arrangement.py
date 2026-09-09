"""Tests for core arrangement algorithms."""

import pytest
from dataclasses import dataclass
from chormanager.choraufstellung.core.arrangement import (
    arrange_by_height,
    arrange_men_outer,
    arrange_satb,
    arrange_sbta,
    arrange_s1s2b2b1t2t1a2a1,
    apply_placements,
)


@dataclass
class MockSinger:
    name: str
    voice_group: str
    height: int
    singer_id: str
    row: int = -1
    col: int = -1


def make_singers():
    """Create a set of mock singers for testing."""
    return [
        MockSinger("Anna", "Sopran 1", 170, "s1"),
        MockSinger("Beate", "Sopran 2", 165, "s2"),
        MockSinger("Clara", "Alt 1", 160, "s3"),
        MockSinger("Dora", "Alt 2", 155, "s4"),
        MockSinger("Erik", "Tenor 1", 180, "s5"),
        MockSinger("Frank", "Tenor 2", 175, "s6"),
        MockSinger("Gustav", "Bass 1", 185, "s7"),
        MockSinger("Heinrich", "Bass 2", 190, "s8"),
    ]


class TestArrangeByHeight:
    def test_tallest_first(self):
        """Should place tallest singer first (top-left)."""
        singers = make_singers()
        placements = arrange_by_height(singers, 4, 2)

        assert len(placements) == 8
        # Heinrich (190) should be first
        assert placements[0] == ("s8", 0, 0)
        # Gustav (185) second
        assert placements[1] == ("s7", 0, 1)

    def test_empty_singers(self):
        """Should handle empty list."""
        assert arrange_by_height([], 4, 2) == []

    def test_all_placed(self):
        """Should place all singers when grid has space."""
        singers = make_singers()
        placements = arrange_by_height(singers, 4, 2)
        placed_ids = {p[0] for p in placements}
        assert len(placed_ids) == 8


class TestArrangeMenOuter:
    def test_basses_on_left(self):
        """Should place first half of basses on column 0."""
        singers = make_singers()
        placements = arrange_men_outer(singers, 4, 6)

        bass_placements = [(sid, r, c) for sid, r, c in placements if c == 0]
        assert len(bass_placements) == 1  # Half of 2 basses (integer division)

    def test_tenors_on_right(self):
        """Should place second half of tenors on cols-2."""
        singers = make_singers()
        placements = arrange_men_outer(singers, 4, 6)

        # tenors[len(tenors)//2:] go to col = cols - 2 = 4
        tenor_placements = [(sid, r, c) for sid, r, c in placements if c == 4]
        assert len(tenor_placements) == 1  # Second half of 2 tenors


class TestArrangeSatb:
    def test_satb_order(self):
        """Should order by Sopran, Alt, Tenor, Bass."""
        singers = make_singers()
        placements = arrange_satb(singers, 4, 2)

        assert len(placements) == 8
        # First should be Sopran (Anna, Beate)
        assert placements[0][0] == "s1"  # Anna Sopran 1
        assert placements[1][0] == "s2"  # Beate Sopran 2


class TestArrangeSbta:
    def test_sbta_order(self):
        """Should order by Sopran, Bass, Tenor, Alt."""
        singers = make_singers()
        placements = arrange_sbta(singers, 4, 2)

        assert len(placements) == 8
        # Order: Sopran (sorted) + Bass (sorted) + Tenor (sorted) + Alt (sorted)
        assert placements[0][0] == "s1"  # Anna Sopran 1
        assert placements[1][0] == "s2"  # Beate Sopran 2
        assert placements[2][0] == "s7"  # Gustav Bass 1 (sorted by name)
        assert placements[3][0] == "s8"  # Heinrich Bass 2


class TestArrangeS1S2B2B1T2T1A2A1:
    def test_specific_order(self):
        """Should order S1-S2-B2-B1-T2-T1-A2-A1."""
        singers = make_singers()
        placements = arrange_s1s2b2b1t2t1a2a1(singers, 4, 2)

        assert len(placements) == 8
        # Check order matches expected
        singer_ids = [p[0] for p in placements]
        assert singer_ids[0] == "s1"  # Anna Sopran 1
        assert singer_ids[1] == "s2"  # Beate Sopran 2
        assert singer_ids[2] == "s8"  # Heinrich Bass 2
        assert singer_ids[3] == "s7"  # Gustav Bass 1


class TestApplyPlacements:
    def test_applies_to_singers(self):
        """Should modify singer row/col based on placements."""
        singers = make_singers()
        placements = [("s1", 2, 3), ("s5", 0, 1)]

        apply_placements(singers, placements)

        assert singers[0].row == 2  # Anna
        assert singers[0].col == 3
        assert singers[4].row == 0  # Erik
        assert singers[4].col == 1

    def test_unplaced_singers_reset(self):
        """Should set row/col to -1 for unplaced singers."""
        singers = make_singers()
        placements = [("s1", 0, 0)]  # Only place Anna

        apply_placements(singers, placements)

        assert singers[0].row == 0  # Anna placed
        assert singers[1].row == -1  # Beate not placed
        assert singers[2].row == -1  # Clara not placed
