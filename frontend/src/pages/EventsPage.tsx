import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import {
  createEvent,
  deleteEvent,
  fetchEvents,
  fetchProjects,
  formatDate,
  updateEvent,
} from '../api/client'
import type { EventInput, EventItem } from '../api/client'
import { Button, EmptyState, ErrorMessage, IconButton, Loading, PageHeader, Th, Td } from '../components/ui'
import EventDialog from '../components/EventDialog'
import { Modal } from '../components/Modal'
import { DeleteIcon, DuplicateIcon, EditIcon } from '../components/icons'
import { useActive } from '../active/active'

const EVENT_TYPES = ['GP', 'OP', 'SOFA', 'Probe', 'Konzert', 'Auftritt']

const inputClass =
  'rounded border border-gray-300 px-2 py-1 dark:border-gray-600 dark:bg-gray-800'

type DialogState =
  | { mode: 'new' }
  | { mode: 'edit'; event: EventItem }
  | null

export default function EventsPage() {
  const [projectId, setProjectId] = useState('')
  const [search, setSearch] = useState('')
  const [eventType, setEventType] = useState('')
  const [sort, setSort] = useState('date-desc')
  const [dialog, setDialog] = useState<DialogState>(null)
  const [deleteConfirmId, setDeleteConfirmId] = useState<string | null>(null)
  const active = useActive()
  const queryClient = useQueryClient()

  const { data: projects = [] } = useQuery({
    queryKey: ['projects'],
    queryFn: fetchProjects,
  })
  const projectNames = Object.fromEntries(
    projects.map((project) => [project.id, project.name]),
  )

  const { data: events = [], isLoading, isError } = useQuery({
    queryKey: ['events', projectId, search, eventType, sort],
    queryFn: () =>
      fetchEvents({
        project_id: projectId || undefined,
        search: search || undefined,
        event_type: eventType || undefined,
        sort: (sort.split('-')[0] ?? 'date') as 'date' | 'name',
        direction: (sort.split('-')[1] ?? 'desc') as 'asc' | 'desc',
      }),
  })

  function invalidate() {
    void queryClient.invalidateQueries({ queryKey: ['events'] })
  }

  const createMutation = useMutation({
    mutationFn: (input: EventInput) => createEvent(input),
    onSuccess: () => {
      setDialog(null)
      invalidate()
    },
  })
  const updateMutation = useMutation({
    mutationFn: ({ id, input }: { id: string; input: Partial<EventInput> }) =>
      updateEvent(id, input),
    onSuccess: () => {
      setDialog(null)
      invalidate()
    },
  })
  const deleteMutation = useMutation({
    mutationFn: (id: string) => deleteEvent(id),
    onSuccess: () => {
      setDeleteConfirmId(null)
      invalidate()
    },
  })

  async function duplicateEvent(event: EventItem) {
    const created = await createMutation.mutateAsync({
      name: `${event.name} (Kopie)`,
      date: event.date,
      event_type: event.event_type,
      location: event.location ?? undefined,
      description: event.description ?? undefined,
      project_id: event.project_id ?? undefined,
    })
    setDialog({ mode: 'edit', event: created })
  }

  return (
    <section>
      <PageHeader
        title="Termine"
        actions={
          <Button variant="primary" onClick={() => setDialog({ mode: 'new' })}>
            Hinzufügen
          </Button>
        }
      />
      <div className="mt-3 flex flex-wrap gap-2">
        <label>
          Projekt{' '}
          <select
            value={projectId}
            onChange={(event) => setProjectId(event.target.value)}
            className={inputClass}
          >
            <option value="">Alle</option>
            {projects.map((project) => (
              <option key={project.id} value={project.id}>
                {project.name}
              </option>
            ))}
          </select>
        </label>
        <input
          type="search"
          placeholder="Suchen …"
          value={search}
          onChange={(event) => setSearch(event.target.value)}
          className={inputClass}
        />
        <select
          aria-label="Typ"
          value={eventType}
          onChange={(event) => setEventType(event.target.value)}
          className={inputClass}
        >
          <option value="">Alle Typen</option>
          {EVENT_TYPES.map((type) => (
            <option key={type} value={type}>
              {type}
            </option>
          ))}
        </select>
        <label>
          Sortieren{' '}
          <select
            value={sort}
            onChange={(event) => setSort(event.target.value)}
            className={inputClass}
          >
            <option value="date-desc">Datum ↓ (neueste zuerst)</option>
            <option value="date-asc">Datum ↑ (älteste zuerst)</option>
            <option value="name-asc">Name ↑</option>
            <option value="name-desc">Name ↓</option>
          </select>
        </label>
      </div>
      {isLoading && <Loading />}
      {isError && <ErrorMessage text="Fehler beim Laden." />}
      {!isLoading && !isError && events.length === 0 && (
        <EmptyState text="Keine Termine gefunden." />
      )}
      {events.length > 0 && (
        <table className="mt-4 w-full border-collapse text-left">
          <thead>
            <tr className="border-b">
              <Th>Datum</Th>
              <Th>Name</Th>
              <Th>Typ</Th>
              <Th>Projekt</Th>
              <Th>Zusagen</Th>
              <Th>Vorbehalt</Th>
              <Th>Status</Th>
              <Th>Aktionen</Th>
            </tr>
          </thead>
          <tbody>
            {events.map((event) => (
              <tr key={event.id} className="border-b border-gray-100 hover:bg-gray-50 dark:border-gray-800 dark:hover:bg-gray-800/50">
                <Td>{formatDate(event.date)}</Td>
                <Td>{event.name}</Td>
                <Td>{event.event_type}</Td>
                <Td>
                  {event.project_id ? (
                    <Link
                      to={`/projects/${event.project_id}`}
                      className="text-blue-600 underline"
                    >
                      {projectNames[event.project_id] ?? event.project_id}
                    </Link>
                  ) : (
                    '–'
                  )}
                </Td>
                <Td>{event.yes_count}</Td>
                <Td>{event.conditional_count}</Td>
                <Td>
                  {active.eventId === event.id ? (
                    <span className="rounded bg-orange-500 px-2 py-0.5 text-xs font-semibold text-white">
                      Aktiv
                    </span>
                  ) : (
                    <Button size="sm" onClick={() => active.setEvent(event.id)}>
                      Aktiv
                    </Button>
                  )}
                </Td>
                <Td>
                  <div className="flex gap-1">
                    <IconButton
                      label="Bearbeiten"
                      onClick={() => setDialog({ mode: 'edit', event })}
                    >
                      <EditIcon />
                    </IconButton>
                    <IconButton
                      label="Duplizieren"
                      onClick={() => void duplicateEvent(event)}
                    >
                      <DuplicateIcon />
                    </IconButton>
                    {deleteConfirmId === event.id ? (
                      <>
                        <Button
                          size="sm"
                          variant="danger"
                          onClick={() => deleteMutation.mutate(event.id)}
                        >
                          Wirklich löschen
                        </Button>
                        <Button size="sm" onClick={() => setDeleteConfirmId(null)}>
                          Abbrechen
                        </Button>
                      </>
                    ) : (
                      <IconButton
                        label="Löschen"
                        onClick={() => setDeleteConfirmId(event.id)}
                      >
                        <DeleteIcon />
                      </IconButton>
                    )}
                  </div>
                </Td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      {dialog && (
        <Modal
          label={dialog.mode === 'new' ? 'Termin anlegen' : 'Termin bearbeiten'}
          onClose={() => setDialog(null)}
        >
          <h2 className="text-lg font-semibold">
            {dialog.mode === 'new' ? 'Termin anlegen' : 'Termin bearbeiten'}
          </h2>
          <EventDialog
            initial={
              dialog.mode === 'edit'
                ? {
                    name: dialog.event.name,
                    date: dialog.event.date,
                    event_type: dialog.event.event_type,
                    location: dialog.event.location ?? undefined,
                    description: dialog.event.description ?? undefined,
                    project_id: dialog.event.project_id ?? undefined,
                  }
                : {}
            }
            projects={projects}
            submitLabel={dialog.mode === 'new' ? 'Anlegen' : 'Speichern'}
            onClose={() => setDialog(null)}
            onSubmit={(input) => {
              if (dialog.mode === 'new') {
                createMutation.mutate(input)
              } else {
                updateMutation.mutate({ id: dialog.event.id, input })
              }
            }}
          />
        </Modal>
      )}
    </section>
  )
}
