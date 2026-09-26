// M3 proper: formation editor surface (dnd-kit, DOM tiles).
// M3.1: single move/swap + click select. M3.2 adds rubber band,
// group drag, search highlight (spike-proven patterns).
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
import type { StoredSinger } from '../api/client'
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
  color,
  onSelect,
}: {
  singer: StoredSinger
  pos: Pos
  staggered: boolean
  selected: boolean
  color: string
  onSelect: (id: string, toggle: boolean) => void
}) {
  const { attributes, listeners, setNodeRef, transform } = useDraggable({
    id: `tile-${singer.singer_id}`,
    data: { singerId: singer.singer_id },
  })
  const point = pixelPos(pos.row, pos.col, staggered)
  return (
    <div
      ref={setNodeRef}
      data-tile={singer.singer_id}
      onClick={(event) => onSelect(singer.singer_id, event.ctrlKey || event.metaKey)}
      style={{
        position: 'absolute',
        left: point.x,
        top: point.y,
        width: 120,
        height: 60,
        transform: CSS.Translate.toString(transform),
        background: color,
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
      {singer.voice_group ?? ''}
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
      {singer.name} ({singer.voice_group ?? '–'})
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
        border: '1px solid #d4c9b8',
        background: '#f8f4eb',
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
  onMove,
  onSelect,
}: {
  singers: StoredSinger[]
  placements: PlacementMap
  selected: string[]
  rows: number
  cols: number
  staggered: boolean
  colors: EditorColors
  onMove: (singerId: string, target: Pos) => void
  onSelect: (id: string, toggle: boolean) => void
}) {
  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 6 } }),
  )

  function handleDragEnd(event: DragEndEvent) {
    const singerId = event.active.data.current?.singerId as string | undefined
    const target = event.over ? parseCell(String(event.over.id)) : null
    if (singerId && target) onMove(singerId, target)
  }

  const placedIds = new Set(
    Object.entries(placements)
      .filter((entry): entry is [string, Pos] => entry[1] !== null)
      .map(([id]) => id),
  )
  const pool = singers.filter((singer) => !placedIds.has(singer.singer_id))
  const width = MARGIN_LEFT + cols * CELL_WIDTH + 50
  const height = MARGIN_TOP + rows * CELL_HEIGHT + 20

  const cells = []
  for (let row = 0; row < rows; row++) {
    for (let col = 0; col < cols; col++) {
      cells.push(<Cell key={`cell-${row}-${col}`} row={row} col={col} staggered={staggered} />)
    }
  }

  return (
    <DndContext sensors={sensors} collisionDetection={rectIntersection} onDragEnd={handleDragEnd}>
      <div style={{ display: 'flex', gap: 16 }}>
        <div style={{ width: 220 }}>
          <h2 className="font-semibold">Pool ({pool.length})</h2>
          {pool.map((singer) => (
            <PoolItem
              key={singer.singer_id}
              singer={singer}
              color={colors[singer.voice_group ?? ''] ?? '#ccc'}
            />
          ))}
        </div>
        <div style={{ position: 'relative', width, height, userSelect: 'none' }}>
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
                color={colors[singer.voice_group ?? ''] ?? '#ccc'}
                onSelect={onSelect}
              />
            )
          })}
        </div>
      </div>
    </DndContext>
  )
}
