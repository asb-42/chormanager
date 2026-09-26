import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  createBesetzung,
  deleteBesetzung,
  fetchBesetzungen,
  fetchProjects,
  fetchSingers,
} from '../api/client'
import type { BesetzungInput } from '../api/client'
import BesetzungDialog from '../components/BesetzungDialog'

const inputClass =
  'rounded border border-gray-300 px-2 py-1 dark:border-gray-600 dark:bg-gray-800'

function DeleteButtons({
  confirming,
  onAsk,
  onConfirm,
  onCancel,
}: {
  confirming: boolean
  onAsk: () => void
  onConfirm: () => void
  onCancel: () => void
}) {
  if (!confirming) {
    return (
      <button type="button" onClick={onAsk} className="rounded border px-2 py-0.5">
        Löschen
      </button>
    )
  }
  return (
    <div className="flex gap-2">
      <button
        type="button"
        onClick={onConfirm}
        className="rounded bg-red-600 px-2 py-0.5 text-white"
      >
        Wirklich löschen
      </button>
      <button
        type="button"
        onClick={onCancel}
        className="rounded border px-2 py-0.5"
      >
        Abbrechen
      </button>
    </div>
  )
}

export default function BesetzungPage() {
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
  const { data: singers = [] } = useQuery({
    queryKey: ['singers', ''],
    queryFn: () => fetchSingers(''),
  })
  const { data: items = [], isLoading, isError } = useQuery({
    queryKey: ['besetzungen', projectId],
    queryFn: () => fetchBesetzungen(projectId || undefined),
  })

  function invalidate() {
    void queryClient.invalidateQueries({ queryKey: ['besetzungen'] })
  }

  const createMutation = useMutation({
    mutationFn: (input: BesetzungInput) => createBesetzung(input),
    onSuccess: () => {
      setShowDialog(false)
      invalidate()
    },
  })
  const deleteMutation = useMutation({
    mutationFn: (id: string) => deleteBesetzung(id),
    onSuccess: () => {
      setDeleteConfirmId(null)
      invalidate()
    },
  })

  return (
    <section>
      <h1 className="text-xl font-semibold">Besetzung</h1>
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
        <p className="mt-4">Keine Besetzungen gefunden.</p>
      )}
      {items.length > 0 && (
        <table className="mt-4 w-full border-collapse text-left">
          <thead>
            <tr className="border-b">
              <th className="py-1 pr-4">Name</th>
              <th className="py-1 pr-4">Projekt</th>
              <th className="py-1 pr-4">Sänger</th>
              <th className="py-1 pr-4">Aktionen</th>
            </tr>
          </thead>
          <tbody>
            {items.map((item) => (
              <tr key={item.id} className="border-b">
                <td className="py-1 pr-4">{item.name}</td>
                <td className="py-1 pr-4">
                  {projectNames[item.project_id ?? ''] ?? '–'}
                </td>
                <td className="py-1 pr-4">{item.singer_ids.length}</td>
                <td className="py-1 pr-4">
                  <DeleteButtons
                    confirming={deleteConfirmId === item.id}
                    onAsk={() => setDeleteConfirmId(item.id)}
                    onConfirm={() => deleteMutation.mutate(item.id)}
                    onCancel={() => setDeleteConfirmId(null)}
                  />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      {showDialog && (
        <BesetzungDialog
          projects={projects}
          singers={singers}
          onSubmit={(input) => createMutation.mutate(input)}
          onClose={() => setShowDialog(false)}
        />
      )}
    </section>
  )
}
