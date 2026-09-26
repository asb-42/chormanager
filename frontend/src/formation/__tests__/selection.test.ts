// M3.2: pure rubber-band intersection (DOM-free core).
import { describe, expect, it } from 'vitest'
import { normalizeRect, tilesInRect } from '../selection'
import type { Rect, TileRect } from '../selection'

const TILES: TileRect[] = [
  { id: 'a', x: 80, y: 20, w: 120, h: 60 },
  { id: 'b', x: 210, y: 20, w: 120, h: 60 },
]

describe('normalizeRect', () => {
  it('orders corners regardless of drag direction', () => {
    const rect: Rect = normalizeRect({ x0: 300, y0: 100, x1: 100, y1: 20 })
    expect(rect).toEqual({ x0: 100, y0: 20, x1: 300, y1: 100 })
  })
})

describe('tilesInRect', () => {
  it('hits intersecting tiles only', () => {
    expect(tilesInRect(TILES, { x0: 0, y0: 0, x1: 150, y1: 100 })).toEqual(['a'])
  })

  it('hits multiple tiles in a wide band', () => {
    expect(tilesInRect(TILES, { x0: 0, y0: 0, x1: 400, y1: 100 })).toEqual(['a', 'b'])
  })

  it('ignores touch-only edges (strict overlap)', () => {
    expect(tilesInRect(TILES, { x0: 200, y0: 0, x1: 400, y1: 100 })).toEqual(['b'])
  })

  it('returns empty for a miss', () => {
    expect(tilesInRect(TILES, { x0: 0, y0: 500, x1: 400, y1: 600 })).toEqual([])
  })
})
