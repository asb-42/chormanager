import { useEffect, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link, useParams } from 'react-router-dom'
import {
  fetchFormation,
  fetchRules,
  fetchVoiceGroups,
  optimizeFormation,
  putPlacements,
} from '../api/client'
import type { FormationDoc, OptimizeResult } from '../api/client'
import FormationEditor from '../formation/FormationEditor'
import type { PlacementMap } from '../formation/placements'
import { toPutPayload } from '../formation/placements'
import OptimizerDialog from '../components/OptimizerDialog'

function docToMap(doc: FormationDoc): {
  map: PlacementMap
  singers: FormationDoc['singers']
} {
  const map: PlacementMap = {}
  const singers = [...doc.singers]
  for (const singer of doc.singers) {
    map[singer.singer_id] = null
  }
  for (const placed of doc.placed) {
    map[placed.singer.singer_id] = { row: placed.row, col: placed.col }
    if (!singers.some((s) => s.singer_id === placed.singer.singer_id)) {
      singers.push(placed.singer)
    }
  }
  return { map, singers }
}

export default function FormationEditorPage() {
  const { id } = useParams<{ id: string }>()
  const queryClient = useQueryClient()
  const [map, setMap] = useState<PlacementMap | null>(null)
  const [selected, setSelected] = useState<string[]>([])
  const [staggered, setStaggered] = useState(false)
  const [saveError, setSaveError] = useState(false)
  const [search, setSearch] = useState('')
  const [savedAt, setSavedAt] = useState<Date | null>(null)
  const [optimizerOpen, setOptimizerOpen] = useState(false)
  const [preview, setPreview] = useState<OptimizeResult | null>(null)
  const [rowsInput, setRowsInput] = useState('')
  const [colsInput, setColsInput] = useState('')
  const [resizeConfirm, setResizeConfirm] = useState<number | null>(null)

  const { data: doc, isLoading, isError } = useQuery({
    queryKey: ['formation', id],
    queryFn: () => fetchFormation(id as string),
    enabled: !!id,
  })
  const { data: voiceGroups = [] } = useQuery({
    queryKey: ['voice-groups'],
    queryFn: fetchVoiceGroups,
  })
  const { data: rules = [] } = useQuery({
    queryKey: ['formation-rules'],
    queryFn: fetchRules,
  })

  useEffect(() => {
    if (doc) {
      const converted = docToMap(doc)
      setMap(converted.map)
      setStaggered(doc.staggered)
      setSelected([])
      setSaveError(false)
      setRowsInput(String(doc.rows))
      setColsInput(String(doc.cols))
      setResizeConfirm(null)
    }
  }, [doc])

  const mutation = useMutation({
    mutationFn: (payload: {
      placements: { singer_id: string; row: number; col: number }[]
      staggered: boolean
      rows?: number
      cols?: number
    }) =>
      putPlacements(id as string, {
        staggered: payload.staggered,
        rows: payload.rows,
        cols: payload.cols,
        placements: payload.placements,
      }),
    onSuccess: () => {
      setSavedAt(new Date())
    },
    onError: () => {
      // Rollback auf den letzten Serverstand.
      if (doc) setMap(docToMap(doc).map)
      setSaveError(true)
    },
    onSettled: () => {
      void queryClient.invalidateQueries({ queryKey: ['formation', id] })
    },
  })

  const optimizeMutation = useMutation({
    mutationFn: (ruleIds: string[]) =>
      optimizeFormation(id as string, ruleIds),
    onSuccess: (result) => setPreview(result),
  })

  if (isLoading || !doc || map === null) {
    return (
      <section>
        <p className="mt-4">Lädt …</p>
      </section>
    )
  }
  if (isError) {
    return (
      <section>
        <p className="mt-4 text-red-600">Fehler beim Laden.</p>
      </section>
    )
  }

  // Const aliases: TS narrowing survives into closures below.
  const loadedDoc: FormationDoc = doc
  const loadedMap: PlacementMap = map

  const colors: Record<string, string> = {}
  for (const group of voiceGroups) {
    colors[group.id] = group.color_light
  }
  const singers = docToMap(loadedDoc).singers
  const needle = search.trim().toLowerCase()
  const highlight =
    needle.length === 0
      ? []
      : singers
          .filter((singer) => singer.name.toLowerCase().includes(needle))
          .map((singer) => singer.singer_id)

  function persist(
    next: PlacementMap,
    stagger: boolean,
    rows?: number,
    cols?: number,
  ) {
    setMap(next)
    setSaveError(false)
    mutation.mutate({ placements: toPutPayload(next), staggered: stagger, rows, cols })
  }

  function handleMapChange(next: PlacementMap) {
    persist(next, staggered)
  }

  function handleResize() {
    if (!loadedMap) return
    const rows = parseInt(rowsInput, 10)
    const cols = parseInt(colsInput, 10)
    if (!Number.isInteger(rows) || rows < 1 || !Number.isInteger(cols) || cols < 1) {
      return
    }
    const excess = Object.values(loadedMap).filter(
      (pos) => pos !== null && (pos.row >= rows || pos.col >= cols),
    ).length
    if (excess > 0) {
      setResizeConfirm(excess)
      return
    }
    persist(loadedMap, staggered, rows, cols)
  }

  function confirmResize() {
    if (!loadedMap) return
    const rows = parseInt(rowsInput, 10)
    const cols = parseInt(colsInput, 10)
    const pruned: PlacementMap = {}
    for (const [singerId, pos] of Object.entries(loadedMap)) {
      pruned[singerId] =
        pos !== null && pos.row < rows && pos.col < cols ? pos : null
    }
    setResizeConfirm(null)
    persist(pruned, staggered, rows, cols)
  }

  function applyPreview() {
    if (!preview) return
    const next: PlacementMap = {}
    for (const placement of preview.placements) {
      next[placement.singer_id] =
        placement.row >= 0 && placement.col >= 0
          ? { row: placement.row, col: placement.col }
          : null
    }
    setPreview(null)
    setOptimizerOpen(false)
    persist(next, staggered)
  }

  function handleSelect(singerId: string, toggle: boolean) {
    setSelected((previous) => {
      if (toggle) {
        return previous.includes(singerId)
          ? previous.filter((s) => s !== singerId)
          : [...previous, singerId]
      }
      return [singerId]
    })
  }

  function handleStagger(checked: boolean) {
    setStaggered(checked)
    mutation.mutate({ placements: toPutPayload(loadedMap), staggered: checked })
  }

  const placedCount = Object.values(loadedMap).filter((pos) => pos !== null).length

  return (
    <section>
      <Link to="/formations" className="text-sm text-blue-600 underline">
        ← Alle Aufstellungen
      </Link>
      <h1 className="mt-1 text-xl font-semibold">{loadedDoc.name ?? loadedDoc.id}</h1>
      <div className="mt-2 flex flex-wrap items-center gap-4 text-sm">
        <label>
          <input
            type="checkbox"
            checked={staggered}
            onChange={(event) => handleStagger(event.target.checked)}
          />{' '}
          Versetzt
        </label>
        <input
          type="search"
          placeholder="Suchen …"
          value={search}
          onChange={(event) => setSearch(event.target.value)}
          className="w-48 rounded border border-gray-300 px-2 py-1 dark:border-gray-600 dark:bg-gray-800"
        />
        <label className="text-sm font-medium">
          Reihen
          <input
            value={rowsInput}
            inputMode="numeric"
            onChange={(event) => setRowsInput(event.target.value)}
            className="ml-2 w-16 rounded border border-gray-300 px-2 py-1 dark:border-gray-600 dark:bg-gray-800"
          />
        </label>
        <label className="text-sm font-medium">
          Spalten
          <input
            value={colsInput}
            inputMode="numeric"
            onChange={(event) => setColsInput(event.target.value)}
            className="ml-2 w-16 rounded border border-gray-300 px-2 py-1 dark:border-gray-600 dark:bg-gray-800"
          />
        </label>
        <button
          type="button"
          onClick={handleResize}
          className="rounded border px-3 py-1"
        >
          Anwenden
        </button>
        <button
          type="button"
          onClick={() => {
            setPreview(null)
            setOptimizerOpen(true)
          }}
          className="rounded border px-3 py-1"
        >
          Optimieren
        </button>
        <span>
          {placedCount} platziert, {singers.length - placedCount} im Pool
        </span>
        {mutation.isPending && <span>Speichert …</span>}
        {savedAt && !mutation.isPending && (
          <span>Gespeichert um {savedAt.toLocaleTimeString()}.</span>
        )}
        {mutation.isPending && <span>Speichert …</span>}
        {savedAt && !mutation.isPending && (
          <span>Gespeichert um {savedAt.toLocaleTimeString()}.</span>
        )}
        {saveError && (
          <span className="text-red-600">Speichern fehlgeschlagen.</span>
        )}
      </div>
      {resizeConfirm !== null && (
        <div className="mt-2">
          <p>
            {resizeConfirm} {resizeConfirm === 1 ? 'Sänger fällt' : 'Sänger fallen'}{' '}
            raus und zurück in den Pool.
          </p>
          <button
            type="button"
            onClick={confirmResize}
            className="mt-1 rounded bg-blue-600 px-3 py-1 text-white"
          >
            Trotzdem anwenden
          </button>
        </div>
      )}
      <div className="mt-2">
        <FormationEditor
          singers={singers}
          placements={loadedMap}
          selected={selected}
          rows={loadedDoc.rows}
          cols={loadedDoc.cols}
          staggered={staggered}
          colors={colors}
          highlight={highlight}
          onMapChange={handleMapChange}
          onSelect={handleSelect}
          onSelectMany={setSelected}
        />
      </div>
      {optimizerOpen && (
        <OptimizerDialog
          rules={rules}
          preview={preview}
          previewPending={optimizeMutation.isPending}
          singers={singers}
          placements={loadedMap}
          onPreview={(ruleIds) => optimizeMutation.mutate(ruleIds)}
          onApply={applyPreview}
          onClose={() => {
            setOptimizerOpen(false)
            setPreview(null)
          }}
        />
      )}
    </section>
  )
}
