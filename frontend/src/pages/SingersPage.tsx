import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  computeAge,
  createSinger,
  deleteSinger,
  fetchSingers,
  fetchVoiceGroups,
  joinedDisplay,
  updateSinger,
} from '../api/client'
import type { Singer, SingerInput } from '../api/client'
import SingerDialog from '../components/SingerDialog'
import {
  Button,
  EmptyState,
  ErrorMessage,
  IconButton,
  Loading,
  PageHeader,
  Th,
  Td,
  inputClassName,
} from '../components/ui'
import { DeleteIcon, DuplicateIcon, EditIcon } from '../components/icons'

type DialogState = { mode: 'new' } | { mode: 'edit'; singer: Singer } | null
type StatusFilter = 'all' | 'active' | 'minor' | 'u16'
type SortKey =
  | 'full_name-asc'
  | 'full_name-desc'
  | 'short_name-asc'
  | 'short_name-desc'
  | 'birth_date-asc'
  | 'birth_date-desc'
  | 'height-asc'
  | 'height-desc'

const inputClass = inputClassName

function statusOf(singer: Singer): { active: boolean; minor: boolean; u16: boolean } {
  const age = computeAge(singer.birth_date)
  return {
    active: singer.left_year === null || singer.left_year === undefined,
    minor: age !== null && age < 18,
    u16: age !== null && age < 16,
  }
}

function sortSingers(singers: Singer[], sort: SortKey): Singer[] {
  const [field, direction] = sort.split('-') as [
    'full_name' | 'short_name' | 'birth_date' | 'height',
    'asc' | 'desc',
  ]
  const value = (singer: Singer): string | number => {
    if (field === 'height') return singer.height ?? Number.NEGATIVE_INFINITY
    if (field === 'birth_date') return singer.birth_date ?? ''
    if (field === 'short_name') return (singer.short_name ?? '').toLowerCase()
    return singer.full_name.toLowerCase()
  }
  const sorted = [...singers].sort((a, b) => {
    const left = value(a)
    const right = value(b)
    if (left < right) return -1
    if (left > right) return 1
    return 0
  })
  return direction === 'asc' ? sorted : sorted.reverse()
}

