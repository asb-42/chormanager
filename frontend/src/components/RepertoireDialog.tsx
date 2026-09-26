import { useState } from 'react'
import type { Project, RepertoireInput } from '../api/client'
import { Button, Field, inputClassName } from './ui'
import { Modal } from './Modal'

interface RepertoireDialogProps {
  title?: string
  submitLabel?: string
  initial?: Partial<RepertoireInput>
  projects: Project[]
  onSubmit: (input: RepertoireInput) => void
  onClose: () => void
}

export default function RepertoireDialog({
  title = 'Stück anlegen',
  submitLabel = 'Speichern',
  initial = {},
  projects,
  onSubmit,
  onClose,
}: RepertoireDialogProps) {
  const [titleValue, setTitleValue] = useState(initial.title ?? '')
  const [composer, setComposer] = useState(initial.composer ?? '')
  const [dates, setDates] = useState(initial.dates ?? '')
  const [country, setCountry] = useState(initial.country ?? '')
  const [publisher, setPublisher] = useState(initial.publisher ?? '')
  const [arrangement, setArrangement] = useState(initial.arrangement ?? '')
  const [location, setLocation] = useState(initial.location ?? '')
  const [projectId, setProjectId] = useState(initial.project_id ?? '')

  const valid = titleValue.trim().length > 0

  function handleSubmit(event: React.FormEvent) {
    event.preventDefault()
    if (!valid) return
    const out: Record<string, string> = { title: titleValue.trim() }
    const text = (value: string) => value.trim() || undefined
    const assign = (key: string, value: string | undefined) => {
      if (value) out[key] = value
    }
    assign('composer', text(composer))
    assign('dates', text(dates))
    assign('country', text(country))
    assign('publisher', text(publisher))
    assign('arrangement', text(arrangement))
    assign('location', text(location))
    if (projectId) out['project_id'] = projectId
    onSubmit(out as unknown as RepertoireInput)
  }

  return (
    <Modal label={title} onClose={onClose} wide>
      <h2 className="text-lg font-semibold">{title}</h2>
      <form onSubmit={handleSubmit} className="mt-3 space-y-3">
        <div className="grid gap-2 sm:grid-cols-2">
          <Field label="Titel">
            <input
              value={titleValue}
              onChange={(event) => setTitleValue(event.target.value)}
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
          <Field label="Lebensdaten">
            <input
              value={dates}
              onChange={(event) => setDates(event.target.value)}
              className={inputClassName}
            />
          </Field>
          <Field label="Land">
            <input
              value={country}
              onChange={(event) => setCountry(event.target.value)}
              className={inputClassName}
            />
          </Field>
          <Field label="Verlag">
            <input
              value={publisher}
              onChange={(event) => setPublisher(event.target.value)}
              className={inputClassName}
            />
          </Field>
          <Field label="Besetzung">
            <input
              value={arrangement}
              onChange={(event) => setArrangement(event.target.value)}
              className={inputClassName}
            />
          </Field>
          <Field label="Standort">
            <input
              value={location}
              onChange={(event) => setLocation(event.target.value)}
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
        </div>
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
