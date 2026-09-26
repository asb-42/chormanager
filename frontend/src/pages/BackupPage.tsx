import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  createBackup,
  deleteBackup,
  fetchBackups,
  restoreBackup,
} from '../api/client'

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : 'Unbekannter Fehler'
}

export default function BackupPage() {
  const [restoreConfirmId, setRestoreConfirmId] = useState<string | null>(null)
  const [deleteConfirmId, setDeleteConfirmId] = useState<string | null>(null)
  const [message, setMessage] = useState<string | null>(null)
  const queryClient = useQueryClient()

  const { data: items = [], isLoading, isError, error } = useQuery({
    queryKey: ['backups'],
    queryFn: fetchBackups,
  })

  function invalidate() {
    void queryClient.invalidateQueries({ queryKey: ['backups'] })
  }

  const createMutation = useMutation({
    mutationFn: () => createBackup(),
    onSuccess: () => {
      setMessage(null)
      invalidate()
    },
    onError: (error) => setMessage(`Anlegen fehlgeschlagen: ${errorMessage(error)}`),
  })
  const restoreMutation = useMutation({
    mutationFn: (id: string) => restoreBackup(id),
    onSuccess: () => {
      setRestoreConfirmId(null)
      setMessage('Wiederhergestellt.')
      invalidate()
    },
    onError: (error) => setMessage(`Wiederherstellen fehlgeschlagen: ${errorMessage(error)}`),
  })
  const deleteMutation = useMutation({
    mutationFn: (id: string) => deleteBackup(id),
    onSuccess: () => {
      setDeleteConfirmId(null)
      invalidate()
    },
    onError: (error) => setMessage(`Löschen fehlgeschlagen: ${errorMessage(error)}`),
  })

  return (
    <section>
      <h1 className="text-xl font-semibold">Backup</h1>
      <div className="mt-3">
        <button
          type="button"
          onClick={() => createMutation.mutate()}
          className="rounded bg-blue-600 px-3 py-1 text-white"
        >
          Backup anlegen
        </button>
      </div>
      {message && <p className="mt-2">{message}</p>}
      {isLoading && <p className="mt-4">Lädt …</p>}
      {isError && (
        <p className="mt-4 text-red-600">Fehler beim Laden: {errorMessage(error)}</p>
      )}
      {!isLoading && !isError && items.length === 0 && (
        <p className="mt-4">Keine Backups vorhanden.</p>
      )}
      {items.length > 0 && (
        <table className="mt-4 w-full border-collapse text-left">
          <thead>
            <tr className="border-b">
              <th className="py-1 pr-4">Datei</th>
              <th className="py-1 pr-4">Größe</th>
              <th className="py-1 pr-4">Aktionen</th>
            </tr>
          </thead>
          <tbody>
            {items.map((item) => (
              <tr key={item.id} className="border-b">
                <td className="py-1 pr-4">{item.id}</td>
                <td className="py-1 pr-4">{item.size} B</td>
                <td className="py-1 pr-4">
                  <div className="flex gap-2">
                    {restoreConfirmId === item.id ? (
                      <>
                        <button
                          type="button"
                          onClick={() => restoreMutation.mutate(item.id)}
                          className="rounded bg-green-700 px-2 py-0.5 text-white"
                        >
                          Wirklich wiederherstellen
                        </button>
                        <button
                          type="button"
                          onClick={() => setRestoreConfirmId(null)}
                          className="rounded border px-2 py-0.5"
                        >
                          Abbrechen
                        </button>
                      </>
                    ) : (
                      <button
                        type="button"
                        onClick={() => setRestoreConfirmId(item.id)}
                        className="rounded border px-2 py-0.5"
                      >
                        Wiederherstellen
                      </button>
                    )}
                    {deleteConfirmId === item.id ? (
                      <>
                        <button
                          type="button"
                          onClick={() => deleteMutation.mutate(item.id)}
                          className="rounded bg-red-600 px-2 py-0.5 text-white"
                        >
                          Wirklich löschen
                        </button>
                        <button
                          type="button"
                          onClick={() => setDeleteConfirmId(null)}
                          className="rounded border px-2 py-0.5"
                        >
                          Abbrechen
                        </button>
                      </>
                    ) : (
                      <button
                        type="button"
                        onClick={() => setDeleteConfirmId(item.id)}
                        className="rounded border px-2 py-0.5"
                      >
                        Löschen
                      </button>
                    )}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  )
}
