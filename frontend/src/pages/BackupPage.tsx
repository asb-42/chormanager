import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  createBackup,
  deleteBackup,
  fetchBackups,
  restoreBackup,
} from '../api/client'
import { Button, PageHeader, Th, Td } from '../components/ui'

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
      <PageHeader title="Backup" />
      <div className="mt-3">
        <Button variant="primary" onClick={() => createMutation.mutate()}>
          Backup anlegen
        </Button>
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
              <Th>Datei</Th>
              <Th>Größe</Th>
              <Th>Aktionen</Th>
            </tr>
          </thead>
          <tbody>
            {items.map((item) => (
              <tr key={item.id} className="border-b border-gray-100 hover:bg-gray-50 dark:border-gray-800 dark:hover:bg-gray-800/50">
                <Td>{item.id}</Td>
                <Td>{item.size} B</Td>
                <Td>
                  <div className="flex gap-2">
                    {restoreConfirmId === item.id ? (
                      <>
                        <Button
                          size="sm"
                          variant="success"
                          onClick={() => restoreMutation.mutate(item.id)}
                        >
                          Wirklich wiederherstellen
                        </Button>
                        <Button
                          size="sm"
                          onClick={() => setRestoreConfirmId(null)}
                          >
                          Abbrechen
                        </Button>
                      </>
                    ) : (
                      <Button
                        size="sm"
                        onClick={() => setRestoreConfirmId(item.id)}
                        >
                        Wiederherstellen
                        </Button>
                    )}
                    {deleteConfirmId === item.id ? (
                      <>
                        <Button
                          size="sm"
                          variant="danger"
                          onClick={() => deleteMutation.mutate(item.id)}
                        >
                          Wirklich löschen
                        </Button>
                        <Button
                          size="sm"
                          onClick={() => setDeleteConfirmId(null)}
                          >
                          Abbrechen
                        </Button>
                      </>
                    ) : (
                      <Button
                        size="sm"
                        onClick={() => setDeleteConfirmId(item.id)}
                        >
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
    </section>
  )
}
