// Info-Bar (Desktop-Parität: _create_info_bar) — permanenter
// Arbeitskontext unter der Menüleiste, mit Zurücksetzen.
// Namen löst die Bar selbst per API auf (keine Prop-Kaskade).
import { Link } from 'react-router-dom'
import { useEffect } from 'react'
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
    <span className="flex items-center gap-1.5 text-sm">
      <span className="font-medium text-warm-500 dark:text-warm-400">{label}:</span>
      {name ? (
        <>
          <Link
            to={to}
            className={`inline-flex items-center rounded-lg px-2.5 py-1 text-sm font-semibold text-white shadow-soft transition-transform hover:scale-[1.02] ${tone}`}
          >
            {name}
          </Link>
          <button
            type="button"
            onClick={onClear}
            aria-label={clearLabel}
            title={clearLabel}
            className="rounded-lg p-1 text-warm-400 hover:bg-warm-100 hover:text-warm-600 dark:hover:bg-warm-800 dark:hover:text-warm-300"
          >
            <svg className="h-3.5 w-3.5" viewBox="0 0 20 20" fill="currentColor">
              <path d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z" />
            </svg>
          </button>
        </>
      ) : (
        <span className="text-warm-400 dark:text-warm-500">{emptyText}</span>
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

  // Verwaiste IDs aufräumen (Desktop-Parität: gelöschte Aktive
  // dürfen nicht als Karteileichen liegen bleiben). Zusätzlich gilt
  // Projektbindung: Eine Besetzung gehört zu genau einem Projekt —
  // passt sie nicht zum aktiven Projekt, wird sie zurückgesetzt.
  useEffect(() => {
    if (active.projectId && projects.length > 0 && !projectName) {
      active.clearProject()
    }
    const activeBesetzungRow = besetzungen.find(
      (besetzung) => besetzung.id === active.besetzungId,
    )
    if (active.besetzungId && besetzungen.length > 0 && !activeBesetzungRow) {
      active.clearBesetzung()
    }
    if (
      activeBesetzungRow &&
      active.projectId &&
      activeBesetzungRow.project_id &&
      activeBesetzungRow.project_id !== active.projectId
    ) {
      active.clearBesetzung()
    }
    if (active.eventId && events.length > 0 && !eventName) {
      active.clearEvent()
    }
    // Nur auf Datenwechsel reagieren (nicht auf jede active-Änderung).
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projects, besetzungen, events])

  return (
    <div className="mb-6 flex flex-wrap items-center gap-3 rounded-xl border border-warm-200 bg-gradient-to-r from-warm-50 to-primary-50/30 px-4 py-3 shadow-soft dark:border-warm-700 dark:from-warm-800 dark:to-primary-900/20">
      <Badge
        label="Aktives Projekt"
        to="/projects"
        name={projectName}
        onClear={active.clearProject}
        clearLabel="Aktives Projekt zurücksetzen"
        tone="bg-primary-600"
        emptyText="Keines"
      />
      <Badge
        label="Aktive Besetzung"
        to="/besetzung"
        name={besetzungName}
        onClear={active.clearBesetzung}
        clearLabel="Aktive Besetzung zurücksetzen"
        tone="bg-primary-600"
        emptyText="Keine"
      />
      <span className="flex-1" />
      <Badge
        label="Aktiver Termin"
        to="/events"
        name={eventName}
        onClear={active.clearEvent}
        clearLabel="Aktiven Termin zurücksetzen"
        tone="bg-accent-500"
        emptyText="Keiner"
      />
    </div>
  )
}
