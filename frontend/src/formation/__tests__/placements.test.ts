// M3 proper: pure placement logic (unit-testable core of the editor).
// Desktop semantics: choraufstellung/widgets/formation_grid.py dropEvent
// (single move with swap) + MoveGroupCommand (validated group move).
import { describe, expect, it } from 'vitest'
import {
  applyGroupMove,
  applyMove,
  occupantAt,
  toPutPayload,
} from '../placements'
import type { PlacementMap } from '../placements'

const MAP: PlacementMap = {
  's-1': { row: 0, col: 0 },
  's-2': { row: 0, col: 1 },
  's-3': null,
}

describe('occupantAt', () => {
  it('finds the occupant or null', () => {
    expect(occupantAt(MAP, 0, 0)).toBe('s-1')
    expect(occupantAt(MAP, 2, 2)).toBeNull()
  })
})

describe('applyMove', () => {
  it('moves onto an empty cell', () => {
    const next = applyMove(MAP, 's-1', { row: 1, col: 1 }, 4, 5)
    expect(next?.['s-1']).toEqual({ row: 1, col: 1 })
    expect(next?.['s-2']).toEqual({ row: 0, col: 1 })
  })

  it('swaps with the occupant', () => {
    const next = applyMove(MAP, 's-1', { row: 0, col: 1 }, 4, 5)
    expect(next?.['s-1']).toEqual({ row: 0, col: 1 })
    expect(next?.['s-2']).toEqual({ row: 0, col: 0 })
  })

  it('moves pool singers in, swapping the occupant back to pool', () => {
    const next = applyMove(MAP, 's-3', { row: 0, col: 0 }, 4, 5)
    expect(next?.['s-3']).toEqual({ row: 0, col: 0 })
    expect(next?.['s-1']).toBeNull()
  })

  it('rejects out-of-bounds targets', () => {
    expect(applyMove(MAP, 's-1', { row: 9, col: 0 }, 4, 5)).toBeNull()
    expect(applyMove(MAP, 's-1', { row: -1, col: 0 }, 4, 5)).toBeNull()
  })
})

describe('applyGroupMove', () => {
  it('moves the group by delta', () => {
    const next = applyGroupMove(MAP, ['s-1', 's-2'], { row: 1, col: 1 }, 4, 5)
    expect(next?.['s-1']).toEqual({ row: 1, col: 1 })
    expect(next?.['s-2']).toEqual({ row: 1, col: 2 })
  })

  it('aborts at the border and on foreign occupants', () => {
    expect(applyGroupMove(MAP, ['s-1', 's-2'], { row: 9, col: 9 }, 4, 5)).toBeNull()
  })

  it('needs a placed drag origin', () => {
    expect(applyGroupMove(MAP, ['s-3'], { row: 1, col: 1 }, 4, 5)).toBeNull()
  })
})

describe('toPutPayload', () => {
  it('serializes only placed singers', () => {
    expect(toPutPayload(MAP)).toEqual([
      { singer_id: 's-1', row: 0, col: 0 },
      { singer_id: 's-2', row: 0, col: 1 },
    ])
  })
})
