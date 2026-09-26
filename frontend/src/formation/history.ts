// M3: undo/redo history over snapshots (map + dims + stagger).
// Pure logic; the page persists snapshots via placements PUT.

import type { PlacementMap } from './placements'

export interface Snapshot {
  map: PlacementMap
  rows: number
  cols: number
  staggered: boolean
}

export interface History {
  past: Snapshot[]
  future: Snapshot[]
}

export const HISTORY_LIMIT = 100

export function clearHistory(): History {
  return { past: [], future: [] }
}

export function pushHistory(
  history: History,
  current: Snapshot,
  cap: number = HISTORY_LIMIT,
): History {
  const past = [...history.past, current].slice(-cap)
  return { past, future: [] }
}

export function undoHistory(
  history: History,
  current: Snapshot,
): { history: History; snapshot: Snapshot } | null {
  if (history.past.length === 0) return null
  const snapshot = history.past[history.past.length - 1]
  return {
    history: {
      past: history.past.slice(0, -1),
      future: [current, ...history.future],
    },
    snapshot,
  }
}

export function redoHistory(
  history: History,
  current: Snapshot,
): { history: History; snapshot: Snapshot } | null {
  if (history.future.length === 0) return null
  const [snapshot, ...future] = history.future
  return {
    history: { past: [...history.past, current], future },
    snapshot,
  }
}
