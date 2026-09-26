import { Link, useNavigate } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import {
  createFormation,
  deleteFormation,
  fetchEvents,
  fetchFormation,
  fetchFormations,
  putPlacements,
} from '../api/client'
import type { FormationListItem } from '../api/client'
import { Button, EmptyState, ErrorMessage, IconButton, Loading, PageHeader, Th, Td, Field, inputClassName } from '../components/ui'
import { Modal } from '../components/Modal'
import { DeleteIcon, DuplicateIcon, EditIcon } from '../components/icons'
import { formatDateTime } from '../api/client'

type SortKey =
  | 'event_date-desc'
  | 'event_date-asc'
  | 'filename-asc'
  | 'filename-desc'
  | 'modified-desc'
  | 'modified-asc'

function formatSize(bytes: number): string {
  if (bytes >= 1024) return `${Math.floor(bytes / 1024)} KB`
  return `${bytes} B`
}

function eventDateOf(item: FormationListItem): string {
  return item.metadata?.event_date ?? ''
}

function sortFormations(items: FormationListItem[], sort: SortKey): FormationListItem[] {
  const sorted = [...items]
  switch (sort) {
    case 'event_date-desc':
      return sorted.sort((a, b) => eventDateOf(b).localeCompare(eventDateOf(a)))
    case 'event_date-asc':
      return sorted.sort((a, b) => eventDateOf(a).localeCompare(eventDateOf(b)))
    case 'filename-asc':
      return sorted.sort((a, b) => (a.name ?? '').localeCompare(b.name ?? ''))
    case 'filename-desc':
      return sorted.sort((a, b) => (b.name ?? '').localeCompare(a.name ?? ''))
    case 'modified-asc':
      return sorted.sort((a, b) => a.updated_at.localeCompare(b.updated_at))
    case 'modified-desc':
    default:
      return sorted.sort((a, b) => b.updated_at.localeCompare(a.updated_at))
  }
}

