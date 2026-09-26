import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { fetchEvents, fetchProjects, formatDate } from '../api/client'
import { Button, PageHeader, Th, Td } from '../components/ui'
import { useActive } from '../active/active'

const EVENT_TYPES = ['GP', 'OP', 'SOFA', 'Probe', 'Konzert', 'Auftritt']

const inputClass =
  'rounded border border-gray-300 px-2 py-1 dark:border-gray-600 dark:bg-gray-800'

export default function EventsPage() {
  const [projectId, setProjectId] = useState('')
  const [search, setSearch] = useState('')
  const [eventType, setEventType] = useState('')
  const active = useActive()

  const { data: projects = [] } = useQuery({
    queryKey: ['projects'],
    queryFn: fetchProjects,
  })
  const projectNames = Object.fromEntries(
    projects.map((project) => [project.id, project.name]),
  )

  const { data: events = [], isLoading, isError } = useQuery({
    queryKey: ['events', projectId, search, eventType],
    queryFn: () =>
      fetchEvents({
        project_id: projectId || undefined,
        search: search || undefined,
        event_type: eventType || undefined,
      }),
  })

  return (
    <section>
      <PageHeader title="Termine" />
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
      </div>
      {isLoading && <p className="mt-4">Lädt …</p>}
      {isError && <p className="mt-4 text-red-600">Fehler beim Laden.</p>}
      {!isLoading && !isError && events.length === 0 && (
        <p className="mt-4">Keine Termine gefunden.</p>
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
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  )
}
