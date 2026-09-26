// Info-Bar (Desktop-Parität: _create_info_bar) — permanenter
// Arbeitskontext unter der Menüleiste, mit Zurücksetzen.
// Namen löst die Bar selbst per API auf (keine Prop-Kaskade).
import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { useActive } from '../active/active'
import { fetchBesetzungen, fetchEvents, fetchProjects } from '../api/client'

function Badge({
  label,
  to,
  name,
  onClear,
  clearLabel,
  tone,
  emptyText,
}: {
  label: string
  to: string
  name: string | null
  onClear: () => void
  clearLabel: string
  tone: string
  emptyText: string
}) {
  return (
    <span className="flex items-center gap-1 text-sm">
      <span className="text-gray-500">{label}:</span>
      {name ? (
        <>
          <Link
            to={to}
            className={`rounded px-2 py-0.5 font-semibold text-white ${tone}`}
          >
            {name}
          </Link>
          <button
            type="button"
            onClick={onClear}
            aria-label={clearLabel}
            title={clearLabel}
            className="rounded px-1 text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-800"
          >
            ×
          </button>
        </>
      ) : (
        <span className="text-gray-400">{emptyText}</span>
      )}
    </span>
  )
}

export default function InfoBar() {
  const active = useActive()
  const { data: projects = [] } = useQuery({
    queryKey: ['projects'],
    queryFn: fetchProjects,
  })
  const { data: besetzungen = [] } = useQuery({
    queryKey: ['besetzungen', ''],
    queryFn: () => fetchBesetzungen(undefined),
  })
  const { data: events = [] } = useQuery({
    queryKey: ['events', '', '', ''],
    queryFn: () => fetchEvents({}),
  })

  const projectName =
    projects.find((project) => project.id === active.projectId)?.name ?? null
  const besetzungName =
    besetzungen.find((besetzung) => besetzung.id === active.besetzungId)?.name ?? null
  const eventName =
    events.find((event) => event.id === active.eventId)?.name ?? null

  return (
    <div className="mb-4 flex flex-wrap items-center gap-4 rounded border-b-2 border-blue-200 bg-sky-50 px-3 py-2 dark:border-blue-900 dark:bg-gray-900">
      <Badge
        label="Aktives Projekt"
        to="/projects"
        name={projectName}
        onClear={active.clearProject}
        clearLabel="Aktives Projekt zurücksetzen"
        tone="bg-blue-600"
        emptyText="Keines"
      />
      <Badge
        label="Aktive Besetzung"
        to="/besetzung"
        name={besetzungName}
        onClear={active.clearBesetzung}
        clearLabel="Aktive Besetzung zurücksetzen"
        tone="bg-blue-600"
        emptyText="Keine"
      />
      <span className="flex-1" />
      <Badge
        label="Aktiver Termin"
        to="/events"
        name={eventName}
        onClear={active.clearEvent}
        clearLabel="Aktiven Termin zurücksetzen"
        tone="bg-orange-500"
        emptyText="Keiner"
      />
    </div>
  )
}
