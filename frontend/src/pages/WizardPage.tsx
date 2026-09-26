import { useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import {
  createEvent,
  createFormation,
  createSinger,
  fetchEvents,
  fetchProjects,
  fetchVoiceGroups,
} from '../api/client'
import type { EventInput, SingerInput } from '../api/client'
import EventDialog from '../components/EventDialog'
import SingerDialog from '../components/SingerDialog'

type Workflow = 'formation' | 'event' | 'singer' | null

const inputClass =
  'rounded border border-gray-300 px-2 py-1 dark:border-gray-600 dark:bg-gray-800'

const buttonClass = 'rounded bg-blue-600 px-3 py-1 text-white'

const cardClass =
  'rounded border p-4 text-left hover:bg-gray-100 dark:hover:bg-gray-800'

export default function WizardPage() {
  const [workflow, setWorkflow] = useState<Workflow>(null)
  const [step, setStep] = useState(1)
  const [projectId, setProjectId] = useState('')
  const [eventId, setEventId] = useState('')
  const [rows, setRows] = useState('4')
  const [cols, setCols] = useState('5')
  const [done, setDone] = useState<string | null>(null)

  const { data: projects = [] } = useQuery({
    queryKey: ['projects'],
    queryFn: fetchProjects,
  })
  const { data: events = [] } = useQuery({
    queryKey: ['events', projectId, '', ''],
    queryFn: () => fetchEvents({ project_id: projectId || undefined }),
    enabled: workflow === 'formation' && step >= 2,
  })
  const { data: voiceGroups = [] } = useQuery({
    queryKey: ['voice-groups'],
    queryFn: fetchVoiceGroups,
    enabled: workflow === 'singer',
  })

  function reset() {
    setWorkflow(null)
    setStep(1)
    setProjectId('')
    setEventId('')
    setRows('4')
    setCols('5')
    setDone(null)
  }

  function start(selected: Exclude<Workflow, null>) {
    reset()
    setWorkflow(selected)
  }

  const createEventMutation = useMutation({
    mutationFn: (input: EventInput) => createEvent(input),
    onSuccess: () => setDone('Termin angelegt.'),
  })
  const createSingerMutation = useMutation({
    mutationFn: (input: SingerInput) => createSinger(input),
    onSuccess: () => setDone('Mitglied aufgenommen.'),
  })
  const createFormationMutation = useMutation({
    mutationFn: () =>
      createFormation({
        rows: parseInt(rows, 10) || 4,
        cols: parseInt(cols, 10) || 5,
        event_id: eventId || undefined,
      }),
    onSuccess: () => setDone('Aufstellung angelegt.'),
  })

  if (workflow === null) {
    return (
      <section>
        <h1 className="text-xl font-semibold">Assistent</h1>
        <p className="mt-2">Womit soll es losgehen?</p>
        <div className="mt-4 grid max-w-2xl gap-2">
          <button
            type="button"
            onClick={() => start('formation')}
            className={cardClass}
          >
            Aufstellung planen
          </button>
          <button
            type="button"
            onClick={() => start('event')}
            className={cardClass}
          >
            Termin eintragen
          </button>
          <button
            type="button"
            onClick={() => start('singer')}
            className={cardClass}
          >
            Chormitglied aufnehmen
          </button>
        </div>
      </section>
    )
  }

  return (
    <section>
      <h1 className="text-xl font-semibold">Assistent</h1>
      {done ? (
        <div>
          <p className="mt-4">{done}</p>
          <button type="button" onClick={reset} className={`${buttonClass} mt-3`}>
            Neuer Vorgang
          </button>
        </div>
      ) : (
        <div>
          {workflow === 'event' && (
            <div className="mt-4 max-w-md">
              <EventDialog
                projects={projects}
                submitLabel="Anlegen"
                onSubmit={(input) => createEventMutation.mutate(input)}
              />
            </div>
          )}
          {workflow === 'singer' && (
            <div className="mt-4 max-w-md">
              <SingerDialog
                title="Neues Chormitglied"
                initial={{}}
                voiceGroups={voiceGroups}
                onSubmit={(input) => createSingerMutation.mutate(input)}
                onClose={reset}
              />
            </div>
          )}
          {workflow === 'formation' && (
            <FormationFlow
              step={step}
              setStep={setStep}
              projectId={projectId}
              setProjectId={setProjectId}
              eventId={eventId}
              setEventId={setEventId}
              rows={rows}
              setRows={setRows}
              cols={cols}
              setCols={setCols}
              projects={projects}
              events={events}
              onCreate={() => createFormationMutation.mutate()}
            />
          )}
          <button
            type="button"
            onClick={reset}
            className="mt-4 rounded border px-3 py-1"
          >
            Abbrechen
          </button>
        </div>
      )}
    </section>
  )
}

function FormationFlow(props: {
  step: number
  setStep: (step: number) => void
  projectId: string
  setProjectId: (id: string) => void
  eventId: string
  setEventId: (id: string) => void
  rows: string
  setRows: (value: string) => void
  cols: string
  setCols: (value: string) => void
  projects: { id: string; name: string }[]
  events: { id: string; name: string }[]
  onCreate: () => void
}) {
  const {
    step,
    setStep,
    projectId,
    setProjectId,
    eventId,
    setEventId,
    rows,
    setRows,
    cols,
    setCols,
    projects,
    events,
    onCreate,
  } = props
  return (
    <div className="mt-4 max-w-md">
      <p className="text-sm text-gray-600">Schritt {step} von 4</p>
      {step === 1 && (
        <label className="mt-2 block text-sm font-medium">
          Projekt
          <select
            value={projectId}
            onChange={(event) => setProjectId(event.target.value)}
            className={`${inputClass} ml-2`}
          >
            <option value="">–</option>
            {projects.map((project) => (
              <option key={project.id} value={project.id}>
                {project.name}
              </option>
            ))}
          </select>
        </label>
      )}
      {step === 2 && (
        <label className="mt-2 block text-sm font-medium">
          Termin
          <select
            value={eventId}
            onChange={(event) => setEventId(event.target.value)}
            className={`${inputClass} ml-2`}
          >
            <option value="">–</option>
            {events.map((event) => (
              <option key={event.id} value={event.id}>
                {event.name}
              </option>
            ))}
          </select>
        </label>
      )}
      {step === 3 && (
        <p className="mt-2">
          Bitte zuerst die Zusagen für den Termin erfassen:{' '}
          <Link to="/availability" className="text-blue-600 underline">
            Verfügbarkeit öffnen
          </Link>
        </p>
      )}
      {step === 4 && (
        <div className="mt-2 flex gap-2">
          <label className="text-sm font-medium">
            Reihen
            <input
              value={rows}
              inputMode="numeric"
              onChange={(event) => setRows(event.target.value)}
              className={`${inputClass} ml-2 w-16`}
            />
          </label>
          <label className="text-sm font-medium">
            Spalten
            <input
              value={cols}
              inputMode="numeric"
              onChange={(event) => setCols(event.target.value)}
              className={`${inputClass} ml-2 w-16`}
            />
          </label>
        </div>
      )}
      <div className="mt-3 flex gap-2">
        {step > 1 && (
          <button
            type="button"
            onClick={() => setStep(step - 1)}
            className="rounded border px-3 py-1"
          >
            Zurück
          </button>
        )}
        {step < 4 && (
          <button
            type="button"
            onClick={() => setStep(step + 1)}
            disabled={
              (step === 1 && !projectId) || (step === 2 && !eventId)
            }
            className={`${buttonClass} disabled:opacity-40`}
          >
            Weiter
          </button>
        )}
        {step === 4 && (
          <button type="button" onClick={onCreate} className={buttonClass}>
            Aufstellung anlegen
          </button>
        )}
      </div>
    </div>
  )
}
