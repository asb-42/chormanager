# TDD: Unit tests for GridEngine
import pytest
from core.grid_engine import GridEngine, GridConfig, SingerRef


class TestGridEngineStaggeredOffset:
    def test_staggered_offset_even_row(self, grid_config_staggered):
        """Staggered offset should be 0 for even rows."""
        engine = GridEngine(grid_config_staggered)
        assert engine.stagger_offset(0) == 0
        assert engine.stagger_offset(2) == 0

    def test_staggered_offset_odd_row(self, grid_config_staggered):
        """Staggered offset should be OFFSET (65) for odd rows."""
        engine = GridEngine(grid_config_staggered)
        assert engine.stagger_offset(1) == 65
        assert engine.stagger_offset(3) == 65

    def test_staggered_offset_non_staggered(self, grid_config):
        """No offset when staggered is disabled."""
        engine = GridEngine(grid_config)
        assert engine.stagger_offset(0) == 0
        assert engine.stagger_offset(1) == 0
        assert engine.stagger_offset(2) == 0


class TestGridEnginePixelPos:
    def test_pixel_pos_no_stagger(self, grid_config):
        """Pixel position should be calculated correctly without staggered."""
        engine = GridEngine(grid_config)
        x, y = engine.pixel_pos(0, 0)
        assert x == 80
        assert y == 20

        x, y = engine.pixel_pos(1, 2)
        expected_x = 80 + 2 * 130
        expected_y = 20 + 1 * 80
        assert x == expected_x
        assert y == expected_y

    def test_pixel_pos_with_stagger(self, grid_config_staggered):
        """Pixel position should include offset for odd rows when staggered."""
        engine = GridEngine(grid_config_staggered)
        x, y = engine.pixel_pos(0, 0)
        assert x == 80
        assert y == 20

        x, y = engine.pixel_pos(1, 0)
        expected_x = 80 + 0 * 130 + 65
        expected_y = 20 + 1 * 80
        assert x == expected_x
        assert y == expected_y


class TestGridEngineValidation:
    def test_valid_position_inside_bounds(self, grid_config):
        """Positions inside bounds should be valid."""
        engine = GridEngine(grid_config)
        assert engine.is_valid_position(0, 0) is True
        assert engine.is_valid_position(3, 4) is True
        assert engine.is_valid_position(2, 3) is True

    def test_valid_position_outside_bounds(self, grid_config):
        """Positions outside bounds should be invalid."""
        engine = GridEngine(grid_config)
        assert engine.is_valid_position(-1, 0) is False
        assert engine.is_valid_position(0, -1) is False
        assert engine.is_valid_position(4, 0) is False
        assert engine.is_valid_position(0, 5) is False

    def test_valid_position_exactly_at_edge(self, grid_config):
        """Positions exactly at edges should be valid."""
        engine = GridEngine(grid_config)
        assert engine.is_valid_position(3, 4) is True
        assert engine.is_valid_position(0, 0) is True


class TestGridEngineOccupancy:
    def test_is_occupied_empty_grid(self, grid_config):
        """Empty grid should have no occupied positions."""
        engine = GridEngine(grid_config)
        placed = []
        assert engine.is_occupied(0, 0, placed) is False
        assert engine.is_occupied(1, 1, placed) is False

    def test_is_occupied_with_singers(self, grid_config):
        """Should correctly detect occupied positions."""
        engine = GridEngine(grid_config)
        placed = [
            SingerRef(singer_id="s1", row=0, col=0),
            SingerRef(singer_id="s2", row=1, col=2),
        ]
        assert engine.is_occupied(0, 0, placed) is True
        assert engine.is_occupied(1, 2, placed) is True
        assert engine.is_occupied(0, 1, placed) is False
        assert engine.is_occupied(2, 0, placed) is False

    def test_can_place_valid_empty(self, grid_config):
        """Should allow placing on empty valid position."""
        engine = GridEngine(grid_config)
        placed = [SingerRef(singer_id="s1", row=0, col=0)]
        assert engine.can_place(1, 1, placed) is True

    def test_can_place_occupied(self, grid_config):
        """Should not allow placing on occupied position."""
        engine = GridEngine(grid_config)
        placed = [SingerRef(singer_id="s1", row=0, col=0)]
        assert engine.can_place(0, 0, placed) is False

    def test_can_place_invalid(self, grid_config):
        """Should not allow placing on invalid position."""
        engine = GridEngine(grid_config)
        placed = []
        assert engine.can_place(-1, 0, placed) is False
        assert engine.can_place(0, 5, placed) is False


