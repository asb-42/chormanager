import { useState } from 'react'
import type {
  FormationRule,
  OptimizeResult,
  StoredSinger,
} from '../api/client'
import type { PlacementMap } from '../formation/placements'
import { dialogClassName } from './ui'

interface OptimizerDialogProps {
  rules: FormationRule[]
  preview: OptimizeResult | null
  previewPending: boolean
  singers: StoredSinger[]
  placements: PlacementMap
  onPreview: (ruleIds: string[]) => void
  onApply: () => void
  onClose: () => void
}

export default function OptimizerDialog({
  rules,
  preview,
  previewPending,
  singers,
  placements,
  onPreview,
  onApply,
  onClose,
}: OptimizerDialogProps) {
  const [checked, setChecked] = useState<string[]>([])

  function toggle(id: string) {
    setChecked((previous) =>
      previous.includes(id)
        ? previous.filter((rule) => rule !== id)
        : [...previous, id],
    )
  }

  const names = Object.fromEntries(
    singers.map((singer) => [singer.singer_id, singer.name]),
  )
  const moves =
    preview?.placements.filter((placement) => {
      const current = placements[placement.singer_id]
      return (
        !current ||
        current.row !== placement.row ||
        current.col !== placement.col
      )
    }) ?? []

  const primary = rules.filter((rule) => rule.primary)
  const refinement = rules.filter((rule) => !rule.primary)

  return (
    <div role="dialog" aria-label="Aufstellung optimieren" className={dialogClassName}>
      <h2 className="text-lg font-semibold">Aufstellung optimieren</h2>
      <fieldset className="mt-2">
        <legend className="text-sm font-medium">Anordnung</legend>
        {primary.map((rule) => (
          <label key={rule.id} className="mr-4 text-sm">
            <input
              type="checkbox"
              checked={checked.includes(rule.id)}
              onChange={() => toggle(rule.id)}
            />{' '}
            {rule.name}
          </label>
        ))}
      </fieldset>
      <fieldset className="mt-2">
        <legend className="text-sm font-medium">Verfeinerung</legend>
        {refinement.map((rule) => (
          <label key={rule.id} className="mr-4 text-sm">
            <input
              type="checkbox"
              checked={checked.includes(rule.id)}
              onChange={() => toggle(rule.id)}
            />{' '}
            {rule.name}
          </label>
        ))}
      </fieldset>
      <div className="mt-2 flex gap-2">
        <button
          type="button"
          onClick={() => onPreview(checked)}
          disabled={checked.length === 0 || previewPending}
          className="rounded bg-blue-600 px-3 py-1 text-white disabled:opacity-40"
        >
          Vorschau
        </button>
        <button
          type="button"
          onClick={onClose}
          className="rounded border px-3 py-1"
        >
          Abbrechen
        </button>
      </div>
      {preview && (
        <div className="mt-3">
          <p>
            {preview.swap_count} Vertauschungen (Kosten {preview.cost})
          </p>
          <ul className="mt-1 list-disc pl-5 text-sm">
            {moves.map((move) => {
              const current = placements[move.singer_id]
              return (
                <li key={move.singer_id}>
                  {names[move.singer_id] ?? move.singer_id}: (
                  {current?.row ?? '–'},{current?.col ?? '–'}) → (
                  {move.row},{move.col})
                </li>
              )
            })}
          </ul>
          <button
            type="button"
            onClick={onApply}
            className="mt-2 rounded bg-green-700 px-3 py-1 text-white"
          >
            Übernehmen
          </button>
        </div>
      )}
    </div>
  )
}
