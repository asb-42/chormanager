import { useEffect, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useParams } from 'react-router-dom'
import {
  createProject,
  deleteProject,
  fetchProject,
  fetchProjects,
  fetchProjectSummary,
  formatDate,
  updateProject,
} from '../api/client'
import type { ProjectInput } from '../api/client'
import { Button, EmptyState, ErrorMessage, IconButton, Loading, PageHeader, Th, Td } from '../components/ui'
import ProjectDialog from '../components/ProjectDialog'
import { DeleteIcon, DuplicateIcon, EditIcon } from '../components/icons'
import { useActive } from '../active/active'

type DialogState =
  | { mode: 'new' }
  | { mode: 'edit'; id: string; name: string; description: string; spielzeit: string }
  | null

const inputClass =
  'rounded border border-gray-300 px-2 py-1 dark:border-gray-600 dark:bg-gray-800'

export default function ProjectsPage() {
  const params = useParams<{ id?: string }>()
  const [selectedId, setSelectedId] = useState<string | null>(params.id ?? null)
  const [search, setSearch] = useState('')
  const [sortField, setSortField] = useState<'name' | 'spielzeit'>('name')
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('asc')
  const [dialog, setDialog] = useState<DialogState>(null)
  const [deleteConfirmId, setDeleteConfirmId] = useState<string | null>(null)
  const active = useActive()
  const queryClient = useQueryClient()

  useEffect(() => {
    if (params.id) setSelectedId(params.id)
  }, [params.id])

  const { data: projects = [], isLoading, isError } = useQuery({
    queryKey: ['projects'],
    queryFn: fetchProjects,
  })
  const { data: summary } = useQuery({
    queryKey: ['project-summary', selectedId],
    queryFn: () => fetchProjectSummary(selectedId as string),
    enabled: selectedId !== null,
  })

  function invalidate() {
    void queryClient.invalidateQueries({ queryKey: ['projects'] })
  }

  const createMutation = useMutation({
    mutationFn: (input: ProjectInput) => createProject(input),
    onSuccess: () => {
      setDialog(null)
      invalidate()
    },
  })
  const updateMutation = useMutation({
    mutationFn: ({ id, input }: { id: string; input: Partial<ProjectInput> }) =>
      updateProject(id, input),
    onSuccess: () => {
      setDialog(null)
      invalidate()
    },
  })
  const deleteMutation = useMutation({
    mutationFn: (id: string) => deleteProject(id),
    onSuccess: (_data, id) => {
      setDeleteConfirmId(null)
      if (active.projectId === id) active.clearProject()
      if (selectedId === id) setSelectedId(null)
      invalidate()
    },
  })

  async function duplicateProject(id: string) {
    const project = await fetchProject(id)
    await createMutation.mutateAsync({
      name: `${project.name} (Kopie)`,
      description: project.description ?? undefined,
      spielzeit: project.spielzeit ?? undefined,
    })
  }

  const needle = search.trim().toLowerCase()
  const visible = projects
    .filter(
      (project) =>
        needle.length === 0 ||
        project.name.toLowerCase().includes(needle) ||
        (project.description ?? '').toLowerCase().includes(needle) ||
        (project.spielzeit ?? '').toLowerCase().includes(needle),
    )
    .sort((a, b) => {
      const left = (sortField === 'name' ? a.name : (a.spielzeit ?? '')).toLowerCase()
      const right = (sortField === 'name' ? b.name : (b.spielzeit ?? '')).toLowerCase()
      const compared = left.localeCompare(right)
      return sortOrder === 'asc' ? compared : -compared
    })

  return (
    <section>
      <PageHeader
        title="Projekte"
        actions={
          <Button variant="primary" onClick={() => setDialog({ mode: 'new' })}>
            Hinzufügen
          </Button>
        }
      />
      <div className="mt-3 flex flex-wrap items-center gap-2">
        <input
          type="search"
          placeholder="Suchen …"
          value={search}
          onChange={(event) => setSearch(event.target.value)}
          className={`${inputClass} w-48`}
        />
        <label>
          Sortieren{' '}
          <select
            value={sortField}
            onChange={(event) => setSortField(event.target.value as 'name' | 'spielzeit')}
            className={inputClass}
          >
            <option value="name">Name</option>
            <option value="spielzeit">Spielzeit</option>
          </select>
        </label>
        <label>
          Reihenfolge{' '}
          <select
            value={sortOrder}
            onChange={(event) => setSortOrder(event.target.value as 'asc' | 'desc')}
            className={inputClass}
          >
            <option value="asc">Aufsteigend</option>
            <option value="desc">Absteigend</option>
          </select>
        </label>
      </div>
      {isLoading && <Loading />}
      {isError && <ErrorMessage text="Fehler beim Laden." />}
      {!isLoading && !isError && visible.length === 0 && (
        <EmptyState text="Keine Projekte gefunden." />
      )}
      {visible.length > 0 && (
        <table className="mt-4 w-full border-collapse text-left">
          <thead>
            <tr className="border-b">
              <Th>Spielzeit</Th>
              <Th>Name</Th>
              <Th>Beschreibung</Th>
              <Th>Aktiv</Th>
              <Th>Anz. Termine</Th>
              <Th>Aktionen</Th>
            </tr>
          </thead>
          <tbody>
            {visible.map((project) => (
              <tr
                key={project.id}
                className="border-b border-gray-100 hover:bg-gray-50 dark:border-gray-800 dark:hover:bg-gray-800/50"
              >
                <Td>{project.spielzeit ?? '–'}</Td>
                <Td>
                  <button
                    type="button"
                    onClick={() => setSelectedId(project.id)}
                    className="text-left hover:underline"
                  >
                    {project.name}
                  </button>
                </Td>
                <Td>{project.description ?? '–'}</Td>
                <Td>
                  {active.projectId === project.id ? (
                    <span className="rounded bg-blue-600 px-2 py-0.5 text-xs font-semibold text-white">
                      Aktiv
                    </span>
                  ) : (
                    <Button size="sm" onClick={() => active.setProject(project.id)}>
                      Als aktiv setzen
                    </Button>
                  )}
                </Td>
                <Td>{project.event_count ?? 0}</Td>
                <Td>
                  <div className="flex gap-1">
                    <IconButton
                      label="Bearbeiten"
                      onClick={() =>
                        setDialog({
                          mode: 'edit',
                          id: project.id,
                          name: project.name,
                          description: project.description ?? '',
                          spielzeit: project.spielzeit ?? '',
                        })
                      }
                    >
                      <EditIcon />
                    </IconButton>
                    <IconButton
                      label="Duplizieren"
                      onClick={() => void duplicateProject(project.id)}
                    >
                      <DuplicateIcon />
                    </IconButton>
                    {deleteConfirmId === project.id ? (
                      <>
                        <Button
                          size="sm"
                          variant="danger"
                          onClick={() => deleteMutation.mutate(project.id)}
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
                        onClick={() => setDeleteConfirmId(project.id)}
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
      {dialog?.mode === 'new' && (
        <ProjectDialog
          title="Neues Projekt"
          submitLabel="Anlegen"
          initial={{}}
          onSubmit={(input) => createMutation.mutate(input)}
          onClose={() => setDialog(null)}
        />
      )}
      {dialog?.mode === 'edit' && (
        <ProjectDialog
          title="Projekt bearbeiten"
          submitLabel="Speichern"
          initial={{
            name: dialog.name,
            description: dialog.description,
            spielzeit: dialog.spielzeit,
          }}
          onSubmit={(input) => updateMutation.mutate({ id: dialog.id, input })}
          onClose={() => setDialog(null)}
        />
      )}
      {summary && (
        <div className="mt-6">
          <h2 className="text-lg font-semibold">Zusagen je Termin</h2>
          <table className="mt-2 w-full border-collapse text-left">
            <thead>
              <tr className="border-b">
                <Th>Datum</Th>
                <Th>Name</Th>
                <Th>Zusagen</Th>
                <Th>Vorbehalt</Th>
              </tr>
            </thead>
            <tbody>
              {summary.events.map((event) => (
                <tr key={event.event_id} className="border-b border-gray-100 hover:bg-gray-50 dark:border-gray-800 dark:hover:bg-gray-800/50">
                  <Td>{formatDate(event.date)}</Td>
                  <Td>{event.name}</Td>
                  <Td>{event.yes}</Td>
                  <Td>{event.conditional}</Td>
                </tr>
              ))}
            </tbody>
          </table>
          <h2 className="mt-4 text-lg font-semibold">Zusagen je Stimmgruppe</h2>
          <table className="mt-2 w-full border-collapse text-left">
            <thead>
              <tr className="border-b">
                <Th>Stimmgruppe</Th>
                <Th>Zusagen</Th>
                <Th>Vorbehalt</Th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(summary.by_voice_group).map(
                ([group, counts]) => (
                  <tr key={group} className="border-b border-gray-100 hover:bg-gray-50 dark:border-gray-800 dark:hover:bg-gray-800/50">
                    <Td>{group}</Td>
                    <Td>{counts.yes ?? 0}</Td>
                    <Td>{counts.conditional ?? 0}</Td>
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
