import { useState } from 'react'
import type { EventInput, Project } from '../api/client'

interface EventDialogProps {
  projects: Project[]
  submitLabel?: string
  onSubmit: (input: EventInput) => void
  onClose?: () => void
}

const inputClass =
  'w-full rounded border border-gray-300 px-2 py-1 dark:border-gray-600 dark:bg-gray-800'

const EVENT_TYPES = ['GP', 'OP', 'SOFA', 'Probe', 'Konzert', 'Auftritt']

export default function EventDialog({
  projects,
  submitLabel = 'Speichern',
  onSubmit,
  onClose,
}: EventDialogProps) {
  const [name, setName] = useState('')
  const [date, setDate] = useState('')
  const [eventType, setEventType] = useState('Probe')
  const [projectId, setProjectId] = useState('')

  const valid = name.trim().length > 0 && date.trim().length > 0

  function handleSubmit(event: React.FormEvent) {
    event.preventDefault()
    if (!valid) return
    const input: EventInput = {
      name: name.trim(),
      date: date.trim(),
      event_type: eventType,
    }
    if (projectId) input.project_id = projectId
    onSubmit(input)
  }

  return (
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
        Datum
        <input
          type="date"
          value={date}
          onChange={(event) => setDate(event.target.value)}
          className={inputClass}
        />
      </label>
      <label className="block text-sm font-medium">
        Typ
        <select
          value={eventType}
          onChange={(event) => setEventType(event.target.value)}
          className={inputClass}
        >
          {EVENT_TYPES.map((type) => (
            <option key={type} value={type}>
              {type}
            </option>
          ))}
        </select>
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
          {submitLabel}
        </button>
        {onClose && (
          <button
            type="button"
            onClick={onClose}
            className="rounded border px-3 py-1"
          >
            Abbrechen
          </button>
        )}
      </div>
    </form>
  )
}
