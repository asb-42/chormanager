import { useEffect, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  fetchAvailabilityMatrix,
  fetchEvents,
  putAvailabilityBulk,
} from '../api/client'
import { Th, Td,
  PageHeader,} from '../components/ui'

const STATUSES = [
  { value: 'yes', label: '✓ Zusage' },
  { value: 'no', label: '✗ Absage' },
  { value: 'none', label: '○ keine Rückmeldung' },
  { value: 'conditional', label: '✓? Vorbehalt' },
  { value: 'unknown', label: '? Weiß nicht' },
  { value: 'maybe', label: '~ Vielleicht' },
]

const inputClass =
  'rounded border border-gray-300 px-2 py-1 dark:border-gray-600 dark:bg-gray-800'

export default function AvailabilityPage() {
  const [eventId, setEventId] = useState<string | null>(null)
  const [overrides, setOverrides] = useState<Record<string, string>>({})
  const [savedMessage, setSavedMessage] = useState(false)
  const queryClient = useQueryClient()

  const { data: events = [] } = useQuery({
    queryKey: ['events', '', '', ''],
    queryFn: () => fetchEvents({}),
  })

  useEffect(() => {
    if (eventId === null && events.length > 0) {
      setEventId(events[0].id)
    }
  }, [eventId, events])

  const { data: matrix, isLoading, isError } = useQuery({
    queryKey: ['availability', eventId],
    queryFn: () => fetchAvailabilityMatrix(eventId as string),
    enabled: eventId !== null,
  })

  const saveMutation = useMutation({
    mutationFn: () =>
      putAvailabilityBulk(
        eventId as string,
        (matrix?.entries ?? []).map((entry) => ({
          singer_id: entry.singer_id,
          status: overrides[entry.singer_id] ?? entry.status,
        })),
      ),
    onSuccess: () => {
      setOverrides({})
      setSavedMessage(true)
      void queryClient.invalidateQueries({ queryKey: ['availability'] })
    },
  })

  function pickEvent(id: string) {
    setEventId(id)
    setOverrides({})
    setSavedMessage(false)
  }

  return (
    <section>
      <PageHeader title="Verfügbarkeit" />
      <div className="mt-3 flex flex-wrap items-center gap-2">
        <label>
          Termin{' '}
          <select
            value={eventId ?? ''}
            onChange={(event) => pickEvent(event.target.value)}
            className={inputClass}
          >
            {events.map((event) => (
              <option key={event.id} value={event.id}>
                {event.name}
              </option>
            ))}
          </select>
        </label>
        <button
          type="button"
          onClick={() => saveMutation.mutate()}
          disabled={eventId === null || saveMutation.isPending}
          className="rounded bg-blue-600 px-3 py-1 text-white disabled:opacity-40"
        >
          Speichern
        </button>
        {savedMessage && <span>Gespeichert.</span>}
      </div>
      {isLoading && <p className="mt-4">Lädt …</p>}
      {isError && <p className="mt-4 text-red-600">Fehler beim Laden.</p>}
      {saveMutation.isError && (
        <p className="mt-4 text-red-600">Speichern fehlgeschlagen.</p>
      )}
      {matrix && matrix.entries.length > 0 && (
        <table className="mt-4 w-full border-collapse text-left">
          <thead>
            <tr className="border-b">
              <Th>Name</Th>
              <Th>Stimmgruppe</Th>
              <Th>Status</Th>
            </tr>
          </thead>
          <tbody>
            {matrix.entries.map((entry) => (
              <tr key={entry.singer_id} className="border-b border-gray-100 hover:bg-gray-50 dark:border-gray-800 dark:hover:bg-gray-800/50">
                <Td>{entry.full_name}</Td>
                <Td>{entry.voice_group ?? '–'}</Td>
                <Td>
                  <select
                    aria-label={entry.full_name}
                    value={overrides[entry.singer_id] ?? entry.status}
                    onChange={(event) =>
                      setOverrides((previous) => ({
                        ...previous,
                        [entry.singer_id]: event.target.value,
                      }))
                    }
                    className={inputClass}
                  >
                    {STATUSES.map((status) => (
                      <option key={status.value} value={status.value}>
                        {status.label}
                      </option>
                    ))}
                  </select>
                </Td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  )
}
