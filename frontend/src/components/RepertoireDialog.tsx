import { useState } from 'react'
import type { Project, RepertoireInput } from '../api/client'
import { Modal } from './Modal'
import { Button, Field, inputClassName } from './ui'

interface RepertoireDialogProps {
  projects: Project[]
  onSubmit: (input: RepertoireInput) => void
  onClose: () => void
}

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
    <Modal label="Stück anlegen" onClose={onClose}>
      <h2 className="text-lg font-semibold">Stück anlegen</h2>
      <h2 className="text-lg font-semibold">Stück anlegen</h2>
      <form onSubmit={handleSubmit} className="mt-3 space-y-3">
        <Field label="Titel">
          <input
            value={title}
            onChange={(event) => setTitle(event.target.value)}
            className={inputClassName}
          />
        </Field>
        <Field label="Komponist">
          <input
            value={composer}
            onChange={(event) => setComposer(event.target.value)}
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