export default function SingersPage() {
  const [search, setSearch] = useState('')
  const [voiceFilter, setVoiceFilter] = useState('')
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all')
  const [sort, setSort] = useState<SortKey>('full_name-asc')
  const [dialog, setDialog] = useState<DialogState>(null)
  const [deleteConfirmId, setDeleteConfirmId] = useState<string | null>(null)
  const queryClient = useQueryClient()

  const { data: singers = [], isLoading, isError } = useQuery({
    queryKey: ['singers', search],
    queryFn: () => fetchSingers(search),
  })
  const { data: voiceGroups = [] } = useQuery({
    queryKey: ['voice-groups'],
    queryFn: fetchVoiceGroups,
  })

  function invalidateSingers() {
    void queryClient.invalidateQueries({ queryKey: ['singers'] })
  }

  function toggleSort(field: 'full_name' | 'short_name' | 'birth_date' | 'height') {
    setSort((previous) => {
      const [currentField, currentDirection] = previous.split('-') as [
        string,
        'asc' | 'desc',
      ]
      if (currentField === field) {
        return `${field}-${currentDirection === 'asc' ? 'desc' : 'asc'}` as SortKey
      }
      return `${field}-asc` as SortKey
    })
  }

  function sortIndicator(field: string): string {
    const [currentField, currentDirection] = sort.split('-')
    if (currentField !== field) return ''
    return currentDirection === 'asc' ? ' ▲' : ' ▼'
  }

  function SortHeader({ field, label }: { field: 'full_name' | 'short_name' | 'birth_date' | 'height'; label: string }) {
    return (
      <button type="button" onClick={() => toggleSort(field)}>
        {label}
        {sortIndicator(field)}
      </button>
    )
  }

  const createMutation = useMutation({
    mutationFn: (input: SingerInput) => createSinger(input),
    onSuccess: () => {
      setDialog(null)
      invalidateSingers()
    },
  })
  const updateMutation = useMutation({
    mutationFn: ({ id, input }: { id: string; input: Partial<SingerInput> }) =>
      updateSinger(id, input),
    onSuccess: () => {
      setDialog(null)
      invalidateSingers()
    },
  })
  const deleteMutation = useMutation({
    mutationFn: (id: string) => deleteSinger(id),
    onSuccess: () => {
      setDeleteConfirmId(null)
      invalidateSingers()
    },
  })

  async function duplicateSinger(singer: Singer) {
    const {
      id: _id,
      created_at: _created,
      updated_at: _updated,
      ...rest
    } = singer as Singer & { created_at?: string; updated_at?: string }
    void _id
    void _created
    void _updated
    await createMutation.mutateAsync({
      ...(rest as SingerInput),
      full_name: `${singer.full_name} (Kopie)`,
    })
  }

  const visible = sortSingers(
    singers.filter((singer) => {
      if (voiceFilter && singer.voice_group !== voiceFilter) return false
      if (statusFilter === 'all') return true
      const status = statusOf(singer)
      if (statusFilter === 'active') return status.active
      if (statusFilter === 'minor') return status.minor
      return status.u16
    }),
    sort,
  )

  return (
    <section>
      <PageHeader
        title="Sänger"
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
          Stimmgruppe{' '}
          <select
            value={voiceFilter}
            onChange={(event) => setVoiceFilter(event.target.value)}
            className={inputClass}
          >
            <option value="">Alle Stimmgruppen</option>
            {voiceGroups.map((group) => (
              <option key={group.id} value={group.id}>
                {group.id}
              </option>
            ))}
          </select>
        </label>
        <label>
          Mitglieder{' '}
          <select
            value={statusFilter}
            onChange={(event) => setStatusFilter(event.target.value as StatusFilter)}
            className={inputClass}
          >
            <option value="all">Alle Mitglieder</option>
            <option value="active">Alle aktiven Mitglieder</option>
            <option value="minor">Alle minderjährigen</option>
            <option value="u16">Alle U16</option>
          </select>
        </label>
        <label>
          Sortieren{' '}
          <select
            value={sort}
            onChange={(event) => setSort(event.target.value as SortKey)}
            className={inputClass}
          >
            <option value="full_name-asc">Vollständiger Name ↑</option>
            <option value="full_name-desc">Vollständiger Name ↓</option>
            <option value="short_name-asc">Kurzname ↑</option>
            <option value="short_name-desc">Kurzname ↓</option>
            <option value="birth_date-asc">Alter ↑</option>
            <option value="birth_date-desc">Alter ↓</option>
            <option value="height-asc">Körpergröße ↑</option>
            <option value="height-desc">Körpergröße ↓</option>
          </select>
        </label>
      </div>
      {isLoading && <Loading />}
      {isError && <ErrorMessage text="Fehler beim Laden." />}
      {!isLoading && !isError && visible.length === 0 && (
        <EmptyState text="Keine Sänger gefunden." />
      )}
      {visible.length > 0 && (
        <table className="mt-4 w-full border-collapse text-left">
          <thead>
            <tr className="border-b">
              <Th>
                <SortHeader field="full_name" label="Vollständiger Name" />
              </Th>
              <Th>
                <SortHeader field="short_name" label="Kurzname" />
              </Th>
              <Th>Geburtsdatum</Th>
              <Th>
                <SortHeader field="birth_date" label="Alter" />
              </Th>
              <Th>Stimmgruppe</Th>
              <Th>
                <SortHeader field="height" label="Größe" />
              </Th>
              <Th>E-Mail</Th>
              <Th>Telefon</Th>
              <Th>Straße</Th>
              <Th>PLZ</Th>
              <Th>Ort</Th>
              <Th>Beitritt</Th>
              <Th>Austritt</Th>
              <Th>UUID</Th>
              <Th>Aktionen</Th>
            </tr>
          </thead>
          <tbody>
            {visible.map((singer) => {
              const age = computeAge(singer.birth_date)
              return (
                <tr
                  key={singer.id}
                  className="border-b border-gray-100 hover:bg-gray-50 dark:border-gray-800 dark:hover:bg-gray-800/50"
                >
                  <Td>{singer.full_name}</Td>
                  <Td>{singer.short_name ?? '–'}</Td>
                  <Td>{singer.birth_date?.slice(0, 10) ?? '–'}</Td>
                  <Td>{age ?? '–'}</Td>
                  <Td>{singer.voice_group ?? '–'}</Td>
                  <Td>{singer.height ?? '–'}</Td>
                  <Td>{singer.email ?? '–'}</Td>
                  <Td>{singer.phone ?? '–'}</Td>
                  <Td>{singer.street ?? '–'}</Td>
                  <Td>{singer.postal_code ?? '–'}</Td>
                  <Td>{singer.city ?? '–'}</Td>
                  <Td>{joinedDisplay(singer.joined_year, singer.joined_month)}</Td>
                  <Td>{joinedDisplay(singer.left_year, singer.left_month)}</Td>
                  <Td title={singer.id}>{singer.id.slice(0, 8)}</Td>
                  <Td>
                    <div className="flex gap-1">
                      <IconButton
                        label="Bearbeiten"
                        onClick={() => setDialog({ mode: 'edit', singer })}
                      >
                        <EditIcon />
                      </IconButton>
                      <IconButton
                        label="Duplizieren"
                        onClick={() => void duplicateSinger(singer)}
                      >
                        <DuplicateIcon />
                      </IconButton>
                      {deleteConfirmId === singer.id ? (
                        <>
                          <Button
                            size="sm"
                            variant="danger"
                            onClick={() => deleteMutation.mutate(singer.id)}
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
                          onClick={() => setDeleteConfirmId(singer.id)}
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
      {dialog?.mode === 'new' && (
        <SingerDialog
          title="Sänger anlegen"
          initial={{}}
          voiceGroups={voiceGroups}
          onSubmit={(input) => createMutation.mutate(input)}
          onClose={() => setDialog(null)}
        />
      )}
      {dialog?.mode === 'edit' && (
        <SingerDialog
          title="Sänger bearbeiten"
          initial={dialog.singer}
          voiceGroups={voiceGroups}
          onSubmit={(input) =>
            updateMutation.mutate({ id: dialog.singer.id, input })
          }
          onClose={() => setDialog(null)}
        />
      )}
    </section>
  )
}
