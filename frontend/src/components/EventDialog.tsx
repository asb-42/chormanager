import { useState } from 'react'
import type { EventInput, Project } from '../api/client'
import { Button, Field, inputClassName } from './ui'

interface EventDialogProps {
  title?: string
  submitLabel?: string
  initial?: Partial<EventInput>
  projects: Project[]
  onSubmit: (input: EventInput) => void
  onClose?: () => void
}

const EVENT_TYPES = ['GP', 'OP', 'SOFA', 'Probe', 'Konzert', 'Auftritt']

export default function EventDialog({
  initial = {},
  projects,
  submitLabel = 'Speichern',
  onSubmit,
  onClose,
}: EventDialogProps) {
  const [name, setName] = useState(initial.name ?? '')
  const [date, setDate] = useState((initial.date ?? '').slice(0, 10))
  const [eventType, setEventType] = useState(initial.event_type ?? 'Probe')
  const [projectId, setProjectId] = useState(initial.project_id ?? '')

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
    <form onSubmit={handleSubmit} className="mt-3 space-y-3">
      <Field label="Name">
        <input
          value={name}
          onChange={(event) => setName(event.target.value)}
          className={inputClassName}
        />
      </Field>
      <Field label="Datum">
        <input
          type="date"
          value={date}
          onChange={(event) => setDate(event.target.value)}
          className={inputClassName}
        />
      </Field>
      <Field label="Typ">
        <select
          value={eventType}
          onChange={(event) => setEventType(event.target.value)}
          className={inputClassName}
        >
          {EVENT_TYPES.map((type) => (
            <option key={type} value={type}>
              {type}
            </option>
          ))}
        </select>
      </Field>
      <Field label="Projekt">
        <select
          value={projectId}
          onChange={(event) => setProjectId(event.target.value)}
          className={inputClassName}
        >
          <option value="">–</option>
          {projects.map((project) => (
            <option key={project.id} value={project.id}>
              {project.name}
            </option>
          ))}
        </select>
      </Field>
      <div className="flex gap-2 pt-1">
        <Button type="submit" variant="primary" disabled={!valid}>
          {submitLabel}
        </Button>
        {onClose && (
          <Button onClick={onClose}>
            Abbrechen
          </Button>
        )}
      </div>
    </form>
  )
}
