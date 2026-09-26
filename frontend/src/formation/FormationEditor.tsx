// M3 proper: formation editor surface (dnd-kit, DOM tiles).
// M3.1: single move/swap + click select. M3.2: rubber band,
// group drag, search highlight (spike-proven, desktop semantics).
import { useEffect, useRef, useState } from 'react'
import {
  DndContext,
  PointerSensor,
  rectIntersection,
  useDraggable,
  useDroppable,
  useSensor,
  useSensors,
} from '@dnd-kit/core'
import type { DragEndEvent } from '@dnd-kit/core'
import { CSS } from '@dnd-kit/utilities'
import type { Pos, PlacementMap } from './placements'
import { applyGroupMove, applyMove } from './placements'
import type { StoredSinger } from '../api/client'
import { normalizeRect, tilesInRect } from './selection'
import type { RawBand } from './selection'
import { CELL_HEIGHT, CELL_WIDTH, MARGIN_LEFT, MARGIN_TOP, pixelPos } from './gridMath'

export interface EditorColors {
  [voiceGroup: string]: string
}

function parseCell(id: string): Pos | null {
  const match = /^cell-(\d+)-(\d+)$/.exec(id)
  if (!match) return null
  return { row: Number(match[1]), col: Number(match[2]) }
}

function Tile({
  singer,
  pos,
  staggered,
  selected,
  highlighted,
  color,
  onSelect,
}: {
  singer: StoredSinger
  pos: Pos
  staggered: boolean
  selected: boolean
  highlighted: boolean
  color: string
  onSelect: (id: string, toggle: boolean) => void
}) {
  const { attributes, listeners, setNodeRef, transform } = useDraggable({
    id: `tile-${singer.singer_id}`,
    data: { singerId: singer.singer_id },
  })
  const point = pixelPos(pos.row, pos.col, staggered)
  const outline = highlighted
    ? '3px solid #FF8C00'
    : selected
      ? '3px solid #0066cc'
      : '1px solid rgba(0,0,0,0.25)'
  return (
    <div
      ref={setNodeRef}
      data-tile={singer.singer_id}
      data-highlight={highlighted || undefined}
      onClick={(event) => onSelect(singer.singer_id, event.ctrlKey || event.metaKey)}
      style={{
        position: 'absolute',
        left: point.x,
        top: point.y,
        width: 120,
        height: 60,
        transform: CSS.Translate.toString(transform),
        background: color,
        outline,
        outlineOffset: -1,
        borderRadius: 8,
        padding: '6px 8px',
        fontSize: 12,
        lineHeight: 1.3,
        cursor: 'grab',
        boxShadow: transform
          ? '0 8px 20px rgba(0,0,0,0.3)'
          : '0 1px 3px rgba(0,0,0,0.2)',
        zIndex: transform ? 10 : 1,
        overflow: 'hidden',
        whiteSpace: 'nowrap',
      }}
      {...listeners}
      {...attributes}
    >
      <strong style={{ fontSize: 13, letterSpacing: '-0.01em' }}>{singer.name}</strong>
      <br />
      <span style={{ opacity: 0.85, fontSize: 11 }}>{singer.voice_group ?? ''}</span>
    </div>
  )
}

function PoolItem({ singer, color }: { singer: StoredSinger; color: string }) {
  const { attributes, listeners, setNodeRef, transform } = useDraggable({
    id: `pool-${singer.singer_id}`,
    data: { singerId: singer.singer_id },
  })
  return (
    <div
      ref={setNodeRef}
      style={{
        transform: CSS.Translate.toString(transform),
        background: color,
        border: '1px solid rgba(0,0,0,0.2)',
        borderRadius: 8,
        padding: '4px 8px',
        marginBottom: 6,
        fontSize: 12,
        cursor: 'grab',
        boxShadow: '0 1px 2px rgba(0,0,0,0.15)',
        overflow: 'hidden',
        whiteSpace: 'nowrap',
        textOverflow: 'ellipsis',
      }}
      {...listeners}
      {...attributes}
    >
      <strong style={{ fontWeight: 600 }}>{singer.name}</strong>{' '}
      <span style={{ opacity: 0.8 }}>({singer.voice_group ?? '–'})</span>
    </div>
  )
}

function Cell({ row, col, staggered }: { row: number; col: number; staggered: boolean }) {
  const { setNodeRef } = useDroppable({ id: `cell-${row}-${col}` })
  const point = pixelPos(row, col, staggered)
  return (
    <div
      ref={setNodeRef}
      style={{
        position: 'absolute',
        left: point.x,
        top: point.y,
        width: 125,
        height: 75,
        border: '1px solid rgba(0,0,0,0.12)',
        borderRadius: 6,
        background: '#faf8f2',
      }}
    />
  )
}

