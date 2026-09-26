import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import {
  createRepertoire,
  deleteRepertoire,
  fetchProjects,
  fetchRepertoire,
  updateRepertoire,
} from '../api/client'
import type { RepertoireEntry, RepertoireInput } from '../api/client'
import { Button, EmptyState, ErrorMessage, IconButton, Loading, PageHeader, Th, Td } from '../components/ui'
import RepertoireDialog from '../components/RepertoireDialog'
import { DeleteIcon, DuplicateIcon, EditIcon } from '../components/icons'

const inputClass =
  'rounded border border-gray-300 px-2 py-1 dark:border-gray-600 dark:bg-gray-800'

type DialogState =
  | { mode: 'new' }
  | { mode: 'edit'; entry: RepertoireEntry }
  | null

export default function RepertoirePage() {
  const [projectId, setProjectId] = useState('')
  const [search, setSearch] = useState('')
  const [sortField, setSortField] = useState('title')
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('asc')
  const [dialog, setDialog] = useState<DialogState>(null)
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
    queryKey: ['repertoire', projectId, search, sortField, sortOrder],
    queryFn: () =>
      fetchRepertoire(
        projectId || undefined,
        search || undefined,
        sortField,
        sortOrder,
      ),
  })

  function invalidate() {
    void queryClient.invalidateQueries({ queryKey: ['repertoire'] })
  }

  const createMutation = useMutation({
    mutationFn: (input: RepertoireInput) => createRepertoire(input),
    onSuccess: () => {
      setDialog(null)
      invalidate()
    },
  })
  const updateMutation = useMutation({
    mutationFn: ({ id, input }: { id: string; input: Partial<RepertoireInput> }) =>
      updateRepertoire(id, input),
    onSuccess: () => {
      setDialog(null)
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

  async function duplicateEntry(entry: RepertoireEntry) {
    const {
      id: _id,
      ...rest
    } = entry as RepertoireEntry & { created_at?: string; updated_at?: string }
    void _id
    await createMutation.mutateAsync({
      ...(rest as RepertoireInput),
      title: `${entry.title} (Kopie)`,
    })
  }

  return (
    <section>
      <PageHeader
        title="Repertoire"
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
        <label>
          Sortieren{' '}
          <select
            value={sortField}
            onChange={(event) => setSortField(event.target.value)}
            className={inputClass}
          >
            <option value="title">Titel</option>
            <option value="composer">Komponist</option>
            <option value="country">Land</option>
            <option value="location">Standort</option>
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
      {!isLoading && !isError && items.length === 0 && (
        <EmptyState text="Keine Stücke gefunden." />
      )}
      {items.length > 0 && (
        <table className="mt-4 w-full border-collapse text-left">
          <thead>
            <tr className="border-b">
              <Th>Komponist</Th>
              <Th>Titel</Th>
              <Th>Lebensdaten</Th>
              <Th>Land</Th>
              <Th>Verlag</Th>
              <Th>Besetzung</Th>
              <Th>Standort</Th>
              <Th>Programm</Th>
              <Th>Aktionen</Th>
            </tr>
          </thead>
          <tbody>
            {items.map((item) => (
              <tr key={item.id} className="border-b border-gray-100 hover:bg-gray-50 dark:border-gray-800 dark:hover:bg-gray-800/50">
                <Td>{item.composer ?? '–'}</Td>
                <Td>{item.title}</Td>
                <Td>{item.dates ?? '–'}</Td>
                <Td>{item.country ?? '–'}</Td>
                <Td>{item.publisher ?? '–'}</Td>
                <Td>{item.arrangement ?? '–'}</Td>
                <Td>{item.location ?? '–'}</Td>
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
                <Td>
                  <div className="flex gap-1">
                    <IconButton
                      label="Bearbeiten"
                      onClick={() => setDialog({ mode: 'edit', entry: item })}
                    >
                      <EditIcon />
                    </IconButton>
                    <IconButton
                      label="Duplizieren"
                      onClick={() => void duplicateEntry(item)}
                    >
                      <DuplicateIcon />
                    </IconButton>
                    {deleteConfirmId === item.id ? (
                      <>
                        <Button
                          size="sm"
                          variant="danger"
                          onClick={() => deleteMutation.mutate(item.id)}
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
                        onClick={() => setDeleteConfirmId(item.id)}
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
        <RepertoireDialog
          projects={projects}
          onSubmit={(input) => createMutation.mutate(input)}
          onClose={() => setDialog(null)}
        />
      )}
      {dialog?.mode === 'edit' && (
        <RepertoireDialog
          title="Stück bearbeiten"
          initial={{
            title: dialog.entry.title,
            composer: dialog.entry.composer ?? undefined,
            dates: dialog.entry.dates ?? undefined,
            country: dialog.entry.country ?? undefined,
            publisher: dialog.entry.publisher ?? undefined,
            arrangement: dialog.entry.arrangement ?? undefined,
            location: dialog.entry.location ?? undefined,
            project_id: dialog.entry.project_id ?? undefined,
          }}
          projects={projects}
          onSubmit={(input) =>
            updateMutation.mutate({ id: dialog.entry.id, input })
          }
          onClose={() => setDialog(null)}
        />
      )}
    </section>
  )
}
