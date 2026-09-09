"""Pure arrangement algorithms for choir formation grid.

These functions take a list of singers and grid dimensions, then return
placement positions without modifying the singers directly. This allows
the algorithms to be tested independently of the UI layer.
"""

from typing import List, Tuple, Any


def _get_vg_str(voice_group) -> str:
    """Extract string value from voice group (enum or string)."""
    return voice_group.value if hasattr(voice_group, 'value') else str(voice_group)


def arrange_by_height(
    singers: List[Any], rows: int, cols: int
) -> List[Tuple[str, int, int]]:
    """Sort singers by height (tallest first) and place in grid.

    Args:
        singers: List of Singer objects with singer_id, height, voice_group, name.
        rows: Number of grid rows.
        cols: Number of grid columns.

    Returns:
        List of (singer_id, row, col) placements.
    """
    if not singers:
        return []

    sorted_singers = sorted(
        singers,
        key=lambda s: (-s.height, _get_vg_str(s.voice_group), s.name)
    )

    placements = []
    idx = 0
    for r in range(rows):
        for c in range(cols):
            if idx < len(sorted_singers):
                s = sorted_singers[idx]
                placements.append((s.singer_id, r, c))
                idx += 1
            else:
                break
    return placements


def arrange_men_outer(
    singers: List[Any], rows: int, cols: int
) -> List[Tuple[str, int, int]]:
    """Place men (Bass/Tenor) on outer columns, others in middle.

    Args:
        singers: List of Singer objects.
        rows: Number of grid rows.
        cols: Number of grid columns.

    Returns:
        List of (singer_id, row, col) placements.
    """
    if not singers:
        return []

    basses = [s for s in singers if "Bass" in _get_vg_str(s.voice_group)]
    tenors = [s for s in singers if "Tenor" in _get_vg_str(s.voice_group)]
    others = [s for s in singers if s not in basses and s not in tenors]

    basses.sort(key=lambda s: (_get_vg_str(s.voice_group), s.name))
    tenors.sort(key=lambda s: (_get_vg_str(s.voice_group), s.name))
    others.sort(key=lambda s: (_get_vg_str(s.voice_group), s.name))

    placements = []
    idx = 0

    for s in basses[:len(basses)//2]:
        placements.append((s.singer_id, idx % rows, 0))
        idx += 1
    for s in tenors[:len(tenors)//2]:
        placements.append((s.singer_id, idx % rows, 1))
        idx += 1
    for s in basses[len(basses)//2:]:
        placements.append((s.singer_id, idx % rows, cols - 1))
        idx += 1
    for s in tenors[len(tenors)//2:]:
        placements.append((s.singer_id, idx % rows, cols - 2))
        idx += 1

    mid_col_start = 2
    mid_col_end = cols - 3
    for s in others:
        col = mid_col_start + (idx % (mid_col_end - mid_col_start + 1))
        placements.append((s.singer_id, idx % rows, col))
        idx += 1

    return placements


def arrange_satb(
    singers: List[Any], rows: int, cols: int
) -> List[Tuple[str, int, int]]:
    """Place singers in SATB order (Sopran, Alt, Tenor, Bass).

    Args:
        singers: List of Singer objects.
        rows: Number of grid rows.
        cols: Number of grid columns.

    Returns:
        List of (singer_id, row, col) placements.
    """
    if not singers:
        return []

    sopran = [s for s in singers if "Sopran" in _get_vg_str(s.voice_group)]
    alt = [s for s in singers if "Alt" in _get_vg_str(s.voice_group)]
    tenor = [s for s in singers if "Tenor" in _get_vg_str(s.voice_group)]
    bass = [s for s in singers if "Bass" in _get_vg_str(s.voice_group)]

    for group in (sopran, alt, tenor, bass):
        group.sort(key=lambda s: s.name)

    ordered = sopran + alt + tenor + bass
    placements = []
    idx = 0

    for col in range(cols):
        for row in range(rows):
            if idx < len(ordered):
                placements.append((ordered[idx].singer_id, row, col))
                idx += 1
            else:
                break

    return placements


def arrange_sbta(
    singers: List[Any], rows: int, cols: int
) -> List[Tuple[str, int, int]]:
    """Place singers in SBTA order (Sopran, Bass, Tenor, Alt).

    Args:
        singers: List of Singer objects.
        rows: Number of grid rows.
        cols: Number of grid columns.

    Returns:
        List of (singer_id, row, col) placements.
    """
    if not singers:
        return []

    sopran = [s for s in singers if "Sopran" in _get_vg_str(s.voice_group)]
    alt = [s for s in singers if "Alt" in _get_vg_str(s.voice_group)]
    tenor = [s for s in singers if "Tenor" in _get_vg_str(s.voice_group)]
    bass = [s for s in singers if "Bass" in _get_vg_str(s.voice_group)]

    for group in (sopran, alt, tenor, bass):
        group.sort(key=lambda s: s.name)

    ordered = sopran + bass + tenor + alt
    placements = []
    idx = 0

    for col in range(cols):
        for row in range(rows):
            if idx < len(ordered):
                placements.append((ordered[idx].singer_id, row, col))
                idx += 1
            else:
                break

    return placements


def arrange_s1s2b2b1t2t1a2a1(
    singers: List[Any], rows: int, cols: int
) -> List[Tuple[str, int, int]]:
    """Place singers in S1-S2-B2-B1-T2-T1-A2-A1 order.

    Args:
        singers: List of Singer objects.
        rows: Number of grid rows.
        cols: Number of grid columns.

    Returns:
        List of (singer_id, row, col) placements.
    """
    if not singers:
        return []

    groups = {
        "Sopran 1": [], "Sopran 2": [],
        "Bass 2": [], "Bass 1": [],
        "Tenor 2": [], "Tenor 1": [],
        "Alt 2": [], "Alt 1": [],
    }

    for s in singers:
        vg = _get_vg_str(s.voice_group)
        if vg in groups:
            groups[vg].append(s)

    for vg_list in groups.values():
        vg_list.sort(key=lambda s: s.name)

    ordered = (
        groups["Sopran 1"] + groups["Sopran 2"]
        + groups["Bass 2"] + groups["Bass 1"]
        + groups["Tenor 2"] + groups["Tenor 1"]
        + groups["Alt 2"] + groups["Alt 1"]
    )

    placements = []
    idx = 0

    for col in range(cols):
        for row in range(rows):
            if idx < len(ordered):
                placements.append((ordered[idx].singer_id, row, col))
                idx += 1
            else:
                break

    return placements


def arrange_s1s2a1a2t1t2b1b2(
    singers: List[Any], rows: int, cols: int
) -> List[Tuple[str, int, int]]:
    """Place singers in S1-S2-A1-A2-T1-T2-B1-B2 order.

    Args:
        singers: List of Singer objects.
        rows: Number of grid rows.
        cols: Number of grid columns.

    Returns:
        List of (singer_id, row, col) placements.
    """
    if not singers:
        return []

    groups = {
        "Sopran 1": [], "Sopran 2": [],
        "Alt 1": [], "Alt 2": [],
        "Tenor 1": [], "Tenor 2": [],
        "Bass 1": [], "Bass 2": [],
    }

    for s in singers:
        vg = _get_vg_str(s.voice_group)
        if vg in groups:
            groups[vg].append(s)

    for vg_list in groups.values():
        vg_list.sort(key=lambda s: s.name)

    ordered = (
        groups["Sopran 1"] + groups["Sopran 2"]
        + groups["Alt 1"] + groups["Alt 2"]
        + groups["Tenor 1"] + groups["Tenor 2"]
        + groups["Bass 1"] + groups["Bass 2"]
    )

    placements = []
    idx = 0

    for col in range(cols):
        for row in range(rows):
            if idx < len(ordered):
                placements.append((ordered[idx].singer_id, row, col))
                idx += 1
            else:
                break

    return placements


def arrange_s1s2b1b2t1t2a1a2(
    singers: List[Any], rows: int, cols: int
) -> List[Tuple[str, int, int]]:
    """Place singers in S1-S2-B1-B2-T1-T2-A1-A2 order.

    Args:
        singers: List of Singer objects.
        rows: Number of grid rows.
        cols: Number of grid columns.

    Returns:
        List of (singer_id, row, col) placements.
    """
    if not singers:
        return []

    groups = {
        "Sopran 1": [], "Sopran 2": [],
        "Bass 1": [], "Bass 2": [],
        "Tenor 1": [], "Tenor 2": [],
        "Alt 1": [], "Alt 2": [],
    }

    for s in singers:
        vg = _get_vg_str(s.voice_group)
        if vg in groups:
            groups[vg].append(s)

    for vg_list in groups.values():
        vg_list.sort(key=lambda s: s.name)

    ordered = (
        groups["Sopran 1"] + groups["Sopran 2"]
        + groups["Bass 1"] + groups["Bass 2"]
        + groups["Tenor 1"] + groups["Tenor 2"]
        + groups["Alt 1"] + groups["Alt 2"]
    )

    placements = []
    idx = 0

    for col in range(cols):
        for row in range(rows):
            if idx < len(ordered):
                placements.append((ordered[idx].singer_id, row, col))
                idx += 1
            else:
                break

    return placements


def apply_placements(
    singers: List[Any], placements: List[Tuple[str, int, int]]
) -> None:
    """Apply placements to singers in-place.

    Args:
        singers: List of Singer objects to modify.
        placements: List of (singer_id, row, col) from arrange_* functions.
    """
    placed_ids = set()
    singer_map = {s.singer_id: s for s in singers}

    for singer_id, row, col in placements:
        if singer_id in singer_map:
            singer_map[singer_id].row = row
            singer_map[singer_id].col = col
            placed_ids.add(singer_id)

    for s in singers:
        if s.singer_id not in placed_ids:
            s.row = -1
            s.col = -1
