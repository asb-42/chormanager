import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import {
  createBesetzung,
  deleteBesetzung,
  fetchBesetzungen,
  fetchProjects,
  fetchSingers,
} from '../api/client'
import { Button, PageHeader, Th, Td } from '../components/ui'
import type { BesetzungInput } from '../api/client'
import BesetzungDialog from '../components/BesetzungDialog'
import { useActive } from '../active/active'

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
      <Button size="sm" onClick={onAsk}>
        Löschen
      </Button>
    )
  }
  return (
    <div className="flex gap-2">
      <Button size="sm" variant="danger" onClick={onConfirm}>
        Wirklich löschen
      </Button>
      <Button size="sm" onClick={onCancel}>
        Abbrechen
      </Button>
    </div>
  )
}

export default function BesetzungPage() {
  const [projectId, setProjectId] = useState('')
  const [showDialog, setShowDialog] = useState(false)
  const [deleteConfirmId, setDeleteConfirmId] = useState<string | null>(null)
  const queryClient = useQueryClient()
  const active = useActive()

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
      <PageHeader title="Besetzung" />
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
        <Button variant="primary" onClick={() => setShowDialog(true)}>
          Neu
        </Button>
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
              <Th>Name</Th>
              <Th>Projekt</Th>
              <Th>Sänger</Th>
              <Th>Aktionen</Th>
            </tr>
          </thead>
          <tbody>
            {items.map((item) => (
              <tr key={item.id} className="border-b border-gray-100 hover:bg-gray-50 dark:border-gray-800 dark:hover:bg-gray-800/50">
                <Td>{item.name}</Td>
                <Td>
                  {item.project_id ? (
                    <Link
                      to={`/projects/${item.project_id}`}
                      className="text-blue-600 underline"
                    >
                      {projectNames[item.project_id] ?? item.project_id}
                    </Link>
                  ) : (
                    '–'
                  )}
                </Td>
                <Td>{item.singer_ids.length}</Td>
                <Td>
                  <div className="flex items-center gap-2">
                    {active.besetzungId === item.id ? (
                      <span className="rounded bg-blue-600 px-2 py-0.5 text-xs font-semibold text-white">
                        Aktiv
                      </span>
                    ) : (
                      <Button size="sm" onClick={() => active.setBesetzung(item.id)}>
                        Als aktiv setzen
                      </Button>
                    )}
                    <DeleteButtons
                      confirming={deleteConfirmId === item.id}
                      onAsk={() => setDeleteConfirmId(item.id)}
                      onConfirm={() => deleteMutation.mutate(item.id)}
                      onCancel={() => setDeleteConfirmId(null)}
                    />
                  </div>
                </Td>
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
