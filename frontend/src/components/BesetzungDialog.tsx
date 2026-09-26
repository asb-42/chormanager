import { useState } from 'react'
import type { BesetzungInput, Project, Singer } from '../api/client'
import { dialogClassName } from './ui'

interface BesetzungDialogProps {
  projects: Project[]
  singers: Singer[]
  onSubmit: (input: BesetzungInput) => void
  onClose: () => void
}

const inputClass =
  'w-full rounded border border-gray-300 px-2 py-1 dark:border-gray-600 dark:bg-gray-800'

export default function BesetzungDialog({
  projects,
  singers,
  onSubmit,
  onClose,
}: BesetzungDialogProps) {
  const [name, setName] = useState('')
  const [projectId, setProjectId] = useState('')
  const [checked, setChecked] = useState<Set<string>>(new Set())

  const valid = name.trim().length > 0

  function toggle(id: string) {
    setChecked((previous) => {
      const next = new Set(previous)
      if (next.has(id)) {
        next.delete(id)
      } else {
        next.add(id)
      }
      return next
    })
  }

  function handleSubmit(event: React.FormEvent) {
    event.preventDefault()
    if (!valid) return
    const input: BesetzungInput = {
      name: name.trim(),
      singer_ids: [...checked],
    }
    if (projectId) input.project_id = projectId
    onSubmit(input)
  }

  return (
    <div role="dialog" aria-label="Besetzung anlegen" className={dialogClassName}>
      <h2 className="text-lg font-semibold">Besetzung anlegen</h2>
      <form onSubmit={handleSubmit} className="mt-2 space-y-2">
        <label className="block text-sm font-medium">
          Name
          <input
            value={name}
            onChange={(event) => setName(event.target.value)}
            className={inputClass}
          />
        </label>
        <label className="block text-sm font-medium">
          Projekt
          <select
            value={projectId}
            onChange={(event) => setProjectId(event.target.value)}
            className={inputClass}
          >
            <option value="">–</option>
            {projects.map((project) => (
              <option key={project.id} value={project.id}>
                {project.name}
              </option>
            ))}
          </select>
        </label>
        <fieldset>
          <legend className="text-sm font-medium">Sänger</legend>
          <div className="max-h-48 space-y-1 overflow-y-auto">
            {singers.map((singer) => (
              <label key={singer.id} className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={checked.has(singer.id)}
                  onChange={() => toggle(singer.id)}
                />
                {singer.full_name} ({singer.voice_group ?? '–'})
              </label>
            ))}
          </div>
        </fieldset>
        <div className="flex gap-2 pt-1">
          <button
            type="submit"
            disabled={!valid}
            className="rounded bg-blue-600 px-3 py-1 text-white disabled:opacity-40"
          >
            Speichern
          </button>
          <button
            type="button"
            onClick={onClose}
            className="rounded border px-3 py-1"
          >
            Abbrechen
          </button>
        </div>
      </form>
    </div>
  )
}
