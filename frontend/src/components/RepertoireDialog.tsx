import { useState } from 'react'
import type { Project, RepertoireInput } from '../api/client'
import { dialogClassName } from './ui'

interface RepertoireDialogProps {
  projects: Project[]
  onSubmit: (input: RepertoireInput) => void
  onClose: () => void
}

const inputClass =
  'w-full rounded border border-gray-300 px-2 py-1 dark:border-gray-600 dark:bg-gray-800'

export default function RepertoireDialog({
  projects,
  onSubmit,
  onClose,
}: RepertoireDialogProps) {
  const [title, setTitle] = useState('')
  const [composer, setComposer] = useState('')
  const [projectId, setProjectId] = useState('')

  const valid = title.trim().length > 0

  function handleSubmit(event: React.FormEvent) {
    event.preventDefault()
    if (!valid) return
    const input: RepertoireInput = { title: title.trim() }
    if (composer.trim()) input.composer = composer.trim()
    if (projectId) input.project_id = projectId
    onSubmit(input)
  }

  return (
    <div role="dialog" aria-label="Stück anlegen" className={dialogClassName}>
      <h2 className="text-lg font-semibold">Stück anlegen</h2>
      <form onSubmit={handleSubmit} className="mt-2 space-y-2">
        <label className="block text-sm font-medium">
          Titel
          <input
            value={title}
            onChange={(event) => setTitle(event.target.value)}
            className={inputClass}
          />
        </label>
        <label className="block text-sm font-medium">
          Komponist
          <input
            value={composer}
            onChange={(event) => setComposer(event.target.value)}
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
