import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { fetchVersion } from '../api/client'
import { PageHeader } from '../components/ui'

export default function AboutPage() {
  const { data } = useQuery({
    queryKey: ['version'],
    queryFn: fetchVersion,
    retry: false,
    staleTime: Infinity,
  })

  return (
    <section>
      <PageHeader title="Über ChorManager" />
      <p className="mt-4 max-w-2xl">
        ChorManager Web ist die Browser-Version der Chorverwaltung:
        Sänger, Termine, Projekte, Besetzungen, Verfügbarkeiten und
        Aufstellungen – mit derselben Datenbasis wie die
        Qt-Desktop-Anwendung.
      </p>
      <p className="mt-2 text-sm text-gray-600">
        {`Backend-Version: ${data ? data.version : '–'}`}
      </p>
      <p className="mt-4">
        <Link to="/help" className="text-blue-600 underline">
          Zur Hilfe
        </Link>
      </p>
    </section>
  )
}
