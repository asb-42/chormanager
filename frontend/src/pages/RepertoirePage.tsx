import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  createRepertoire,
  deleteRepertoire,
  fetchProjects,
  fetchRepertoire,
} from '../api/client'
import type { RepertoireInput } from '../api/client'
import RepertoireDialog from '../components/RepertoireDialog'

const inputClass =
  'rounded border border-gray-300 px-2 py-1 dark:border-gray-600 dark:bg-gray-800'

export default function RepertoirePage() {
  const [projectId, setProjectId] = useState('')
  const [showDialog, setShowDialog] = useState(false)
  const [deleteConfirmId, setDeleteConfirmId] = useState<string | null>(null)
  const queryClient = useQueryClient()

  const { data: projects = [] } = useQuery({
    queryKey: ['projects'],
    queryFn: fetchProjects,
  })
  const projectNames = Object.fromEntries(
    projects.map((project) => [project.id, project.name]),
  )
  const { data: items = [], isLoading, isError } = useQuery({
    queryKey: ['repertoire', projectId],
    queryFn: () => fetchRepertoire(projectId || undefined),
  })

  function invalidate() {
    void queryClient.invalidateQueries({ queryKey: ['repertoire'] })
  }

  const createMutation = useMutation({
    mutationFn: (input: RepertoireInput) => createRepertoire(input),
    onSuccess: () => {
      setShowDialog(false)
      invalidate()
    },
  })
  const deleteMutation = useMutation({
    mutationFn: (id: string) => deleteRepertoire(id),
    onSuccess: () => {
      setDeleteConfirmId(null)
      invalidate()
    },
  })

  return (
    <section>
      <h1 className="text-xl font-semibold">Repertoire</h1>
      <div className="mt-3 flex flex-wrap items-center gap-2">
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
        <button
          type="button"
          onClick={() => setShowDialog(true)}
          className="rounded bg-blue-600 px-3 py-1 text-white"
        >
          Neu
        </button>
      </div>
      {isLoading && <p className="mt-4">Lädt …</p>}
      {isError && <p className="mt-4 text-red-600">Fehler beim Laden.</p>}
      {!isLoading && !isError && items.length === 0 && (
        <p className="mt-4">Keine Stücke gefunden.</p>
      )}
      {items.length > 0 && (
        <table className="mt-4 w-full border-collapse text-left">
          <thead>
            <tr className="border-b">
              <th className="py-1 pr-4">Titel</th>
              <th className="py-1 pr-4">Komponist</th>
              <th className="py-1 pr-4">Projekt</th>
              <th className="py-1 pr-4">Aktionen</th>
            </tr>
          </thead>
          <tbody>
            {items.map((item) => (
              <tr key={item.id} className="border-b">
                <td className="py-1 pr-4">{item.title}</td>
                <td className="py-1 pr-4">{item.composer ?? '–'}</td>
                <td className="py-1 pr-4">
                  {projectNames[item.project_id ?? ''] ?? '–'}
                </td>
                <td className="py-1 pr-4">
                  {deleteConfirmId === item.id ? (
                    <div className="flex gap-2">
                      <button
                        type="button"
                        onClick={() => deleteMutation.mutate(item.id)}
                        className="rounded bg-red-600 px-2 py-0.5 text-white"
                      >
                        Wirklich löschen
                      </button>
                      <button
                        type="button"
                        onClick={() => setDeleteConfirmId(null)}
                        className="rounded border px-2 py-0.5"
                      >
                        Abbrechen
                      </button>
                    </div>
                  ) : (
                    <button
                      type="button"
                      onClick={() => setDeleteConfirmId(item.id)}
                      className="rounded border px-2 py-0.5"
                    >
                      Löschen
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      {showDialog && (
        <RepertoireDialog
          projects={projects}
          onSubmit={(input) => createMutation.mutate(input)}
          onClose={() => setShowDialog(false)}
        />
      )}
    </section>
  )
}
