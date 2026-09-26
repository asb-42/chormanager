import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { fetchSingers } from '../api/client'

export default function SingersPage() {
  const [search, setSearch] = useState('')
  const { data: singers = [], isLoading, isError } = useQuery({
    queryKey: ['singers', search],
    queryFn: () => fetchSingers(search),
  })

  return (
    <section>
      <h1 className="text-xl font-semibold">Sänger</h1>
      <input
        type="search"
        placeholder="Suchen …"
        value={search}
        onChange={(event) => setSearch(event.target.value)}
        className="mt-3 w-64 rounded border border-gray-300 px-2 py-1 dark:border-gray-600 dark:bg-gray-800"
      />
      {isLoading && <p className="mt-4">Lädt …</p>}
      {isError && <p className="mt-4 text-red-600">Fehler beim Laden.</p>}
      {!isLoading && !isError && singers.length === 0 && (
        <p className="mt-4">Keine Sänger gefunden.</p>
      )}
      {singers.length > 0 && (
        <table className="mt-4 w-full border-collapse text-left">
          <thead>
            <tr className="border-b">
              <th className="py-1 pr-4">Name</th>
              <th className="py-1 pr-4">Kurzname</th>
              <th className="py-1 pr-4">Stimmgruppe</th>
            </tr>
          </thead>
          <tbody>
            {singers.map((singer) => (
              <tr key={singer.id} className="border-b">
                <td className="py-1 pr-4">{singer.full_name}</td>
                <td className="py-1 pr-4">{singer.short_name ?? '–'}</td>
                <td className="py-1 pr-4">{singer.voice_group ?? '–'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  )
}
