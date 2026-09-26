import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { fetchFormations } from '../api/client'

export default function FormationsPage() {
  const { data: items = [], isLoading, isError } = useQuery({
    queryKey: ['formations'],
    queryFn: fetchFormations,
  })

  return (
    <section>
      <h1 className="text-xl font-semibold">Aufstellungen</h1>
      {isLoading && <p className="mt-4">Lädt …</p>}
      {isError && <p className="mt-4 text-red-600">Fehler beim Laden.</p>}
      {!isLoading && !isError && items.length === 0 && (
        <p className="mt-4">Keine Aufstellungen vorhanden.</p>
      )}
      {items.length > 0 && (
        <table className="mt-4 w-full border-collapse text-left">
          <thead>
            <tr className="border-b">
              <th className="py-1 pr-4">Name</th>
              <th className="py-1 pr-4">Raster</th>
            </tr>
          </thead>
          <tbody>
            {items.map((item) => (
              <tr key={item.id} className="border-b">
                <td className="py-1 pr-4">
                  <Link
                    to={`/formations/${item.id}`}
                    className="text-blue-600 underline"
                  >
                    {item.name ?? item.id}
                  </Link>
                </td>
                <td className="py-1 pr-4">
                  {item.rows}×{item.cols}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  )
}
