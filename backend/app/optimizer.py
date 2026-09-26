"""Monorepo bridge: reuse the Qt-free ``choraufstellung/core`` rules.

Analyse §3.3 — the arrangement rules run server-side, unchanged.
``core`` is imported by path (no Qt package ``__init__`` involved);
the backend always runs from the repo root (see backend/README).
"""
import sys
from pathlib import Path
from typing import Dict, List, Tuple

_core_dir = str(
    Path(__file__).resolve().parents[2] / "chormanager" / "choraufstellung"
)
if _core_dir not in sys.path:
    sys.path.insert(0, _core_dir)

from core.rules import RULE_REGISTRY, SingerRef  # noqa: E402


def valid_rule_ids() -> List[str]:
    """Return the sorted registry keys (for validation/docs)."""
    return sorted(RULE_REGISTRY)


def run_preview(
    singers: List[Dict],
    positions: Dict[str, Tuple[int, int]],
    rows: int,
    cols: int,
    staggered: bool,
    rule_ids: List[str],
) -> Tuple[List[Dict], int, float, List[str]]:
    """Apply rules sequentially over ``SingerRef``\ s (no persistence).

    Args:
        singers: Stored singer dicts (``singer_id``, ``name``,
            ``voice_group``, ``height``, ``affinity``).
        positions: ``singer_id`` → ``(row, col)`` (``-1/-1`` unplaced).
        rows/cols/staggered: Grid dimensions.
        rule_ids: Registry keys in application order.

    Returns:
        Tuple of (placements ``[{singer_id, row, col}]``, total
        ``swap_count``, total ``cost``, per-rule messages).

    Raises:
        KeyError: for unknown rule ids (caller maps to 422).
    """
    refs = [
        SingerRef(
            singer_id=item["singer_id"],
            name=item.get("name") or "",
            voice_group=item.get("voice_group") or "",
            height=int(item.get("height") or 0),
            row=positions.get(item["singer_id"], (-1, -1))[0],
            col=positions.get(item["singer_id"], (-1, -1))[1],
            affinity=item.get("affinity") or "",
        )
        for item in singers
    ]
    swaps = 0
    cost = 0.0
    messages: List[str] = []
    for rule_id in rule_ids:
        try:
            rule = RULE_REGISTRY[rule_id]
        except KeyError:
            raise KeyError(f"unknown rule: {rule_id}") from None
        result = rule.apply(refs, rows, cols, staggered)
        refs = result.singers
        swaps += result.swap_count
        cost += result.cost
        messages.append(result.message)
    placements = [
        {"singer_id": ref.singer_id, "row": ref.row, "col": ref.col}
        for ref in refs
    ]
    return placements, swaps, cost, messages
