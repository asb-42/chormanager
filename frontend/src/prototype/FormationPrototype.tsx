// M3-Spike THROWAWAY prototype: 20 tiles + dnd-kit + rubber band.
//
// Proves the risky interactions before the real M3 editor:
// DOM tiles with absolute CSS-transform positioning (no canvas),
// pool→grid + grid→grid + swap, rubber-band multi-select,
// group drag, stagger toggle. No backend, no undo, no optimizer.
// DELETE this directory when the M3 editor lands (route /prototype).
import { useRef, useState } from 'react'
import {
  DndContext,
  PointerSensor,
  rectIntersection,
  useDraggable,
  useDroppable,
  useSensor,
  useSensors,
} from '@dnd-kit/core'
import { CSS } from '@dnd-kit/utilities'
import type { DragEndEvent } from '@dnd-kit/core'
import {
  CELL_HEIGHT,
  CELL_WIDTH,
  MARGIN_LEFT,
  MARGIN_TOP,
  pixelPos,
} from './gridMath'

interface Singer {
  id: string
  name: string
  voiceGroup: string
}

interface Placed {
  row: number
  col: number
}

// Light-theme colors copied from config/voice_groups.json (spike only).
const COLORS: Record<string, string> = {
  'Sopran 1': '#E5C84B',
  'Sopran 2': '#B8A23A',
  'Alt 1': '#C75B5B',
  'Alt 2': '#9B5B6B',
  'Tenor 1': '#6BA888',
  'Tenor 2': '#5B8A6B',
  'Bass 1': '#6B8AA8',
  'Bass 2': '#5B6B8A',
}

const GROUPS = Object.keys(COLORS)

function makeSingers(): Singer[] {
  return Array.from({ length: 20 }, (_, i) => ({
    id: `spike-${i}`,
    name: `Sänger ${i + 1}`,
    voiceGroup: GROUPS[i % GROUPS.length],
  }))
}

const ROWS = 4
const COLS = 5

function cellId(row: number, col: number): string {
  return `cell-${row}-${col}`
}

function parseCell(id: string): { row: number; col: number } | null {
  const match = /^cell-(\d+)-(\d+)$/.exec(id)
  if (!match) return null
  return { row: Number(match[1]), col: Number(match[2]) }
}

function Tile({
  singer,
  row,
  col,
  staggered,
  selected,
  onSelect,
}: {
  singer: Singer
  row: number
  col: number
  staggered: boolean
  selected: boolean
  onSelect: (id: string, toggle: boolean) => void
}) {
  const { attributes, listeners, setNodeRef, transform } = useDraggable({
    id: `tile-${singer.id}`,
    data: { singerId: singer.id },
  })
  const pos = pixelPos(row, col, staggered)
  return (
    <div
      ref={setNodeRef}
      data-tile={singer.id}
      onClick={(event) => onSelect(singer.id, event.ctrlKey || event.metaKey)}
      style={{
        position: 'absolute',
        left: pos.x,
        top: pos.y,
        width: 120,
        height: 60,
        transform: CSS.Translate.toString(transform),
        background: COLORS[singer.voiceGroup] ?? '#ccc',
        border: selected ? '3px solid #0066cc' : '1px solid #888',
        borderRadius: 4,
        padding: 4,
        fontSize: 12,
        cursor: 'grab',
        zIndex: transform ? 10 : 1,
      }}
      {...listeners}
      {...attributes}
    >
      <strong>{singer.name}</strong>
      <br />
      {singer.voiceGroup}
    </div>
  )
}

function PoolItem({ singer }: { singer: Singer }) {
  const { attributes, listeners, setNodeRef, transform } = useDraggable({
    id: `pool-${singer.id}`,
    data: { singerId: singer.id, fromPool: true },
  })
  return (
    <div
      ref={setNodeRef}
      style={{
        transform: CSS.Translate.toString(transform),
        background: COLORS[singer.voiceGroup] ?? '#ccc',
        border: '1px solid #888',
        borderRadius: 4,
        padding: '2px 6px',
        marginBottom: 4,
        fontSize: 12,
        cursor: 'grab',
      }}
      {...listeners}
      {...attributes}
    >
      {singer.name} ({singer.voiceGroup})
    </div>
  )
}

function Cell({ row, col, staggered }: { row: number; col: number; staggered: boolean }) {
  const { setNodeRef } = useDroppable({ id: cellId(row, col) })
  const pos = pixelPos(row, col, staggered)
  return (
    <div
      ref={setNodeRef}
      style={{
        position: 'absolute',
        left: pos.x,
        top: pos.y,
        width: 125,
        height: 75,
        border: '1px solid #d4c9b8',
        background: '#f8f4eb',
      }}
    />
  )
}

interface Band {
  x0: number
  y0: number
  x1: number
  y1: number
}

