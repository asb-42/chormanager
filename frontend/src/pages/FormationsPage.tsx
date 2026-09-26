import { Link, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { createFormation, fetchEvents, fetchFormations } from '../api/client'
import { PageHeader } from '../components/ui'
import { Th, Td } from '../components/ui'
import { Modal } from '../components/Modal'

const inputClass =
  'w-full rounded border border-gray-300 px-2 py-1 dark:border-gray-600 dark:bg-gray-800'

export default function FormationsPage() {
  const [showDialog, setShowDialog] = useState(false)
  const [name, setName] = useState('')
  const [rows, setRows] = useState('4')
  const [cols, setCols] = useState('5')
  const [eventId, setEventId] = useState('')
  const navigate = useNavigate()
  const { data: items = [], isLoading, isError } = useQuery({
    queryKey: ['formations'],
    queryFn: fetchFormations,
  })
  const { data: events = [] } = useQuery({
    queryKey: ['events', '', '', ''],
    queryFn: () => fetchEvents({}),
    enabled: showDialog,
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

  return (
    <section>
      <PageHeader title="Aufstellungen" />
      <div className="mt-3">
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
      {!isLoading && !isError && items.length === 0 && !showDialog && (
        <p className="mt-4">
          Keine Aufstellungen vorhanden. Lege eine über „Neu" an oder
          folge dem{' '}
          <Link to="/wizard/formation" className="text-blue-600 underline">
            Assistenten (Aufstellung planen)
          </Link>
          .
        </p>
      )}
      {items.length > 0 && (
        <table className="mt-4 w-full border-collapse text-left">
          <thead>
            <tr className="border-b">
              <Th>Name</Th>
              <Th>Raster</Th>
            </tr>
          </thead>
          <tbody>
            {items.map((item) => (
              <tr key={item.id} className="border-b">
                <Td>
                  <Link
                    to={`/formations/${item.id}`}
                    className="text-blue-600 underline"
                  >
                    {item.name ?? item.id}
                  </Link>
                </Td>
                <Td>
                  {item.rows}×{item.cols}
                </Td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      {showDialog && (
        <Modal label="Aufstellung anlegen" onClose={() => setShowDialog(false)}>
          <h2 className="text-lg font-semibold">Aufstellung anlegen</h2>
          <h2 className="text-lg font-semibold">Aufstellung anlegen</h2>
          <form onSubmit={(event) => void handleCreate(event)} className="mt-2 space-y-2">
            <label className="block text-sm font-medium">
              Name
              <input
                value={name}
                onChange={(event) => setName(event.target.value)}
                className={inputClass}
              />
            </label>
            <div className="flex gap-2">
              <label className="text-sm font-medium">
                Reihen
                <input
                  value={rows}
                  inputMode="numeric"
                  onChange={(event) => setRows(event.target.value)}
                  className={`${inputClass} ml-2 w-16`}
                />
              </label>
              <label className="text-sm font-medium">
                Spalten
                <input
                  value={cols}
                  inputMode="numeric"
                  onChange={(event) => setCols(event.target.value)}
                  className={`${inputClass} ml-2 w-16`}
                />
              </label>
            </div>
            <label className="block text-sm font-medium">
              Termin (Zusagen übernehmen)
              <select
                value={eventId}
                onChange={(event) => setEventId(event.target.value)}
                className={inputClass}
              >
                <option value="">–</option>
                {events.map((event) => (
                  <option key={event.id} value={event.id}>
                    {event.name}
                  </option>
                ))}
              </select>
            </label>
            <div className="flex gap-2 pt-1">
              <button
                type="submit"
                className="rounded bg-blue-600 px-3 py-1 text-white"
              >
                Anlegen
              </button>
              <button
                type="button"
                onClick={() => setShowDialog(false)}
                className="rounded border px-3 py-1"
              >
                Abbrechen
              </button>
            </div>
          </form>
        </Modal>
      )}
    </section>
  )
}
