import { useState } from 'react'
import type { ProjectInput } from '../api/client'
import { Button, Field, inputClassName } from './ui'
import { Modal } from './Modal'

interface ProjectDialogProps {
  title: string
  submitLabel: string
  initial: { name?: string; description?: string; spielzeit?: string }
  onSubmit: (input: ProjectInput) => void
  onClose: () => void
}

export default function ProjectDialog({
  title,
  submitLabel,
  initial,
  onSubmit,
  onClose,
}: ProjectDialogProps) {
  const [name, setName] = useState(initial.name ?? '')
  const [description, setDescription] = useState(initial.description ?? '')
  const [spielzeit, setSpielzeit] = useState(initial.spielzeit ?? '')

  const valid = name.trim().length > 0

  function handleSubmit(event: React.FormEvent) {
    event.preventDefault()
    if (!valid) return
    const input: ProjectInput = { name: name.trim() }
    if (description.trim()) input.description = description.trim()
    if (spielzeit.trim()) input.spielzeit = spielzeit.trim()
    onSubmit(input)
  }

  return (
    <Modal label={title} onClose={onClose}>
      <h2 className="text-lg font-semibold">{title}</h2>
      <form onSubmit={handleSubmit} className="mt-3 space-y-3">
        <Field label="Name">
          <input
            value={name}
            onChange={(event) => setName(event.target.value)}
            className={inputClassName}
          />
        </Field>
        <Field label="Beschreibung">
          <textarea
            value={description}
            onChange={(event) => setDescription(event.target.value)}
            rows={3}
            className={inputClassName}
          />
        </Field>
        <Field label="Spielzeit">
          <input
            value={spielzeit}
            onChange={(event) => setSpielzeit(event.target.value)}
            className={inputClassName}
          />
        </Field>
        <div className="flex gap-2 pt-1">
          <Button type="submit" variant="primary" disabled={!valid}>
            {submitLabel}
          </Button>
          <Button onClick={onClose}>Abbrechen</Button>
        </div>
      </form>
    </Modal>
  )
}
