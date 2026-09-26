// M3-Spike: unit tests for the ported grid geometry
// (mirrors choraufstellung/core/grid_engine.py pixel_pos).
import { describe, expect, it } from 'vitest'
import {
  CELL_HEIGHT,
  CELL_WIDTH,
  MARGIN_LEFT,
  MARGIN_TOP,
  STAGGER_OFFSET,
  cellFromPoint,
  pixelPos,
} from '../gridMath'

describe('pixelPos', () => {
  it('places the origin cell at the margins', () => {
    expect(pixelPos(0, 0, false)).toEqual({ x: MARGIN_LEFT, y: MARGIN_TOP })
  })

  it('advances by cell pitch', () => {
    expect(pixelPos(2, 3, false)).toEqual({
      x: MARGIN_LEFT + 3 * CELL_WIDTH,
      y: MARGIN_TOP + 2 * CELL_HEIGHT,
    })
  })

  it('offsets odd rows when staggered', () => {
    expect(pixelPos(1, 0, true).x).toBe(MARGIN_LEFT + STAGGER_OFFSET)
    expect(pixelPos(0, 0, true).x).toBe(MARGIN_LEFT)
    expect(pixelPos(2, 0, true).x).toBe(MARGIN_LEFT)
  })
})

describe('cellFromPoint', () => {
  it('round-trips pixelPos', () => {
    expect(cellFromPoint(MARGIN_LEFT + 5, MARGIN_TOP + 5, 4, 5, false)).toEqual({
      row: 0,
      col: 0,
    })
    expect(
      cellFromPoint(
        MARGIN_LEFT + 2 * CELL_WIDTH + 10 + STAGGER_OFFSET,
        MARGIN_TOP + CELL_HEIGHT + 10,
        4,
        5,
        true,
      ),
    ).toEqual({ row: 1, col: 2 })
  })

  it('rejects out-of-bounds and negative points', () => {
    expect(cellFromPoint(0, 0, 4, 5, false)).toBeNull()
    expect(cellFromPoint(9999, 9999, 4, 5, false)).toBeNull()
    expect(cellFromPoint(MARGIN_LEFT, MARGIN_TOP + 4 * CELL_HEIGHT, 4, 5, false)).toBeNull()
  })
})
