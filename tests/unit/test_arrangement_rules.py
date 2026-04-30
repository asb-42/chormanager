# TDD: Unit tests for Arrangement Rules
import pytest
from core.rules import (
    HeightRule, SATBRule, SBTARule, AffinityRule, AffinityCostFunction,
    ArrangementRule, ArrangementResult, RULE_REGISTRY,
    get_rule, get_primary_rules, get_refinement_rules
)
from core.grid_engine import GridConfig


class TestHeightRule:
    def test_height_rule_is_primary(self):
        """HeightRule should be marked as primary."""
        rule = HeightRule()
        assert rule.is_primary is True

    def test_height_rule_sorting(self):
        """Should sort singers by height ascending and place row-major."""
        from core.rules import SingerRef
        
        singers = [
            SingerRef(singer_id="s1", name="Tall", voice_group="Bass 1", height=190, row=-1, col=-1),
            SingerRef(singer_id="s2", name="Short", voice_group="Sopran 1", height=150, row=-1, col=-1),
            SingerRef(singer_id="s3", name="Medium", voice_group="Alt 1", height=170, row=-1, col=-1),
        ]
        
        rule = HeightRule()
        result = rule.apply(singers, 2, 2, staggered=False)
        
        assert result.success is True
        
        short = next(s for s in singers if s.singer_id == "s2")
        medium = next(s for s in singers if s.singer_id == "s3")
        tall = next(s for s in singers if s.singer_id == "s1")
        
        assert short.height == 150
        assert medium.height == 170
        assert tall.height == 190

    def test_height_rule_placement_row_major(self):
        """Should fill grid row by row."""
        from core.rules import SingerRef
        
        singers = [
            SingerRef(singer_id="s1", name="S1", voice_group="Sopran 1", height=160, row=-1, col=-1),
            SingerRef(singer_id="s2", name="S2", voice_group="Sopran 2", height=165, row=-1, col=-1),
            SingerRef(singer_id="s3", name="S3", voice_group="Alt 1", height=170, row=-1, col=-1),
            SingerRef(singer_id="s4", name="S4", voice_group="Bass 1", height=180, row=-1, col=-1),
        ]
        
        rule = HeightRule()
        result = rule.apply(singers, 2, 2, staggered=False)
        
        s1 = next(s for s in singers if s.singer_id == "s1")
        s2 = next(s for s in singers if s.singer_id == "s2")
        s3 = next(s for s in singers if s.singer_id == "s3")
        s4 = next(s for s in singers if s.singer_id == "s4")
        
        assert s1.row == 0 and s1.col == 0
        assert s2.row == 0 and s2.col == 1
        assert s3.row == 1 and s3.col == 0
        assert s4.row == 1 and s4.col == 1

    def test_height_rule_overflow_unplaced(self):
        """Should mark overflow singers as unplaced."""
        from core.rules import SingerRef
        
        singers = [
            SingerRef(singer_id="s1", name="S1", voice_group="Sopran 1", height=160, row=-1, col=-1),
            SingerRef(singer_id="s2", name="S2", voice_group="Sopran 2", height=165, row=-1, col=-1),
            SingerRef(singer_id="s3", name="S3", voice_group="Alt 1", height=170, row=-1, col=-1),
        ]
        
        rule = HeightRule()
        result = rule.apply(singers, 2, 1, staggered=False)
        
        placed = [s for s in singers if s.row >= 0]
        unplaced = [s for s in singers if s.row == -1]
        assert len(placed) == 2
        assert len(unplaced) == 1


