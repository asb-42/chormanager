// M3.2: pure rubber-band intersection (DOM-free core of the
// grid-container mouse handlers in FormationEditor).

export interface RawBand {
  x0: number
  y0: number
  x1: number
  y1: number
}

export interface Rect {
  x0: number
  y0: number
  x1: number
  y1: number
}

export interface TileRect {
  id: string
  x: number
  y: number
  w: number
  h: number
}

export function normalizeRect(band: RawBand): Rect {
  return {
    x0: Math.min(band.x0, band.x1),
    y0: Math.min(band.y0, band.y1),
    x1: Math.max(band.x0, band.x1),
    y1: Math.max(band.y0, band.y1),
  }
}

export function tilesInRect(tiles: TileRect[], rect: Rect): string[] {
  return tiles
    .filter(
      (tile) =>
        tile.x < rect.x1 &&
        tile.x + tile.w > rect.x0 &&
        tile.y < rect.y1 &&
        tile.y + tile.h > rect.y0,
    )
    .map((tile) => tile.id)
}
