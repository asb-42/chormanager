import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { fetchVersion } from '../api/client'
import { PageHeader } from '../components/ui'

const inputClass =
  'w-full rounded border border-gray-300 px-2 py-1 dark:border-gray-600 dark:bg-gray-800'

export default function SettingsPage() {
  const [token, setToken] = useState(
    () => window.localStorage.getItem('chor-api-token') ?? '',
  )
  const [message, setMessage] = useState<string | null>(null)
  const { data: version } = useQuery({
    queryKey: ['version'],
    queryFn: fetchVersion,
    retry: false,
    staleTime: Infinity,
  })

  function saveToken() {
    if (token.trim()) {
      window.localStorage.setItem('chor-api-token', token.trim())
      setMessage('Token gespeichert.')
    } else {
      window.localStorage.removeItem('chor-api-token')
      setMessage('Token gelöscht.')
    }
  }

  function clearToken() {
    window.localStorage.removeItem('chor-api-token')
    setToken('')
    setMessage('Token gelöscht.')
  }

  return (
    <section>
      <PageHeader title="Konfiguration" />
      <div className="mt-4 max-w-md">
        <h2 className="font-semibold">API-Token</h2>
        <p className="text-sm text-gray-600">
          Für schreibende Aktionen (vom Chorleiter vergeben). Leer lassen
          im offenen Entwicklungsbetrieb.
        </p>
        <label className="mt-1 block text-sm font-medium">
          API-Token
          <input
            type="password"
            value={token}
            onChange={(event) => setToken(event.target.value)}
            className={inputClass}
          />
        </label>
        <div className="mt-2 flex gap-2">
          <button
            type="button"
            onClick={saveToken}
            className="rounded bg-blue-600 px-3 py-1 text-white"
          >
            Token speichern
          </button>
          <button
            type="button"
            onClick={clearToken}
            className="rounded border px-3 py-1"
          >
            Token löschen
          </button>
        </div>
        {message && <p className="mt-2">{message}</p>}
        <h2 className="mt-6 font-semibold">Server</h2>
        <p className="text-sm">
          {`Backend-Version: ${version ? version.version : '–'}`}
        </p>
      </div>
    </section>
  )
}
