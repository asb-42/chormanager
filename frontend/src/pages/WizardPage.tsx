import { useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { Link, useNavigate, useParams } from 'react-router-dom'
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
import { useActive } from '../active/active'
import { Button, PageHeader } from '../components/ui'

type Workflow = 'formation' | 'event' | 'singer' | 'availability' | null

const FLOWS: Exclude<Workflow, null>[] = ['formation', 'event', 'singer', 'availability']

function initialWorkflow(flow: string | undefined): Workflow {
  return (FLOWS as string[]).includes(flow ?? '')
    ? (flow as Exclude<Workflow, null>)
    : null
}

const inputClass =
  'rounded border border-gray-300 px-2 py-1 dark:border-gray-600 dark:bg-gray-800'

const cardClass =
  'rounded border p-4 text-left hover:bg-gray-100 dark:hover:bg-gray-800'

export default function WizardPage() {
  const params = useParams<{ flow?: string }>()
  const active = useActive()
  const navigate = useNavigate()
  const [workflow, setWorkflow] = useState<Workflow>(() =>
    initialWorkflow(params.flow),
  )
  const [step, setStep] = useState(1)
  const [projectId, setProjectId] = useState(active.projectId ?? '')
  const [eventId, setEventId] = useState(active.eventId ?? '')
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
    enabled:
      (workflow === 'formation' && step >= 2) || workflow === 'availability',
  })
  const { data: voiceGroups = [] } = useQuery({
    queryKey: ['voice-groups'],
    queryFn: fetchVoiceGroups,
    enabled: workflow === 'singer',
  })

  function reset() {
    setWorkflow(null)
    setStep(1)
    setProjectId(active.projectId ?? '')
    setEventId(active.eventId ?? '')
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
        <PageHeader title="Assistent" />
        <p className="mt-2">Womit soll es losgehen?</p>
        <div className="mt-4 grid max-w-2xl gap-2">
          <button
            type="button"
            onClick={() => start('formation')}
            className={cardClass}
          >
            Eine Aufstellung für einen Auftritt planen
          </button>
          <button
            type="button"
            onClick={() => start('event')}
            className={cardClass}
          >
            Einen neuen Termin eintragen
          </button>
          <button
            type="button"
            onClick={() => start('availability')}
            className={cardClass}
          >
            Zusagen und Absagen für einen Termin erfassen
          </button>
          <button
            type="button"
            onClick={() => start('singer')}
            className={cardClass}
          >
            Ein Chormitglied aufnehmen
          </button>
        </div>
      </section>
    )
  }

  return (
    <section>
      <PageHeader title="Assistent" />
      {done ? (
        <div>
          <p className="mt-4">{done}</p>
          <Button variant="primary" className="mt-3" onClick={reset}>
            Neuer Vorgang
          </Button>
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
          {workflow === 'availability' && (
            <AvailabilityFlow
              step={step}
              setStep={setStep}
              eventId={eventId}
              setEventId={setEventId}
              events={events}
              onOpen={() => {
                active.setEvent(eventId)
                navigate('/availability')
              }}
            />
          )}
          <Button className="mt-4" onClick={reset}>
            Abbrechen
          </Button>
        </div>
      )}
    </section>
  )
}

function AvailabilityFlow(props: {
  step: number
  setStep: (step: number) => void
  eventId: string
  setEventId: (id: string) => void
  events: { id: string; name: string }[]
  onOpen: () => void
}) {
  const { step, setStep, eventId, setEventId, events, onOpen } = props
  return (
    <div className="mt-4 max-w-md">
      <p className="text-sm text-gray-600">Schritt {step} von 2</p>
      {step === 1 && (
        <label className="mt-2 block text-sm font-medium">
          Termin
          <select
            value={eventId}
            onChange={(event) => setEventId(event.target.value)}
            className="ml-2 rounded border border-gray-300 px-2 py-1 dark:border-gray-600 dark:bg-gray-800"
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
      {step === 2 && (
        <p className="mt-2">
          Markieren Sie pro Sänger, ob er beim Termin dabei ist.
          Mindestens eine Zusage ist nötig.
        </p>
      )}
      <div className="mt-3 flex gap-2">
        {step > 1 && (
          <Button onClick={() => setStep(step - 1)}>Zurück</Button>
        )}
        {step === 1 && (
          <Button
            variant="primary"
            onClick={() => setStep(2)}
            disabled={!eventId}
          >
            Weiter
          </Button>
        )}
        {step === 2 && (
          <Button variant="primary" onClick={onOpen}>
            Verfügbarkeit öffnen
          </Button>
        )}
      </div>
    </div>
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
          <Button onClick={() => setStep(step - 1)}>Zurück</Button>
        )}
        {step < 4 && (
          <Button
            variant="primary"
            onClick={() => setStep(step + 1)}
            disabled={
              (step === 1 && !projectId) || (step === 2 && !eventId)
            }
          >
            Weiter
          </Button>
        )}
        {step === 4 && (
          <Button variant="primary" onClick={onCreate}>
            Aufstellung anlegen
          </Button>
        )}
      </div>
    </div>
  )
}