export default function FormationsPage() {
  const [showDialog, setShowDialog] = useState(false)
  const [name, setName] = useState('')
  const [rows, setRows] = useState('4')
  const [cols, setCols] = useState('5')
  const [eventId, setEventId] = useState('')
  const [search, setSearch] = useState('')
  const [sort, setSort] = useState<SortKey>('event_date-desc')
  const [deleteConfirmId, setDeleteConfirmId] = useState<string | null>(null)
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { data: items = [], isLoading, isError } = useQuery({
    queryKey: ['formations'],
    queryFn: fetchFormations,
  })
  const { data: events = [] } = useQuery({
    queryKey: ['events', '', '', ''],
    queryFn: () => fetchEvents({}),
    enabled: showDialog,
  })

  function invalidate() {
    void queryClient.invalidateQueries({ queryKey: ['formations'] })
  }

  const deleteMutation = useMutation({
    mutationFn: (id: string) => deleteFormation(id),
    onSuccess: () => {
      setDeleteConfirmId(null)
      invalidate()
    },
  })

  async function handleCreate(event: React.FormEvent) {
    event.preventDefault()
    const created = await createFormation({
      name: name.trim() || undefined,
      rows: parseInt(rows, 10) || 4,
      cols: parseInt(cols, 10) || 5,
      event_id: eventId || undefined,
    })
    navigate(`/formations/${created.id}`)
  }

  async function duplicateFormation(item: FormationListItem) {
    const detail = await fetchFormation(item.id)
    const created = await createFormation({
      name: `${detail.name ?? 'Aufstellung'} (Kopie)`,
      rows: detail.rows,
      cols: detail.cols,
      staggered: detail.staggered,
      event_id: detail.event_id ?? undefined,
    })
    await putPlacements(created.id, {
      rows: detail.rows,
      cols: detail.cols,
      staggered: detail.staggered,
      placements: detail.placed.map((placed) => ({
        singer_id: placed.singer.singer_id,
        row: placed.row,
        col: placed.col,
      })),
    })
    invalidate()
  }

  const needle = search.trim().toLowerCase()
  const visible = sortFormations(
    items.filter((item) => {
      if (needle.length === 0) return true
      const meta = item.metadata ?? {}
      return [
        item.name ?? '',
        meta.project ?? '',
        meta.event ?? '',
        meta.event_date ?? '',
      ].some((field) => field.toLowerCase().includes(needle))
    }),
    sort,
  )

  return (
    <section>
      <PageHeader
        title="Aufstellungen"
        actions={
          <Button variant="primary" onClick={() => setShowDialog(true)}>
            Neu
          </Button>
        }
      />
      <div className="mt-3 flex flex-wrap items-center gap-2">
        <input
          type="search"
          placeholder="Suchen …"
          value={search}
          onChange={(event) => setSearch(event.target.value)}
          className={`${inputClassName} w-48`}
        />
        <label>
          Sortieren{' '}
          <select
            value={sort}
            onChange={(event) => setSort(event.target.value as SortKey)}
            className="rounded border border-gray-300 px-2 py-1 dark:border-gray-600 dark:bg-gray-800"
          >
            <option value="event_date-desc">Termin ↓ (neueste zuerst)</option>
            <option value="event_date-asc">Termin ↑ (älteste zuerst)</option>
            <option value="filename-asc">Dateiname ↑</option>
            <option value="filename-desc">Dateiname ↓</option>
            <option value="modified-desc">Gespeichert ↓ (neueste zuerst)</option>
            <option value="modified-asc">Gespeichert ↑ (älteste zuerst)</option>
          </select>
        </label>
      </div>
      {isLoading && <Loading />}
      {isError && <ErrorMessage text="Fehler beim Laden." />}
      {!isLoading && !isError && visible.length === 0 && !showDialog && (
        <EmptyState
          text="Keine Aufstellungen vorhanden. Lege eine über Neu an oder folge dem Assistenten."
          action={<Link to="/wizard/formation" className="text-blue-600 underline">Assistent (Aufstellung planen)</Link>}
        />
      )}
      {visible.length > 0 && (
        <table className="mt-4 w-full border-collapse text-left">
          <thead>
            <tr className="border-b">
              <Th>Dateiname</Th>
              <Th>Dateigröße</Th>
              <Th>Projekt</Th>
              <Th>Termin</Th>
              <Th>Typ</Th>
              <Th>Gespeichert</Th>
              <Th>Aktionen</Th>
            </tr>
          </thead>
          <tbody>
            {visible.map((item) => {
              const meta = item.metadata ?? {}
              return (
                <tr
                  key={item.id}
                  className="border-b border-gray-100 hover:bg-gray-50 dark:border-gray-800 dark:hover:bg-gray-800/50"
                >
                  <Td>
                    <Link
                      to={`/formations/${item.id}`}
                      className="text-blue-600 underline"
                    >
                      {item.name ?? item.id}
                    </Link>
                  </Td>
                  <Td>{formatSize(item.size ?? 0)}</Td>
                  <Td>{meta.project ?? '–'}</Td>
                  <Td>{(meta.event_date ?? '').slice(0, 10) || '–'}</Td>
                  <Td>{meta.event_type ?? '–'}</Td>
                  <Td>{formatDateTime(item.updated_at)}</Td>
                  <Td>
                    <div className="flex gap-1">
                      <IconButton
                        label="Bearbeiten"
                        onClick={() => navigate(`/formations/${item.id}`)}
                      >
                        <EditIcon />
                      </IconButton>
                      <IconButton
                        label="Duplizieren"
                        onClick={() => void duplicateFormation(item)}
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
              )
            })}
          </tbody>
        </table>
      )}
      {showDialog && (
        <Modal label="Aufstellung anlegen" onClose={() => setShowDialog(false)}>
          <h2 className="text-lg font-semibold">Aufstellung anlegen</h2>
          <form onSubmit={(event) => void handleCreate(event)} className="mt-3 space-y-3">
            <Field label="Name">
              <input
                value={name}
                onChange={(event) => setName(event.target.value)}
                className={inputClassName}
              />
            </Field>
            <div className="flex gap-2">
              <Field label="Reihen">
                <input
                  value={rows}
                  inputMode="numeric"
                  onChange={(event) => setRows(event.target.value)}
                  className={`${inputClassName} w-16`}
                />
              </Field>
              <Field label="Spalten">
                <input
                  value={cols}
                  inputMode="numeric"
                  onChange={(event) => setCols(event.target.value)}
                  className={`${inputClassName} w-16`}
                />
              </Field>
            </div>
            <Field label="Termin (Zusagen übernehmen)">
              <select
                value={eventId}
                onChange={(event) => setEventId(event.target.value)}
                className={inputClassName}
              >
                <option value="">–</option>
                {events.map((event) => (
                  <option key={event.id} value={event.id}>
                    {event.name}
                  </option>
                ))}
              </select>
            </Field>
            <div className="flex gap-2 pt-1">
              <Button type="submit" variant="primary">
                Anlegen
              </Button>
              <Button onClick={() => setShowDialog(false)}>
                Abbrechen
              </Button>
            </div>
          </form>
        </Modal>
      )}
    </section>
  )
}
