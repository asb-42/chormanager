import { useState } from 'react'
import type { BesetzungInput, Project, Singer } from '../api/client'
import { Modal } from './Modal'
import { Button, Field, inputClassName } from './ui'

interface BesetzungDialogProps {
  projects: Project[]
  singers: Singer[]
  onSubmit: (input: BesetzungInput) => void
  onClose: () => void
}

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
    <Modal label="Besetzung anlegen" onClose={onClose}>
      <h2 className="text-lg font-semibold">Besetzung anlegen</h2>
      <h2 className="text-lg font-semibold">Besetzung anlegen</h2>
      <form onSubmit={handleSubmit} className="mt-3 space-y-3">
        <Field label="Name">
          <input
            value={name}
            onChange={(event) => setName(event.target.value)}
            className={inputClassName}
          />
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
          <Button type="submit" variant="primary" disabled={!valid}>
            Speichern
          </Button>
          <Button onClick={onClose}>
            Abbrechen
          </Button>
        </div>
      </form>
    </Modal>
  )
}