export default function FormationPrototype() {
  const [singers] = useState<Singer[]>(makeSingers)
  const [placements, setPlacements] = useState<Record<string, Placed | null>>({})
  const [selected, setSelected] = useState<string[]>([])
  const [staggered, setStaggered] = useState(false)
  const [band, setBand] = useState<Band | null>(null)
  const bandStart = useRef<{ x: number; y: number } | null>(null)
  const dragActive = useRef(false)
  const gridRef = useRef<HTMLDivElement>(null)

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 6 } }),
  )

  const occupantAt = (placed: Record<string, Placed | null>, row: number, col: number) =>
    Object.entries(placed).find(
      ([, pos]) => pos !== null && pos.row === row && pos.col === col,
    )?.[0] ?? null

  function handleSelect(id: string, toggle: boolean) {
    // A click right after a drag must not toggle selection.
    if (dragActive.current) {
      dragActive.current = false
      return
    }
    setSelected((previous) => {
      if (toggle) {
        return previous.includes(id)
          ? previous.filter((s) => s !== id)
          : [...previous, id]
      }
      return [id]
    })
  }

  function handleDragEnd(event: DragEndEvent) {
    const singerId = event.active.data.current?.singerId as string | undefined
    const target = event.over ? parseCell(String(event.over.id)) : null
    if (!singerId || !target) return
    setPlacements((previous) => {
      const next = { ...previous }
      const origin = next[singerId] ?? null
      const group =
        selected.includes(singerId) && selected.length > 1
          ? selected
          : [singerId]
      if (group.length === 1) {
        // Single move with swap (superset of desktop dropEvent).
        const occupant = occupantAt(next, target.row, target.col)
        if (occupant && occupant !== singerId) {
          next[occupant] = origin
        }
        next[singerId] = target
        return next
      }
      // Group move: validate all targets first, abort otherwise.
      const delta = origin
        ? {
            row: target.row - origin.row,
            col: target.col - origin.col,
          }
        : null
      if (!delta) return previous
      const destinations = new Map<string, Placed>()
      for (const id of group) {
        const pos = next[id]
        if (!pos) return previous
        const dest = { row: pos.row + delta.row, col: pos.col + delta.col }
        if (dest.row < 0 || dest.row >= ROWS || dest.col < 0 || dest.col >= COLS) {
          return previous
        }
        const occupant = occupantAt(next, dest.row, dest.col)
        if (occupant && !group.includes(occupant)) return previous
        destinations.set(id, dest)
      }
      for (const [id, dest] of destinations) next[id] = dest
      return next
    })
  }

  function gridPoint(event: React.MouseEvent): { x: number; y: number } {
    const rect = gridRef.current?.getBoundingClientRect() ?? { left: 0, top: 0 }
    return { x: event.clientX - rect.left, y: event.clientY - rect.top }
  }

  function handleMouseDown(event: React.MouseEvent) {
    // Rubber band only on empty area (tiles handle their own clicks).
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
    if (!bandStart.current || !band) {
      bandStart.current = null
      return
    }
    const x0 = Math.min(band.x0, band.x1)
    const x1 = Math.max(band.x0, band.x1)
    const y0 = Math.min(band.y0, band.y1)
    const y1 = Math.max(band.y0, band.y1)
    const hits: string[] = []
    gridRef.current
      ?.querySelectorAll('[data-tile]')
      ?.forEach((node) => {
        const rect = (node as HTMLElement).getBoundingClientRect()
        const grid = gridRef.current?.getBoundingClientRect()
        if (!grid) return
        const left = rect.left - grid.left
        const top = rect.top - grid.top
        if (left < x1 && left + rect.width > x0 && top < y1 && top + rect.height > y0) {
          const id = (node as HTMLElement).dataset.tile
          if (id) hits.push(id)
        }
      })
    setSelected(hits)
    bandStart.current = null
    setBand(null)
  }

  const placed = Object.entries(placements).filter(
    (entry): entry is [string, Placed] => entry[1] !== null,
  )
  const pool = singers.filter((singer) => !placements[singer.id])
  const width = MARGIN_LEFT + COLS * CELL_WIDTH + 50
  const height = MARGIN_TOP + ROWS * CELL_HEIGHT + 20

  const cells = []
  for (let row = 0; row < ROWS; row++) {
    for (let col = 0; col < COLS; col++) {
      cells.push(<Cell key={cellId(row, col)} row={row} col={col} staggered={staggered} />)
    }
  }

  return (
    <section>
      <h1 className="text-xl font-semibold">Formation-Prototyp (M3-Spike, throwaway)</h1>
      <label className="mt-2 block text-sm">
        <input
          type="checkbox"
          checked={staggered}
          onChange={(event) => setStaggered(event.target.checked)}
        />{' '}
        Versetzt
      </label>
      <p className="text-sm text-gray-600">
        {placed.length} platziert, {pool.length} im Pool, {selected.length} selektiert.
      </p>
      <div style={{ display: 'flex', gap: 16 }}>
        <div style={{ width: 220 }}>
          <h2 className="font-semibold">Pool</h2>
          <DndContext
            sensors={sensors}
            collisionDetection={rectIntersection}
            onDragStart={() => {
              dragActive.current = true
            }}
            onDragEnd={handleDragEnd}
          >
            {pool.map((singer) => (
              <PoolItem key={singer.id} singer={singer} />
            ))}
            <h2 className="mt-4 font-semibold">Aufstellung</h2>
            <div
              ref={gridRef}
              onMouseDown={handleMouseDown}
              onMouseMove={handleMouseMove}
              onMouseUp={handleMouseUp}
              style={{ position: 'relative', width, height, userSelect: 'none' }}
            >
              {cells}
              {placed.map(([id, pos]) => {
                const singer = singers.find((s) => s.id === id)
                if (!singer) return null
                return (
                  <Tile
                    key={id}
                    singer={singer}
                    row={pos.row}
                    col={pos.col}
                    staggered={staggered}
                    selected={selected.includes(id)}
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
          </DndContext>
        </div>
      </div>
    </section>
  )
}