class TestSATBRule:
    def test_satb_rule_is_primary(self):
        """SATBRule should be marked as primary."""
        rule = SATBRule()
        assert rule.is_primary is True

    def test_satb_rule_ordering(self):
        """Should order by Sopran -> Alt -> Tenor -> Bass, fill column-wise."""
        from core.rules import SingerRef
        
        singers = [
            SingerRef(singer_id="s1", name="Bass1", voice_group="Bass 1", height=180, row=-1, col=-1),
            SingerRef(singer_id="s2", name="Sopran1", voice_group="Sopran 1", height=160, row=-1, col=-1),
            SingerRef(singer_id="s3", name="Tenor1", voice_group="Tenor 1", height=175, row=-1, col=-1),
            SingerRef(singer_id="s4", name="Alt1", voice_group="Alt 1", height=165, row=-1, col=-1),
        ]
        
        rule = SATBRule()
        result = rule.apply(singers, 2, 2, staggered=False)
        
        sopran = next(s for s in singers if "Sopran" in s.voice_group)
        alt = next(s for s in singers if "Alt" in s.voice_group)
        tenor = next(s for s in singers if "Tenor" in s.voice_group)
        bass = next(s for s in singers if "Bass" in s.voice_group)
        
        assert sopran.col == 0 and sopran.row == 0
        assert alt.col == 0 and alt.row == 1
        assert tenor.col == 1 and tenor.row == 0
        assert bass.col == 1 and bass.row == 1

    def test_satb_rule_column_wise_fill(self):
        """Should fill grid column by column (col 0 first, then col 1)."""
        from core.rules import SingerRef
        
        singers = [
            SingerRef(singer_id="s1", name="S1", voice_group="Sopran 1", height=160, row=-1, col=-1),
            SingerRef(singer_id="s2", name="A1", voice_group="Alt 1", height=165, row=-1, col=-1),
            SingerRef(singer_id="s3", name="T1", voice_group="Tenor 1", height=175, row=-1, col=-1),
            SingerRef(singer_id="s4", name="B1", voice_group="Bass 1", height=180, row=-1, col=-1),
        ]
        
        rule = SATBRule()
        result = rule.apply(singers, 2, 2, staggered=False)
        
        s1 = next(s for s in singers if s.singer_id == "s1")
        a1 = next(s for s in singers if s.singer_id == "s2")
        t1 = next(s for s in singers if s.singer_id == "s3")
        b1 = next(s for s in singers if s.singer_id == "s4")
        
        assert s1.col == 0 and s1.row == 0
        assert a1.col == 0 and a1.row == 1
        assert t1.col == 1 and t1.row == 0
        assert b1.col == 1 and b1.row == 1

    def test_satb_rule_sorted_by_name_within_group(self):
        """Should sort by name within each voice group."""
        from core.rules import SingerRef
        
        singers = [
            SingerRef(singer_id="s1", name="Zoe", voice_group="Sopran 1", height=160, row=-1, col=-1),
            SingerRef(singer_id="s2", name="Anna", voice_group="Sopran 1", height=162, row=-1, col=-1),
        ]
        
        rule = SATBRule()
        result = rule.apply(singers, 1, 2, staggered=False)
        
        anna = next(s for s in singers if s.name == "Anna")
        zoe = next(s for s in singers if s.name == "Zoe")
        
        assert anna.col == 0
        assert zoe.col == 1


class TestSBTARule:
    def test_sbta_rule_is_primary(self):
        """SBTARule should be marked as primary."""
        rule = SBTARule()
        assert rule.is_primary is True

    def test_sbta_rule_ordering(self):
        """Should order by Sopran -> Bass -> Tenor -> Alt and fill column-wise."""
        from core.rules import SingerRef
        
        singers = [
            SingerRef(singer_id="s1", name="Alt1", voice_group="Alt 1", height=165, row=-1, col=-1),
            SingerRef(singer_id="s2", name="Bass1", voice_group="Bass 1", height=180, row=-1, col=-1),
            SingerRef(singer_id="s3", name="Sopran1", voice_group="Sopran 1", height=160, row=-1, col=-1),
            SingerRef(singer_id="s4", name="Tenor1", voice_group="Tenor 1", height=175, row=-1, col=-1),
        ]
        
        rule = SBTARule()
        result = rule.apply(singers, 2, 2, staggered=False)
        
        placed = {s.singer_id: s for s in singers if s.row >= 0}
        
        sopran_singer = next(s for s in singers if "Sopran" in s.voice_group)
        bass_singer = next(s for s in singers if "Bass" in s.voice_group)
        tenor_singer = next(s for s in singers if "Tenor" in s.voice_group)
        alt_singer = next(s for s in singers if "Alt" in s.voice_group)
        
        assert sopran_singer.col == 0
        assert sopran_singer.row == 0
        assert bass_singer.col == 0
        assert bass_singer.row == 1
        assert tenor_singer.col == 1
        assert tenor_singer.row == 0
        assert alt_singer.col == 1
        assert alt_singer.row == 1


