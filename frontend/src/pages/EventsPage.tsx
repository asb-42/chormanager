import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { fetchEvents, fetchProjects, formatDate } from '../api/client'

const EVENT_TYPES = ['GP', 'OP', 'SOFA', 'Probe', 'Konzert', 'Auftritt']

const inputClass =
  'rounded border border-gray-300 px-2 py-1 dark:border-gray-600 dark:bg-gray-800'

export default function EventsPage() {
  const [projectId, setProjectId] = useState('')
  const [search, setSearch] = useState('')
  const [eventType, setEventType] = useState('')

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
      <h1 className="text-xl font-semibold">Termine</h1>
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
              <th className="py-1 pr-4">Datum</th>
              <th className="py-1 pr-4">Name</th>
              <th className="py-1 pr-4">Typ</th>
              <th className="py-1 pr-4">Projekt</th>
              <th className="py-1 pr-4">Zusagen</th>
              <th className="py-1 pr-4">Vorbehalt</th>
            </tr>
          </thead>
          <tbody>
            {events.map((event) => (
              <tr key={event.id} className="border-b">
                <td className="py-1 pr-4">{formatDate(event.date)}</td>
                <td className="py-1 pr-4">{event.name}</td>
                <td className="py-1 pr-4">{event.event_type}</td>
                <td className="py-1 pr-4">
                  {projectNames[event.project_id ?? ''] ?? '–'}
                </td>
                <td className="py-1 pr-4">{event.yes_count}</td>
                <td className="py-1 pr-4">{event.conditional_count}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  )
}
