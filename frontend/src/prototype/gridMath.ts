// M3-Spike: grid geometry ported from choraufstellung/core/grid_engine.py
// (GridConfig cell 130x80, stagger offset 65, margins 80/20).
// Throwaway with the prototype (deleted when the M3 editor lands).

export const CELL_WIDTH = 130
export const CELL_HEIGHT = 80
export const STAGGER_OFFSET = 65
export const MARGIN_LEFT = 80
export const MARGIN_TOP = 20

export interface Point {
  x: number
  y: number
}

export interface Cell {
  row: number
  col: number
}

export function staggerOffset(row: number, staggered: boolean): number {
  return staggered && row % 2 === 1 ? STAGGER_OFFSET : 0
}

export function pixelPos(row: number, col: number, staggered: boolean): Point {
  return {
    x: MARGIN_LEFT + col * CELL_WIDTH + staggerOffset(row, staggered),
    y: MARGIN_TOP + row * CELL_HEIGHT,
  }
}

export function cellFromPoint(
  x: number,
  y: number,
  rows: number,
  cols: number,
  staggered: boolean,
): Cell | null {
  const row = Math.floor((y - MARGIN_TOP) / CELL_HEIGHT)
  if (row < 0 || row >= rows) return null
  const col = Math.floor(
    (x - MARGIN_LEFT - staggerOffset(row, staggered)) / CELL_WIDTH,
  )
  if (col < 0 || col >= cols) return null
  return { row, col }
}
