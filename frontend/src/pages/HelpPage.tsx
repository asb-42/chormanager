import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { fetchVersion } from '../api/client'
import { Button, PageHeader } from '../components/ui'

export default function HelpPage() {
  const [checkedAt, setCheckedAt] = useState<Date | null>(null)
  const queryClient = useQueryClient()
  const { data } = useQuery({
    queryKey: ['version'],
    queryFn: fetchVersion,
    retry: false,
    staleTime: Infinity,
  })

  async function checkVersion() {
    await queryClient.invalidateQueries({ queryKey: ['version'] })
    setCheckedAt(new Date())
  }

  return (
    <section>
      <PageHeader title="Hilfe" />
      <h2 className="mt-4 font-semibold">Über ChorManager Web</h2>
      <p className="mt-1 text-sm">
        Chorverwaltung im Browser. {`Backend-Version: ${data ? data.version : '–'}`}
      </p>
      <Button className="mt-2" onClick={() => void checkVersion()}>
        Version prüfen
      </Button>
      {checkedAt && (
        <p className="mt-1 text-sm">
          Geprüft um {checkedAt.toLocaleTimeString()}.
        </p>
      )}
      <h2 className="mt-4 font-semibold">Anleitungen</h2>
      <p className="mt-1 text-sm">
        Web-Anleitung: <code>docs/benutzerhandbuch-web.md</code> im Repo.
        Desktop-Anleitung: <code>docs/benutzerhandbuch.md</code>.
      </p>
    </section>
  )
}