export default function FormationEditor({
  singers,
  placements,
  selected,
  rows,
  cols,
  staggered,
  colors,
  highlight,
  poolFilter,
  onMapChange,
  onSelect,
  onSelectMany,
}: {
  singers: StoredSinger[]
  placements: PlacementMap
  selected: string[]
  rows: number
  cols: number
  staggered: boolean
  colors: EditorColors
  highlight: string[]
  poolFilter: string
  onMapChange: (next: PlacementMap) => void
  onSelect: (id: string, toggle: boolean) => void
  onSelectMany: (ids: string[]) => void
}) {
  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 6 } }),
  )
  const [band, setBand] = useState<RawBand | null>(null)
  const bandStart = useRef<{ x: number; y: number } | null>(null)
  const dragActive = useRef(false)
  const gridRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (highlight.length === 0) return
    const first = gridRef.current?.querySelector('[data-highlight="true"]')
    ;(first as HTMLElement | null)?.scrollIntoView?.({ block: 'nearest' })
  }, [highlight])

  function handleSelect(id: string, toggle: boolean) {
    if (dragActive.current) {
      dragActive.current = false
      return
    }
    onSelect(id, toggle)
  }

  function handleDragEnd(event: DragEndEvent) {
    const singerId = event.active.data.current?.singerId as string | undefined
    const target = event.over ? parseCell(String(event.over.id)) : null
    if (!singerId || !target) return
    const group =
      selected.includes(singerId) && selected.length > 1
        ? [singerId, ...selected.filter((id) => id !== singerId)]
        : [singerId]
    const next =
      group.length === 1
        ? applyMove(placements, singerId, target, rows, cols)
        : applyGroupMove(placements, group, target, rows, cols)
    if (next) onMapChange(next)
  }

  function gridPoint(event: React.MouseEvent): { x: number; y: number } {
    const rect = gridRef.current?.getBoundingClientRect() ?? { left: 0, top: 0 }
    return { x: event.clientX - rect.left, y: event.clientY - rect.top }
  }

  function handleMouseDown(event: React.MouseEvent) {
    if ((event.target as HTMLElement).closest('[data-tile]')) return
    const point = gridPoint(event)
    bandStart.current = point
    setBand({ x0: point.x, y0: point.y, x1: point.x, y1: point.y })
  }

  function handleMouseMove(event: React.MouseEvent) {
    if (!bandStart.current) return
    const point = gridPoint(event)
    setBand({
      x0: bandStart.current.x,
      y0: bandStart.current.y,
      x1: point.x,
      y1: point.y,
    })
  }

  function handleMouseUp() {
    if (!bandStart.current || !band || !gridRef.current) {
      bandStart.current = null
      return
    }
    const rect = normalizeRect(band)
    const grid = gridRef.current.getBoundingClientRect()
    const tiles: { id: string; x: number; y: number; w: number; h: number }[] = []
    gridRef.current.querySelectorAll('[data-tile]').forEach((node) => {
      const box = (node as HTMLElement).getBoundingClientRect()
      const id = (node as HTMLElement).dataset.tile
      if (id) {
        tiles.push({
          id,
          x: box.left - grid.left,
          y: box.top - grid.top,
          w: box.width,
          h: box.height,
        })
      }
    })
    onSelectMany(tilesInRect(tiles, rect))
    bandStart.current = null
    setBand(null)
  }

  const placedIds = new Set(
    Object.entries(placements)
      .filter((entry): entry is [string, Pos] => entry[1] !== null)
      .map(([id]) => id),
  )
  const pool = singers.filter((singer) => !placedIds.has(singer.singer_id))
  const needle = poolFilter.trim().toLowerCase()
  const visiblePool =
    needle.length === 0
      ? pool
      : pool.filter((singer) => singer.name.toLowerCase().includes(needle))
  const width = MARGIN_LEFT + cols * CELL_WIDTH + 50
  const height = MARGIN_TOP + rows * CELL_HEIGHT + 20

  const cells = []
  for (let row = 0; row < rows; row++) {
    for (let col = 0; col < cols; col++) {
      cells.push(<Cell key={`cell-${row}-${col}`} row={row} col={col} staggered={staggered} />)
    }
  }

  return (
    <DndContext
      sensors={sensors}
      collisionDetection={rectIntersection}
      onDragStart={() => {
        dragActive.current = true
      }}
      onDragEnd={handleDragEnd}
    >
      <div style={{ display: 'flex', gap: 16 }}>
        <div style={{ width: 220 }}>
          <h2 className="font-semibold">
            Pool ({visiblePool.length}
            {visiblePool.length !== pool.length ? ` von ${pool.length}` : ''})
          </h2>
          {visiblePool.map((singer) => (
            <PoolItem
              key={singer.singer_id}
              singer={singer}
              color={colors[singer.voice_group ?? ''] ?? '#ccc'}
            />
          ))}
        </div>
        <div
          ref={gridRef}
          onMouseDown={handleMouseDown}
          onMouseMove={handleMouseMove}
          onMouseUp={handleMouseUp}
          style={{ position: 'relative', width, height, userSelect: 'none' }}
        >
          {cells}
          {Object.entries(placements).map(([id, pos]) => {
            if (!pos) return null
            const singer = singers.find((s) => s.singer_id === id)
            if (!singer) return null
            return (
              <Tile
                key={id}
                singer={singer}
                pos={pos}
                staggered={staggered}
                selected={selected.includes(id)}
                highlighted={highlight.includes(id)}
                color={colors[singer.voice_group ?? ''] ?? '#ccc'}
                onSelect={handleSelect}
              />
            )
          })}
          {band && (
            <div
              style={{
                position: 'absolute',
                left: Math.min(band.x0, band.x1),
                top: Math.min(band.y0, band.y1),
                width: Math.abs(band.x1 - band.x0),
                height: Math.abs(band.y1 - band.y0),
                border: '1px solid #0066cc',
                background: 'rgba(0,102,204,0.1)',
              }}
            />
          )}
        </div>
      </div>
    </DndContext>
  )
}
