"""TDD RED: C4.2 \u2014 Dict-Index in ``AffinityRule._build_pairs``.

Previously, the inner loop
    ``for other in singers: if other.singer_id == s.affinity``
was O(n), making the whole method O(n\u00b2). For a 50-singer choir
with 20 affinity pairs, that's 2500 comparisons.

C4.2 (sub-task from subplan_optimizer_perf.md) builds a
``singer_id -> SingerRef`` dict once and looks up partners in O(1).
"""
from __future__ import annotations

import pytest


def _singer(singer_id: str, row: int = 0, col: int = 0, affinity: str = ""):
    from chormanager.choraufstellung.core.rules import SingerRef
    return SingerRef(
        singer_id=singer_id, name=singer_id,
        voice_group="Sopran 1", height=0, row=row, col=col, affinity=affinity,
    )


def test_build_pairs_returns_matched_pairs():
    from chormanager.choraufstellung.core.rules import AffinityRule
    rule = AffinityRule()
    pairs = rule._build_pairs([
        _singer("a", 0, 0, affinity="b"),
        _singer("b", 0, 1, affinity="a"),
    ])
    assert len(pairs) == 1


def test_build_pairs_ignores_unmatched_affinity():
    from chormanager.choraufstellung.core.rules import AffinityRule
    rule = AffinityRule()
    pairs = rule._build_pairs([
        _singer("a", 0, 0, affinity="ghost"),  # no partner
        _singer("b", 0, 1, affinity=""),
    ])
    assert pairs == []


def test_build_pairs_ignores_unplaced_singers():
    from chormanager.choraufstellung.core.rules import AffinityRule
    rule = AffinityRule()
    pairs = rule._build_pairs([
        _singer("a", -1, -1, affinity="b"),  # unplaced
        _singer("b", -1, -1, affinity="a"),  # unplaced
    ])
    assert pairs == []


def test_build_pairs_one_sided_affinity_does_not_create_pair():
    """Only mutual affinity counts. a->b without b->a is no pair."""
    from chormanager.choraufstellung.core.rules import AffinityRule
    rule = AffinityRule()
    pairs = rule._build_pairs([
        _singer("a", 0, 0, affinity="b"),
        _singer("b", 0, 1, affinity=""),  # does not reciprocate
    ])
    assert pairs == []


def test_build_pairs_scales_linearly():
    """Build 1000 singers with random mutual affinity. The method
    must complete in well under a second (O(n) thanks to dict index)."""
    import time
    from chormanager.choraufstellung.core.rules import AffinityRule
    rule = AffinityRule()
    # 1000 singers, all in a chain: 0<->1, 2<->3, ...
    singers = []
    for i in range(1000):
        if i % 2 == 0 and i + 1 < 1000:
            singers.append(_singer(str(i), i // 10, 0, affinity=str(i + 1)))
        else:
            singers.append(_singer(str(i), i // 10, 0, affinity=str(i - 1)))
    t0 = time.perf_counter()
    pairs = rule._build_pairs(singers)
    elapsed = time.perf_counter() - t0
    assert elapsed < 1.0, f"_build_pairs too slow: {elapsed:.2f}s"
    assert len(pairs) == 500  # 500 mutual pairs
