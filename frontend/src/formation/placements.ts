// M3 proper: pure placement logic (testable core of the editor).
// Desktop semantics: formation_grid.dropEvent (single move with swap)
// + MoveGroupCommand (validated group move). The dragged singer must
// come first in the group array (delta is computed from its origin).

export interface Pos {
  row: number
  col: number
}

export type PlacementMap = Record<string, Pos | null>

export function occupantAt(
  map: PlacementMap,
  row: number,
  col: number,
): string | null {
  for (const [id, pos] of Object.entries(map)) {
    if (pos !== null && pos.row === row && pos.col === col) return id
  }
  return null
}

function inBounds(target: Pos, rows: number, cols: number): boolean {
  return target.row >= 0 && target.row < rows && target.col >= 0 && target.col < cols
}

export function applyMove(
  map: PlacementMap,
  singerId: string,
  target: Pos,
  rows: number,
  cols: number,
): PlacementMap | null {
  if (!inBounds(target, rows, cols)) return null
  const next = { ...map }
  const origin = next[singerId] ?? null
  const occupant = occupantAt(next, target.row, target.col)
  if (occupant && occupant !== singerId) {
    next[occupant] = origin
  }
  next[singerId] = target
  return next
}

export function applyGroupMove(
  map: PlacementMap,
  group: string[],
  target: Pos,
  rows: number,
  cols: number,
): PlacementMap | null {
  const dragged = group[0]
  const origin = dragged ? (map[dragged] ?? null) : null
  if (!dragged || !origin) return null
  if (!inBounds(target, rows, cols)) return null
  const delta = { row: target.row - origin.row, col: target.col - origin.col }
  const destinations = new Map<string, Pos>()
  for (const id of group) {
    const pos = map[id]
    if (!pos) return null
    const dest = { row: pos.row + delta.row, col: pos.col + delta.col }
    if (!inBounds(dest, rows, cols)) return null
    const occupant = occupantAt(map, dest.row, dest.col)
    if (occupant && !group.includes(occupant)) return null
    destinations.set(id, dest)
  }
  const next = { ...map }
  for (const [id, dest] of destinations) next[id] = dest
  return next
}

export function toPutPayload(
  map: PlacementMap,
): { singer_id: string; row: number; col: number }[] {
  return Object.entries(map)
    .filter((entry): entry is [string, Pos] => entry[1] !== null)
    .map(([singer_id, pos]) => ({ singer_id, row: pos.row, col: pos.col }))
}
