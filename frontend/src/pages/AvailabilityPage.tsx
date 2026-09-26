import { useEffect, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  fetchAvailabilityMatrix,
  fetchBesetzungen,
  fetchEvents,
  putAvailabilityBulk,
} from '../api/client'
import { Button, PageHeader, Th, Td } from '../components/ui'
import { useActive } from '../active/active'

const STATUS_DOT: Record<string, string> = {
  yes: 'bg-green-600',
  no: 'bg-red-600',
  none: 'bg-gray-300',
  conditional: 'bg-amber-500',
  unknown: 'bg-gray-400',
  maybe: 'bg-yellow-400',
}

export function StatusDot({ status }: { status: string }) {
  return (
    <span
      data-status-dot={status}
      title={status}
      aria-hidden="true"
      className={`mr-2 inline-block h-2.5 w-2.5 rounded-full ${STATUS_DOT[status] ?? 'bg-gray-300'}`}
    />
  )
}

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
  const active = useActive()
  const [eventId, setEventId] = useState<string | null>(active.eventId)
  const [overrides, setOverrides] = useState<Record<string, string>>({})
  const [savedMessage, setSavedMessage] = useState(false)
  const [showAll, setShowAll] = useState(false)
  const queryClient = useQueryClient()

  const { data: events = [] } = useQuery({
    queryKey: ['events', '', '', ''],
    queryFn: () => fetchEvents({}),
  })
  const { data: besetzungen = [] } = useQuery({
    queryKey: ['besetzungen', ''],
    queryFn: () => fetchBesetzungen(undefined),
  })

  useEffect(() => {
    if (eventId === null && events.length > 0) {
      const initial = active.eventId ?? events[0].id
      setEventId(initial)
    }
    // Absichtlich nur beim Laden der Terminliste (aktiver Termin sonst).
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [events])

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
    active.setEvent(id)
    setOverrides({})
    setSavedMessage(false)
    setShowAll(false)
  }

  const activeBesetzung = besetzungen.find(
    (besetzung) => besetzung.id === active.besetzungId,
  )
  const visibleEntries = (matrix?.entries ?? []).filter(
    (entry) =>
      showAll ||
      !activeBesetzung ||
      activeBesetzung.singer_ids.includes(entry.singer_id),
  )

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
        <Button
          variant="primary"
          onClick={() => saveMutation.mutate()}
          disabled={eventId === null || saveMutation.isPending}
        >
          Speichern
        </Button>
        {savedMessage && <span>Gespeichert.</span>}
        {activeBesetzung && (
          <span className="text-sm text-gray-600">
            Gefiltert auf Besetzung {activeBesetzung.name} (
            {visibleEntries.length} von {matrix?.entries.length ?? 0}).{' '}
            <Button
              size="sm"
              variant="ghost"
              onClick={() => setShowAll((previous) => !previous)}
            >
              {showAll ? 'Nur Besetzung zeigen' : 'Alle Sänger zeigen'}
            </Button>
          </span>
        )}
      </div>
      {isLoading && <p className="mt-4">Lädt …</p>}
      {isError && <p className="mt-4 text-red-600">Fehler beim Laden.</p>}
      {saveMutation.isError && (
        <p className="mt-4 text-red-600">Speichern fehlgeschlagen.</p>
      )}
      {matrix && visibleEntries.length > 0 && (
        <table className="mt-4 w-full border-collapse text-left">
          <thead>
            <tr className="border-b">
              <Th>Name</Th>
              <Th>Stimmgruppe</Th>
              <Th>Status</Th>
            </tr>
          </thead>
          <tbody>
            {visibleEntries.map((entry) => (
              <tr key={entry.singer_id} className="border-b border-gray-100 hover:bg-gray-50 dark:border-gray-800 dark:hover:bg-gray-800/50">
                <Td>{entry.full_name}</Td>
                <Td>{entry.voice_group ?? '–'}</Td>
                <Td>
                  <span className="flex items-center">
                    <StatusDot status={overrides[entry.singer_id] ?? entry.status} />
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
                  </span>
                </Td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  )
}
