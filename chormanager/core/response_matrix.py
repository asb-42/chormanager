"""Response-Matrix Aggregator for the project-wide availability export.

This module is pure-Python and Qt-free: it transforms a flat list of
singers, events, and availabilities into a structured
:class:`ResponseMatrix` that downstream renderers (ODT/PDF) can
consume without further computation.

The layout mirrors the ODT template used by the user
(``workdir/2026-04-19_Zusagen OKO.odt``):

  * Title at the top.
  * One column per event, sorted by date ascending.
  * Singers grouped by ``voice_group`` in the canonical
    :data:`VOICE_GROUP_ORDER` (Sopran 1, Sopran 2, Alt 1, Alt 2,
    Tenor 1, Tenor 2, Bass 1, Bass 2). Unknown groups are appended
    in their first-seen order.
  * Within a group, singers are sorted alphabetically by
    ``short_name`` (case-insensitive).
  * Status -> label mapping::

        yes         -> "X"
        no          -> "-"
        conditional -> "X?"
        unknown     -> "?"
        maybe       -> "~"
        none/empty  -> ""
  * Subtotals per group per event count "yes" responses only.
  * Grand totals (matrix-level) sum "yes" across all groups per event.

Optional ``singer_filter_ids`` lets the caller restrict the matrix to
the singers of the active Besetzung (Choraufstellung filter cascade).

.. note::
   This module lives in ``core/`` and must NOT import PyQt6. The UI
   layer wires the inputs together and calls the renderers.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Iterable, List, Optional, Sequence


# ---------------------------------------------------------------------------
# Public constants
# ---------------------------------------------------------------------------

#: Canonical voice-group ordering used in every export. Unknown groups
#: (anything not in this list) are appended in their first-seen order.
VOICE_GROUP_ORDER: List[str] = [
    "Sopran 1", "Sopran 2",
    "Alt 1", "Alt 2",
    "Tenor 1", "Tenor 2",
    "Bass 1", "Bass 2",
]


# Status -> short label for the matrix cell.
_STATUS_LABELS = {
    "yes": "X",
    "no": "-",
    "conditional": "X?",
    "unknown": "?",
    "maybe": "~",
}


@dataclass(frozen=True)
class ResponseCell:
    """A single cell in the response matrix.

    Attributes:
        status: The raw availability status (``yes``, ``no``, ...).
            ``"none"`` means the singer gave no response for this event.
        label: Short display label, e.g. ``"X"`` or ``"-"``. Empty
            string when there was no response.
    """
    status: str
    label: str


@dataclass(frozen=True)
class EventColumn:
    """A column in the response matrix corresponds to one event."""
    event_id: str
    label: str
    date: str  # ISO-8601, may be empty


@dataclass
class SingerRow:
    """A row in the response matrix corresponds to one singer."""
    singer_id: str
    name: str
    voice_group: str
    cells: List[ResponseCell] = field(default_factory=list)


@dataclass
class GroupBlock:
    """A group of SingerRow objects with the same voice_group.

    The block carries a per-event subtotal (count of "yes" responses).
    """
    voice_group: str
    rows: List[SingerRow] = field(default_factory=list)
    subtotal: List[int] = field(default_factory=list)


@dataclass
class ResponseMatrix:
    """The full aggregated response matrix."""
    title: str
    columns: List[EventColumn]
    groups: List[GroupBlock]
    totals: List[int]  # one grand total per event column


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _format_event_label(date_str: str, event_type: Optional[str]) -> str:
    """Build a column header like ``"15.05. OP"`` or ``"15.05."``.

    Falls back gracefully:
      * If ``date_str`` is empty, only the type is shown.
      * If the type is empty, only the date is shown.
      * If both are empty, an empty string is returned.
      * If the date is unparseable, the raw date string is used.
    """
    date_part = ""
    if date_str:
        try:
            # Accept "2026-05-15", "2026-05-15T18:00:00", etc.
            dt = datetime.fromisoformat(date_str[:19])
            date_part = dt.strftime("%d.%m.")
        except (ValueError, TypeError):
            date_part = date_str.strip()
    suffix = (event_type or "").strip()
    if date_part and suffix:
        return f"{date_part} {suffix}"
    if date_part:
        return date_part
    if suffix:
        return suffix
    return ""


def _label_for_status(status: Optional[str]) -> str:
    if not status:
        return ""
    return _STATUS_LABELS.get(status, "?")


def _name_sort_key(singer: Any) -> str:
    """Case-insensitive sort key on short_name (fallback: full_name)."""
    name = (
        getattr(singer, "short_name", None)
        or getattr(singer, "full_name", "")
        or ""
    )
    return name.casefold()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def build_response_matrix(
    singers: Sequence[Any],
    events: Sequence[Any],
    availabilities: Sequence[Any],
    title: str = "",
    singer_filter_ids: Optional[Iterable[str]] = None,
) -> ResponseMatrix:
    """Build a :class:`ResponseMatrix` from flat input lists.

    Args:
        singers: Singer-like objects (need ``id``, ``short_name`` (or
            ``full_name``), ``voice_group``).
        events: Event-like objects (need ``id``, ``date``,
            ``event_type``).
        availabilities: Availability-like objects (need ``singer_id``,
            ``event_id``, ``status``).
        title: Document title (project name).
        singer_filter_ids: Optional set of singer IDs to include. If
            ``None``, all singers are kept. Used to apply the active
            Besetzung filter.

    Returns:
        A fully-populated :class:`ResponseMatrix`.
    """
    # 1) Sort and project events into columns (ascending by date).
    def _event_dt(e: Any) -> str:
        return getattr(e, "date", "") or ""

    events_sorted = sorted(events, key=_event_dt)
    columns: List[EventColumn] = [
        EventColumn(
            event_id=getattr(e, "id", ""),
            label=_format_event_label(
                getattr(e, "date", "") or "",
                getattr(e, "event_type", None),
            ),
            date=getattr(e, "date", "") or "",
        )
        for e in events_sorted
    ]

    # 2) Build a fast lookup (singer_id, event_id) -> status
    status_lookup: dict = {}
    for a in availabilities:
        sid = getattr(a, "singer_id", None)
        eid = getattr(a, "event_id", None)
        st = getattr(a, "status", None)
        if sid is not None and eid is not None:
            status_lookup[(sid, eid)] = st

    # 3) Apply singer filter (Besetzung cascade)
    if singer_filter_ids is not None:
        filter_set = set(singer_filter_ids)
        singers = [s for s in singers if getattr(s, "id", None) in filter_set]

    # 4) Group singers by voice_group
    groups_map: dict = {}
    first_seen_order: List[str] = []
    for s in singers:
        vg = getattr(s, "voice_group", None) or "(keine)"
        if vg not in groups_map:
            groups_map[vg] = []
            first_seen_order.append(vg)
        groups_map[vg].append(s)

    # 5) Order groups: canonical first (in VOICE_GROUP_ORDER), then unknown
    #    groups in their first-seen order.
    canonical_present = [g for g in VOICE_GROUP_ORDER if g in groups_map]
    unknown_present = [g for g in first_seen_order if g not in VOICE_GROUP_ORDER]
    group_order = canonical_present + unknown_present

    # 6) Build GroupBlock / SingerRow / ResponseCell
    groups: List[GroupBlock] = []
    grand_totals: List[int] = [0] * len(columns)

    for vg in group_order:
        singers_in_group = sorted(groups_map[vg], key=_name_sort_key)
        block = GroupBlock(voice_group=vg)
        subtotal = [0] * len(columns)

        for s in singers_in_group:
            sid = getattr(s, "id", "")
            name = (
                getattr(s, "short_name", None)
                or getattr(s, "full_name", "")
                or sid
            )
            row = SingerRow(singer_id=sid, name=name, voice_group=vg)
            for col_idx, col in enumerate(columns):
                st = status_lookup.get((sid, col.event_id))
                if st == "yes":
                    subtotal[col_idx] += 1
                    grand_totals[col_idx] += 1
                row.cells.append(ResponseCell(
                    status=st or "none",
                    label=_label_for_status(st),
                ))
            block.rows.append(row)
        block.subtotal = subtotal
        groups.append(block)

    return ResponseMatrix(
        title=title,
        columns=columns,
        groups=groups,
        totals=grand_totals,
    )