class TestGridEnginePlacement:
    def test_find_empty_slot_empty_grid(self, grid_config):
        """Should find first slot in empty grid."""
        engine = GridEngine(grid_config)
        slot = engine.find_empty_slot([])
        assert slot == (0, 0)

    def test_find_empty_slot_partial(self, grid_config):
        """Should find first empty slot in partially filled grid."""
        engine = GridEngine(grid_config)
        placed = [SingerRef(singer_id="s1", row=0, col=0)]
        slot = engine.find_empty_slot(placed)
        assert slot == (0, 1)

    def test_find_empty_slot_full(self, grid_config):
        """Should return None when grid is full."""
        engine = GridEngine(grid_config)
        placed = [
            SingerRef(singer_id=f"s{r}{c}", row=r, col=c)
            for r in range(grid_config.rows)
            for c in range(grid_config.cols)
        ]
        slot = engine.find_empty_slot(placed)
        assert slot is None

    def test_unplace_singer(self, grid_config):
        """Should correctly remove a singer from placed list."""
        engine = GridEngine(grid_config)
        placed = [
            SingerRef(singer_id="s1", row=0, col=0),
            SingerRef(singer_id="s2", row=1, col=1),
        ]
        engine.unplace_singer("s1", placed)
        assert len(placed) == 1
        assert placed[0].singer_id == "s2"


class TestGridEngineDistance:
    def test_compute_distance_simple(self, grid_config):
        """Should compute simple Euclidean distance."""
        engine = GridEngine(grid_config)
        dist = engine.compute_distance((0, 0), (1, 1))
        assert dist == pytest.approx((2 ** 0.5), rel=1e-5)

    def test_compute_distance_no_stagger(self, grid_config):
        """Distance should be same in non-staggered mode regardless of row parity."""
        engine = GridEngine(grid_config)
        dist1 = engine.compute_distance((0, 0), (1, 1), 0, 1)
        dist2 = engine.compute_distance((0, 0), (1, 1), 0, 0)
        assert dist1 == dist2

    def test_compute_distance_with_stagger(self, grid_config_staggered):
        """Distance should account for stagger offset - odd row has x+0.5."""
        engine = GridEngine(grid_config_staggered)

        dist_same_row_even = engine.compute_distance((0, 0), (0, 1), 0, 0)
        dist_mixed_parity = engine.compute_distance((0, 0), (1, 1), 0, 1)

        assert dist_mixed_parity > dist_same_row_even


class TestGridEngineNeighbors:
    def test_get_neighbors_center(self, grid_config):
        """Should return all 8 neighbors for a center position."""
        engine = GridEngine(grid_config)
        placed = [
            SingerRef(singer_id="s1", row=0, col=0),
            SingerRef(singer_id="s2", row=0, col=1),
            SingerRef(singer_id="s3", row=1, col=0),
        ]
        neighbors = engine.get_neighbors(1, 1, placed)
        neighbor_ids = {n.singer_id for n in neighbors}
        assert "s1" in neighbor_ids
        assert "s2" in neighbor_ids
        assert "s3" in neighbor_ids
        assert len(neighbors) == 3

    def test_get_neighbors_corner(self, grid_config):
        """Should return fewer neighbors at corner positions."""
        engine = GridEngine(grid_config)
        placed = [SingerRef(singer_id="s1", row=1, col=1)]
        neighbors = engine.get_neighbors(0, 0, placed)
        assert len(neighbors) == 1
        assert neighbors[0].singer_id == "s1"


class TestGridEngineGetSingerAt:
    def test_get_singer_at_found(self, grid_config):
        """Should return singer at given position."""
        engine = GridEngine(grid_config)
        placed = [
            SingerRef(singer_id="s1", row=0, col=0),
            SingerRef(singer_id="s2", row=1, col=1),
        ]
        singer = engine.get_singer_at(0, 0, placed)
        assert singer is not None
        assert singer.singer_id == "s1"

    def test_get_singer_at_not_found(self, grid_config):
        """Should return None when no singer at position."""
        engine = GridEngine(grid_config)
        placed = [SingerRef(singer_id="s1", row=0, col=0)]
        singer = engine.get_singer_at(1, 1, placed)
        assert singer is None


class TestGridEnginePositions:
    def test_occupied_positions(self, grid_config):
        """Should return all occupied positions."""
        engine = GridEngine(grid_config)
        placed = [
            SingerRef(singer_id="s1", row=0, col=0),
            SingerRef(singer_id="s2", row=1, col=1),
        ]
        occupied = engine.occupied_positions(placed)
        assert (0, 0) in occupied
        assert (1, 1) in occupied
        assert len(occupied) == 2

    def test_all_positions(self, grid_config):
        """Should return all possible positions in row-major order."""
        engine = GridEngine(grid_config)
        positions = engine.all_positions()
        assert len(positions) == grid_config.rows * grid_config.cols
        assert positions[0] == (0, 0)
        assert positions[-1] == (3, 4)

    def test_get_placed_count(self, grid_config):
        """Should return correct count of placed singers."""
        engine = GridEngine(grid_config)
        assert engine.get_placed_count([]) == 0
        placed = [
            SingerRef(singer_id="s1", row=0, col=0),
            SingerRef(singer_id="s2", row=1, col=1),
        ]
        assert engine.get_placed_count(placed) == 2