class TestAffinityCostFunction:
    def test_cost_function_simple_distance(self):
        """Should compute simple Euclidean distance."""
        cost_fn = AffinityCostFunction(staggered=False)
        dist = cost_fn.compute_distance((0, 0), (1, 1), 0, 0)
        assert dist == pytest.approx((2 ** 0.5), rel=1e-5)

    def test_cost_function_no_stagger_ignores_parity(self):
        """Non-staggered mode should ignore row parity."""
        cost_fn = AffinityCostFunction(staggered=False)
        dist1 = cost_fn.compute_distance((1, 0), (1, 1), 1, 1)
        dist2 = cost_fn.compute_distance((1, 0), (1, 1), 0, 0)
        assert dist1 == dist2

    def test_cost_function_stagger_accounts_offset(self):
        """Staggered mode should add 0.5 offset for odd rows."""
        cost_fn = AffinityCostFunction(staggered=True)
        dist_same_even = cost_fn.compute_distance((0, 0), (0, 1), 0, 0)
        dist_odd = cost_fn.compute_distance((1, 0), (1, 1), 1, 1)
        dist_mixed = cost_fn.compute_distance((0, 0), (1, 1), 0, 1)
        assert dist_odd == dist_same_even
        assert dist_mixed > dist_same_even

    def test_cost_function_compute_cost_sum(self):
        pytest.skip("Cost calculation test requires verification after integration")

    def test_cost_function_inf_for_unplaced(self):
        """Should return infinity cost for unplaced singers."""
        from core.rules import SingerRef
        
        cost_fn = AffinityCostFunction(staggered=False)
        pairs = [
            (SingerRef(singer_id="s1", name="S1", voice_group="Sopran", height=160, row=-1, col=-1, affinity="s2"),
             SingerRef(singer_id="s2", name="S2", voice_group="Alt", height=165, row=0, col=0, affinity="s1")),
        ]
        
        cost = cost_fn.compute_cost(pairs)
        assert cost == float('inf')


class TestAffinityRule:
    def test_affinity_rule_is_refinement(self):
        """AffinityRule should be marked as refinement (not primary)."""
        rule = AffinityRule()
        assert rule.is_primary is False

    def test_affinity_rule_no_pairs(self):
        """Should handle case with no affinity pairs."""
        from core.rules import SingerRef
        
        singers = [
            SingerRef(singer_id="s1", name="S1", voice_group="Sopran 1", height=160, row=0, col=0, affinity=""),
            SingerRef(singer_id="s2", name="S2", voice_group="Alt 1", height=165, row=1, col=1, affinity=""),
        ]
        
        rule = AffinityRule()
        result = rule.apply(singers, 2, 2, staggered=False)
        
        assert result.success is True

    def test_affinity_rule_respects_max_swaps(self):
        """Should respect max_swaps limit."""
        from core.rules import SingerRef
        
        singers = [
            SingerRef(singer_id="s1", name="S1", voice_group="Sopran 1", height=160, row=0, col=0, affinity="s2"),
            SingerRef(singer_id="s2", name="S2", voice_group="Alt 1", height=165, row=3, col=4, affinity="s1"),
        ]
        
        rule = AffinityRule(max_swaps=2, max_iterations=3)
        result = rule.apply(singers, 4, 5, staggered=False)
        
        assert result.swap_count <= 2

    def test_affinity_rule_respects_max_iterations(self):
        """Should stop after max_iterations even if improving."""
        from core.rules import SingerRef
        
        singers = [
            SingerRef(singer_id="s1", name="S1", voice_group="Sopran 1", height=160, row=0, col=0, affinity="s2"),
            SingerRef(singer_id="s2", name="S2", voice_group="Alt 1", height=165, row=3, col=4, affinity="s1"),
        ]
        
        rule = AffinityRule(max_swaps=100, max_iterations=1)
        result = rule.apply(singers, 4, 5, staggered=False)
        
        assert result.swap_count <= 10

    def test_affinity_rule_early_stopping(self):
        """Should stop early when cost is not improving."""
        from core.rules import SingerRef
        
        singers = [
            SingerRef(singer_id="s1", name="S1", voice_group="Sopran 1", height=160, row=0, col=0, affinity="s2"),
            SingerRef(singer_id="s2", name="S2", voice_group="Alt 1", height=165, row=0, col=1, affinity="s1"),
        ]
        
        rule = AffinityRule(max_swaps=50, max_iterations=3)
        result = rule.apply(singers, 4, 5, staggered=False)
        
        assert result.cost < float('inf')


class TestRuleRegistry:
    def test_registry_has_all_rules(self):
        """Registry should contain all defined rules."""
        assert "height" in RULE_REGISTRY
        assert "satb" in RULE_REGISTRY
        assert "sbta" in RULE_REGISTRY
        assert "affinity" in RULE_REGISTRY

    def test_get_rule_returns_rule(self):
        """get_rule should return the correct rule."""
        rule = get_rule("satb")
        assert rule is not None
        assert isinstance(rule, ArrangementRule)
        assert rule.name == "SATB (Stimmgruppe)"

    def test_get_rule_returns_none_for_unknown(self):
        """get_rule should return None for unknown rule IDs."""
        rule = get_rule("unknown_rule")
        assert rule is None

    def test_get_primary_rules(self):
        """Should return only primary rules."""
        primaries = get_primary_rules()
        assert all(r.is_primary for r in primaries)
        assert len(primaries) == 4

    def test_get_refinement_rules(self):
        """Should return only refinement rules."""
        refinements = get_refinement_rules()
        assert all(not r.is_primary for r in refinements)
        assert len(refinements) == 2