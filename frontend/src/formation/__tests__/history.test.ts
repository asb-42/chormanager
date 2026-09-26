// Editor-Undo/Redo: reine History-Logik (Desktop: core/commands).
// Snapshots enthalten Map + Dims, damit Undo auch Resize zurücknimmt.
import { describe, expect, it } from 'vitest'
import { clearHistory, pushHistory, redoHistory, undoHistory } from '../history'
import type { Snapshot } from '../history'

const A: Snapshot = { map: { 's-1': { row: 0, col: 0 } }, rows: 4, cols: 5, staggered: false }
const B: Snapshot = { map: { 's-1': { row: 1, col: 1 } }, rows: 4, cols: 5, staggered: false }
const C: Snapshot = { map: { 's-1': { row: 1, col: 1 } }, rows: 3, cols: 5, staggered: false }

describe('pushHistory', () => {
  it('remembers the previous snapshot and clears redo', () => {
    const history = pushHistory({ past: [A], future: [C] }, B)
    expect(history.past).toEqual([A, B])
    expect(history.future).toEqual([])
  })

  it('caps the stack (Desktop: 100)', () => {
    const past = Array.from({ length: 100 }, () => A)
    const history = pushHistory({ past, future: [] }, B, 100)
    expect(history.past).toHaveLength(100)
    expect(history.past[99]).toEqual(B)
  })
})

describe('undoHistory/redoHistory', () => {
  it('round-trips incl. dims', () => {
    const undone = undoHistory({ past: [A], future: [] }, C)
    expect(undone?.snapshot).toEqual(A)
    const redone = redoHistory(undone!.history, A)
    expect(redone?.snapshot).toEqual(C)
  })

  it('returns null when empty', () => {
    expect(undoHistory(clearHistory(), A)).toBeNull()
    expect(redoHistory(clearHistory(), A)).toBeNull()
  })
})
