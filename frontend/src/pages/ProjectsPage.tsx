import { useEffect, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useParams } from 'react-router-dom'
import { fetchProjects, fetchProjectSummary, formatDate } from '../api/client'

export default function ProjectsPage() {
  const params = useParams<{ id?: string }>()
  const [selectedId, setSelectedId] = useState<string | null>(params.id ?? null)
  const { data: projects = [], isLoading, isError } = useQuery({
    queryKey: ['projects'],
    queryFn: fetchProjects,
  })
  const { data: summary } = useQuery({
    queryKey: ['project-summary', selectedId],
    queryFn: () => fetchProjectSummary(selectedId as string),
    enabled: selectedId !== null,
  })

  useEffect(() => {
    if (params.id) setSelectedId(params.id)
  }, [params.id])

  return (
    <section>
      <h1 className="text-xl font-semibold">Projekte</h1>
      {isLoading && <p className="mt-4">Lädt …</p>}
      {isError && <p className="mt-4 text-red-600">Fehler beim Laden.</p>}
      <ul className="mt-4 space-y-1">
        {projects.map((project) => (
          <li key={project.id}>
            <button
              type="button"
              onClick={() => setSelectedId(project.id)}
              className={`rounded px-2 py-1 text-left hover:bg-gray-100 dark:hover:bg-gray-800 ${
                selectedId === project.id
                  ? 'bg-gray-200 dark:bg-gray-700'
                  : ''
              }`}
            >
              {project.name}
            </button>
          </li>
        ))}
      </ul>
      {summary && (
        <div className="mt-6">
          <h2 className="text-lg font-semibold">Zusagen je Termin</h2>
          <table className="mt-2 w-full border-collapse text-left">
            <thead>
              <tr className="border-b">
                <th className="py-1 pr-4">Datum</th>
                <th className="py-1 pr-4">Name</th>
                <th className="py-1 pr-4">Zusagen</th>
                <th className="py-1 pr-4">Vorbehalt</th>
              </tr>
            </thead>
            <tbody>
              {summary.events.map((event) => (
                <tr key={event.event_id} className="border-b">
                  <td className="py-1 pr-4">{formatDate(event.date)}</td>
                  <td className="py-1 pr-4">{event.name}</td>
                  <td className="py-1 pr-4">{event.yes}</td>
                  <td className="py-1 pr-4">{event.conditional}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <h2 className="mt-4 text-lg font-semibold">Zusagen je Stimmgruppe</h2>
          <table className="mt-2 w-full border-collapse text-left">
            <thead>
              <tr className="border-b">
                <th className="py-1 pr-4">Stimmgruppe</th>
                <th className="py-1 pr-4">Zusagen</th>
                <th className="py-1 pr-4">Vorbehalt</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(summary.by_voice_group).map(
                ([group, counts]) => (
                  <tr key={group} className="border-b">
                    <td className="py-1 pr-4">{group}</td>
                    <td className="py-1 pr-4">{counts.yes ?? 0}</td>
                    <td className="py-1 pr-4">{counts.conditional ?? 0}</td>
                  </tr>
                ),
              )}
            </tbody>
          </table>
        </div>
      )}
    </section>
  )
}
