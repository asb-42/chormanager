import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  createSinger,
  deleteSinger,
  fetchSingers,
  fetchVoiceGroups,
  updateSinger,
} from '../api/client'
import type { Singer, SingerInput } from '../api/client'
import SingerDialog from '../components/SingerDialog'
import {
  Button,
  EmptyState,
  ErrorMessage,
  Loading,
  PageHeader,
  Th,
  Td,
  inputClassName,
} from '../components/ui'

type DialogState = { mode: 'new' } | { mode: 'edit'; singer: Singer } | null

export default function SingersPage() {
  const [search, setSearch] = useState('')
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

  return (
    <section>
      <PageHeader
        title="Sänger"
        actions={
          <>
            <input
              type="search"
              placeholder="Suchen …"
              aria-label="Suchen"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              className={`${inputClassName} w-64`}
            />
            <Button variant="primary" onClick={() => setDialog({ mode: 'new' })}>
              Neu
            </Button>
          </>
        }
      />
      {isLoading && <Loading />}
      {isError && <ErrorMessage text="Fehler beim Laden." />}
      {!isLoading && !isError && singers.length === 0 && (
        <EmptyState text="Keine Sänger gefunden." />
      )}
      {singers.length > 0 && (
        <table className="mt-4 w-full border-collapse text-left">
          <thead>
            <tr className="border-b">
              <Th>Name</Th>
              <Th>Kurzname</Th>
              <Th>Stimmgruppe</Th>
              <Th>Aktionen</Th>
            </tr>
          </thead>
          <tbody>
            {singers.map((singer) => (
              <tr key={singer.id} className="border-b">
                <Td>{singer.full_name}</Td>
                <Td>{singer.short_name ?? '–'}</Td>
                <Td>{singer.voice_group ?? '–'}</Td>
                <Td>
                  <div className="flex gap-2">
                    <Button size="sm" onClick={() => setDialog({ mode: 'edit', singer })}>
                      Bearbeiten
                    </Button>
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
                      <Button size="sm" onClick={() => setDeleteConfirmId(singer.id)}>
                        Löschen
                      </Button>
                    )}
                  </div>
                </Td>
              </tr>
            ))}
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
